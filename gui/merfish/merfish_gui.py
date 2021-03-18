# -*- coding: utf-8 -*-
"""
This module contains a GUI that allows to create a merFISH injection sequence
"""
import os
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy import uic

from gui.guibase import GUIBase
from core.connector import Connector

class MerfishWindow(QtWidgets.QMainWindow):
    """ Class defined for the main window (not the module)
    """
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_merfish.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)

        self.show()


class MerfishGUI(GUIBase):
    """ Main window that allows to create a merFISH injection sequence, save it to a file, or load it from file.
    An injection sequence can also be run directly (for tests)

    Example config for copy-paste:

    merfish_gui:
        module.Class: 'merfish.merfish_gui.MerfishGUI'
        connect:
            merfish_logic: 'merfish_logic'
    """

    # connector to logic module
    merfish_logic = Connector(interface='MerfishLogic')

    # Signals
    sigAddBuffer = QtCore.Signal(str, int)
    sigDeleteBuffer = QtCore.Signal(QtCore.QModelIndex)
    sigAddProbe = QtCore.Signal(str, int)
    sigDeleteProbe = QtCore.Signal(QtCore.QModelIndex)
    sigAddInjectionStep = QtCore.Signal(str, str, float, float)
    sigAddIncubationTime = QtCore.Signal(str, int)
    sigDeleteHybrStep = QtCore.Signal(QtCore.QModelIndex)
    sigDeletePhotoblStep = QtCore.Signal(QtCore.QModelIndex)

    sigLoadInjections = QtCore.Signal(str)
    sigSaveInjections = QtCore.Signal(str)



    def __init__(self, config, **kwargs):
        # load connection
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Required initialization steps.
        """
        self._merfish_logic = self.merfish_logic()

        self._mw = MerfishWindow()
        self._mw.centralwidget.hide()  # everything is in dockwidgets

        # initialize list views
        self._mw.buffer_ListView.setModel(self._merfish_logic.buffer_list_model)
        self._mw.probe_ListView.setModel(self._merfish_logic.probe_position_model)
        self._mw.hybridization_ListView.setModel(self._merfish_logic.hybridization_injection_sequence_model)
        self._mw.photobleaching_ListView.setModel(self._merfish_logic.photobleaching_injection_sequence_model)
        self._mw.product_ComboBox.setModel(self._merfish_logic.buffer_list_model) # not sure if it is possible to also display the merfish probe if not defined in the buffer list

        # initialize comboboxes
        self._mw.valve_position_ComboBox.addItems([str(i) for i in range(1, 9)])  # to be read from config later
        self._mw.probe_position_ComboBox.addItems([str(i) for i in range(1, 101)])  # to be read from config later
        self._mw.procedure_ComboBox.addItems(self._merfish_logic.procedures)

        # signals
        # internal signals
        # menubar
        self._mw.close_Action.triggered.connect(self._mw.close)

        # toolbar
        self._mw.load_Action.triggered.connect(self.load_injections_clicked)
        self._mw.save_Action.triggered.connect(self.save_injections_clicked)

        # pushbuttons
        self._mw.add_buffer_PushButton.clicked.connect(self.add_buffer_clicked)
        self._mw.delete_buffer_PushButton.clicked.connect(self.delete_buffer_clicked)

        self._mw.add_probe_PushButton.clicked.connect(self.add_probe_clicked)
        self._mw.delete_probe_PushButton.clicked.connect(self.delete_probe_clicked)

        self._mw.add_injection_PushButton.clicked.connect(self.add_injection_step_clicked)
        self._mw.add_time_PushButton.clicked.connect(self.add_incubation_time_clicked)

        self._mw.delete_hybridization_PushButton.clicked.connect(self.delete_hybr_step_clicked)
        self._mw.delete_photobleaching_PushButton.clicked.connect(self.delete_photobl_step_clicked)

        # signals to logic
        self.sigAddBuffer.connect(self._merfish_logic.add_buffer)
        self.sigDeleteBuffer.connect(self._merfish_logic.delete_buffer)
        self.sigAddProbe.connect(self._merfish_logic.add_probe)
        self.sigDeleteProbe.connect(self._merfish_logic.delete_probe)
        self.sigAddInjectionStep.connect(self._merfish_logic.add_injection_step)
        self.sigAddIncubationTime.connect(self._merfish_logic.add_incubation_step)
        self.sigDeleteHybrStep.connect(self._merfish_logic.delete_hybr_step)
        self._mw.delete_all_hybr_PushButton.clicked.connect(self._merfish_logic.delete_hybr_all)
        self.sigDeletePhotoblStep.connect(self._merfish_logic.delete_photobl_step)
        self._mw.delete_all_photobl_PushButton.clicked.connect(self._merfish_logic.delete_photobl_all)
        self.sigSaveInjections.connect(self._merfish_logic.save_injections)
        self.sigLoadInjections.connect(self._merfish_logic.load_injections)

        # signals from logic
        self._merfish_logic.sigBufferListChanged.connect(self.update_buffer_listview)
        self._merfish_logic.sigProbeListChanged.connect(self.update_probe_listview)
        self._merfish_logic.sigHybridizationListChanged.connect(self.update_hybridization_listview)
        self._merfish_logic.sigPhotobleachingListChanged.connect(self.update_photobleaching_listview)


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

    def add_buffer_clicked(self):
        """ Callback of add buffer pushbutton, inserting an entry into the buffer list """
        buffername = self._mw.buffername_LineEdit.text()
        valve_number = self._mw.valve_position_ComboBox.currentIndex() + 1  # or could use a spinbox instead to work in integer format directly
        if not buffername:
            text = 'Please specify a valid buffer name!'
            QtWidgets.QMessageBox.information(self._mw, 'No buffer name', text, QtWidgets.QMessageBox.Ok)
        else:
            self.sigAddBuffer.emit(buffername, valve_number)

    def delete_buffer_clicked(self):
        """ Callback of delete buffer pushbutton, deleting the currently selected item in the listview.
        (Single select mode) """
        indexes = self._mw.buffer_ListView.selectedIndexes()
        if indexes:
            index = indexes[0]  # single select mode
            self.sigDeleteBuffer.emit(index)

    def add_probe_clicked(self):
        """ Callback of add probe pushbutton, inserting an entry into the buffer list """
        probename = self._mw.probename_LineEdit.text()
        probe_position = self._mw.probe_position_ComboBox.currentIndex() + 1  # or could use a spinbox instead to work in integer format directly
        if not probename:
            text = 'Please specify a valid probe name!'
            QtWidgets.QMessageBox.information(self._mw, 'No probe name', text, QtWidgets.QMessageBox.Ok)
        else:
            self.sigAddProbe.emit(probename, probe_position)

    def delete_probe_clicked(self):
        """ Callback of delete probe pushbutton, deleting the currently selected item in the listview.
        (Single select mode) """
        indexes = self._mw.probe_ListView.selectedIndexes()
        if indexes:
            index = indexes[0]  # single select mode
            self.sigDeleteProbe.emit(index)

    def add_injection_step_clicked(self):
        """ Callback of pushbutton inserting an entry into hybridization or photobleaching sequence """
        procedure = self._mw.procedure_ComboBox.currentText()  # 'Hybridization' or 'Photobleaching'
        product = self._mw.product_ComboBox.currentText()
        volume = self._mw.volume_DSpinBox.value()
        flowrate = self._mw.flowrate_DSpinBox.value()
        self.sigAddInjectionStep.emit(procedure, product, volume, flowrate)

    def add_incubation_time_clicked(self):
        """ Callback of pushbutton inserting an incubation time into hybridization or photobleaching sequence """
        procedure = self._mw.procedure_ComboBox.currentText()  # 'Hybridization' or 'Photobleaching'
        time = self._mw.incubation_time_SpinBox.value()
        self.sigAddIncubationTime.emit(procedure, time)

    def delete_hybr_step_clicked(self):
        """ Callback of pushbutton deleting an entry (single select mode) from the hybridization manager listview """
        indexes = self._mw.hybridization_ListView.selectedIndexes()
        if indexes:
            index = indexes[0]  # single select mode
            self.sigDeleteHybrStep.emit(index)

    def delete_photobl_step_clicked(self):
        """ Callback of pushbutton deleting an entry (single select mode) from the photobleaching manager listview """
        indexes = self._mw.photobleaching_ListView.selectedIndexes()
        if indexes:
            index = indexes[0]  # single select mode
            self.sigDeletePhotoblStep.emit(index)

    def update_buffer_listview(self):
        """ Callback of a signal sent from merfish logic (sigBufferListChanged) notifying that the listview model has
        changed and the listview can now be updated.

        Note that it is not possible to send the layoutChanged (built-in) signal over threads this is why the custom
        signal establishes the communication over threads and the layoutChanged is emitted here. """
        self._merfish_logic.buffer_list_model.layoutAboutToBeChanged.emit()
        self._merfish_logic.buffer_list_model.layoutChanged.emit()
        # for the delete entry case, if one row is selected then it will be deleted
        indexes = self._mw.buffer_ListView.selectedIndexes()
        if indexes:
            self._mw.buffer_ListView.clearSelection()

    def update_probe_listview(self):
        """ Callback of a signal sent from merfish logic (sigProbeListChanged) notifying that the listview model has
        changed and the listview can now be updated.

        Note that it is not possible to send the layoutChanged (built-in) signal over threads this is why the custom
        signal establishes the communication over threads and the layoutChanged is emitted here. """
        self._merfish_logic.probe_position_model.layoutChanged.emit()
        # for the delete entry case, if one row is selected then it will be deleted
        indexes = self._mw.probe_ListView.selectedIndexes()
        if indexes:
            self._mw.probe_ListView.clearSelection()

    def update_hybridization_listview(self):
        """ Callback of a signal sent from merfish logic (sigHybridizationListChanged) notifying that the listview
        model has changed and the listview can now be updated.

        Note that it is not possible to send the layoutChanged (built-in) signal over threads this is why the custom
        signal establishes the communication over threads and the layoutChanged is emitted here. """
        self._merfish_logic.hybridization_injection_sequence_model.layoutChanged.emit()
        # for the delete entry case, if one row is selected then it will be deleted
        indexes = self._mw.hybridization_ListView.selectedIndexes()
        if indexes:
            self._mw.hybridization_ListView.clearSelection()

    def update_photobleaching_listview(self):
        """ Callback of a signal sent from merfish logic (sigPhotobleachingListChanged) notifying that the listview
        model has changed and the listview can now be updated.

        Note that it is not possible to send the layoutChanged (built-in) signal over threads this is why the custom
        signal establishes the communication over threads and the layoutChanged is emitted here. """
        self._merfish_logic.photobleaching_injection_sequence_model.layoutChanged.emit()
        # # for the delete entry case, if one row is selected then it will be deleted
        indexes = self._mw.photobleaching_ListView.selectedIndexes()
        if indexes:
            self._mw.photobleaching_ListView.clearSelection()

    def load_injections_clicked(self):
        data_directory = '/home/barho'  # to be read from config later, default location to look for the file
        this_file = QtWidgets.QFileDialog.getOpenFileName(self._mw, 'Load injections', data_directory, 'txt files (*.txt)')[0]
        if this_file:
            self.sigLoadInjections.emit(this_file)

    def save_injections_clicked(self):
        data_directory = '/home/barho/'  # 'C:\\Users\\admin\\qudi-cb-user-configs'  # we will use this as default location to look for files
        this_file = QtWidgets.QFileDialog.getSaveFileName(self._mw,
                                                          'Save experiment configuration',
                                                          data_directory,
                                                          'txt files (*.txt)')[0]
        if this_file:
            self.sigSaveInjections.emit(this_file)

# delete all buttons for buffer and probe list
# make posiiton combobox move to the next index once the former one is attributed
