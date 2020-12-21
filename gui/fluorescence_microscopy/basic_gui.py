#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 29 08:13:08 2020

@author: barho


This module contains a GUI for the basic functions of the fluorescence microscopy setup.

Camera image, laser and filter settings.

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


# copied this validator from poimangui.py
class NameValidator(QtGui.QValidator):
    """
    This is a validator for strings that should be compatible with filenames.
    So no special characters (except '_') and blanks are allowed.
    """

    name_re = re.compile(r'([\w]+)')

    def __init__(self, *args, empty_allowed=False, **kwargs):
        super().__init__(*args, **kwargs)
        self._empty_allowed = bool(empty_allowed)

    def validate(self, string, position):
        """
        This is the actual validator. It checks whether the current user input is a valid string
        every time the user types a character. There are 3 states that are possible.
        1) Invalid: The current input string is invalid. The user input will not accept the last
                    typed character.
        2) Acceptable: The user input in conform with the regular expression and will be accepted.
        3) Intermediate: The user input is not a valid string yet but on the right track. Use this
                         return value to allow the user to type fill-characters needed in order to
                         complete an expression.
        @param string: The current input string (from a QLineEdit for example)
        @param position: The current position of the text cursor
        @return: enum QValidator::State: the returned validator state,
                 str: the input string, int: the cursor position
        """
        # Return intermediate status when empty string is passed
        if not string:
            if self._empty_allowed:
                return self.Acceptable, '', position
            else:
                return self.Intermediate, string, position

        match = self.name_re.match(string)
        if not match:
            return self.Invalid, '', position

        matched = match.group()
        if matched == string:
            return self.Acceptable, string, position

        return self.Invalid, matched, position

    def fixup(self, text):
        match = self.name_re.search(text)
        if match:
            return match.group()
        return ''


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
        self.show()


