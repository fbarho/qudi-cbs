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
from core.configoption import ConfigOption


class NIDAQMSeries(Base):
    """ National Instruments DAQ that controls the lasers via an OTF.
    
    Example config for copy-paste:
        nidaq_6259:
            module.Class: 'national_instruments_m_series.NIDAQMSeries'
            wavelengths:
                - '405 nm'
                - '488 nm'
                - '561 nm'
                - '641 nm'
            ao_channels:
                - '/Dev1/AO0'
                - '/Dev1/AO1'
                - '/Dev1/AO2'
                - '/Dev1/AO3'
            ao_voltage_ranges: 
                - [0, 10]
                - [0, 10]
                - [0, 10]
                - [0, 10]
            read_write_timeout: 10

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
         # initialize the tasks used on the hardware device:
        self._ao_task = None
        
        if (len(self._ao_channels) != len(self._ao_voltage_ranges)) or (len(self._ao_channels) != len(self._wavelengths)):
            self.log.error('Specify equal numbers of ao channels, voltage ranges and OTF input channels!')

        # create an analog output task and create the channels
        if self._start_analog_output() < 0:
            self.log.error('Failed to start analog output')
            raise Exception('Failed to start analog output')

    def _start_analog_output(self):
        """ Creates an analog output task and the channels

        @returns: error code: ok = 0
        """
        try:
            # if an analog task is already running, stop it first
            if self._ao_task is not None:
                # stop analog output task
                daq.DAQmxStopTask(self._ao_task)
                # delete the configuration of the analog task
                daq.DAQmxClearTask(self._ao_task)
                # set the task handle to None as a safety
                self._ao_task = None

            # create ao task
            self._ao_task = daq.TaskHandle()
            daq.DAQmxCreateTask('OTF_control_AO', daq.byref(self._ao_task))  # Via byref you pass the pointer of the object to the TaskCreation function (see ctypes doc)

            # create the channels
            for n, chan in enumerate(self._ao_channels): # iterate over the specified channels read from config
                daq.DAQmxCreateAOVoltageChan(
                        # The AO voltage operation function is assigned to this task.
                        self._ao_task,
                        # use (all) ao_channels for the output
                        chan,
                        # assign a name for that channel
                        'OTF AO Channel {0}'.format(n),
                        # minimum possible voltage
                        self._ao_voltage_ranges[n][0],
                        # maximum possible voltage
                        self._ao_voltage_ranges[n][1],
                        # units is Volt
                        daq.DAQmx_Val_Volts,
                        # empty for future use
                        None)

        except:
            self.log.exception('Error starting analog output task.')
            return -1
        return 0


    def on_deactivate(self):
        """ Shut down the NI card.
        """
        # clear the task
        try:
            daq.DAQmxClearTask(self._ao_task)
            self._ao_task = None
        except:
            self.log.exception('Could not clear AO Out Task.')

        
    def apply_voltqge(self, voltqge, channel):
        """
        """


  

 
## this version works well:        
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
        
        
       
        
    # def apply_voltage(self, value, start=True):
    #     daq.DAQmxStartTask(self._ao_task)
    #     daq.DAQmxWriteAnalogScalarF64(self._ao_task, start, self._RWTimeout, value, None)
    #     #daq.DAQmxStopTask(self._ao_task)
    #     #daq.DAQmxClearTask(self._ao_task) # clean up after stopping the task
    #     #self._ao_task = None # set handle to None as safety


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

        
        



