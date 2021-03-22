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

        self.ref['valves'].set_valve_position('b', 2)
        self.ref['valves'].wait_for_idle()
        self.ref['valves'].set_valve_position('c', 2)
        self.ref['valves'].wait_for_idle()

    def runTaskStep(self):
        """ Task step (iterating over the number of injection steps to be done) """
        print(f'step: {self.step_counter+1}')

        if self.hybridization_list[self.step_counter]['product'] is not None:  # then it is an injection step
            # set the 8 way valve to the position corresponding to the product
            product = self.hybridization_list[self.step_counter]['product']
            valve_pos = self.buffer_dict[product]
            self.ref['valves'].set_valve_position('a', valve_pos)
            self.ref['valves'].wait_for_idle()

            # as an initial value, set the pressure to 0 mbar
            self.ref['flow'].set_pressure(0.0)
            # start the pressure regulation
            self.ref['flow'].start_pressure_regulation_loop(self.hybridization_list[self.step_counter]['flowrate'])
            # start counting the volume of buffer or probe
            sampling_interval = 0.5  #in seconds
            self.ref['flow'].start_volume_measurement(self.hybridization_list[self.step_counter]['volume'], sampling_interval)

            # put this thread to sleep until the target volume is reached
            # is it a problem that this thread becomes inresponsive when using sleep function ?
            ready = self.ref['flow'].target_volume_reached
            while not ready:
                sleep(2)
                ready = self.ref['flow'].target_volume_reached
            self.ref['flow'].stop_pressure_regulation_loop()
            sleep(2)  # waiting time to wait until last regulation step is finished, afterwards reset pressure to 0
            self.ref['flow'].set_pressure(0.0)
        else:  # product is none: then it is an incubation step
            time = self.hybridization_list[self.step_counter]['time']
            print(f'Incubation time.. {time} s')
            self.ref['valves'].set_valve_position('c', 1)
            self.ref['valves'].wait_for_idle()
            sleep(self.hybridization_list[self.step_counter]['time'])
            # maybe it is better to split into small intervals to keep the thread responsive ?????
            self.ref['valves'].set_valve_position('c', 2)
            self.ref['valves'].wait_for_idle()
            print('Incubation time finished')

        self.step_counter += 1
        return self.step_counter < len(self.hybridization_list)

    def pauseTask(self):
        """ Pause """
        self.log.info('Pause task called')

    def resumeTask(self):
        """ Resume """
        self.log.info('Resume task called')

    def cleanupTask(self):
        """ Cleanup """
        self.ref['flow'].set_pressure(0.0)
        self.ref['valves'].set_valve_position('b', 1)
        self.ref['valves'].wait_for_idle()
        self.ref['valves'].set_valve_position('a', 1)
        self.ref['valves'].wait_for_idle()
        self.ref['valves'].set_valve_position('c', 1)
        self.ref['valves'].wait_for_idle()

        self.log.info('Cleanup task called')

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
             'product': 'Buffer4',
             'volume': 100,
             'flowrate': 250,
             'time': None},
            {'step_number': 2,
             'procedure': 'Hybridization',
             'product': None,
             'volume': None,
             'flowrate': None,
             'time': 20},
            {'step_number': 3,
             'procedure': 'Hybridization',
             'product': 'Buffer1',
             'volume': 120,
             'flowrate': 500,
             'time': None}
        ]

