#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 30 11:09:20 2020

@author: fbarho


A module to control the DAQ analog output. 

The DAQ is used here to control the OTF to select the laser wavelength


"""

from core.connector import Connector
#from core.configoption import ConfigOption
from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic
from qtpy import QtCore


class DAQaoLogic(GenericLogic):
    """ Controls the DAQ analog output.
    
    """

    # declare connectors
    daq = Connector(interface='DaqInterface')

    # signals
    sigIntensityChanged = QtCore.Signal() # if intensity dict is changed programatically, this updates the GUI
    
    # private attributes
    _intensity_dict = {}
    _laser_dict = {}


    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # this might be necessary..
        self.threadlock = Mutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._daq = self.daq()

        self.enabled = False # attribute to handle the on-off switching of the laser-on button

        self._laser_dict = self.get_laser_dict()
        self._intensity_dict = self.init_intensity_dict(0)

    def on_deactivate(self):
        """ Perform required deactivation. """
        pass

    def get_laser_dict(self):
        """ Retrieve the dictionary containing wavelength, channel, and voltage range from the hardware.

        exemplary entry: {'laser1': {'label': 'laser1', 'wavelength': '405 nm', 'channel': '/Dev1/AO2', 'voltage_range': [0, 10]}

        returns: dict
        """
        return self._daq.get_dict()

    def init_intensity_dict(self, value=0):
        """ creates a dictionary with the same keys as the laser dict and set an initial value for the output voltage

        example: {'laser1': 0, 'laser2': 0, 'laser3': 0, 'laser4': 0}

        returns: dict: intensity_dict
        """
        intensity_dict = {}
        for key in self._laser_dict:
            intensity_dict[key] = value

        return intensity_dict

    def reset_intensity_dict(self):
        """ resets all values of the intensity_dict to zero

        """
        # function is called from filterwheel logic before setting a new filter
        for key in self._intensity_dict:
            self._intensity_dict[key] = 0
        self.sigIntensityChanged.emit()

    def apply_voltage(self):
        self.enabled = True
        for key in self._laser_dict:
            self._daq.apply_voltage(self._intensity_dict[key] * self._laser_dict[key]['ao_voltage_range'][1] / 100, self._laser_dict[key]['channel'])
            # conversion factor: user indicates values in percent of max voltage

        # does the delay due to iteration matter ? (laser 4 switched on slightly after laser 1 ? ..)

    def voltage_off(self):
        self.enabled = False
        for key in self._laser_dict:
            self._daq.apply_voltage(0.0, self._laser_dict[key]['channel'])
        # it could be useful to reset also the intensity dict .. to keep in mind
      

    @QtCore.Slot(str, int) # should the decorator be removed when this function is called in a task ???
    def update_intensity_dict(self, key, value):
        self._intensity_dict[key] = value
        # if laser is already on, the new value must be written to the daq output
        if self.enabled:
            self.apply_voltage()




