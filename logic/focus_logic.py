# -*- coding: utf-8 -*-
"""
Extension for qudi software

This module contains a class to control the focus of the microscope objective carried by a piezo
"""
from core.connector import Connector
from core.configoption import ConfigOption
# from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic
from qtpy import QtCore
from time import sleep
import numpy as np
from numpy.polynomial import Polynomial as Poly


# import matplotlib.pyplot as plt


class WorkerSignals(QtCore.QObject):
    """ Defines the signals available from a running worker thread """

    sigFinished = QtCore.Signal()


class QPDAutofocusWorker(QtCore.QRunnable):
    """ Worker thread to monitor the QPD signal and adjust the piezo position when autofocus in ON
    The worker handles only the waiting time, and emits a signal that serves to trigger the update indicators """

    def __init__(self, dt, *args, **kwargs):
        super(QPDAutofocusWorker, self).__init__()
        self.signals = WorkerSignals()
        self.frequency = dt

    @QtCore.Slot()
    def run(self):
        """ """
        sleep(self.frequency)  # 1 second as time constant
        self.signals.sigFinished.emit()


class CameraAutofocusWorker(QtCore.QRunnable):
    """ Worker thread to monitor the camera IR signal and adjust the piezo position when autofocus in ON
    The worker handles only the waiting time, and emits a signal that serves to trigger the update indicators """

    def __init__(self, *args, **kwargs):
        super(CameraAutofocusWorker, self).__init__()
        self.signals = WorkerSignals()

    @QtCore.Slot()
    def run(self):
        """ """
        sleep(0.2)  # 1 second as time constant
        self.signals.sigFinished.emit()


class StageAutofocusWorker(QtCore.QRunnable):
    """ Worker thread to control the stage position and adjust the piezo position when autofocus in ON
    The worker handles only the waiting time, and emits a signal that serves to trigger the update indicators """

    def __init__(self, *args, **kwargs):
        super(StageAutofocusWorker, self).__init__()
        self.signals = WorkerSignals()

    @QtCore.Slot()
    def run(self):
        """ """
        sleep(0.5)  # 1 second as time constant
        self.signals.sigFinished.emit()


