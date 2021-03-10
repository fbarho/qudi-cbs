#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 29 08:13:08 2020

@author: barho

This module contains a GUI for the basic functions of the fluorescence microscopy setup.

Camera image, camera status control, laser and filter settings.

"""
import os
import sys
from datetime import datetime
import re
import numpy as np

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy import uic
import pyqtgraph as pg

from gui.guibase import GUIBase
from core.connector import Connector
from core.configoption import ConfigOption
from qtwidgets.scan_plotwidget import ScanImageItem, ScanViewBox
from gui.validators import NameValidator


class CameraSettingDialog(QtWidgets.QDialog):
    """ Create the SettingsDialog window, based on the corresponding *.ui file."""
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_camera_settings.ui')

        # Load it
        super(CameraSettingDialog, self).__init__()
        uic.loadUi(ui_file, self)


class SaveSettingDialog(QtWidgets.QDialog):
    """ Create the SaveDialog window, based on the corresponding *.ui file.

    This dialog pops up on click of the save video toolbuttons"""
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_save_settings.ui')

        # Load it
        super(SaveSettingDialog, self).__init__()
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

        # Statusbar   # this can not be done in qt designer and must be handcoded
        # this label is used to display the progress during spooling and video saving
        self.progress_label = QtWidgets.QLabel('')
        self.statusBar().addPermanentWidget(self.progress_label)

        self.show()


class BasicGUI(GUIBase):
    """ Main window containing the basic tools for the fluorescence microscopy setup

    Example config for copy-paste:

    basic_gui:
        module.Class: 'fluorescence_microscopy.basic_gui.BasicGUI'
        default_path: '/home/barho/images'     # indicate here the default path where data should be saved to
                                               # folder with current date will be created automatically therein
        brightfield_control: False
        connect:
            camera_logic: 'camera_logic'
            laser_logic: 'lasercontrol_logic'
            filterwheel_logic: 'filterwheel_logic'
    """
    
    # Define connectors to logic modules
    camera_logic = Connector(interface='CameraLogic')
    laser_logic = Connector(interface='LaserControlLogic')
    filterwheel_logic = Connector(interface='FilterwheelLogic')

    brightfield_logic = Connector(interface='BrightfieldLogic', optional=True)  

    # set the default save path (stem) from config
    default_path = ConfigOption('default_path', missing='warn')
    brightfield_control = ConfigOption('brightfield_control', False)

    # Signals
    # signals to camera logic
    sigVideoStart = QtCore.Signal()
    sigVideoStop = QtCore.Signal()
    sigImageStart = QtCore.Signal()

    sigVideoSavingStart = QtCore.Signal(str, str, int, bool, dict)
    sigSpoolingStart = QtCore.Signal(str, str, int, bool, dict)
    
    sigInterruptLive = QtCore.Signal()
    sigResumeLive = QtCore.Signal()
    
    sigSetSensor = QtCore.Signal(int, int, int, int, int, int)
    sigResetSensor = QtCore.Signal()
    
    sigReadTemperature = QtCore.Signal()

    # signals to laser control logic
    sigLaserOn = QtCore.Signal()
    sigLaserOff = QtCore.Signal()

    # signals to brightfield control logic
    sigBFOn = QtCore.Signal(int)
    sigBFOff = QtCore.Signal()
    
    # signals to filterwheel logic
    sigFilterChanged = QtCore.Signal(int)

    # attributes
    _image = []
    _camera_logic = None
    _laser_logic = None
    _filterwheel_logic = None
    _brightfield_logic = None
    _mw = None
    region_selector_enabled = False
    imageitem = None
    spinbox_list = None

    # flags that enable to reuse the save settings dialog for both save video and save long video (=spooling)
    _video = False
    _spooling = False

    # flags that for rotation settings
    rotation_cw = False
    rotation_ccw = False
    rot180 = False

    def __init__(self, config, **kwargs):

        # load connection
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initializes all needed UI files and establishes the connectors.
        """
        self._camera_logic = self.camera_logic()
        self._laser_logic = self.laser_logic()
        self._filterwheel_logic = self.filterwheel_logic()

        if self.brightfield_control:
            self._brightfield_logic = self.brightfield_logic()

        # Windows
        self._mw = BasicWindow()
        self._mw.centralwidget.hide()  # everything is in dockwidgets
        # self._mw.setDockNestingEnabled(True)
        self.init_camera_settings_ui()

        # make sure that the flags for image rotation are initially false and toggle buttons in options menu unchecked
        self.rotation_cw = False
        self.rotation_ccw = False
        self.rot180 = False
        self._mw.rotate_image_cw_MenuAction.setChecked(False)
        self._mw.rotate_image_ccw_MenuAction.setChecked(False)
        self._mw.rot180_image_MenuAction.setChecked(False)

        # Menu bar actions
        # File menu
        self._mw.close_MenuAction.triggered.connect(self._mw.close)
        # Options menu
        self._mw.camera_settings_Action.triggered.connect(self.open_camera_settings)
        self._mw.rotate_image_cw_MenuAction.toggled.connect(self.rotate_image_cw_toggled)
        self._mw.rotate_image_ccw_MenuAction.toggled.connect(self.rotate_image_ccw_toggled)
        self._mw.rot180_image_MenuAction.toggled.connect(self.rot180_image_toggled)
        
        # initialize functionality of the camera dockwidget and its toolbar
        self.init_camera_dockwidget()

        # initialize functionality of the camera status dockwidget
        self.init_camera_status_dockwidget()

        # initialize functionality of the laser dockwidget and its toolbar
        self.init_laser_dockwidget()

        # initialize functionality of the filter dockwidget
        self.init_filter_dockwidget()

        # connect signals for status bar
        self._camera_logic.sigProgress.connect(self.update_statusbar)
        self._camera_logic.sigSaving.connect(self.update_statusbar_saving)

        # initialize the save settings dialog
        # this needs to come after the initialization of the camera_dockwidget because the fields on the gui must first be initialized
        self.init_save_settings_ui()

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

    # methods to initialize the functionality for dockwidgets and associated toolbar if there is one
    def init_camera_dockwidget(self):
        """ initializes the display item and the indicators.
        Connects signals for the camera dockwidget and the camera toolbar
        """
        # initialize the imageitem (display of camera image) qnd its histogram
        self.imageitem = pg.ImageItem(axisOrder='row-major', invertY=True)
        self._mw.camera_ScanPlotWidget.addItem(self.imageitem)
        self._mw.camera_ScanPlotWidget.setAspectLocked(True)
        self._mw.camera_ScanPlotWidget.sigMouseAreaSelected.connect(self.mouse_area_selected)
        self._mw.histogram_Widget.setImageItem(self.imageitem)

        # set the default path
        self._mw.save_path_LineEdit.setText(self.default_path)
        # add validators to the sample name and the default path lineedits
        self._mw.save_path_LineEdit.setValidator(NameValidator(path=True))
        self._mw.samplename_LineEdit.setValidator(NameValidator(empty_allowed=True))
        # synchronize the samplename_LineEdit with the LineEdit in the save settings dialog
        self._mw.samplename_LineEdit.textChanged[str].connect(self.update_sample_name)

        # initialize the camera setting indicators on the GUI
        # use the kinetic time for andor camera, exposure time for all others
        if self._camera_logic.get_name() == 'iXon Ultra 897':
            self._mw.exposure_LineEdit.setText('{:0.5f}'.format(self._camera_logic.get_kinetic_time()))
            self._mw.exposure_Label.setText('Kinetic time (s):')
        else:
            self._mw.exposure_LineEdit.setText('{:0.5f}'.format(self._camera_logic.get_exposure()))
            self._mw.exposure_Label.setText('Exposure time (s):')

        self._mw.gain_LineEdit.setText(str(self._camera_logic.get_gain()))
        if not self._camera_logic.has_temp:
            self._mw.temp_setpoint_LineEdit.setText('')
            self._mw.temp_setpoint_LineEdit.setEnabled(False)
            self._mw.temp_setpoint_Label.setEnabled(False)
        else:
            self._mw.temp_setpoint_LineEdit.setText(str(self._camera_logic.temperature_setpoint))

        # signals from logic
        # update the camera setting indicators when value changed (via settings window or iPython console)
        self._camera_logic.sigExposureChanged.connect(self.update_exposure)
        self._camera_logic.sigGainChanged.connect(self.update_gain)
        self._camera_logic.sigTemperatureChanged.connect(self.update_temperature)

        # camera toolbar
        # configure the toolbar action buttons and connect internal signals
        self._mw.take_image_Action.setEnabled(True)
        self._mw.take_image_Action.setChecked(self._camera_logic.enabled)
        self._mw.take_image_Action.triggered.connect(self.take_image_clicked)

        self._mw.start_video_Action.setEnabled(True)
        self._mw.start_video_Action.setChecked(self._camera_logic.enabled)
        self._mw.start_video_Action.triggered.connect(self.start_video_clicked)

        self._mw.save_last_image_Action.triggered.connect(self.save_last_image_clicked)

        self._mw.save_video_Action.setEnabled(True)
        self._mw.save_video_Action.setChecked(self._camera_logic.saving)  # maybe replace by saving attribute instead
        self._mw.save_video_Action.triggered.connect(self.save_video_clicked)

        # spooling action only available for andor iXon Ultra camera
        if not self._camera_logic.get_name() == 'iXon Ultra 897':
            self._mw.spooling_Action.setEnabled(False)
        else:
            self._mw.spooling_Action.setEnabled(True)
            self._mw.spooling_Action.setChecked(self._camera_logic.saving)  # maybe replace by saving attribute instead
        self._mw.spooling_Action.triggered.connect(self.set_spooling_clicked)

        self._mw.video_quickstart_Action.triggered.connect(self.video_quickstart_clicked)

        self._mw.set_sensor_Action.setEnabled(True)
        self._mw.set_sensor_Action.setChecked(self.region_selector_enabled)
        self._mw.set_sensor_Action.triggered.connect(self.select_sensor_region)

        # signals to logic
        self.sigImageStart.connect(self._camera_logic.start_single_acquistion)
        self.sigVideoStart.connect(self._camera_logic.start_loop)
        self.sigVideoStop.connect(self._camera_logic.stop_loop)
        self.sigVideoSavingStart.connect(self._camera_logic.save_video)
        self.sigSpoolingStart.connect(self._camera_logic.do_spooling)
        self.sigInterruptLive.connect(self._camera_logic.interrupt_live)
        self.sigResumeLive.connect(self._camera_logic.resume_live)
        self.sigSetSensor.connect(self._camera_logic.set_sensor_region)
        self.sigResetSensor.connect(self._camera_logic.reset_sensor_region)
        self.sigReadTemperature.connect(self._camera_logic.get_temperature)

        # signals from logic
        self._camera_logic.sigUpdateDisplay.connect(self.update_data)
        self._camera_logic.sigAcquisitionFinished.connect(self.acquisition_finished)  # for single acquisition
        self._camera_logic.sigVideoFinished.connect(self.enable_camera_toolbuttons)
        self._camera_logic.sigVideoSavingFinished.connect(self.video_saving_finished)
        self._camera_logic.sigSpoolingFinished.connect(self.spooling_finished)
        self._camera_logic.sigCleanStatusbar.connect(self.clean_statusbar)

    def init_camera_status_dockwidget(self):
        """ initializes the indicators and connects signals for the camera status dockwidget"""
        # add the camera name to the status dockwidget
        # name = self._camera_logic.get_name()
        # self._mw.camera_status_Label.setText(f'Camera status: {name}')
        # initialize the camera status indicators on the GUI
        self._mw.camera_status_LineEdit.setText(self._camera_logic.get_ready_state())
        if not self._camera_logic.has_shutter:
            self._mw.shutter_status_LineEdit.setText('')
            self._mw.shutter_status_LineEdit.setEnabled(False)
            self._mw.shutter_Label.setEnabled(False)
        else:
            self._mw.shutter_status_LineEdit.setText(self._camera_logic.get_shutter_state())
        if not self._camera_logic.has_temp:
            self._mw.cooler_status_LineEdit.setText('')
            self._mw.cooler_status_LineEdit.setEnabled(False)
            self._mw.cooler_Label.setEnabled(False)
            self._mw.temperature_LineEdit.setText('')
            self._mw.temperature_LineEdit.setEnabled(False)
            self._mw.temperature_Label.setEnabled(False)
        else:
            self._mw.cooler_status_LineEdit.setText(self._camera_logic.get_cooler_state())
            self._mw.temperature_LineEdit.setText(str(self._camera_logic.get_temperature()))

        # signals
        # update the indicators when pushbutton is clicked
        self._mw.cam_status_pushButton.clicked.connect(self._camera_logic.update_camera_status)

        # connect signal from logic
        self._camera_logic.sigUpdateCamStatus.connect(self.update_camera_status_display)

    def init_laser_dockwidget(self):
        """ initializes the labels for the lasers given in config and connects signals for the laser control toolbar"""
        # set the labels of the laser control spinboxes according to specified wavelengths from config
        self._mw.laser1_Label.setText(self._laser_logic._laser_dict['laser1']['wavelength'])
        self._mw.laser2_Label.setText(self._laser_logic._laser_dict['laser2']['wavelength'])
        self._mw.laser3_Label.setText(self._laser_logic._laser_dict['laser3']['wavelength'])
        self._mw.laser4_Label.setText(self._laser_logic._laser_dict['laser4']['wavelength'])


        # add brightfield control widgets if applicable
        if self.brightfield_control:
            self.bf_Label = QtWidgets.QLabel('BF')
            self.bf_control_SpinBox = QtWidgets.QSpinBox()
            self._mw.formLayout_3.addRow(self.bf_Label, self.bf_control_SpinBox)

            self.brightfield_on_Action = self._mw.toolBar_2.addAction('Brightfield on')
            self.brightfield_on_Action.setCheckable(True)
            self.brightfield_on_Action.setChecked(False)

            self.brightfield_on_Action.triggered.connect(self.brightfield_on_clicked)

            self.sigBFOn.connect(self._brightfield_logic.led_control)
            self.sigBFOff.connect(self._brightfield_logic.led_off)

            # update the physical output when the spinbox value is changed
            self.bf_control_SpinBox.valueChanged.connect(self._brightfield_logic.update_intensity)

        # toolbar actions
        self._mw.laser_on_Action.setEnabled(True)
        self._mw.laser_on_Action.setChecked(self._laser_logic.enabled)
        self._mw.laser_on_Action.triggered.connect(self.laser_on_clicked)

        self._mw.laser_zero_Action.setEnabled(True)
        self._mw.laser_zero_Action.triggered.connect(self.laser_set_to_zero)

        # Signals to logic
        # starting / stopping the analog output
        self.sigLaserOn.connect(self._laser_logic.apply_voltage)
        self.sigLaserOff.connect(self._laser_logic.voltage_off)

        # actions on changing laser spinbox values
        self.spinbox_list = [self._mw.laser1_control_SpinBox, self._mw.laser2_control_SpinBox,
                             self._mw.laser3_control_SpinBox, self._mw.laser4_control_SpinBox]
        # actualize the laser intensity dictionary
        self._mw.laser1_control_SpinBox.valueChanged.connect(
            lambda: self._laser_logic.update_intensity_dict(self._laser_logic._laser_dict['laser1']['label'],
                                                             self._mw.laser1_control_SpinBox.value()))
        self._mw.laser2_control_SpinBox.valueChanged.connect(
            lambda: self._laser_logic.update_intensity_dict(self._laser_logic._laser_dict['laser2']['label'],
                                                             self._mw.laser2_control_SpinBox.value()))
        self._mw.laser3_control_SpinBox.valueChanged.connect(
            lambda: self._laser_logic.update_intensity_dict(self._laser_logic._laser_dict['laser3']['label'],
                                                             self._mw.laser3_control_SpinBox.value()))
        self._mw.laser4_control_SpinBox.valueChanged.connect(
            lambda: self._laser_logic.update_intensity_dict(self._laser_logic._laser_dict['laser4']['label'],
                                                             self._mw.laser4_control_SpinBox.value()))
        # lambda function is used to pass in an additional argument. See also the decorator @QtCore.Slot(str, int).
        # in case lambda does not work well on runtime, check functools.partial
        # or signal mapper ? to explore ..

        # Signals from logic
        # update GUI when intensity is changed programatically
        self._laser_logic.sigIntensityChanged.connect(self.update_laser_spinbox)

    def init_filter_dockwidget(self):
        """ initializes the filter selection combobox and connects signals"""
        # initialize the combobox displaying the available filters
        self.init_filter_selection()

        # internal signals
        self._mw.filter_ComboBox.activated[str].connect(self.change_filter)
        # remark: signals currentIndexChanged vs activated:
        # currentIndexChanged is sent regardless of being done programatically or by user interaction whereas
        # activated is only sent on user interaction.
        # activated seems the better option, then the signal is only sent when a new value is selected,
        # whereas the slot change_filter is called twice when using currentIndexChanged, once for the old index,
        # once for the new one.
        # comparable to radiobutton toggled vs clicked

        # signals to logic
        self.sigFilterChanged.connect(self._filterwheel_logic.set_position)

        # signals from logic
        # update GUI when filter was manually changed
        self._filterwheel_logic.sigNewFilterSetting.connect(self.update_filter_display)

    # Initialisation of the camera settings windows in the options menu
    def init_camera_settings_ui(self):
        """ Definition, configuration and initialisation of the camera settings GUI.

        """
        # Create the Camera settings window
        self._cam_sd = CameraSettingDialog()
        # Connect the action of the settings window with the code:
        self._cam_sd.accepted.connect(self.cam_update_settings)  # ok button
        self._cam_sd.rejected.connect(self.cam_keep_former_settings)  # cancel buttons
        
        # frame transfer settings
        self._cam_sd.frame_transfer_CheckBox.toggled[bool].connect(self._camera_logic.set_frametransfer)
        
        if not self._camera_logic.has_temp:
            self._cam_sd.temp_spinBox.setEnabled(False)
            self._cam_sd.label_3.setEnabled(False)

        if self._camera_logic.get_name() == 'iXon Ultra 897':
            self._cam_sd.frame_transfer_CheckBox.setEnabled(True)

        # write the configuration to the settings window of the GUI.
        self.cam_keep_former_settings()

    # slots of the camerasettingswindow
    def cam_update_settings(self):
        """ Write new settings from the gui to the logic module
        """
        # interrupt live display if it is on
        if self._camera_logic.enabled:  # camera is acquiring
            self.sigInterruptLive.emit()
        self._camera_logic.set_exposure(self._cam_sd.exposure_doubleSpinBox.value())
        self._camera_logic.set_gain(self._cam_sd.gain_spinBox.value())
        self._camera_logic.set_temperature(int(self._cam_sd.temp_spinBox.value()))
        self._mw.temp_setpoint_LineEdit.setText(str(self._cam_sd.temp_spinBox.value()))
        if self._camera_logic.enabled:
            self.sigResumeLive.emit()

    def cam_keep_former_settings(self):
        """ Keep the old settings and restores them in the gui. 
        """
        # interrupt live display
        if self._camera_logic.enabled:  # camera is acquiring
            self.sigInterruptLive.emit()
        self._cam_sd.exposure_doubleSpinBox.setValue(self._camera_logic._exposure)
        self._cam_sd.gain_spinBox.setValue(self._camera_logic._gain)
        self._cam_sd.temp_spinBox.setValue(self._camera_logic.temperature_setpoint)
        self._cam_sd.frame_transfer_CheckBox.setChecked(False)  # as default value
        if self._camera_logic.enabled:
            self.sigResumeLive.emit()

    # slot to open the camerasettingswindow
    def open_camera_settings(self):
        """ Opens the settings menu. 
        """
        self._cam_sd.exec_()

    # Initialisation of the save settings windows
    def init_save_settings_ui(self):
        """ Definition, configuration and initialisation of the dialog window which allows to configure the video saving
        """
        # Create the Camera settings window
        self._save_sd = SaveSettingDialog()
        # Connect the action of the settings window with the code:
        self._save_sd.accepted.connect(self.save_video_accepted)  # ok button
        self._save_sd.rejected.connect(self.cancel_save)  # cancel buttons

        # add a validator to the folder name lineedit
        self._save_sd.foldername_LineEdit.setValidator(NameValidator(empty_allowed=True))  # empty_allowed=True should be set or not ?

        # populate the file format combobox
        self._save_sd.file_format_ComboBox.addItems(self._camera_logic.fileformat_list)

        # connect the lineedit with the path label
        self._save_sd.foldername_LineEdit.textChanged.connect(self.update_path_label)
        # link the number of frames to the acquisition time
        self._save_sd.n_frames_SpinBox.valueChanged.connect(self.update_acquisition_time)
        # link the acquisition time to the number of frames
        self._save_sd.acquisition_time_DoubleSpinBox.valueChanged.connect(self.update_n_frames)

        # set default values on start
        self.set_default_values()

    # slots of the save settings window
    def save_video_accepted(self):
        """ callback of the ok button.
        Retrieves the information given by the user and transfers them by the signal which will start the physical
        measurement
        """
        folder_name = self._save_sd.foldername_LineEdit.text()
        default_path = self._mw.save_path_LineEdit.text()
        today = datetime.today().strftime('%Y-%m-%d')
        path = os.path.join(default_path, today, folder_name)
        fileformat = '.'+str(self._save_sd.file_format_ComboBox.currentText())

        n_frames = self._save_sd.n_frames_SpinBox.value()

        display = self._save_sd.enable_display_CheckBox.isChecked()

        metadata = self._create_metadata_dict()

        # we need a case structure here: if the dialog was called from save video button, sigVideoSavingStart must be
        # emitted, if it was called from save long video (=spooling) sigSpoolingStart must be emitted
        if self._video:
            self.sigVideoSavingStart.emit(path, fileformat, n_frames, display, metadata)
        elif self._spooling:
            self.sigSpoolingStart.emit(path, fileformat, n_frames, display, metadata)
        else:  # to do: write an error message or something like this ???
            pass

    def cancel_save(self):
        """ callback of the cancel button of the video save settings dialog"""
        self.set_default_values()
        self.reset_toolbuttons()  # this resets the toolbar buttons to callable state
        self._video = False
        self._spooling = False

    def set_default_values(self):
        """ (re)sets the default values for the field of the dialog """
        self._save_sd.foldername_LineEdit.setText(self._mw.samplename_LineEdit.text())
        self.update_path_label()
        self._save_sd.n_frames_SpinBox.setValue(1)
        self.update_acquisition_time()
        self._save_sd.enable_display_CheckBox.setChecked(True)
        self._save_sd.file_format_ComboBox.setCurrentIndex(0)

    def update_path_label(self):
        """ generates the informative text indicating the complete path,
        displayed below the folder name specified by the user """
        folder_name = self._save_sd.foldername_LineEdit.text()
        default_path = self._mw.save_path_LineEdit.text()
        today = datetime.today().strftime('%Y-%m-%d')
        path = os.path.join(default_path, today, folder_name)  #
        self._save_sd.complete_path_Label.setText('Save to: {}'.format(path))

    def update_acquisition_time(self):
        """ links the displayed acquisition duration to the number of frames indicated by the user"""
        exp_time = float(self._mw.exposure_LineEdit.text())  # if andor cam is used, the kinetic_time is retrieved here
        n_frames = self._save_sd.n_frames_SpinBox.value()
        acq_time = exp_time * n_frames
        self._save_sd.acquisition_time_DoubleSpinBox.setValue(acq_time)

    def update_n_frames(self):
        """ links the number of frames to the selected total acquisition time,
        if the user prefers indicating the duration of the video to be saved """
        exp_time = float(self._mw.exposure_LineEdit.text())  # if andor cam is used, the kinetic_time is retrieved here
        acq_time = self._save_sd.acquisition_time_DoubleSpinBox.value()
        n_frames = int(round(acq_time / exp_time))
        self._save_sd.n_frames_SpinBox.setValue(n_frames)
        self.update_acquisition_time()  # call this to adapt the acquisition time to the nearest possible value according to n_frames

    # slot to open the save settings window
    def open_save_settings(self):
        """ Opens the settings menu.
        """
        self._save_sd.exec_()

    # slots for the menu and toolbar actions
    # camera dockwidget
    @QtCore.Slot(float)
    def update_exposure(self, exposure):
        """ updates the displayed value of exposure time in the corresponding read-only lineedit
        indicates the kinetic time instead of the user defined exposure time in case of andor camera

        @param: float exposure"""
        # indicate the kinetic time instead of the exposure time for andor ixon camera
        if self._camera_logic.get_name() == 'iXon Ultra 897':
            self._mw.exposure_LineEdit.setText('{:0.5f}'.format(self._camera_logic.get_kinetic_time()))
        else:
            self._mw.exposure_LineEdit.setText('{:0.5f}'.format(exposure))

    @QtCore.Slot(float)
    def update_gain(self, gain):
        """ updates the read-only lineedit showing the applied gain

        @param: float gain"""
        self._mw.gain_LineEdit.setText(str(gain))

    @QtCore.Slot(float)
    def update_temperature(self, temp):
        """ updates the read-only lineedit showing the current sensor temperature

        @param: float temperature """
        self._mw.temperature_LineEdit.setText(str(temp))

    @QtCore.Slot(str)
    def update_sample_name(self, samplename):
        """ updates the folder name lineedit in the save settings dialog when the sample name on the gui was modified"""
        self._save_sd.foldername_LineEdit.setText(samplename)

    @QtCore.Slot()
    def take_image_clicked(self):
        """ Callback of take_image_Action (take and display a single image, without saving).
        Emits a signal that is connected to the logic module, and disables the tool buttons
        """
        self.sigImageStart.emit()
        self.disable_camera_toolbuttons()
        self.imageitem.getViewBox().rbScaleBox.hide()  # hide the rubberband tool used for roi selection on sensor

    @QtCore.Slot()
    def acquisition_finished(self):
        """ Callback of sigAcquisitionFinished. Resets all tool buttons to callable state
        """
        self._mw.take_image_Action.setChecked(False)
        self.enable_camera_toolbuttons()

    @QtCore.Slot()
    def start_video_clicked(self):
        """ Callback of start_video_Action. (start and display a continuous image from the camera, without saving)
        Handles the state of the start button and emits a signal (connected to logic above) to start the acquisition loop.
        """
        self._mw.take_image_Action.setDisabled(True)  # snap and live are mutually exclusive
        if self._camera_logic.enabled:  # video already running
            self._mw.start_video_Action.setText('Live')
            self._mw.start_video_Action.setToolTip('Start live video')
            self.sigVideoStop.emit()
        else:
            self._mw.start_video_Action.setText('Stop Live')
            self._mw.start_video_Action.setToolTip('Stop live video')
            self.sigVideoStart.emit()
        self.imageitem.getViewBox().rbScaleBox.hide()  # hide the rubberband tool used for roi selection on sensor

    @QtCore.Slot()
    def update_data(self):
        """ Callback of sigUpdateDisplay in the camera_logic module.
        Get the image data from the logic and print it on the window
        """
        image_data = self._camera_logic.get_last_image()
        # handle the rotation that occurs due to the image formatting conventions (see also https://github.com/pyqtgraph/pyqtgraph/issues/315) 
        # this could be improved by another method ?! though reversing the y axis did not work. 
        image_data = np.rot90(image_data, 3)  # 90 deg clockwise 

        # handle the user defined rotation settings
        if self.rotation_cw:
            image_data = np.rot90(image_data, 3)
        if self.rotation_ccw:
            image_data = np.rot90(image_data, 1)  # eventually replace by faster rotation method T and invert
        if self.rot180:
            image_data = np.rot90(image_data, 2)
        self.imageitem.setImage(image_data.T)
        # transposing the data makes the rotations behave as they should when axisOrder row-major is used (set in initialization of ImageItem)
        # see also https://github.com/pyqtgraph/pyqtgraph/issues/315

    @QtCore.Slot()
    def save_last_image_clicked(self):
        """ callback of save_last_image_Action.
        saves the last image (the one currently displayed on the image widget), using the following format
        (analogously to video saving procedures)
        images are saved to:
        filenamestem/num_type/file.tiff
        example: /home/barho/images/2020-12-16/samplename/000_Image/image.tiff
        filenamestem is generated below, example /home/barho/images/2020-12-16/foldername
        folder_name is taken from the field on GUI. to decide : put it in a dialog as for the save settings dialog ??
        num_type is an incremental number followed by _Image
        """
        # save data
        default_path = self._mw.save_path_LineEdit.text()
        today = datetime.today().strftime('%Y-%m-%d')
        folder_name = self._mw.samplename_LineEdit.text()
        filenamestem = os.path.join(default_path, today, folder_name)
        metadata = self._create_metadata_dict()
        self._camera_logic.save_last_image(filenamestem, metadata)

    @QtCore.Slot()
    def save_video_clicked(self):
        """ callback of save_video_Action. Handles toolbutton state, and opens the save settings dialog"""
        # disable camera related toolbuttons
        self.disable_camera_toolbuttons()
        # set the flag to True so that the dialog knows that is was called from save video button
        self._video = True
        # open the save settings window
        self.open_save_settings()
        # hide the rubberband tool used for roi selection on sensor
        self.imageitem.getViewBox().rbScaleBox.hide()

    @QtCore.Slot()
    def video_saving_finished(self):
        """ resets the toolbuttons to callable state and clear up the flag and statusbar"""
        # reset the flag
        self._video = False
        # toolbuttons
        self.enable_camera_toolbuttons()
        self._mw.save_video_Action.setChecked(False)
        # clear the statusbar
        self._mw.progress_label.setText('')

    @QtCore.Slot()
    def set_spooling_clicked(self):
        """ callback of spooling_Action. Handles toolbutton state, and opens the save settings dialog"""
        # disable camera related toolbuttons
        self.disable_camera_toolbuttons()
        # set the flag to True so that the dialog nows that is was called from save video button
        self._spooling = True
        # open the save settings dialog
        self.open_save_settings()
        # hide the rubberband tool used for roi selection on sensor
        self.imageitem.getViewBox().rbScaleBox.hide()

    @QtCore.Slot()
    def spooling_finished(self):
        """ resets the toolbuttons to callable state and clear up the flag and statusbar"""
        # reset the flag
        self._spooling = False
        # enable the toolbuttons
        self.enable_camera_toolbuttons()
        self._mw.spooling_Action.setChecked(False)
        # clear the statusbar
        self._mw.progress_label.setText('')

    @QtCore.Slot()
    def video_quickstart_clicked(self):
        """ callback of video quickstart action (uses last parameters written in the settings dialog which will not be opened again)
        handles toolbutton state and calls the save_video_accepted method """
        # disable camera related toolbuttons
        self.disable_camera_toolbuttons()
        # decide depending on camera which signal has to be emitted in save_video_accepted method
        # same approach can later be used to regroup save_video and save_long_video buttons into one action
        if self._camera_logic.get_name == 'iXon Ultra 897':
            self._spooling = True
        else:
            self._video = True
        self.save_video_accepted()

    @QtCore.Slot(int)
    def update_statusbar(self, number_images):
        # total = self._save_sd.n_frames_SpinBox.value()
        # progress = number_images / total * 100
        # try first with the simple version, maybe use later rescaling in %
        self._mw.progress_label.setText('{} images saved'.format(number_images))
        
    @QtCore.Slot()
    def update_statusbar_saving(self):
        self._mw.progress_label.setText('Saving..')

    @QtCore.Slot()
    def clean_statusbar(self):
        self._mw.progress_label.setText('')

    def reset_toolbuttons(self):
        """ this slot is called when save dialog is canceled

        Sets the camera toolbuttons to callable state, and unchecks them"""
        self.enable_camera_toolbuttons()
        self._mw.save_video_Action.setChecked(False)  # simply uncheck both independent of which one was checked before
        self._mw.spooling_Action.setChecked(False)

    def disable_camera_toolbuttons(self):
        """ disables all toolbuttons of the camera toolbar"""
        self._mw.take_image_Action.setDisabled(True)
        self._mw.start_video_Action.setDisabled(True)
        self._mw.save_last_image_Action.setDisabled(True)
        self._mw.save_video_Action.setDisabled(True)
        self._mw.spooling_Action.setDisabled(True)
        self._mw.video_quickstart_Action.setDisabled(True)
        self._mw.set_sensor_Action.setDisabled(True)

    def enable_camera_toolbuttons(self):
        """ enables all toolbuttons of the camera toolbar

        serves also as callback of SigVideoFinished.
        """
        if not self._camera_logic.enabled:  # do not reset to active state if live mode is on
            self._mw.take_image_Action.setDisabled(False)
        self._mw.start_video_Action.setDisabled(False)
        self._mw.save_last_image_Action.setDisabled(False)
        self._mw.save_video_Action.setDisabled(False)
        self._mw.video_quickstart_Action.setDisabled(False)
        self._mw.set_sensor_Action.setDisabled(False)
        if self._camera_logic.get_name() == 'iXon Ultra 897':  # in this case the button needs to be reactivated
            self._mw.spooling_Action.setDisabled(False)

    def _create_metadata_dict(self):
        """ create a dictionary containing the metadata.
        For compatibility with fits header: use only keys with 8 letters, no special symbols.
        """
        # maybe reformat using tuples of value and comment (good for fits, less adapted for txt).
        metadata = {}
        metadata['time'] = datetime.now().strftime('%m-%d-%Y, %H:%M:%S')
        filterpos = self._filterwheel_logic.get_position()
        filterdict = self._filterwheel_logic.get_filter_dict()
        label = 'filter{}'.format(filterpos)
        metadata['filter'] = filterdict[label]['name']
        metadata['gain'] = self._camera_logic.get_gain()
        metadata['exposure'] = self._camera_logic.get_exposure()
        if self._camera_logic.get_name() == 'iXon Ultra 897':
            metadata['kinetic'] = self._camera_logic.get_kinetic_time()
        intensity_dict = self._laser_logic._intensity_dict
        keylist = [key for key in intensity_dict if intensity_dict[key] != 0]
        laser_dict = self._laser_logic.get_laser_dict()
        metadata['laser'] = [laser_dict[key]['wavelength'] for key in keylist]
        if metadata['laser'] == []:  # for compliance with fits header conventions ([] is forbidden)
            metadata['laser'] = None
        metadata['intens'] = [intensity_dict[key] for key in keylist]
        if metadata['intens'] == []:
            metadata['intens'] = None
        if self._camera_logic.has_temp:
#            metadata['temp'] = self._camera_logic.get_temperature()  # old version with missing metadata entry when live mode is running and save is clicked
            # new version allowing temperature reading during live (short interruption of live mode)
            self.sigReadTemperature.emit()
            metadata['temp'] = self._camera_logic._temperature
        else:
            metadata['temp'] = 'Not available'
        return metadata

    @ QtCore.Slot()
    def select_sensor_region(self):
        """ callback of set_sensor_Action.
        Enables or disables (according to initial state) the rubberband selection tool on the camera image."""
        # area selection initially off
        if not self.region_selector_enabled:
            self._mw.camera_ScanPlotWidget.toggle_selection(True)
            self.region_selector_enabled = True
            self._mw.set_sensor_Action.setText('Reset sensor to default size')
        else:  # area selection is initially on:
            self._mw.camera_ScanPlotWidget.toggle_selection(False)
            self.region_selector_enabled = False
#            self._camera_logic.reset_sensor_region()
            self.sigResetSensor.emit()
            self._mw.set_sensor_Action.setText('Set sensor region')

    @QtCore.Slot(QtCore.QRectF)
    def mouse_area_selected(self, rect):
        """ This slot is called when the user has selected an area of the camera image using the rubberband tool

        allows to reduce the used area of the camera sensor
        """
        self.log.info('selected an area')
        self.log.debug(rect.getCoords())
        hstart, vstart, hend, vend = rect.getCoords()
        hstart = round(hstart)
        vstart = round(vstart)
        hend = round(hend)
        vend = round(vend)
        # order the values so that they can be used as arguments for the set_sensor_region function
        hstart_ = min(hstart, hend)
        hend_ = max(hstart, hend)
        vstart_ = min(vstart, vend)
        vend_ = max(vstart, vend)
        self.log.debug('hstart={}, hend={}, vstart={}, vend={}'.format(hstart_, hend_, vstart_, vend_))
        # inversion along the y axis: 
        # it is needed to call the function set_sensor_region(hbin, vbin, hstart, hend, vstart, vend)
        # using the following arguments: set_sensor_region(hbin, vbin, start, hend, num_px_y - vend, num_px_y - vstart) ('vstart' needs to be smaller than 'vend')
        num_px_y = self._camera_logic.get_max_size()[1]  # height is stored in the second return value of get_size
        # self.log.debug(num_px_y)
        
        # version where set sensor region is only possible when live mode is stopped 
