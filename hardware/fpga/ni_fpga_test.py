#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed March 8 2021

@author: barho

This file contains a class for the NI-FPGA.

This module is an extension to the hardware code base of Qudi software
obtained from <https://github.com/Ulm-IQO/qudi/>
"""

from nifpga import Session
# import numpy as np
# import ctypes
from time import sleep

# from core.module import Base
# from interface.lasercontrol_interface import LaserControlInterface
from core.configoption import ConfigOption


class Nifpga(object):
    """ National Instruments FPGA that controls the lasers via an OTF.
    """
    # indicate bitfile path
    # simple test with one laser line 561 nm and writing a list of values to this
    # bitfile = 'C:\\Users\\sCMOS-1\\qudi-cbs\\hardware\\fpga\\FPGA\\FPGA Bitfiles\\FPGAv0_FPGATarget_FPGAlasercontrol_pdDEc3yii+w.lvbitx'
    # multicolor imaging bitfile
    bitfile = 'C:\\Users\\sCMOS-1\\qudi-cbs\\hardware\\fpga\\FPGA\\FPGA Bitfiles\\FPGAv0_FPGATarget_FPGAtriggercamer_u12WjFsC0U8.lvbitx'
    resource = 'RIO0'

    def __init__(self, *args, **kwargs):
        super().__init__()

    def on_activate(self):
        """ Required initialization steps when module is called."""
        self.session = Session(bitfile=self.bitfile, resource=self.resource)
        print(self.session._registers)
        # self.n_lines = self.session.registers['N']
        # self.laser_control = self.session.registers['561 Laser Power']

    def on_deactivate(self):
        """ Required deactivation steps. """
        self.session.close()
        print('session closed')

    # def apply_voltage_values(self):
    #     self.session.reset()
    #
    #     print(self.n_lines.read())
    #     self.n_lines.write(5)
    #     print(self.n_lines.read())
    #
    #     data = [4, 0, 4, 2, 0]
    #     conv_values = [self.convert_value(item) for item in data]
    #     print(conv_values)
    #     self.laser_control.write(conv_values)
    #     self.session.run()


    def convert_value(self, value):
        """ helper function: fpga needs int16 (-32768 to + 32767) data format: do rescaling of value to apply in percent of max value

        apply min function to limit the allowed range """
        return min(int(value/100*(2**15-1)), 36767)  # set to maximum in case value > 100
    #
    # def read_values(self):
    #     """ for tests - returns the (converted) values applied to the registers """
    #     return self.laser1_control.read(), self.laser2_control.read(), self.laser3_control.read(), self.laser4_control.read()
    #
    # def get_dict(self):
    #     """ Retrieves the register name (and the corresponding voltage range???) for each analog output from the
    #     configuration file and associates it to the laser wavelength which is controlled by this channel.
    #
    #     @returns: laser_dict
    #     """
    #     laser_dict = {}
    #
    #     for i, item in enumerate(
    #             self._wavelengths):  # use any of the lists retrieved as config option, just to have an index variable
    #         label = 'laser{}'.format(i + 1)  # create a label for the i's element in the list starting from 'laser1'
    #
    #         dic_entry = {'label': label,
    #                      'wavelength': self._wavelengths[i],
    #                      'channel': self._registers[i]
    #                      }
    #                      # 'ao_voltage_range': self._ao_voltage_ranges[i]
    #
    #         laser_dict[dic_entry['label']] = dic_entry
    #
    #     return laser_dict
    #
    # ### new 3 march 2021 test with tasks
    # ## these methods must be callable from the lasercontrol logic
    # def close_default_session(self):
    #     """ This method is called before another bitfile than the default one shall be loaded
    #
    #     (in this version it actually does the same as on_deactivate (we could also just call this method ..  but this might evolve)
    #     """
    #     for i in range(len(self._registers)):
    #         self.apply_voltage(0, self._registers[i])   # make sure to switch the lasers off before closing the session
    #     self.session.close()
    #
    # def restart_default_session(self):
    #     """ This method allows to restart the default session"""
    #     self.on_activate()
    #
    # def start_task_session(self, bitfile):
    #     """ loads a bitfile used for a specific task """
    #     self.session = Session(bitfile=bitfile, resource=self.resource)
    #
    # def end_task_session(self):
    #     self.session.close()
    #
    # #specific methods associated to a bitfile
    # def run_test_task_session(self):
    #     #using for a simple test the FPGA_laser_control_Qudi bitfile (control only for the 561 nm laser)
    #     # laser_control = self.session.registers['561']  # '561' register
    #     # self.session.reset()
    #     # self.apply_voltage(0, laser_control)  # set initial value to each channel
    #     # self.session.run()
    #     # # write some values
    #     # conv_value = self.convert_value(5)
    #     # laser_control.write(conv_value)
    #     # self.session.run()
    #     # sleep(1)
    #     # conv_value = self.convert_value(0)
    #     # laser_control.write(conv_value)
    #     # self.session.run()
    #     # sleep(1)
    #     # conv_value = self.convert_value(4)
    #     # laser_control.write(conv_value)
    #     # self.session.run()
    #     # sleep(1)
    #     # conv_value = self.convert_value(0)
    #     # laser_control.write(conv_value)
    #     # self.session.run()
    #
    #     #with array
    #     laser_control = self.session.registers['561 Laser Power']
    #     self.session.reset()
    #     self.session.run()
    #     values = [5, 0, 5, 0, 5]
    #     conv_values = [self.convert_value(item) for item in values]
    #     print(conv_values)
    #     laser_control.write(conv_values)
    #     self.session.run()

if __name__ == '__main__':
    fpga = Nifpga()
    fpga.on_activate()
    # fpga.apply_voltage_values()
    fpga.on_deactivate()





