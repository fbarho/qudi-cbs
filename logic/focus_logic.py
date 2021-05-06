# -*- coding: utf-8 -*-
"""
Extension for qudi software

This module contains a class to control the focus of the microscope objective carried by a piezo.
"""
from core.connector import Connector
from core.configoption import ConfigOption
# from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic
from qtpy import QtCore
from time import sleep
import numpy as np
from numpy.polynomial import Polynomial as Poly
from functools import partial


class WorkerSignals(QtCore.QObject):
    """ Defines the signals available from a running worker thread. """
    sigFinished = QtCore.Signal()


class AutofocusWorker(QtCore.QRunnable):
    """ Worker thread to monitor the Autofocus signal (QPD or camera) and adjust the piezo position when autofocus in ON
    The worker handles only the waiting time, and emits a signal that serves to trigger the update indicators. """
    def __init__(self, dt, *args, **kwargs):
        super(AutofocusWorker, self).__init__(*args, **kwargs)
        self.signals = WorkerSignals()
        self.frequency = dt

    @QtCore.Slot()
    def run(self):
        """ """
        sleep(self.frequency)
        self.signals.sigFinished.emit()


class CameraImageWorker(QtCore.QRunnable):
    """ Worker thread to monitor the camera IR signal and adjust the piezo position when autofocus in ON.
    The worker handles only the waiting time, and emits a signal that serves to trigger the update indicators """

    def __init__(self, *args, **kwargs):
        super(CameraImageWorker, self).__init__(*args, **kwargs)
        self.signals = WorkerSignals()

    @QtCore.Slot()
    def run(self):
        """ """
        sleep(0.2)
        self.signals.sigFinished.emit()


class FocusLogic(GenericLogic):
    """ Class to control the focus.

    Config entry for copy-paste:

    focus_logic:
        module.Class: 'focus_logic.FocusLogic'
        setup: 'RAMM'
        connect:
            piezo: 'mcl'
            autofocus: 'autofocus_logic'
    """

    # declare connectors
    piezo = Connector(interface='MotorInterface')
    autofocus = Connector(interface='AutofocusLogic')

    # Config options
    _setup = ConfigOption('setup', missing='error')

    # signals
    sigStepChanged = QtCore.Signal(float)
    sigPositionChanged = QtCore.Signal(float)
    sigPiezoInitFinished = QtCore.Signal()
    sigUpdateTimetrace = QtCore.Signal(float)
    sigPlotCalibration = QtCore.Signal(object, object, object, float)
    sigOffsetCalibration = QtCore.Signal(float)
    sigDisplayImageAndMask = QtCore.Signal(object, object, float, float)
    sigDisplayImage = QtCore.Signal(object)  # np.ndarray
    sigAutofocusError = QtCore.Signal()
    sigAutofocusStopped = QtCore.Signal()  # signal emitted when autofocus is programmatically stopped
    sigSetpointDefined = QtCore.Signal(float)
    sigDoStageMovement = QtCore.Signal(float)

    # piezo attributes
    _step = 0.01
    _init_position = ConfigOption('init_position', 10, missing='warn')
    _max_step = 0
    _axis = None

    # display element state attributes
    timetrace_enabled = False
    refresh_time = 100  # time in ms for timer interval
    live_display_enabled = False  # camera image

    # autofocus attributes
    _calibration_range = 2  # Autofocus calibration range in µm
    _slope = None
    _z0 = None
    _z_new = None
    _dt = None

    _calibrated = False
    _setpoint_defined = False
    _autofocus_lost = False

    autofocus_enabled = False


    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.threadpool = QtCore.QThreadPool()

        # uncomment if needed:
        # self.threadlock = Mutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # initialize the piezo
        self._piezo = self.piezo()
        self._axis = self._piezo._axis_label
        self._max_step = self._piezo.get_constraints()[self._axis]['max_step']
        self._min_z = self._piezo.get_constraints()[self._axis]['pos_min']
        self._max_z = self._piezo.get_constraints()[self._axis]['pos_max']
        self.init_piezo()

        # initialize the autofocus class
        self._autofocus_logic = self.autofocus()

        # signals to autofocus logic
        self.sigDoStageMovement.connect(self._autofocus_logic.do_position_correction)

        # signals from autofocus logic
        self._autofocus_logic.sigOffsetDefined.connect(self.define_autofocus_setpoint)
        self._autofocus_logic.sigStageMoved.connect(self.do_piezo_position_correction)

        # initialize the timer for the timetrace of the piezo position, it is then started when start_position_tracking is called
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)  # instead of using intervall. Repetition is then handled via the slot loop (and start_position_tracking at first)
        self.timer.timeout.connect(self.position_tracking_loop)

    def on_deactivate(self):
        """ Perform required deactivation.
        Return the piezo to the zero position
         """
        self.go_to_position(0.5)

