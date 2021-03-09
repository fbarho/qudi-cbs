# -*- coding: utf-8 -*-
"""
Created on Tue March 9 2021

@author: barho

This file contains a brightfield controller dummy

It is an extension to the hardware code base of Qudi software
obtained from <https://github.com/Ulm-IQO/qudi/>
"""
from core.module import Base
from interface.brightfield_interface import BrightfieldInterface
from core.configoption import ConfigOption


class BrightfieldDummy(Base, BrightfieldInterface):
    """ Class representing a brightfield controller dummy.

    Example config for copy-paste:

    brightfield_dummy:
        module.Class: 'brightfield_dummy.BrightfieldDummy'
    """

    current_intensity = 0

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initialization
        """
        pass

    def on_deactivate(self):
        """ Deactivation steps
        """
        pass

    def led_control(self, intens):
        """ sets the intensity of the LED to the value intens (0-99)

        @returns: error code: ok = 0 """
        # truncate to allowed range
        value = int(min(max(intens, 0), 99))
        self.current_intensity = value
        return 0
