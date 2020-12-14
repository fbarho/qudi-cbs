#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 17 09:07:59 2020

@author: fbarho


This module contains the logic to control a filter wheel and provides a security on the laser selection depending on the mounted filter.
"""


from core.connector import Connector
#from core.configoption import ConfigOption
#from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic
from qtpy import QtCore




class FilterwheelLogic(GenericLogic):
    """
    Class for the control of a motorized filterwheel.
    """

    # declare connectors
    wheel = Connector(interface='FilterwheelInterface')
    lasercontrol = Connector(interface='DAQaoLogic')
    
    # signals
    sigNewFilterSetting = QtCore.Signal(int) # if position changed using the iPython console, use this signal to update GUI
    sigDeactivateLaserControl = QtCore.Signal()

    filter_dict = {}
    

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        #self.filter_dict = self.wheel().get_filter_dict()
        self.get_filter_dict()

    def on_deactivate(self):
        """ Perform required deactivation. """
        pass


    @QtCore.Slot(int)
    def set_position(self, position):
        if not self.lasercontrol().enabled: # do not allow changing filter while lasers are on # Combobox on gui is also disabled but this here is an additional security to prevent setting filter via iPython console
            self.lasercontrol().reset_intensity_dict()  # set all values to 0 before changing the filter
            err = self.wheel().set_position(position)
            if err == 0:
                self.log.info('Set filter {}'.format(position))
                self.sigNewFilterSetting.emit(position)
        else:
            self.log.warn('Laser is on. Can not change filter')


    def get_position(self):
        pos = self.wheel().get_position()
        return pos

    def get_filter_dict(self):
        dict = self.wheel().get_filter_dict()
        self.filter_dict = dict
        return dict

    
    
    
    