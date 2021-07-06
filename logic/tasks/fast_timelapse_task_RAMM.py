# -*- coding: utf-8 -*-
"""
Created on Thu June 17 2021

@author: fbarho

This file is an extension to Qudi software
obtained from <https://github.com/Ulm-IQO/qudi/>

Fast timelapse task for the RAMM setup

Config example pour copy-paste:
    FastTimelapseTask:
        module: 'fast_timelapse_task_RAMM'
        needsmodules:
            laser: 'lasercontrol_logic'
            bf: 'brightfield_logic'
            cam: 'camera_logic'
            daq: 'nidaq_6259_logic'
            focus: 'focus_logic'
            roi: 'roi_logic'
        config:
            path_to_user_config: 'C:/Users/sCMOS-1/qudi_data/qudi_task_config_files/fast_timelapse_task_RAMM.yml'

"""
import numpy as np
import os
import yaml
import time
import asyncio
from datetime import datetime
from tqdm import tqdm
from logic.generic_task import InterruptableTask


class Task(InterruptableTask):  # do not change the name of the class. it is always called Task !
    """ This task iterates over all roi given in a file (typically a mosaique) and does an acquisition of a series of
    planes in z direction in multicolor.
    """
    # ==================================================================================================================
    # Generic Task methods
    # ==================================================================================================================

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.directory = None
        self.counter = None
        self.user_param_dict = {}
        self.lightsource_dict = {'BF': 0, '405 nm': 1, '488 nm': 2, '561 nm': 3, '640 nm': 4}
        print('Task {0} added!'.format(self.name))
        self.user_config_path = self.config['path_to_user_config']

    def startTask(self):
        """ """
        self.log.info('started Task')
        # stop all interfering modes on GUIs and disable GUI actions
        self.ref['roi'].disable_tracking_mode()
        self.ref['roi'].disable_roi_actions()

        self.ref['cam'].stop_live_mode()
        self.ref['cam'].disable_camera_actions()

        self.ref['laser'].stop_laser_output()
        self.ref['bf'].led_off()
        self.ref['laser'].disable_laser_actions()  # includes also disabling of brightfield on / off button

        self.ref['focus'].stop_autofocus()
        self.ref['focus'].disable_focus_actions()

        # read all user parameters from config
        self.load_user_parameters()

        # create a directory in which all the data will be saved
        self.directory = self.create_directory(self.save_path)

        # close default FPGA session
        self.ref['laser'].close_default_session()

        # start the session on the fpga using the user parameters
        bitfile = 'C:\\Users\\sCMOS-1\\qudi-cbs\\hardware\\fpga\\FPGA\\FPGA Bitfiles\\FPGAv0_FPGATarget_QudiHiMQPDPID_sHetN0yNJQ8.lvbitx'
        self.ref['laser'].start_task_session(bitfile)
        self.ref['laser'].run_multicolor_imaging_task_session(self.num_z_planes, self.wavelengths, self.intensities, self.num_laserlines, self.exposure)

        # prepare the camera
        self.num_frames = len(self.roi_names) * self.num_z_planes * self.num_laserlines
        self.ref['cam'].prepare_camera_for_multichannel_imaging(self.num_frames, self.exposure, None, None, None)

        # set the active_roi to none to avoid having two active rois displayed
        self.ref['roi'].active_roi = None

        # initialize a counter to iterate over the number of cycles to do
        self.counter = 0

    def runTaskStep(self):
        """ Implement one work step of your task here.
        @return bool: True if the task should continue running, False if it should finish.
        """
        start_time = time.time()

        # create a save path for the current iteration
        cur_save_path = self.get_complete_path(self.directory, self.counter+1)

        # start camera acquisition
        self.ref['cam'].stop_acquisition()  # for safety
        self.ref['cam'].start_acquisition()

        # print(f'time after preparing camera: {time.time()-start_time}')

        # --------------------------------------------------------------------------------------------------------------
        # move to ROI and focus (using autofocus and stop when stable)
        # --------------------------------------------------------------------------------------------------------------
        roi_start_times = []
        for item in self.roi_names:
            # measure the start time for the ROI
            roi_start_time = time.time()
            roi_start_times.append(roi_start_time)

            # autofocus
            self.ref['focus'].start_autofocus(stop_when_stable=True, search_focus=False)

            # go to roi
            self.ref['roi'].set_active_roi(name=item)
            self.ref['roi'].go_to_roi_xy()
            self.ref['roi'].stage_wait_for_idle()

            # ensure that focus is stable here
            busy = self.ref['focus'].autofocus_enabled  # autofocus_enabled is True when autofocus is started and once it is stable is set to false
            counter = 0
            while busy:
                counter += 1
                time.sleep(0.1)
                busy = self.ref['focus'].autofocus_enabled
                if counter > 50:  # maybe increase the counter ?
                    break

            start_position = self.calculate_start_position(self.centered_focal_plane)

            # print(f'time after moving to roi {item} and autofocus: {time.time() - start_time}')

            # ----------------------------------------------------------------------------------------------------------
            # imaging sequence
            # ----------------------------------------------------------------------------------------------------------
            # prepare the daq: set the digital output to 0 before starting the task
            self.ref['daq'].write_to_do_channel(self.ref['daq']._daq.start_acquisition_taskhandle, 1, np.array([0], dtype=np.uint8))

            for plane in range(self.num_z_planes):

                # position the piezo
                position = start_position + plane * self.z_step
                self.ref['focus'].go_to_position(position)
                time.sleep(0.03)

                # send signal from daq to FPGA connector 0/DIO3 ('piezo ready')
                self.ref['daq'].write_to_do_channel(self.ref['daq']._daq.start_acquisition_taskhandle, 1, np.array([1], dtype=np.uint8))
                time.sleep(0.005)
                self.ref['daq'].write_to_do_channel(self.ref['daq']._daq.start_acquisition_taskhandle, 1, np.array([0], dtype=np.uint8))

                # wait for signal from FPGA to DAQ ('acquisition ready')
                fpga_ready = self.ref['daq'].read_di_channel(self.ref['daq']._daq.acquisition_done_taskhandle, 1)[0]
                t0 = time.time()

                while not fpga_ready:
                    time.sleep(0.001)
                    fpga_ready = self.ref['daq'].read_di_channel(self.ref['daq']._daq.acquisition_done_taskhandle, 1)[0]

                    t1 = time.time() - t0
                    if t1 > 1:  # for safety: timeout if no signal received within 1 s
                        self.log.warning('Timeout occurred')
                        break

            self.ref['focus'].go_to_position(start_position)
            # print(f'time after imaging {item}: {time.time() - start_time}')

        # go back to first ROI
        self.ref['roi'].set_active_roi(name=self.roi_names[0])
        self.ref['roi'].go_to_roi_xy()

        # --------------------------------------------------------------------------------------------------------------
        # data saving
        # --------------------------------------------------------------------------------------------------------------
        image_data = self.ref['cam'].get_acquired_data()

        # np.save(cur_save_path, image_data)

        if self.file_format == 'fits':
            metadata = self.get_fits_metadata()
            self.ref['cam']._save_to_fits(cur_save_path, image_data, metadata)
        else:  # use tiff as default format
            self.ref['cam']._save_to_tiff(self.num_frames, cur_save_path, image_data)

        # print(f'time after data saving: {time.time() - start_time}')

        self.counter += 1

        print(f'Finished cycle in {time.time() - start_time} s.')

        return self.counter < self.num_iterations

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
        self.ref['laser'].end_task_session()
        self.ref['laser'].restart_default_session()
        self.log.info('restarted default session')

        # enable gui actions
        # roi gui
        self.ref['roi'].enable_tracking_mode()
        self.ref['roi'].enable_roi_actions()
        # basic imaging gui
        self.ref['cam'].enable_camera_actions()
        self.ref['laser'].enable_laser_actions()
        # focus tools gui
        self.ref['focus'].enable_focus_actions()

        self.log.info('cleanupTask finished')

    # ==================================================================================================================
    # Helper functions
    # ==================================================================================================================

    # ------------------------------------------------------------------------------------------------------------------
    # user parameters
    # ------------------------------------------------------------------------------------------------------------------

    def load_user_parameters(self):
        try:
            with open(self.user_config_path, 'r') as stream:
                self.user_param_dict = yaml.safe_load(stream)

                self.sample_name = self.user_param_dict['sample_name']
                self.exposure = self.user_param_dict['exposure']
                self.centered_focal_plane = self.user_param_dict['centered_focal_plane']
                self.num_z_planes = self.user_param_dict['num_z_planes']
                self.z_step = self.user_param_dict['z_step']  # in um
                self.save_path = self.user_param_dict['save_path']
                self.file_format = self.user_param_dict['file_format']
                self.roi_list_path = self.user_param_dict['roi_list_path']
                self.num_iterations = self.user_param_dict['num_iterations']
                self.time_step = self.user_param_dict['time_step']
                # self.imaging_sequence = self.user_param_dict['imaging_sequence']
                self.imaging_sequence = [{'laserline': '488 nm', 'intensity': 5},
                                         {'laserline': '561 nm', 'intensity': 5},
                                         {'laserline': '561 nm', 'intensity': 5}]

        except Exception as e:  # add the type of exception
            self.log.warning(f'Could not load user parameters for task {self.name}: {e}')

        # establish further user parameters derived from the given ones:
        # create a list of roi names
        self.ref['roi'].load_roi_list(self.roi_list_path)
        # get the list of the roi names
        self.roi_names = self.ref['roi'].roi_names

        # count the number of lightsources
        self.num_laserlines = len(self.imaging_sequence)

        # convert the imaging_sequence given by user into format required by the bitfile
        wavelengths = [self.imaging_sequence[i]['laserline'] for i in range(self.num_laserlines)]
        wavelengths = [self.lightsource_dict[key] for key in wavelengths]
        for i in range(self.num_laserlines, 5):
            wavelengths.append(0)  # must always be a list of length 5: append zeros until necessary length reached
        self.wavelengths = wavelengths

        self.intensities = [self.imaging_sequence[i]['intensity'] for i in range(self.num_laserlines)]
        for i in range(self.num_laserlines, 5):
            self.intensities.append(0)

    def calculate_start_position(self, centered_focal_plane):
        """
        @param bool centered_focal_plane: indicates if the scan is done below and above the focal plane (True)
        or if the focal plane is the bottommost plane in the scan (False)
        """
        current_pos = self.ref['focus'].get_position()  # for tests until we have the autofocus #self.ref['piezo'].get_position()  # lets assume that we are at focus (user has set focus or run autofocus)

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

    # ------------------------------------------------------------------------------------------------------------------
    # file path handling
    # ------------------------------------------------------------------------------------------------------------------

    def create_directory(self, path_stem):
        """ Create the directory (based on path_stem given as user parameter),
        in which the data is saved.
        Example: path_stem/YYYY_MM_DD/001_Timelapse_samplename

        :param: str path_stem: name of the (default) directory for data saving
        :return: str path to the directory where data is saved (see example above)
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
        dir_list = [folder for folder in os.listdir(path_stem_with_date) if
                    os.path.isdir(os.path.join(path_stem_with_date, folder))]
        number_dirs = len(dir_list)

        prefix = str(number_dirs + 1).zfill(3)
        # make prefix accessible to include it in the filename generated in the method get_complete_path
        self.prefix = prefix

        foldername = f'{prefix}_Timelapse_{self.sample_name}'

        path = os.path.join(path_stem_with_date, foldername)

        # create the path  # no need to check if it already exists due to incremental prefix
        try:
            os.makedirs(path)  # recursive creation of all directories on the path
        except Exception as e:
            self.log.error('Error {0}'.format(e))

        return path

    def get_complete_path(self, directory, counter):
        """ Get the complete path to the data file, for the current iteration.

        :param: str directory: path to the data directory
        :param: int counter: number of the current iteration

        :return: str complete_path """

        file_name = f'timelapse_{self.prefix}_step_{str(counter).zfill(2)}.{self.file_format}'
        # file_name = f'timelapse_{self.prefix}_step_{str(counter).zfill(2)}'

        complete_path = os.path.join(directory, file_name)
        return complete_path

    # ------------------------------------------------------------------------------------------------------------------
    # metadata
    # ------------------------------------------------------------------------------------------------------------------

    def get_metadata(self):
        """ Get a dictionary containing the metadata in a plain text compatible format. """
        metadata = {}
        metadata['Sample name'] = self.sample_name
        metadata['Exposure time (s)'] = self.exposure
        metadata['Scan step length (um)'] = self.z_step
        metadata['Scan total length (um)'] = self.z_step * self.num_z_planes
        metadata['Number laserlines'] = self.num_laserlines
        for i in range(self.num_laserlines):
            metadata[f'Laser line {i+1}'] = self.imaging_sequence[i]['laserline']
            metadata[f'Laser intensity {i+1} (%)'] = self.imaging_sequence[i]['intensity']
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
            metadata[f'LINE{i+1}'] = (self.imaging_sequence[i]['laserline'], f'laser line {i+1}')
            metadata[f'INTENS{i+1}'] = (self.imaging_sequence[i]['intensity'], f'laser intensity {i+1}')
        return metadata

    def save_metadata_file(self, metadata, path):
        """" Save a txt or yaml file containing the metadata dictionary

        :param dict metadata: dictionary containing the metadata
        :param str path: pathname
        """
        with open(path, 'w') as outfile:
            yaml.safe_dump(metadata, outfile, default_flow_style=False)
        self.log.info('Saved metadata to {}'.format(path))


# async def save_data(path, array):
#     np.save(path, array)
#
# async def do_nothing():
#     pass
#
# async def main():
#     do_nothing()