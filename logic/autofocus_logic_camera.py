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

import numpy as np
from simple_pid import PID
import pyqtgraph as pg
from time import sleep


class AutofocusLogic(GenericLogic):
    """ This logic connect to the instruments necessary for the autofocus method based on the camera. This logic
    is directly connected to the focus_logic controlling the piezo position.
    
    autofocus_logic:
        module.Class: 'autofocus_logic.AutofocusLogic'
        Autofocus_ref_axis : 'X' # 'Y'
        connect:
            camera : 'thorlabs_camera'
            fpga: 'nifpga'
    """

    # declare connectors
    camera = Connector(interface='CameraInterface')

    # autofocus attributes
    _autofocus_signal = None
    _ref_axis = ConfigOption('Autofocus_ref_axis', 'X', missing='warn')

    # camera attributes
    _threshold = 150
    _exposure = ConfigOption('Exposure', 0.001, missing='warn')
    _camera_acquiring = False

    # pid attributes
    _pid_frequency = 0.2  # in s, frequency for the autofocus PID update
    _P_gain = ConfigOption('Proportional_gain', 0, missing='warn')
    _I_gain = ConfigOption('Integration_gain', 0, missing='warn')
    _setpoint = None
    _pid = PID(_P_gain, _I_gain, 0, setpoint=_setpoint)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # self.threadlock = Mutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # initialize the camera
        self._camera = self.camera()
        self._camera.set_exposure(self._exposure)
        self._im_size = self._camera.get_size()
        self._idx_X = np.linspace(0, self._im_size[0] - 1, self._im_size[0])
        self._idx_Y = np.linspace(0, self._im_size[1] - 1, self._im_size[1])

    def on_deactivate(self):
        """ Required deactivation.
        """
        if self._camera_acquiring:
            self.stop_camera()

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
        """ Check that the camera is properly detecting a spot
        """
        im = self.get_latest_image()
        im_threshold = self.calculate_threshold_image(im)

        if np.sum(im_threshold) < 50:
            self.log.warning('autofocus lost')
            return True
        else:
            return False

    def pid_setpoint(self):
        """ Initialize the pid setpoint
        """
        self._setpoint = self.read_detector_signal()

    def init_pid(self):
        """ Initialize the pid for the autofocus
        """
        self._pid = PID(self._P_gain, self._I_gain, 0, setpoint=self._setpoint)
        self._pid.sample_time = self._pid_frequency

    def read_pid_output(self):
        """ Read the pid output signal in order to adjust the position of the objective
        """
        return self._pid(self.read_detector_signal())

    def start_camera_live(self):
        """ Launch live acquisition of the camera
        """
        self._camera.start_live_acquisition()
        self._camera_acquiring = True

    def stop_camera(self):
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
        x0 = sum(self._idx_X * im_x) / sum(im_x)
        y0 = sum(self._idx_Y * im_y) / sum(im_y)

        return x0, y0

