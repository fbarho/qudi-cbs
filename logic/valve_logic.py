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

    # attributes
    valve_names = ['Buffer 8-way Valve', 'Syringe 2-way Valve', 'RT rinsing 2-way valve']  # get this from hardware module (config) in next version
    valve_positions = [['1', '2', '3', '4', '5', '6', '7: MerFISH Probe', '8'], ['1', '2'], ['1', '2']]  # get this from hardware module (config)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # connector
        self._valves = self.valves()

    def on_deactivate(self):
        """ Perform required deactivation. """
        pass

    def get_valve_position(self, valve):
        pass

    def set_valve_position(self, valve, position):
        # map key valve to address using a valve dict (like the laser dict or filter dict)
        valve_dict = self.get_valve_dict()
        valve_address = valve_dict[valve]['address']
        self._valves.set_valve_position(valve_address, position)

    def get_valve_dict(self):
        return self._valves.get_valve_dict()
