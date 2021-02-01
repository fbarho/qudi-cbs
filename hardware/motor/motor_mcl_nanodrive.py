"""
Created on Mon Feb 1 2021

@author: fbarho

This file contains a class for the Mad city labs piezo controller.

It is an extension to the hardware code base of Qudi software
obtained from <https://github.com/Ulm-IQO/qudi/>
"""
import ctypes

from core.module import Base
from interface.motor_interface import MotorInterface
from core.configoption import ConfigOption


class MCLNanoDrive(Base):  # , MotorInterface
    """ Class representing the MCL Piezo controller.

    Example config for copy-paste:

    mcl:
        module.Class: 'motor.motor_mcl_nanodrive.MCLNanoDrive'
        dll_location: 'C:\\Program Files\\Mad City Labs\\NanoDrive\\Madlib.dll'   # path to library file
    """

    dll_location = ConfigOption('dll_location', missing='error')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        self.dll = ctypes.cdll.LoadLibrary(self.dll_location)

    def on_deactivate(self):
        pass
