# -*- coding: utf-8 -*-
"""
Created on Tue Feb 2 2021

@author: fbarho

This file is an extension to Qudi software
obtained from <https://github.com/Ulm-IQO/qudi/>

Task to perform multicolor imaging

Config example pour copy-paste:
    MulticolorImagingTask:
        module: 'multicolor_imaging_task'
        needsmodules:
            camera: 'camera_logic'
            daq: 'daq_ao_logic'
            filter: 'filterwheel_logic'
        config:
            path_to_user_config: '/home/barho/qudi-cbs-user-configs/multichannel_imaging_task.json'
"""

from logic.generic_task import InterruptableTask
import json
from datetime import datetime
import os
import numpy as np


class Task(InterruptableTask):  # do not change the name of the class. it is always called Task !
    """ This task does an acquisition of a series of images from different channels or using different intensities
    """

    filter_pos = None
    imaging_sequence = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print('Task {0} added!'.format(self.name))
        # self.laser_allowed = False
        # self.user_config_path = self.config['path_to_user_config']
        # self.log.info('Task {0} using the configuration at {1}'.format(self.name, self.user_config_path))

    def startTask(self):
        """ """
        self._load_user_parameters()

        # # control the config : laser allowed for given filter ?
        # self.laser_allowed = self._control_user_parameters()
        #
        # if not self.laser_allowed:
        #     self.log.warning('Task aborted. Please specify a valid filter / laser combination')
        #     return

        # else:
        # set the filter to the specified position
        self.ref['filter'].set_position(self.filter_pos)
        # use only one filter. do not allow changing filter because this will be too slow

        # prepare the camera
        self.ref['camera'].set_trigger_mode('EXTERNAL')

        # set the exposure time
        self.ref['camera'].set_exposure(0.05)   # to be read from user config

        # initialize the data structure
        self.image_data = np.empty((4, 512, 512))  # to be read from camera and config (nb channels)


    def runTaskStep(self):
        """ Implement one work step of your task here.
        @return bool: True if the task should continue running, False if it should finish.
        """
        # this task only has one step until a data set is prepared and saved (but loops over the channels)
        for i in range(len(self.imaging_sequence)):
            # prepare the output value for the specified channel
            self.ref['daq'].update_intensity_dict(self.imaging_sequence[i][0], self.imaging_sequence[i][1])

            # start the acquisition. Camera waits for trigger
            self.ref['camera'].start_single_acquistion()   # watch out for the typo
            # or is it needed to rewrite another method so that we avoid switching so often between the acquisition modes ?
            # because start_single_acquisition will first set to single_scan and then back to run till abort when finished

            # switch the laser on and send the trigger to the camera
            self.ref['daq'].apply_voltage()

            # laser off or just apply_voltage for a given duration ??


            # data handling: we want to add the images to create a 3D numpy array
            # then we can call one of the methods to save this 3D array to fits or tiff using the methods from the camera logic
            image_data = self.ref['camera'].get_last_image()

            self.image_data[i,:,:] = image_data

        # define save path
        path = '/home/barho/images/testmulticolorstack.fits'
        # retrieve the metadata
        metadata = {'info1': 1, 'info2': 2}

        # allow to specify file format and put in if structure
        self.ref['camera']._save_to_fits(path, self.image_data, metadata)

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
            save_path: '/home/barho/myfolder'
            num_planes: 15
            step: 5  # in um
            lightsource: 'laser1'
            intensity: 10
            filter_pos: 2
            n_frames: 5
            activate_display: 1
        """
        self.filter_pos = 1
        # a dictionary is not a good option for the imaging sequence. is a list better ? preserve order (dictionary would do as well), allows repeated entries
        # use a list with tuples, or a a list with dicts ?)
        self.imaging_sequence = [('laser1', 10), ('laser1', 20), ('laser3', 10)]
        # or rather
        # self.imaging_sequence = [('405nm', 10), ('405nm', 20), ('512nm', 10)]


        # try:
        #     with open(self.user_config_path, 'r') as file:
        #         self.user_param_dict = json.load(file)
        #
        #     self.save_path = self.user_param_dict['save_path']
        #
        #     self.log.info('loaded user parameters')
        # except:
        #     self.log.warning('Could not load user parameters for task {}'.format(self.name))

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







