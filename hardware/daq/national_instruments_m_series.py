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
    _ao_channels = ConfigOption('ao_channels', missing='error')
    _ao_voltage_ranges = ConfigOption('ao_voltage_ranges', missing='error') 
    
    
    # timeout for the Read or/and write process in s
    _RWTimeout = ConfigOption('read_write_timeout', default=10)
  
#    def __init__(self):
#        super().__init__() 
#  
    
    def on_activate(self):
        """ Initialization steps when module is called.
        """
         # initialize the tasks used on the hardware device:
        self._ao_task = None
        
        if len(self._ao_channels) > len(self._ao_voltage_ranges):
            self.log.error('Specify at least as many ao_voltage_ranges as ao_channels!')
        
#        # Analog output is always needed and it does not interfere with the
#        # rest, so start it always and leave it running
##        if self._start_analog_output() < 0:
##            self.log.error('Failed to start analog output.')
##            raise Exception('Failed to start NI Card module due to analog output failure.')
#    
    def on_deactivate(self):
        """ Shut down the NI card.
        """
        self._stop_analog_output()
        # clear the task
        try:
            daq.DAQmxClearTask(self._ao_task)
            self._ao_task = None
        except:
            self.log.exception('Could not clear AO Out Task.')

        # uncomment if needed: self.reset_hardware()
        
        
    
    def _start_analog_output(self):
        """ Starts or restarts the analog output. Initializes the task and prepares the channels.
        
        @return int: error code (O: OK, -1: error)
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
                
            # initialize ao task
            self._ao_task = daq.TaskHandle()
            
            # create the actual analog output task on the hardware device. 
            # Via byref you pass the pointer of the object to the TaskCreation function (see ctypes doc):
            daq.DAQmxCreateTask('OTF_control_AO', daq.byref(self._ao_task))
            for n, chan in enumerate(self._ao_channels):
                # Assign and configure the created task to an analog output voltage channel.
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
  
    def _stop_analog_output(self):
        """ Stops the analog output.
        
        @return: int: error code (0: OK, -1: error)
        """
        # if there is no task active, return error
        if self._ao_task is None:
            return -1
        
        retval = 0
        
        try: 
            # stop the analog output task
            daq.DAQmxStopTask(self._ao_task)
        except:
            # else raise an error in the log 
            self.log.exception('Error stopping analog output.')
            retval = -1
            
        try: 
            daq.DAQmxSetSampTimingType(self._ao_task, daq.DAQmx_Val_OnDemand)
        except:
            self.log.exception('Error changing analog output mode.')
            retval = -1
        
        return retval


 
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
        
        
       
        
    def apply_voltage(self, value, start=True):
        daq.DAQmxStartTask(self._ao_task)
        daq.DAQmxWriteAnalogScalarF64(self._ao_task, start, self._RWTimeout, value, None)
        #daq.DAQmxStopTask(self._ao_task)
        #daq.DAQmxClearTask(self._ao_task) # clean up after stopping the task
        #self._ao_task = None # set handle to None as safety
        
        # how to organize to decouple task preparation from writing to analog output without necessity to rerun _start_analog_output again ?
        
        




##    def _write_to_analog_output(self, voltages, length=1, start=False):
##        """Writes a set of voltages to the analog output channels.
##        
##        @param float[][n] voltages: array of n-part tuples defining the voltage points
##        
##        @param int length: number of tuples to write
##        
##        @param bool: start: write immediately (True) or wait for start of task (False)
##        
##        n depends on how many channels are configured for analog output
##        """
##        # Number of samples which are actually written will be stored here.
##        # The error code of self._aoNwritten can be asked with .value to check 
##        # whether all channels have been written successfully.
##        self._aoNwritten = daq.int32()
##        # write the voltage instructions fot the analog output to the hardware
##        daq.DAQmxWriteAnalogF64(
##                # write to this task
##                self._ao_task,
##                # length of the command (points)
##                length, 
##                # start immediately (True) or wait for software start (False)
##                start, 
##                # maximal timeout in seconds for the write process
##                self._RWTimeout,
##                # Specify how the samples are arranged: each pixel is grouped by channel number
##                daq.DAQmx_Va_GroupByChannel,
##                # the voltages to be written
##                voltages,
##                # The actual number of samples per channel successfully written to the buffer
##                daq.byref(self._aoNwritten),
##                # Reserved for future use. Pass None to this parameter
##                None)
##        return self._aoNwritten.value
  
