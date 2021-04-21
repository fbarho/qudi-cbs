# -*- coding: utf-8 -*-
"""
Created on Tue Mars 2 2021

@author: fbarho

This module contains the logic to configure an injection sequence
"""
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
    consisting of entries of the form (procedure, product, volume, flowrate, time)
    """
    def __init__(self, *args, items=None, **kwargs):
        super(InjectionSequenceModel, self).__init__(*args, **kwargs)
        self.items = items or []

    def data(self, index, role):
        if role == QtCore.Qt.DisplayRole:
            procedure, product, volume, flowrate, time = self.items[index.row()]
            if product is None:  # then it is an incubation step
                return f'{index.row()+1}: Incubation time: {time} s'
            else:  # injection step
                product = str.split(product, ':')[0]  # display only the name of the product and not the valve number
                return f'{index.row()+1}: {product}, {volume} ul, {flowrate} ul/min'

    def rowCount(self, index):
        return len(self.items)


class MerfishLogic(GenericLogic):
    """
    Class containing the logic to configure and save an injection sequence

    Example config for copy-paste:

    merfish_logic:
        module.Class: 'merfish_logic.MerfishLogic'
        merfish_probe_valve_number: 7
        number_of_valve_positions: 8
        number_of_probes: 100
    """
    merfish_valve_number = ConfigOption('merfish_probe_valve_number', missing='warn')
    num_valve_positions = ConfigOption('number_of_valve_positions', missing='warn')
    num_probes = ConfigOption('number_of_probes', missing='warn')

    # signals
    sigBufferListChanged = QtCore.Signal()
    sigProbeListChanged = QtCore.Signal()
    sigHybridizationListChanged = QtCore.Signal()
    sigPhotobleachingListChanged = QtCore.Signal()

    # attributes
    procedures = ['Hybridization', 'Photobleaching']
    products = ['Probe']

    buffer_dict = {}  # key: value = valve_number: buffer_name (to make sure that each valve is only used once, although it would be good to be able to address the valve number via the buffer name, but we will handle this differently
    probe_dict = {}  # key: value = position_number: probe_name (same comment)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self.buffer_list_model = BufferListModel()
        self.probe_position_model = ProbePositionModel()
        self.hybridization_injection_sequence_model = InjectionSequenceModel()
        self.photobleaching_injection_sequence_model = InjectionSequenceModel()

        # add the merfish probe entry as default into the bufferlist
        self.add_buffer('Probe', self.merfish_valve_number)

    def on_deactivate(self):
        """ Perform required deactivation. """
        pass

    def add_buffer(self, buffername, valve_number):
        """ This method adds an entry to the buffer dict and to the buffer list model and informs the GUI that the
        data was changed.
        @:param: str buffername
        @:param: int valve_number
        """
        self.buffer_dict[valve_number] = buffername
        # synchronize buffer_dict and list_model, this approach also ensures that each valve number is only set once
        self.buffer_list_model.items = [(self.buffer_dict[key], key) for key in sorted(self.buffer_dict.keys())]
        self.sigBufferListChanged.emit()

    def delete_buffer(self, index):
        """ This method deletes a single entry from the buffer list model and from the buffer dict. The signal
        informs the GUI that the data was changed.
        @:param: QtCore.QModelIndex index
        """
        key = self.buffer_list_model.items[index.row()][1]  # the valve number
        if key == self.merfish_valve_number:
            pass
        else:
            del self.buffer_dict[key]
            del self.buffer_list_model.items[index.row()]
            self.sigBufferListChanged.emit()

    def delete_all_buffer(self):
        """ This method resets the buffer dict and deletes all items from the buffer list model. The GUI is informed
        that the data has changed.
        """
        self.buffer_dict = {}
        self.buffer_list_model.items = []
        # add the default entry Probe
        self.add_buffer('Probe', self.merfish_valve_number)
        self.sigBufferListChanged.emit()

    def add_probe(self, probename, probe_position):
        """ This method adds an entry to the probe dict and to the probe position model and informs the GUI that the
        data was changed.
        @:param: str probename
        @:param: int probe_position
        """
        self.probe_dict[probe_position] = probename
        # synchronize buffer_dict and list_model, this approach also ensures that each valve number is only set once
        self.probe_position_model.items = [(self.probe_dict[key], key) for key in sorted(self.probe_dict.keys())]
        self.sigProbeListChanged.emit()

    def delete_probe(self, index):
        """ This method deletes a single entry from the probe position model and from the probe dict. The signal
        informs the GUI that the data was changed.
        @:param: QtCore.QModelIndex index
        """
        key = self.probe_position_model.items[index.row()][1]   # the probe position number
        # delete the entry both in the dictionary and in the list model
        del self.probe_dict[key]
        del self.probe_position_model.items[index.row()]
        self.sigProbeListChanged.emit()

    def delete_all_probes(self):
        """ This method resets the probe position dict and deletes all items from the probe position model. The GUI is
        informed that the data has changed.
        """
        self.probe_dict = {}
        self.probe_position_model.items = []
        self.sigProbeListChanged.emit()

    @QtCore.Slot(str, str, int, int)
    def add_injection_step(self, procedure, product, volume, flowrate):
        """ This method adds an entry tho the hybridization or photobleaching sequence model and informs the
        GUI that the underlying data has changed.
        @:param: str procedure: identifier to select to which model the entry should be added
        @:param: str product
        @:param: int volume: amount of product to be injected (in ul)
        @:param: int flowrate: target flowrate in ul/min
        """
        if procedure == 'Hybridization':
            self.hybridization_injection_sequence_model.items.append((procedure, product, volume, flowrate, None))
            self.sigHybridizationListChanged.emit()
        elif procedure == 'Photobleaching':
            self.photobleaching_injection_sequence_model.items.append((procedure, product, volume, flowrate, None))
            self.sigPhotobleachingListChanged.emit()
        else:
            pass

    @QtCore.Slot(str, int)
    def add_incubation_step(self, procedure, time):
        """ This method adds an incubation time entry tho the hybridization or photobleaching sequence model and emits
        a signal to inform the GUI that the underlying data has changed.
        @:param: str procedure: identifier to select to which model the entry should be added
        @:param: int time: incubation time in seconds
        """
        if procedure == 'Hybridization':
            self.hybridization_injection_sequence_model.items.append((procedure, None, None, None, time))
            self.sigHybridizationListChanged.emit()
        elif procedure == 'Photobleaching':
            self.photobleaching_injection_sequence_model.items.append((procedure, None, None, None, time))
            self.sigPhotobleachingListChanged.emit()
        else:
            pass

    @QtCore.Slot(QtCore.QModelIndex)
    def delete_hybr_step(self, index):
        """ This method deletes an entry from the hybridization sequence model and notifies about data modification.
        @:param: QtCore.QModelIndex index: selected entry
        """
        del self.hybridization_injection_sequence_model.items[index.row()]
        self.sigHybridizationListChanged.emit()

    @QtCore.Slot(QtCore.QModelIndex)
    def delete_photobl_step(self, index):
        """ This method deletes an entry from the photobleaching sequence model and notifies about data modification.
        @:param: QtCore.QModelIndex index: selected entry
        """
        del self.photobleaching_injection_sequence_model.items[index.row()]
        self.sigPhotobleachingListChanged.emit()

    def delete_hybr_all(self):
        """ This method deletes all entries from the hybridization sequence model and notifies about data modification.
        """
        self.hybridization_injection_sequence_model.items = []
        self.sigHybridizationListChanged.emit()

    def delete_photobl_all(self):
        """ This method deletes all entries from the photobleaching sequence model and notifies about data modification.
        """
        self.photobleaching_injection_sequence_model.items = []
        self.sigPhotobleachingListChanged.emit()

    def load_injections(self, path):
        """ This method allows to open a file and fills in data to the buffer dict, probe dict and to the models
        if the specified document contains all relevant information. The GUI is notified and updated with the new data.
        @:param: str path: full path to the file
        """
        try:
            with open(path, 'r') as stream:
                documents = yaml.full_load(stream)
                self.buffer_dict = documents['buffer']
                self.probe_dict = documents['probes']
                hybridization_list = documents['hybridization list']
                photobleaching_list = documents['photobleaching list']

                # update the models based on the dictionaries / lists content
                self.buffer_list_model.items = [(self.buffer_dict[key], key) for key in self.buffer_dict]
                self.probe_position_model.items = [(self.probe_dict[key], key) for key in self.probe_dict]

                for i in range(len(hybridization_list)):
                    entry = hybridization_list[i]  # entry is a dict
                    self.hybridization_injection_sequence_model.items.append((entry['procedure'], entry['product'], entry['volume'], entry['flowrate'], entry['time']))

                for i in range(len(photobleaching_list)):
                    entry = photobleaching_list[i]  # entry is a dict
                    self.photobleaching_injection_sequence_model.items.append((entry['procedure'], entry['product'], entry['volume'], entry['flowrate'], entry['time']))

                self.sigBufferListChanged.emit()
                self.sigProbeListChanged.emit()
                self.sigHybridizationListChanged.emit()
                self.sigPhotobleachingListChanged.emit()

        except KeyError:
            self.log.warning('Injections not loaded. Document is incomplete.')

    def save_injections(self, path):
        """ This method allows to write the data from the models and from the buffer dict and probe position dict
        to a file. For readability, hybridization and photobleaching sequence model entries are converted into a
        dictionary format.
        @:param: str path: full path
        """
        # prepare the list entries in dictionary format for good readability in the file
        hybridization_list = []
        photobleaching_list = []

        for entry_num, item in enumerate(self.hybridization_injection_sequence_model.items, 1):
            if item[1] is not None:
                product = str.split(item[1], ':')[0]  # write just the product name, not the corresponding valve pos
            else:
                product = None
            entry = self.make_dict_entry(entry_num, item[0], product, item[2], item[3], item[4])
            hybridization_list.append(entry)

        for entry_num, item in enumerate(self.photobleaching_injection_sequence_model.items, 1):
            if item[1] is not None:
                product = str.split(item[1], ':')[0]
            else:
                product = None
            entry = self.make_dict_entry(entry_num, item[0], product, item[2], item[3], item[4])
            photobleaching_list.append(entry)

        # write a complete file containing buffer_dict, probe_dict, hybridization_list and photobleaching_list
        with open(path, 'w') as file:
            dict_file = {'buffer': self.buffer_dict, 'probes': self.probe_dict, 'hybridization list': hybridization_list, 'photobleaching list': photobleaching_list}
            yaml.safe_dump(dict_file, file, default_flow_style=False)  #, sort_keys=False
            self.log.info('Injections saved to {}'.format(path))

    @staticmethod
    def make_dict_entry(step_num, procedure, product, volume, flowrate, time=None):
        """ Helper function """
        inj_step_dict = {}
        inj_step_dict['step_number'] = step_num
        inj_step_dict['procedure'] = procedure
        inj_step_dict['product'] = product
        inj_step_dict['volume'] = volume
        inj_step_dict['flowrate'] = flowrate
        inj_step_dict['time'] = time
        return inj_step_dict
