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
import yaml


class Task(InterruptableTask):
    """ Fluidic injection task

    Config example pour copy-paste:
    FluidicsTask:
        module: 'fluidics_task'
        needsmodules:
            valves: 'valve_logic'
            pos: 'positioning_logic'
            flow: 'flowcontrol_logic'
        config:
            path_to_user_config: 'C:/Users/sCMOS-1/qudi_files/qudi_task_config_files/fluidics_task_RAMM.yaml'
    """
    # ===============================================================================================================
    # Generic Task methods
    # ===============================================================================================================

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print('Task {0} added!'.format(self.name))
        self.user_config_path = self.config['path_to_user_config']

    def startTask(self):
        """ """
        self.log.info('started Task')

        # disable actions on Fluidics GUI (except from measurement mode)
        self.ref['valves'].disable_valve_positioning()
        self.ref['flow'].disable_pressure_setting()
        self.ref['pos'].disable_positioning_actions()

        # load user parameters
        self.load_user_parameters()
        self.step_counter = 0

        self.ref['valves'].set_valve_position('b', 2)
        self.ref['valves'].wait_for_idle()
        self.ref['valves'].set_valve_position('c', 2)
        self.ref['valves'].wait_for_idle()

    def runTaskStep(self):
        """ Task step (iterating over the number of injection steps to be done) """
        print(f'step: {self.step_counter+1}')

        if self.hybridization_list[self.step_counter]['product'] is not None:  # an injection step
            # set the 8 way valve to the position corresponding to the product
            product = self.hybridization_list[self.step_counter]['product']
            valve_pos = self.buffer_dict[product]
            self.ref['valves'].set_valve_position('a', valve_pos)
            self.ref['valves'].wait_for_idle()

            # pressure regulation
            self.ref['flow'].set_pressure(0.0)  # as initial value
            self.ref['flow'].start_pressure_regulation_loop(self.hybridization_list[self.step_counter]['flowrate'])
            # start counting the volume of buffer or probe
            sampling_interval = 1  # in seconds
            self.ref['flow'].start_volume_measurement(self.hybridization_list[self.step_counter]['volume'], sampling_interval)

            ready = self.ref['flow'].target_volume_reached
            while not ready:
                sleep(2)
                ready = self.ref['flow'].target_volume_reached
            self.ref['flow'].stop_pressure_regulation_loop()
            sleep(2)  # waiting time to wait until last regulation step is finished, afterwards reset pressure to 0
            self.ref['flow'].set_pressure(0.0)
        else:  # an incubation step
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

        # enable actions on Fluidics GUI
        self.ref['valves'].enable_valve_positioning()
        self.ref['flow'].enable_pressure_setting()
        self.ref['pos'].enable_positioning_actions()

        self.ref['flow'].set_pressure(0.0)
        self.ref['valves'].set_valve_position('b', 1)
        self.ref['valves'].wait_for_idle()
        self.ref['valves'].set_valve_position('a', 1)
        self.ref['valves'].wait_for_idle()
        self.ref['valves'].set_valve_position('c', 1)
        self.ref['valves'].wait_for_idle()

        self.log.info('Cleanup task finished')

    # ===============================================================================================================
    # Helper functions
    # ===============================================================================================================

    # ------------------------------------------------------------------------------------------
    # user parameters
    # ------------------------------------------------------------------------------------------

    def load_user_parameters(self):
        try:
            with open(self.user_config_path, 'r') as stream:
                self.user_param_dict = yaml.safe_load(stream)  # yaml.full_load when yaml package updated

                self.injections_path = self.user_param_dict['injections_path']

            self.load_injection_parameters()

        except Exception as e:  # add the type of exception
            self.log.warning(f'Could not load user parameters for task {self.name}: {e}')

    def load_injection_parameters(self):
        """ """
        try:
            with open(self.injections_path, 'r') as stream:
                documents = yaml.safe_load(stream)  # yaml.full_load when yaml package updated
                buffer_dict = documents['buffer']  #  example {3: 'Buffer3', 7: 'Probe', 8: 'Buffer8'}
                self.hybridization_list = documents['hybridization list']

            # invert the buffer dict to address the valve by the product name as key
            self.buffer_dict = dict([(value, key) for key, value in buffer_dict.items()])

        except Exception as e:
            self.log.warning(f'Could not load hybridization sequence for task {self.name}: {e}')