# ==========================================================
# methods for manual focus setting (manual focus dockwidget)
# ==========================================================

    def init_piezo(self):
        """ Move piezo to initial position defined in the configuration file. """
        init_pos = self._init_position
        self.piezo_ramp(init_pos)
        sleep(0.03)  # stabilization time
        self.sigPiezoInitFinished.emit()

    def move_up(self, step):
        """ Make a relative movement in positive z direction.
        :param float step: target relative movement (positive value)
        :return None
        """
        self._piezo.move_rel({self._axis: step})
        # the wait on target function does not really work yet. so we get the precedent position
        # because the value is read too fast..
        # possible solution is to use the stabilisation time of 30 ms but this could slow down continuous movements (button pressed down on GUI or key shortcuts)
        position = self.get_position()
        # self.log.debug('moved up: {0} um. New position: {1}'.format(step, position))
        self.sigPositionChanged.emit(position)

    def move_down(self, step):
        """ Make a relative movement in negative z direction.
        :param float step: target relative movement (positive value, orientation is handled in this method)
        :return None
        """
        self._piezo.move_rel({self._axis: -step})
        position = self.get_position()
        # self.log.debug('moved down: {0} um. New position: {1}'.format(step, position))
        self.sigPositionChanged.emit(position)

    def get_position(self):
        """ Read the current piezo position.
        :return current piezo position
        """
        return self._piezo.get_pos()[self._axis]

    def abort_movement(self):
        self._piezo.abort()  # this function is not yet implemented 

    def set_step(self, step):
        """ Set the step for a piezo movement. """
        self._step = step
        # in case this function is called via console, update the GUI
        self.sigStepChanged.emit(step)

    def go_to_position(self, position):
        """ Move piezo to the target position using a ramp to avoid moving in too big steps.
        :param: float position: target position for piezo
        """
        self.piezo_ramp(position)

    def piezo_ramp(self, target_pos):
        """ Use a ramp to go to target_pos with max step as far as possible and then do a last_step <= max_step
        :param float target_pos: target position for piezo
        :return: None
        """
        constraints = self._piezo.get_constraints()
        step = constraints[self._axis]['max_step']
        position = self.get_position()  # check the return format, and reformat it in case it is needed
        while position < abs(target_pos - step) or position > abs(
                target_pos + step):  # approach in an interval of step around the target position
            if position > target_pos:
                self.move_down(step)
            else:
                self.move_up(step)
            position = self.get_position()

        last_step = target_pos - position
        if last_step > 0:
            self.move_up(last_step)
        else:
            self.move_down(-last_step)

# ==============================================================
# methods for timetrace of piezo position (timetrace dockwidget)
# ==============================================================

    def start_position_tracking(self):
        """ Slot called from gui signal sigTimetraceOn.
        """
        self.timetrace_enabled = True
        self.timer.start()

    def stop_position_tracking(self):
        """ Slot called from gui signal sigTimetraceOff.
        """
        self.timer.stop()
        self.timetrace_enabled = False

    def position_tracking_loop(self):
        """ Execute step in the data recording loop, get the current z position of the piezo.
        """
        position = self.get_position()
        self.sigUpdateTimetrace.emit(position)
        if self.timetrace_enabled:
            self.timer.start(self.refresh_time)

# ==============================================================
# live display for camera (image display dockwidget)
# ==============================================================

    def start_live_display(self):
        """ Start the camera live display. """
        self.live_display_enabled = True
        self._autofocus_logic.start_camera_live()

        worker = CameraImageWorker()
        worker.signals.sigFinished.connect(self.live_display_loop)
        self.threadpool.start(worker)

    def live_display_loop(self):
        """ Refresh the camera live image.
        """
        im = self._autofocus_logic.get_latest_image()
        if self._setup == "PALM":
            mask = self._autofocus_logic.calculate_threshold_image(im)
            x, y = self._autofocus_logic.calculate_centroid(im, mask)
            self.sigDisplayImageAndMask.emit(im, mask, x, y)
        elif self._setup == "RAMM":
            self.sigDisplayImage.emit(im)
        else:
            pass

        if self.live_display_enabled:
            worker = CameraImageWorker()
            worker.signals.sigFinished.connect(self.live_display_loop)
            self.threadpool.start(worker)

    def stop_live_display(self):
        """ Stop the camera live image. """
        self.live_display_enabled = False
        self._autofocus_logic.stop_camera_live()

