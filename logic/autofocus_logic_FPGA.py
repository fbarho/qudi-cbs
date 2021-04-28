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


class WorkerSignals(QtCore.QObject):
    """ Defines the signals available from a running worker thread """

    sigFinished = QtCore.Signal()


class StageAutofocusWorker(QtCore.QRunnable):
    """ Worker thread to control the stage position and adjust the piezo position when autofocus in ON
    The worker handles only the waiting time, and emits a signal that serves to trigger the update indicators """

    def __init__(self, *args, **kwargs):
        super(StageAutofocusWorker, self).__init__(*args, **kwargs)
        self.signals = WorkerSignals()

    @QtCore.Slot()
    def run(self):
        """ """
        sleep(0.5)
        self.signals.sigFinished.emit()


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
            stage: 'ms2000'
    """

    # declare connectors
    fpga = Connector(interface='FPGAInterface')  # to check _ a new interface was defined for FPGA connection
    stage = Connector(interface='MotorInterface')
    camera = Connector(interface='CameraInterface')

    # camera attributes
    _exposure = ConfigOption('exposure', 0.001, missing='warn')
    _camera_acquiring = False

    # autofocus attributes
    # _autofocus_signal = None
    _focus_offset = ConfigOption('focus_offset', 0, missing='warn')
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

        self.threadpool = QtCore.QThreadPool()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # hardware connections
        self._fpga = self.fpga()
        self._stage = self.stage()
        self._camera = self.camera()
        self._camera.set_exposure(self._exposure)

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
        return self.qpd_read_position()

    # fpga only
    def read_detector_intensity(self):
        """ Function used for the focus search. Measured the intensity of the reflection instead of reading its
        position
        """
        return self.qpd_read_sum()

    # for better readability maybe invert true and false .. false meaning that signal not ok ..
    def autofocus_check_signal(self):
        """ Check that the intensity detected by the QPD is above a specific threshold (50). If the signal is too low,
        the function returns a TRUE signal indicating that the autofocus has been lost.
        """
        qpd_sum = self.qpd_read_sum()
        if qpd_sum < 300:
            return True
        else:
            return False

    def define_pid_setpoint(self):
        """ Initialize the pid setpoint
        """
        self.qpd_reset()
        self._setpoint = self.read_detector_signal()

    def init_pid(self):
        """ Initialize the pid for the autofocus
        """
        self.qpd_reset()
        self._fpga.init_pid(self._P_gain, self._I_gain, self._setpoint, self._ref_axis)
        self.set_worker_frequency()

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

    # fpga only
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

    def calibrate_offset(self):
        """ Calibrate the offset between the sample position and a reference on the bottom of the coverslip. This method
        is inspired from the LSM-Zeiss microscope and is used when the sample (such as embryos) is interfering too much
        with the IR signal and makes the regular focus stabilization unstable.
        """
        # Read the stage position
        z_up = self._stage.get_pos()['z']

        # Move the stage by the default offset value along the z-axis
        pos_dict = {'z': self._focus_offset}
        self._stage.move_rel(pos_dict)

        # Check the IR signal is detected
        if self.autofocus_check_signal():  # returns true if focus lost
            self.rescue_autofocus()

        # Look for the position with the maximum intensity - for the QPD the SUM signal is used.
        max_sum = 0
        z_range = 5  # in µm
        z_step = 0.1  # in µm

        pos_dict = {'z': -z_range//2}
        self._stage.move_rel(pos_dict)

        for n in range(int(z_range/z_step)):

            pos_dict = {'z': z_step}
            self._stage.move_rel(pos_dict)

            sum = self.read_detector_intensity()
            print(sum)
            if sum > max_sum:
                max_sum = sum
            elif sum < max_sum and max_sum > 500:
                break

        # Read the qpd signal and define the new setpoint
        self.define_autofocus_setpoint()

        # Calculate the offset for the stage and move back to the initial position
        self._focus_offset = self._stage.get_pos()['z'] - z_up

        pos_dict = {'z': -self._focus_offset}
        self._stage.move_rel(pos_dict)

        return self._focus_offset

    def rescue_autofocus(self):
        """ When the autofocus signal is lost, launch a rescuing procedure by using the MS2000 translation stage. The
        z position of the stage is moved until the piezo signal is found again.
        """
        z_range = 20
        # while self._autofocus_lost and z_range <= 40:
        while self.autofocus_check_signal() and z_range <= 40:

            pos_dict = {'z': -z_range//2}
            self._stage.move_rel(pos_dict)

            for z in range(z_range):
                step = 1
                pos_dict = {'z': step}
                self._stage.move_rel(pos_dict)

                # self._autofocus_lost = self._autofocus_logic.autofocus_check_signal()
                # if not self._autofocus_lost:
                if not self.autofocus_check_signal():
                    print("autofocus signal found!")
                    break

            # if self._autofocus_lost:
            if self.autofocus_check_signal():
                pos_dict = {'z': -z_range//2}
                self._stage.move_rel(pos_dict)
                z_range += 10

    def start_piezo_position_correction(self, direction):
        """ When the piezo position gets too close to the limits, the MS2000 stage is used to move the piezo back
        to a standard position. If the piezo close to the lower limit (<5µm) it is moved to 25µm. If the piezo is too
        close to the upper limit (>70µm), it is moved back to 50µm.
        """

        if direction == "up":
            step = 1
        elif direction == "down":
            step = -1
        else:
            self.log.warning('no valid direction specified')
            return

        self._pos_dict = {'z': step}

        # this needs to be modified :
        if not self._run_autofocus:
            self.start_autofocus()

        stage_worker = StageAutofocusWorker()
        stage_worker.signals.sigFinished.connect(self.run_piezo_position_correction)
        self.threadpool.start(stage_worker)

    def run_piezo_position_correction(self):
        """ Correct the piezo position by moving the MS2000 stage while the autofocus ON
        """
        z = self.get_position()  # z posiiton of the piezo -- to be modified, this needs to be passed in by the focus_logic
        # if not self._autofocus_lost and (z < 25 or z > 50):
        if not self.autofocus_check_signal and (z < 25 or z > 50):
            self._stage.move_rel(self._pos_dict)

            stage_worker = StageAutofocusWorker()
            stage_worker.signals.sigFinished.connect(self.run_piezo_position_correction)
            self.threadpool.start(stage_worker)

# =================================================================
# private methods for QPD-based autofocus
# =================================================================

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

    def set_worker_frequency(self):
        """ Update the worker frequency according to the iteration time of the fpga
        """
        qpd = self._fpga.read_qpd()
        self._pid_frequency = qpd[4] / 1000 + 0.01

    def qpd_reset(self):
        """ Reset the QPD counter
        """
        self._fpga.reset_qpd_counter()
