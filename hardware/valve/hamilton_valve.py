#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 16 13:46:16 2020

@author: fbarho


This file contains the class for the Hamilton modular valve positioner (MVP)

based on file valve.py
Created on Thu Jul 16 16:21:53 2020 
@author: aymerick
putting it to qudi style 
"""

import serial
from time import sleep

from core.module import Base
#from interface.valvepositioner_interface import ValveInterface
from core.configoption import ConfigOption


class HamiltonValve(Base): #, ValveInterface):
    """ Class representing the Hamilton MVP
    
    Example config for copy-paste:
        
    Hamilton:
        module.Class: 'valve.hamilton_valve.HamiltonValve'
        com_port: 'COM1''
    """  
    

    _com_port = ConfigOption("com_port", missing="error")
    
    _valve_state = {} # dictionary holding the valve names as keys and their status as values # {'valve1': status_valve1, ..}

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        
        
    def on_activate(self):
        """ Initialization: open the serial port 
        
        """
        self._serial_connection = serial.Serial(self._com_port, baudrate=9600, bytesize=serial.SEVENBITS, parity=serial.PARITY_ODD, stopbits=serial.STOPBITS_ONE)
        sleep(2) # keep 2 s time delay to ensure that communication has been established
        
        # add the initialisation of every valve # first version: do as if only one valve (a)
        cmd = "aLXR"
        self.write(cmd)
        self.wait_for_idle()
        
        
        
        





#    def OpenConnection(self):
#        """
#        The OpenConnection method is opening the serial communication port and 
#        keeps the output in self.
#        The time delay of 2s is important to keep, else the communication will 
#        not be established and it won't be possible to control the valve.
#        Returns
#        -------
#        None.
#        """
#        try:
#            self.s = serial.Serial(self.port,baudrate=9600,bytesize=serial.SEVENBITS,parity=serial.PARITY_ODD,stopbits=serial.STOPBITS_ONE) # Open the port and keep the output in self.s
#            time.sleep(2)                                                  # Wait 2 seconds
#            self.s.flushInput()                                            # Remove data from input buffer
#            Init="1a\r"                                                    # This str input ask the device to do an auto adressing (First valve="a"; Second valve="b"; ....)
#            self.s.write(Init.encode())                                    # Send the command to the device encoded in UTF-8
#            for i in range (0,Config.NbofValve):                           # We want to initialize every valve adressed 
#                string2Send=Config.ValveNB[i]+"LXR\r"                      # This str input initialize the current valve (Config.ValveNB[0]='a';Config.ValveNB[1]='b')
#                self.s.write(string2Send.encode())                         # Send the command to the device encoded in UTF-8
#                Valve.WaitForIdle(self)                                    # Use the method WaitForIdle to be sure the initialization is finished before sending new instructions
#                self.ValveState["ValvePosition"+str(Config.ValveNB[i])]=1  # Save the position of each valve (After initialization every valve shall be in position 1)          
#                self.ValveState["Outrange"+str(Config.ValveNB[i])]="Values within limits"  # For now all the values are in the limits
#        except AttributeError:
#            print("The port "+str(self.port)+"is already opened")
#        except serial.SerialException:
#            print("Wrong port given, please check the file Config.py")
        
        
    def on_deactivate(self):
        """ Close serial port when deactivating the module.
        
        @returns int: error code (ok: 0)
        """
        self._serial_connection.close()
        return 0
    
    
    def get_status(self):
        """ 
        
        """
        pass
        
#    def Status(self):
#        """
#        The Status method is checking if the one of the valve is doing something or not
#        Returns
#        -------
#        None.
#        """
#        self.s.flushInput()                                             # Remove data from input buffer
#        for i in range (0,Config.NbofValve):                            # Check the state of each valve 
#            self.s.flushInput()                                         # Remove data from input buffer
#            status=Config.ValveNB[i]+"F\r"                              # This str input ask to the current valve his state
#            self.s.write(status.encode())                               # Send the command to the device encoded in UTF-8 
#            Line1=self.s.read()                                         # First line give us useless information so we will not use it
#            Output=self.s.read()                                        # Return "*" if the valve is busy "Y" if the valve is idle
#            self.ValveState["State"+Config.ValveNB[i]]=Output.decode()  # Save the state of the current valve in the dictionnary
     
   
    def get_valve_position(self):
        pass
        
        
        
        
