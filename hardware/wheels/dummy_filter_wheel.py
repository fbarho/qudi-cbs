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
        filterpositions:
            - 1
            - 2
            - 3
            - 4
            - 5
            - 6
        filters:
            - '700 +/- 37 nm'
            - '600 +/- 25 nm'
            - '488 - 491 / 561 nm'
            - '525 +/- 22.5 nm'
            - '617 +/- 36 nm'
            - '460 +/- 25 nm'
        allowed_lasers:
            - [True, True, True, True]
            - [True, True, True, True]
            - [True, True, True, True]
            - [True, True, True, True]
            - [True, True, True, False]
            - [True, False, True, True]

            # please specify for all elements corresponding information in the same order.
            # allowed lasers:
            # entries corresponding to [laser1_allowed, laser2_allowed, laser3_allowed, laser4_allowed, ..]
            # see also the config for the daq ao output to associate a laser number to a wavelength
    """

    _num_filters = ConfigOption('num_filters', 6)
    _filternames = ConfigOption('filters', missing='error')
    _positions = ConfigOption('filterpositions', missing='error')
    _allowed_lasers = ConfigOption('allowed_lasers', missing='error')

    position = np.random.randint(1, 7)  # generate an arbitrary start value from 1 to 6

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_activate(self):
        """ Module activation method """
        if len(self._filternames) != self._num_filters or len(self._positions) != self._num_filters or len(self._allowed_lasers) != self._num_filters:
            self.log.warning('Please specify name, position, and allowed lasers for each filter')

    def on_deactivate(self):
        pass

    def get_position(self):
        """ Get the current position. """
        return self.position

    def set_position(self, value):
        """ Set the position to a given value

        @ params: int: value: new position

        @ returns: int: error code: ok = 0
        """
        if value in range(1, self._num_filters + 1):
            self.position = value
            err = 0
        else:  
            self.log.error(f'Can not go to filter {value}. Filterwheel has only {self._num_filters} positions')
            err = -1
        return err

    def get_filter_dict(self):
        """ Retrieves a dictionary with the following entries:
                    {'filter1': {'label': 'filter1', 'name': str(name), 'position': 1, 'lasers': bool list},
                     'filter2': {'label': 'filter2', 'name': str(name), 'position': 2, 'lasers': bool list},
                    ...
                    }

                    # to be modified: using position as label suffix can lead to problems when not all positions are
                    used and gives some constraints

        @returns: filter_dict
        """
        filter_dict = {}

        for i, item in enumerate(
                self._filternames):  # use any of the lists retrieved as config option, just to have an index variable
            label = 'filter{}'.format(i + 1)  # create a label for the i's element in the list starting from 'filter1'

            dic_entry = {'label': label,
                         'name': self._filternames[i],
                         'position': self._positions[i],
                         'lasers': self._allowed_lasers[i]}

            filter_dict[dic_entry['label']] = dic_entry

        return filter_dict
