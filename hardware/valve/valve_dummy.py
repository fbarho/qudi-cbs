from time import sleep
from core.module import Base
from interface.valvepositioner_interface import ValveInterface
from core.configoption import ConfigOption


class ValveDummy(Base, ValveInterface):
    """ Dummy implementation of the microfluidics pump and flowrate sensor

    Example config for copy-paste:

    valve_dummy:
        module.Class: 'valve.valve_dummy.ValveDummy'
        num_valves: 3
        daisychain_ID:
            - 'a'
            - 'b'
            - 'c'
        name:
            - 'Buffer 8-way valve'
            - 'Syringe 2-way valve'
            - 'RT rinsing 2-way valve'
        number_outputs:
            - 8
            - 2
            - 2
        valve_positions:
            - - '1'
              - '2'
              - '3'
              - '4'
              - '5'
              - '6'
              - '7'
              - '8'
            - - '1: Rinse needle'
              - '2: Inject probe'
            - - '1: Syringe'
              - '2: Pump'

    # please specify for all elements corresponding information in the same order,
    # starting from the first valve in the daisychain (valve 'a')

    """
    _num_valves = ConfigOption('num_valves', missing='warn')
    _valve_names = ConfigOption('name', missing='warn')
    _daisychain_IDs = ConfigOption('daisychain_ID', missing='warn')
    _number_outputs = ConfigOption('number_outputs', missing='warn')
    _valve_positions = ConfigOption('valve_positions', [])

    init_pos = 1  # initial  position for all valves
    position_dict = {}


    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        # initialize the position_dict:
        for i in range(self._num_valves):
            self.set_valve_position(self._daisychain_IDs[i], self.init_pos)

    def on_deactivate(self):
        pass

    def get_valve_dict(self):
        """ Retrieves a dictionary with the following entries:
                            {'a': {'daisychain_ID': 'a', 'name': str name, 'number_outputs': int number_outputs},
                            {'b': {'daisychain_ID': 'b', 'name': str name, 'number_outputs': int number_outputs},
                            ...
                            }

                @returns: valve_dict
                """
        valve_dict = {}

        for i in range(self._num_valves):
            dic_entry = {'daisychain_ID': self._daisychain_IDs[i],
                         'name': self._valve_names[i],
                         'number_outputs': self._number_outputs[i],
                         }

            valve_dict[dic_entry['daisychain_ID']] = dic_entry

        return valve_dict

    def get_status(self):
        """ Read the valve status and return it.

        @return dict: containing the valve ID as key and the str status code as value (N=not executed - Y=idle - *=busy)
        """
        status = ['Y' for item in self._daisychain_IDs]
        status_dict = dict(zip(self._daisychain_IDs, status))
        return status_dict

    def get_valve_position(self, valve_address):
        """ Gets current position of the hamilton valve

        @param str valve_address: ID of the valve

        @return int position: position of the valve specified by valve_address
        """
        if valve_address in self._daisychain_IDs:
            return self.position_dict[valve_address]
        else:
            self.log.warn(f'Valve {valve_address} not available.')

    def set_valve_position(self, valve_address, target_position):
        """ Sets the valve position for the valve specified by valve_address.

        @param str: valve address (eg. "a")
               int: target_position
        """
        if valve_address in self._daisychain_IDs:
            max_pos = self.get_valve_dict()[valve_address]['number_outputs']
            if target_position > max_pos:
                self.log.warn(f'Target position out of range for valve {valve_address}. Position not set.')
            else:
                self.position_dict[valve_address] = target_position
                self.log.info(f'Set {self.get_valve_dict()[valve_address]["name"]} to position {target_position}')
                # self.log.info(f'Set valve {valve_address} to position {target_position}')
        else:
            self.log.warn(f'Valve {valve_address} not available.')

    def wait_for_idle(self):
        """ Wait for the valves to be idle. This is important when one wants to
        read the position of a valve or make sure the valve are not moving before
        starting an injection.
        """
        sleep(0.5)