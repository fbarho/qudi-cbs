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
            path_to_user_config: '/home/barho/serpentine_scan_task_config.json'
"""

from logic.generic_task import InterruptableTask
# import time
import json

class Task(InterruptableTask): # do not change the name of the class. it is always called Task !
    """ This task does an acquisition of a series of images on the ROIs defined by the user

    current version: allows to iterate over 1 ROI list
    using one light source with intensity specified in user config
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print('Task {0} added!'.format(self.name))
        self.user_config_path = self.config['path_to_user_config']
        self.log.info('Task {0} using the configuration at {1}'.format(self.name, self.user_config_path))


    def startTask(self):
        """ """
        self._load_user_parameters()

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


    def runTaskStep(self):
        """ Implement one work step of your task here.
        @return bool: True if the task should continue running, False if it should finish.
        """
        # go to roi
        self.ref['roi'].go_to_roi(name=self.roi_names[self.counter])
        self.log.info('Moved to {}'.format(self.roi_names[self.counter]))

        # switch the laser on
        self.ref['daq'].apply_voltage()

        # take an image and save it -> it is needed to first call start_single_acquisition otherwise no data is available
        self.ref['camera'].start_single_acquistion() # mind the typo !!
        self.ref['camera'].save_last_image(self.save_path, 'testimg', fileformat='tiff')

        # switch laser off
        self.ref['daq'].voltage_off()

        # in a following version the laser on off switching should be triggered by the camera. but this actually goes into the daq_ao_logic module ..

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
        """
        try:
            with open(self.user_config_path, 'r') as file:
                self.user_param_dict = json.load(file)

            self.roi_path = self.user_param_dict['roilist_path']
            self.save_path = self.user_param_dict['save_path']
            self.lightsource = self.user_param_dict['lightsource']
            self.intensity = self.user_param_dict['intensity']
            self.filter_pos = self.user_param_dict['filter_pos']
            
            self.log.info('loaded user parameters')

        except:
            self.log.warning('Could not load user parameters for task {}'.format(self.name))







