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
    """
    """
    @abstract_interface_method
    def get_valve_dict(self):
        """ Retrieves a dictionary with the following entries:
                    {'a': {'daisychain_ID': 'a', 'name': str name, 'number_outputs': int number_outputs},
                    {'b': {'daisychain_ID': 'b', 'name': str name, 'number_outputs': int number_outputs},
                    ...
                    }

        @returns: valve_dict
        """
        pass

    @abstract_interface_method
    def get_status(self):
        """ Read the valve status and return it.

        @return dict: containing the valve ID as key and the str status code as value (N=not executed - Y=idle - *=busy)
        """
        pass

    @abstract_interface_method
    def get_valve_position(self, valve_address):
        """ Gets current position of the valve positioner

        @param str valve_address: ID of the valve

        @return int position: position of the valve specified by valve_address
        """
        pass

    @abstract_interface_method
    def set_valve_position(self, valve_address, target_position):
        """ Sets the valve position for the valve specified by valve_address.

        @param str: valve address (eg. "a")
               int: target_position
        """
        pass

    @abstract_interface_method
    def wait_for_idle(self):
        """ Wait for the valves to be idle. This is important when one wants to
        read the position of a valve or make sure the valves are not moving before
        starting an injection.
        """
        pass


