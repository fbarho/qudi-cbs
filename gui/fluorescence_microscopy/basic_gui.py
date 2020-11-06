#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 29 08:13:08 2020

@author: barho


This module contains a GUI for the basic functions of the fluorescence microscopy setup.

Camera image and laser settings. 

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


class CameraSettingDialog(QtWidgets.QDialog):
    """ Create the SettingsDialog window, based on the corresponding *.ui file."""

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_camera_settings.ui')

        # Load it
        super(CameraSettingDialog, self).__init__()
        uic.loadUi(ui_file, self)
        
        

        
        
class BasicWindow(QtWidgets.QMainWindow):
    """ Class defined for the main window (not the module)

    """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_basic.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()
        
        
        
        
class BasicGUI(GUIBase):
    """ Main window containing the basic tools for the fluorescence microscopy setup
    """
    
    # Define connectors to logic modules
    camera_logic = Connector(interface='CameraLogic')
    daq_ao_logic = Connector(interface='DAQaoLogic')
    
      
    # Signals
    sigVideoStart = QtCore.Signal()
    sigVideoStop = QtCore.Signal()
    sigImageStart = QtCore.Signal()
    # sigImageStop = QtCore.Signal() # not used

    
    sigLaserOn = QtCore.Signal()
    sigLaserOff = QtCore.Signal()


    _image = []

    _camera_logic = None
    _daq_ao_logic = None
    _mw = None

    def __init__(self, config, **kwargs):

        # load connection
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initializes all needed UI files and establishes the connectors.
        """

        self._camera_logic = self.camera_logic()
        self._daq_ao_logic = self.daq_ao_logic()

        # Windows
        self._mw = BasicWindow()
        self._mw.centralwidget.hide() # everything is in dockwidgets
        #self._mw.setDockNestingEnabled(True)
        self.initCameraSettingsUI()
        
        
        
        # Menu bar actions
        # Options menu
        self._mw.camera_settings_Action.triggered.connect(self.open_camera_settings)
        
        # camera dockwidget
        # configure the toolbar action buttons and connect signals
        self._mw.start_video_Action.setEnabled(True)
        self._mw.start_video_Action.setChecked(self._camera_logic.enabled)
        self._mw.start_video_Action.triggered.connect(self.start_video_clicked)

        self._mw.take_image_Action.setEnabled(True)
        self._mw.take_image_Action.setChecked(self._camera_logic.enabled)
        self._mw.take_image_Action.triggered.connect(self.take_image_clicked)

        self._camera_logic.sigUpdateDisplay.connect(self.update_data)
        self._camera_logic.sigAcquisitionFinished.connect(self.acquisition_finished)
        self._camera_logic.sigVideoFinished.connect(self.enable_take_image_action)
        
        #self._mw.save_last_image_Action.triggered.connect(self.save_last_image)

        #starting the physical measurement
        self.sigVideoStart.connect(self._camera_logic.start_loop)
        self.sigVideoStop.connect(self._camera_logic.stop_loop)
        self.sigImageStart.connect(self._camera_logic.start_single_acquistion)
        

        # prepare the image display. Data is added in the slot update_data
        # interpret image data as row-major instead of col-major
        pg.setConfigOptions(imageAxisOrder='row-major') 
        
        # hide ROI and menubutton, histogram is activated when data is added to the ImageView
        self._mw.camera_ImageView.ui.roiBtn.hide()
        self._mw.camera_ImageView.ui.menuBtn.hide()
        self._mw.camera_ImageView.ui.histogram.hide()
        
        cmap = pg.ColorMap(pos = np.linspace(0.0, 1.0, 3), color = self._camera_logic.colors)
        self._mw.camera_ImageView.setColorMap(cmap)
        
             
        
        
        
        
        
        
        # laser dockwidget
        self._mw.laser_zero_Action.setEnabled(True)
        self._mw.laser_zero_Action.triggered.connect(self.laser_set_to_zero)
        
        self._mw.laser_on_Action.setEnabled(True)
        # self._mw.laser_on_Action.setChecked(self._daq_ao_logic.enabled) # is this really needed ?
        self._mw.laser_on_Action.triggered.connect(self.laser_on_clicked)
        
        # starting the analog output - interact with logic module
        self.sigLaserOn.connect(self._daq_ao_logic.apply_voltage)
        self.sigLaserOff.connect(self._daq_ao_logic.voltage_off)
        

        # actions on changing laser spinbox values
        self.spinbox_list = [self._mw.laser1_control_SpinBox, self._mw.laser2_control_SpinBox, self._mw.laser3_control_SpinBox, self._mw.laser4_control_SpinBox]
#        
#        self._mw.laser1_control_SpinBox.valueChanged.connect(self.update_laser_dict) # or something like this to be defined..
#        
#        self._mw.laser2_control_SpinBox.valueChanged.connect(lambda: self.set_slider_value(1))
#        
#        self._mw.laser3_control_SpinBox.valueChanged.connect(lambda: self.set_slider_value(2))
#        
#        self._mw.laser4_control_SpinBox.valueChanged.connect(lambda: self.set_slider_value(3))
        # lambda function is used to pass in an additional argument. This allows to use the same slots for all sliders / spinboxes
        # in case lambda does not work well on runtime, check functools.partial
        # or signal mapper ? to explore ..
        

 
        


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
        
        
    # Initialisation of the camera settings windows in the options menu    
    def initCameraSettingsUI(self):
        """ Definition, configuration and initialisation of the camera settings GUI.

        """
        # Create the Camera settings window
        self._cam_sd = CameraSettingDialog()
        # Connect the action of the settings window with the code:
        self._cam_sd.accepted.connect(self.cam_update_settings) # ok button
        self._cam_sd.rejected.connect(self.cam_keep_former_settings) # cancel buttons
        #self._cam_sd.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(self.cam_update_settings)
        
        if self._camera_logic.has_temp == False:
            self._cam_sd.temp_doubleSpinBox.setEnabled(False)
            self._cam_sd.label_3.setEnabled(False)

        # write the configuration to the settings window of the GUI.
        self.cam_keep_former_settings()
        
        
    # slots of the camerasettingswindow
    def cam_update_settings(self):
        """ Write new settings from the gui to the file. 
        """
        self._camera_logic.set_exposure(self._cam_sd.exposure_doubleSpinBox.value())
        self._camera_logic.set_gain(self._cam_sd.gain_doubleSpinBox.value())
        #self._camera_logic.set_temperature(self._cam_sd.temp_doubleSpinBox.value())
     

    def cam_keep_former_settings(self):
        """ Keep the old settings and restores them in the gui. 
        """
        self._cam_sd.exposure_doubleSpinBox.setValue(self._camera_logic._exposure)
        self._cam_sd.gain_doubleSpinBox.setValue(self._camera_logic._gain)
        #self._cam_sd.temperature_doubleSpinBox.setValue(self._camera_logic._temperature)
        

    # slot to open the camerasettingswindow
    def open_camera_settings(self):
        """ Opens the settings menu. 
        """
        self._cam_sd.exec_()
        
        
   
    
    

    # definition of the slots
    # camera dockwidget
    def take_image_clicked(self):
        """ Callback from take_image_Action. Emits a signal that is connected to the logic module 
        and disables the tool buttons
        """
        self.sigImageStart.emit()
        self._mw.take_image_Action.setDisabled(True)
        self._mw.start_video_Action.setDisabled(True)
        self._mw.save_last_image_Action.setDisabled(True)

    def acquisition_finished(self):
        """ Callback from sigAcquisitionFinished. Resets all tool buttons to callable state
        """
        self._mw.take_image_Action.setChecked(False)
        self._mw.take_image_Action.setDisabled(False)
        self._mw.start_video_Action.setDisabled(False)
        self._mw.save_last_image_Action.setDisabled(False)
        

    def start_video_clicked(self):
        """ Callback from start_video_Action. 
        Handling the Start button to stop and restart the counter.
        """
        self._mw.take_image_Action.setDisabled(True)
        if self._camera_logic.enabled:
            self._mw.start_video_Action.setText('Start Video')
            self.sigVideoStop.emit()
        else:
            self._mw.start_video_Action.setText('Stop Video')
            self.sigVideoStart.emit()
            

    def enable_take_image_action(self):
        """ Callback from SigVideoFinished. Resets the state of the take_image_Action tool button
        """
        self._mw.take_image_Action.setEnabled(True)
        

    def update_data(self):
        """ Callback from sigUpdateDisplay in the camera_logic module. 
        Get the image data from the logic and print it on the window
        """
        image_data = self._camera_logic.get_last_image()
        self._mw.camera_ImageView.setImage(image_data)
        self._mw.camera_ImageView.ui.histogram.show()
       
  
    
    
    # laser dockwidget
    def laser_on_clicked(self):
        """
        """
        if self._daq_ao_logic.enabled:
            # laser is initially on
            self._mw.laser_zero_Action.setDisabled(False)
            self._mw.laser_on_Action.setText('Laser On')
            self.sigLaserOff.emit()
        else:
            # laser is initially off
            self._mw.laser_zero_Action.setDisabled(True)
            self._mw.laser_on_Action.setText('Laser Off')
            self.sigLaserOn.emit()
        
    def laser_set_to_zero(self):
        """
        """
        for item in self.spinbox_list: 
            item.setValue(0)

        


        
        




## for testing      
#if __name__ == '__main__':
#    app = QtWidgets.QApplication(sys.argv)
#    # it's required to save a reference to MainWindow.
#    # if it goes out of scope, it will be destroyed.
#    mw = BasicWindow()
#    sys.exit(app.exec())