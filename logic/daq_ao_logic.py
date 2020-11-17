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
    daq = Connector(interface='DAQInterface')


 
    
    
    # private attributes
    #_intensity_value = 0 # for testing do as if there is only one laser
    _intensity_dict = {}
    _channel_dict = {} # see how constraints dicts are passed to logic modules.. this should be similar here. 



    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.threadlock = Mutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        #self._daq = self.daq()
        
        self.enabled = False # attribute to handle the on-off switching of the laser-on button


    def on_deactivate(self):
        """ Perform required deactivation. """
        pass

    
    def apply_voltage(self): #channel, voltage
        
        self.enabled = True
        self._daq.set_voltage('/Dev1/AO0', self._intensity_dict['Laser1'])
        ## something like [self._daq.set_voltage(self._channel_dict[laser], self._intensity_dict[laser]) for laser in self._intensity_dict]
        # have to link laser names to channels in config and create a dictionary from this ### to be fixed !!!!!!!!!
        # does the delay due to iteration matter ? (laser 4 switched on slightly after laser 1 ..)
    
    def voltage_off(self): # channel
        
        self.enabled = False
        #self._daq.apply_voltage(0.0, channel)
      
#    @QtCore.Slot(int)  
#    def update_intensity_value(self, value):
#        self._intensity_value = value


    @QtCore.Slot(str, int)  
    def update_intensity_dict(self, key, value):
        self._intensity_dict[key] = value


 ## check when intensity should be used and when it is converted into voltage .. the user indicates intensity ??? or a percentage of max voltage ????
 




