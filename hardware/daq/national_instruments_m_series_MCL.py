#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 23 08:00:40 2020

@author: barho

This file contains a class for the NI-DAQ M series.

It is used to control the MCL piezo from the DAQ and read its position.

This module is an extension to the hardware code base of Qudi software 
obtained from <https://github.com/Ulm-IQO/qudi/> 
"""

import PyDAQmx as daq  # this only runs on systems where the niDAQmx library is available
from core.module import Base
from core.configoption import ConfigOption
import numpy as np
from time import sleep


class NIDAQMSeries(Base):
    """ National Instruments DAQ

    functionality
    - control the mcl piezo stage
    - generate/read signals for communication with an FPGA
    - control the pump for needle rinsing
    
    Example config for copy-paste:
        nidaq_6259:
            module.Class: 'daq.national_instruments_m_series_MCL.NIDAQMSeries'
            piezo_read: 'Dev1/AI0'
            piezo_write: 'Dev1/AO1'
            ao_voltage_range: [0, 10]
            pump_write: 'Dev1/AO0'
            read_write_timeout: 10 # in seconds
    """
    
    # config
    _piezo_read_channel = ConfigOption('piezo_read', missing='error')
    _piezo_write_channel = ConfigOption('piezo_write', missing='error')
    _pump_write_channel = ConfigOption('pump_write', missing='error')
    _ao_voltage_range = ConfigOption('ao_voltage_range', missing='error')
    # timeout for the Read or/and write process in s
    _RWTimeout = ConfigOption('read_write_timeout', default=10)
    _do_start_acquisition_DIO3 = ConfigOption('do_start_acquisition', missing='error')
    _do_acquisition_done_DIO4 = ConfigOption('do_acquisition_done', missing='error')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initialization steps when module is called.
        """

        # create the piezo_write_task
        try:
            taskhandles = self.create_taskhandle()
            self.piezo_write_taskhandles = self.activate_AO(taskhandles, self._piezo_write_channel, self._ao_voltage_range)
            print('Piezo write created')
        except:
            self.log.error('Failed to start analog output')

        # create the piezo-read task
        try:
            taskhandles = self.create_taskhandle()
            self.piezo_read_taskhandle = self.activate_AI(taskhandles, self._piezo_read_channel)
            print('Piezo read created')
        except:
            self.log.error('Failed to start analog input')

        # create the digital channels
        try:
            taskhandles = self.create_taskhandle()
            self.DIO3_taskhandle = self.activate_DO(taskhandles, self._do_start_acquisition_DIO3)
            print('DIO3 created')
            taskhandles = self.create_taskhandle()
            self.DIO4_taskhandle = self.activate_DI(taskhandles, self._do_acquisition_done_DIO4)
            print('DIO4 created')
        except:
            self.log.error('Failed to start digital input / output')

        # create the analog output for pump control
        try:
            taskhandles = self.create_taskhandle()
            self.pump_write_taskhandle = self.activate_AO(taskhandles, self._pump_write_channel, [-10, 10]) # self._ao_voltage_range)
            print('Pump write created')
        except:
            self.log.error('Failed to start analog output')


    def activate_AO(self, taskhandles, channel, voltage_range):
        daq.DAQmxCreateTask('', daq.byref(taskhandles))
        daq.DAQmxCreateAOVoltageChan(taskhandles, channel, '', voltage_range[0],
                                     voltage_range[1], daq.DAQmx_Val_Volts, None)
        return taskhandles

    def activate_AI(self, taskhandles, channel):
        daq.DAQmxCreateTask('', daq.byref(taskhandles))
        daq.DAQmxCreateAIVoltageChan(taskhandles, channel, '', daq.DAQmx_Val_RSE, 0.0, 10.0,
                                 daq.DAQmx_Val_Volts, None)
        return taskhandles

    def activate_DO(self, taskhandles, channel):
        daq.DAQmxCreateTask('', daq.byref(taskhandles))
        daq.DAQmxCreateDOChan(taskhandles, channel, '', daq.DAQmx_Val_ChanPerLine)  # last argument: line grouping
        return taskhandles

    def activate_DI(self, taskhandles, channel):
        daq.DAQmxCreateTask('', daq.byref(taskhandles))
        daq.DAQmxCreateDIChan(taskhandles, channel, '', daq.DAQmx_Val_ChanPerLine)  # last argument: line grouping
        return taskhandles

    def create_taskhandle(self):
        taskhandles = daq.TaskHandle()
        if taskhandles.value is not None:
            # stop analog output task
            daq.DAQmxStopTask(taskhandles)
            # delete the configuration of the analog task
            daq.DAQmxClearTask(taskhandles)
            # set the task handle to None as a safety
            taskhandles.value = None
        return taskhandles

    def on_deactivate(self):
        """ Shut down the NI card.
        """
        # clear the task
        try:
            daq.DAQmxClearTask(self.piezo_write_taskhandles)
            self.piezo_write_taskhandles.value = None  # reset it to nullpointer
            daq.DAQmxClearTask(self.piezo_read_taskhandle)
            self.piezo_read_taskhandle.value = None  # reset it to nullpointer
            daq.DAQmxClearTask(self.pump_write_taskhandle)
            self.pump_write_taskhandle.value = None  # reset it to nullpointer
        except:
            self.log.exception('Could not clear AO/AI Tasks.')

    def read_piezo(self):
        """
        """
        data = np.zeros((1,), dtype=np.float64)
        read = daq.c_int32()
        daq.DAQmxStartTask(self.piezo_read_taskhandle)
        daq.DAQmxReadAnalogF64(self.piezo_read_taskhandle,   # taskhandle
                           1,  # num_samples per channel # default value -1: all available samples
                           self._RWTimeout,  # timeout
                           daq.DAQmx_Val_GroupByChannel,  # fillMode
                           data,  # the array to rea samples into, organized according to fillMode
                           1,  # the size of the array in samples into which samples are read
                           daq.byref(read), # the actual number of samples read from each channel
                           None)  # reserved
        daq.DAQmxStopTask(self.piezo_read_taskhandle)
        return data[0]

    def move_piezo(self, pos, autostart=True, timeout=10):
        """ Move the piezo to the indicated position.

        @params: float position: expected position of the piezo
        @params: bool autostart: True = task started immediately on call of start task. autostart = False can only be used if timing is configured.
        @param: float timeout: RW timeout in seconds

        @returns: None
        """

        if pos>=0 and pos<=90:
            voltage = pos/10
            daq.WriteAnalogScalarF64(self.piezo_write_taskhandles, autostart, timeout, voltage, None)  # parameters passed in: taskHandle, autoStart, timeout, value, reserved
            daq.DAQmxStartTask(self.piezo_write_taskhandles)
            daq.DAQmxStopTask(self.piezo_write_taskhandles)
        else:
            self.log.exception('Position out of boundaries')


    def write_to_pump_ao_channel(self, voltage, autostart=True, timeout=10):
        """ Start / Stop the needle rinsing pump

        @params: float voltage: target voltage to apply to the channel
        @params: bool autostart: True = task started immediately on call of start task. autostart = False can only be used if timing is configured.
        @param: float timeout: RW timeout in seconds

        @returns: None
        """
        if voltage > -10 and voltage < 10:  # read limits from config
            daq.WriteAnalogScalarF64(self.pump_write_taskhandle, autostart, timeout, voltage,
                                     None)  # parameters passed in: taskHandle, autoStart, timeout, value, reserved
            daq.DAQmxStartTask(self.pump_write_taskhandle)
            daq.DAQmxStopTask(self.pump_write_taskhandle)
        else:
            self.log.warning('Voltage not in allowed range.')

    def write_to_do_channel(self, num_samp, digital_write, channel):
        """ use the digital output as trigger """

        num_samples_per_channel = daq.c_int32(num_samp)
        #        digital_write1 = np.array([1,1,1,1,1,1,1,1], dtype=np.uint8)
        digital_read = daq.c_int32()
        daq.DAQmxStartTask(channel)
        daq.DAQmxWriteDigitalLines(channel,  # taskhandle
                                   num_samples_per_channel,  # number of samples to write per channel
                                   True,  # autostart
                                   self._RWTimeout,  # time to wait to write all the samples
                                   daq.DAQmx_Val_GroupByChannel,
                                   # dataLayout: non-interleaved: all samples for first channel, all samples for second channel, ...
                                   digital_write,  # array of 32 bit integer samples to write to the task
                                   daq.byref(digital_read),  # samples per channel successfully written
                                   None)  # reserved for futur use
        daq.DAQmxStopTask(channel)

    def read_do_channel(self, num_samp, channel):
        num_samples_per_channel = daq.c_int32(num_samp)
        sampsPerChanRead = daq.c_int32()
        numBytesPerSamp = daq.c_int32()
        data = np.zeros((num_samp,), dtype=np.uint8)
        daq.DAQmxStartTask(channel)
        daq.DAQmxReadDigitalLines(channel, num_samples_per_channel, self._RWTimeout, daq.DAQmx_Val_GroupByChannel, data,
                                  num_samp, sampsPerChanRead, numBytesPerSamp, None)
        daq.DAQmxStopTask(channel)
        return data
