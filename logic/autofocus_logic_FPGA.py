#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

"""

from core.connector import Connector
from core.configoption import ConfigOption
from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic
from qtpy import QtCore

import pyqtgraph as pg
import numpy as np
from numpy.polynomial import Polynomial as Poly
from time import sleep


class AutofocusLogic(GenericLogic):
    """ This logic connect to the instruments necessary for the autofocus method based on the FPGA + QPD. This logic
    is directly connected to the focus_logic controlling the piezo position.
    
    autofocus_logic:
        module.Class: 'autofocus_logic.AutofocusLogic'
        autofocus_ref_axis : 'X' # 'Y'
        proportional_gain : 0.1 # in %%
        integration_gain : 1 # in %%
        exposure = 0.001
        connect:
            camera : 'thorlabs_camera'
            fpga: 'nifpga'
    """

    # declare connectors
    fpga = Connector(interface='FPGAInterface')  # to check _ a new interface was defined for FPGA connection
    camera = Connector(interface='CameraInterface')

    # camera attributes
    _exposure = ConfigOption('exposure', 0.001, missing='warn')
    _camera_acquiring = False

    # autofocus attributes
    # _autofocus_signal = None
    _ref_axis = ConfigOption('autofocus_ref_axis', 'X', missing='warn')
    _autofocus_stable = False
    _autofocus_iterations = 0

    # pid attributes
    _pid_frequency = 0.2  # in s, frequency for the autofocus PID update
    _P_gain = ConfigOption('proportional_gain', 0, missing='warn')
    _I_gain = ConfigOption('integration_gain', 0, missing='warn')
    _setpoint = None

    _last_pid_output_values = np.zeros((10,))

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # initialize the fpga
        self._fpga = self.fpga()

        # initialize the camera
        self._camera = self.camera()
        self._camera.set_exposure(self._exposure)

    def on_deactivate(self):
        """ Required deactivation.
        """
        pass

    # Public method for the autofocus, used by all the methods (camera or FPGA/QPD based)
    # -----------------------------------------------------------------------------------
        
    def read_detector_signal(self):
        """ General function returning the reference signal for the autofocus correction. In the case of the
        method using a FPGA, it returns the QPD signal measured along the reference axis.
        """
        return self.qpd_read_position()

    def read_detector_intensity(self):
        """ Function used for the focus search. Measured the intensity of the reflection instead of reading its
        position
        """
        return self.qpd_read_sum()

    def autofocus_check_signal(self):
        """ Check that the intensity detected by the QPD is above a specific threshold (50). If the signal is too low,
        the function returns a TRUE signal indicating that the autofocus has been lost.
        """
        qpd_sum = self.qpd_read_sum()
        if qpd_sum < 300:
            return True
        else:
            return False

    def pid_setpoint(self):
        """ Initialize the pid setpoint
        """
        self.qpd_reset()
        self._setpoint = self.read_detector_signal()
        return(self._setpoint)

    def init_pid(self):
        """ Initialize the pid for the autofocus
        """
        self.qpd_reset()
        self._fpga.init_pid(self._P_gain, self._I_gain, self._setpoint, self._ref_axis)
        self.worker_frequency()

        self._autofocus_stable = False
        self._autofocus_iterations = 0

    def read_pid_output(self, check_stabilization):
        """ Read the pid output signal in order to adjust the position of the objective
        """
        pid_output = self._fpga.read_pid()

        if check_stabilization:
            self._autofocus_iterations += 1
            self._last_pid_output_values = np.concatenate((self._last_pid_output_values[1:10], [pid_output]))
            return pid_output, self.check_stabilization()
        else:
            return pid_output

    def check_stabilization(self):
        """ Check for the stabilization of the focus
        """
        if self._autofocus_iterations > 10:
            p = Poly.fit(np.linspace(0, 9, num=10), self._last_pid_output_values, deg=1)
            slope = p(9) - p(0)
            if np.absolute(slope) < 10:
                self._autofocus_stable = True
            else :
                self._autofocus_stable = False

        return self._autofocus_stable

    # Methods specific to the QPD-based method (private).
    # --------------------------------------------------

    def qpd_read_position(self):
        """ Read the QPD signal from the FPGA. The signal is read from X/Y positions. In order to make sure we are
        always reading from the latest piezo position, the method is waiting for a new count.
        """
        qpd = self._fpga.read_qpd()
        last_count = qpd[3]
        while last_count == qpd[3]:
            qpd = self._fpga.read_qpd()
            sleep(0.01)

        if self._ref_axis == 'X':
            return qpd[0]
        elif self._ref_axis == 'Y':
            return qpd[1]

    def qpd_read_sum(self):
        """ Read the SUM signal from the QPD. Returns an indication whether there is a detected signal or not
        """
        qpd = self._fpga.read_qpd()
        return qpd[2]

    def worker_frequency(self):
        """ Update the worker frequency according to the iteration time of the fpga
        """
        qpd = self._fpga.read_qpd()
        self._pid_frequency = qpd[4] / 1000 + 0.01

    def qpd_reset(self):
        """ Reset the QPD counter
        """
        self._fpga.reset_qpd_counter()

    def start_camera_live(self):
        """ Launch live acquisition of the camera
        """
        self._camera.start_live_acquisition()
        self._camera_acquiring = True

    def get_latest_image(self):
        """ Get the latest acquired image from the camera. This function returns the raw image as well as the
        threshold image
        """
        im = self._camera.get_acquired_data()
        return im

    def stop_camera(self):
        """ Stop live acquisition of the camera
        """
        self._camera.stop_acquisition()
        self._camera_acquiring = False

