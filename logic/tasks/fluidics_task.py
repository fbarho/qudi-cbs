# -*- coding: utf-8 -*-
"""
Fluidics task for taskrunner.

Extension to Qudi.

Created: March 16, 2021
Author: fbarho

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
from logic.generic_task import InterruptableTask
from time import sleep


class Task(InterruptableTask):
    """ Fluidic injection task

    Config example pour copy-paste:
    FluidicsTask:
        module: 'fluidics_task'
        needsmodules:
            valves: 'valve_logic'
            pos: 'positioning_logic'
            flow: 'flowcontrol_logic'
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print('Task {0} added!'.format(self.name))


    def startTask(self):
        """ """
        self._load_injection_parameters()
        self.log.info('Injection parameters loaded')
        self.step_counter = 0



    def runTaskStep(self):
        """ Task step (iterating over the number of injection steps to be done) """
        # set the 8 way valve to the position corresponding to the product
        product = self.hybridization_list[self.step_counter]['product']
        valve_pos = self.buffer_dict[product]
        self.ref['valves'].set_valve_position('a', valve_pos)  # replace a by a dynamic information instead of valve name 'a'

        # add here a waiting procedure to be sure the valve is in its specified position

        # as an initial value, set the pressure to 0 mbar
        self.ref['flow'].set_pressure(0)
        self.ref['flow'].regulate_pressure(self.hybridization_list[self.step_counter]['flowrate'])

        self.step_counter += 1
        return self.step_counter < len(self.hybridization_list)

    def pauseTask(self):
        """ Pause """
        pass


    def resumeTask(self):
        """ Resume """
        pass


    def cleanupTask(self):
        """ Cleanup """
        pass

    def _load_injection_parameters(self):
        """ """
        buffer_dict = {1: 'Buffer1', 2: 'Buffer2', 3: 'Buffer3', 4: 'Buffer4', 7: 'MerfishProbe'}  # later version: read this from file
        # invert the buffer dict to address the valve by the product name as key
        self.buffer_dict = dict([(value, key) for key, value in buffer_dict.items()])
        print(self.buffer_dict)

        self.probe_dict = {1: 'Probe1', 2: 'Probe2', 3: 'Probe3'}
        # inversion might be needed as for the buffer_dict.. to check

        self.hybridization_list = [
            {'step_number': 1,
             'procedure': 'Hybridization',
             'product': 'Buffer2',
             'volume': 10,
             'flowrate': 20,
             'time': None},
            {'step_number': 2,
             'procedure': 'Hybridization',
             'product': None,
             'volume': None,
             'flowrate': None,
             'time': 60},
            {'step_number': 3,
             'procedure': 'Hybridization',
             'product': 'MerfishProbe',
             'volume': 2,
             'flowrate': 1,
             'time': None}
        ]




