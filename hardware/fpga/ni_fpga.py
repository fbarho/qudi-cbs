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
import numpy as np
import ctypes
from time import sleep

from core.module import Base
from interface.daq_interface import DaqInterface
from core.configoption import ConfigOption

class Nifpga(Base, DaqInterface):  # rename the DAQInterface into lasercontrolinterface ..
    """ National Instruments FPGA that controls the lasers via an OTF.

    Example config for copy-paste:
        nifpga:
            module.Class: 'fpga.ni_fpga.Nifpga'
            resource: 'RIO0'
            default_bitfile: 'C:\\Users\\sCMOS-1\\Desktop\\LabView\\Current version\\Time lapse\\HUBBLE_FTL_v7_LabView 64bit\\FPGA\\FPGA Bitfiles\\FPGAv0_FPGATarget_FPGAlasercontrol_o8wg7Z4+KAQ.lvbitx'
            wavelengths:
                - '405 nm'
                - '488 nm'
                - '561 nm'
                - '641 nm'

            # copy the bitfile to another location later on..
    """
    # config
    resource = ConfigOption('resource', missing='error')
    default_bitfile = ConfigOption('default_bitfile', missing='error')
    _wavelengths = ConfigOption('wavelengths', missing='error')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        self.session = Session(bitfile=self.default_bitfile, resource=self.resource)
        self.laser3_control = self.session.registers['561']  # use a config entry for this instead in a future version
        self.control_val = self.session.registers['value']  # only for tests, to be removed later
        self.session.reset()
        self.write_value(0)  # set initial value
        self.session.run()

    def on_deactivate(self):
        self.write_value(0)  # make sure to switch the laser off before closing the session
        self.session.close()

    def apply_voltage(self, voltage, channel):
        pass

    def write_value(self, value):
        """
        @param: any numeric type, (recommended int) value: percent of maximal volts to be applied

        if value < 0 or value > 100, value will be rescaled to be in the allowed range """
        value = max(0, value)  # make sure only positive values allowed, reset to zero in case negative value entered
        conv_value = self.convert_value(value)
        self.laser3_control.write(conv_value)
        self.session.run()

    def read_value(self):
        return self.laser3_control.read()
        # return self.control_val.read()  # this is finally not needed because we can read directly the value of laser3_control register

    def convert_value(self, value):
        """ helper function: fpga needs int16 (-32768 to + 32767) data format: do rescaling of value to apply in percent of max value

        apply min function to limit the allowed range """
        return min(int(value/100*(2**15-1)), 36767)  # set to maximum in case value > 100

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
                         'wavelength': self._wavelengths[i]
                         }
                         #'channel': self._ao_channels[i]
                         # }
                         # 'ao_voltage_range': self._ao_voltage_ranges[i]


            laser_dict[dic_entry['label']] = dic_entry

        return laser_dict


# if __name__ == '__main__':
#     bitfile = 'C:\\Users\\sCMOS-1\\Desktop\\LabView\\Current version\\Time lapse\\HUBBLE_FTL_v7_LabView 64bit\\FPGA\\FPGA Bitfiles\\FPGAv0_FPGATarget_FPGAlasercontrol_o8wg7Z4+KAQ.lvbitx'
#     resource = 'RIO0'
#     nifpga = Nifpga(bitfile, resource)
#     nifpga.on_activate()
#     nifpga.write_value(10)
#     print(nifpga.read_value())
#     sleep(2)
#     nifpga.write_value(0)
#     print(nifpga.read_value())
#     sleep(2)
#     nifpga.write_value(5)
#     print(nifpga.read_value())
#     sleep(2)
#     nifpga.on_deactivate()