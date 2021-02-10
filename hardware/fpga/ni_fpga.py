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

from core.module import Base
from interface.lasercontrol_interface import LaserControlInterface
from core.configoption import ConfigOption


class Nifpga(Base, LaserControlInterface):
    """ National Instruments FPGA that controls the lasers via an OTF.

    Example config for copy-paste:
        nifpga:
            module.Class: 'fpga.ni_fpga.Nifpga'
            resource: 'RIO0'
            default_bitfile: 'C:\\Users\\sCMOS-1\\Desktop\\LabView\\Current version\\Time lapse\\HUBBLE_FTL_v7_LabView 64bit\\FPGA\\FPGA Bitfiles\\FPGAv0_FPGATarget_FPGAlasercontrol_mLrb7Qjptmw.lvbitx'
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

            # registers represent something like the channels.
            # The link between registers and the physical channel is made in the labview file from which the bitfile is generated.
            # copy the bitfile to another location later on..
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
        self.session.run()

    def on_deactivate(self):
        """ Required deactivation steps. """
        for i in range(len(self._registers)):
            self.apply_voltage(0, self._registers[i])   # make sure to switch the lasers off before closing the session
        self.session.close()

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
