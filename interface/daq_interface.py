#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Nov  6 13:56:15 2020

@author: fbarho
"""


from core.interface import abstract_interface_method
from core.meta import InterfaceMetaclass


class DaqInterface(metaclass=InterfaceMetaclass):
    """ This interface can be used to access the analog output of a DAQ
    
    it might be extended to other types of DAQ channels .. counter for example 
    """


    @abstract_interface_method
    def get_dict(self):
        """ Retrieves the channel name and the corresponding voltage range for each analog output and associates it to
        the laser wavelength which is controlled by this channel.

        @returns: laser_dict
        """
        pass
    
    @abstract_interface_method
    def apply_voltage(self, voltage, channel):
        """ 
        """
        pass
    