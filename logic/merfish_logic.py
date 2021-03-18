# -*- coding: utf-8 -*-
"""
Created on Tue Mars 2 2021

@author: fbarho

This module contains the logic to configure a merfish injection sequence
"""
import os
import yaml
from qtpy import QtCore
from logic.generic_logic import GenericLogic
from core.configoption import ConfigOption


class BufferListModel(QtCore.QAbstractListModel):
    """ This class contains the model class for the listview with the buffer names and the associated valve
    consisting of entries of the form (buffername, valve number)
    """

    def __init__(self, *args, items=None, **kwargs):
        super(BufferListModel, self).__init__(*args, **kwargs)
        self.items = items or []

    def data(self, index, role):
        if role == QtCore.Qt.DisplayRole:
            buffername, valve_number = self.items[index.row()]
            return f'{buffername}: Valve {valve_number}'

    def rowCount(self, index):
        return len(self.items)


class ProbePositionModel(QtCore.QAbstractListModel):
    """ This class contains the model class for the listview with the probe names and the associated positions
    consisting of entries of the form (probe name, position number)
    """

    def __init__(self, *args, items=None, **kwargs):
        super(ProbePositionModel, self).__init__(*args, **kwargs)
        self.items = items or []

    def data(self, index, role):
        if role == QtCore.Qt.DisplayRole:
            probename, position_number = self.items[index.row()]
            return f'{probename}: Position {position_number}'

    def rowCount(self, index):
        return len(self.items)


class InjectionSequenceModel(QtCore.QAbstractListModel):
    """ This class contains the model class for the listview with the injection parameters
    consisting of entries of the form (num_entry, procedure, product, volume, flowrate, time)
    """

    def __init__(self, *args, items=None, **kwargs):
        super(InjectionSequenceModel, self).__init__(*args, **kwargs)
        self.items = items or []
        self.step_list = []

    def data(self, index, role):
        if role == QtCore.Qt.DisplayRole:
            procedure, product, volume, flowrate, time = self.items[index.row()]
            step_num = self.items.index(self.items[index.row()]) + 1  # first occurence of index (self.items.index): method index of list.
            # this is to get the number which the element is in the list
            # if there are two identic entries only the first will be found .. this is a problem
            if product is None:  # then it is an incubation step
                return f'{step_num}: Incubation time: {time} s'
            else:  # injection step
                return f'{step_num}: {product}, {volume} ul, {flowrate} ul/min'

    def rowCount(self, index):
        return len(self.items)


