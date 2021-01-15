# -*- coding: utf-8 -*-
"""
This module contains a test GUI for controlling a piezo which allows to set the focus

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


class FocusWindow(QtWidgets.QMainWindow):
    """ Class defined for the main window (not the module)

    """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_focus.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()


class FocusGUI(GUIBase):
    """ Tools to position the piezo to set the focus
    """

    # Define connectors to logic modules
    focus_logic = Connector(interface='FocusLogic')

    # Signals
    sigUpdateStep = QtCore.Signal(float)
    sigMoveUp = QtCore.Signal(float)
    sigMoveDown = QtCore.Signal(float)
    sigInitPiezo = QtCore.Signal()


    _mw = None

    def __init__(self, config, **kwargs):

        # load connection
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initializes all needed UI files and establishes the connectors.
        """

        self._focus_logic = self.focus_logic()

        # Windows
        self._mw = FocusWindow()

        self._mw.piezo_init_Action.setChecked(False)
        # connect signals
        # internal signals
        self._mw.close_MenuAction.triggered.connect(self._mw.close)
        self._mw.step_doubleSpinBox.valueChanged.connect(self.step_changed)
        self._mw.move_up_PushButton.clicked.connect(self.move_up_button_clicked)
        self._mw.move_down_PushButton.clicked.connect(self.move_down_button_clicked)
        self._mw.piezo_init_Action.triggered.connect(self.piezo_init_clicked)

        # signals to logic
        self.sigUpdateStep.connect(self._focus_logic.set_step)
        self.sigMoveUp.connect(self._focus_logic.move_up)
        self.sigMoveDown.connect(self._focus_logic.move_down)
        self.sigInitPiezo.connect(self._focus_logic.init_piezo)

        # keyboard shortcuts for up / down buttons
        self._mw.move_up_PushButton.setShortcut(QtCore.Qt.Key_Up)
        self._mw.move_down_PushButton.setShortcut(QtCore.Qt.Key_Down)

        # signals from logic
        self._focus_logic.sigStepChanged.connect(self.update_step)
        self._focus_logic.sigPositionChanged.connect(self.update_position)
        self._focus_logic.sigPiezoInitFinished.connect(self.piezo_init_finished)

    def on_deactivate(self):
        self.sigUpdateStep.disconnect()
        self._mw.move_up_PushButton.clicked.disconnect()
        self._mw.move_down_PushButton.clicked.disconnect()
        self._focus_logic.sigStepChanged.disconnect()
        self._focus_logic.sigPositionChanged.disconnect()
        self._mw.close()


    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def step_changed(self, step):
        step = self._mw.step_doubleSpinBox.value()
        self.sigUpdateStep.emit(step)

    def update_step(self, step):
        self._mw.step_doubleSpinBox.setValue(step)

    def update_position(self, position):
        self._mw.position_Label.setText('z position (um): {:.3f}'.format(position))

    def move_up_button_clicked(self):
        # the function move_up in the logic module needs to receive the step as parameter
        # for this reason, we use this function move_up_button_clicked to send the signal with the step as parameter.
        # this signal is then in turn connected to the function in the logic module
        step = self._mw.step_doubleSpinBox.value()
        self.sigMoveUp.emit(step)

    def move_down_button_clicked(self):
        step = self._mw.step_doubleSpinBox.value()
        self.sigMoveDown.emit(step)

    def piezo_init_clicked(self):
        self._mw.piezo_init_Action.setEnabled(False)
        self._mw.piezo_init_Action.setText('Initialization running..')
        self._mw.piezo_init_Action.setChecked(True)
        self.sigInitPiezo.emit()

    def piezo_init_finished(self):
        self._mw.piezo_init_Action.setText('Reinitialize')
        self._mw.piezo_init_Action.setEnabled(True)
        self._mw.piezo_init_Action.setChecked(False)