#            def ValvePosition(self,MD):
#        """
#        The ValvePosition method is asking to a specific valve is current position. 
#        The user must indicate the name of the valve (Module adress). 
#        
#        Parameters
#        ----------
#        MD : Module adress
#        
#        Returns
#        -------
#        """
#        try:
#            self.s.flushInput()                                              # Remove data from input buffer
#            Position=str(MD)+"LQP\r"                                         # This str input ask to the valve is current position
#            self.s.write(Position.encode())                                  # Send the command to the device encoded in UTF-8
#            Line1=self.s.read()                                              # First line give us useless information so we will not use it
#            Output=self.s.read()                                             # Return the position of the valve (For example : "3" if the valve is in position 3)
#            self.ValveState["CurrentPosition"+str(MD)]=Output.decode()       # Save the position of the valve in the dictionnary
#        except AttributeError:
#            print("You have to open the connection if you want to communicate with the device")
        
        
    def set_valve_position(self, valve):
        pass
    
    
    
#    def ValveRotation(self,MD,pp):    
#        """
#        The ValveRotation method is sending instructions to a specific valve in order to 
#        rotate the valve. The user must indicate the position of the valve as input and 
#        the name of the valve (Module adress). In order to optimize the rotation the method
#        will choose rotate clockwis or counterclockwise depending of wich one is fastest.
#        Parameters
#        ----------
#        MD : Module adress
#        pp : Position
#        
#        Returns
#        -------
#        """
#        try:
#            if 0>=pp or pp>=Config.ValveConfigPosition[MD]+1:                                              # Check if the valve number is fine or not depending of the valve configuration (Look Config.py)
#                self.ValveState["Outrange"]="Valve number is out of the limits"
#                print("Wrong Value")
#            else :                                                                                         # The idea here is to calulate the oppoite number of our current position depending of the valve configuration
#                if 1<=self.ValveState["ValvePosition"+str(MD)]<=Config.ValveConfigPosition[MD]/2:          # For example if we have 8 positions, the valve looks like this :   8  1  2
#                    opposite=self.ValveState["ValvePosition"+str(MD)]+Config.ValveConfigPosition[MD]/2     #                                                                   7     3
#                else:                                                                                      #                                                                   6  5  4
#                    opposite=self.ValveState["ValvePosition"+str(MD)]-Config.ValveConfigPosition[MD]/2     # So the opposite of 1 is 5; the opposite of 8 is 4; the opposite of 2 is 6; ........
#                                                                                                           # So we add 4 if our current position is lower or even at 4 and we substract 4 if our current position is 4 or upper
#                                                                                                       
#                if self.ValveState["ValvePosition"+str(MD)]<=pp<=opposite:                                 # We check if: Current position < Target position < Opposite of current position (For example : 2<3<6)
#                    string2Send=str(MD)+"LP0"+str(pp)+"R\r"                                                # This str input move the valve in clockwise to target position
#                    self.s.write(string2Send.encode())                                                     # Send the command to the device encoded in UTF-8
#                    self.ValveState["ValvePosition"+str(MD)]=pp                                            # Change the Current position to the position where the valve will be at the end of the rotation
#                    Valve.WaitForIdle(self)                                                                # Wait until the movement is finished
#                
#                elif opposite<=pp<=self.ValveState["ValvePosition"+str(MD)]:                               # We check if: Opposite of current position < Target position < Current position (For example : 3<4<7)
#                    string2Send=str(MD)+"LP1"+str(pp)+"R\r"                                                # This str input move the valve in counterclockwise to target position
#                    self.s.write(string2Send.encode())                                                     # Send the command to the device encoded in UTF-8
#                    self.ValveState["ValvePosition"+str(MD)]=pp                                            # Change the Current position to the position where the valve will be at the end of the rotation
#                    Valve.WaitForIdle(self)                                                                # Wait until the movement is finished
#                    
#                elif self.ValveState["ValvePosition"+str(MD)]<=opposite<=pp:                               # We check if: current position < Opposite of current position < Target position (For example : 1<5<7)
#                    string2Send=str(MD)+"LP1"+str(pp)+"R\r"                                                # This str input move the valve in counterclockwise to target position
#                    self.s.write(string2Send.encode())                                                     # Send the command to the device encoded in UTF-8
#                    self.ValveState["ValvePosition"+str(MD)]=pp                                            # Change the Current position to the position where the valve will be at the end of the rotation
#                    Valve.WaitForIdle(self)                                                                # Wait until the movement is finished
#                    
#                elif opposite<=self.ValveState["ValvePosition"+str(MD)]<=pp:                               # We check if: Opposite of current position < current position < Target position (For example : 2<6<8)
#                    string2Send=str(MD)+"LP0"+str(pp)+"R\r"                                                # This str input move the valve in clockwise to target position
#                    self.s.write(string2Send.encode())                                                     # Send the command to the device encoded in UTF-8
#                    self.ValveState["ValvePosition"+str(MD)]=pp                                            # Change the Current position to the position where the valve will be at the end of the rotation
#                    Valve.WaitForIdle(self)                                                                # Wait until the movement is finished
#                
#                elif pp<=self.ValveState["ValvePosition"+str(MD)]<=opposite:                               # We check if: Target position < current position < Opposite of current position (For example : 2<3<7)
#                    string2Send=str(MD)+"LP1"+str(pp)+"R\r"                                                # This str input move the valve in counterclockwise to target position
#                    self.s.write(string2Send.encode())                                                     # Send the command to the device encoded in UTF-8
#                    self.ValveState["ValvePosition"+str(MD)]=pp                                            # Change the Current position to the position where the valve will be at the end of the rotation
#                    Valve.WaitForIdle(self)                                                                # Wait until the movement is finished
#                
#                elif pp<=opposite<=self.ValveState["ValvePosition"+str(MD)]:                               # We check if: Target position < Oppopsite of current position < current position (For example : 1<3<7)
#                    string2Send=str(MD)+"LP0"+str(pp)+"R\r"                                                # This str input move the valve in clockwise to target position
#                    self.s.write(string2Send.encode())                                                     # Send the command to the device encoded in UTF-8
#                    self.ValveState["ValvePosition"+str(MD)]=pp                                            # Change the Current position to the position where the valve will be at the end of the rotation
#                    Valve.WaitForIdle(self)                                                                # Wait until the movement is finished
#        except AttributeError:
#            print("You have to open the connection if you want to communicate with the device")   
    
    
    
    ## helper function
    
    def wait_for_idle(self):
        pass
    
    
