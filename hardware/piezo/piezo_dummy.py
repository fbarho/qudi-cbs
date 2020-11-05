#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov  4 09:32:48 2020

@author: fbarho

This module contains the piezo dummy for the piezo interface
"""


import numpy as np
from core.module import Base
from core.configoption import ConfigOption
from interface.piezo_interface import PiezoInterface


class PiezoDummy(Base, PiezoInterface):
    """ Dummy for piezo interface

    Example config for copy-paste:

    piezo_dummy:
        module.Class: 'piezo.piezo_dummy.PiezoDummy'
        step: 0.01 # in µm
    """


    step = ConfigOption('step', 0.01) 

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        pass

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        pass

    def get_position(self):
        """ Retrieves the current position
        
        @returns: float pos: simulated position
        """
        pos = np.random.normal()
        return pos
    
    
    def set_step(self, step):
        """ sets the step entered on the GUI by the user
        
        @returns: None
        """
        self.step = step