# -*- coding: utf-8 -*-
"""
Created on Wed Mars 3 2021

@author: fbarho

This file is an extension to Qudi software
obtained from <https://github.com/Ulm-IQO/qudi/>

Test task: how to handle fpga bitfiles during task

Config example pour copy-paste:
    TestTask:
        module: 'testtask_ramm'
        needsmodules:
            fpga: 'lasercontrol_logic'
"""
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
        #bitfile = 'C:\\Users\\sCMOS-1\\qudi-cbs\\hardware\\fpga\\FPGA\\FPGA Bitfiles\\FPGAv0_FPGATarget_FPGAlasercontrol_o8wg7Z4+KAQ.lvbitx'
        bitfile =  'C:\\Users\\sCMOS-1\\qudi-cbs\\hardware\\fpga\\FPGA\\FPGA Bitfiles\\FPGAv0_FPGATarget_FPGAlasercontrol_pdDEc3yii+w.lvbitx'
        self.ref['fpga'].start_task_session(bitfile)
        self.log.info('started task session')




    def runTaskStep(self):
        """ Implement one work step of your task here.
        @return bool: True if the task should continue running, False if it should finish.
        """
        self.ref['fpga'].run_test_task_session()
        self.log.info('task session running ..')
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
        self.ref['fpga'].restart_default_session()
        self.log.info('restarted default session')