#        self._camera_logic.set_sensor_region(1, 1, hstart_, hend_, num_px_y-vend_, num_px_y-vstart_)
        
        # new version allowing set sensor region during live: it is needed to send a signal to camera
        # logic otherwise the start loop / stop loop functionality cannot be used 
        # (timers cannot be started / stopped from another thread)
        # send the 6 arguments for camera_logic.set_sensor_region via the signal
        self.sigSetSensor.emit(1, 1, hstart_, hend_, num_px_y-vend_, num_px_y-vstart_)
        if self._camera_logic.enabled:  # if live mode is on hide rubberband selector directly
            self.imageitem.getViewBox().rbScaleBox.hide()

    @QtCore.Slot()
    def rotate_image_cw_toggled(self):
        """ Callback of the rotate image 90 deg clockwise menu action """
        if self.rotation_cw:  # rotation is already applied. Toggle button has just been unchecked by user
            self.rotation_cw = False
        else:  # rotation not yet applied. Toggle button has just been checked by user
            self.rotation_cw = True
            # automatically uncheck the rotate ccw and rotate 180deg button (make them mutually exclusive)
            self._mw.rotate_image_ccw_MenuAction.setChecked(False)
            self._mw.rot180_image_MenuAction.setChecked(False)
            self.rotation_ccw = False
            self.rot180 = False

    @QtCore.Slot()
    def rotate_image_ccw_toggled(self):
        """ Callback of the rotate image 90 deg counter clockwise menu action """
        if self.rotation_ccw:  # rotation is already applied. Toggle button has just been unchecked by user
            self.rotation_ccw = False
        else:  # rotation not yet applied. Toggle button has just been checked by user
            self.rotation_ccw = True
            # automatically uncheck the rotate cw button and rotate 180deg button (make them mutually exclusive)
            self._mw.rotate_image_cw_MenuAction.setChecked(False)
            self._mw.rot180_image_MenuAction.setChecked(False)
            self.rotation_cw = False
            self.rot180 = False

    @QtCore.Slot()
    def rot180_image_toggled(self):
        """ Callback of the rotate image 180 deg menu action """
        if self.rot180:  # rotation is already applied. Toggle button has just been unchecked by user
            self.rot180 = False
        else:  # rotation not yet applied. Toggle button has just been checked by user
            self.rot180 = True
            # automatically uncheck the rotate cw button and rotate 180deg button (make them mutually exclusive)
            self._mw.rotate_image_cw_MenuAction.setChecked(False)
            self._mw.rotate_image_ccw_MenuAction.setChecked(False)
            self.rotation_cw = False
            self.rotation_ccw = False

    # camera status dockwidget
    @QtCore.Slot(str, str, str, str)  # temperature already converted into str
    def update_camera_status_display(self, ready_state, shutter_state='', cooler_state='', temperature=''):
        """ Updates the indicators in the camera status dockwidget using the information retrieved by the logic module"""
        self._mw.camera_status_LineEdit.setText(ready_state)
        self._mw.shutter_status_LineEdit.setText(shutter_state)
        self._mw.cooler_status_LineEdit.setText(cooler_state)
        self._mw.temperature_LineEdit.setText(temperature)

    # laser dockwidget
    @QtCore.Slot()
    def laser_on_clicked(self):
        """ callback of laser_on_Action.
        Handles the state of the toolbutton and emits a signal that is in turn connected to the physical output.
        Hanles also the state of the filter selection combobox to avoid changing filter while lasers are on
        """
        if self._laser_logic.enabled:
            # laser is initially on
            self._mw.laser_on_Action.setText('Laser On')
            self.sigLaserOff.emit()
            # enable filter setting again
            self._mw.filter_ComboBox.setEnabled(True)
        else:
            # laser is initially off
            self._mw.laser_on_Action.setText('Laser Off')
            self.sigLaserOn.emit()
            # do not change filters while laser is on
            self._mw.filter_ComboBox.setEnabled(False)

    @QtCore.Slot()
    def laser_set_to_zero(self):
        """ callback of laser_zero_Action.
        """
        for item in self.spinbox_list: 
            item.setValue(0)
        # also set brightfield control to zero in case it is available
        if self.brightfield_control:
            self.bf_control_SpinBox.setValue(0)

    def update_laser_spinbox(self):
        """ update values in laser spinboxes if the intensity dictionary in the logic module was changed """
        for index, item in enumerate(self.spinbox_list):
            label = 'laser'+str(index + 1)  # create the label to address the corresponding laser
            item.setValue(self._laser_logic._intensity_dict[label])

    @QtCore.Slot()
    def brightfield_on_clicked(self):
        """ callback of brightfield_on_Action.
        Handles the state of the toolbutton and emits a signal that is in turn connected to the physical output.
        """
        if self._brightfield_logic.enabled:
            # brightfield is initially on
            self.brightfield_on_Action.setText('Brightfield On')
            self.sigBFOff.emit()
        else:
            # brightfield is initially off
            self.brightfield_on_Action.setText('Brightfield Off')
            intensity = self.bf_control_SpinBox.value()
            self.sigBFOn.emit(intensity)

    # filter dockwidget
    def init_filter_selection(self):
        """ Initializes the filter selection combobox with the available filters"""
        filter_dict = self._filterwheel_logic.filter_dict
        for key in filter_dict:
            text = str(filter_dict[key]['position'])+': '+filter_dict[key]['name']
            self._mw.filter_ComboBox.addItem(text)

        # set the active filter position in the list
        current_filter_position = self._filterwheel_logic.get_position()  # returns an int: position
        index = current_filter_position - 1  # zero indexing
        self._mw.filter_ComboBox.setCurrentIndex(index)

        # disable the laser control spinboxes of lasers that are not allowed to be used with the selected filter
        key = 'filter'+str(current_filter_position)  # create the key which allows to access the corresponding entry in the filter_dict
        self._disable_laser_control(self._filterwheel_logic.filter_dict[key]['lasers'])  # get the corresponding bool list from the logic module

    def change_filter(self):
        """ Slot connected to the filter selection combobox. It sends the (int) number of the selected filter to the filterwheel logic.
        Triggers also the deactivation of forbidden laser control spinboxes for the given filter.
        @param: None

        @returns: None
        """
        # get current index of the filter selection combobox
        index = self._mw.filter_ComboBox.currentIndex()
        filter_pos = index + 1  # zero indexing
        self.sigFilterChanged.emit(filter_pos)
        # to keep in mind: is this the good way to address the filters in case they are not given in an ordered way (filter1 on position 1 etc?) or is this always
        # covered by using the position as suffix of the label anyway ? but when position starts at > 1 if filterwheel is not completely filled this will not work ..

        # disable the laser control spinboxes of lasers that are not allowed to be used with the selected filter
        key = 'filter'+str(filter_pos)  # create the key which allows to access the corresponding entry in the filter_dict
        self._disable_laser_control(self._filterwheel_logic.filter_dict[key]['lasers'])  # get the corresponding bool list from the logic module

    def update_filter_display(self, position):
        """ refresh the checked state of the radio buttons to ensure that after manually modifying the filter (for example using the iPython console)
        the GUI displays the correct filter
        """
        index = position - 1  # zero indexing
        self._mw.filter_ComboBox.setCurrentIndex(index)

    def _disable_laser_control(self, bool_list):        
        """ disables the control spinboxes of the lasers which are not allowed for a given filter
        
        @param: bool_list: list of length 4 with entries corresponding to laser1 - laser4 [True False True False] -> Laser1 and laser3 allowed, laser2 and laser4 forbidden
        
        @returns: None
        """                   
        self._mw.laser1_control_SpinBox.setEnabled(bool_list[0])
        self._mw.laser2_control_SpinBox.setEnabled(bool_list[1])
        self._mw.laser3_control_SpinBox.setEnabled(bool_list[2])
        self._mw.laser4_control_SpinBox.setEnabled(bool_list[3])
