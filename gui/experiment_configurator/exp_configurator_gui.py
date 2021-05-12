# -*- coding: utf-8 -*-
"""
This module contains a GUI that allows to create a user config file for a Task
"""
import os
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy import uic

from gui.guibase import GUIBase
from core.connector import Connector
from core.configoption import ConfigOption


class ExpConfiguratorWindow(QtWidgets.QMainWindow):
    """ Class defined for the main window (not the module)

    """
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_exp_configurator.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)

        self.show()


class ExpConfiguratorGUI(GUIBase):

    """ Main window that helps to define the user the configuration file for the different types of experiments.

    Example config for copy-paste:

    exp_configurator_gui:
        module.Class: 'experiment_configurator.exp_configurator_gui.ExpConfiguratorGUI'
        default_location_qudi_files: '/home/barho/qudi_files'
        connect:
            exp_config_logic: 'exp_config_logic'
    """

    # connector to logic module
    exp_logic = Connector(interface='ExpConfigLogic')

    # config options
    default_location = ConfigOption('default_location_qudi_files', missing='warn')
    # serves as a path stem to default locations where experimental configurations are saved, and where roi lists and injections lists are loaded

    # Signals
    sigSaveConfig = QtCore.Signal(str, str, str)
    sigSaveConfigCopy = QtCore.Signal(str)
    sigLoadConfig = QtCore.Signal(str)
    sigAddEntry = QtCore.Signal(str, int)
    sigDeleteEntry = QtCore.Signal(QtCore.QModelIndex)

    def __init__(self, config, **kwargs):
        # load connection
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Required initialization steps.
        """
        self._exp_logic = self.exp_logic()

        self._mw = ExpConfiguratorWindow()
        self._mw.formWidget.hide()

        # initialize combobox
        self._mw.select_experiment_ComboBox.addItems(self._exp_logic.experiments)
        self._mw.fileformat_ComboBox.addItems(self._exp_logic.supported_fileformats)

        # hide save configuration toolbuttons while no experiment selected yet
        self._mw.save_config_Action.setDisabled(True)
        self._mw.save_config_copy_Action.setDisabled(True)

        # initialize the entry form
        self.init_configuration_form()

        # initialize list view
        self._mw.imaging_sequence_ListView.setModel(self._exp_logic.img_sequence_model)

        # signals
        # internal signals
        # toolbar
        self._mw.save_config_Action.triggered.connect(self.save_config_clicked)
        self._mw.save_config_copy_Action.triggered.connect(self.save_config_copy_clicked)
        self._mw.load_config_Action.triggered.connect(self.load_config_clicked)
        self._mw.clear_all_Action.triggered.connect(self._exp_logic.init_default_config_dict)

        # widgets on the configuration form
        self._mw.select_experiment_ComboBox.activated[str].connect(self.update_form)

        self._mw.sample_name_LineEdit.textChanged.connect(self._exp_logic.update_sample_name)
        self._mw.dapi_CheckBox.stateChanged.connect(self._exp_logic.update_is_dapi)
        self._mw.rna_CheckBox.stateChanged.connect(self._exp_logic.update_is_rna)
        self._mw.exposure_DSpinBox.valueChanged.connect(self._exp_logic.update_exposure)
        self._mw.gain_SpinBox.valueChanged.connect(self._exp_logic.update_gain)
        self._mw.num_frames_SpinBox.valueChanged.connect(self._exp_logic.update_frames)
        self._mw.filterpos_ComboBox.currentIndexChanged.connect(self._exp_logic.update_filterpos)
        self._mw.save_path_LineEdit.textChanged.connect(self._exp_logic.update_save_path)
        self._mw.fileformat_ComboBox.currentTextChanged.connect(self._exp_logic.update_fileformat)
        self._mw.num_z_planes_SpinBox.valueChanged.connect(self._exp_logic.update_num_z_planes)
        self._mw.z_step_DSpinBox.valueChanged.connect(self._exp_logic.update_z_step)
        self._mw.centered_focal_plane_CheckBox.stateChanged.connect(self._exp_logic.update_centered_focal_plane)
        self._mw.roi_list_path_LineEdit.textChanged.connect(self._exp_logic.update_roi_path)
        self._mw.injections_list_LineEdit.textChanged.connect(self._exp_logic.update_injections_path)
        self._mw.illumination_time_DSpinBox.valueChanged.connect(self._exp_logic.update_illumination_time)

        # pushbuttons
        self._mw.add_entry_PushButton.clicked.connect(self.add_entry_clicked)
        self._mw.delete_entry_PushButton.clicked.connect(self.delete_entry_clicked)
        self._mw.delete_all_PushButton.clicked.connect(self._exp_logic.delete_imaging_list)

        # get-current-value pushbutton signals
        self._mw.get_exposure_PushButton.clicked.connect(self._exp_logic.get_exposure)
        self._mw.get_gain_PushButton.clicked.connect(self._exp_logic.get_gain)
        self._mw.get_filterpos_PushButton.clicked.connect(self._exp_logic.get_filterpos)

        # load file pushbutton signals
        self._mw.load_roi_PushButton.clicked.connect(self.load_roi_list_clicked)
        self._mw.load_injections_PushButton.clicked.connect(self.load_injections_clicked)

        # signals to logic
        self.sigSaveConfig.connect(self._exp_logic.save_to_exp_config_file)
        self.sigLoadConfig.connect(self._exp_logic.load_config_file)
        self.sigAddEntry.connect(self._exp_logic.add_entry_to_imaging_list)
        self.sigDeleteEntry.connect(self._exp_logic.delete_entry_from_imaging_list)

        # signals from logic
        self._exp_logic.sigConfigDictUpdated.connect(self.update_entries)
        self._exp_logic.sigImagingListChanged.connect(self.update_listview)
        self._exp_logic.sigConfigLoaded.connect(self.display_loaded_config)

        # update the entries on the form
        self._exp_logic.init_default_config_dict()

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

    def init_configuration_form(self):
        self._mw.filterpos_ComboBox.addItems(self._exp_logic.filters)
        self._mw.laser_ComboBox.addItems(self._exp_logic.lasers)

    def update_form(self):
        experiment = self._mw.select_experiment_ComboBox.currentText()
        self._mw.save_config_Action.setDisabled(False)
        self._mw.save_config_copy_Action.setDisabled(False)
        if experiment == 'Select your experiment..':
            self._mw.formWidget.hide()
            self._mw.save_config_Action.setDisabled(True)
            self._mw.save_config_copy_Action.setDisabled(True)
        elif experiment == 'Multicolor imaging':
            self._mw.formWidget.setVisible(True)
            self.set_visibility_general_settings(True)
            self.set_visibility_camera_settings(True)
            self.set_visibility_filter_settings(True)
            self.set_visibility_imaging_settings(True)
            self.set_visibility_save_settings(True)
            self.set_visibility_scan_settings(False)
            self.set_visibility_documents_settings(False)
            self.set_visibility_prebleaching_settings(False)
        elif experiment == 'Multicolor scan PALM':
            self._mw.formWidget.setVisible(True)
            self.set_visibility_general_settings(True)
            self.set_visibility_camera_settings(True)
            self.set_visibility_filter_settings(True)
            self.set_visibility_imaging_settings(True)
            self.set_visibility_save_settings(True)
            self.set_visibility_scan_settings(True)
            self.set_visibility_documents_settings(False)
            self.set_visibility_prebleaching_settings(False)
        elif experiment == 'Multicolor scan RAMM':
            self._mw.formWidget.setVisible(True)
            self.set_visibility_general_settings(True)
            self.set_visibility_camera_settings(True)
            self.set_visibility_filter_settings(False)
            self.set_visibility_imaging_settings(True)
            self.set_visibility_save_settings(True)
            self.set_visibility_scan_settings(True)
            self.set_visibility_documents_settings(False)
            self.set_visibility_prebleaching_settings(False)

            # additional visibility settings
            self._mw.gain_Label.setVisible(False)
            self._mw.gain_SpinBox.setVisible(False)
            self._mw.get_gain_PushButton.setVisible(False)
            self._mw.num_frames_Label.setVisible(False)
            self._mw.num_frames_SpinBox.setVisible(False)

        elif experiment == 'ROI multicolor scan PALM':
            self._mw.formWidget.setVisible(True)
            self.set_visibility_general_settings(True)
            self.set_visibility_camera_settings(True)
            self.set_visibility_filter_settings(True)
            self.set_visibility_imaging_settings(True)
            self.set_visibility_save_settings(True)
            self.set_visibility_scan_settings(True)
            self.set_visibility_documents_settings(True)
            self.set_visibility_prebleaching_settings(False)

            # additional visibility modifications
            self._mw.injections_list_Label.setVisible(False)
            self._mw.injections_list_LineEdit.setVisible(False)
            self._mw.load_injections_PushButton.setVisible(False)

        elif experiment == 'ROI multicolor scan':  # maybe modifiy into ROI multicolor scan RAMM
            self._mw.formWidget.setVisible(True)
            self.set_visibility_general_settings(True)
            self.set_visibility_camera_settings(True)
            self.set_visibility_filter_settings(False)
            self.set_visibility_imaging_settings(True)
            self.set_visibility_save_settings(True)
            self.set_visibility_scan_settings(True)
            self.set_visibility_documents_settings(True)
            self.set_visibility_prebleaching_settings(False)

            # additional visibility modifications
            self._mw.dapi_CheckBox.setVisible(True)
            self._mw.rna_CheckBox.setVisible(True)
            self._mw.gain_Label.setVisible(False)
            self._mw.gain_SpinBox.setVisible(False)
            self._mw.get_gain_PushButton.setVisible(False)
            self._mw.injections_list_Label.setVisible(False)
            self._mw.injections_list_LineEdit.setVisible(False)
            self._mw.load_injections_PushButton.setVisible(False)
            self._mw.num_frames_Label.setVisible(False)
            self._mw.num_frames_SpinBox.setVisible(False)

        elif experiment == 'Fluidics':  # do we need this ?
            self._mw.formWidget.setVisible(True)
            self.set_visibility_general_settings(False)
            self.set_visibility_camera_settings(False)
            self.set_visibility_filter_settings(False)
            self.set_visibility_imaging_settings(False)
            self.set_visibility_save_settings(False)
            self.set_visibility_scan_settings(False)
            self.set_visibility_documents_settings(True)
            self.set_visibility_prebleaching_settings(False)

            # additional visibility modifications
            self._mw.roi_list_path_Label.setVisible(False)
            self._mw.roi_list_path_LineEdit.setVisible(False)
            self._mw.load_roi_PushButton.setVisible(False)

        elif experiment == 'Hi-M':
            self._mw.formWidget.setVisible(True)
            self.set_visibility_general_settings(True)
            self.set_visibility_camera_settings(True)
            self.set_visibility_filter_settings(False)
            self.set_visibility_imaging_settings(True)
            self.set_visibility_save_settings(True)
            self.set_visibility_scan_settings(True)
            self.set_visibility_documents_settings(True)
            self.set_visibility_prebleaching_settings(False)

            # additional visibility settings
            self._mw.gain_Label.setVisible(False)
            self._mw.gain_SpinBox.setVisible(False)
            self._mw.get_gain_PushButton.setVisible(False)
            self._mw.num_frames_Label.setVisible(False)
            self._mw.num_frames_SpinBox.setVisible(False)

        elif experiment == 'Photobleaching':
            self._mw.formWidget.setVisible(True)
            self.set_visibility_general_settings(False)
            self.set_visibility_camera_settings(False)
            self.set_visibility_filter_settings(False)
            self.set_visibility_imaging_settings(True)
            self.set_visibility_save_settings(False)
            self.set_visibility_scan_settings(False)
            self.set_visibility_documents_settings(True)
            self.set_visibility_prebleaching_settings(True)

            # additional visibility modifications
            self._mw.injections_list_Label.setVisible(False)
            self._mw.injections_list_LineEdit.setVisible(False)
            self._mw.load_injections_PushButton.setVisible(False)

        else:
            pass

    def set_visibility_general_settings(self, visible):
        """ Show or hide the block with the general ettings widgets
        :param bool visible: show widgets = True, hide widgets = False
        """
        self._mw.general_Label.setVisible(visible)
        self._mw.sample_name_Label.setVisible(visible)
        self._mw.sample_name_LineEdit.setVisible(visible)

        # the dapi and rna checkboxes are needed only for the ROI Multicolor scan
        self._mw.dapi_CheckBox.setVisible(False)
        self._mw.rna_CheckBox.setVisible(False)

    def set_visibility_camera_settings(self, visible):
        """ Show or hide the block with the camera settings widgets
        :param bool visible: show widgets = True, hide widgets = False
        """
        self._mw.cam_settings_Label.setVisible(visible)
        self._mw.exposure_Label.setVisible(visible)
        self._mw.exposure_DSpinBox.setVisible(visible)
        self._mw.get_exposure_PushButton.setVisible(visible)
        self._mw.gain_Label.setVisible(visible)
        self._mw.gain_SpinBox.setVisible(visible)
        self._mw.get_gain_PushButton.setVisible(visible)
        self._mw.num_frames_Label.setVisible(visible)
        self._mw.num_frames_SpinBox.setVisible(visible)

    def set_visibility_filter_settings(self, visible):
        """ Show or hide the block with the filter settings widgets
        :param bool visible: show widgets = True, hide widgets = False
        """
        self._mw.filter_settings_Label.setVisible(visible)
        self._mw.filterpos_Label.setVisible(visible)
        self._mw.filterpos_ComboBox.setVisible(visible)
        self._mw.get_filterpos_PushButton.setVisible(visible)

    def set_visibility_imaging_settings(self, visible):
        """ Show or hide the block with the imaging sequence widgets
        :param bool visible: show widgets = True, hide widgets = False
        """
        self._mw.imaging_settings_Label.setVisible(visible)
        self._mw.imaging_sequence_Label.setVisible(visible)
        self._mw.imaging_sequence_ListView.setVisible(visible)
        self._mw.laser_ComboBox.setVisible(visible)
        self._mw.laser_intensity_SpinBox.setVisible(visible)
        self._mw.delete_entry_PushButton.setVisible(visible)
        self._mw.add_entry_PushButton.setVisible(visible)
        self._mw.delete_all_PushButton.setVisible(visible)

    def set_visibility_save_settings(self, visible):
        """ Show or hide the block with the save settings widgets
        :param bool visible: show widgets = True, hide widgets = False
        """
        self._mw.save_settings_Label.setVisible(visible)
        self._mw.save_path_Label.setVisible(visible)
        self._mw.save_path_LineEdit.setVisible(visible)
        self._mw.fileformat_Label.setVisible(visible)
        self._mw.fileformat_ComboBox.setVisible(visible)

    def set_visibility_scan_settings(self, visible):
        """ Show or hide the block with the scan settings widgets
        :param bool visible: show widgets = True, hide widgets = False
        """
        self._mw.scan_settings_Label.setVisible(visible)
        self._mw.num_z_planes_Label.setVisible(visible)
        self._mw.num_z_planes_SpinBox.setVisible(visible)
        self._mw.z_step_Label.setVisible(visible)
        self._mw.z_step_DSpinBox.setVisible(visible)
        self._mw.centered_focal_plane_CheckBox.setVisible(visible)

    def set_visibility_documents_settings(self, visible):
        """ Show or hide the block with the additional documents settings widgets
        :param bool visible: show widgets = True, hide widgets = False
        """
        self._mw.documents_Label.setVisible(visible)
        self._mw.roi_list_path_Label.setVisible(visible)
        self._mw.roi_list_path_LineEdit.setVisible(visible)
        self._mw.load_roi_PushButton.setVisible(visible)
        self._mw.injections_list_Label.setVisible(visible)
        self._mw.injections_list_LineEdit.setVisible(visible)
        self._mw.load_injections_PushButton.setVisible(visible)

    def set_visibility_prebleaching_settings(self, visible):
        """ Show or hide the block with the prebleaching settings widgets
        :param bool visible: show widgets = True, hide widgets = False
        """
        self._mw.prebleach_settings_Label.setVisible(visible)
        self._mw.illumination_time_Label.setVisible(visible)
        self._mw.illumination_time_DSpinBox.setVisible(visible)

    def save_config_clicked(self):
        path = os.path.join(self.default_location, 'qudi_task_config_files') # '/home/barho/qudi-cbs-experiment-config'  # 'C:/Users/admin/qudi-cbs-user-configs'  # later: from config according to used computer
        self.log.info(path)
        experiment = self._mw.select_experiment_ComboBox.currentText()
        self.sigSaveConfig.emit(path, experiment, None)

    def save_config_copy_clicked(self):
        path = os.path.join(self.default_location, 'qudi_task_config_files')
        experiment = self._mw.select_experiment_ComboBox.currentText()
        this_file = QtWidgets.QFileDialog.getSaveFileName(self._mw, 'Save copy of experiental configuration',
                                                          path, 'yaml files (*.yaml)')[0]
        filename = os.path.split(this_file)[1]
        if this_file:
            self.sigSaveConfig.emit(path, experiment, filename)

    def load_config_clicked(self):
        data_directory = os.path.join(self.default_location, 'qudi_task_config_files') # '/home/barho/qudi-cbs-experiment-config'  # 'C:\\Users\\admin\\qudi-cb-user-configs'  # we will use this as default location to look for files
        this_file = QtWidgets.QFileDialog.getOpenFileName(self._mw,
                                                          'Open experiment configuration',
                                                          data_directory,
                                                          'yaml files (*.yaml)')[0]
        if this_file:
            self.sigLoadConfig.emit(this_file)

    def update_entries(self):
        self._mw.sample_name_LineEdit.setText(self._exp_logic.config_dict.get('sample_name', ''))
        self._mw.exposure_DSpinBox.setValue(self._exp_logic.config_dict.get('exposure', 0.0))
        self._mw.gain_SpinBox.setValue(self._exp_logic.config_dict.get('gain', 0))
        self._mw.num_frames_SpinBox.setValue(self._exp_logic.config_dict.get('num_frames', 1))
        self._mw.filterpos_ComboBox.setCurrentIndex(self._exp_logic.config_dict.get('filter_pos', 1) - 1)  # zero indexing
        self._exp_logic.img_sequence_model.layoutChanged.emit()
        self._mw.save_path_LineEdit.setText(self._exp_logic.config_dict.get('save_path', ''))
        self._mw.fileformat_ComboBox.setCurrentText(self._exp_logic.config_dict.get('file_format', ''))
        self._mw.num_z_planes_SpinBox.setValue(self._exp_logic.config_dict.get('num_z_planes', 1))
        self._mw.z_step_DSpinBox.setValue(self._exp_logic.config_dict.get('z_step', 0.0))
        self._mw.centered_focal_plane_CheckBox.setChecked(self._exp_logic.config_dict.get('centered_focal_plane', False))
        self._mw.roi_list_path_LineEdit.setText(self._exp_logic.config_dict.get('roi_list_path', ''))
        self._mw.injections_list_LineEdit.setText(self._exp_logic.config_dict.get('injections_path', ''))
        self._mw.illumination_time_DSpinBox.setValue(self._exp_logic.config_dict.get('illumination_time', 0.0))

    def add_entry_clicked(self):
        """ callback from pushbutton inserting an item into the imaging sequence list"""
        lightsource = self._mw.laser_ComboBox.currentText()  # or replace by current index
        intensity = self._mw.laser_intensity_SpinBox.value()
        self.sigAddEntry.emit(lightsource, intensity)

    def update_listview(self):
        self._exp_logic.img_sequence_model.layoutChanged.emit()
        # for the delete entry case, if one row is selected then it will be deleted
        indexes = self._mw.imaging_sequence_ListView.selectedIndexes()
        if indexes:
            self._mw.imaging_sequence_ListView.clearSelection()

    def delete_entry_clicked(self):
        indexes = self._mw.imaging_sequence_ListView.selectedIndexes()
        if indexes:
            # Indexes is a list of a single item in single-select mode.
            index = indexes[0]
            self.sigDeleteEntry.emit(index)

    def load_roi_list_clicked(self):
        data_directory = os.path.join(self.default_location, 'qudi_roi_lists')
        this_file = QtWidgets.QFileDialog.getOpenFileName(self._mw,
                                                          'Open ROI list',
                                                          data_directory,
                                                          'json files (*.json)')[0]
        if this_file:
            self._mw.roi_list_path_LineEdit.setText(this_file)

    def load_injections_clicked(self):
        data_directory = os.path.join(self.default_location, 'qudi_injection_parameters')
        this_file = QtWidgets.QFileDialog.getOpenFileName(self._mw,
                                                          'Open injections file',
                                                          data_directory,
                                                          'yaml files (*.yaml)')[0]
        # print(this_file)
        if this_file:
            self._mw.injections_list_LineEdit.setText(this_file)

    def display_loaded_config(self):
        self._mw.select_experiment_ComboBox.setCurrentText(self._exp_logic.config_dict['experiment'])
        self.update_form()
        self.update_entries()

# clear all toolbutton: reset also selectors for imaging sequence to default values ? (first laser, 0)



