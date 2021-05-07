# -*- coding: utf-8 -*-
"""
Created on Tue May 04 2021

@author: fbarho

This file is an extension to Qudi software
obtained from <https://github.com/Ulm-IQO/qudi/>

Hi-M dummy Experiment

Config example pour copy-paste:
    HiMTask:
        module: 'HiM_task_dummy'
        needsmodules:
            laser: 'lasercontrol_logic'
            cam: 'camera_logic'
            focus: 'focus_logic'
            roi: 'roi_logic'
            valves: 'valve_logic'
            pos: 'positioning_logic'
            flow: 'flowcontrol_logic'
        config:
            path_to_user_config: 'home/barho/qudi_files/qudi_task_config_files/hi_m_task_RAMM.yaml'
"""
import yaml
from datetime import datetime
import numpy as np
import os
import time
from logic.generic_task import InterruptableTask


class Task(InterruptableTask):  # do not change the name of the class. it is always called Task !
    """ This task iterates over all roi given in a file and does an acquisition of a series of planes in z direction
    using a sequence of lightsources for each plane, for each roi.
    """
    # ===============================================================================================================
    # Generic Task methods
    # ===============================================================================================================

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
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
        self.ref['laser'].disable_laser_actions()
        # brightfield off in case it is on ?? then connection to brightfield logic needs to be established as well

        self.ref['valves'].disable_valve_positioning()
        self.ref['flow'].disable_pressure_setting()
        self.ref['pos'].disable_positioning_actions()

        # control if experiment can be started : origin defined in position logic ?
        if not self.ref['pos'].origin:
            self.log.warning('No position 1 defined for injections. Experiment can not be started. Please define position 1')
            return

        # set stage velocity
        self.ref['roi'].set_stage_velocity({'x': 1, 'y': 1})

        # read all user parameters from config
        self.load_user_parameters()

        # create a directory in which all the data will be saved
        self.directory = self.create_directory(self.save_path)

        # prepare the camera
        self.num_frames = self.num_z_planes * self.num_laserlines
        self.ref['cam'].prepare_camera_for_multichannel_imaging(self.num_frames, self.exposure, None, None, None)

        # initialize a counter to iterate over the number of probes to inject
        self.probe_counter = 0


    def runTaskStep(self):
        """ Implement one work step of your task here.
        @return bool: True if the task should continue running, False if it should finish.
        """
        # go directly to cleanupTask if position 1 is not defined
        if not self.ref['pos'].origin:
            return False

        # info message
        self.probe_counter += 1
        print(f'Probe number {self.probe_counter}')
        self.log.info(f'Probe number {self.probe_counter}')

        # position the needle in the probe
        self.ref['pos'].start_move_to_target(self.probe_counter)


        # ------------------------------------------------------------------------------------------
        # Hybridization
        # ------------------------------------------------------------------------------------------
        # position the valves for hybridization sequence
        self.ref['valves'].set_valve_position('b', 2)  # RT rinsing valve: inject probe
        self.ref['valves'].wait_for_idle()
        self.ref['valves'].set_valve_position('c', 2)  # Syringe valve: towards pump
        self.ref['valves'].wait_for_idle()

        # iterate over the steps in the hybridization sequence
        for step in range(len(self.hybridization_list)):
            print(f'Hybridisation step {step+1}')
            self.log.info(f'Hybridisation step {step+1}')

            if self.hybridization_list[step]['product'] is not None:  # an injection step
                # set the 8 way valve to the position corresponding to the product
                product = self.hybridization_list[step]['product']
                valve_pos = self.buffer_dict[product]
                self.ref['valves'].set_valve_position('a', valve_pos)
                self.ref['valves'].wait_for_idle()

                print(f'Injection of {product} ... ')
                self.log.info(f'Injection of {product} ... ')
                time.sleep(1)

                # add here simulated data for pressure value and total volume

            else:  # an incubation step
                t = self.hybridization_list[step]['time']
                print(f'Incubation time.. {t} s')
                self.log.info(f'Incubation time.. {t} s')
                self.ref['valves'].set_valve_position('c', 1)
                self.ref['valves'].wait_for_idle()
                time.sleep(self.hybridization_list[step]['time'])
                # maybe it is better to split into small intervals to keep the thread responsive ?????
                self.ref['valves'].set_valve_position('c', 2)
                self.ref['valves'].wait_for_idle()
                print('Incubation time finished')
                self.log.info('Incubation time finished')

        # set valves to default positions
        self.ref['valves'].set_valve_position('a', 1)  # 8 way valve
        self.ref['valves'].wait_for_idle()
        self.ref['valves'].set_valve_position('b', 1)  # RT rinsing valve: Rinse needle
        self.ref['valves'].wait_for_idle()
        self.ref['valves'].set_valve_position('c', 1)  # Syringe valve: towards syringe
        self.ref['valves'].wait_for_idle()
        # Hybridization finished ---------------------------------------------------------------------------------------

        # ------------------------------------------------------------------------------------------
        # Imaging for all ROI
        # ------------------------------------------------------------------------------------------
        # iterate over all ROIs
        for item in self.roi_names:
            # create the save path for each roi ------------------------------------------------------------------------
            cur_save_path = self.get_complete_path(self.directory, item, self.probe_dict[self.probe_counter])

            # move to roi ----------------------------------------------------------------------------------------------
            self.ref['roi'].active_roi = None
            self.ref['roi'].set_active_roi(name=item)
            self.ref['roi'].go_to_roi()
            self.log.info('Moved to {}'.format(item))
            time.sleep(1)  # replace maybe by wait for idle

            # autofocus ------------------------------------------------------------------------------------------------
            # self.ref['focus'].search_focus()
            reference_position = self.ref['focus'].get_position() + np.random.normal() # save it to go back to this plane after imaging
            # for simulatied task only
            self.ref['focus'].go_to_position(reference_position)
            start_position = self.calculate_start_position(self.centered_focal_plane)

            # imaging sequence -----------------------------------------------------------------------------------------
            # self.ref['cam'].stop_acquisition()   # for safety
            # self.ref['cam'].start_acquisition()

            # iterate over all planes in z
            for plane in range(self.num_z_planes):
                print(f'plane number {plane + 1}')

                # position the piezo
                position = start_position + plane * self.z_step
                self.ref['focus'].go_to_position(position)
                print(f'target position: {position} um')
                time.sleep(0.03)
                cur_pos = self.ref['focus'].get_position()
                print(f'current position: {cur_pos} um')

            self.ref['focus'].go_to_position(reference_position)

            # data handling --------------------------------------------------------------------------------------------
            image_data = np.random.normal(size=(self.num_frames, 125, 125))  # self.ref['cam'].get_acquired_data()

            if self.file_format == 'fits':
                metadata = {} # self.get_fits_metadata()
                self.ref['cam']._save_to_fits(cur_save_path, image_data, metadata)
            else:  # use tiff as default format
                self.ref['cam']._save_to_tiff(self.num_frames, cur_save_path, image_data)
                metadata = self.get_metadata()
                file_path = cur_save_path.replace('tiff', 'txt', 1)
                self.save_metadata_file(metadata, file_path)
        # Imaging (for all ROIs) finished ------------------------------------------------------------------------------

        # ------------------------------------------------------------------------------------------
        # Photobleaching
        # ------------------------------------------------------------------------------------------
        # position the valves for photobleaching sequence
        self.ref['valves'].set_valve_position('b', 2)  # RT rinsing valve: inject probe
        self.ref['valves'].wait_for_idle()
        # to add: do the rinsing of the needle

        self.ref['valves'].set_valve_position('c', 2)  # Syringe valve: towards pump
        self.ref['valves'].wait_for_idle()

        # iterate over the steps in the photobleaching sequence
        for step in range(len(self.photobleaching_list)):
            print(f'Photobleaching step {step+1}')
            self.log.info(f'Photobleaching step {step+1}')

            if self.photobleaching_list[step]['product'] is not None:  # an injection step
                # set the 8 way valve to the position corresponding to the product
                product = self.photobleaching_list[step]['product']
                valve_pos = self.buffer_dict[product]
                self.ref['valves'].set_valve_position('a', valve_pos)
                self.ref['valves'].wait_for_idle()

                print(f'Injection of {product} ... ')
                self.log.info(f'Injection of {product} ... ')
                time.sleep(1)
                # add here simulated data for pressure value and total volume

            else:  # an incubation step
                t = self.photobleaching_list[step]['time']
                print(f'Incubation time.. {t} s')
                self.log.info(f'Incubation time .. {t} s')
                self.ref['valves'].set_valve_position('c', 1)
                self.ref['valves'].wait_for_idle()
                time.sleep(self.photobleaching_list[step]['time'])
                # maybe it is better to split into small intervals to keep the thread responsive ?????
                self.ref['valves'].set_valve_position('c', 2)
                self.ref['valves'].wait_for_idle()
                print('Incubation time finished')
                self.log.info('Incubation time finished')

        # set valves to default positions
        self.ref['valves'].set_valve_position('a', 1)  # 8 way valve
        self.ref['valves'].wait_for_idle()
        self.ref['valves'].set_valve_position('b', 1)  # RT rinsing valve: Rinse needle
        self.ref['valves'].wait_for_idle()
        self.ref['valves'].set_valve_position('c', 1)  # Syringe valve: towards syringe
        self.ref['valves'].wait_for_idle()
        # Photobleaching finished --------------------------------------------------------------------------------------

        return self.probe_counter < len(self.probe_dict)

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

        # reset stage velocity to default
        self.ref['roi'].set_stage_velocity({'x': 6, 'y': 6})  # 5.74592

        # enable gui actions
        # roi gui
        self.ref['roi'].enable_tracking_mode()
        self.ref['roi'].enable_roi_actions()
        # basic imaging gui
        self.ref['cam'].enable_camera_actions()
        self.ref['laser'].enable_laser_actions()
        self.ref['valves'].enable_valve_positioning()
        self.ref['flow'].enable_pressure_setting()
        self.ref['pos'].enable_positioning_actions()

        self.log.info('cleanupTask finished')

    # ===============================================================================================================
    # Helper functions
    # ===============================================================================================================

    # ------------------------------------------------------------------------------------------
    # user parameters
    # ------------------------------------------------------------------------------------------

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
                self.injections_path = self.user_param_dict['injections_path']

        except Exception as e:  # add the type of exception
            self.log.warning(f'Could not load user parameters for task {self.name}: {e}')

        # establish further user parameters derived from the given ones
        # load rois from file and create a list ------------------------------------------------------------------------
        self.ref['roi'].load_roi_list(self.roi_list_path)
        self.roi_names = self.ref['roi'].roi_names

        # imaging ------------------------------------------------------------------------------------------------------
        self.num_laserlines = len(self.imaging_sequence)
        # not needed for dummy him task (maybe for metadata..)
        self.wavelengths = [self.imaging_sequence[i][0] for i, item in enumerate(self.imaging_sequence)]
        self.intensities = [self.imaging_sequence[i][1] for i, item in enumerate(self.imaging_sequence)]

        # injections ---------------------------------------------------------------------------------------------------
        self.load_injection_parameters()

    def load_injection_parameters(self):
        """ """
        with open(self.injections_path, 'r') as stream:
            documents = yaml.safe_load(stream)  # yaml.full_load when yaml package updated
            buffer_dict = documents['buffer']  #  example {3: 'Buffer3', 7: 'Probe', 8: 'Buffer8'}
            self.probe_dict = documents['probes']
            self.hybridization_list = documents['hybridization list']
            self.photobleaching_list = documents['photobleaching list']

        # invert the buffer dict to address the valve by the product name as key
        self.buffer_dict = dict([(value, key) for key, value in buffer_dict.items()])

    def calculate_start_position(self, centered_focal_plane):
        """
        @param bool centered_focal_plane: indicates if the scan is done below and above the focal plane (True) or if the focal plane is the bottommost plane in the scan (False)
        """
        current_pos = self.ref['focus'].get_position()

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

    # ------------------------------------------------------------------------------------------
    # file path handling
    # ------------------------------------------------------------------------------------------
    def create_directory(self, path_stem):
        """ Create the directory (based on path_stem given as user parameter),
        in which the folders for the ROI will be created
        Example: path_stem/YYYY_MM_DD/001_HiM_samplename
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

        foldername = f'{prefix}_HiM_{self.sample_name}'

        path = os.path.join(path_stem_with_date, foldername)

        # create the path  # no need to check if it already exists due to incremental prefix
        try:
            os.makedirs(path)  # recursive creation of all directories on the path
        except Exception as e:
            self.log.error('Error {0}'.format(e))

        return path

    def get_complete_path(self, directory, roi_number, probe_number):
        path = os.path.join(directory, roi_number, probe_number)

        if not os.path.exists(path):
            try:
                os.makedirs(path)  # recursive creation of all directories on the path
            except Exception as e:
                self.log.error('Error {0}'.format(e))

        file_name = f'scan_{self.prefix}_{probe_number}_{roi_number}.{self.file_format}'

        complete_path = os.path.join(path, file_name)
        return complete_path

    # ------------------------------------------------------------------------------------------
    # metadata
    # ------------------------------------------------------------------------------------------
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
        # to check where the problem comes from :
        # metadata['x position'] = self.ref['roi'].stage_position[0]
        # metadata['y position'] = self.ref['roi'].stage_position[1]
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


# to do: validate metadata saving
# use this to explore how to handle the live / laser on / tracking mode states for the other guis if activated
# use for integration with bokeh app

