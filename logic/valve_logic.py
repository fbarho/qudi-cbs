# -*- coding: utf-8 -*-
"""
Created on Thu Mars 4 2021

@author: fbarho

This module contains the logic to control the valves
"""
from qtpy import QtCore
from logic.generic_logic import GenericLogic
from core.configoption import ConfigOption
from core.connector import Connector


class ValveLogic(GenericLogic):
    """
    Class containing the logic to control the valves

    Example config for copy-paste:

    valve_logic:
        module.Class: 'valve_logic.ValveLogic'
    """
    # declare connectors
    valves = Connector(interface='ValveInterface')

    # signals
    sigPositionChanged = QtCore.Signal(str, int)

    # attributes
    # valve_names = ['Buffer 8-way Valve', 'Syringe 2-way Valve', 'RT rinsing 2-way valve']  # get this from hardware module (config) in next version
    # valve_positions = [['1', '2', '3', '4', '5', '6', '7: MerFISH Probe', '8'], ['1', '2'], ['1', '2']]  # get this from hardware module (config)

    valve_dict = {}
    valve_names = []
    max_positions = []
    valve_IDs = []

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # connector
        self._valves = self.valves()

        self.valve_dict = self._valves.get_valve_dict()
        self.valve_names = [self.valve_dict[key]['name'] for key in self.valve_dict]
        self.max_positions = [self.valve_dict[key]['number_outputs'] for key in self.valve_dict]
        self.valve_IDs = [self.valve_dict[key]['daisychain_ID'] for key in self.valve_dict]

    def on_deactivate(self):
        """ Perform required deactivation. """
        pass

    def get_valve_position(self, valve_ID):
        return self._valves.get_valve_position(valve_ID)

    def set_valve_position(self, valve_ID, position):
        self._valves.set_valve_position(valve_ID, position)
        # add here a signal to update gui when position manually changed
        self.sigPositionChanged.emit(valve_ID, position)

    def get_valve_dict(self):
        return self._valves.get_valve_dict()

    def wait_for_idle(self):
        self._valves.wait_for_idle()
