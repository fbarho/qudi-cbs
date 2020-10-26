# -*- coding: utf-8 -*-
"""
Created on Mon Oct 26 14:33:09 2020

@author: barho


This file contains a class for the ASI MS2000 translation stage. 

It is an extension to the hardware code base of Qudi software 
obtained from <https://github.com/Ulm-IQO/qudi/> 
"""

from core.module import Base
from interface.motor_interface import MotorInterface
from core.configoption import ConfigOption


class MS2000(Base, MotorInterface):
    """ Class representing the ASI MS 2000 xy translation stage.
    
    Example config for copy-paste:
        
    ms2000:
        module.Class: 'motor.motor_asi_ms2000.MS2000'
        com_port: 'COM4'
    """
    
    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
    
    def on_activate(self):
        pass
    
    def on_deactivate(self):
        pass
    
    def get_constraints(self):
        pass
    
    def move_rel(self):
        pass
    
    def move_abs(self):
        pass
    
    def abort(self):
        pass
    
    def get_pos(self):
        pass
    
    def get_status(self):
        pass
    
    def calibrate(self):
        pass
    
    def get_velocity(self):
        pass
    
    def set_velocity(self):
        pass 
    
    
    
    

    


