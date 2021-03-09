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
        connect:
            exp_config_logic: 'exp_config_logic'
    """

    # connector to logic module
    exp_logic = Connector(interface='ExpConfigLogic')

    # Signals
    sigSaveConfig = QtCore.Signal(str, str)
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

        # initialize the entry form
        self.init_configuration_form()

        # initialize list view
        self._mw.imaging_sequence_ListView.setModel(self._exp_logic.img_sequence_model)

        # signals
        # internal signals
        # toolbar
        self._mw.save_config_Action.triggered.connect(self.save_config_clicked)
        self._mw.load_config_Action.triggered.connect(self.load_config_clicked)

        # widgets on the configuration form
        self._mw.select_experiment_ComboBox.currentIndexChanged.connect(self.set_form_visible)
        self._mw.exposure_DSpinBox.valueChanged.connect(self._exp_logic.update_exposure)
        self._mw.gain_SpinBox.valueChanged.connect(self._exp_logic.update_gain)
        self._mw.frames_SpinBox.valueChanged.connect(self._exp_logic.update_frames)
        self._mw.filterpos_ComboBox.currentIndexChanged.connect(self._exp_logic.update_filterpos)
        self._mw.save_path_LineEdit.textChanged.connect(self._exp_logic.update_save_path)

        # pushbuttons
        self._mw.add_entry_PushButton.clicked.connect(self.add_entry_clicked)
        self._mw.delete_entry_PushButton.clicked.connect(self.delete_entry_clicked)
        # get-current-value pushbutton signals
        self._mw.get_exposure_PushButton.clicked.connect(self._exp_logic.get_exposure)
        self._mw.get_gain_PushButton.clicked.connect(self._exp_logic.get_gain)
        self._mw.get_filterpos_PushButton.clicked.connect(self._exp_logic.get_filterpos)

        # signals to logic
        self.sigSaveConfig.connect(self._exp_logic.save_to_exp_config_file)
        self.sigLoadConfig.connect(self._exp_logic.load_config_file)
        self.sigAddEntry.connect(self._exp_logic.add_entry_to_imaging_list)
        self.sigDeleteEntry.connect(self._exp_logic.delete_entry_from_imaging_list)

        # signals from logic
        self._exp_logic.sigConfigDictUpdated.connect(self.update_entries)
        self._exp_logic.sigImagingListChanged.connect(self.update_listview)

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

    # slots
    def set_form_visible(self, index):
        if index == 0:
            self._mw.formWidget.hide()
        else:
            self._mw.formWidget.setVisible(True)

            # could also add specific adaptations depending on the experiment type here

    def save_config_clicked(self):
        path = '/home/barho/qudi-cbs-experiment-config'  # 'C:/Users/admin/qudi-cbs-user-configs'  # later: from config according to used computer
        filename = 'testconfigfile.txt'  # adapt filename as a function of experiment type chosen in combobox
        self.sigSaveConfig.emit(path, filename)

    def load_config_clicked(self):
        data_directory = '/home/barho/qudi-cbs-experiment-config'  # 'C:\\Users\\admin\\qudi-cb-user-configs'  # we will use this as default location to look for files
        this_file = QtWidgets.QFileDialog.getOpenFileName(self._mw,
                                                          'Open experiment configuration',
                                                          data_directory,
                                                          'txt files (*.txt)')[0]
        if this_file:
            self._mw.formWidget.setVisible(True)
            self.sigLoadConfig.emit(this_file)

    def update_entries(self):
        self._mw.exposure_DSpinBox.setValue(self._exp_logic.config_dict['exposure'])
        self._mw.gain_SpinBox.setValue(self._exp_logic.config_dict['gain'])
        self._mw.frames_SpinBox.setValue(self._exp_logic.config_dict['num_frames'])
        self._mw.filterpos_ComboBox.setCurrentIndex(self._exp_logic.config_dict['filter_pos'] - 1)  # zero indexing
        self._mw.save_path_LineEdit.setText(self._exp_logic.config_dict['save_path'])
        self._exp_logic.img_sequence_model.layoutChanged.emit()

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

