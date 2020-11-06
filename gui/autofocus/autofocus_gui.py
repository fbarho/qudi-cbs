#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Nov  6 07:31:15 2020

@author: fbarho

This module holds the gui for the focus tracking and autofocus procedure
"""

import os
import sys

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy import uic
import pyqtgraph as pg

from gui.guibase import GUIBase
from core.connector import Connector

import numpy as np



        
class PiezoSettingDialog(QtWidgets.QDialog):
    """ Create the SettingsDialog window, based on the corresponding *.ui file."""

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_piezo_settings.ui')

        # Load it
        super(PiezoSettingDialog, self).__init__()
        uic.loadUi(ui_file, self)


class AutofocusWindow(QtWidgets.QMainWindow):
    """ Class defined for the main window (not the module)

    """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_autofocus.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()


class AutofocusGUI(GUIBase):
    """ Main window containing the GUI for focus and autofocus control
    """
    
    # Define connectors to logic modules
    autofocus_logic = Connector(interface='AutofocusLogic')
    
      
    # Signals  
    sigTimetraceOn = QtCore.Signal()
    sigTimetraceOff = QtCore.Signal()

    # attributes
    _autofocus_logic = None
    _mw = None

    def __init__(self, config, **kwargs):

        # load connection
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initializes all needed UI files and establishes the connectors.
        """

        self._autofocus_logic = self.autofocus_logic()

        # Windows
        self._mw = AutofocusWindow()
        self._mw.centralwidget.hide() # everything is in dockwidgets
        #self._mw.setDockNestingEnabled(True)
        self.initPiezoSettingsUI()
        
        
        
        # Menu bar actions
        # Options menu
        self._mw.piezo_settings_Action.triggered.connect(self.open_piezo_settings)
               
        
        # piezo dockwidget
        self._mw.z_track_Action.setEnabled(True) # button can be used # just to be sure, this is the initial state defined in designer
        self._mw.z_track_Action.setChecked(self._autofocus_logic.enabled) # checked state takes the same bool value as enabled attribute in logic (enabled = 0: no timetrace running) # button is defined as checkable in designer
        self._mw.z_track_Action.triggered.connect(self.start_z_track_clicked)
        
        # start and stop the physical measurement
        self.sigTimetraceOn.connect(self._autofocus_logic.start_tracking)
        self._autofocus_logic.sigUpdateDisplay.connect(self.update_timetrace)
        self.sigTimetraceOff.connect(self._autofocus_logic.stop_tracking)

        
        
        # some data for testing
        #self.t_data = np.arange(100) # not needed if the x axis stays fixed (no moving ticks)
        self.y_data = np.zeros(100) # for initialization
        

        
        # create a reference to the line object (this is returned when calling plot method of pg.PlotWidget)
        self._timetrace = self._mw.piezo_PlotWidget.plot(self.y_data)
           
        

 
        


    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self._mw.close()


    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()
        
        
    # Initialisation of the piezo settings windows in the options menu    
    def initPiezoSettingsUI(self):
        """ Definition, configuration and initialisation of the camera settings GUI.

        """
        # Create the Piezo settings window
        self._piezo_sd = PiezoSettingDialog()
        # Connect the action of the settings window with the code:
        self._piezo_sd.accepted.connect(self.piezo_update_settings) # ok button
        self._piezo_sd.rejected.connect(self.piezo_keep_former_settings) # cancel buttons
        #self._piezo_sd.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(self.piezo_update_settings)

        # write the configuration to the settings window of the GUI.
        self.piezo_keep_former_settings()
        
        
    # slots of the piezosettingswindow
    def piezo_update_settings(self):
        """ Write new settings from the gui to the file. 
        """
        self._autofocus_logic.set_step(self._piezo_sd.step_doubleSpinBox.value())

  
    def piezo_keep_former_settings(self):
        """ Keep the old settings and restores them in the gui. 
        """
        self._piezo_sd.step_doubleSpinBox.setValue(self._autofocus_logic._step)

        
    # slot to open the camerasettingswindow
    def open_piezo_settings(self):
        """ Opens the settings menu. 
        """
        self._piezo_sd.exec_()
    
    
    

    # definition of the slots    
    def start_z_track_clicked(self):
        if self._autofocus_logic.enabled: # timetrace already running
            self._mw.z_track_Action.setText('Piezo: Start Tracking')
            self.sigTimetraceOff.emit()
        else: 
            self._mw.z_track_Action.setText('Piezo: Stop Tracking')
            self.sigTimetraceOn.emit()
            
            
    def update_timetrace(self):
        # t data not needed, only if it is wanted that the axis labels move also. then see variant 2 from pyqtgraph.examples scrolling plot
        #self.t_data[:-1] = self.t_data[1:] # shift data in the array one position to the left, keeping same array size
        #self.t_data[-1] += 1 # add the new last element
        self.y_data[:-1] = self.y_data[1:] # shfit data one position to the left ..
        self.y_data[-1] = self._autofocus_logic.get_last_position()

        
        #self._timetrace.setData(self.t_data, self.y_data) # x axis values running with the timetrace
        self._timetrace.setData(self.y_data) # x axis values do not move
        
    
    
