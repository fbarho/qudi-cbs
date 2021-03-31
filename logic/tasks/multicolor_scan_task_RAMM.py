# -*- coding: utf-8 -*-
"""
Created on Wed March 10 2021

@author: fbarho

This file is an extension to Qudi software
obtained from <https://github.com/Ulm-IQO/qudi/>

Multicolor z-scan task for the RAMM setup

Config example pour copy-paste:
    MulticolorScanTask:
        module: 'multicolor_scan_task_RAMM'
        needsmodules:
            fpga: 'lasercontrol_logic'
            cam: 'camera_logic'
            daq: 'nidaq_6259_logic'
            piezo: 'focus_logic'
"""

import numpy as np
from time import sleep, time
from logic.generic_task import InterruptableTask


class Task(InterruptableTask):  # do not change the name of the class. it is always called Task !
    """ This task does an acquisition of a series of planes in z direction using a sequence of lightsources for each plane
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print('Task {0} added!'.format(self.name))

    def startTask(self):
        """ """
        print('start Task')
        self.log.info('started Task')
        # close default FPGA session
        self.ref['fpga'].close_default_session()

        # read all user parameters from config
        self.load_user_parameters()

        # download the bitfile for the task on the FPGA
        # bitfile = 'C:\\Users\\sCMOS-1\\qudi-cbs\\hardware\\fpga\\FPGA\\FPGA Bitfiles\\FPGAv0_FPGATarget_FPGAtriggercamer_u12WjFsC0U8.lvbitx'  #old version
        bitfile = 'C:\\Users\\sCMOS-1\\qudi-cbs\\hardware\\fpga\\FPGA\\FPGA Bitfiles\\FPGAv0_FPGATarget_FPGAmerFISHtrigg_jtu2knQ4gk8.lvbitx'  #new version including qpd but qpd part not yet corrected
        self.ref['fpga'].start_task_session(bitfile)

        # prepare the daq: set the digital output to 0 before starting the task
        self.ref['daq'].write_to_do_channel(1, np.array([0], dtype=np.uint8), self.ref['daq']._daq.DIO3_taskhandle)

        # prepare the camera
        self.num_frames = self.num_z_planes * self.num_laserlines
        self.ref['cam'].prepare_camera_for_multichannel_imaging(self.num_frames, self.exposure, None, None, None)

        # initialize the counter (corresponding to the number of planes already acquired)
        self.step_counter = 0

        # start the session on the fpga using the user parameters
        self.ref['fpga'].run_multicolor_imaging_task_session(self.num_z_planes, self.wavelengths, self.intensities, self.num_laserlines)

    def runTaskStep(self):
        """ Implement one work step of your task here.
        @return bool: True if the task should continue running, False if it should finish.
        """
        self.step_counter += 1
        print(f'plane number {self.step_counter}')

        # position the piezo
        position = self.start_position + (self.step_counter - 1) * self.z_step
        self.ref['piezo'].go_to_position(position)
        print(f'target position: {position} um')
        sleep(0.03)
        cur_pos = self.ref['piezo'].get_position()
        print(f'current position: {cur_pos} um')

        # send signal from daq to FPGA connector 0/DIO3 ('piezo ready')
        self.ref['daq'].write_to_do_channel(1, np.array([1], dtype=np.uint8), self.ref['daq']._daq.DIO3_taskhandle)
        sleep(0.005)
        self.ref['daq'].write_to_do_channel(1, np.array([0], dtype=np.uint8), self.ref['daq']._daq.DIO3_taskhandle)

        # wait for signal from FPGA to DAQ ('acquisition ready')
        fpga_ready = self.ref['daq'].read_do_channel(1, self.ref['daq']._daq.DIO4_taskhandle)[0]
        t0 = time()

        while not fpga_ready:
            sleep(0.001)
            fpga_ready = self.ref['daq'].read_do_channel(1, self.ref['daq']._daq.DIO4_taskhandle)[0]

            t1 = time() - t0
            if t1 > 5:  # for safety: timeout if no signal received within 5 s
                break

        return self.step_counter < self.num_z_planes

    def pauseTask(self):
        """ """
        self.log.info('pauseTask called')

    def resumeTask(self):
        """ """
        self.log.info('resumeTask called')

    def cleanupTask(self):
        """ """
        self.log.info('cleanupTask called')
        # get acquired data from the camera and save it to file in case the task has not been aborted during acquisition
        if self.step_counter == self.num_z_planes:
            image_data = self.ref['cam'].get_acquired_data()
            print(image_data.shape)

            if self.file_format == 'fits':
                metadata = {}  # to be added
                self.ref['cam']._save_to_fits(self.save_path, image_data, metadata)
            else:   # use tiff as default format
                self.ref['cam']._save_to_tiff(self.num_frames, self.save_path, image_data)
                # add metadata saving

        # reset the camera to default state
        self.ref['cam'].reset_camera_after_multichannel_imaging()
        # close the fpga session and restart the default session
        self.ref['fpga'].end_task_session()
        self.ref['fpga'].restart_default_session()
        self.log.info('restarted default session')
        self.log.info('cleanupTask finished')

    def load_user_parameters(self):
        # to be read from config later
        self.exposure = 0.1
        self.num_z_planes = 10
        self.z_step = 0.25  # in um
        self.centered_focal_plane = True
        self.start_position = self.calculate_start_position(self.centered_focal_plane)
        self.save_path = 'C:\\Users\\sCMOS-1\\Desktop\\teststack.tiff'  # to be defined how the default folder structure should be set up
        self.file_format = 'tiff'

        lightsource_dict = {'BF': 0, '405 nm': 1, '488 nm': 2, '561 nm': 3, '640 nm': 4}
        self.imaging_sequence = [('561 nm', 5), ('640 nm', 50)]
        self.num_laserlines = len(self.imaging_sequence)
        wavelengths = [self.imaging_sequence[i][0] for i, item in enumerate(self.imaging_sequence)]
        wavelengths = [lightsource_dict[key] for key in wavelengths]
        for i in range(self.num_laserlines, 5):
            wavelengths.append(0)  # must always be a list of length 5: append zeros until necessary length reached
        self.wavelengths = wavelengths
        print(self.wavelengths)

        self.intensities = [self.imaging_sequence[i][1] for i, item in enumerate(self.imaging_sequence)]
        for i in range(self.num_laserlines, 5):
            self.intensities.append(0)
        print(self.intensities)

        # self.wavelengths = [3, 3, 3, 3, 3]
        # self.intensities = [3, 0, 4, 0, 5]



    def calculate_start_position(self, centered_focal_plane):
        """
        @param bool centered_focal_plane: indicates if the scan is done below and above the focal plane (True) or if the focal plane is the bottommost plane in the scan (False)
        """
        current_pos = self.ref['piezo'].get_position()  # lets assume that we are at focus (user has set focus or run autofocus)

        if centered_focal_plane:  # the scan should start below the current position so that the focal plane will be the central plane or one of the central planes in case of an even number of planes
            # even number of planes:
            if self.num_z_planes % 2 == 0:
                start_pos = current_pos - self.num_z_planes / 2 * self.z_step  # focal plane is the first one of the upper half of the number of planes
            # odd number of planes:
            else:
                start_pos = current_pos - (self.num_z_planes - 1)/2 * self.z_step
            return start_pos
        else:
            return current_pos  # the scan starts at the current position and moves up
