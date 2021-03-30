# -*- coding: utf-8 -*-
"""
Extension for qudi software

This module contains a class to control the focus of the microscope objective carried by a piezo
"""
from core.connector import Connector
from core.configoption import ConfigOption
from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic
from qtpy import QtCore
from time import sleep
import numpy as np
from numpy.polynomial import Polynomial as poly
import matplotlib.pyplot as plt


class WorkerSignals(QtCore.QObject):
    """ Defines the signals available from a running worker thread """

    sigFinished = QtCore.Signal()


class AutofocusWorker(QtCore.QRunnable):
    """ Worker thread to monitor the QPD signal and adjust the piezo position when autofocus in ON
    The worker handles only the waiting time, and emits a signal that serves to trigger the update indicators """

    def __init__(self, dt, **kwargs):
        super(AutofocusWorker, self).__init__()
        self.signals = WorkerSignals()
        self.frequency = dt

    @QtCore.Slot()
    def run(self):
        """ """
        sleep(self.frequency)  # 1 second as time constant
        self.signals.sigFinished.emit()


class FocusLogic(GenericLogic):
    """
    """
    # declare connectors
    piezo = Connector(interface='MotorInterface')  # to check if the motor interface can be reused here or if we should better define a PiezoInterface
    fpga = Connector(interface='FPGAInterface') # to check _ a new interface was defined fpr FPGA connection

    # signals
    sigStepChanged = QtCore.Signal(float)
    sigPositionChanged = QtCore.Signal(float)
    sigPiezoInitFinished = QtCore.Signal()
    sigUpdateDisplay = QtCore.Signal()

    # piezo attributes
    _step = 0.01
    _init_position = ConfigOption('init_position', 0, missing='warn')
    _max_step = 0
    _axis = None
    timetrace_enabled = False

    # autofocus attributes
    _calibration_range = 2 # Autofocus calibration range in µm
    _calibrated = False
    _slope = None
    _setpoint_defined = False
    _setpoint = None
    _P_gain = ConfigOption('Proportional_gain', 0, missing='warn')
    _I_gain = ConfigOption('Integration_gain', 0, missing='warn')
    _ref_axis = ConfigOption('Autofocus_ref_axis', 'X', missing='warn')
    _run_autofocus = False
    _dt = None # in s, frequency for the autofocus update

    refresh_time = 100 # time in ms for timer interval

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

        # initialize the fpga
        self._fpga = self.fpga()

        # initialize the timer, it is then started when start_tracking is called
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)  # instead of using intervall. Repetition is then handled via the slot loop (and start_tracking at first)
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

    def qpd(self):
        """ Read the QPD signal from the FPGA. In order to make sure we are always reading from the latest piezo
            position, the method is waiting for a new count.
        """
        qpd = self._fpga.read_qpd()
        last_count = qpd[3]
        while last_count == qpd[3]:
            qpd = self._fpga.read_qpd()
            sleep(0.01)

        if self._ref_axis == 'X':
            return qpd[0]
        elif self._ref_axis == 'Y':
            return qpd[1]

    def worker_frequency(self):
        """ Update the worker frequency according to the iteration time of the fpga
        """
        qpd = self._fpga.read_qpd()
        iteration_duration = qpd[4]/1000+0.01
        return iteration_duration

    def qpd_reset(self):
        """ Reset the QPD counter
        """
        self._fpga.reset_qpd_counter()

    def define_autofocus_setpoint(self):
        """ Define the setpoint for the autofocus
        """
        self._setpoint = self.qpd()
        self._setpoint_defined = True

    def start_autofocus(self):
        """ Launch the autofocus only if the piezo was calibrated and a setpoint defined.
        """

        if self._calibrated and self._setpoint_defined:
            self._fpga.init_pid(self._P_gain, self._I_gain, self._setpoint, self._ref_axis)
            self._run_autofocus = True
            self._dt = self.worker_frequency()
            worker = AutofocusWorker(self._dt)
            worker.signals.sigFinished.connect(self.run_autofocus)
            self.threadpool.start(worker)

        elif not self._calibrated:
            self.log.warning('autofocus not yet calibrated')

        elif not self._setpoint_defined:
            self.log.warning('setpoint not yet defined')

    def run_autofocus(self):
        if self._run_autofocus:
            worker = AutofocusWorker(self._dt)
            worker.signals.sigFinished.connect(self.run_autofocus)
            self.threadpool.start(worker)
            pid = self._fpga.read_pid()
            print(pid/self._slope)

    def stop_autofocus(self):
        self._fpga.stop_pid()
        self._run_autofocus = False

    def calibrate_autofocus(self):
        """ Calibrate the autofocus.
        """
        self.qpd_reset()
        z0 = self.get_position()
        dz = self._calibration_range//2
        Z = np.arange(z0-dz, z0+dz, 0.1)
        n_positions = len(Z)
        piezo_position = np.zeros((n_positions,))
        qpd_signal = np.zeros((n_positions,))

        for n in range(n_positions):
            z = Z[n]
            self.go_to_position(z)
            # Timer necessary to make sure the piezo reached the position and is stable
            sleep(0.03)
            piezo_position[n] = self.get_position()
            # Read the latest QPD signal
            qpd_signal[n] = self.qpd()

        # Calculate the slope of the calibration curve
        p = poly.fit(piezo_position, qpd_signal, deg=1)
        self._slope = p(1)-p(0)
        self._calibrated = True

        fig, ax = plt.subplots()
        ax.plot(piezo_position, qpd_signal, 'bo')
        ax.plot(piezo_position, p(piezo_position), 'r-')
        ax.set(xlabel='z (um)', ylabel='QPD signal (V)')
        plt.show()