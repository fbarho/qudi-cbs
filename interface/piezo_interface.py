#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov  4 08:48:33 2020

@author: fbarho

This module contains the interface for the piezo.

"""
from core.interface import abstract_interface_method
from core.meta import InterfaceMetaclass


class PiezoInterface(metaclass=InterfaceMetaclass):
    """ This interface is used to control the piezo. 
    
    All methods that must be implemented by the piezo hardware modules are initialized here.
    """

    @abstract_interface_method
    def get_position(self):
        """ Returns the current position of the piezo

        @returns: float position
        """
        pass



