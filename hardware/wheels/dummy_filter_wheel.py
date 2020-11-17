#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 17 08:53:44 2020

@author: fbarho
"""

import numpy as np
from core.module import Base
from core.configoption import ConfigOption
from interface.filterwheel_interface import FilterwheelInterface


class FilterWheelDummy(Base, FilterwheelInterface):
    """ This class represents a dummy filterwheel

    Example config for copy-paste:

    dummy_wheel:
        module.Class: 'wheels.dummy_filter_wheel.FilterWheelDummy'
        num_filters: 6



    """

    _num_filters = ConfigOption('num_filters', 6)
    position = np.random.randint(1, 7) # generate an arbitrary start value from 1 to 6


    def on_activate(self):
        pass

    def on_deactivate(self):
        pass

    def get_position(self):
        """ Get the current position, from 1 to 6 (or 12) """
        return self.position

    def set_position(self, value):
        """ Set the position to a given value
        """
        if value in range(1, 7):
            self.position = value
        else:  
            self.log.error('Can not go to filter {}. Filterwheel has only 6 positions'.format(value))

        return None