#    def WaitForIdle(self):
#        """
#        The WaitForIdle method wait 1 sec if one of the valve is already working
#        Returns
#        -------
#        None.
#        """
#        Valve.Status(self)                                         # Check the status of each valve
#        WaitingTime=0
#        for i in range (0,Config.NbofValve):                       # Check if the status is idle or not for each device
#            while self.ValveState["State"+Config.ValveNB[i]]!="Y": # While the status is not "Y" (valve is idle) for the current valve, we wait 1 sec
#                time.sleep(1)                                      # We wait 1 sec
#                Valve.Status(self)                                 # Check if the status has changed
#                WaitingTime=WaitingTime+1
#                if WaitingTime >= 15.0:                            # If the status has not changed in 15 sec there might be an error so we stop the "while" and write an error message
#                    print("There is an error")
#                    break


#    def query(self, command):
#        """ Clears the input buffer and queries an utf-8 encoded command
#        
#        @ param string: command: message to send to the serial port
#        
#        @ returns string: answer: formatted and decoded response from serial port
#        """
#        self._serial_connection.flushInput()
#        self._serial_connection.write(command.encode())
#        answer = self._serial_connection.readline().decode().strip()
#        return answer
#
    def write(self, command):
        """ Clears the input buffer and writes an utf-8 encoded command to the serial port 
        
        @ param string: command: message to send to the serial port, in the format "valve adress(a-p) specific command termination" for example "aLXR" (valve a, LX = initialization R = execute command)
        """
        self._serial_connection.flushInput()
        self._serial_connection.write(command.encode())


                  



#if __name__ == "__main__":
#    a=Valve()
#    a.OpenConnection()
#    a.ValveRotation("a",2)
##    a.ValveRotation("b",2)
##    a.ValveRotation("c",2)
##    a.ValveRotation("a",6)
##    a.ValvePosition("a")
##    a.ValveRotation("a",5)
##    a.ValveRotation("a",6)
