# -*- coding: utf-8 -*-
"""
A module for controlling a white light source

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

from core.connector import Connector
from logic.generic_logic import GenericLogic
from qtpy import QtCore
from core.util.mutex import Mutex


class BrightfieldLogic(GenericLogic):
    """

    Example config for copy-paste:

    brightfield_logic:
        module.Class: 'brightfield_logic.BrightfieldLogic'
        connect:
            controller: 'ms2000'
    """

    # declare connectors
    controller = Connector(interface='BrightfieldInterface')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # threading  # might be needed here
        # self._threadlock = Mutex()


    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._controller = self.controller()

    def on_deactivate(self):
        pass

    def led_control(self, intens):
        self._controller.led_control(intens)

    def led_off(self):
        self.led_control(0)

    def led_on_max(self):
        self.led_control(99)