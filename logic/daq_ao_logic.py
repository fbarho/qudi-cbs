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
    #daq = Connector(interface='DAQInterface')


 
    
    
    # private attributes
    



    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.threadlock = Mutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        #self._daq = self.daq()
        
        self.enabled = False # attribute to handle the on-off switching 


    def on_deactivate(self):
        """ Perform required deactivation. """
        pass

    def apply_voltage(self): #voltage, channel
        
        self.enabled = True
        #self._daq.apply_voltage(voltage, channel)
    
    def voltage_off(self): # channel
        
        self.enabled = False
        #self._daq.apply_voltage(0.0, channel)



 




