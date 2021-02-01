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

class FocusLogic(GenericLogic):
    """
    """
    # declare connectors
    piezo = Connector(interface='MotorInterface')  # to check if the motor interface can be reused here or if we should better define a PiezoInterface

    # signals
    sigStepChanged = QtCore.Signal(float)
    sigPositionChanged = QtCore.Signal(float)
    sigPiezoInitFinished = QtCore.Signal()
    sigUpdateDisplay = QtCore.Signal()

    # attributes
    _step = 0.01
    _init_position = ConfigOption('init_position', 20, missing='warn')
    _max_step = 0
    _axis = None
    timetrace_enabled = False


    refresh_time = 100 # time in ms for timer interval

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # uncomment if needed:
        # self.threadlock = Mutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._piezo = self.piezo()
        self._axis = self._piezo._axis_label
        self._max_step = self._piezo.get_constraints()[self._axis]['max_step']

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

        # use a ramp to go to the init_pos with max step
        constraints = self._piezo.get_constraints()
        step = constraints[self._axis]['max_step']
        position = self.get_position()  # check the return format, and reformat it in case it is needed
        while position < abs(init_pos - step) or position > abs(init_pos + step):  # approach in an interval of step around the target position
            if position > init_pos:
                self.move_down(step)
            else:
                self.move_up(step)
            position = self.get_position()

        last_step = init_pos - position
        if last_step > 0:
            self.move_up(last_step)
        else:
            self.move_down(-last_step)
        self.sigPiezoInitFinished.emit()

    def go_to_position(self, position):
        self._piezo.move_abs({self._axis: position})
        # to improve ! better implement a ramp to avoid making to rapid movements # move the ramp used in init piezo in a
        # dedicated function and call it for init piezo and also for go to position

    def run_autofocus(self):
        self.log.info('autofocus not yet available')

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


