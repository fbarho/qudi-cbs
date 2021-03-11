# -*- coding: utf-8 -*-
"""
Created on Wed Mars 3 2021

@author: barho

This file contains a class for the PI 3 axis stage.

It is an extension to the hardware code base of Qudi software
obtained from <https://github.com/Ulm-IQO/qudi/>
"""

# from core.module import Base
# from interface.motor_interface import MotorInterface
# from core.configoption import ConfigOption
from time import sleep

from pipython import GCSDevice, pitools


class PIMotorStage(object):
    """ Class representing the PI 3 axis positioning motor stage

    Example config for copy-paste:

    pi_stage:
        module.Class: 'motor.motor_motor_pi_3axis_stage.PIMotorStage'
        # controllername: 'E816'
        # serialnumber: '110059675'
        # pos_min: 0  # in um
        # pos_max: 100  # in um
        # max_step: 1  # in um
    """

    _controllername = 'C863'  #check if correct
    _serialnum = '0019550121'

    # def __init__(self, config, **kwargs):
    #     super().__init__(config=config, **kwargs)

    def __init__(self, *args, **kwargs):
        super().__init__()

    def on_activate(self):
        # open the daisy chain connection
        self.pidevice_c863_x = GCSDevice('C-863')  # controller name to be read from config later  # x_axis controller # master device
        self.pidevice_c863_y = GCSDevice('C-863')  # controller name to be read from config later  # y_axis controller
        self.pidevice_c863_z = GCSDevice('C-863')  # controller name to be read from config later  # z_axis controller

        self.pidevice_c863_x.OpenUSBDaisyChain(description='0019550121')  # serial number
        self.daisychainid = self.pidevice_c863_x.dcid
        print(f'Daisychainid: {self.daisychainid}')
        self.pidevice_c863_z.ConnectDaisyChainDevice(1, self.daisychainid)
        self.pidevice_c863_x.ConnectDaisyChainDevice(2, self.daisychainid)
        self.pidevice_c863_y.ConnectDaisyChainDevice(3, self.daisychainid)
        print('\n{}:\n{}'.format(self.pidevice_c863_x.GetInterfaceDescription(), self.pidevice_c863_x.qIDN()))
        print('\n{}:\n{}'.format(self.pidevice_c863_y.GetInterfaceDescription(), self.pidevice_c863_y.qIDN()))
        print('\n{}:\n{}'.format(self.pidevice_c863_z.GetInterfaceDescription(), self.pidevice_c863_z.qIDN()))

        # testing
        print('initialize connected stages...')
        pitools.startup(self.pidevice_c863_x)

        rangemin = self.pidevice_c863_x.qTMN()
        rangemax = self.pidevice_c863_x.qTMX()
        curpos = self.pidevice_c863_x.qPOS()
        print(f'{rangemin}, {rangemax}, {curpos}')

        x_axis = self.pidevice_c863_x.axes[0]
        print(x_axis)
        answer = self.pidevice_c863_x.qSVO()
        print(answer)
        # self.pidevice_c863_x.RON(x_axis, values=1)
        # self.pidevice_c863_x.FNL(x_axis)
        sleep(5)
        self.pidevice_c863_x.MOV(x_axis, 0.0)

        # rangemin = self.pidevice_c863_y.qTMN()
        # rangemax = self.pidevice_c863_y.qTMX()
        # curpos = self.pidevice_c863_y.qPOS()
        # print(f'{rangemin}, {rangemax}, {curpos}')
        #
        # y_axis = str(self.pidevice_c863_y.axes[0])
        # print(y_axis)
        # answer = self.pidevice_c863_y.qSVO()
        # print(answer)
        #
        # rangemin = self.pidevice_c863_z.qTMN()
        # rangemax = self.pidevice_c863_z.qTMX()
        # curpos = self.pidevice_c863_z.qPOS()
        # print(f'{rangemin}, {rangemax}, {curpos}')
        #
        # z_axis = str(self.pidevice_c863_z.axes[0])
        # print(z_axis)
        # answer = self.pidevice_c863_z.qSVO()
        # print(answer)

    def on_deactivate(self):
        """ Required deactivation steps
        """
        self.pidevice_c863_x.CloseDaisyChain()
        self.pidevice_c863_x.CloseConnection()

    # def main(self):
    #     """Search controllers on interface, show dialog and connect a controller."""
    #     with GCSDevice() as pidevice:
    #         print('search for controllers...')
    #         devices = pidevice.EnumerateUSB()
    #         for i, device in enumerate(devices):
    #             print('{} - {}'.format(i, device))
    #         # item = int(input('select device to connect: '))
    #         # pidevice.ConnectTCPIPByDescription(devices[item])
    #         # pidevice.ConnectUSB(devices[item])
    #         # print('connected: {}'.format(pidevice.qIDN().strip()))








if __name__ == '__main__':
    pistage = PIMotorStage()
    # pistage.main()
    pistage.on_activate()
    pistage.on_deactivate()





