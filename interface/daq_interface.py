#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Nov  6 13:56:15 2020

@author: fbarho
"""


from core.interface import abstract_interface_method
from core.meta import InterfaceMetaclass


class DaqInterface(metaclass=InterfaceMetaclass):
    """ This interface contains the specific functions only for DAQ (DAQ for laser control also inherits LaserControlInterface)
    """
    ### to be completed
