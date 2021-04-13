#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov  3 10:27:15 2020

@author: fbarho


A module to control the piezo.

The piezo carries the microscope objective and is used to manually set the focus and for autofocus procedure

"""

from core.connector import Connector
from core.configoption import ConfigOption
from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic
from qtpy import QtCore

import pyqtgraph as pg
import numpy as np
from time import sleep


class AutofocusLogic(GenericLogic):
    """ Controls the piezo and the focus and autofocus procedures
    
    Config pour copy-paste
    
        autofocus_logic:
        module.Class: 'autofocus_logic.AutofocusLogic'
        connect: 
            piezo: 'piezo_dummy'
                
            
    
    """

    # declare connectors
    camera = Connector(interface='CameraInterface')
    fpga = Connector(interface='FPGAInterface')  # to check _ a new interface was defined for FPGA connection

    # declare the system used for the experiment
    _system = ConfigOption('System', missing='error')

    # autofocus attributes
    _autofocus_signal = None
    _ref_axis = ConfigOption('Autofocus_ref_axis', 'X', missing='warn')


    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        #self.threadlock = Mutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # initialize the fpga
        self._fpga = self.fpga()

        # initialize the camera
        self._camera = self.camera()

    def on_deactivate(self):
        """ Required deactivation.
        """
        pass
        
    def read_autofocus_signal(self):

        if self._system == 'RAMM':
            self._autofocus_signal = self.qpd()

        return self._autofocus_signal

    def qpd(self, *args):
        """ Read the QPD signal from the FPGA. When no argument is specified, the signal is read from X/Y positions. In
        order to make sure we are always reading from the latest piezo position, the method is waiting for a new count.
        If the argument 'sum' is specified, the SUM signal is read without waiting for the latest iteration.
        """
        qpd = self._fpga.read_qpd()

        if not args:
            last_count = qpd[3]
            while last_count == qpd[3]:
                qpd = self._fpga.read_qpd()
                sleep(0.01)

            if self._ref_axis == 'X':
                return qpd[0]
            elif self._ref_axis == 'Y':
                return qpd[1]
        else:
            if args[0] == "sum":
                return qpd[2]