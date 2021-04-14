# -*- coding: utf-8 -*-
"""
Created on Wed March 30 2021

@author: fbarho

This file is an extension to Qudi software
obtained from <https://github.com/Ulm-IQO/qudi/>

Multicolor z-scan task for the RAMM setup iterating over a list of ROIs

Config example pour copy-paste:
    ROIMulticolorScanTask:
        module: 'roi_multicolor_scan_task_RAMM'
        needsmodules:
            fpga: 'lasercontrol_logic'
            cam: 'camera_logic'
            daq: 'nidaq_6259_logic'
            piezo: 'focus_logic'
            roi: 'roi_logic'
        path_to_user_config: 'C:\\Users\\sCMOS-1\\qudi_task_configs\\roi_multicolor_scan_task_RAMM'
"""

import numpy as np
import os
import yaml
from time import sleep, time
from logic.generic_task import InterruptableTask


class Task(InterruptableTask):  # do not change the name of the class. it is always called Task !
    """ This task iterates over all roi given in a file and does an acquisition of a series of planes in z direction
    using a sequence of lightsources for each plane, for each roi.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print('Task {0} added!'.format(self.name))
        # self.user_config_path = self.config['path_to_user_config']

    def startTask(self):
        """ """
        self.log.info('started Task')
        # close default FPGA session
        self.ref['fpga'].close_default_session()

        # read all user parameters from config
        self.load_user_parameters()

        # set stage velocity
        self.ref['roi'].set_stage_velocity({'x': 1, 'y': 1})

        bitfile = 'C:\\Users\\sCMOS-1\\qudi-cbs\\hardware\\fpga\\FPGA\\FPGA Bitfiles\\FPGAv0_FPGATarget_FPGAmerFISHtrigg_jtu2knQ4gk8.lvbitx'  #new version including qpd but qpd part not yet corrected
        self.ref['fpga'].start_task_session(bitfile)

        # start the session on the fpga using the user parameters
        self.ref['fpga'].run_multicolor_imaging_task_session(self.num_z_planes, self.wavelengths, self.intensities, self.num_laserlines)

        # prepare the camera
        self.num_frames = self.num_z_planes * self.num_laserlines
        self.ref['cam'].prepare_camera_for_multichannel_imaging(self.num_frames, self.exposure, None, None, None)

        # initialize a counter to iterate over the ROIs
        self.roi_counter = 0
        # set the active_roi to none # to avoid having two active rois displayed
        self.ref['roi'].active_roi = None

    def runTaskStep(self):
        """ Implement one work step of your task here.
        @return bool: True if the task should continue running, False if it should finish.
        """
        # go to roi
        self.ref['roi'].set_active_roi(name=self.roi_names[self.roi_counter])
        self.ref['roi'].go_to_roi()
        self.log.info('Moved to {}'.format(self.roi_names[self.roi_counter]))
        # waiting time needed ???
        sleep(1)  # replace maybe by wait for idle

        # create a folder for each roi
        cur_save_path = os.path.join(self.save_path, self.roi_names[self.roi_counter])
        # create the complete path
        complete_path = self.ref['cam']._create_generic_filename(cur_save_path, '_Scan', 'Scan', '.'+self.file_format, addfile=False)
        self.log.info(f'complete path: {complete_path}')

        # imaging sequence:
        # prepare the daq: set the digital output to 0 before starting the task
        self.ref['daq'].write_to_do_channel(1, np.array([0], dtype=np.uint8), self.ref['daq']._daq.DIO3_taskhandle)

        # start camera acquisition
        self.ref['cam'].stop_acquisition()  # for safety
        self.ref['cam'].start_acquisition()

        for plane in range(self.num_z_planes):
            print(f'plane number {plane + 1}')

            # position the piezo
            position = self.start_position + plane * self.z_step
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

        # get acquired data from the camera and save it to file
        image_data = self.ref['cam'].get_acquired_data()
        print(image_data.shape)

        # save path needs to be adapted depending on the file hierarchy

        if self.file_format == 'fits':
            metadata = {}  # to be added
            self.ref['cam']._save_to_fits(complete_path, image_data, metadata)
        else:  # use tiff as default format
            self.ref['cam']._save_to_tiff(self.num_frames, complete_path, image_data)
            # add metadata saving

        self.roi_counter += 1

        return self.roi_counter < len(self.roi_names)

    def pauseTask(self):
        """ """
        self.log.info('pauseTask called')

    def resumeTask(self):
        """ """
        self.log.info('resumeTask called')

    def cleanupTask(self):
        """ """
        self.log.info('cleanupTask called')
        # reset the camera to default state
        self.ref['cam'].reset_camera_after_multichannel_imaging()
        # close the fpga session
        self.ref['fpga'].end_task_session()
        self.ref['fpga'].restart_default_session()
        self.log.info('restarted default session')
        # reset stage velocity to default
        self.ref['roi'].set_stage_velocity({'x': 7, 'y': 7})  # 5.74592
        self.log.info('cleanupTask finished')

    def load_user_parameters(self):
        # define user parameters  # to be read from config later
        self.exposure = 0.1
        self.num_z_planes = 50
        self.z_step = 0.2  # in um
        self.centered_focal_plane = True
        self.start_position = self.calculate_start_position(self.centered_focal_plane)
        self.imaging_sequence = [('488 nm', 20), ('561 nm', 10), ('640 nm', 10)]
        self.save_path = 'C:\\Users\\sCMOS-1\\Desktop\\2021_03_31'  # to be defined how the default folder structure should be set up
        self.file_format = 'fits'
        self.roi_list_path = 'C:\\Users\\sCMOS-1\\Desktop\\roilist1.json'

        # try:
        #     with open(self.user_config_path, 'r') as stream:
        #         self.user_param_dict = yaml.safe_load(stream)
        #
        #         self.exposure = self.user_param_dict['exposure']
        #         self.num_z_planes = self.user_param_dict['num_z_planes']
        #         self.z_step = self.user_param_dict['z_step']  # in um
        #         self.centered_focal_plane = self.user_param_dict['centered_focal_plane']
        #         self.imaging_sequence = self.user_param_dict['imaging_sequence']
        #         self.save_path = self.user_param_dict['save_path']
        #         self.file_format = self.user_param_dict['file_format']
        #         self.roi_list_path = self.user_param_dict['roi_list_path']
        #
        # except Exception as e:  # add the type of exception
        #     self.log.warning(f'Could not load user parameters for task {self.name}: {e}')

        # establish further user parameters derived from the given ones:
        # create a list of roi names
        self.ref['roi'].load_roi_list(self.roi_list_path)
        # get the list of the roi names
        self.roi_names = self.ref['roi'].roi_names

        # convert the imaging_sequence given by user into format required by the bitfile
        lightsource_dict = {'BF': 0, '405 nm': 1, '488 nm': 2, '561 nm': 3, '640 nm': 4}
        self.num_laserlines = len(self.imaging_sequence)
        wavelengths = [self.imaging_sequence[i][0] for i, item in enumerate(self.imaging_sequence)]
        wavelengths = [lightsource_dict[key] for key in wavelengths]
        for i in range(self.num_laserlines, 5):
            wavelengths.append(0)  # must always be a list of length 5: append zeros until necessary length reached
        self.wavelengths = wavelengths

        self.intensities = [self.imaging_sequence[i][1] for i, item in enumerate(self.imaging_sequence)]
        for i in range(self.num_laserlines, 5):
            self.intensities.append(0)




    def calculate_start_position(self, centered_focal_plane):
        """
        @param bool centered_focal_plane: indicates if the scan is done below and above the focal plane (True) or if the focal plane is the bottommost plane in the scan (False)
        """
        current_pos = self.ref['piezo'].get_position()  # for tests until we have the autofocus #self.ref['piezo'].get_position()  # lets assume that we are at focus (user has set focus or run autofocus)
        print(f'current position: {current_pos}')

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