class BasicGUI(GUIBase):
    """ Main window containing the basic tools for the fluorescence microscopy setup

    Example config for copy-paste:

    basic_gui:
        module.Class: 'fluorescence_microscopy.basic_gui.BasicGUI'
        default_path: '/home/barho/images'
        connect:
            camera_logic: 'camera_logic'
            daq_ao_logic: 'daq_logic'
            filterwheel_logic: 'filterwheel_logic'
    """
    
    # Define connectors to logic modules
    camera_logic = Connector(interface='CameraLogic')
    daq_ao_logic = Connector(interface='DAQaoLogic')
    filterwheel_logic = Connector(interface='FilterwheelLogic')

    # set the default save path (stem) from config
    default_path = ConfigOption('default_path', missing='warn')

    # Signals
    # signals to camera logic
    sigVideoStart = QtCore.Signal()
    sigVideoStop = QtCore.Signal()
    sigImageStart = QtCore.Signal()

    sigVideoSavingStart = QtCore.Signal(str, int, bool)
    sigSpoolingStart = QtCore.Signal(str, int, bool)

    # signals to daq logic
    sigLaserOn = QtCore.Signal()
    sigLaserOff = QtCore.Signal()
    
    # signals to filterwheel logic
    sigFilterChanged = QtCore.Signal(int)

    _image = []
    _camera_logic = None
    _daq_ao_logic = None
    _filterwheel_logic = None
    _mw = None
    _last_path = None
    region_selector_enabled = False

    # flags that enable to reuse the save settings dialog for both save video and save long video (=spooling)
    _video = False
    _spooling = False

    def __init__(self, config, **kwargs):

        # load connection
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initializes all needed UI files and establishes the connectors.
        """

        self._camera_logic = self.camera_logic()
        self._daq_ao_logic = self.daq_ao_logic()
        self._filterwheel_logic = self.filterwheel_logic()

        # Windows
        self._mw = BasicWindow()
        self._mw.centralwidget.hide()  # everything is in dockwidgets
        # self._mw.setDockNestingEnabled(True)
        self.initCameraSettingsUI()


        # set the default path
        self._mw.save_path_LineEdit.setText(self.default_path)

        # add validators to the sample name and the default path lineedits
        #self._mw.save_path_LineEdit.setValidator(NameValidator()) here another validator is needed which allows /
        self._mw.samplename_LineEdit.setValidator(NameValidator(empty_allowed=True))

        # Menu bar actions
        # Options menu
        self._mw.camera_settings_Action.triggered.connect(self.open_camera_settings)
        
        # camera dockwidget
        # initialize the camera setting indicators on the GUI
        # use the kinetic time for andor camera, exposure time for all others
        if self._camera_logic.get_name() == 'iXon Ultra 897':
            self._mw.exposure_LineEdit.setText(str(self._camera_logic.get_kinetic_time()))
            self._mw.exposure_Label.setText('Kinetic time (s)')
        else:
            self._mw.exposure_LineEdit.setText(str(self._camera_logic.get_exposure()))
            self._mw.exposure_Label.setText('Exposure time (s)')

        self._mw.gain_LineEdit.setText(str(self._camera_logic.get_gain()))
        if not self._camera_logic.has_temp:
            self._mw.temperature_LineEdit.setText('')
            self._mw.temperature_LineEdit.setEnabled(False)
            self._mw.temperature_Label.setEnabled(False)
        else:
            self._mw.temperature_LineEdit.setText(str(self._camera_logic.get_temperature()))

        # update the camera setting indicators when value changed (via settings window or iPython console for example)
        self._camera_logic.sigExposureChanged.connect(self.update_exposure)
        self._camera_logic.sigGainChanged.connect(self.update_gain)
        self._camera_logic.sigTemperatureChanged.connect(self.update_temperature)

        # configure the toolbar action buttons and connect signals
        self._mw.take_image_Action.setEnabled(True)
        self._mw.take_image_Action.setChecked(self._camera_logic.enabled)
        self._mw.take_image_Action.triggered.connect(self.take_image_clicked)

        self._mw.start_video_Action.setEnabled(True)
        self._mw.start_video_Action.setChecked(self._camera_logic.enabled)
        self._mw.start_video_Action.triggered.connect(self.start_video_clicked)

        self._camera_logic.sigUpdateDisplay.connect(self.update_data)
        self._camera_logic.sigAcquisitionFinished.connect(self.acquisition_finished)
        self._camera_logic.sigVideoFinished.connect(self.enable_take_image_action)
        
        self._mw.save_last_image_Action.triggered.connect(self.save_last_image_clicked)

        self._mw.save_video_Action.setEnabled(True)
        self._mw.save_video_Action.setChecked(self._camera_logic.enabled)  # maybe replace by saving attribute instead
        self._mw.save_video_Action.triggered.connect(self.save_video_clicked)

        self.sigVideoSavingStart.connect(self._camera_logic.save_video)

        self._camera_logic.sigVideoSavingFinished.connect(self.video_saving_finished)

        # spooling action only available for andor iXon Ultra camera
        if not self._camera_logic.get_name() == 'iXon Ultra 897':
            self._mw.spooling_Action.setEnabled(False)
        else:
            self._mw.spooling_Action.setEnabled(True)
            self._mw.spooling_Action.setChecked(self._camera_logic.enabled)
        self._mw.spooling_Action.triggered.connect(self.set_spooling_clicked)

        self.sigSpoolingStart.connect(self._camera_logic.do_spooling)

        self._camera_logic.sigSpoolingFinished.connect(self.spooling_finished)
        
        self._mw.set_sensor_Action.setEnabled(True)
        self._mw.set_sensor_Action.setChecked(self.region_selector_enabled)  # on start this is false  # better: link it to an attribute
        self._mw.set_sensor_Action.triggered.connect(self.select_sensor_region)


        # starting the physical measurement
        self.sigVideoStart.connect(self._camera_logic.start_loop)
        self.sigVideoStop.connect(self._camera_logic.stop_loop)
        self.sigImageStart.connect(self._camera_logic.start_single_acquistion)

        # imageitem
        self.imageitem = pg.ImageItem()  # image=data can be set here ..
        self._mw.camera_ScanPlotWidget.addItem(self.imageitem)
        self._mw.camera_ScanPlotWidget.setAspectLocked(True)
        self._mw.camera_ScanPlotWidget.sigMouseAreaSelected.connect(self.mouse_area_selected)

        # histogram
        self._mw.histogram_Widget.setImageItem(self.imageitem)

        # old version. to be removed soon
        # prepare the image display. Data is added in the slot update_data
        # interpret image data as row-major instead of col-major
        # pg.setConfigOptions(imageAxisOrder='row-major')
        
        # # hide ROI and menubutton, histogram is activated when data is added to the ImageView
        # self._mw.camera_ImageView.ui.roiBtn.hide()
        # self._mw.camera_ImageView.ui.menuBtn.hide()
        # self._mw.camera_ImageView.ui.histogram.hide()

        # camera status dockwidget
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
        else:
            self._mw.cooler_status_LineEdit.setText(self._camera_logic.get_cooler_state())

        # update the indicators when pushbutton is clicked
        self._mw.cam_status_pushButton.clicked.connect(self._camera_logic.update_camera_status)

        # connect signal from logic
        self._camera_logic.sigUpdateCamStatus.connect(self.update_camera_status_display)

        # laser dockwidget
        # set the labels of the laser control spinboxes according to specified wavelengths from config
        self._mw.laser1_Label.setText(self._daq_ao_logic._laser_dict['laser1']['wavelength'])
        self._mw.laser2_Label.setText(self._daq_ao_logic._laser_dict['laser2']['wavelength'])
        self._mw.laser3_Label.setText(self._daq_ao_logic._laser_dict['laser3']['wavelength'])
        self._mw.laser4_Label.setText(self._daq_ao_logic._laser_dict['laser4']['wavelength'])

        # toolbar actions
        self._mw.laser_zero_Action.setEnabled(True)
        self._mw.laser_zero_Action.triggered.connect(self.laser_set_to_zero)
        
        self._mw.laser_on_Action.setEnabled(True)
        # self._mw.laser_on_Action.setChecked(self._daq_ao_logic.enabled) # is this really needed ?
        self._mw.laser_on_Action.triggered.connect(self.laser_on_clicked)
        
        # starting the analog output - interact with logic module
        self.sigLaserOn.connect(self._daq_ao_logic.apply_voltage)
        self.sigLaserOff.connect(self._daq_ao_logic.voltage_off)

        # actions on changing laser spinbox values
        self.spinbox_list = [self._mw.laser1_control_SpinBox, self._mw.laser2_control_SpinBox,
                             self._mw.laser3_control_SpinBox, self._mw.laser4_control_SpinBox]

        # actualize the laser intensity dictionary
        self._mw.laser1_control_SpinBox.valueChanged.connect(lambda: self._daq_ao_logic.update_intensity_dict(self._daq_ao_logic._laser_dict['laser1']['label'], self._mw.laser1_control_SpinBox.value()))
        self._mw.laser2_control_SpinBox.valueChanged.connect(lambda: self._daq_ao_logic.update_intensity_dict(self._daq_ao_logic._laser_dict['laser2']['label'], self._mw.laser2_control_SpinBox.value()))
        self._mw.laser3_control_SpinBox.valueChanged.connect(lambda: self._daq_ao_logic.update_intensity_dict(self._daq_ao_logic._laser_dict['laser3']['label'], self._mw.laser3_control_SpinBox.value()))
        self._mw.laser4_control_SpinBox.valueChanged.connect(lambda: self._daq_ao_logic.update_intensity_dict(self._daq_ao_logic._laser_dict['laser4']['label'], self._mw.laser4_control_SpinBox.value()))
        # lambda function is used to pass in an additional argument. See also the decorator @QtCore.Slot(str, int).
        # in case lambda does not work well on runtime, check functools.partial
        # or signal mapper ? to explore ..

        # update GUI when intensity is changed programatically
        self._daq_ao_logic.sigIntensityChanged.connect(self.update_laser_spinbox)

        # filter dockwidget
        # initialize the combobox displaying the available filters
        self.init_filter_selection()

        # signals currentIndexChanged vs activated: currentIndexChanged is sent regardless of being done programatically or by user interaction whereas activated is only sent on user interaction
        # activated seems the better option, then the signal is only sent when a new value is selected, whereas the slot change_filter is called twice when using currentIndexChanged, once for the old index, once for the new one. comparable to radiobutton toggled vs clicked
        self._mw.filter_ComboBox.activated[str].connect(self.change_filter)

        self.sigFilterChanged.connect(self._filterwheel_logic.set_position)

        # control signal from logic to update GUI when filter was manually changed
        self._filterwheel_logic.sigNewFilterSetting.connect(self.update_filter_display)

        # this needs to go to the end because the fields on the gui must first be initialized
        self.initSaveSettingsUI()

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
        self._cam_sd.accepted.connect(self.cam_update_settings)  # ok button
        self._cam_sd.rejected.connect(self.cam_keep_former_settings)  # cancel buttons
        # self._cam_sd.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(self.cam_update_settings)
        
        if not self._camera_logic.has_temp:
            self._cam_sd.temp_spinBox.setEnabled(False)
            self._cam_sd.label_3.setEnabled(False)

        # write the configuration to the settings window of the GUI.
        self.cam_keep_former_settings()

    # slots of the camerasettingswindow
    def cam_update_settings(self):
        """ Write new settings from the gui to the logic module
        """
        self._camera_logic.set_exposure(self._cam_sd.exposure_doubleSpinBox.value())
        self._camera_logic.set_gain(self._cam_sd.gain_spinBox.value())
        self._camera_logic.set_temperature(int(self._cam_sd.temp_spinBox.value()))

    def cam_keep_former_settings(self):
        """ Keep the old settings and restores them in the gui. 
        """
        self._cam_sd.exposure_doubleSpinBox.setValue(self._camera_logic._exposure)
        self._cam_sd.gain_spinBox.setValue(self._camera_logic._gain)
        self._cam_sd.temp_spinBox.setValue(self._camera_logic.temperature_setpoint)

    # slot to open the camerasettingswindow
    def open_camera_settings(self):
        """ Opens the settings menu. 
        """
        self._cam_sd.exec_()

    # Initialisation of the save settings windows
    def initSaveSettingsUI(self):
        """ Definition, configuration and initialisation of the dialog window which allows to configure the video saving
        """
        # Create the Camera settings window
        self._save_sd = SaveSettingDialog()
        # Connect the action of the settings window with the code:
        self._save_sd.accepted.connect(self.save_video_accepted)  # ok button
        self._save_sd.rejected.connect(self.cancel_save)  # cancel buttons

        # add a validator to the folder name lineedit
        self._save_sd.foldername_LineEdit.setValidator(NameValidator(empty_allowed=True))  # empty_allowed=True should be set or not ?

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
        """
        """
        folder_name = self._save_sd.foldername_LineEdit.text()
        default_path = self._mw.save_path_LineEdit.text()
        today = datetime.today().strftime('%Y-%m-%d')
        path = os.path.join(default_path, today, folder_name)
        # self.log.info('created path: {}'.format(path))

        n_frames = self._save_sd.n_frames_SpinBox.value()
        self._last_path = path  # maintain this variable to make it accessible for metadata saving

        display = self._save_sd.enable_display_CheckBox.isChecked()

        # we need a case structure here: if the dialog was called from save video button, sigVideoSavingStart must be
        # emitted, if it was called from save long video (=spooling) sigSpoolingStart must be emitted
        if self._video:
            self.sigVideoSavingStart.emit(path, n_frames, display)
        elif self._spooling:
            self.sigSpoolingStart.emit(path, n_frames, display)
        else:  # to do: write an error message or something like this ???
            pass

    def cancel_save(self):
        self.set_default_values()
        self.reset_toolbuttons()  # this resets the toolbar buttons to callable state
        self._video = False
        self._spooling = False

    def set_default_values(self):
        self._save_sd.foldername_LineEdit.setText(self._mw.samplename_LineEdit.text())
        self.update_path_label()
        self._save_sd.n_frames_SpinBox.setValue(1)
        self.update_acquisition_time()
        self._save_sd.enable_display_CheckBox.setChecked(False)  # set True later when the procedure works

    def update_path_label(self):
        folder_name = self._save_sd.foldername_LineEdit.text()
        default_path = self._mw.save_path_LineEdit.text()
        today = datetime.today().strftime('%Y-%m-%d')
        path = os.path.join(default_path, today, folder_name)  #
        self._save_sd.complete_path_Label.setText('Save to: {}'.format(path))

    def update_acquisition_time(self):
        exp_time = float(self._mw.exposure_LineEdit.text())  # if andor camera is used, the kinetic_time is retrieved here
        n_frames = self._save_sd.n_frames_SpinBox.value()
        acq_time = exp_time * n_frames
        self._save_sd.acquisition_time_DoubleSpinBox.setValue(acq_time)

    def update_n_frames(self):
        exp_time = float(self._mw.exposure_LineEdit.text())  # if andor camera is used, the kinetic_time is retrieved here
        acq_time = self._save_sd.acquisition_time_DoubleSpinBox.value()
        n_frames = int(round(acq_time / exp_time))
        self._save_sd.n_frames_SpinBox.setValue(n_frames)
        self.update_acquisition_time()  # call this to adapt the acquisition time to the nearest possible value according to n_frames




    # slot to open the save settings window
    def open_save_settings(self):
        """ Opens the settings menu.
        """
        self._save_sd.exec_()

    # definition of the slots
    # camera dockwidget
    @QtCore.Slot(float)
    def update_exposure(self, exposure):
        # indicate the kinetic time instead of the exposure time for andor ixon camera
        if self._camera_logic.get_name() == 'iXon Ultra 897':
            self._mw.exposure_LineEdit.setText(str(self._camera_logic.get_kinetic_time()))
        else:
            self._mw.exposure_LineEdit.setText(str(exposure))

    @QtCore.Slot(float)
    def update_gain(self, gain):
        self._mw.gain_LineEdit.setText(str(gain))

    @QtCore.Slot(float)
    def update_temperature(self, temp):
        self._mw.temperature_LineEdit.setText(str(temp))

    def take_image_clicked(self):
        """ Callback from take_image_Action. Emits a signal that is connected to the logic module 
        and disables the tool buttons
        """
        self.sigImageStart.emit()
        self._mw.take_image_Action.setDisabled(True)
        self._mw.start_video_Action.setDisabled(True)
        self._mw.save_last_image_Action.setDisabled(True)
        self._mw.save_video_Action.setDisabled(True)
        self._mw.spooling_Action.setDisabled(True)

    def acquisition_finished(self):
        """ Callback from sigAcquisitionFinished. Resets all tool buttons to callable state
        """
        self._mw.take_image_Action.setChecked(False)
        self._mw.take_image_Action.setDisabled(False)
        self._mw.start_video_Action.setDisabled(False)
        self._mw.save_last_image_Action.setDisabled(False)
        self._mw.save_video_Action.setDisabled(False)
        if self._camera_logic.get_name() == 'iXon Ultra 897':  # in this case the button needs to be reactivated
            self._mw.spooling_Action.setDisabled(False)

    def start_video_clicked(self):
        """ Callback from start_video_Action. 
        Handling the Start button to stop and restart the counter.
        """
        self._mw.take_image_Action.setDisabled(True)
        self._mw.save_last_image_Action.setDisabled(True)
        self._mw.save_video_Action.setDisabled(True)
        self._mw.spooling_Action.setDisabled(True)
        if self._camera_logic.enabled:
            self._mw.start_video_Action.setText('Live')
            self.sigVideoStop.emit()
        else:
            self._mw.start_video_Action.setText('Stop Live')
            self.sigVideoStart.emit()

    def enable_take_image_action(self):
        """ Callback from SigVideoFinished. Resets the state of the take_image_Action tool button

        and of all other camera toolbuttons which were added afterwards
        """
        self._mw.take_image_Action.setEnabled(True)
        self._mw.save_last_image_Action.setEnabled(True)
        self._mw.save_video_Action.setEnabled(True)
        if self._camera_logic.get_name() == 'iXon Ultra 897':  # in this case the button needs to be reactivated
            self._mw.spooling_Action.setEnabled(True)

    def update_data(self):
        """ Callback from sigUpdateDisplay in the camera_logic module. 
        Get the image data from the logic and print it on the window
        """
        image_data = self._camera_logic.get_last_image()
        self.imageitem.setImage(image_data)
        ## old version. to be removed soon
        # self._mw.camera_ImageView.setImage(image_data)
        # self._mw.camera_ImageView.ui.histogram.show()

    @QtCore.Slot()
    def save_last_image_clicked(self):
        """ saves the last image, using a format adalogously to video saving procedures

        filenamestem/000_type/file.tiff
        example: /home/barho/images/2020-12-16/samplename/000_Image/image.tiff
        filenamestem is generated below ex. /home/barho/images/2020-12-16/foldername

        folder_name is taken from the field on GUI. to decide : put it in a dialog as for the save settings dialog ??
        """
        # save data
        default_path = self._mw.save_path_LineEdit.text()
        today = datetime.today().strftime('%Y-%m-%d')
        folder_name = self._mw.samplename_LineEdit.text()
        filenamestem = os.path.join(default_path, today, folder_name)
        self._last_path = filenamestem  # maintain this variable to make it accessible for metadata saving
        self._camera_logic.save_last_image(filenamestem)
        # save metadata
        complete_path = self._camera_logic._create_generic_filename(filenamestem, '_Image', 'parameters', '.txt', addfile=True)
        metadata = self._create_metadata_dict()
        with open(complete_path, 'w') as file:
            file.write(str(metadata))
        self.log.info('saved metadata to {}'.format(complete_path))

    @QtCore.Slot()
    def save_video_clicked(self):
        # disable camera related toolbuttons
        self._mw.save_video_Action.setDisabled(True)
        self._mw.take_image_Action.setDisabled(True)
        self._mw.start_video_Action.setDisabled(True)
        self._mw.save_last_image_Action.setDisabled(True)
        self._mw.spooling_Action.setDisabled(True)
        # set the flag to True so that the dialog nows that is was called from save video button
        self._video = True
        # open the save settings window
        self.open_save_settings()

    def video_saving_finished(self):
        """ handles the saving of the experiment's metadata. resets the toolbuttons to return to callable state """
        # save metadata to additional txt file in the same folder as the experiment
        # this needs to be done by the gui because this is where all the parameters are available.
        # The camera logic has not access to all needed parameters
        filenamestem = self._last_path  # when the save dialog is called, this variable is generated to keep it accessible for the metadata saving
        complete_path = self._camera_logic._create_generic_filename(filenamestem, '_Movie', 'parameters', '.txt', addfile=True)
        metadata = self._create_metadata_dict()
        with open(complete_path, 'w') as file:
            file.write(str(metadata))
        self.log.info('saved metadata to {}'.format(complete_path))
        # reset the flag
        self._video = False
        # toolbuttons
        self._mw.save_video_Action.setDisabled(False)
        self._mw.save_video_Action.setChecked(False)
        self._mw.take_image_Action.setDisabled(False)
        self._mw.start_video_Action.setDisabled(False)
        self._mw.save_last_image_Action.setDisabled(False)
        if self._camera_logic.get_name() == 'iXon Ultra 897':  # in this case the button needs to be reactivated
            self._mw.spooling_Action.setDisabled(False)


    def set_spooling_clicked(self):
        # disable camera related toolbuttons
        self._mw.spooling_Action.setDisabled(True)
        self._mw.take_image_Action.setDisabled(True)
        self._mw.start_video_Action.setDisabled(True)
        self._mw.save_last_image_Action.setDisabled(True)
        self._mw.save_video_Action.setDisabled(True)
        # set the flag to True so that the dialog nows that is was called from save video button
        self._spooling = True
        # open the save settings dialog
        self.open_save_settings()

        # path = '/home/barho/testfolder/testimage' # set this programatically # 'C:\\Users\\admin\\qudi-cbs-testdata\\images\\testimg'
        # n_frames = 1
        # self.sigSpoolingStart.emit(path, n_frames)

    def spooling_finished(self):
        """ handles the saving of the experiment's metadata. resets the toolbuttons to return to callable state """
        # save metadata to additional txt file in the same folder as the experiment
        # this needs to be done by the gui because this is where all the parameters are available.
        # The camera logic has not access to all needed parameters
        filenamestem = self._last_path  # when the save dialog is called, this variable is generated to keep it accessible for the metadata saving
        complete_path = self._camera_logic._create_generic_filename(filenamestem, '_Movie', 'parameters', '.txt', addfile=True)
        metadata = self._create_metadata_dict()
        with open(complete_path, 'w') as file:
            file.write(str(metadata))
        self.log.info('saved metadata to {}'.format(complete_path))
        # reset the flag
        self._spooling = False
        # enable the toolbuttons
        self._mw.spooling_Action.setDisabled(False)
        self._mw.spooling_Action.setChecked(False)
        self._mw.take_image_Action.setDisabled(False)
        self._mw.start_video_Action.setDisabled(False)
        self._mw.save_last_image_Action.setDisabled(False)
        self._mw.save_video_Action.setDisabled(False)

    def reset_toolbuttons(self):
        """ this slot is called when save dialog is canceled

        Sets the camera toolbuttons to callable state"""
        self._mw.take_image_Action.setDisabled(False)
        self._mw.start_video_Action.setDisabled(False)
        self._mw.save_last_image_Action.setDisabled(False)
        self._mw.save_video_Action.setDisabled(False)
        self._mw.save_video_Action.setChecked(False)
        if self._camera_logic.get_name() == 'iXon Ultra 897':  # in this case the button needs to be reactivated
            self._mw.spooling_Action.setDisabled(False)
            self._mw.spooling_Action.setChecked(False)

    def _create_metadata_dict(self):
        """ create a dictionary containing the metadata"""
        metadata = {}
        metadata['timestamp'] = datetime.now().strftime('%m-%d-%Y, %H:%M:%S')
        filterpos = self._filterwheel_logic.get_position()
        filterdict = self._filterwheel_logic.get_filter_dict()
        label = 'filter{}'.format(filterpos)
        metadata['filter'] = filterdict[label]['name']
        metadata['gain'] = self._camera_logic.get_gain()
        metadata['exposuretime (s)'] = self._camera_logic.get_exposure()
        intensity_dict = self._daq_ao_logic._intensity_dict
        keylist = [key for key in intensity_dict if intensity_dict[key] != 0]
        laser_dict = self._daq_ao_logic.get_laser_dict()
        metadata['laser'] = [laser_dict[key]['wavelength'] for key in keylist]
        metadata['intensity (%)'] = [intensity_dict[key] for key in keylist]
        if self._camera_logic.has_temp == True:
            metadata['sensor temperature'] = self._camera_logic.get_temperature()
        else:
            metadata['sensor temperature'] = 'Not available'
        return metadata

    # camera status dockwidget
    @QtCore.Slot(str, str, str, str)  # temperature already converted into str
    def update_camera_status_display(self, ready_state, shutter_state='', cooler_state='', temperature=''):
        self._mw.camera_status_LineEdit.setText(ready_state)
        self._mw.shutter_status_LineEdit.setText(shutter_state)
        self._mw.cooler_status_LineEdit.setText(cooler_state)
        self._mw.temperature_LineEdit.setText(temperature)

    # laser dockwidget
    def laser_on_clicked(self):
        """
        """
        if self._daq_ao_logic.enabled:
            # laser is initially on
            self._mw.laser_zero_Action.setDisabled(False)
            self._mw.laser_on_Action.setText('Laser On')
            self.sigLaserOff.emit()
            # enable filter setting again
            self._mw.filter_ComboBox.setEnabled(True)

        else:
            # laser is initially off
            self._mw.laser_zero_Action.setDisabled(True)
            self._mw.laser_on_Action.setText('Laser Off')
            self.sigLaserOn.emit()
            # do not change filters while laser is on
            self._mw.filter_ComboBox.setEnabled(False)

    def laser_set_to_zero(self):
        """
        """
        for item in self.spinbox_list: 
            item.setValue(0)

    def update_laser_spinbox(self):
        """ update values in laser spinboxes if the intensity dictionary in the logic was changed """
        for index, item in enumerate(self.spinbox_list):
            label = 'laser'+str(index + 1) # create the label to address the corresponding laser
            item.setValue(self._daq_ao_logic._intensity_dict[label])

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


    def select_sensor_region(self):
        # to be completed with the deactivation of the selector tool
        self._mw.camera_ScanPlotWidget.toggle_selection(True)
        self._region_selector_enabled = True

    def mouse_area_selected(self, rect):
        self.log.info('selected an area')
        self.log.info(rect.getCoords())
        hstart, vstart, hend, vend = rect.getCoords()
        hstart = round(hstart)
        vstart = round(vstart)
        hend = round(hend)
        vend = round(vend)
        self.log.info('hstart={}, vstart={}, hend={}, vend={}'.format(hstart, vstart, hend, vend))
            
# for testing
# if __name__ == '__main__':
#    app = QtWidgets.QApplication(sys.argv)
#    # it's required to save a reference to MainWindow.
#    # if it goes out of scope, it will be destroyed.
#    mw = BasicWindow()
#    sys.exit(app.exec())
