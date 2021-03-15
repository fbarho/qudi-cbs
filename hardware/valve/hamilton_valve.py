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
        
    Hamilton:
        module.Class: 'valve.hamilton_valve.HamiltonValve'
        com_port: 'COM1'
	    name:
    	daisychain_ID:'a'
        output_number:
            
     @returns int: error code (ok: O)
    """  
    

#   _com_port = "/dev/ttyS0"   # ConfigOption("com_port", missing="error")
    _com_port = ConfigOption("com_port", missing="error")
    print(_com_port)
    _valve_n = 3 # Number of valves connected in daisy chain
    _valve_state = {} # dictionary holding the valve names as keys and their status as values # {'a': status_valve1, ..}
    _valve_positions = {'a':8, 'b': 2, 'c': 2}
    
    # def __init__(self, config, **kwargs):
    #     super().__init__(config=config, **kwargs)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        

    def on_activate(self):
        """ Initialization: open the serial port 
        
        """
        self._serial_connection = serial.Serial(self._com_port, baudrate=9600, bytesize=serial.SEVENBITS, parity=serial.PARITY_ODD, stopbits=serial.STOPBITS_ONE)
        sleep(2) # keep 2 s time delay to ensure that communication has been established
        
        # initialization of the daisy chain
        cmd = "1a\r"
        self.write(cmd)
        
        # add the initialisation of every valve. In the daisy chain, the valves 
        # are referenced by a letter, starting with "a". The valve status dictionary
        # is created during this process.
        for n in range(self._valve_n):
            cmd = chr(n+97) + "LXR\r"
            self.write(cmd)
            self._valve_state[chr(n+97)] = 'Idle'
            

    def on_deactivate(self):
        """ Close serial port when deactivating the module.
        
        @returns int: error code (ok: 0)
        """
        self._serial_connection.close()

    def get_valve_dict(self):
        pass
    
    
    def get_status(self):
        """ Read the valve status and return it. 
        
        @return str: status code (N=not executed - Y=idle - *=busy)
        """
        for n in range(self._valve_n):
            cmd = chr(n+97) + "F\r"
            self.write(cmd)
            status = self.read()

            self._valve_state[chr(n+97)] = status
        return self._valve_state
            
     
    def get_valve_position(self, valve_adress):
        """ Read the valve position using a specific adress. 
        
        @param str: valve adress (eg. "a") 
        @return int: position of the selected valve
        """
        
        cmd = valve_adress + "LQP\r"
        self.write(cmd)
        pos = self.read()
        return(int(pos))

    #ajouter try except
        
        
    def set_valve_position(self, valve_adress, end_pos):
        """ Set the valve position using a specific adress. 
        
        @param str: valve adress (eg. "a")
               int: end_pos
        """
        
        start_pos = int(self.get_valve_position(valve_adress))
        max_pos = self._valve_positions[valve_adress]
        if (start_pos>end_pos and abs(end_pos-start_pos)<max_pos/2) or (start_pos<end_pos and abs(end_pos-start_pos)>max_pos/2):
            cmd = valve_adress + "LP1" + str(end_pos) + "R\r"
        else:
            cmd = valve_adress + "LP0" + str(end_pos) + "R\r"
        self.write(cmd)

        # sens modification position
        
        
    def wait_for_idle(self):
        """ Wait for the valves to be idle. This is important when one wants to 
        read the position of a valve or make sure the valve are not moving before
        starting an injection.
        
        """
        
        self.get_status()
        for n in range(self._valve_n):
            while(self._valve_state[chr(n+97)]!="Y"):
                sleep(0.5)
                self.get_status()


    def write(self, command):
        """ Clears the input buffer and writes an utf-8 encoded command to the serial port 
        
        @ param str: command: message to send to the serial port
        """
        self._serial_connection.flushInput()
        self._serial_connection.write(command.encode())
        
    def read(self):
        """ Read the buffer of the valve. The first line does not contain relevant
        information. Only the second line is useful.

        @ Returns : string : read from the valve buffer
        """
        self._serial_connection.read()
        output = self._serial_connection.read().decode('utf-8')
        return(output)


if __name__ == "__main__":
    valve=HamiltonValve()
    valve.on_activate()
    valve.wait_for_idle()
    print(valve.get_valve_position("a"))
    
    valve.set_valve_position("a",8)
    valve.wait_for_idle()
    print(valve.get_valve_position("a"))
    valve.set_valve_position("a",7)
    valve.wait_for_idle()
    print(valve.get_valve_position("a"))
    valve.set_valve_position("a",2)
    valve.wait_for_idle()
    print(valve.get_valve_position("a"))
    valve.on_deactivate()

