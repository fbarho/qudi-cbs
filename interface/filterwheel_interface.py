#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 17 09:04:06 2020

@author: fbarho
"""

from core.interface import abstract_interface_method
from core.meta import InterfaceMetaclass




class FilterwheelInterface(metaclass=InterfaceMetaclass):
    """ This interface contains the necessary functions to be implemented for a filterwheel
    """


    @abstract_interface_method
    def get_position(self):
        """ Get the current position """
        pass

    @abstract_interface_method
    def set_position(self, value):
        """ Set the position to a given value
        """
        pass