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
        config:
            path_to_user_config: 'C:/Users/sCMOS-1/qudi_data/qudi_task_config_files/multicolor_scan_task_RAMM.yaml'
"""
import os
from datetime import datetime
import numpy as np
import yaml
from time import sleep, time
from logic.generic_task import InterruptableTask


class Task(InterruptableTask):  # do not change the name of the class. it is always called Task !
    """ This task does an acquisition of a series of planes in z direction using a sequence of lightsources for each plane
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print('Task {0} added!'.format(self.name))
        self.user_config_path = self.config['path_to_user_config']

    def startTask(self):
        """ """
        print('start Task')
        self.log.info('started Task')
        # close default FPGA session
        self.ref['fpga'].close_default_session()

        # read all user parameters from config
        self.load_user_parameters()

        # download the bitfile for the task on the FPGA
        bitfile = 'C:\\Users\\sCMOS-1\\qudi-cbs\\hardware\\fpga\\FPGA\\FPGA Bitfiles\\FPGAv0_FPGATarget_FPGAmerFISHtrigg_jtu2knQ4gk8.lvbitx'  #new version including qpd but qpd part not yet corrected
        self.ref['fpga'].start_task_session(bitfile)

        # prepare the daq: set the digital output to 0 before starting the task
        self.ref['daq'].write_to_do_channel(1, np.array([0], dtype=np.uint8), self.ref['daq']._daq.DIO3_taskhandle)

        # prepare the camera
        self.num_frames = self.num_z_planes * self.num_laserlines
        self.ref['cam'].prepare_camera_for_multichannel_imaging(self.num_frames, self.exposure, None, None, None)
        self.ref['cam'].start_acquisition()

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
                self.log.warning('Timeout occured')
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

        # reset piezo position to the initial one
        self.ref['piezo'].go_to_position(self.focal_plane_position)

        # get acquired data from the camera and save it to file in case the task has not been aborted during acquisition
        if self.step_counter == self.num_z_planes:
            image_data = self.ref['cam'].get_acquired_data()

            if self.file_format == 'fits':
                metadata = self.get_fits_metadata()
                self.ref['cam']._save_to_fits(self.complete_path, image_data, metadata)
            else:   # use tiff as default format
                self.ref['cam']._save_to_tiff(self.num_frames, self.complete_path, image_data)
                metadata = self.get_metadata()
                file_path = self.complete_path.replace('tiff', 'txt', 1)
                self.save_metadata_file(metadata, file_path)

        # reset the camera to default state
        self.ref['cam'].reset_camera_after_multichannel_imaging()
        # close the fpga session and restart the default session
        self.ref['fpga'].end_task_session()
        self.ref['fpga'].restart_default_session()
        self.log.info('restarted default fpga session')
        self.log.info('cleanupTask finished')

    def load_user_parameters(self):
        try:
            with open(self.user_config_path, 'r') as stream:
                self.user_param_dict = yaml.safe_load(stream)

                self.sample_name = self.user_param_dict['sample_name']
                self.exposure = self.user_param_dict['exposure']
                self.num_z_planes = self.user_param_dict['num_z_planes']
                self.z_step = self.user_param_dict['z_step']  # in um
                self.centered_focal_plane = self.user_param_dict['centered_focal_plane']
                self.imaging_sequence = self.user_param_dict['imaging_sequence']
                self.save_path = self.user_param_dict['save_path']
                self.file_format = self.user_param_dict['file_format']

        except Exception as e:  # add the type of exception
            self.log.warning(f'Could not load user parameters for task {self.name}: {e}')

        # establish further user parameters derived from the given ones
        self.complete_path = self.get_complete_path(self.save_path)

        self.start_position = self.calculate_start_position(self.centered_focal_plane)

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
        current_pos = self.ref['piezo'].get_position()  # user has set focus
        self.focal_plane_position = current_pos  # save it to come back to this plane at the end of the task

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

    def get_metadata(self):
        """ Get a dictionary containing the metadata in a plain text compatible format. """
        metadata = {}
        metadata['exposure time (s)'] = self.exposure
        metadata['scan step length (um)'] = self.z_step
        metadata['scan total length (um)'] = self.z_step * self.num_z_planes
        metadata['filter'] = 'filtername'  # or without this entry ???
        metadata['number laserlines'] = self.num_laserlines
        for i in range(self.num_laserlines):
            metadata[f'laser line {i+1}'] = self.imaging_sequence[i][0]
            metadata[f'laser intensity {i+1}'] = self.imaging_sequence[i][1]
        # pixel size ???
        return metadata

    def get_fits_metadata(self):
        """ Get a dictionary containing the metadata in a fits header compatible format. """
        metadata = {}
        metadata['EXPOSURE'] = (self.exposure, 'exposure time (s)')
        metadata['Z_STEP'] = (self.z_step, 'scan step length (um)')
        metadata['Z_TOTAL'] = (self.z_step * self.num_z_planes, 'scan total length (um)')
        metadata['CHANNELS'] = (self.num_laserlines, 'number laserlines')
        for i in range(self.num_laserlines):
            metadata[f'LINE{i+1}'] = (self.imaging_sequence[i][0], f'laser line {i+1}')
            metadata[f'INTENS{i+1}'] = (self.imaging_sequence[i][1], f'laser intensity {i+1}')
        return metadata

    def save_metadata_file(self, metadata, path):
        """" Save a txt file containing the metadata dictionary

        :param dict metadata: dictionary containing the metadata
        :param str path: pathname
        """
        with open(path, 'w') as outfile:
            yaml.safe_dump(metadata, outfile, default_flow_style=False)
        self.log.info('Saved metadata to {}'.format(path))

    def get_complete_path(self, path_stem):
        """ Create the complete path based on path_stem given as user parameter,
        such as path_stem/YYYY_MM_DD/001_Scan_samplename/scan_001.tiff
        or path_stem/YYYY_MM_DD/027_Scan_samplename/scan_027.fits

        :param: str path_stem such as E:/DATA
        :return: str complete path (see examples above)
        """
        # check if folder path_stem exists, if not: create it
        if not os.path.exists(path_stem):
            try:
                os.makedirs(path_stem)  # recursive creation of all directories on the path
            except Exception as e:
                self.log.error('Error {0}'.format(e))

        cur_date = datetime.today().strftime('%Y_%m_%d')

        path_stem_date = os.path.join(path_stem, cur_date)

        # count the subdirectories in the directory path (non recursive !) to generate an incremental prefix
        dir_list = [folder for folder in os.listdir(path_stem_date) if os.path.isdir(os.path.join(path_stem_date, folder))]
        number_dirs = len(dir_list)

        prefix=str(number_dirs).zfill(3)
        foldername = f'{prefix}_Scan_{self.sample_name}'

        path = os.path.join(path_stem_date, foldername)

        file_name = f'scan_{prefix}.{self.file_format}'
        complete_path = os.path.join(path, file_name)
        return complete_path
