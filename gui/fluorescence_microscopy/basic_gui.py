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

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy import uic
import pyqtgraph as pg

from gui.guibase import GUIBase
from core.connector import Connector


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
    filterwheel_logic = Connector(interface='FilterwheelLogic')

    # Signals
    # signals to camera logic
    sigVideoStart = QtCore.Signal()
    sigVideoStop = QtCore.Signal()
    sigImageStart = QtCore.Signal()

    sigVideoStartSaving = QtCore.Signal()
    sigVideoStopSaving = QtCore.Signal()

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
        self._mw.start_video_Action.setEnabled(True)
        self._mw.start_video_Action.setChecked(self._camera_logic.enabled)
        self._mw.start_video_Action.triggered.connect(self.start_video_clicked)

        self._mw.take_image_Action.setEnabled(True)
        self._mw.take_image_Action.setChecked(self._camera_logic.enabled)
        self._mw.take_image_Action.triggered.connect(self.take_image_clicked)

        self._camera_logic.sigUpdateDisplay.connect(self.update_data)
        self._camera_logic.sigAcquisitionFinished.connect(self.acquisition_finished)
        self._camera_logic.sigVideoFinished.connect(self.enable_take_image_action)
        
        self._mw.save_last_image_Action.triggered.connect(self.save_last_image_clicked)
        # self._mw.save_video_Action.triggered.connect(self.save_video_clicked)

        # spooling action only available for andor iXon Ultra camera
        if not self._camera_logic.get_name() == 'iXon Ultra 897':
            self._mw.spooling_Action.setEnabled(False)
        self._mw.spooling_Action.triggered.connect(self.set_spooling_clicked)


        # starting the physical measurement
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
        """ Write new settings from the gui to the file. 
        """
        self._camera_logic.set_exposure(self._cam_sd.exposure_doubleSpinBox.value())
        self._camera_logic.set_gain(self._cam_sd.gain_spinBox.value())
        self._camera_logic.set_temperature(int(self._cam_sd.temp_spinBox.value()))

    def cam_keep_former_settings(self):
        """ Keep the old settings and restores them in the gui. 
        """
        self._cam_sd.exposure_doubleSpinBox.setValue(self._camera_logic._exposure)
        self._cam_sd.gain_spinBox.setValue(self._camera_logic._gain)
        self._cam_sd.temp_spinBox.setValue(self._camera_logic._temperature_setpoint)

    # slot to open the camerasettingswindow
    def open_camera_settings(self):
        """ Opens the settings menu. 
        """
        self._cam_sd.exec_()

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

    def acquisition_finished(self):
        """ Callback from sigAcquisitionFinished. Resets all tool buttons to callable state
        """
        self._mw.take_image_Action.setChecked(False)
        self._mw.take_image_Action.setDisabled(False)
        self._mw.start_video_Action.setDisabled(False)
        self._mw.save_last_image_Action.setDisabled(False)
        self._mw.save_video_Action.setDisabled(False)

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

    @QtCore.Slot()
    def save_last_image_clicked(self):
        """ saves the last image, using user specified filepath and filename (with a generated suffix)
        """
        filename = self._mw.filename_LineEdit.text()
        path = self._mw.save_path_LineEdit.text()
        self._camera_logic.save_last_image(path, filename)



    # @QtCore.Slot()
    # def save_video_clicked(self):
    #     self._mw.take_image_Action.setDisabled(True)
    #     self._mw.save_last_image_Action.setDisabled(True)
    #     if self._camera_logic.saving:
    #         self._mw.save_video_Action.setText('Save Video')
    #         self.sigVideoStopSaving.emit()
    #     else:
    #         self._mw.save_video_Action.setText('Stop Saving')
    #         self.sigVideoStartSaving.emit()


    def set_spooling_clicked(self):
        # add here disableing of the other tool buttons # or use sleep in the start spooling method then everything should be unavailable
        # use a dialog window to get filename and time of film or number of images ?
        filenamestem = '/home/barho/testfolder/testimage' # set this programatically # 'C:\\Users\\admin\\qudi-cbs-testdata\\images\\testimg'
        time_film = 5  # in seconds
        self._camera_logic.start_spooling(filenamestem, time_film)

    # camera status dockwidget
    @QtCore.Slot(str, str, str)
    def update_camera_status_display(self, ready_state, shutter_state='', cooler_state=''):
        self._mw.camera_status_LineEdit.setText(ready_state)
        self._mw.shutter_status_LineEdit.setText(shutter_state)
        self._mw.cooler_status_LineEdit.setText(cooler_state)

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



            
# for testing
# if __name__ == '__main__':
#    app = QtWidgets.QApplication(sys.argv)
#    # it's required to save a reference to MainWindow.
#    # if it goes out of scope, it will be destroyed.
#    mw = BasicWindow()
#    sys.exit(app.exec())
