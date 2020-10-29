#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 29 08:13:08 2020

@author: barho


This module contains a GUI for the basic functions of the fluorescence microscopy setup.

current state: handling the camera image 
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
    
      
    # Signals
    sigVideoStart = QtCore.Signal()
    sigVideoStop = QtCore.Signal()
    sigImageStart = QtCore.Signal()
    sigImageStop = QtCore.Signal()
    
    sigLaserOn = QtCore.Signal()
    sigLaserOff = QtCore.Signal()


    _image = []

    _camera_logic = None
    _mw = None

    def __init__(self, config, **kwargs):

        # load connection
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initializes all needed UI files and establishes the connectors.
        """

        self._camera_logic = self.camera_logic()

        # Windows
        self._mw = BasicWindow()
        
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

        # starting the physical measurement
        self.sigVideoStart.connect(self._camera_logic.start_loop)
        self.sigVideoStop.connect(self._camera_logic.stop_loop)
        self.sigImageStart.connect(self._camera_logic.start_single_acquistion)

        raw_data_image = self._camera_logic.get_last_image()
        self._image = pg.ImageItem(image=raw_data_image, axisOrder='row-major')
        self._mw.image_PlotWidget.addItem(self._image)
        self._mw.image_PlotWidget.setAspectLocked(True)
        
        
        # laser dockwidget
        self._mw.laser_on_Action.setEnabled(True)
        self._mw.laser_on_Action.triggered.connect(self.laser_on_clicked)
        
        # laser off part still missing 
        
        
        self._mw.laser_zero_Action.setEnabled(True)
        self._mw.laser_zero_Action.triggered.connect(self.laser_set_to_zero)
        
        # connect the slider with the spinbox so that they show the same value     
        
        self.slider_list = [self._mw.laser1_HorizontalSlider, self._mw.laser2_HorizontalSlider]
        self.spinbox_list = [self._mw.laser1_control_SpinBox, self._mw.laser2_control_SpinBox]
        
        
        # exploratory part: 
#        for item in self.slider_list:
#            item.valueChanged.connect(lambda num = 0: self.set_spinbox_value(num))
            
        
        #
        for item in self.spinbox_list:
            item.valueChanged.connect(self.set_slider_value)
        # the slot has to be generalized to take an argument corresponding to the element in the list .. 
        #self._mw.laser1_HorizontalSlider.valueChanged.connect(self.set_spinbox_value)
        #self._mw.laser1_control_SpinBox.valueChanged.connect(self.set_slider_value)
        # so there should be the same thing for all other lasers .. but there must be a way without repetition. 
        # use a signal mapper ? to explore .. 
 
        


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
        raw_data_image = self._camera_logic.get_last_image()
        self._image.setImage(image=raw_data_image)
        

    def updateView(self):
        """
        Update the view when the model changes
        """
        pass
    
 
# color bar functions to be defined here    

    
    # laser dockwidget
    def laser_on_clicked(self):
        """
        """
        self._mw.laser_on_Action.setText('Laser Off')
        self._mw.laser_zero_Action.setDisabled(True)
        self.sigLaserOn.emit()
        
        
    def laser_set_to_zero(self):
        """
        """
        for item in self.slider_list: #[self._mw.laser1_HorizontalSlider, self._mw.laser2_HorizontalSlider, self._mw.laser3_HorizontalSlider, self._mw.laser4_HorizontalSlider]:
            item.setValue(0)

        
    def set_spinbox_value(self, num):
        """
        """
        laser_value = self.slider_list[num].value()
        self.spinbox_list[num].setValue(laser_value)
#        laser1_value = self._mw.laser1_HorizontalSlider.value()
#        self._mw.laser1_control_SpinBox.setValue(laser1_value)
        
    def set_slider_value(self):
        """
        """
        laser1_value = self._mw.laser1_control_SpinBox.value()
        self._mw.laser1_HorizontalSlider.setValue(laser1_value)



        
        




## for testing      
#if __name__ == '__main__':
#    app = QtWidgets.QApplication(sys.argv)
#    # it's required to save a reference to MainWindow.
#    # if it goes out of scope, it will be destroyed.
#    mw = BasicWindow()
#    sys.exit(app.exec())