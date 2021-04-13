# -*- coding: utf-8 -*-
"""
This module contains a test GUI for controlling a piezo which allows to set the focus

"""
import os
import sys
import numpy as np

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
    sigTimetraceOn = QtCore.Signal()
    sigTimetraceOff = QtCore.Signal()
    sigReadPID = QtCore.Signal()
    sigUpdatePIDgain = QtCore.Signal(float, float)
    sigLaunchCalibration = QtCore.Signal()
    sigLiveOn = QtCore.Signal()
    sigLiveOff = QtCore.Signal()
    sigUpdateThreshold = QtCore.Signal(int)

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

        # actualize the position
        position = self._focus_logic.get_position()
        self._mw.position_Label.setText('z position (um): {:.3f}'.format(position))

        # to modify: data for initialization
        self.y_data = np.zeros(100)
        self._image = None
        self._binary = None

        # create a reference to the line object (this is returned when calling plot method of pg.PlotWidget)
        self._timetrace = self._mw.timetrace_PlotWidget.plot(self.y_data)

        # toolbutton state
        self._mw.piezo_init_Action.setChecked(False)
        self._mw.tracking_Action.setEnabled(True)  # button can be used # just to be sure, this is the initial state defined in designer
        self._mw.tracking_Action.setChecked(self._focus_logic.timetrace_enabled)  # checked state takes the same bool value as enabled attribute in logic (enabled = 0: no timetrace running) # button is defined as checkable in designer

        # connect signals
        # internal signals
        self._mw.close_MenuAction.triggered.connect(self._mw.close)
        self._mw.step_doubleSpinBox.valueChanged.connect(self.step_changed)
        self._mw.move_up_PushButton.clicked.connect(self.move_up_button_clicked)
        self._mw.move_down_PushButton.clicked.connect(self.move_down_button_clicked)
        self._mw.piezo_init_Action.triggered.connect(self.piezo_init_clicked)
        self._mw.tracking_Action.triggered.connect(self.start_tracking_clicked)
        self._mw.Pgain_doubleSpinBox.valueChanged.connect(self.pid_changed)
        self._mw.Igain_doubleSpinBox.valueChanged.connect(self.pid_changed)
        self._mw.calibration_pushButton.clicked.connect(self.calibrate_autofocus)
        self._mw.threshold_spinBox.valueChanged.connect(self.threshold_changed)
        self._mw.live_Action.triggered.connect(self.start_live)

        # signals to logic
        self.sigUpdateStep.connect(self._focus_logic.set_step)
        self.sigMoveUp.connect(self._focus_logic.move_up)
        self.sigMoveDown.connect(self._focus_logic.move_down)
        self.sigInitPiezo.connect(self._focus_logic.init_piezo)
        self.sigTimetraceOn.connect(self._focus_logic.start_tracking)
        self.sigTimetraceOff.connect(self._focus_logic.stop_tracking)
        self.sigReadPID.connect(self._focus_logic.read_pid)
        self.sigUpdatePIDgain.connect(self._focus_logic.update_pid)
        self.sigLaunchCalibration.connect(self._focus_logic.calibrate_autofocus)
        self.sigLiveOn.connect(self._focus_logic.start_live_display)
        self.sigLiveOff.connect(self._focus_logic.stop_live_display)
        self.sigUpdateThreshold.connect(self._focus_logic.update_threshold)

        # keyboard shortcuts for up / down buttons
        self._mw.move_up_PushButton.setShortcut(QtCore.Qt.Key_Up)
        self._mw.move_down_PushButton.setShortcut(QtCore.Qt.Key_Down)

        # signals from logic
        self._focus_logic.sigStepChanged.connect(self.update_step)
        self._focus_logic.sigPositionChanged.connect(self.update_position)
        self._focus_logic.sigPiezoInitFinished.connect(self.piezo_init_finished)
        self._focus_logic.sigUpdateDisplay.connect(self.update_timetrace)
        self._focus_logic.sigPIDChanged.connect(self.update_pid)
        self._focus_logic.sigPlotCalibration.connect(self.plot_calibration)
        self._focus_logic.sigDisplayImage.connect(self.live_display)

        # update pid values
        self.sigReadPID.emit()

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
        # update the label
        self._mw.position_Label.setText('z position (um): {:.3f}'.format(position))
        # and the timetrace
        if self._focus_logic.timetrace_enabled:
            self.update_timetrace()

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

    def start_tracking_clicked(self):

        if self._focus_logic.timetrace_enabled:  # timetrace already running
            self._mw.tracking_Action.setText('Start Tracking')
            self.sigTimetraceOff.emit()
        else:
            self._mw.tracking_Action.setText('Stop Tracking')
            self.sigTimetraceOn.emit()

    def update_timetrace(self):
        # t data not needed, only if it is wanted that the axis labels move also. then see variant 2 from pyqtgraph.examples scrolling plot
        # self.t_data[:-1] = self.t_data[1:] # shift data in the array one position to the left, keeping same array size
        # self.t_data[-1] += 1 # add the new last element
        self.y_data[:-1] = self.y_data[1:]  # shfit data one position to the left ..
        self.y_data[-1] = self._focus_logic.get_position()

        # self._timetrace.setData(self.t_data, self.y_data) # x axis values running with the timetrace
        self._timetrace.setData(self.y_data)  # x axis values do not move

    # Functions for the autofocus

    def pid_changed(self):
        p_gain = self._mw.Pgain_doubleSpinBox.value()
        i_gain = self._mw.Igain_doubleSpinBox.value()
        self.sigUpdatePIDgain.emit(p_gain, i_gain)

    def threshold_changed(self):
        threshold = self._mw.threshold_spinBox.value()
        self.sigUpdateThreshold.emit(threshold)

    def update_pid(self, p_gain, i_gain):
        self._mw.Pgain_doubleSpinBox.setValue(p_gain)
        self._mw.Igain_doubleSpinBox.setValue(i_gain)

    def calibrate_autofocus(self):
        if not self._mw.calibration_pushButton.isChecked():
            self.sigLaunchCalibration.emit()

    def plot_calibration(self, piezo_position, qpd_signal, fit, slope):
        self._mw.calibration_PlotWidget.clear()
        self._mw.calibration_PlotWidget.plot(piezo_position, qpd_signal, symbol='o')
        self._mw.calibration_PlotWidget.plot(piezo_position, fit)
        self._mw.calibration_PlotWidget.setLabel('bottom', 'piezo position (nm)')
        self._mw.calibration_PlotWidget.setLabel('left', 'QPD signal')
        self._mw.slope_lineEdit.setText("{:.2f}".format(slope))

    def start_live(self):
        if self._focus_logic._live_display:
            self._mw.live_Action.setText('Start Live')
            self.sigLiveOff.emit()
        else:
            self._mw.live_Action.setText('Stop Live')
            self.sigLiveOn.emit()

    def live_display(self, im, im_thresh):
        self._image = pg.ImageItem(image=im, axisOrder='row-major')
        self._mw.raw_image_PlotWidget.addItem(self._image)
        self._mw.raw_image_PlotWidget.setAspectLocked(True)

        self._binary = pg.ImageItem(image=im_thresh, axisOrder='row-major')
        self._mw.threshold_image_PlotWidget.addItem(self._binary)
        self._mw.threshold_image_PlotWidget.setAspectLocked(True)
        #self._mw.raw_image_PlotWidget.plot([500], [500], symbol='o')

