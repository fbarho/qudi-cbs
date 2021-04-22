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


class PIDSettingDialog(QtWidgets.QDialog):
    """ Create the SettingsDialog window, based on the corresponding *.ui file.
    """
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_PID_parameters.ui')

        # Load it
        super(PIDSettingDialog, self).__init__()
        uic.loadUi(ui_file, self)


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
    sigCalibrateFocusStabilization = QtCore.Signal()
    sigCalibrateOffset = QtCore.Signal()
    sigSetSetpoint = QtCore.Signal()
    sigLiveOn = QtCore.Signal()
    sigLiveOff = QtCore.Signal()
    sigUpdateThreshold = QtCore.Signal(int)
    sigLaunchAutofocus = QtCore.Signal()
    sigAutofocusStart = QtCore.Signal()
    sigAutofocusStop = QtCore.Signal()

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
        self._mw.centralwidget.hide()
        self.init_pid_settings_ui()

        # DockWidget for the camera - for the RAMM setup, the camera is only used to check for the quality of the
        # reflexion. By default the dock widget is hidden.
        if self._focus_logic._setup == 'RAMM':
            self._mw.threshold_image_PlotWidget.hide()
            self._mw.threshold_label.hide()
            self._mw.threshold_spinBox.hide()
            self._mw.im_display_dockWidget.hide()

        # Menu bar actions
        # File menu
        self._mw.close_MenuAction.triggered.connect(self._mw.close)
        self._mw.pid_settings_Action.triggered.connect(self.open_pid_settings)

        # initialize the display of the camera
        self.raw_imageitem = pg.ImageItem(axisOrder='row-major')
        self._mw.raw_image_PlotWidget.addItem(self.raw_imageitem)
        self._mw.raw_image_PlotWidget.setAspectLocked(True)

        self.threshold_imageitem = pg.ImageItem(axisOrder='row-major')
        self._mw.threshold_image_PlotWidget.addItem(self.threshold_imageitem)
        self._mw.threshold_image_PlotWidget.setAspectLocked(True)

        self._centroid = self._mw.threshold_image_PlotWidget.plot([0], [0], symbol='+')

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
        self._mw.calibration_pushButton.clicked.connect(self.calibrate_focus_stabilization)
        self._mw.Find_offset_pushButton.clicked.connect(self.calibrate_offset)
        self._mw.setpoint_pushButton.clicked.connect(self.define_autofocus_setpoint)
        self._mw.threshold_spinBox.valueChanged.connect(self.threshold_changed)
        self._mw.live_Action.triggered.connect(self.start_stop_live)
        self._mw.autofocus_Action.triggered.connect(self.start_stop_focus_stabilization)

        # signals to logic
        self.sigUpdateStep.connect(self._focus_logic.set_step)
        self.sigMoveUp.connect(self._focus_logic.move_up)
        self.sigMoveDown.connect(self._focus_logic.move_down)
        self.sigInitPiezo.connect(self._focus_logic.init_piezo)
        self.sigTimetraceOn.connect(self._focus_logic.start_tracking)
        self.sigTimetraceOff.connect(self._focus_logic.stop_tracking)
        self.sigCalibrateFocusStabilization.connect(self._focus_logic.calibrate_focus_stabilization)
        self.sigCalibrateOffset.connect(self._focus_logic.calibrate_offset)
        self.sigSetSetpoint.connect(self._focus_logic.define_autofocus_setpoint)
        self.sigLiveOn.connect(self._focus_logic.start_live_display)
        self.sigLiveOff.connect(self._focus_logic.stop_live_display)
        self.sigUpdateThreshold.connect(self._focus_logic.update_threshold)
        self.sigAutofocusStart.connect(self._focus_logic.start_autofocus)
        self.sigAutofocusStop.connect(self._focus_logic.stop_autofocus)

        # keyboard shortcuts for up / down buttons
        self._mw.move_up_PushButton.setShortcut(QtCore.Qt.Key_Up)
        self._mw.move_down_PushButton.setShortcut(QtCore.Qt.Key_Down)

        # signals from logic
        self._focus_logic.sigStepChanged.connect(self.update_step)
        self._focus_logic.sigPositionChanged.connect(self.update_position)
        self._focus_logic.sigPiezoInitFinished.connect(self.piezo_init_finished)
        self._focus_logic.sigUpdateDisplay.connect(self.update_timetrace)
        self._focus_logic.sigPlotCalibration.connect(self.plot_calibration)
        self._focus_logic.sigOffsetCalibration.connect(self.display_offset)
        self._focus_logic.sigDisplayImage.connect(self.live_display)
        self._focus_logic.sigDisplayImageAndMask.connect(self.live_display)
        self._focus_logic.sigAutofocusError.connect(self.error_live_stabilization)
        self._focus_logic.sigSetpoint.connect(self.update_autofocus_setpoint)

    def on_deactivate(self):
        self.sigUpdateStep.disconnect()
        self._mw.move_up_PushButton.clicked.disconnect()
        self._mw.move_down_PushButton.clicked.disconnect()
        self._focus_logic.sigStepChanged.disconnect()
        self._focus_logic.sigPositionChanged.disconnect()
        self._mw.close()

    def show(self):
        """ Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def init_pid_settings_ui(self):
        """ Initialize the window for the pid parameters
        """
        # Create the PID settings window
        self._w_pid = PIDSettingDialog()
        # Connect the action of the settings window with the code:
        self._w_pid.accepted.connect(self.update_pid_parameters)  # ok button
        self._w_pid.rejected.connect(self.keep_pid_parameters)  # cancel buttons

        self.keep_pid_parameters()

    # slot to open the PID settings window
    def open_pid_settings(self):
        """ Opens the PID settings menu.
        """
        self._w_pid.exec_()

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

    def update_pid_parameters(self):
        self._focus_logic._autofocus_logic._P_gain = int(self._w_pid.Pgain_doubleSpinBox.value())
        self._focus_logic._autofocus_logic._I_gain = int(self._w_pid.Igain_doubleSpinBox.value())

    def keep_pid_parameters(self):
        self._w_pid.Pgain_doubleSpinBox.setValue(self._focus_logic._autofocus_logic._P_gain)
        self._w_pid.Igain_doubleSpinBox.setValue(self._focus_logic._autofocus_logic._I_gain)

    def threshold_changed(self):
        threshold = self._mw.threshold_spinBox.value()
        self.sigUpdateThreshold.emit(threshold)

    def calibrate_focus_stabilization(self):
        if not self._mw.calibration_pushButton.isChecked():
            self.sigCalibrateFocusStabilization.emit()
            self._mw.calibration_pushButton.setText('Calibrating ...')

    def calibrate_offset(self):
        if not self._mw.Find_offset_pushButton.isChecked():
            self.sigCalibrateOffset.emit()
            self._mw.Find_offset_pushButton.setText('Calibrating ...')

    def display_offset(self, offset):
        self._mw.offset_lineEdit.setText("{:.2f}".format(offset))
        self._mw.Find_offset_pushButton.setText('Find offset')

    def define_autofocus_setpoint(self):
        self.sigSetSetpoint.emit()

    def update_autofocus_setpoint(self, setpoint):
        self._mw.setpoint_lineEdit.setText("{:.2f}".format(setpoint))

    def plot_calibration(self, piezo_position, qpd_signal, fit, slope):
        self._mw.calibration_PlotWidget.clear()
        self._mw.calibration_PlotWidget.plot(piezo_position, qpd_signal, symbol='o')
        self._mw.calibration_PlotWidget.plot(piezo_position, fit)
        self._mw.calibration_PlotWidget.setLabel('bottom', 'piezo position (nm)')
        self._mw.calibration_PlotWidget.setLabel('left', 'autofocus signal')
        self._mw.slope_lineEdit.setText("{:.2f}".format(slope))
        self._mw.calibration_pushButton.setText('Launch calibration')

    def start_stop_focus_stabilization(self):
        """ When the pushbutton start/stop autofocus is pushed, a signal is sent to this function. If the autofocus is
        not running yet, a signal is sent to the logic to launch it and the button text is changed to "stop autofocus".
        If the autofocus is already running, a signal is sent to the logic to stop the autofocus loop. The text of the
        button is changed back to "Start autofocus".
        """
        if self._focus_logic._run_autofocus:
            self._mw.autofocus_Action.setText('Start focus stabilization')
            self.sigAutofocusStop.emit()
        else:
            self._mw.autofocus_Action.setText('Stop focus stabilization')
            self.sigAutofocusStart.emit()

    def error_live_stabilization(self):
        self._mw.autofocus_Action.setText('Start focus stabilization')
        self._mw.calibration_pushButton.setChecked(False)

    def start_stop_live(self):
        """ When the pushbutton start/stop Live is pushed, a signal is sent to this function. If the camera is
        not running yet, a signal is sent to the logic to launch it and the button text is changed to "Stop Live".
        If the camera is already running, a signal is sent to the logic to stop the acquisition loop. The text of the
        button is changed back to "Start Live".
        """
        if self._focus_logic._live_display:
            self._mw.live_Action.setText('Start live display')
            self.sigLiveOff.emit()
        else:
            self._mw.live_Action.setText('Stop live display')
            self._mw.im_display_dockWidget.show()
            self.sigLiveOn.emit()

    def live_display(self, im, *threshold):
        """ Display the live image captured by the Thorlabs camera. This function accepts two inputs :
            - the raw image im
            - an optional input called threshold that is used only when the autofocus is working directly with the
            image. In that case, this input should contain a binary image (mask) as well as the X/Y positions of the
            detected IR reflection.
        """
        self.raw_imageitem.setImage(im)
        if threshold:
            im_thresh = threshold(0)
            x = threshold(1)
            y = threshold(2)
            self.threshold_imageitem.setImage(im_thresh)
            self._mw.threshold_image_PlotWidget.removeItem(self._centroid)
            self._centroid = self._mw.threshold_image_PlotWidget.plot([x], [y], symbol='+', color='red')

