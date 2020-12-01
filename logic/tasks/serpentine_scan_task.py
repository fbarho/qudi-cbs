# -*- coding: utf-8 -*-
"""
Tests on implementing a serpentine scan task using the predefined task structure of qudi.


Config example pour copy-paste:
    serpentineScanTask:
        module: 'serpentine_scan_task'
        needsmodules:
            roi: 'roi_logic'
            daq: 'daq_ao_logic'
            camera: 'camera_logic2'
            filter: 'filterwheel_logic'
        config:
            roilist_path: '/home/barho/roilists/mylist.json'
            save_path: '/home/barho/myfolder'
            lightsource: 'laser1'
            intensity: 10
            filter_pos: 2


"""

from logic.generic_task import InterruptableTask
import time

class Task(InterruptableTask): # do not change the name of the class. it is always called Task !
    """ This task does an acquisition of a series of images on the ROIs defined by the user

    current version: allows to iterate over 1 ROI list, path given in global config,
    using one light source with intensity specified in the global config
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print('Task {0} added!'.format(self.name))
        self.log.info(self.config)

        self.roi_path = self.config['roilist_path']
        self.save_path = self.config['save_path']
        self.lightsource = self.config['lightsource']
        self.intensity = self.config['intensity']
        self.filter_pos = self.config['filter_pos']


    def startTask(self):
        """ """
        # load a specified list in the ROI module
        self.ref['roi'].load_roi_list(self.roi_path)
        self.log.info('loaded list')

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

        # save an image - here: replaced by take image. save image needs to be implemented
        # remember also to specify the save path in startTask method
        self.ref['camera'].start_single_acquistion() # mind the typo !!
        self.log.info('Saved an image into folder {}'.format(self.save_path)) # ... lets say we did ..

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

    def my_function(self):
        """ """
        self.log.info('called a custom function')