# ==============================================================
# methods for autofocus
# ==============================================================

    def read_detector_signal(self):
        """ According to the method used for the autofocus, returns either the QPD signal or the centroid position
        of the IR reflection measured on the camera.
        """
        return self._autofocus_logic.read_detector_signal()
    # specify return format

    def calibrate_focus_stabilization(self):
        """ Calibrate the focus stabilization by performing a quick 2 µm ramp with the piezo and measuring the
        autofocus signal (either camera or QPD) for each position.
        """
        if self._setup == 'PALM' and not self.live_display_enabled:
            self._autofocus_logic.start_camera_live()

        z0 = self.get_position()
        dz = self._calibration_range // 2
        z = np.arange(z0 - dz, z0 + dz, 0.1)
        n_positions = len(z)
        piezo_position = np.zeros((n_positions,))
        autofocus_signal = np.zeros((n_positions,))

        # Position the piezo (the first position is taking longer to stabilize)
        self.go_to_position(z[0])
        sleep(0.5)

        # Start the calibration
        for n in range(n_positions):
            current_z = z[n]
            self.go_to_position(current_z)
            # Timer necessary to make sure the piezo has reached the position and is stable
            sleep(0.05)
            piezo_position[n] = self.get_position()
            # Read the latest QPD signal
            autofocus_signal[n] = self.read_detector_signal()

        # Calculate the slope of the calibration curve
        p = Poly.fit(piezo_position, autofocus_signal, deg=1)
        self._slope = p(1) - p(0)
        self._calibrated = True

        self.go_to_position(z0)
        self.sigPlotCalibration.emit(piezo_position, autofocus_signal, p(piezo_position), self._slope)

        if self._setup == 'PALM' and not self.live_display_enabled:
            self._autofocus_logic.stop_camera_live()

    def define_autofocus_setpoint(self):
        """ From the present piezo position, read the detector signal and keep the value as reference for the pid
        """
        setpoint = self._autofocus_logic.define_pid_setpoint()
        self._setpoint_defined = True
        self.sigSetpointDefined.emit(setpoint)

    def check_autofocus(self):
        """ Check if there is signal detected for the autofocus. Depending on the method it can be a non-zero signal
        detected by the QPD or the camera.
        """
        self._autofocus_lost = not self._autofocus_logic.autofocus_check_signal()
        if self._autofocus_lost:
            self.log.warning('autofocus lost!')
            self.sigAutofocusError.emit()

    def start_autofocus(self, stop_when_stable=False):
        """ Launch the autofocus only if the piezo was calibrated and a setpoint defined.
            A check is also performed in order to make sure there is enough signal detected by the detector.
        """
        if self._calibrated and self._setpoint_defined:

            self.check_autofocus()
            if not self._autofocus_lost:
                self.autofocus_enabled = True

                if self._setup == 'PALM' and not self.live_display_enabled:
                    self._autofocus_logic.start_camera_live()

                self._autofocus_logic.init_pid()
                self._z0 = self.get_position()
                self._z_new = self._z0  # do we need this ?
                self._dt = self._autofocus_logic._pid_frequency

                worker = AutofocusWorker(self._dt)
                worker.signals.sigFinished.connect(partial(self.run_autofocus, stop_when_stable))
                self.threadpool.start(worker)

        elif not self._calibrated:
            self.log.warning('autofocus not yet calibrated')
            self.sigAutofocusError.emit()

        elif not self._setpoint_defined:
            self.log.warning('setpoint not yet defined')
            self.sigAutofocusError.emit()

    def run_autofocus(self, stop_when_stable):
        """ Based on the pid output, the position of the piezo is corrected in real time. In order to avoid
        unnecessary movement of the piezo, the corrections are only applied when an absolute displacement >100nm is
        required.
        """
        self.check_autofocus()
        if self.autofocus_enabled and not self._autofocus_lost:

            worker = AutofocusWorker(self._dt)
            worker.signals.sigFinished.connect(partial(self.run_autofocus, stop_when_stable))
            self.threadpool.start(worker)

            if not stop_when_stable:
                pid = self._autofocus_logic.read_pid_output(False)
            else:
                pid, stable = self._autofocus_logic.read_pid_output(True)

            z = self._z0 + pid / self._slope

            dz = np.absolute(self.get_position() - z)

            if self._min_z + 1 < z < self._max_z - 1:
                if dz > 0.1:
                    self.go_to_position(z)
            else:
                self.log.warning('piezo position out of constraints')
                self.stop_autofocus()
                self.sigAutofocusError.emit()

            if stop_when_stable:
                if stable:
                    self.log.info('focus is stable')
                    self.stop_autofocus()
                    self.sigAutofocusStopped.emit()

    def stop_autofocus(self):
        """ Stop the autofocus loop
        """
        self.autofocus_enabled = False

    # autofocus methods based on camera detection
    # -------------------------------------------

    def update_threshold(self, threshold):
        self._autofocus_logic._threshold = threshold

        # this will cause an error when fpga autofocus connected . to be handled

