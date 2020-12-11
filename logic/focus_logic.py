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

class FocusLogic(GenericLogic): # should this class be the FocusLogic or PiezoLogic ?
    """
    """

    # declare connectors
    piezo = Connector(interface='MotorInterface')  # to check if the motor interface can be reused here or if we should better define a PiezoInterface

    # signals
    sigStepChanged = QtCore.Signal(float)
    sigPositionChanged = QtCore.Signal(float)

    # attributes
    _step = 0.01

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # uncomment if needed:
        # self.threadlock = Mutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._piezo = self.piezo()



    def on_deactivate(self):
        """ Perform required deactivation. """
        pass

    def move_up(self):
        self._piezo.move_rel({'z': self._step})
        position = self.get_position()
        self.log.info('moved up: {0} um. New position: {1}'.format(self._step, position))
        self.sigPositionChanged.emit(position)

    def move_down(self):
        self._piezo.move_rel({'z': -self._step})
        position = self.get_position()
        self.log.info('moved down: {0} um. New position: {1}'.format(self._step, position))
        self.sigPositionChanged.emit(position)

    def get_position(self):
        return self._piezo.get_pos()['z']

    def abort_movement(self):
        self._piezo.abort()

    def set_step(self, step):
        self._step = step
        # in case this function is called via console, update the GUI
        self.sigStepChanged.emit(step)


