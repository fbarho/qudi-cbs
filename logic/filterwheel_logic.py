#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 17 09:07:59 2020

@author: fbarho

This module contains the logic to control a filter wheel and provides a security on the laser selection depending on
the mounted filter. """

from core.connector import Connector
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
    sigNewFilterSetting = QtCore.Signal(int)  # if position changed using the iPython console, use this signal to update GUI
    sigDeactivateLaserControl = QtCore.Signal()

    filter_dict = {}

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self.get_filter_dict()

    def on_deactivate(self):
        """ Perform required deactivation. """
        pass

    @QtCore.Slot(int)
    def set_position(self, position):
        """ Checks if the filterwheel can move (only if lasers are off), resets the intensity values of all lasers to 0
        to avoid having a laser line which may be forbidden with the newly set filter and changes position if possible.

        @params: position: new filter wheel position

        @returns: None
        """
        if not self.lasercontrol().enabled:  # do not allow changing filter while lasers are on # Combobox on gui is also disabled but this here is an additional security to prevent setting filter via iPython console
            self.lasercontrol().reset_intensity_dict()  # set all values to 0 before changing the filter
            err = self.wheel().set_position(position)
            if err == 0:
                self.log.info('Set filter {}'.format(position))
                self.sigNewFilterSetting.emit(position)
        else:
            self.log.warn('Laser is on. Can not change filter')

    def get_position(self):
        """ Get the current position from the hardware """
        pos = self.wheel().get_position()
        return pos

    def get_filter_dict(self):
        """ Retrieves a dictionary specified in the configuration of the connected filterwheel with the following entries:
                    {'filter1': {'label': 'filter1', 'name': str(name), 'position': 1, 'lasers': bool list},
                     'filter2': {'label': 'filter2', 'name': str(name), 'position': 2, 'lasers': bool list},
                    ...
                    }
        """
        filter_dict = self.wheel().get_filter_dict()
        self.filter_dict = filter_dict
        return filter_dict
