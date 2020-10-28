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
    #_second_axis_label = ConfigOption('second_axis_label', 'y', missing='warn')
        


   
    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
    
    def on_activate(self):
        """ Initialization: opening serial port and setting internal attributes
        
        @returns int: error code (ok: O)
        """
        
        self._serial_connection = serial.Serial(self._com_port, baudrate=9600, bytesize=8, parity='N', stopbits=1, xonxoff=True)
        
        # add here the setting of private attributes
        self._timeout = 15
        
        return 0
        
    
    def on_deactivate(self):
        """ Close serial port when deactivating the module.
        
        @returns int: error code (ok: 0)
        """
        self._serial_connection.close()
        return 0
    
    
    
    def get_constraints(self):
        pass
    
    
    
    
    
    def move_rel(self, param_dict):
        """ Moves the stage in the given direction relative to the current position.
        
        @ param dict param_dict: Dictionary with axis name and relative movement in units of 0.1 µm
        
        @ returns 
        
        """
        try:
            if self._first_axis_label in param_dict:
                new_pos = param_dict[self._first_axis_label]
                cmd = f'R {self._first_axis_label}={new_pos}\r'
                self.write(cmd)
                # eventually: add here read_error function to be implemented 
                self.wait_for_idle() # this timer is necessary to correctly handle write followed by query method. otherwise the serial port is still busy. replace eventually by wait_for_idle method to be implemented
                pos = self.get_pos()
            
            else:
                self.log.error('specified axis not available')
                pos = self.get_pos()
                
        except:
            self.log.error('relative movement of ASI MS2000 translation stage is not possible')
            pos = self.get_pos()  # retrieve the unchanged position
            
        return {self._first_axis_label: pos}
    
   
    
    
    def move_abs(self, param_dict):
        """ Moves the stage to the given position.
        
        @ param dict param_dict: Dictionary with axis name and absolute position in units of 0.1 µm
        
        @ returns 
        
        """
        try:
            if self._first_axis_label in param_dict:
                new_pos = param_dict[self._first_axis_label]
                cmd = f'M {self._first_axis_label}={new_pos}\r'
                self.write(cmd)
                # eventually: add here read_error function to be implemented 
                self.wait_for_idle() # this timer is necessary to correctly handle write followed by query methods. otherwise the serial port is still busy. replace eventually by wait_for_idle method to be implemented
                pos = self.get_pos()
                
            else:
                self.log.error('specified axis not available')
                pos = self.get_pos()
                    
        except:
            self.log.error('absolute movement of ASI MS2000 translation stage is not possible')
            pos = self.get_pos() 
            
        return {self._first_axis_label: pos}
            
            
   
    def abort(self):
        """ Stops all active motors, stops a movement of the stage if ongoing. 
        
        Attention, the (following) command N+1 is not performed! The N+2 command is again performed.
        
        @ returns: error code (ok: 0)
        """
        cmd="\\r"
        self.write(cmd)
        # self._serial_connection.flush() # tried this, also flushInput(), to enable command N+1. does not work.... to be improved 
        return 0
    
    
    def get_pos(self): # only for x axis now (for testing)
        """ Gets current position of the translation stage.
        
        @ returns: float pos: position
        """
        cmd="W X\r" # 'W X Y Z\r'
        pos = float(self.query(cmd)[3:])  # [3:] -> remove the leading 'A: '
        return pos
    
    
    def get_status(self):
        """ Queries if any motors are still busy moving following a serial command. 
        
        @ returns: str status: 'N' if no motors running, 'B' if busy
        """
        cmd="/ \r"
        status = self.query(cmd)
        return status
    
    
    def calibrate(self): # only x axis for testing
        # to be defined what should be done here: AALIGN, ZEROING, HOMING ? 
        """ Performs self-calibration of the axis motor drive circuit. 
        
        @ returns error code (ok: 0)
        """
        cmd="AA X\r"
        self.write(cmd)
        return 0
    
    
    def get_velocity(self):
        """ Gets the current velocity of the translation stage (for the specified axis).
        
        @ returns float velo: current velocity of the specified axis. 
        """
        cmd="S X?\r" 
        velo = float(self.query(cmd)[5:])   # format from query ':A X=5.745920', remove leading X= and convert to float
        return velo
       
    
    def set_velocity(self, param_dict):
        """ Sets the velocity at which the stage moves. 
        Velocity is set in millimeters per second. Maximum speed is 7.5 mm/s for standard 6.5 mm pitch leadscrews.
        
        @ param dict param_dict: Dictionary with axis name and target velocity in mm/s
        
        @ returns dict: velocity: Dictionary with axis name and current velocity in mm/s -> to be done !!!
        """
        try:
            if self._first_axis_label in param_dict:
                self._serial_connection.flushInput()
                new_velo = param_dict[self._first_axis_label]
                cmd = f'S {self._first_axis_label}={new_velo}\r'
                self._serial_connection.write(cmd.encode())
                # eventually: add here read_error function to be implemented 
                self.wait_for_idle() # this timer is necessary to correctly handle write followed by query methods. otherwise the serial port is still busy. replace eventually by wait_for_idle method to be implemented
                velo = self.get_velocity()
                
            else:
                self.log.error('specified axis not available')
                velo = self.get_velocity()
                    
        except:
            self.log.error('could not set new velocity')
            velo = self.get_velocity()
            
        return {self._first_axis_label: velo}
        
    
##################    
        
    # other custom functions not defined in the MotorInterface
    def wait_for_idle(self):
        """ Checks every 1 s until timeout if a motor is running from a serial command 'B' or not 'N'
        
        @ returns None
        """
        status = self.get_status()
        waiting_time = 0
        while status != 'N':
            sleep(0.5)
            waiting_time = waiting_time + 0.5
            status = self.get_status()
            if waiting_time >= self._timeout:
                self.log.error('ASI MS2000 translation stage timeout occured')
                break
            
    
    def homing(self):
        """ Moves the stage to homeposition on x and y axes.
        Motor stops when hardware or firmware limit switch is encountered.
        
        @ returns: error code (ok: 0)
        """
        cmd="! X Y \r"
        self.write(cmd)
        return 0
    
    def set_to_zero(self):
        """ Sets the current position as the origin
        
        @ returns: error code (ok: 0)
        """
        cmd="Z \r"
        self.write(cmd)
        return 0   
    
    
    # helper functions 
    
    def query(self, command):
        """ Clears the input buffer and queries an utf-8 encoded command
        
        @ param string: command: message to send to the serial port, typically in the format 'COMMANDSHORTCUT [AXIS=value]\r'
        
        @ returns string: answer: formatted and decoded response from serial port
        """
        self._serial_connection.flushInput()
        self._serial_connection.write(command.encode())
        answer = self._serial_connection.readline().decode().strip()        
        return answer
    
    def write(self, command):
        """ Clears the input buffer and writes an utf-8 encoded command to the serial port 
        
        @ param string: command: message to send to the serial port, typically in the format 'COMMANDSHORTCUT [AXIS=value]\r'
        """
        self._serial_connection.flushInput()
        self._serial_connection.write(command.encode())
        

    

    


