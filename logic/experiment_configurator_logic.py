# -*- coding: utf-8 -*-
"""
Created on Wed Feb 17 2021

@author: fbarho

This module contains the logic for the experiment configurator.
"""
import os
import yaml
from qtpy import QtCore
from logic.generic_logic import GenericLogic
from core.configoption import ConfigOption
from core.connector import Connector


class ImagingSequenceModel(QtCore.QAbstractListModel):
    """ This class contains the model class for the listview with the imaging sequence
    consisting of entries of the form (lightsource, intensity)
    """
    def __init__(self, *args, items=None, **kwargs):
        super(ImagingSequenceModel, self).__init__(*args, **kwargs)
        self.items = items or []

    def data(self, index, role):
        if role == QtCore.Qt.DisplayRole:
            source, intens = self.items[index.row()]
            return f'{source}: {intens}'

    def rowCount(self, index):
        return len(self.items)


class ExpConfigLogic(GenericLogic):
    """
    Class containing the logic for the setup of a configuration file for an experiment

    Example config for copy-paste:

    exp_config_logic:
        module.Class: 'experiment_configurator_logic.ExpConfigLogic'
        experiments:
            - 'Multichannel imaging'
            - 'Multichannel scan PALM'
            - 'Dummy experiment'
        supported fileformats:
            - 'tiff'
            - 'fits'
        default path: '/home/barho'
        connect:
            camera_logic: 'camera_logic'
            laser_logic: 'lasercontrol_logic'
            filterwheel_logic: 'filterwheel_logic'

    """
    # Define connectors to logic modules
    camera_logic = Connector(interface='CameraLogic')
    laser_logic = Connector(interface='LaserControlLogic')
    filterwheel_logic = Connector(interface='FilterwheelLogic')


    # signals
    sigConfigDictUpdated = QtCore.Signal()
    sigImagingListChanged = QtCore.Signal()
    sigConfigLoaded = QtCore.Signal()

    # attributes
    experiments = ConfigOption('experiments')
    supported_fileformats = ConfigOption('supported fileformats')
    default_path = ConfigOption('default path')

    config_dict = {}

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._camera_logic = self.camera_logic()
        self._laser_logic = self.laser_logic()
        self._filterwheel_logic = self.filterwheel_logic()

        # prepare the items that will go in the ComboBoxes on the GUI
        filter_dict = self._filterwheel_logic.get_filter_dict()
        self.filters = [filter_dict[key]['name'] for key in filter_dict]
        laser_dict = self._laser_logic.get_laser_dict()
        self.lasers = [laser_dict[key]['wavelength'] for key in laser_dict]

        self.img_sequence_model = ImagingSequenceModel()
        # add an additional entry to the experiment selector combobox with placeholder text
        self.experiments.insert(0, 'Select your experiment..')
        self.init_default_config_dict()

    def on_deactivate(self):
        """ Perform required deactivation. """
        pass

    def save_to_exp_config_file(self, path, experiment):
        """ Saves the current config_dict to a txt file using yaml style

        @param: str path: path to directory where the config file is saved
        @param: str filename: name of the config file including the suffix

        @returns None
        """
        if not os.path.exists(path):
            try:
                os.makedirs(path)  # recursive creation of all directories on the path
            except Exception as e:
                self.log.error(f'Error {e}.')

        config_dict = {}

        try:

            if experiment == 'Multicolor imaging':
                filename = 'multicolor_imaging_task_PALM.yaml'
                keys_to_extract = ['sample_name', 'filter_pos', 'exposure', 'gain', 'num_frames', 'save_path', 'imaging_sequence', 'file_format']
                config_dict = {key: self.config_dict[key] for key in keys_to_extract}
            elif experiment == 'Multicolor scan PALM':
                filename = 'multicolor_scan_task_PALM.yaml'
                keys_to_extract = ['sample_name', 'filter_pos', 'exposure', 'gain', 'num_frames', 'save_path', 'file_format', 'imaging_sequence', 'num_z_planes', 'z_step', 'centered_focal_plane']
                config_dict = {key: self.config_dict[key] for key in keys_to_extract}
            elif experiment == 'Multicolor scan RAMM':
                filename = 'multicolor_scan_task_RAMM.yaml'
                keys_to_extract = ['sample_name', 'exposure', 'save_path', 'file_format', 'imaging_sequence', 'num_z_planes', 'z_step', 'centered_focal_plane']
                config_dict = {key: self.config_dict[key] for key in keys_to_extract}
            elif experiment == 'ROI multicolor scan':
                filename = 'ROI_multicolor_scan_task_RAMM.yaml'
                keys_to_extract = ['sample_name', 'exposure', 'save_path', 'file_format', 'imaging_sequence', 'num_z_planes', 'z_step', 'roi_list_path', 'centered_focal_plane']
                config_dict = {key: self.config_dict[key] for key in keys_to_extract}
            elif experiment == 'Fluidics':
                filename = 'fluidics_task_RAMM.yaml'
                keys_to_extract = ['sample_name', 'injections_path']
                config_dict = {key: self.config_dict[key] for key in keys_to_extract}
            elif experiment == 'Hi-M':
                filename = 'hi_m_task_RAMM.yaml'
                keys_to_extract = ['sample_name', 'exposure', 'save_path', 'file_format', 'imaging_sequence', 'num_z_planes', 'z_step', 'centered_focal_plane', 'roi_list_path', 'injections_path']
                config_dict = {key: self.config_dict[key] for key in keys_to_extract}
            elif experiment == 'Photobleaching':
                filename = 'photobleaching_task_RAMM.yaml'
                keys_to_extract = ['sample_name', 'imaging_sequence', 'roi_list_path', 'illumination_time']
                config_dict = {key: self.config_dict[key] for key in keys_to_extract}
            else:
                pass
        except KeyError as e:
            self.log.warning(f'Experiment configuration not saved. Missing information {e}.')

        config_dict['experiment'] = experiment
        complete_path = os.path.join(path, filename)
        with open(complete_path, 'w') as file:
            yaml.safe_dump(config_dict, file, default_flow_style=False)  # yaml file. can use suffix .txt.
        self.log.info('Saved experiment configuration to {}'.format(complete_path))

    def load_config_file(self, path):
        """ Loads a configuration file and sets the entries of the config_dict accordingly

        @param: str path: complete path to an experiment configuration file """
        with open(path, 'r') as stream:
            data_dict = yaml.safe_load(stream)

        self.config_dict = data_dict

        if 'imaging_sequence' in self.config_dict.keys():
            # synchronize the listviewmodel with the config_dict['imaging_sequence'] entry
            self.img_sequence_model.items = self.config_dict['imaging_sequence']

        self.sigConfigLoaded.emit()

    def init_default_config_dict(self):
        """ Initialize the entries of the dictionary with some default values,
        to set entries to the form displayed on the GUI on startup.
        """
        self.config_dict = {}
        self.config_dict['exposure'] = 0.0
        self.config_dict['gain'] = 0
        self.config_dict['num_frames'] = 1
        self.config_dict['filter_pos'] = 1
        self.img_sequence_model.items = []
        self.config_dict['save_path'] = self.default_path
        self.config_dict['file_format'] = 'tiff'
        self.config_dict['centered_focal_plane'] = False
        self.sigConfigDictUpdated.emit()

    # methods for updating dict entries on change of associated element on GUI
    @QtCore.Slot(str)
    def update_sample_name(self, name):
        """ Updates the dictionary entry 'sample_name' """
        self.config_dict['sample_name'] = name
        self.sigConfigDictUpdated.emit()

    @QtCore.Slot(float)
    def update_exposure(self, value):
        """ Updates the dictionary entry 'exposure'"""
        self.config_dict['exposure'] = value
        # update the gui in case this method was called from the ipython console
        self.sigConfigDictUpdated.emit()

    @QtCore.Slot(int)
    def update_gain(self, value):
        """ Updates the dictionary entry 'gain'. """
        self.config_dict['gain'] = value
        self.sigConfigDictUpdated.emit()

    @QtCore.Slot(int)
    def update_frames(self, value):
        """ Updates the dictionary entry 'num_frames' (number of frames per channel). """
        self.config_dict['num_frames'] = value
        self.sigConfigDictUpdated.emit()

    @QtCore.Slot(int)
    def update_filterpos(self, index):
        """ Updates the dictionary entry 'filter_pos'"""
        self.config_dict['filter_pos'] = index + 1  # zero indexing !
        self.sigConfigDictUpdated.emit()

    @QtCore.Slot(str)
    def update_save_path(self, path):
        """ Updates the dictionary entry 'save_path' (path where image data is saved to). """
        self.config_dict['save_path'] = path
        self.sigConfigDictUpdated.emit()

    @QtCore.Slot(str)
    def update_fileformat(self, entry):
        self.config_dict['file_format'] = entry
        self.sigConfigDictUpdated.emit()

    @QtCore.Slot(int)
    def update_num_z_planes(self, value):
        """ Updates the dictionary entry 'num_z_planes' (number of planes in a z stack for scan experiments). """
        self.config_dict['num_z_planes'] = value
        self.sigConfigDictUpdated.emit()

    @QtCore.Slot(float)
    def update_z_step(self, value):
        """ Updates the dictionary entry 'z_step' (step between two planes in a z stack). """
        self.config_dict['z_step'] = value
        self.sigConfigDictUpdated.emit()

    @QtCore.Slot(int)
    def update_centered_focal_plane(self, state):
        """ Updates the dictionary entry 'centered_focal_plane' (z stack starting at bottom plane if False, or taking current plane as center plane if True). """
        if state == 2:  # Enum Qt::CheckState Checked = 2
            self.config_dict['centered_focal_plane'] = True
        elif state == 0:  # Unchecked = 0
            self.config_dict['centered_focal_plane'] = False
        self.sigConfigDictUpdated.emit()

    @QtCore.Slot(str)
    def update_roi_path(self, path):
        """ Updates the dictionary entry 'roi_list_path' (path to the roi list). """
        self.config_dict['roi_list_path'] = path
        self.sigConfigDictUpdated.emit()

    @QtCore.Slot(str)
    def update_injections_path(self, path):
        """ Updates the dictionary entry 'injections_path' (path to the injections list). """
        self.config_dict['injections_path'] = path
        self.sigConfigDictUpdated.emit()

    @QtCore.Slot(float)
    def update_illumination_time(self, value):
        """ Updates the dictionary entry 'illumination_time' (laser-on time for photobleaching). """
        self.config_dict['illumination_time'] = value
        self.sigConfigDictUpdated.emit()

    @QtCore.Slot(str, int)
    def add_entry_to_imaging_list(self, lightsource, intensity):
        # Access the list via the model.
        self.img_sequence_model.items.append((lightsource, intensity))
        # update the dictionary entry with the current content of the model
        self.config_dict['imaging_sequence'] = self.img_sequence_model.items
        # self.log.info(self.img_sequence_model.items[-1])  # just for tests
        # Trigger refresh of the listview on the GUI:
        # signal layoutChanged cannot be queued over different threads. use custom signal
        self.sigImagingListChanged.emit()

    @QtCore.Slot(QtCore.QModelIndex)
    def delete_entry_from_imaging_list(self, index):
        # Remove the item and refresh.
        del self.img_sequence_model.items[index.row()]
        # self.log.info(self.img_sequence_model.items)
        # update the dictionary entry with the current content of the model
        self.config_dict['imaging_sequence'] = self.img_sequence_model.items
        # Trigger refresh of the livtview on the GUI
        self.sigImagingListChanged.emit()

    @QtCore.Slot()
    def delete_imaging_list(self):
        self.img_sequence_model.items = []
        self.sigImagingListChanged.emit()

    # retrieving current values from devices
    def get_exposure(self):
        exposure = self._camera_logic.get_exposure()
        self.config_dict['exposure'] = exposure
        self.sigConfigDictUpdated.emit()

    def get_gain(self):
        gain = self._camera_logic.get_gain()
        self.config_dict['gain'] = gain
        self.sigConfigDictUpdated.emit()

    def get_filterpos(self):
        filterpos = self._filterwheel_logic.get_position()
        self.config_dict['filter_pos'] = filterpos
        self.sigConfigDictUpdated.emit()



