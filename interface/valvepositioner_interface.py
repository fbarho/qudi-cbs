# -*- coding: utf-8 -*-

"""
This file contains the Qudi Interface file to control Hamilton valves daisychain.

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

from core.interface import abstract_interface_method
from core.meta import InterfaceMetaclass


class ValveInterface(metaclass=InterfaceMetaclass):
    """ This is the Interface class to define the controls for the simple
        step motor device. The actual hardware implementation might have a
        different amount of axis. Implement each single axis as 'private'
        methods for the hardware class, which get called by the general method.
    """


    @abstract_interface_method
    def get_valve_position(self, param_list=None):
        """ Gets current position of the hamilton valves

        @param list param_list: optional, if a specific position of a valve
                                is desired, then the adress of the needed
                                valve should be passed in the param_list.
                                If nothing is passed, then from each valve the
                                position is asked.

        @return dict: with keys being the axis labels and item the current
                      position.
        """
        pass