class FocusLogic(GenericLogic):
    """
    """
    # declare connectors
    piezo = Connector(
        interface='MotorInterface')  # to check if the motor interface can be reused here or if we should better define a PiezoInterface
    stage = Connector(interface='MotorInterface')
    autofocus = Connector(interface='AutofocusLogic')

    # define the setup we are working on
    _setup = ConfigOption('Setup', missing='error')

    # signals
    sigStepChanged = QtCore.Signal(float)
    sigPositionChanged = QtCore.Signal(float)
    sigPiezoInitFinished = QtCore.Signal()
    sigUpdateDisplay = QtCore.Signal()
    sigPlotCalibration = QtCore.Signal(object, object, object, float)
    sigDisplayImageAndMask = QtCore.Signal(object, object, float, float)
    sigDisplayImage = QtCore.Signal(object)
    sigAutofocusLost = QtCore.Signal()

    # piezo attributes
    _step = 0.01
    _init_position = ConfigOption('init_position', 0, missing='warn')
    _max_step = 0
    _axis = None
    timetrace_enabled = False

    # camera attributes
    _live_display = False

    # stage attributes
    _pos_dict = dict()

    # autofocus attributes
    _calibration_range = 2  # Autofocus calibration range in µm
    _slope = None
    _z0 = None
    _z_new = None
    _z_last = None
    _dt = None

    _calibrated = False
    _setpoint_defined = False
    _run_autofocus = False
    _autofocus_lost = False
    _enable_autofocus_rescue = False

    refresh_time = 100  # time in ms for timer interval

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
        self.go_to_position(self._init_position)

        # initialize the autofocus class
        self._autofocus_logic = self.autofocus()

        # initialize the ms2000 stage
        self._stage = self.stage()

        # allow the rescue option when working with then RAMM setup
        if self._setup == "RAMM":
            self._enable_autofocus_rescue = True

        # initialize the timer, it is then started when start_tracking is called
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(
            True)  # instead of using intervall. Repetition is then handled via the slot loop (and start_tracking at first)
        self.timer.timeout.connect(self.loop)

    def on_deactivate(self):
        """ Perform required deactivation. """
        pass

    def move_up(self, step):
        self._piezo.move_rel({self._axis: step})
        # self._piezo.wait_for_idle()
        # the wait on target function does not really work yet. so we get the precedent position
        # because the value is read too fast.. 
        position = self.get_position()
        # self.log.debug('moved up: {0} um. New position: {1}'.format(step, position))
        self.sigPositionChanged.emit(position)

    def move_down(self, step):
        self._piezo.move_rel({self._axis: -step})
        # self._piezo.wait_for_idle()
        position = self.get_position()
        # self.log.debug('moved down: {0} um. New position: {1}'.format(step, position))
        self.sigPositionChanged.emit(position)

    def get_position(self):
        return self._piezo.get_pos()[self._axis]

    def abort_movement(self):
        self._piezo.abort()  # this function is not yet implemented 

    def set_step(self, step):
        self._step = step
        # in case this function is called via console, update the GUI
        self.sigStepChanged.emit(step)

    def init_piezo(self):
        init_pos = self._init_position
        self.piezo_ramp(init_pos)

        # # use a ramp to go to the init_pos with max step
        # constraints = self._piezo.get_constraints()
        # step = constraints[self._axis]['max_step']
        # position = self.get_position()  # check the return format, and reformat it in case it is needed
        # while position < abs(init_pos - step) or position > abs(init_pos + step):  # approach in an interval of step around the target position
        #     if position > init_pos:
        #         self.move_down(step)
        #     else:
        #         self.move_up(step)
        #     position = self.get_position()
        #
        # last_step = init_pos - position
        # if last_step > 0:
        #     self.move_up(last_step)
        # else:
        #     self.move_down(-last_step)
        self.sigPiezoInitFinished.emit()

    def go_to_position(self, position):
        # self._piezo.move_abs({self._axis: position})
        self.piezo_ramp(position)
        # to improve ! better implement a ramp to avoid making to rapid movements # move the ramp used in init piezo in a
        # dedicated function and call it for init piezo and also for go to position

    def piezo_ramp(self, target_pos):
        # use a ramp to go to target_pos with max step as far as possible and then do a last_step <= max_step
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

    # methods for timetrace
    def start_tracking(self):
        """ slot called from gui signal sigTimetraceOn.
        """
        self.timetrace_enabled = True
        self.timer.start()

    def stop_tracking(self):
        """ slot called from gui signal sigTimetraceOff
        """
        self.timer.stop()
        self.timetrace_enabled = False

    def loop(self):
        """ Execute step in the data recording loop, get the current z position
        """
        self._position = self.get_position()  # to be replaced with get physical data
        self.sigUpdateDisplay.emit()
        if self.timetrace_enabled:
            self.timer.start(self.refresh_time)

    # methods for autofocus
    # ----------------------

    def define_autofocus_setpoint(self):
        """ Define the setpoint for the autofocus
        """
        self._setpoint = self._autofocus_logic.read_detector_signal()
        self._setpoint_defined = True

    def check_autofocus(self):
        """ Check there is signal detected for the autofocus. Depending on the method it can be a non-zero signal
        detected by the QPD or the camera.
        """
        self._autofocus_lost = self._autofocus_logic.autofocus_check_signal()
        if self._autofocus_lost:
            self.log.warning('autofocus lost!')
            self.sigAutofocusLost.emit()

    def read_detector_signal(self):
        """ According to the method used for the autofocus, returns either the QPD signal or the centroid position
        of the IR reflection measured on the camera.
        """
        return self._autofocus_logic.read_detector_signal()

    def calibrate_autofocus(self):
        """ Calibrate the autofocus.
        """
        if self._setup == 'PALM' and not self._live_display:
            self._autofocus_logic.start_camera_live()

        z0 = self.get_position()
        dz = self._calibration_range // 2
        Z = np.arange(z0 - dz, z0 + dz, 0.1)
        n_positions = len(Z)
        piezo_position = np.zeros((n_positions,))
        autofocus_signal = np.zeros((n_positions,))

        # Position the piezo (the first position is taking longer to stabilize)
        self.go_to_position(Z[0])
        sleep(0.5)

        # Start the calibration
        for n in range(n_positions):
            z = Z[n]
            self.go_to_position(z)
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

        if self._setup == 'PALM' and not self._live_display:
            self._autofocus_logic.stop_camera()

    def define_autofocus_setpoint(self):
        """ From the present piezo position, read the detector signal and keep the value as reference for the pid
        """
        self._autofocus_logic.pid_setpoint()
        self._setpoint_defined = True

    def start_autofocus(self):
        """ Launch the autofocus only if the piezo was calibrated and a setpoint defined.
            A check is also performed in order to make sure there is enough signal detected by the detector.
        """
        self.check_autofocus()
        if self._calibrated and self._setpoint_defined and not self._autofocus_lost:

            if self._setup == 'PALM' and not self._live_display:
                self._autofocus_logic.start_camera_live()

            self._autofocus_logic.init_pid()
            self._run_autofocus = True
            self._z0 = self.get_position()
            self._z_new = self._z0
            self._dt = self._autofocus_logic._pid_frequency

            worker = QPDAutofocusWorker(self._dt)
            worker.signals.sigFinished.connect(self.run_autofocus)
            self.threadpool.start(worker)

        elif not self._calibrated:
            self.log.warning('autofocus not yet calibrated')

        elif not self._setpoint_defined:
            self.log.warning('setpoint not yet defined')

    def run_autofocus(self):
        """ Based on the pid output, the position of the piezo is corrected in real time. In order to avoid
        unnecessary movement of the piezo, the corrections are only applied when an absolute displacement >100nm is
        required.
        """
        self.check_autofocus()
        if self._run_autofocus and not self._autofocus_lost:

            worker = QPDAutofocusWorker(self._dt)
            worker.signals.sigFinished.connect(self.run_autofocus)
            self.threadpool.start(worker)

            # pid = self.pid(self.read_detector_signal())
            pid = self._autofocus_logic.read_pid_output()
            z = self._z0 + pid / self._slope
            # z = np.around(z, 3)

            self._z_last = self._z_new
            self._z_new = z
            dz = np.absolute(self.get_position() - z)

            if self._min_z + 1 < z < self._max_z - 1:
                if dz > 0.1:
                    self.go_to_position(z)
            else:
                self.log.warning('piezo position out of constraints')
                self.stop_autofocus()

    def stop_autofocus(self):
        """ Stop the autofocus loop
        """
        self._run_autofocus = False

    def rescue_autofocus(self):
        """ When the autofocus signal is lost, launch a rescuing procedure by using the MS2000 translation stage. The
        z position of the stage is moved until the piezo signal is found again.
        """
        z_range = 20
        while self._autofocus_lost and z_range <= 40:

            axis_label = ('x', 'y', 'z')
            positions = (0, 0, -z_range // 2)
            pos_dict = dict([*zip(axis_label, positions)])
            self._stage.move_rel(pos_dict)

            for z in range(z_range):
                positions = (0, 0, 1)
                pos_dict = dict([*zip(axis_label, positions)])
                self._stage.move_rel(pos_dict)

                self._autofocus_lost = self._autofocus_logic.autofocus_check_signal()
                if not self._autofocus_lost:
                    print("autofocus signal found!")
                    break

            if self._autofocus_lost:
                positions = (0, 0, -z_range // 2)
                pos_dict = dict([*zip(axis_label, positions)])
                self._stage.move_rel(pos_dict)
                z_range = z_range + 10

    def start_piezo_position_correction(self, direction):
        """ When the piezo position gets too close to the limits, the MS2000 stage is used to move the piezo back
        to a standard position. If the piezo close to the lower limit (<5µm) it is moved to 25µm. If the piezo is too
        close to the upper limit (>70µm), it is moved back to 50µm.
        """
        axis_label = ('x', 'y', 'z')

        if direction == "up":
            positions = (0, 0, 1)
        elif direction == "down":
            positions = (0, 0, -1)

        self._pos_dict = dict([*zip(axis_label, positions)])
        if not self._run_autofocus:
            self.start_autofocus()

        stage_worker = StageAutofocusWorker()
        stage_worker.signals.sigFinished.connect(self.run_piezo_position_correction)
        self.threadpool.start(stage_worker)

    def run_piezo_position_correction(self):
        """ Correct the piezo position by moving the MS2000 stage while the autofocus ON
        """
        z = self.get_position()
        if not self._autofocus_lost and (z < 25 or z > 50):
            self._stage.move_rel(self._pos_dict)

            stage_worker = StageAutofocusWorker()
            stage_worker.signals.sigFinished.connect(self.run_piezo_position_correction)
            self.threadpool.start(stage_worker)


    # autofocus methods based on camera detection
    # -------------------------------------------

    def update_threshold(self, threshold):
        self._autofocus_logic._threshold = threshold

    def start_live_display(self):

        self._live_display = True
        self._autofocus_logic.start_camera_live()

        worker = CameraAutofocusWorker()
        worker.signals.sigFinished.connect(self.live_display)
        self.threadpool.start(worker)

    def live_display(self):

        im = self._autofocus_logic.get_latest_image()
        if self._setup == "PALM":
            mask = self._autofocus_logic.calculate_threshold_image(im)
            x, y = self._autofocus_logic.calculate_centroid(im, mask)
            self.sigDisplayImageAndMask.emit(im, mask, x, y)
        elif self._setup == "RAMM":
            self.sigDisplayImage.emit(im)

        if self._live_display:
            worker = CameraAutofocusWorker()
            worker.signals.sigFinished.connect(self.live_display)
            self.threadpool.start(worker)

    def stop_live_display(self):
        self._live_display = False
        self._autofocus_logic.stop_camera()
