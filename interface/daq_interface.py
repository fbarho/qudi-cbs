#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Nov  6 13:56:15 2020

@author: fbarho
"""


from core.interface import abstract_interface_method
from core.meta import InterfaceMetaclass


class DAQInterface(metaclass=InterfaceMetaclass):
    """ This interface can be used to access the analog output of a DAQ
    
    it might be extended to other types of DAQ channels .. counter for example 
    """
    
    @abstract_interface_method
    def set_voltage(self, channel, voltage):
        """ 
        """
        pass
    