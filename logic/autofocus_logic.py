#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov  3 10:27:15 2020

@author: fbarho


A module to control the piezo.

The piezo carries the microscope objective and is used to manually set the focus and for autofocus procedure

"""

from core.connector import Connector
#from core.configoption import ConfigOption
from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic
from qtpy import QtCore

import pyqtgraph as pg
import numpy as np
from time import sleep


class AutofocusLogic(GenericLogic):
    """ Controls the piezo and the focus and autofocus procedures
    
    Config pour copy-paste
    
        autofocus_logic:
        module.Class: 'autofocus_logic.AutofocusLogic'
        connect: 
            piezo: 'piezo_dummy'
                
            
    
    """

    # declare connectors
    piezo = Connector(interface='PiezoInterface')
    
    
    # signals
    sigUpdateDisplay = QtCore.Signal()
    
    
    # attributes    
    _position = None
    _step = 0.1 # maybe use configoption instead 
    
    refresh_time = 100 # time in ms for timer interval



    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.threadlock = Mutex()
        


    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._piezo = self.piezo()
        
        self.enabled = False # timetrace not running on activation of the module
        
        # initialize the timer, it is then started when start_tracking is called
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)  # instead of using intervall. Repetition is then handled via the slot loop (and start_tracking at first)
        self.timer.timeout.connect(self.loop)
        
        
    def on_deactivate(self):
        """ Required deactivation.
        """
        pass
        
    def start_tracking(self):
        """ slot called from gui signal sigTimetraceOn. 
        """
        self.enabled = True      
        self.timer.start()
        
    def stop_tracking(self):
        """ slot called from gui signal sigTimetraceOff
        """
        self.timer.stop()
        self.enabled = False
        
    
    def loop(self):
        """ Execute step in the data recording loop, get the current z position
        """
        self._position = self._piezo.get_position() # to be replaced with get physical data
        self.sigUpdateDisplay.emit()
        if self.enabled:
            self.timer.start(self.refresh_time)


        
    def get_last_position(self):
        """ called from GUI to get the last registered position
        """
        return self._position
    
    
    def set_step(self, step):
        """ sets the step entered on the GUI by the user
        """
        self._piezo.set_step(step)
        

        

        
    