# ========================================================
# methods available only with a 3 axis translation stage (here: autofocus_logic_fpga)
# autofocus_logic_camera contains only warning messages that these methods are not available
# ========================================================

    def calibrate_offset(self):
        """ Calibrate the offset between the sample position and a reference on the bottom of the coverslip. This method
        is inspired from the LSM-Zeiss microscope and is used when the sample (such as embryos) is interfering too much
        with the IR signal and makes the regular focus stabilization unstable.
        """
        offset = self._autofocus_logic.calibrate_offset()
        self.sigOffsetCalibration.emit(offset)

    def rescue_autofocus(self):
        """ When the autofocus signal is lost, launch a rescuing procedure by using the MS2000 translation stage. The
        z position of the stage is moved until the signal is found again.
        """
        self._autofocus_logic.rescue_autofocus()

    def do_piezo_position_correction(self):
        """ When the piezo position gets too close to the limits, the MS2000 stage moves by steps of 1 um
        while autofocus is on, so that piezo will follow back into the central range (between 25 and 50 um).
        If the piezo is close to the lower limit (<5µm for example) it is moved to 25µm. If the piezo is too
        close to the upper limit (>70µm for example), it is moved back to 50µm.
        """
        # start autofocus if not yet started (maybe not necessary because this method will only be called inside the run_autofocus)
        if not self.autofocus_enabled:
            self.start_autofocus()  # maybe add a signal to tell the gui that autofocus was programatically started
        # get the piezo position
        piezo_pos = self.get_position()
        if (piezo_pos < 25) or (piezo_pos > 50):  # or and not self._autofocus_lost
            if self._autofocus_lost:
                self.sigAutofocusError.emit()
            else:
                if piezo_pos < 25:
                    self.sigDoStageMovement.emit(1)  # check if the directions are ok
                else:
                    self.sigDoStageMovement.emit(-1)

#----------------to be completed----------------------------------
    # def start_piezo_position_correction(self, direction):
    #     """ When the piezo position gets too close to the limits, the MS2000 stage is used to move the piezo back
    #     to a standard position. If the piezo close to the lower limit (<5µm) it is moved to 25µm. If the piezo is too
    #     close to the upper limit (>70µm), it is moved back to 50µm.
    #     """
    #     self._autofocus_logic.start_piezo_position_correction(direction)

        # maybe pass current piezo position as parameter and then communicate current position via signals ..

    # def run_piezo_position_correction(self):
    #     """ Correct the piezo position by moving the MS2000 stage while the autofocus ON
    #     """
    #     self._autofocus_logic.run_piezo_position_correction()
# ---------------------------------------------------------------

    def search_focus(self):
        """ Search the IR reflection signal on a reference plane at a distance 'offset' from the current position.
        Autofocus is programatically stopped once the signal was found and is stable.
        This method can only be used when calibrations were correctly made.
        """
        if self._calibrated and self._setpoint_defined:
            offset = self._autofocus_logic._focus_offset
            self._autofocus_logic.stage_move_z(offset)
            sleep(1)  #replace by wait for idle
            self.start_autofocus(stop_when_stable=True)
            ready = self._autofocus_logic._autofocus_stable
            print(f'ready {ready}')
            while not ready:
                sleep(0.1)
                ready = self._autofocus_logic._autofocus_stable
                print(f'ready {ready}')
                autofocus_lost = self._autofocus_lost
                if autofocus_lost:
                    break
            self._autofocus_logic.stage_move_z(-offset)
        else:
            self.log.warn('Search focus can not be used. Calibration or setpoint missing.')


