#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 16 13:46:16 2020

@author: fbarho


This file contains the class for the Hamilton modular valve positioner (MVP)

based on file valve.py
Created on Thu Jul 16 16:21:53 2020 
@author: aymerick
converting it to qudi style


Questions pour Franziska : 
    - pas de try pour l'initializaton. Comment on teste que l'appareil est proprement connecté?
    - on_deactivate : return 0? Why?
    - for the moment no time out for the wait for idle -> should add one.
    - 
"""

import serial
from time import sleep

from core.module import Base
from interface.valvepositioner_interface import ValveInterface
from core.configoption import ConfigOption


class HamiltonValve(Base, ValveInterface):
    """ Class representing the Hamilton MVP
    
    Example config for copy-paste:
        
    hamilton_mvc:
        module.Class: 'valve.hamilton_valve.HamiltonValve'
        com_port: 'COM1'
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
    

#   _com_port = "/dev/ttyS0"   # ConfigOption("com_port", missing="error")
    _com_port = ConfigOption("com_port", missing="error")
    # print(_com_port)

    _num_valves = ConfigOption('num_valves', missing='warn')
    _valve_names = ConfigOption('name', missing='warn')
    _daisychain_IDs = ConfigOption('daisychain_ID', missing='warn')
    _number_outputs = ConfigOption('number_outputs', missing='warn')
    _valve_positions = ConfigOption('valve_positions', [])

    _valve_state = {}  # dictionary holding the valve names as keys and their status as values # {'a': status_valve1, ..}
    
    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initialization: open the serial port
        """
        self._serial_connection = serial.Serial(self._com_port, baudrate=9600, bytesize=serial.SEVENBITS, parity=serial.PARITY_ODD, stopbits=serial.STOPBITS_ONE)
        sleep(2)  # keep 2 s time delay to ensure that communication has been established
        
        # initialization of the daisy chain
        cmd = "1a\r"
        self.write(cmd)
        
        # add the initialisation of every valve. In the daisy chain, the valves 
        # are referenced by a letter, starting with "a". The valve status dictionary
        # is created during this process.
        for n in range(self._num_valves):
            cmd = chr(n+97) + "LXR\r"
            self.write(cmd)
            # self._valve_state[chr(n+97)] = 'Idle'
        self.wait_for_idle()
        self._valve_state = self.get_status()

    def on_deactivate(self):
        """ Close serial port when deactivating the module.
        """
        self._serial_connection.close()

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
        for n in range(self._num_valves):
            cmd = chr(n+97) + "F\r"
            self.write(cmd)
            status = self.read()

            self._valve_state[chr(n+97)] = status
        return self._valve_state

    def get_valve_position(self, valve_address):
        """ Read the valve position using a specific address.
        
        @param str valve_address: (eg. "a")
        @return int position: position of the selected valve
        """
        if valve_address in self._daisychain_IDs:
            cmd = valve_address + "LQP\r"
            self.write(cmd)
            pos = self.read()
            return int(pos)
        else:
            self.log.warn(f'Valve {valve_address} not available.')

    def set_valve_position(self, valve_address, end_pos):
        """ Set the valve position using a specific adress. 
        
        @param str valve_address: eg. "a"
        @param int end_pos: new position
        """
        if valve_address in self._daisychain_IDs:
            start_pos = int(self.get_valve_position(valve_address))
            max_pos = self.get_valve_dict()[valve_address]['number_outputs']
            if end_pos > max_pos:
                self.log.warn(f'Target position out of range for valve {valve_address}. Position not set.')
            else:
                if (start_pos > end_pos and abs(end_pos - start_pos) < max_pos/2) or (start_pos < end_pos and abs(end_pos-start_pos) > max_pos/2):
                    cmd = valve_address + "LP1" + str(end_pos) + "R\r"
                else:
                    cmd = valve_address + "LP0" + str(end_pos) + "R\r"
                self.write(cmd)
        else:
            self.log.warn(f'Valve {valve_address} not available.')

        # sens modification position

    def wait_for_idle(self):
        """ Wait for the valves to be idle. This is important when one wants to 
        read the position of a valve or make sure the valve are not moving before
        starting an injection.
        """
        self.get_status()
        for n in range(self._num_valves):
            while self._valve_state[chr(n+97)] != "Y":
                sleep(0.5)
                self.get_status()

                # this waits on valve 'a' until idle before moving to the next one

    def write(self, command):
        """ Clears the input buffer and writes an utf-8 encoded command to the serial port 
        
        @ param str: command: message to send to the serial port
        """
        self._serial_connection.flushInput()
        self._serial_connection.write(command.encode())
        
    def read(self):
        """ Read the buffer of the valve. The first line does not contain relevant
        information. Only the second line is useful.

        @returns str output: read from the valve buffer
        """
        self._serial_connection.read()
        output = self._serial_connection.read()
        output = output.decode('utf-8')
        # output = self._serial_connection.read().decode('utf-8')
        print(output)
        return output