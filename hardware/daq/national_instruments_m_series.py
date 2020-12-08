#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 23 08:00:40 2020

@author: barho


This file contains a class for the NI-DAQ M series. 

It is used to control the analog output channels of the DAQ.

This module is an extension to the hardware code base of Qudi software 
obtained from <https://github.com/Ulm-IQO/qudi/> 
"""

#import nidaqmx
import PyDAQmx as daq # this only runs on systems where the niDAQmx library is available 
from core.module import Base
from interface.daq_interface import DaqInterface
from core.configoption import ConfigOption


class NIDAQMSeries(Base, DaqInterface):
    """ National Instruments DAQ that controls the lasers via an OTF.
    
    Example config for copy-paste:
        nidaq_6259:
            module.Class: 'daq.national_instruments_m_series.NIDAQMSeries'
            wavelengths:
                - '405 nm'
                - '488 nm'
                - '561 nm'
                - '641 nm'
            ao_channels:
                - '/Dev1/AO0'
                - '/Dev1/AO2'
                - '/Dev1/AO1'
                - '/Dev1/AO3'
            ao_voltage_ranges: 
                - [0, 10]
                - [0, 10]
                - [0, 10]
                - [0, 10]
            read_write_timeout: 10
            
            # please indicate belonging elements in the same order in each category ao_channels, voltage_ranges, wavelengths
            # order preferentially by increasing wavelength (this will result in an ordered gui)
    """
    
    # config
    _wavelengths = ConfigOption('wavelengths', missing='error')
    _ao_channels = ConfigOption('ao_channels', missing='error')
    _ao_voltage_ranges = ConfigOption('ao_voltage_ranges', missing='error')
    # timeout for the Read or/and write process in s
    _RWTimeout = ConfigOption('read_write_timeout', default=10)

    
    def on_activate(self):
        """ Initialization steps when module is called.
        """
        # control if the config was correctly specified
        if (len(self._ao_channels) != len(self._ao_voltage_ranges)) or (len(self._ao_channels) != len(self._wavelengths)):
            self.log.error('Specify equal numbers of ao channels, voltage ranges and OTF input channels!')

        # create analog output tasks and channels
        if self._start_analog_output() < 0:
            self.log.error('Failed to start analog output')
            raise Exception('Failed to start analog output')


    def _start_analog_output(self):
        """ Creates for each physical channel a task and its virtual channel

        @returns: error code: ok = 0 
        """
        try:
            # create a dictionary with physical channel name as key and a pointer as value {'/Dev1/AO0': c_void_p(None), ... }
            taskhandles = dict([(name, daq.TaskHandle(0)) for name in self._ao_channels])
            
            # if an analog task is already running, stop it first (safety if one of the created pointers already points somewhere) 
            for channel in self._ao_channels: 
                if taskhandles[channel].value is not None: 
                    # stop analog output task
                    daq.DAQmxStopTask(taskhandles[channel])
                    # delete the configuration of the analog task
                    daq.DAQmxClearTask(taskhandles[channel])
                    # set the task handle to None as a safety
                    taskhandles[channel].value = None
            
            # create an individual task and a channel per analog output 
            for n, channel in enumerate(self._ao_channels): # use enumerate to access the equivalent list element 
                daq.DAQmxCreateTask('', daq.byref(taskhandles[channel])) 
                daq.DAQmxCreateAOVoltageChan(taskhandles[channel], channel, '', self._ao_voltage_ranges[n][0], self._ao_voltage_ranges[n][1], daq.DAQmx_Val_Volts, None) 
                # to do : acces min and max value and replace it above
            self.taskhandles = taskhandles
            
        except:
            self.log.exception('Error starting analog output task.')
            return -1
        return 0


    def on_deactivate(self):
        """ Shut down the NI card.
        """
        # clear the task
        try:
            for channel in self._ao_channels:
                daq.DAQmxClearTask(self.taskhandles[channel])
                self.taskhandles[channel].value = None  # reset it to nullpointer
            print(self.taskhandles)
        except:
            self.log.exception('Could not clear AO Out Task.')

        
    def apply_voltage(self, voltage, channel, autostart=True, timeout=10): # autostart = False can only be used if timing is configured. to be done later when working on synchronization with camera acquisition
        """        
        """
        daq.WriteAnalogScalarF64(self.taskhandles[channel], autostart, timeout, voltage, None)#parameters passed in: taskHandle, autoStart, timeout, value, reserved
        daq.DAQmxStartTask(self.taskhandles[channel])
        daq.DAQmxStopTask(self.taskhandles[channel])


    def get_dict(self):
        """ Retrieves the channel name and the corresponding voltage range for each analog output and associates it to
        the laser wavelength which is controlled by this channel.

        @returns: laser_dict
        """
        """ Retrieves the channel name and the corresponding voltage range for each analog output from the
        configuration file and associates it to the laser wavelength which is controlled by this channel.

        Make sure that the config contains all the necessary elements.

        @returns: laser_dict
        """
        laser_dict = {}

        for i, item in enumerate(
                self._wavelengths):  # use any of the lists retrieved as config option, just to have an index variable
            label = 'laser{}'.format(i + 1)  # create a label for the i's element in the list starting from 'laser1'

            dic_entry = {'label': label,
                         'wavelength': self._wavelengths[i],
                         'channel': self._ao_channels[i],
                         'ao_voltage_range': self._ao_voltage_ranges[i]}

            laser_dict[dic_entry['label']] = dic_entry

        return laser_dict

        
# simple version for tests       
#    def apply_voltage_test(self, value, channel): # specify channel in format '/Dev1/ao1'
#        """ simple method to apply a voltage to a channel.
#        """
#        
#        # simple version similar to PyDAQmx doc but using TaskHandle instead of creating a Task object        
#        self._ao_task = daq.TaskHandle()
#        daq.DAQmxCreateTask('AO Task', daq.byref(self._ao_task))
#        # replace physical channel with correct location
#        daq.DAQmxCreateAOVoltageChan(self._ao_task, channel, 'AO Channel', 0, 10, daq.DAQmx_Val_Volts, None)
#        daq.DAQmxStartTask(self._ao_task)
#        daq.WriteAnalogScalarF64(self._ao_task, True, 5.0, value, None) #parameters passed in: taskHandle, autoStart, timeout, value, reserved
#        daq.DAQmxStopTask(self._ao_task)
#        daq.DAQmxClearTask(self._ao_task) # clean up after stopping the task
#        self._ao_task = None # set task handle to None as safety