class MerfishLogic(GenericLogic):
    """
    Class containing the logic to configure and save a merfish injection sequence

    Example config for copy-paste:

    merfish_logic:
        module.Class: 'merfish_logic.MerfishLogic'
        default path: '/home/barho'
    """

    # signals
    sigBufferListChanged = QtCore.Signal()
    sigProbeListChanged = QtCore.Signal()
    sigHybridizationListChanged = QtCore.Signal()
    sigPhotobleachingListChanged = QtCore.Signal()

    # attributes
    procedures = ['Hybridization', 'Photobleaching']
    products = ['Merfish Probe']

    buffer_dict = {}  # key: value = valve_number: buffer_name (to make sure that each valve is only used once, although it would be good to be able to address the valve number via the buffer name, but we will handle this differently
    probe_dict = {}  # key: value = position_number: probe_name (same comment)
    hybridization_list = []  # list of dictionaries with the parameters for each injection step
    photobleaching_list = []  # list of dictionaries with the parameters for each injection step

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self.buffer_list_model = BufferListModel()
        self.probe_position_model = ProbePositionModel()
        self.hybridization_injection_sequence_model = InjectionSequenceModel()
        self.photobleaching_injection_sequence_model = InjectionSequenceModel()

    def on_deactivate(self):
        """ Perform required deactivation. """
        pass

    def add_buffer(self, buffername, valve_number):
        self.buffer_dict[valve_number] = buffername
        # synchronize buffer_dict and list_model, this approach also ensures that each valve number is only set once
        self.buffer_list_model.items = [(self.buffer_dict[key], key) for key in self.buffer_dict]
        self.sigBufferListChanged.emit()

    def delete_buffer(self, index):
        key = self.buffer_list_model.items[index.row()][1]  # the valve number
        del self.buffer_dict[key]
        del self.buffer_list_model.items[index.row()]
        self.sigBufferListChanged.emit()

    def add_probe(self, probename, probe_position):
        self.probe_dict[probe_position] = probename
        # synchronize buffer_dict and list_model, this approach also ensures that each valve number is only set once
        self.probe_position_model.items = [(self.probe_dict[key], key) for key in self.probe_dict]
        self.sigProbeListChanged.emit()

    def delete_probe(self, index):
        key = self.probe_position_model.items[index.row()][1]   # the probe position number
        # delete the entry both in the dictionary and in the list model
        del self.probe_dict[key]
        del self.probe_position_model.items[index.row()]
        self.sigProbeListChanged.emit()

    @QtCore.Slot(str, str, float, float)
    def add_injection_step(self, procedure, product, volume, flowrate):
        if procedure == 'Hybridization':
            step_num = len(self.hybridization_injection_sequence_model.items) + 1  # to modify
            # handle the entry in the hybridization list and also in the model
            entry = self.make_dict_entry(step_num, procedure, product, volume, flowrate)
            self.hybridization_list.append(entry)

            self.hybridization_injection_sequence_model.items.append((procedure, product, volume, flowrate, None))
            self.sigHybridizationListChanged.emit()
        elif procedure == 'Photobleaching':
            step_num = len(self.photobleaching_injection_sequence_model.items) + 1  # to modify
            # handle the entry in the hybridization list and also in the model
            entry = self.make_dict_entry(step_num, procedure, product, volume, flowrate)
            self.photobleaching_list.append(entry)

            self.photobleaching_injection_sequence_model.items.append((procedure, product, volume, flowrate, None))
            self.sigPhotobleachingListChanged.emit()
        else:
            pass

    def make_dict_entry(self, step_num, procedure, product, volume, flowrate, time=None):
        """ Helper function .. """
        inj_step_dict = {}
        inj_step_dict['step_number'] = step_num
        inj_step_dict['procedure'] = procedure
        inj_step_dict['product'] = product
        inj_step_dict['volume'] = volume
        inj_step_dict['flowrate'] = flowrate
        inj_step_dict['time'] = time
        return inj_step_dict



    @QtCore.Slot(str, int)
    def add_incubation_step(self, procedure, time):
        if procedure == 'Hybridization':
            step_num = len(self.hybridization_injection_sequence_model.items) + 1  # to modify
            # handle the entry in the hybridization list and also in the model
            entry = self.make_dict_entry(step_num, procedure, None, None, None, time)
            self.hybridization_list.append(entry)

            self.hybridization_injection_sequence_model.items.append((procedure, None, None, None, time))
            self.log.info(self.hybridization_injection_sequence_model.items)
            self.sigHybridizationListChanged.emit()
        elif procedure == 'Photobleaching':
            step_num = len(self.photobleaching_injection_sequence_model.items) + 1  # to modify
            # handle the entry in the photobleaching list and also in the model
            entry = self.make_dict_entry(step_num, procedure, None, None, None, time)
            self.photobleaching_list.append(entry)

            self.photobleaching_injection_sequence_model.items.append((procedure, None, None, None, time))
            self.log.info(self.photobleaching_injection_sequence_model.items)
            self.sigPhotobleachingListChanged.emit()
        else:
            pass

    @QtCore.Slot(QtCore.QModelIndex)
    def delete_hybr_step(self, index):
        del self.hybridization_injection_sequence_model.items[index.row()]
        del self.hybridization_list[index.row()]
        self.sigHybridizationListChanged.emit()
        # handle the modification of step_num entry

    @QtCore.Slot(QtCore.QModelIndex)
    def delete_photobl_step(self, index):
        del self.photobleaching_injection_sequence_model.items[index.row()]
        del self.photobleaching_list[index.row()]
        self.sigPhotobleachingListChanged.emit()
        # handle the modification of step_num entry

    def delete_hybr_all(self):
        self.hybridization_injection_sequence_model.items = []
        self.hybridization_list = []
        self.sigHybridizationListChanged.emit()

    def delete_photobl_all(self):
        self.photobleaching_injection_sequence_model.items = []
        self.photobleachin_list = []
        self.sigPhotobleachingListChanged.emit()

    def load_injections(self, path):
        try:
            with open(path, 'r') as stream:
                documents = yaml.full_load(stream)
                self.buffer_dict = documents['buffer']
                self.probe_dict = documents['probes']
                self.hybridization_list = documents['hybridization list']
                self.photobleaching_list = documents['photobleaching list']

                # update the models based on the dictionaries / lists content
                self.buffer_list_model.items = [(self.buffer_dict[key], key) for key in self.buffer_dict]
                self.probe_position_model.items = [(self.probe_dict[key], key) for key in self.probe_dict]

                for i in range(len(self.hybridization_list)):
                    entry = self.hybridization_list[i]  # entry is a dict
                    self.log.info(entry)
                    self.hybridization_injection_sequence_model.items.append((entry['procedure'], entry['product'], entry['volume'], entry['flowrate'], entry['time']))

                for i in range(len(self.photobleaching_list)):
                    entry = self.photobleaching_list[i]  # entry is a dict
                    self.log.info(entry)
                    self.photobleaching_injection_sequence_model.items.append((entry['procedure'], entry['product'], entry['volume'], entry['flowrate'], entry['time']))

                self.sigBufferListChanged.emit()
                self.sigProbeListChanged.emit()
                self.sigHybridizationListChanged.emit()
                self.sigPhotobleachingListChanged.emit()

        except KeyError:
            self.log.warning('Injections not loaded. Document is incomplete.')

    def save_injections(self, path):
        with open(path, 'w') as file:
            dict_file = {'buffer': self.buffer_dict, 'probes': self.probe_dict, 'hybridization list': self.hybridization_list, 'photobleaching list': self.photobleaching_list}
            yaml.safe_dump(dict_file, file, default_flow_style=False, sort_keys=False)
            self.log.info('Injections saved to {}'.format(path))

# maybe it would be easier to just work with the hybridization / photobleaching list models and not to use
# the separate lists of dictionaries which are however nicer for user readability
# if we just use the tuples as entries, this is also possible but one needs to know which value corresponds to which parameter

# handle the step num value when deleting
