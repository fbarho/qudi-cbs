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
            laser: 'lasercontrol_logic'
            roi: 'roi_logic'
        config:
            path_to_user_config: 'C:/Users/sCMOS-1/qudi_data/qudi_task_config_files/photobleaching_task_RAMM.yaml'
"""
import yaml
from time import sleep
from logic.generic_task import InterruptableTask


class Task(InterruptableTask):  # do not change the name of the class. it is always called Task !
    """ This task iterates over all roi given in a file and illuminates this position with a sequence of lasers.
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

        self.ref['laser'].stop_laser_output()
        self.ref['laser'].disable_laser_actions()

        # set stage velocity
        self.ref['roi'].set_stage_velocity({'x': 1, 'y': 1})

        # read all user parameters from config
        self.load_user_parameters()

        # initialize a counter to iterate over the ROIs
        self.roi_counter = 0
        # set the active_roi to none to avoid having two active rois displayed
        self.ref['roi'].active_roi = None

    def runTaskStep(self):
        """ Implement one work step of your task here.
        @return bool: True if the task should continue running, False if it should finish.
        """
        # ------------------------------------------------------------------------------------------
        # move to ROI
        # ------------------------------------------------------------------------------------------
        self.ref['roi'].set_active_roi(name=self.roi_names[self.roi_counter])
        self.ref['roi'].go_to_roi_xy()
        self.log.info('Moved to {}'.format(self.roi_names[self.roi_counter]))
        sleep(1)  # replace maybe by wait for idle

        # ------------------------------------------------------------------------------------------
        # activate lightsource
        # ------------------------------------------------------------------------------------------
        # all laser lines at once
        for item in self.imaging_sequence:
            self.ref['laser'].update_intensity_dict(item[0], item[1])  # key (register in fpga bitfile), value (intensity in %)
        self.ref['laser'].apply_voltage()
        sleep(self.illumination_time)
        self.ref['laser'].voltage_off()

        # version with individual laser lines
        # for item in self.imaging_sequence:
        #     self.ref['laser'].apply_voltage_single_channel(item[1], item[0])  #  param: intensity, channel
        #     sleep(self.illumination_time)
        #     self.ref['laser'].apply_voltage_single_channel(0, item[0])

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
        # for item in self.imaging_sequence:
        #     self.ref['laser'].apply_voltage_single_channel(0, item[0])

        # new version
        self.ref['laser'].voltage_off()


        # enable gui actions
        # roi gui
        self.ref['roi'].enable_tracking_mode()
        self.ref['roi'].enable_roi_actions()
        # basic imaging gui
        self.ref['laser'].enable_laser_actions()

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

                self.illumination_time = self.user_param_dict['illumination_time'] * 60   # illumination time is given in min and needs to be converted to seconds
                imaging_sequence = self.user_param_dict['imaging_sequence']
                self.roi_list_path = self.user_param_dict['roi_list_path']

        except Exception as e:  # add the type of exception
            self.log.warning(f'Could not load user parameters for task {self.name}: {e}')

        # establish further user parameters derived from the given ones:
        self.ref['roi'].load_roi_list(self.roi_list_path)
        self.roi_names = self.ref['roi'].roi_names

        # convert the imaging_sequence given by user into format required for function call
        lightsource_dict = {'405 nm': '405', '488 nm': '488', '561 nm': '561', '640 nm': '640'}
        self.imaging_sequence = [(lightsource_dict[item[0]], item[1]) for item in imaging_sequence]
