# -*- coding: utf-8 -*-
"""
Created on Mon Oct 26 14:33:09 2020

@author: barho


This file contains a class for the ASI MS2000 translation stage. 

It is an extension to the hardware code base of Qudi software 
obtained from <https://github.com/Ulm-IQO/qudi/> 
"""

import serial
from time import sleep

from core.module import Base
from interface.motor_interface import MotorInterface
from core.configoption import ConfigOption


class MS2000(Base, MotorInterface):
    """ Class representing the ASI MS 2000 xy translation stage.
    
    Example config for copy-paste:
        
    ms2000:
        module.Class: 'motor.motor_asi_ms2000.MS2000'
        com_port: 'COM4'
        first_axis_label: 'x'
        second_axis_label: 'y'
    """
    
    _com_port = ConfigOption('com_port', missing='error')
    
    _first_axis_label = ConfigOption('first_axis_label', 'x', missing='warn')
    _second_axis_label = ConfigOption('second_axis_label', 'y', missing='warn')

   
    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
    
    def on_activate(self):
        """ Initialization: opening serial port and setting internal attributes
        
        @return int: error code (ok: O)
        """
        
        self._serial_connection = serial.Serial(self._com_port, baudrate=9600, bytesize=8, parity='N', stopbits=1, xonxoff=True)
        
        print(f"Hello i am ms2000 connected on port {self._com_port}")
        # add here the setting of private attributes
        
        return 0
        
    
    def on_deactivate(self):
        """ Close serial port when deactivating the module.
        
        @return int: error code (ok: 0)
        """
        self._serial_connection.close()
        return 0
    
    def get_constraints(self):
        pass
    
    
    
    
    
    def move_rel(self):
        """ 
        
        """
        try:
            pass
        except:
            self.log.error('relative movement of ASI MS2000 translation stage is not possible')
        return pos
    
   
    
    
    def move_abs(self, param_dict):
        try:
            if self._first_axis_label in param_dict:
                self._serial_connection.flushInput()
                new_pos = param_dict[self._first_axis_label]
                cmd = f'MOVE {self._first_axis_label}={new_pos}\r'
                self._serial_connection.write(cmd.encode())
                # eventually: add read_error function to be implemented here
                sleep(0.5) # this timer is necessary to correctly handle .write followed by .query methods. otherwise the serial port is still busy. replace eventually by wait_for_idle method to be implemented
                pos = self.get_pos()
                    
        except:
            self.log.error('absolute movement of ASI MS2000 translation stage is not possible')
            pos = self.get_pos() # retrieve the unchanged position
            
        return {self._first_axis_label: pos}
            
            
   
    def abort(self):
        pass
    
    
    
    
    
#    first version -> define a query function to combine write and readline
#    def get_pos(self):
#        self._serial_connection.flushInput()                    # remove data from input buffer
#        command="W X Y Z\r"                                     # command to ask for the current X Y Z position (W: Where ?)
#        self._serial_connection.write(command.encode())         # send the command using UTF8 encoding (default paramter)
#        position = self._serial_connection.readline().decode()  # absolute coordonates
#        return position.strip()                                 # remove leading and trailing characters
    
    
    def get_pos(self): # only for x axis now (for testing)
        """
        """
        cmd="W X\r" # 'W X Y Z\r'
        pos = float(self.query(cmd))
        return pos
    
    def get_status(self):
        pass
    
    def calibrate(self):
        pass
    
    def get_velocity(self):
        pass
       
    
    def set_velocity(self):
        pass
        
    
##################    
    # helper functions 
    
    def query(self, command):
        """ 
        """
        self._serial_connection.flushInput()
        self._serial_connection.write(command.encode())
        answer = self._serial_connection.readline().decode().strip()[3:]    # [3:] -> remove the leading 'A: '
        return answer
        

    

    


