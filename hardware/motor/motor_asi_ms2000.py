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
        third_axis_label: 'z'
    """

    _com_port = ConfigOption("com_port", missing="error")
    _baud_rate = ConfigOption("baud_rate", 9600, missing="warn")

    _first_axis_label = ConfigOption("first_axis_label", "x", missing="warn")
    _second_axis_label = ConfigOption("second_axis_label", "y", missing="warn")
    _third_axis_label = ConfigOption("third_axis_label", None)  # default case is intended for 2 axes stage, for 3 axes specify in config
   
    _conversion_factor = 10.0  # user will send positions in um, stage uses 0.1 um
    axis_list = None

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initialization: opening serial port and setting internal attributes
        
        @returns int: error code (ok: O)
        """

        self._serial_connection = serial.Serial(
            self._com_port, baudrate=self._baud_rate, bytesize=8, parity="N", stopbits=1, xonxoff=True
        )

        # add here the setting of private attributes
        self._timeout = 15

        # create a list as iterator for methods that need a specified axis to apply to
        axis_list = [self._first_axis_label, self._second_axis_label, self._third_axis_label]  # this serves only as local iterator
        self.axis_list = []
        for item in axis_list:
            if isinstance(item, str):
                self.axis_list.append(item)

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
        
        @ param dict param_dict: Dictionary with axis name and relative movement in units of µm
        
        @ returns dict pos: Dictionary with the axis name and the current position in µm
        
        """
        pos = {} 

        try:
            for axis_label in param_dict:
                if (
                    axis_label in self.axis_list
                ):  # to ensure that only configured axes are taken into account in case param_dict indicates other axes
                    step = param_dict[axis_label] * self._conversion_factor
                    cmd = f"R {axis_label}={step}\r"
                    self.write(cmd)
                    # eventually: add here read_error function to be implemented
                    self.wait_for_idle()  # this timer is necessary to correctly handle write followed by query method. otherwise the serial port is still busy. replace eventually by wait_for_idle method to be implemented
                    # see get_pos method. it cannot be called directly because we would again iterate over the axis_list.
                    cmd = f"W {axis_label}\r"
                    pos[axis_label] = (
                        float(self.query(cmd)[3:]) / self._conversion_factor
                    )  # [3:] -> remove the leading 'A: '

                else:
                    self.log.warn(f"axis {axis_label} is not configured")
        except:
            self.log.error("relative movement of ASI MS2000 translation stage is not possible")
            pos = {}
            
        return pos
        # pos contains only the axes that were moved. Should the others also be returned ?

    def move_abs(self, param_dict):
        """ Moves the stage to the given position.
        
        @ param dict param_dict: Dictionary with axis name and absolute position in units of µm
        
        @ returns dict pos: Dictionary with axis name and current position in µm
        
        """
        pos = {}

        try:
            for axis_label in param_dict:
                if (
                    axis_label in self.axis_list
                ):  # to ensure that only configured axes are taken into account in case param_dict indicates other axes
                    new_pos = param_dict[axis_label] * self._conversion_factor
                    cmd = f"M {axis_label}={new_pos}\r"
                    self.write(cmd)
                    # eventually: add here read_error function to be implemented
                    self.wait_for_idle()  # this timer is necessary to correctly handle write followed by query method. otherwise the serial port is still busy. replace eventually by wait_for_idle method to be implemented
                    # see get_pos method. it cannot be called directly because we would again iterate over the axis_list.
                    cmd = f"W {axis_label}\r"
                    pos[axis_label] = (
                        float(self.query(cmd)[3:]) / self._conversion_factor
                    )  # [3:] -> remove the leading 'A: '

                else:
                    self.log.warn(f"axis {axis_label} is not configured")

        except:
            self.log.error("relative movement of ASI MS2000 translation stage is not possible")
            pos = {}

        return pos

    def abort(self):
        """ Stops all active motors, stops a movement of the stage if ongoing. 
        
        Attention, the (following) command N+1 is not performed! The N+2 command is again performed.
        new tests on RAMM: following command is perfomed normally ..
        
        @ returns: error code (ok: 0)
        """
        cmd = "\\r"
        self.write(cmd)
        # self._serial_connection.flush() # tried this, also flushInput(), to enable command N+1. does not work.... to be improved
        return 0

    def get_pos(self):
        """ Gets current position of the translation stage.
        
        @ returns: dict pos: Dictionary with axis name and current position of the translation stage
        """
        pos = {}

        for (
            axis_label
        ) in self.axis_list:  # this list is generated above to generalize more easily in case that more axes are added
            cmd = f"W {axis_label}\r"
            pos[axis_label] = float(self.query(cmd)[3:]) / self._conversion_factor  # [3:] -> remove the leading 'A: '

        return pos

    def get_status(self):
        """ Queries if any motors are still busy moving following a serial command. 
        
        @ returns: str status: 'N' if no motors running, 'B' if busy
        """
        cmd = "/ \r"
        status = self.query(cmd)
        return status

    def calibrate(self):
        # to be defined what should be done here: AALIGN, ZEROING, HOMING ?
        """ Performs self-calibration of the axis motor drive circuit. 
        
        @ returns error code (ok: 0)
        """
        # iterate over axes, for generalization. other option is to hardcode 'AA X Y \r' when always the two axes are used
        for axis_label in self.axis_list:
            cmd = f"AA {axis_label} \r"
            self.write(cmd)
        return 0

    def get_velocity(self):
        """ Gets the current velocity of the translation stage (for the specified axis).
        
        @ returns dict velo: Dictionary with axis name and current velocity of the specified axis. 
        """
        velo = {}

        for axis_label in self.axis_list:
            cmd = f"S {axis_label}?\r"
            velo[axis_label] = float(
                self.query(cmd)[5:]
            )  # format from query ':A X=5.745920', remove leading X= and convert to float

        return velo

    def set_velocity(self, param_dict):
        """ Sets the velocity at which the stage moves. 
        Velocity is set in millimeters per second. Maximum speed is 7.5 mm/s for standard 6.5 mm pitch leadscrews.
        
        @ param dict param_dict: Dictionary with axis name and target velocity in mm/s
        
        @ returns dict: velo: Dictionary with axis name and current velocity in mm/s 
        """
        velo = {}

        try:
            for axis_label in param_dict:
                if axis_label in self.axis_list:
                    new_velo = param_dict[axis_label]
                    cmd = f"S {axis_label}={new_velo}\r"
                    self.write(cmd)
                    self.wait_for_idle()  # this timer is necessary to correctly handle write followed by query methods. otherwise the serial port is still busy. replace eventually by wait_for_idle method to be implemented
                    cmd = f"S {axis_label}?\r"
                    velo[axis_label] = float(self.query(cmd)[5:])

                else:
                    self.log.warn("specified axis {axis_label} not available")

        except:
            self.log.error("could not set new velocity")
            velo = {}

        return velo

    ##################

    # other custom functions not defined in the MotorInterface
    def wait_for_idle(self):
        """ Checks every 1 s until timeout if a motor is running from a serial command 'B' or not 'N'
        
        @ returns None
        """
        status = self.get_status()
        waiting_time = 0
        while status != "N":
            sleep(0.5)
            waiting_time = waiting_time + 0.5
            status = self.get_status()
            if waiting_time >= self._timeout:
                self.log.error("ASI MS2000 translation stage timeout occurred")
                break

    def homing_xy(self):
        """ Moves the stage to homeposition on x and y axes.
        Motor stops when hardware or firmware limit switch is encountered.
        
        @ returns: error code (ok: 0)
        """
        cmd = "! X Y \r"
        self.write(cmd)
        return 0

    def set_to_zero(self):
        """ Sets the current position as the origin
        
        @ returns: error code (ok: 0)
        """
        cmd = "Z \r"
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
