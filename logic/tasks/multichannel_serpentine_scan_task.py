# -*- coding: utf-8 -*-
"""
Task allowing to iterate over an ROI list taking images in several channels (sequentially)


Config example pour copy-paste:
    multichannelSerpentineScanTask:
        module: 'multichannel_serpentine_scan_task'
        needsmodules:
            roi: 'roi_logic'
            daq: 'daq_ao_logic'
            camera: 'camera_logic'
            filter: 'filterwheel_logic'
        config:
            path_to_user_config: '/home/barho/multichannel_scan_task_config.json'
"""

from logic.generic_task import InterruptableTask
import time
import json

class Task(InterruptableTask): # do not change the name of the class. it is always called Task !
    """ This task does an acquisition of a series of images on the ROIs defined by the user

    current version: allows to iterate over 1 ROI list
    using a sequence of light sources to be used
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print('Task {0} added!'.format(self.name))
        self.user_config_path = self.config['path_to_user_config']
        self.log.info('Task {0} using the configuration at {1}'.format(self.name, self.user_config_path))


    def startTask(self):
        """ """
        self._load_user_parameters()
        self.log.info('loaded user parameters')

        # load a specified list in the ROI module
        self.ref['roi'].load_roi_list(self.roi_path)
        self.log.info('loaded roi list')

        # get the list of the roi names
        self.roi_names = self.ref['roi'].roi_names

        # initialize the counter that will be used to iterate over the ROIs
        self.counter = 0  # counter for the number of task steps


    def runTaskStep(self):
        """ Implement one work step of your task here.
        @return bool: True if the task should continue running, False if it should finish.
        """
        # go to roi
        self.ref['roi'].go_to_roi(name=self.roi_names[self.counter])
        self.log.info('Moved to {}'.format(self.roi_names[self.counter]))

        # iterate over the imaging sequence specified by the user
        for key in self.imaging_sequence:
            # set the filter to the specified position
            self.ref['filter'].set_position(self.imaging_sequence[key]['filter_pos'])

            # indicate the intensity value to be applied to the lightsource
            self.ref['daq'].update_intensity_dict(self.imaging_sequence[key]['lightsource'], self.imaging_sequence[key]['intensity'])

            # the following part has to be reworked when the synchronization between daq and camera is established
            # and when saving functionality of camera is available

            # switch the laser on
            self.ref['daq'].apply_voltage()
            # take an image
            self.ref['camera'].start_single_acquistion() # mind the typo !!
            # time.sleep(0.1)
            # save an image # also think about the generic filename .. it must include the roi it belongs to, the channel, ..
            self.log.info('Saved an image from channel {0} into folder {1}'.format(self.imaging_sequence[key]['lightsource'], self.save_path)) # ... lets say we did ..
            # switch laser off
            self.ref['daq'].voltage_off()

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
            imaging_sequence: {1: {'lightsource': 'laser2', 'intensity': 10, 'filter_pos': 2},
                               2: {'lightsource': 'laser1', 'intensity': 30, 'filter_pos': 5}}

        """
        try:
            with open(self.user_config_path, 'r') as file:
                self.user_param_dict = json.load(file)

            self.roi_path = self.user_param_dict['roilist_path']
            self.save_path = self.user_param_dict['save_path']
            self.imaging_sequence = self.user_param_dict['imaging_sequence'] # which itself is a dictionary

        except:
            self.log.warning('Could not load user parameters for task {}'.format(self.name))







