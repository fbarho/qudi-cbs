#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed June 6 2021

@author: fbarho

This file contains a class for the Measurement Computing DAQ

This module is an extension to the hardware code base of Qudi software
obtained from <https://github.com/Ulm-IQO/qudi/>
"""

from core.module import Base
from core.configoption import ConfigOption
import numpy as np
from time import sleep


class McDAQ():
    """ Class representing the measurement computing DAQ.

    Example config for copy-paste:
        mc_daq:
            module.Class: 'daq.measurement_computing_daq.McDAQ'

    """

    # config

    # def __init__(self, config, **kwargs):
    #     super().__init__(config=config, **kwargs)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_activate(self):
        """ Initialization steps when module is called.
        """
        pass

    def on_deactivate(self):
        """ Required deactivation steps.
        """
        pass

if __name__ == '__main__':
    mc_daq = McDAQ()
    mc_daq.on_activate()