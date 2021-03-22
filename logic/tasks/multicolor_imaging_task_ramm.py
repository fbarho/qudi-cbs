# -*- coding: utf-8 -*-
"""
Created on Wed March 10 2021

@author: fbarho

This file is an extension to Qudi software
obtained from <https://github.com/Ulm-IQO/qudi/>

Multicolor imaging task for the RAMM setup

Config example pour copy-paste:
    MulticolorImagingTask:
        module: 'multicolor_imaging_task_ramm'
        needsmodules:
            fpga: 'lasercontrol_logic'
            cam: 'camera_logic'
"""

# would it be smarter to connect directly to the hardware layer and not to the logic ??  to explore.

from time import sleep
from logic.generic_task import InterruptableTask


class Task(InterruptableTask):  # do not change the name of the class. it is always called Task !
    """ This task does an acquisition of a series of images from different channels or using different intensities
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print('Task {0} added!'.format(self.name))

    def startTask(self):
        """ """
        self.log.info('started Task')
        self.ref['fpga'].close_default_session()
        self.log.info('closed default session')

        # set the camera state
        self.ref['cam'].set_acquisition_mode_hcam('fixed_length', 5)  # num_frames
        self.ref['cam'].set_trigger_mode('EXTERNAL')
        self.ref['cam'].start_acquisition()



        bitfile = 'C:\\Users\\sCMOS-1\\qudi-cbs\\hardware\\fpga\\FPGA\\FPGA Bitfiles\\FPGAv0_FPGATarget_FPGAtriggercamer_u12WjFsC0U8.lvbitx'
        self.ref['fpga'].start_task_session(bitfile)
        self.log.info('started task session')



    def runTaskStep(self):
        """ Implement one work step of your task here.
        @return bool: True if the task should continue running, False if it should finish.
        """
        z_planes = 1
        wavelength = [3, 3, 3, 3, 3]
        values = [3, 0, 4, 0, 5]

        # modifier pos piezo
        # attendre 30 ms
        # envoyer signal du daq vers le FPGA connector 0 /DIO3
        # attendre signal du FPGA vers le DAQ

        self.ref['fpga'].run_multicolor_imaging_task_session(z_planes, wavelength, values)
        self.log.info('task session running ..')

        sleep(1)  # add some waiting time for tests to see if task is executed # use real timing functionality for real tasks
        return False

    def pauseTask(self):
        """ """
        self.log.info('pauseTask called')

    def resumeTask(self):
        """ """
        self.log.info('resumeTask called')

    def cleanupTask(self):
        """ """
        self.log.info('cleanupTask called')
        self.ref['fpga'].end_task_session()
        self.log.info('closed task session')

        self.ref['cam'].stop_acquisition()  # for tests as safety
        # reset also other camera properties
        self.ref['cam'].set_acquisition_mode_hcam('run_till_abort', None)
        self.ref['cam'].set_trigger_mode('INTERNAL')

        self.ref['fpga'].restart_default_session()
        self.log.info('restarted default session')