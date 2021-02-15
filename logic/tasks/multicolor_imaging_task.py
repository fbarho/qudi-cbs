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
import time
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

        # prepare the camera  # this version is quite specific for andor camera -- implement compatibility later on
        self.ref['camera'].set_acquisition_mode('SINGLE_SCAN')
        self.ref['camera'].set_trigger_mode('EXTERNAL')  
        # add eventually other settings that may be read from user config .. frame transfer etc. 

        # set the exposure time
        self.ref['camera'].set_exposure(self.exposure)   # to be read from user config instead

        # initialize the data structure
        width, height = self.ref['camera'].get_size()
        frames = len(self.imaging_sequence)
        self.image_data = np.empty((frames, height, width))  
        
        # initialize the digital output channel for trigger
        self.ref['daq'].set_up_do_channel()


    def runTaskStep(self):
        """ Implement one work step of your task here.
        @return bool: True if the task should continue running, False if it should finish.
        """
        # this task only has one step until a data set is prepared and saved (but loops over the channels)
        for i in range(len(self.imaging_sequence)):
            # prepare the output value for the specified channel
            self.ref['daq'].update_intensity_dict(self.imaging_sequence[i][0], self.imaging_sequence[i][1])
            # self.log.info(f'will apply {self.imaging_sequence[i][1]/10} volts to channel {self.imaging_sequence[i][0]}')

            # start the acquisition. Camera waits for trigger
            self.ref['camera'].start_acquisition()   
            # switch the laser on and send the trigger to the camera
            self.ref['daq'].apply_voltage()
            self.ref['daq'].send_trigger()  
            # self.ref['camera'].wait_for_acquisition()   # wait for acquisition event  # when using this fucntion and trigger is not received by camera this makes program run till infinity
            time.sleep(self.exposure)
            # eventually read fire signal of camera and switch of when low signal
#            if self.ref['daq'].read_ai() == 0:
#                self.ref['daq'].voltage_off()
            self.ref['daq'].voltage_off()
            

            # data handling: we want to add the images to create a 3D numpy array
            # then we can call one of the methods to save this 3D array to fits or tiff using the methods from the camera logic
            image_data = self.ref['camera'].get_acquired_data()

            self.image_data[i,:,:] = image_data

        # define save path
        path = 'C:\\Users\\admin\\imagetest\\testmulticolorstack'
        complete_path = self.ref['camera']._create_generic_filename(path, 'Stack', 'testimg', 'fits', False)
        # retrieve the metadata
        metadata = {'info1': 1, 'info2': 2}

        # allow to specify file format and put in if structure
        self.ref['camera']._save_to_fits(complete_path, self.image_data, metadata)
        
        return False

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
        self.ref['daq'].close_do_task()
        self.ref['camera'].abort_acquisition()
        self.ref['camera'].set_trigger_mode('INTERNAL') 
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
        laser_dict = self.ref['daq'].get_laser_dict()
        self.filter_pos = 1
        self.exposure = 0.05  # in s
        # a dictionary is not a good option for the imaging sequence. is a list better ? preserve order (dictionary would do as well), allows repeated entries
        self.imaging_sequence = [('512 nm', 10), ('512 nm', 5), ('512 nm', 10)]
        # now we need to access the corresponding labels
        imaging_sequence = [(*get_entry_nested_dict(laser_dict, self.imaging_sequence[i][0], 'label'), self.imaging_sequence[i][1]) for i in range(len(self.imaging_sequence))]
        self.log.info(imaging_sequence)
        self.imaging_sequence = imaging_sequence
        # new format should be self.imaging_sequence = [('laser2', 10), ('laser2', 20), ('laser3', 10)]



        # try:
        #     with open(self.user_config_path, 'r') as file:
        #         self.user_param_dict = json.load(file)
        #
        #     self.save_path = self.user_param_dict['save_path']
        #
        #     self.log.info('loaded user parameters')
        # except:
        #     self.log.warning('Could not load user parameters for task {}'.format(self.name))

#    def _control_user_parameters(self):
#        """ this function checks if the specified laser is allowed given the filter setting
#        @return bool: valid ?"""
#        filterpos = self.filter_pos
#        key = 'filter{}'.format(filterpos)
#        filterdict = self.ref['filter'].get_filter_dict()
#        laserlist = filterdict[key]['lasers']  # returns a list of boolean elements, laser allowed ?
#        # this part should be improved using a correct addressing of the element
#        laser = self.lightsource
#        laser_index = int(laser.strip('laser'))-1
#        ##########
#        return laserlist[laser_index]




def get_entry_nested_dict(nested_dict, val, entry):
    """ helper function that searches for 'val' as value in a nested dictionary and returns the corresponding value in the category 'entry'
    example: search in laser_dict (nested_dict) for the label (entry) corresponding to a given wavelength (val)
    search in filter_dict (nested_dict) for the label (entry) corresponding to a given filter position (val)

    @param: dict nested dict
    @param: val: any data type, value that is searched for in the dictionary
    @param: str entry: key in the inner dictionary whose value needs to be accessed

    note that this function is not the typical way how dictionaries should be used. due to the unambiguity in the dictionaries used here,
    it can however be useful to try to find a key given a value.
    so in practical cases, list will consist of a single element only. """
    list = []
    for outer_key in nested_dict:
        item = [nested_dict[outer_key][entry] for inner_key, value in nested_dict[outer_key].items() if val == value]
        if item != []:
            list.append(*item)
    return list
