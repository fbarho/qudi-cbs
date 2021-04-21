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
        config:
            path_to_user_config: 'C:/Users/sCMOS-1/qudi_data/qudi_task_config_files/ROI_multicolor_scan_task_RAMM.yaml'

"""

import numpy as np
import os
import yaml
from time import sleep, time
from datetime import datetime
from logic.generic_task import InterruptableTask


class Task(InterruptableTask):  # do not change the name of the class. it is always called Task !
    """ This task iterates over all roi given in a file and does an acquisition of a series of planes in z direction
    using a sequence of lightsources for each plane, for each roi.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print('Task {0} added!'.format(self.name))
        self.user_config_path = self.config['path_to_user_config']

    def startTask(self):
        """ """
        self.log.info('started Task')
        # close default FPGA session
        self.ref['fpga'].close_default_session()

        # read all user parameters from config
        self.load_user_parameters()

        # create a directory in which all the data will be saved
        self.directory = self.create_directory(self.save_path)

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
        self.ref['roi'].go_to_roi_xy()
        self.log.info('Moved to {} xy position'.format(self.roi_names[self.roi_counter]))
        # waiting time needed ???
        sleep(1)  # replace maybe by wait for idle

        # create the path for each roi
        # cur_save_path = os.path.join(self.save_path, self.roi_names[self.roi_counter])
        cur_save_path = self.get_complete_path(self.directory, self.roi_names[self.roi_counter])

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
                if t1 > 1:  # for safety: timeout if no signal received within 5 s
                    # self.log.info('Timeout occured')
                    break

        # get acquired data from the camera and save it to file
        image_data = self.ref['cam'].get_acquired_data()

        if self.file_format == 'fits':
            metadata = self.get_fits_metadata()
            self.ref['cam']._save_to_fits(cur_save_path, image_data, metadata)
        else:  # use tiff as default format
            self.ref['cam']._save_to_tiff(self.num_frames, cur_save_path, image_data)
            metadata = self.get_metadata()
            file_path = cur_save_path.replace('tiff', 'txt', 1)
            self.save_metadata_file(metadata, file_path)

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

        # reset piezo position to the initial one
        self.ref['piezo'].go_to_position(self.focal_plane_position)

        # reset the camera to default state
        self.ref['cam'].reset_camera_after_multichannel_imaging()
        # close the fpga session
        self.ref['fpga'].end_task_session()
        self.ref['fpga'].restart_default_session()
        self.log.info('restarted default session')
        # reset stage velocity to default
        self.ref['roi'].set_stage_velocity({'x': 6, 'y': 6})  # 5.74592
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
                self.roi_list_path = self.user_param_dict['roi_list_path']

        except Exception as e:  # add the type of exception
            self.log.warning(f'Could not load user parameters for task {self.name}: {e}')

        # establish further user parameters derived from the given ones
        self.start_position = self.calculate_start_position(self.centered_focal_plane)
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

