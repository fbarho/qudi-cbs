#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb 10 2021

@author: barho

This file contains a class for the NI-FPGA.

This module is an extension to the hardware code base of Qudi software
obtained from <https://github.com/Ulm-IQO/qudi/>
"""

from nifpga import Session
# import numpy as np
# import ctypes
from time import sleep

from core.module import Base
from interface.lasercontrol_interface import LaserControlInterface
from core.configoption import ConfigOption


class Nifpga(Base, LaserControlInterface):
    """ National Instruments FPGA that controls the lasers via an OTF.

    Example config for copy-paste:
        nifpga:
            module.Class: 'fpga.ni_fpga.Nifpga'
            resource: 'RIO0'
            default_bitfile: 'C:\\Users\\sCMOS-1\\qudi-cbs\\hardware\\fpga\\FPGA\\FPGA Bitfiles\\FPGAv0_FPGATarget_FPGAlasercontrol_mLrb7Qjptmw.lvbitx'
            wavelengths:
                - '405 nm'
                - '488 nm'
                - '561 nm'
                - '640 nm'
            registers:
                - '405'
                - '488'
                - '561'
                - '640'
            registers_qpd:
                - 'x'
                - 'y'
                - 'i'

            # registers represent something like the channels.
            # The link between registers and the physical channel is made in the labview file from which the bitfile is generated.
    """
    # config
    resource = ConfigOption('resource', missing='error')
    default_bitfile = ConfigOption('default_bitfile', missing='error')
    _wavelengths = ConfigOption('wavelengths', missing='error')
    _registers = ConfigOption('registers', missing='error')


    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Required initialization steps when module is called."""
        self.session = Session(bitfile=self.default_bitfile, resource=self.resource)
        self.laser1_control = self.session.registers[self._registers[0]]
        self.laser2_control = self.session.registers[self._registers[1]]
        self.laser3_control = self.session.registers[self._registers[2]]
        self.laser4_control = self.session.registers[self._registers[3]]
        # maybe think of replacing the hardcoded version of assigning the registers to an identifier by something more dynamic
        self.session.reset()
        for i in range(len(self._registers)):
            self.apply_voltage(0, self._registers[i])  # set initial value to each channel

        self.QPD_X_read = self.session.registers[self._registers_qpd[0]]
        self.QPD_Y_read = self.session.registers[self._registers_qpd[1]]
        self.QPD_I_read = self.session.registers[self._registers_qpd[2]]
        self.Integration_time_us = self.session.registers[self._registers_qpd[3]]
        self.Duration_ms = self.session.registers[self._registers_qpd[4]]
        self.Task = self.session.registers[self._registers_qpd[5]]

        self.Task.write(False)
        self.session.run()

    def on_deactivate(self):
        """ Required deactivation steps. """
        for i in range(len(self._registers)):
            self.apply_voltage(0, self._registers[i])   # make sure to switch the lasers off before closing the session
        self.session.close()

    def read_qpd(self, _integration_time_us):
        self.Integration_time_us.write(_integration_time_us)
        self.Task.write(True)
        self.session.run()

        X = self.QPD_X_read.read()
        Y = self.QPD_Y_read.read()
        I = self.QPD_I_read.read()
        d = self.Duration_ms.read()
        print([X, Y, I, d])

    def apply_voltage(self, voltage, channel):
        """ Writes a voltage to the specified channel.

        @param: any numeric type, (recommended int) voltage: percent of maximal volts to be applied

        if value < 0 or value > 100, value will be rescaled to be in the allowed range

        @param: str channel: register name corresponding to the physical channel (link made in labview bitfile), example '405'

        @returns: None
        """
        # maybe think of replacing the hardcoded version of comparing channels with registers by something more dynamic
        value = max(0, voltage)
        conv_value = self.convert_value(value)
        if channel == self._registers[0]:  # '405'
            self.laser1_control.write(conv_value)
        elif channel == self._registers[1]:  # '488'
            self.laser2_control.write(conv_value)
        elif channel == self._registers[2]:  # '561'
            self.laser3_control.write(conv_value)
        elif channel == self._registers[3]:  # '640'
            self.laser4_control.write(conv_value)
        else:
            pass
        self.session.run()

    def convert_value(self, value):
        """ helper function: fpga needs int16 (-32768 to + 32767) data format: do rescaling of value to apply in percent of max value

        apply min function to limit the allowed range """
        return min(int(value/100*(2**15-1)), 36767)  # set to maximum in case value > 100

    def read_values(self):
        """ for tests - returns the (converted) values applied to the registers """
        return self.laser1_control.read(), self.laser2_control.read(), self.laser3_control.read(), self.laser4_control.read()

    def get_dict(self):
        """ Retrieves the register name (and the corresponding voltage range???) for each analog output from the
        configuration file and associates it to the laser wavelength which is controlled by this channel.

        @returns: laser_dict
        """
        laser_dict = {}

        for i, item in enumerate(
                self._wavelengths):  # use any of the lists retrieved as config option, just to have an index variable
            label = 'laser{}'.format(i + 1)  # create a label for the i's element in the list starting from 'laser1'

            dic_entry = {'label': label,
                         'wavelength': self._wavelengths[i],
                         'channel': self._registers[i]
                         }
                         # 'ao_voltage_range': self._ao_voltage_ranges[i]

            laser_dict[dic_entry['label']] = dic_entry

        return laser_dict

    ### new 3 march 2021 test with tasks
    ## these methods must be callable from the lasercontrol logic
    def close_default_session(self):
        """ This method is called before another bitfile than the default one shall be loaded

        (in this version it actually does the same as on_deactivate (we could also just call this method ..  but this might evolve)
        """
        for i in range(len(self._registers)):
            self.apply_voltage(0, self._registers[i])   # make sure to switch the lasers off before closing the session
        self.session.close()

    def restart_default_session(self):
        """ This method allows to restart the default session"""
        self.on_activate()
        #or is it sufficient to just call         self.session = Session(bitfile=self.default_bitfile, resource=self.resource) and session run ?

    def start_task_session(self, bitfile):
        """ loads a bitfile used for a specific task """
        self.session = Session(bitfile=bitfile, resource=self.resource)

    def end_task_session(self):
        self.session.close()

    # methods associated to a specific bitfile
    def run_test_task_session(self, data):
        """
        associated bitfile 'C:\\Users\\sCMOS-1\\qudi-cbs\\hardware\\fpga\\FPGA\\FPGA Bitfiles\\FPGAv0_FPGATarget_FPGAlasercontrol_pdDEc3yii+w.lvbitx'
        @param: list data: values to be applied to the output (in % of max intensity) """
        #using for a simple test the FPGA_laser_control_Qudi bitfile (control only for the 561 nm laser)
        n_lines = self.session.registers['N']
        laser_control = self.session.registers['561 Laser Power']
        self.session.reset()

        print(n_lines.read())
        n_lines.write(5)
        print(n_lines.read())

        conv_values = [self.convert_value(item) for item in data]
        print(conv_values)
        laser_control.write(conv_values)
        self.session.run()


    def run_multicolor_imaging_task_session(self, z_planes, wavelength, values):
        """
        associated bitfile 'C:\\Users\\sCMOS-1\\qudi-cbs\\hardware\\fpga\\FPGA\\FPGA Bitfiles\\FPGAv0_FPGATarget_FPGAtriggercamer_u12WjFsC0U8.lvbitx'
        @param: int z_planes: number of z planes
        @param: int list wavelength: list containing the number of the laser line to be addressed: 0: BF, 1: 405, 2: 488, 3: 561, 4: 640
        @param: int list values: intensity in per cent to be applied to the line given at the same index in the wavelength list
        """
        num_lines = self.session.registers['N laser lines']  # number of laser lines
        num_z_pos = self.session.registers['N Z positions']  # number of z positions
        num_images_acquired = self.session.registers['Images acquired']  # indicator register how many images have been acquired
        laser_lines = self.session.registers['Laser lines']  # list containing numbers of the laser lines which should be addressed
        laser_power = self.session.registers['Laser power']  # list containing the intensity in % to apply (to the element at the same index in laser_lines list

        self.session.reset()

        conv_values = [self.convert_value(item) for item in values]
        n = len(wavelength)
        num_lines.write(n)
        num_z_pos.write(z_planes)
        laser_lines.write(wavelength)
        laser_power.write(conv_values)

        self.session.run()  # wait_until_done=True
        num_imgs = num_images_acquired.read()
        print(num_imgs)








