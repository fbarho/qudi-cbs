# -*- coding: utf-8 -*-
"""
Created on Thu Mars 4 2021

@author: fbarho

This module contains the logic to control the valves
"""
from qtpy import QtCore
from logic.generic_logic import GenericLogic
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
    valve_dict = {}
    valve_names = []
    max_positions = []
    valve_IDs = []
    valve_positions = []  # a list of lists containing customised entries for the GUI Comboboxes, optionally given in hardware's config

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
        self.valve_positions = self._valves._valve_positions

    def on_deactivate(self):
        """ Perform required deactivation. """
        pass

    def get_valve_position(self, valve_id):
        """ Read the valve position of the specified valve.
        :param str valve_id: identifier of the valve, such as 'a', 'b', ..
        :return int position
        """
        return self._valves.get_valve_position(valve_id)

    def set_valve_position(self, valve_id, position):
        """ Set the position of the specified valve.
        :param str valve_id: identifier of the valve, such as 'a', 'b', ..
        :param int position: target position for the valve
        :return None
        """
        self._valves.set_valve_position(valve_id, position)
        self.sigPositionChanged.emit(valve_id, position)  # signal to update gui when position changed by direct call to this function

    def get_valve_dict(self):
        """ Get the dictionary specified in the hardware modules config entry, containing daisy chain id, valve name
        and number of outputs.
        :return dict valve_dict
        """
        return self._valves.get_valve_dict()

    def wait_for_idle(self):
        """ Wait for valves to be set to position.
        """
        self._valves.wait_for_idle()
