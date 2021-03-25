#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed March 24, 2021

@author: fbarho

A general module to control any DAQ functionality (analog input / output, digital input / output)
except the laser control which is handled by a dedicated module (lasercontrol_logic)

Used for the DAQ on RAMM setup. This module may be reorganized later into individual parts for different functionality.
"""

from core.connector import Connector
from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic
from qtpy import QtCore


class DAQaoLogic(GenericLogic):
    """ Controls the DAQ analog output and allows to set a digital output line for triggering
    """

    # declare connectors
    daq = Connector(interface='Base')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        # activate if necessary
        # self.threadlock = Mutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._daq = self.daq()

    def on_deactivate(self):
        """ Perform required deactivation. """
        pass


    def read_piezo(self):
        """
        """
        return self._daq.read_piezo()

    def move_piezo(self, pos, autostart=True, timeout=10):
        """
        """
        self._daq.move_piezo(pos, autostart=True, timeout=10)

    def write_to_do_channel(self, num_samp, digital_write, channel):
        """ use the digital output as trigger """
        self._daq.write_to_do_channel(num_samp, digital_write, channel)

    def read_do_channel(self, num_samp, channel):
        return self._daq.read_do_channel(num_samp, channel)







