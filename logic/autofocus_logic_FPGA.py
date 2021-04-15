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
    """ This logic connect to the instruments necessary for the autofocus method based on the FPGA + QPD. This logic
    is directly connected to the focus_logic controlling the piezo position.
    
    autofocus_logic:
        module.Class: 'autofocus_logic.AutofocusLogic'
        Autofocus_ref_axis : 'X' # 'Y'
        connect:
            camera : 'thorlabs_camera'
            fpga: 'nifpga'
    """

    # declare connectors
    fpga = Connector(interface='FPGAInterface')  # to check _ a new interface was defined for FPGA connection
    camera = Connector(interface='CameraInterface')

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
        self._camera = self.camera()

    def on_deactivate(self):
        """ Required deactivation.
        """
        pass
        
    def read_autofocus_signal(self):
        """ General function returning the reference signal for the autofocus correction. In the case of the
        method using a FPGA, it returns the QPD signal measured along the reference axis.
        """
        return self.qpd()

    def set_point(self):
        """ Define the autofocus reference set_point
        """
        return self.qpd()

    def autofocus_check_signal(self):
        """ Check that the intensity detected by the QPD is above a specific threshold (50). If the signal is too low,
        the function returns a TRUE signal indicating that the autofocus has been lost.
        """
        self.qpd_reset()
        qpd_sum = self.qpd('sum')
        if qpd_sum < 50:
            self.log.warning('autofocus lost')
            return True
        else:
            return False

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

    def worker_frequency(self):
        """ Update the worker frequency according to the iteration time of the fpga
        """
        qpd = self._fpga.read_qpd()
        iteration_duration = qpd[4] / 1000 + 0.01
        return iteration_duration

    def qpd_reset(self):
        """ Reset the QPD counter
        """
        self._fpga.reset_qpd_counter()

