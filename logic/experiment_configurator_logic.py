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
            - 'Dummy experiment'
        supported fileformats:
            - 'tiff'
            - 'fits'
        default path: '/home/barho'

    """

    # signals
    sigConfigDictUpdated = QtCore.Signal()
    sigImagingListChanged = QtCore.Signal()

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
        self.img_sequence_model = ImagingSequenceModel()
        # add an additional entry to the experiment selector combobox with placeholder text
        self.experiments.insert(0, 'Select your experiment..')
        self.init_default_config_dict()

    def on_deactivate(self):
        """ Perform required deactivation. """
        pass

    def save_to_exp_config_file(self, path, filename):
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
                
        complete_path = os.path.join(path, filename)
        with open(complete_path, 'w') as file:
            yaml.safe_dump(self.config_dict, file, default_flow_style=False)  # yaml file. can use suffix .txt. change if .yaml preferred.
        self.log.info('Saved experiment configuration to {}'.format(complete_path))

    def load_config_file(self, path):
        """ Loads a configuration file and sets the entries of the config_dict accordingly

        @param: str path: complete path to an experiment configuration file """
        with open(path, 'r') as stream:
            data_dict = yaml.safe_load(stream)

        for key in self.config_dict:
            if key in data_dict:
                self.config_dict[key] = data_dict[key]
            else:
                self.config_dict[key] = None  # should the config_dict always contain all entries, even those that are non applicable for the experiment in question ?
        self.sigConfigDictUpdated.emit()

    def init_default_config_dict(self):
        """ Initialize the entries of the dictionary with some default values,
        to set entries to the form displayed on the GUI on startup.
        """
        self.config_dict['exposure'] = 0.05
        self.config_dict['gain'] = 0
        self.config_dict['num_frames'] = 1
        self.config_dict['filter_pos'] = 1
        self.config_dict['imaging_sequence'] = []
        self.config_dict['save_path'] = self.default_path
        self.sigConfigDictUpdated.emit()

    # methods for updating dict entries on change of associated element on GUI
    @QtCore.Slot(float)
    def update_exposure(self, value):
        """ Updates the dictionary entry 'exposure'"""
        self.config_dict['exposure'] = value

    @QtCore.Slot(int)
    def update_gain(self, value):
        """ Updates the dictionary entry 'gain'"""
        self.config_dict['gain'] = value

    @QtCore.Slot(int)
    def update_frames(self, value):
        """ Updates the dictionary entry 'num_frames' (number of frames per channel)"""
        self.config_dict['num_frames'] = value

    @QtCore.Slot(str)
    def update_save_path(self, path):
        """ Updates the dictionary entry 'save_path' (path where image data is saved to)"""
        self.config_dict['save_path'] = path

    @QtCore.Slot(int)
    def update_filterpos(self, index):
        """ Updates the dictionary entry 'filter_pos'"""
        self.config_dict['filter_pos'] = index + 1  # zero indexing !

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


