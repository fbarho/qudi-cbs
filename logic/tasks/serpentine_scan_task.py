# -*- coding: utf-8 -*-
"""
Tests on implementing a serpentine scan task using the predefined task structure of qudi.


Config example pour copy-paste:
    serpentineScanTask:
        module: 'serpentine_scan_task'
        needsmodules:
            roi: 'roi_logic'
            daq: 'daq_ao_logic'
            camera: 'camera_logic'
            filter: 'filterwheel_logic'
        config:
            path_to_user_config: '/home/barho/qudi-cbs-user-configs/serpentine_scan_task_config.json'
"""

from logic.generic_task import InterruptableTask
import time
import json
from datetime import datetime
import os

class Task(InterruptableTask): # do not change the name of the class. it is always called Task !
    """ This task does an acquisition of a series of images on the ROIs defined by the user

    current version: allows to iterate over 1 ROI list
    using one light source with intensity specified in user config
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print('Task {0} added!'.format(self.name))
        self.user_config_path = self.config['path_to_user_config']
        self.laser_allowed = True
        self.log.info('Task {0} using the configuration at {1}'.format(self.name, self.user_config_path))


    def startTask(self):
        """ """
        self._load_user_parameters()

        # control the config : laser allowed for given filter ?
        self.laser_allowed = self._control_user_parameters()

        if not self.laser_allowed:
            self.log.warning('Task aborted. Please specify a valid filter / laser combination')
            return
        else:
            # load a specified list in the ROI module
            self.ref['roi'].load_roi_list(self.roi_path)
            self.log.info('loaded roi list')

            # get the list of the roi names
            self.roi_names = self.ref['roi'].roi_names
            #self.log.info(self.roi_names)

            # initialize the counter that will be used to iterate over the ROIs
            self.counter = 0  # counter for the number of task steps

            # set the filter to the specified position
            self.ref['filter'].set_position(self.filter_pos)

            # indicate the intensity values to be applied
            self.ref['daq'].update_intensity_dict(self.lightsource, self.intensity)

            # set the active_roi to none # to avoid having two active rois displayed
            self.ref['roi'].active_roi = None


    def runTaskStep(self):
        """ Implement one work step of your task here.
        @return bool: True if the task should continue running, False if it should finish.
        """
        if not self.laser_allowed:
            return False
        else:
            # go to roi
            self.ref['roi'].set_active_roi(name=self.roi_names[self.counter])
            self.ref['roi'].go_to_roi()
            self.log.info('Moved to {}'.format(self.roi_names[self.counter]))

            # create a folder for each roi
            cur_save_path = os.path.join(self.save_path, self.roi_names[self.counter])

            # switch the laser on
            self.ref['daq'].apply_voltage()

            if self.n_frames == 1:  # single image acquisition
                # take an image and save it -> it is needed to first call start_single_acquisition otherwise no data is available
                self.ref['camera'].start_single_acquistion() # mind the typo !!
                self.ref['camera'].save_last_image(cur_save_path, '.tiff')
                # create the path for metadata file
                complete_path = self.ref['camera']._create_generic_filename(cur_save_path, '_Image', 'parameters', '.txt', addfile=True)

            else:  # n_frames > 1: movie acquisition
                self.ref['camera'].save_video(cur_save_path, self.n_frames, self.display, emit_signal=False)
                # create the path for metadata file
                complete_path = self.ref['camera']._create_generic_filename(cur_save_path, '_Movie', 'parameters', '.txt', addfile=True)

            # switch laser off
            self.ref['daq'].voltage_off()
            # in a following version the laser on off switching should be triggered by the camera. but this actually goes into the daq_ao_logic module ..

            # # save the metadata
            metadata = self._create_metadata_dict()
            with open(complete_path, 'w') as file:
                file.write(str(metadata))
            self.log.info('Saved metadata to {}'.format(complete_path))

            self.counter += 1
            return self.counter < len(self.roi_names) # continue when there are still rois left in the list


    def pauseTask(self):
        """ """
        self.log.info('pauseTask called')

    def resumeTask(self):
        """ """
        self.log.info('resumeTask called')

    def cleanupTask(self):
        """ """
        self.ref['daq'].voltage_off()  # as security
        self.ref['daq'].reset_intensity_dict()
        self.log.info('cleanupTask called')

    def _load_user_parameters(self):
        """ this function is called from startTask() to load the parameters given in a specified format by the user

        specify only the path to the user defined config in the (global) config of the experimental setup

        user must specify the following dictionary (here with example entries):
            roilist_path: '/home/barho/roilists/mylist.json'
            save_path: '/home/barho/myfolder'
            lightsource: 'laser1'
            intensity: 10
            filter_pos: 2
            n_frames: 5
        """
        try:
            with open(self.user_config_path, 'r') as file:
                self.user_param_dict = json.load(file)

            self.roi_path = self.user_param_dict['roilist_path']
            self.save_path = self.user_param_dict['save_path']
            self.lightsource = self.user_param_dict['lightsource']
            self.intensity = self.user_param_dict['intensity']
            self.filter_pos = self.user_param_dict['filter_pos']
            self.n_frames = self.user_param_dict['n_frames']
            self.display = bool(self.user_param_dict['activate_display'])

            self.log.info('loaded user parameters')

        except:
            self.log.warning('Could not load user parameters for task {}'.format(self.name))

    def _control_user_parameters(self):
        """ this function checks if the specified laser is allowed given the filter setting
        @return bool: valid ?"""
        filterpos = self.filter_pos
        key = 'filter{}'.format(filterpos)
        filterdict = self.ref['filter'].get_filter_dict()
        laserlist = filterdict[key]['lasers']  # returns a list of boolean elements, laser allowed ?
        # this part should be improved using a correct addressing of the element
        laser = self.lightsource
        laser_index = int(laser.strip('laser'))-1
        ##########
        return laserlist[laser_index]


    def _create_metadata_dict(self):
        """ create a dictionary containing the metadata

        this is a copy of the function available in basic_gui. the values are addressed slightly differently via the refs"""
        metadata = {}
        metadata['timestamp'] = datetime.now().strftime('%m-%d-%Y, %H:%M:%S')
        filterpos = self.ref['filter'].get_position()
        filterdict = self.ref['filter'].get_filter_dict()
        label = 'filter{}'.format(filterpos)
        metadata['filter'] = filterdict[label]['name']
        metadata['gain'] = self.ref['camera'].get_gain()
        metadata['exposuretime (s)'] = self.ref['camera'].get_exposure()
        intensity_dict = self.ref['daq']._intensity_dict
        keylist = [key for key in intensity_dict if intensity_dict[key] != 0]
        laser_dict = self.ref['daq'].get_laser_dict()
        metadata['laser'] = [laser_dict[key]['wavelength'] for key in keylist]
        metadata['intensity (%)'] = [intensity_dict[key] for key in keylist]
        if self.ref['camera'].has_temp:
            metadata['sensor temperature'] = self.ref['camera'].get_temperature()
        else:
            metadata['sensor temperature'] = 'Not available'
        return metadata


## to do:
# improve the way how the laser filter pair is controlled before the start
# define how to pause / resume / stop the task




