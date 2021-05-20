#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

"""

from core.connector import Connector
from core.configoption import ConfigOption
from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic
from qtpy import QtCore

import numpy as np
from numpy.polynomial import Polynomial as Poly
from simple_pid import PID
import pyqtgraph as pg
from time import sleep


class AutofocusLogic(GenericLogic):
    """ This logic connect to the instruments necessary for the autofocus method based on the camera. This logic
    is directly connected to the focus_logic controlling the piezo position.
    
    autofocus_logic:
        module.Class: 'autofocus_logic.AutofocusLogic'
        autofocus_ref_axis : 'X' # 'Y'
        proportional_gain : 0.1 # in %%
        integration_gain : 1 # in %%
        exposure = 0.001
        connect:
            camera : 'thorlabs_camera'
    """

    # declare connectors
    camera = Connector(interface='CameraInterface')

    # camera attributes
    _exposure = ConfigOption('exposure', 0.001, missing='warn')
    _camera_acquiring = False
    _threshold = 150

    # autofocus attributes
    _focus_offset = 0  # defaults to zero for a 2 axes system
    _ref_axis = ConfigOption('autofocus_ref_axis', 'X', missing='warn')
    _autofocus_stable = False
    _autofocus_iterations = 0

    # pid attributes
    _pid_frequency = 0.2  # in s, frequency for the autofocus PID update
    _P_gain = ConfigOption('proportional_gain', 0, missing='warn')
    _I_gain = ConfigOption('integration_gain', 0, missing='warn')
    _setpoint = None
    _pid = None

    _last_pid_output_values = np.zeros((10,))

    # signals
    sigOffsetDefined = QtCore.Signal()  # never emitted from this module, just for compatibility
    sigStageMoved = QtCore.Signal()     # never emitted from this module, just for compatibility

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # hardware connection
        self._camera = self.camera()

        # initialize the camera
        self._camera.set_exposure(self._exposure)
        self._im_size = self._camera.get_size()
        self._idx_X = np.linspace(0, self._im_size[0] - 1, self._im_size[0])
        self._idx_Y = np.linspace(0, self._im_size[1] - 1, self._im_size[1])
        self.init_pid()

    def on_deactivate(self):
        """ Required deactivation.
        """
        self.stop_camera_live()

# =======================================================================================
# Public method for the autofocus, used by all the methods (camera or FPGA/QPD based)
# =======================================================================================

    def read_detector_signal(self):
        """ General function returning the reference signal for the autofocus correction. In the case of the
        method using a FPGA, it returns the QPD signal measured along the reference axis.
        """
        im = self.get_latest_image()
        mask = self.calculate_threshold_image(im)
        x0, y0 = self.calculate_centroid(im, mask)

        if self._ref_axis == 'X':
            return x0
        else:
            return y0

    def autofocus_check_signal(self):
        """ Check that the camera is properly detecting a spot (above a specific threshold). If the signal is too low,
        the function returns False to indicate that the autofocus signal is lost.
        :return bool: True: signal ok, False: signal too low
        """
        im = self.get_latest_image()
        im_threshold = self.calculate_threshold_image(im)

        if np.sum(im_threshold) < 50:
            return False
        else:
            return True

    def define_pid_setpoint(self):
        """ Initialize the pid setpoint
        """
        self._setpoint = self.read_detector_signal()
        return self._setpoint

    def init_pid(self):
        """ Initialize the pid for the autofocus
        """
        self._pid = PID(self._P_gain, self._I_gain, 0, setpoint=self._setpoint)
        self._pid.sample_time = self._pid_frequency

        self._autofocus_stable = False
        self._autofocus_iterations = 0

    def read_pid_output(self, check_stabilization):
        """ Read the pid output signal in order to adjust the position of the objective
        """
        centroid = self.read_detector_signal()
        pid_output = self._pid(centroid)

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
            else:
                self._autofocus_stable = False

        return self._autofocus_stable

    def start_camera_live(self):
        """ Launch live acquisition of the camera
        """
        self._camera.start_live_acquisition()
        self._camera_acquiring = True

    def stop_camera_live(self):
        """ Stop live acquisition of the camera
        """
        self._camera.stop_acquisition()
        self._camera_acquiring = False

    def get_latest_image(self):
        """ Get the latest acquired image from the camera. This function returns the raw image as well as the
        threshold image
        """
        im = self._camera.get_acquired_data()
        return im

# ================================================================================
# empty methods (only available on systems with 3 axes stage)
# ================================================================================

    def calibrate_offset(self):
        """ This method requires a connected 3 axis stage and is not available for the camera based autofocus logic.
        """
        self.log.warning('calibrate_offset is not available on this setup.')
        return 0  # to test if this is ok to use 0 value for not available offset

    def rescue_autofocus(self):
        """ This method requires a connected 3 axis stage and is not available for the camera based autofocus logic.
        """
        self.log.warning('rescue_autofocus is not available on this setup.')

    def stage_move_z(self, step):
        self.log.warning('stage movement is not supported on this setup')

    def do_position_correction(self):
        self.log.warning('stage movement is not supported on this setup')

    def start_piezo_position_correction(self, direction):
        """ This method requires a connected 3 axis stage and is not available for the camera based autofocus logic.
        """
        self.log.warning('start_piezo_position_correction is not available on this setup.')

    # def run_piezo_position_correction(self):
    #     """ This method requires a connected 3 axis stage and is not available for the camera based autofocus logic.
    #     """
    #     self.log.info('run_piezo_position_correction is not available on this setup.')

# =================================================================
# private methods for camera-based autofocus
# =================================================================
    def calculate_threshold_image(self, im):
        """ Calculate the threshold image according to the threshold value
        """
        mask = np.copy(im)
        mask[mask > self._threshold] = 254
        mask[mask <= self._threshold] = 0
        return mask

    def calculate_centroid(self, im, mask):
        """ Calculate the centroid of the raw image using the threshold image as mask
        """
        im_x = np.sum(im * mask, 0)  # Calculate the projection along the X axis
        im_y = np.sum(im * mask, 1)  # Calculate the projection along the Y axis
        if sum(im_x) != 0 and sum(im_y) != 0:
            x0 = sum(self._idx_X * im_x) / sum(im_x)
            y0 = sum(self._idx_Y * im_y) / sum(im_y)
        else:
            x0 = 0 
            y0 = 0

        return x0, y0