# --------------------------------------------------------
    def get_metadata(self):
        """ Get a dictionary containing the metadata in a plain text compatible format. """
        metadata = {}
        metadata['Sample name'] = self.sample_name
        metadata['Exposure time (s)'] = self.exposure
        metadata['Scan step length (um)'] = self.z_step
        metadata['Scan total length (um)'] = self.z_step * self.num_z_planes
        # metadata['Filter'] = 'filtername'  # or without this entry ???
        metadata['Number laserlines'] = self.num_laserlines
        for i in range(self.num_laserlines):
            metadata[f'Laser line {i+1}'] = self.imaging_sequence[i][0]
            metadata[f'Laser intensity {i+1} (%)'] = self.imaging_sequence[i][1]
        metadata['x position'] = self.ref['roi'].stage_position[0]
        metadata['y position'] = self.ref['roi'].stage_position[1]
        roi_001_pos = self.ref['roi'].get_roi_position('ROI_001')  # np.ndarray return type
        metadata['ROI_001'] = (float(roi_001_pos[0]), float(roi_001_pos[1]), float(roi_001_pos[2]))
        # pixel size ???
        return metadata

    def get_fits_metadata(self):
        """ Get a dictionary containing the metadata in a fits header compatible format. """
        metadata = {}
        metadata['SAMPLE'] = (self.sample_name, 'sample name')
        metadata['EXPOSURE'] = (self.exposure, 'exposure time (s)')
        metadata['Z_STEP'] = (self.z_step, 'scan step length (um)')
        metadata['Z_TOTAL'] = (self.z_step * self.num_z_planes, 'scan total length (um)')
        metadata['CHANNELS'] = (self.num_laserlines, 'number laserlines')
        for i in range(self.num_laserlines):
            metadata[f'LINE{i+1}'] = (self.imaging_sequence[i][0], f'laser line {i+1}')
            metadata[f'INTENS{i+1}'] = (self.imaging_sequence[i][1], f'laser intensity {i+1}')
        metadata['X_POS'] = (self.ref['roi'].stage_position[0], 'x position')
        metadata['Y_POS'] = (self.ref['roi'].stage_position[1], 'y position')
        # metadata['ROI001'] = (self.ref['roi'].get_roi_position('ROI001'), 'ROI 001 position')
        # pixel size
        return metadata

    def save_metadata_file(self, metadata, path):
        """" Save a txt file containing the metadata dictionary

        :param dict metadata: dictionary containing the metadata
        :param str path: pathname
        """
        with open(path, 'w') as outfile:
            yaml.safe_dump(metadata, outfile, default_flow_style=False)
        self.log.info('Saved metadata to {}'.format(path))

    def create_directory(self, path_stem):
        """ Create the directory (based on path_stem given as user parameter),
        in which the folders for the ROI will be created
        Example: path_stem/YYYY_MM_DD/001_Scan_samplename
        """
        cur_date = datetime.today().strftime('%Y_%m_%d')

        path_stem_with_date = os.path.join(path_stem, cur_date)

        # check if folder path_stem_with_date exists, if not: create it
        if not os.path.exists(path_stem_with_date):
            try:
                os.makedirs(path_stem_with_date)  # recursive creation of all directories on the path
            except Exception as e:
                self.log.error('Error {0}'.format(e))

        # count the subdirectories in the directory path (non recursive !) to generate an incremental prefix
        dir_list = [folder for folder in os.listdir(path_stem_with_date) if os.path.isdir(os.path.join(path_stem_with_date, folder))]
        number_dirs = len(dir_list)

        prefix=str(number_dirs+1).zfill(3)
        # make prefix accessible to include it in the filename generated in the method get_complete_path
        self.prefix = prefix

        foldername = f'{prefix}_Scan_{self.sample_name}'

        path = os.path.join(path_stem_with_date, foldername)

        # create the path  # no need to check if it already exists due to incremental prefix
        try:
            os.makedirs(path)  # recursive creation of all directories on the path
        except Exception as e:
            self.log.error('Error {0}'.format(e))

        return path

    def get_complete_path(self, directory, roi_number):
        path = os.path.join(directory, roi_number)

        if not os.path.exists(path):
            try:
                os.makedirs(path)  # recursive creation of all directories on the path
            except Exception as e:
                self.log.error('Error {0}'.format(e))

        file_name = f'scan_{self.prefix}_{roi_number}.{self.file_format}'
        complete_path = os.path.join(path, file_name)
        return complete_path

#for Hi-M experiment
    # def get_complete_path(self, path_stem, roi_number, probe_number):
    #     """ Create the complete path based on path_stem given as user parameter,
    #     such as path_stem/YYYY_MM_DD/001_Scan_samplename/ROI007/RT17/scan_001_RT17_ROI007.tiff
    #     or path_stem/YYYY_MM_DD/027_Scan_samplename/ROI002/DAPI/scan_027_DAPI_ROI002.fits
    #
    #     :param: str path_stem such as E:/DATA
    #     :return: str complete path (see examples above)
    #     """
    #     # check if folder path_stem exists, if not: create it
    #     if not os.path.exists(path_stem):
    #         try:
    #             os.makedirs(path_stem)  # recursive creation of all directories on the path
    #         except Exception as e:
    #             self.log.error('Error {0}'.format(e))
    #
    #     cur_date = datetime.today().strftime('%Y_%m_%d')
    #
    #     path_stem_date = os.path.join(path_stem, cur_date)
    #
    #     # count the subdirectories in the directory path (non recursive !) to generate an incremental prefix
    #     dir_list = [folder for folder in os.listdir(path_stem_date) if os.path.isdir(os.path.join(path_stem_date, folder))]
    #     number_dirs = len(dir_list)
    #
    #     prefix=str(number_dirs).zfill(3)
    #     foldername = f'{prefix}_Scan_{self.sample_name}'
    #
    #     path = os.path.join(path_stem_date, foldername, roi_number, probe_number)
    #
    #     file_name = f'scan_{prefix}_{probe_number}_{roi_number}.{self.file_format}'
    #     complete_path = os.path.join(path, file_name)
    #     return complete_path