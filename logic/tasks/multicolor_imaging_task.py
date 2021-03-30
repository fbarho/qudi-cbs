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
import yaml
from datetime import datetime
import os
from time import sleep
from logic.generic_task import InterruptableTask


class Task(InterruptableTask):  # do not change the name of the class. it is always called Task !
    """ This task does an acquisition of a series of images from different channels or using different intensities
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print('Task {0} added!'.format(self.name))
        # self.laser_allowed = False
        self.user_config_path = self.config['path_to_user_config']
        self.log.info('Task {0} using the configuration at {1}'.format(self.name, self.user_config_path))

    def startTask(self):
        """ """
        self.err_count = 0  # initialize the error counter (counts number of missed triggers for debug)
        
        # control if live mode in basic gui is running. Task can not be started then.
        if self.ref['camera'].enabled:
            self.log.warn('Task cannot be started: Please stop live mode first')
            # calling self.cleanupTask() here does not seem to guarantee that the taskstep is not performed. so put an additional safety check in taskstep
            return
        # control if video saving is currently running.  Task can not be started then.
        if self.ref['camera'].saving:
            self.log.warn('Task cannot be started: Wait until saving finished')
            return
        # control if laser has been switched on in basic gui. Task can not be started then.
        if self.ref['daq'].enabled:
            self.log.warn('Task cannot be started: Please switch laser off first')
            return

        self._load_user_parameters()

        # control the config : laser allowed for given filter ?
        self.laser_allowed = self._control_user_parameters()
        
        if not self.laser_allowed:
            self.log.warning('Task aborted. Please specify a valid filter / laser combination')
            return
        
        ### all conditions to start the task have been tested: Task can now be started safely   
        
        # set the filter to the specified position
        self.ref['filter'].set_position(self.filter_pos)
        # use only one filter. do not allow changing filter because this will be too slow
        # wait until filter position set
        pos = self.ref['filter'].get_position()
        while not pos == self.filter_pos:
            sleep(1)
            pos = self.ref['filter'].get_position()

        # initialize the digital output channel for trigger
        self.ref['daq'].set_up_do_channel()
        
        # initialize the analog input channel that reads the fire
        self.ref['daq'].set_up_ai_channel()
        
        # define save path
        self.complete_path = self.ref['camera']._create_generic_filename(self.save_path, '_Stack', 'testimg', '', False)
        # maybe add an extension with the current date to self.save_path. Could be done in load_user_param method
        
        # prepare the camera
        frames = len(self.imaging_sequence) * self.num_frames 
        self.ref['camera'].prepare_camera_for_multichannel_imaging(frames, self.exposure, self.gain, self.complete_path, self.file_format)

    def runTaskStep(self):
        """ Implement one work step of your task here.
        @return bool: True if the task should continue running, False if it should finish.
        """
        # control if live mode in basic gui is running. Taskstep will not be run then.
        if self.ref['camera'].enabled:
            return False
        # control if video saving is currently running
        if self.ref['camera'].saving:
            return False
        # control if laser is switched on
        if self.ref['daq'].enabled:
            return False
        # add similar control for all other criteria
        # .. 
        if not self.laser_allowed:
            return False
        
        
        # this task only has one step until a data set is prepared and saved (but loops over the number of frames per channel and the channels)
        # outer loop over the number of frames per color
        for j in range(self.num_frames):

            # use a while loop to catch the exception when a trigger is missed and just repeat the last (missed) image
            i = 0
            while i < len(self.imaging_sequence):
                # reset the intensity dict to zero
                self.ref['daq'].reset_intensity_dict()
                # prepare the output value for the specified channel
                self.ref['daq'].update_intensity_dict(self.imaging_sequence[i][0], self.imaging_sequence[i][1])
                # waiting time for stability
                sleep(0.05)
            
                # switch the laser on and send the trigger to the camera
                self.ref['daq'].apply_voltage()
                err = self.ref['daq'].send_trigger_and_control_ai()  
            
                # read fire signal of camera and switch off when the signal is low
                ai_read = self.ref['daq'].read_ai_channel()
                count = 0
                while not ai_read <= 2.5:  # analog input varies between 0 and 5 V. use max/2 to check if signal is low
                    sleep(0.001)  # read every ms
                    ai_read = self.ref['daq'].read_ai_channel()
                    count += 1  # can be used for control and debug
                self.ref['daq'].voltage_off()
                # self.log.debug(f'iterations of read analog in - while loop: {count}')
            
                # waiting time for stability
                sleep(0.05)

                # repeat the last step if the trigger was missed
                if err < 0:
                    self.err_count += 1  # control value to check how often a trigger was missed
                    i = i  # then the last iteration will be repeated
                else:
                    i += 1  # increment to continue with the next image

        
        # finish the acquisition  # calling this here allows to access the temperature for the metadata
        self.ref['camera'].abort_acquisition()
        # save metadata
        metadata = self._create_metadata_dict()  # {'key1': 1, 'key2': 2, 'key3': 3}
        if self.file_format == 'fits':
            complete_path = self.complete_path + '.fits'
            self.ref['camera']._add_fits_header(complete_path, metadata)
        else:  # default case, add a txt file with the metadata
            self.ref['camera']._save_metadata_txt_file(self.save_path, '_Stack', metadata)
        
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
        self.ref['daq'].close_ai_task()
        self.ref['camera'].reset_camera_after_multichannel_imaging()
        self.log.debug(f'number of missed triggers: {self.err_count}')
        self.log.info('cleanupTask called')
        
# # to do: use these two methods instead of the way it is now implemented        
#    def checkExtraStartPrerequisites(self):
#        """ Check extra start prerequisites, there are none """
#        start_prerequisites = True  # as initialization
#        # control if live mode in basic gui is running. Task can not be started then.
#        if self.ref['camera'].enabled:
#            start_prerequisites = False
#        # control if video saving is currently running.  Task can not be started then.
#        if self.ref['camera'].saving:
#            start_prerequisites = False
#        # control if laser has been switched on in basic gui. Task can not be started then.
#        if self.ref['daq'].enabled:
#            start_prerequisites = False
#        return start_prerequisites
#
#    def checkExtraPausePrerequisites(self):
#        """ Check extra pause prerequisites, there are none """
#        return True

    def _load_user_parameters(self):
        """ this function is called from startTask() to load the parameters given in a specified format by the user

        specify only the path to the user defined config in the (global) config of the experimental setup

        user must specify the following dictionary (here with example entries):
            filter_pos: 1
            exposure: 0.05  # in s
            gain: 0
            num_frames: 1  # number of frames per color
            save_path: 'E:\\Data'
            file_format: 'tiff'
            imaging_sequence = [('488 nm', 3), ('561 nm', 3), ('641 nm', 10)]
        """
        try:
            with open(self.user_config_path, 'r') as stream:
                self.user_param_dict = yaml.safe_load(stream)

                self.filter_pos = self.user_param_dict['filter_pos']
                self.exposure = self.user_param_dict['exposure']
                self.gain = self.user_param_dict['gain']
                self.num_frames = self.user_param_dict['num_frames']
                self.save_path = self.user_param_dict['save_path']
                self.imaging_sequence_raw = self.user_param_dict['imaging_sequence']
                self.file_format = self.user_param_dict['file_format']
                self.log.debug(self.imaging_sequence_raw)  # remove after tests

                # for the imaging sequence, we need to access the corresponding labels
                laser_dict = self.ref['daq'].get_laser_dict()
                imaging_sequence = [(*get_entry_nested_dict(laser_dict, self.imaging_sequence_raw[i][0], 'label'),
                                     self.imaging_sequence_raw[i][1]) for i in range(len(self.imaging_sequence_raw))]
                self.log.info(imaging_sequence)
                self.imaging_sequence = imaging_sequence
                # new format should be self.imaging_sequence = [('laser2', 10), ('laser2', 20), ('laser3', 10)]
                
        except Exception as e:  # add the type of exception
            self.log.warning(f'Could not load user parameters for task {self.name}: {e}')
                          
            
    def _control_user_parameters(self):
        # use the filter position to create the key # simpler than using get_entry_netsted_dict method
        key = 'filter{}'.format(self.filter_pos)
        bool_laserlist = self.ref['filter'].get_filter_dict()[key]['lasers']  # list of booleans, laser allowed ? such as [True True False True], corresponding to [laser1, laser2, laser3, laser4]
        forbidden_lasers = []
        for i, item in enumerate(bool_laserlist):
            if not item:  # if the element in the list is False:
                label = 'laser'+str(i+1)
                forbidden_lasers.append(label)      
        lasers_allowed = True  # as initialization
        for item in forbidden_lasers:
            if item in [self.imaging_sequence[i][0] for i in range(len(self.imaging_sequence))]:
                lasers_allowed = False
                break  # stop if at least one forbidden laser is found
        return lasers_allowed
    
            
    def _create_metadata_dict(self):
        """ create a dictionary containing the metadata

        this is a similar to the function available in basic_gui. the values are addressed slightly differently via the refs"""
        metadata = {}
        # timestamp
        metadata['time'] = datetime.now().strftime('%m-%d-%Y, %H:%M:%S')  # or take the starting time of the acquisition instead ??? # then add a variable to startTask
        
        # filter name
        filterpos = self.ref['filter'].get_position()
        filterdict = self.ref['filter'].get_filter_dict()
        label = 'filter{}'.format(filterpos)
        metadata['filter'] = filterdict[label]['name']
        
        # gain
        metadata['gain'] = self.ref['camera'].get_gain()  # could also use the value from the user config directly ?? 
        
        # exposure and kinetic time              
        metadata['exposure'] = self.ref['camera'].get_exposure()
        metadata['kinetic'] = self.ref['camera'].get_kinetic_time()
        
        # lasers and intensity 
        imaging_sequence = self.imaging_sequence_raw
        metadata['laser'] = [imaging_sequence[i][0] for i in range(len(imaging_sequence))]  # needs to be adapted for fits header compatibility
        metadata['intens'] = [imaging_sequence[i][1] for i in range(len(imaging_sequence))]  # needs to be adapted for fits header compatibility
        
        # sensor temperature
        if self.ref['camera'].has_temp:
            metadata['temp'] = self.ref['camera'].get_temperature()
        else:
            metadata['temp'] = 'Not available'
            
        return metadata




def get_entry_nested_dict(nested_dict, val, entry):
    """ helper function that searches for 'val' as value in a nested dictionary and returns the corresponding value in the category 'entry'
    example: search in laser_dict (nested_dict) for the label (entry) corresponding to a given wavelength (val)
    search in filter_dict (nested_dict) for the label (entry) corresponding to a given filter position (val)

    @param: dict nested dict
    @param: val: any data type, value that is searched for in the dictionary
    @param: str entry: key in the inner dictionary whose value needs to be accessed

    note that this function is not the typical way how dictionaries should be used. due to the unambiguity in the dictionaries used here,
    it can however be useful to try to find a key given a value.
    Hence, in practical cases, the return value 'list' will consist of a single element only. """
    entrylist = []
    for outer_key in nested_dict:
        item = [nested_dict[outer_key][entry] for inner_key, value in nested_dict[outer_key].items() if val == value]
        if item != []:
            entrylist.append(*item)
    return entrylist


# to do on this task:
# check if metadata contains everything that is needed
# checked state for laser on button in basic gui gets messed up    (because of call to voltage_off in cleanupTask called)
    # fits header: can value be a list ? check with simple example
    
    