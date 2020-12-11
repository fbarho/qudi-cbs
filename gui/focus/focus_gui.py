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
        ui_file = os.path.join(this_dir, 'ui_focustest.ui')

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


        # connect signals
        # internal signals
        self._mw.step_doubleSpinBox.valueChanged.connect(self.step_changed)

        # signals to logic
        self.sigUpdateStep.connect(self._focus_logic.set_step)
        self._mw.move_up_PushButton.clicked.connect(self._focus_logic.move_up)
        self._mw.move_down_PushButton.clicked.connect(self._focus_logic.move_down)

        # keyboard shortcuts for up / down buttons
        self._mw.move_up_PushButton.setShortcut(QtCore.Qt.Key_Up)
        self._mw.move_down_PushButton.setShortcut(QtCore.Qt.Key_Down)

        # signals from logic
        self._focus_logic.sigStepChanged.connect(self.update_step)
        self._focus_logic.sigPositionChanged.connect(self.update_position)

    def on_deactivate(self):
        self.sigUpdateStep.disconnect()
        self._mw.move_up_PushButton.clicked.disconnect()
        self._mw.move_down_PushButton.clicked.disconnect()
        self._focus_logic.sigStepChanged.disconnect()
        self._focus_logic.sigPositionChanged.disconnect()


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

