#!/usr/bin/env python3
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


class ExpConfigLogic(GenericLogic):
    """
    Class containing the logic for the setup of a configuration file for an experiment

    Example config for copy-paste:

    exp_config_logic:
        module.Class: 'experiment_configurator_logic.ExpConfigLogic'
        experiments:
            - 'Multichannel imaging'
            - 'Dummy experiment'

    """

    # signals
    sigConfigDictUpdated = QtCore.Signal()
    sigImagingListChanged = QtCore.Signal()

    # attributes
    experiments = ConfigOption('experiments')
    imaging_data = ['first entry', 'second entry']

    config_dict = {}
    imaging_data = []

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self.imaging_listviewmodel = QtCore.QStringListModel(self.imaging_data)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self.experiments.insert(0, 'Select your experiment..')
        self.init_default_config_dict()


    def on_deactivate(self):
        """ Perform required deactivation. """
        pass

    def save_to_exp_config_file(self, path, filename):
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
        with open(path, 'r') as stream:
            data_dict = yaml.safe_load(stream)

        for key in self.config_dict:
            if key in data_dict:
                self.config_dict[key] = data_dict[key]
        self.sigConfigDictUpdated.emit()

    def init_default_config_dict(self):
        self.config_dict['exposure'] = 0.05
        self.config_dict['gain'] = 0
        self.config_dict['num_frames'] = 1
        self.config_dict['filter_pos'] = 1
        self.config_dict['imaging_sequence'] = []
        self.config_dict['save_path'] = '/home/barho'
        self.sigConfigDictUpdated.emit()


    # methods for updating dict entries on change of associated element on GUI
    @QtCore.Slot(float)
    def update_exposure(self, value):
        self.config_dict['exposure'] = value

    @QtCore.Slot(int)
    def update_gain(self, value):
        self.config_dict['gain'] = value

    @QtCore.Slot(int)
    def update_frames(self, value):
        self.config_dict['num_frames'] = value

    @QtCore.Slot(str)
    def update_save_path(self, path):
        self.config_dict['save_path'] = path

    @QtCore.Slot(int)
    def update_filterpos(self, index):
        self.config_dict['filter_pos'] = index + 1  # zero indexing ! 

    @QtCore.Slot(str, int)
    def add_entry_to_imaging_list(self, lightsource, intensity):
        entry = f'{lightsource}: {intensity}'
        self.imaging_data.append(entry)
        self.config_dict['imaging_sequence'] = self.imaging_data
        # self.imaging_listviewmodel.insertRows()
        # self.imaging_listviewmodel.layoutChanged.emit()
        # # test if this helps ..
        self.imaging_listviewmodel = QtCore.QStringListModel(self.imaging_data)
        self.sigImagingListChanged.emit()

    @QtCore.Slot(QtCore.QModelIndex)
    def delete_entry_from_imaging_list(self, index):
        self.imaging_listviewmodel.removeRows(0, 1, index)
        self.sigImagingListChanged.emit()




## rework the part with the listviewmodel and why it does not work with layoutChanged.
# it seems not the good way to have to reassign the model all over again. adapt also the part in the gui module
# delete entry does not work at all ..
