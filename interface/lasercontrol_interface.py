#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb 10 2021

@author: fbarho
"""

from core.interface import abstract_interface_method
from core.meta import InterfaceMetaclass


class LaserControlInterface(metaclass=InterfaceMetaclass):
    """ This interface contains the common part for laser control by a DAQ or by a FPGA

    formerly named DaqInterface
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
