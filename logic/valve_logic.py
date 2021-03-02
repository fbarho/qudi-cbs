# -*- coding: utf-8 -*-
"""
Created on Thu Mars 4 2021

@author: fbarho

This module contains the logic to control the valves
"""
from qtpy import QtCore
from logic.generic_logic import GenericLogic
from core.configoption import ConfigOption


class ValveLogic(GenericLogic):
    """
    Class containing the logic to control the valves

    Example config for copy-paste:

    valve_logic:
        module.Class: 'valve_logic.ValveLogic'
    """

    # signals

    # attributes

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        pass

    def on_deactivate(self):
        """ Perform required deactivation. """
        pass
