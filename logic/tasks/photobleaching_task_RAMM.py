# -*- coding: utf-8 -*-
"""
Created on Friday April 2 2021

@author: fbarho

This file is an extension to Qudi software
obtained from <https://github.com/Ulm-IQO/qudi/>

Task iterating over a list of ROIs illuminating with several laser colors (no imaging)

Config example pour copy-paste:
    PhotobleachingTask:
        module: 'photobleaching_task_RAMM'
        needsmodules:
            fpga: 'lasercontrol_logic'
            roi: 'roi_logic'
        config:
            path_to_user_config: 'C:/Users/sCMOS-1/qudi_data/qudi_task_config_files/photobleaching_task_RAMM.yaml'
"""


import numpy as np
import os
import yaml
from time import sleep, time
from logic.generic_task import InterruptableTask


class Task(InterruptableTask):  # do not change the name of the class. it is always called Task !
    """ This task iterates over all roi given in a file and illuminates this position with a sequence of lasers.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print('Task {0} added!'.format(self.name))
        self.user_config_path = self.config['path_to_user_config']

    def startTask(self):
        """ """
        self.log.info('started Task')

        # read all user parameters from config
        self.load_user_parameters()

        # set stage velocity
        self.ref['roi'].set_stage_velocity({'x': 1, 'y': 1})

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

        # activate lightsources
        for item in self.imaging_sequence:
            self.ref['fpga'].apply_voltage_single_channel(item[1], item[0])  #  param: intensity, channel
            sleep(self.illumination_time)
            self.ref['fpga'].apply_voltage_single_channel(0, item[0])

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
        # reset stage velocity to default
        self.ref['roi'].set_stage_velocity({'x': 6, 'y': 6})  # 5.74592

        # for safety, make sure all lasers are off
        for item in self.imaging_sequence:
            self.ref['fpga'].apply_voltage_single_channel(0, item[0])

        self.log.info('cleanupTask finished')

    def load_user_parameters(self):
        # define user parameters  # to be read from config later
        # self.illumination_time = 1  # in s
        # imaging_sequence = [('488 nm', 20), ('561 nm', 10), ('640 nm', 10)]
        # self.roi_list_path = 'C:\\Users\\sCMOS-1\\Desktop\\roilist1.json'

        try:
            with open(self.user_config_path, 'r') as stream:
                self.user_param_dict = yaml.safe_load(stream)

                self.illumination_time = self.user_param_dict['illumination_time']
                imaging_sequence = self.user_param_dict['imaging_sequence']
                self.roi_list_path = self.user_param_dict['roi_list_path']

        except Exception as e:  # add the type of exception
            self.log.warning(f'Could not load user parameters for task {self.name}: {e}')

        # establish further user parameters derived from the given ones:
        # create a list of roi names
        self.ref['roi'].load_roi_list(self.roi_list_path)
        # get the list of the roi names
        self.roi_names = self.ref['roi'].roi_names

        # convert the imaging_sequence given by user into format required for function call
        lightsource_dict = {'405 nm': '405', '488 nm': '488', '561 nm': '561', '640 nm': '640'}
        self.imaging_sequence = [(lightsource_dict[item[0]], item[1]) for item in imaging_sequence]
