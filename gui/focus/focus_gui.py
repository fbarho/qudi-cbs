# -*- coding: utf-8 -*-
"""
This module contains a test GUI for controlling a piezo which allows to set the focus

"""
import os
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

class FocusWindowCE(FocusWindow):
    """ Focus Window child class that allows to stop the tracking mode and camera live mode when window is closed. """
    def __init__(self, close_function):
        super().__init__()
        self.close_function = close_function

    def closeEvent(self, event):
        self.close_function()
        event.accept()


class FocusGUI(GUIBase):
    """ Tools to position the piezo to set the focus, and to calibrate and start focus stabilization (= autofocus)
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
    sigCalibrateFocusStabilization = QtCore.Signal()
    sigCalibrateOffset = QtCore.Signal()
    sigLiveOn = QtCore.Signal()
    sigLiveOff = QtCore.Signal()
    sigUpdateThreshold = QtCore.Signal(int)
    sigAutofocusStart = QtCore.Signal()
    sigAutofocusStop = QtCore.Signal()
    sigSearchFocus = QtCore.Signal()
    sigDoPiezoPositionCorrection = QtCore.Signal()

    _mw = None

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initializes all needed UI files and establishes the connectors. Signal connections.
        """
        self._focus_logic = self.focus_logic()

        # Windows
        self._mw = FocusWindowCE(self.close_function)
        self._mw.centralwidget.hide()
        self.init_pid_settings_ui()

        # setup specific adjustments of the GUI
        # DockWidget for the camera - for the RAMM setup, the camera is only used to check for the quality of the
        # reflexion. By default the dock widget is hidden.
        if self._focus_logic._setup == 'RAMM':
            self._mw.threshold_image_PlotWidget.hide()
            self._mw.threshold_label.hide()
            self._mw.threshold_SpinBox.hide()
            self._mw.im_display_dockWidget.hide()
        if self._focus_logic._setup == 'PALM':
            self._mw.find_offset_PushButton.hide()
            self._mw.offset_lineEdit.hide()

        # initialize the display of the camera
        self.raw_imageitem = pg.ImageItem(axisOrder='row-major')
        self._mw.raw_image_PlotWidget.addItem(self.raw_imageitem)
        self._mw.raw_image_PlotWidget.setAspectLocked(True)

        self.threshold_imageitem = pg.ImageItem(axisOrder='row-major')
        self._mw.threshold_image_PlotWidget.addItem(self.threshold_imageitem)
        self._mw.threshold_image_PlotWidget.setAspectLocked(True)

        self._centroid = self._mw.threshold_image_PlotWidget.plot([0], [0], symbol='+')

        # actualize the piezo position
        position = self._focus_logic.get_position()
        self._mw.position_Label.setText('z position (um): {:.3f}'.format(position))

        # data for timetrace initialization
        self.y_data = np.zeros(100)
        # create a reference to the line object (this is returned when calling plot method of pg.PlotWidget)
        self._timetrace = self._mw.timetrace_PlotWidget.plot(self.y_data, pen=(0, 255, 0))

        # toolbutton state
        self._mw.piezo_init_Action.setChecked(False)
        self._mw.tracking_Action.setEnabled(True)  # just to be sure, this is the initial state defined in designer
        self._mw.tracking_Action.setChecked(self._focus_logic.timetrace_enabled)  # checked state takes the same bool value as enabled attribute in logic (enabled = 0: no timetrace running) # button is defined as checkable in designer
        self._mw.start_live_Action.setChecked(self._focus_logic.live_display_enabled)
        self._mw.autofocus_Action.setChecked(self._focus_logic.autofocus_enabled)
        self._mw.autofocus_Action.setDisabled(True)
        self._mw.search_focus_Action.setDisabled(True)
        self._mw.piezo_position_correction_Action.setDisabled(True)

        # connect signals
        # internal signals
        # menubar
        self._mw.close_MenuAction.triggered.connect(self._mw.close)
        self._mw.pid_settings_Action.triggered.connect(self.open_pid_settings)
        # toolbar
        self._mw.piezo_init_Action.triggered.connect(self.piezo_init_clicked)
        self._mw.tracking_Action.triggered.connect(self.start_tracking_clicked)
        self._mw.start_live_Action.triggered.connect(self.start_live_clicked)
        self._mw.autofocus_Action.triggered.connect(self.start_focus_stabilization_clicked)
        self._mw.search_focus_Action.triggered.connect(self.search_focus_clicked)
        self._mw.piezo_position_correction_Action.triggered.connect(self.piezo_position_correction_clicked)
        # widgets
        self._mw.step_doubleSpinBox.valueChanged.connect(self.step_changed)
        self._mw.move_up_PushButton.clicked.connect(self.move_up_button_clicked)
        self._mw.move_down_PushButton.clicked.connect(self.move_down_button_clicked)
        self._mw.calibration_PushButton.clicked.connect(self.calibrate_focus_stabilization_clicked)
        self._mw.find_offset_PushButton.clicked.connect(self.calibrate_offset_clicked)
        self._mw.threshold_SpinBox.valueChanged.connect(self.threshold_changed)

        # signals to logic
        self._mw.setpoint_PushButton.clicked.connect(self._focus_logic.define_autofocus_setpoint)
        self.sigUpdateStep.connect(self._focus_logic.set_step)
        self.sigMoveUp.connect(self._focus_logic.move_up)
        self.sigMoveDown.connect(self._focus_logic.move_down)
        self.sigInitPiezo.connect(self._focus_logic.init_piezo)
        self.sigTimetraceOn.connect(self._focus_logic.start_position_tracking)
        self.sigTimetraceOff.connect(self._focus_logic.stop_position_tracking)
        self.sigCalibrateFocusStabilization.connect(self._focus_logic.calibrate_focus_stabilization)
        self.sigCalibrateOffset.connect(self._focus_logic.calibrate_offset)
        self.sigLiveOn.connect(self._focus_logic.start_live_display)
        self.sigLiveOff.connect(self._focus_logic.stop_live_display)
        self.sigUpdateThreshold.connect(self._focus_logic.update_threshold)
        self.sigAutofocusStart.connect(self._focus_logic.start_autofocus)
        self.sigAutofocusStop.connect(self._focus_logic.stop_autofocus)
        self.sigSearchFocus.connect(self._focus_logic.start_search_focus)
        self.sigDoPiezoPositionCorrection.connect(self._focus_logic.do_piezo_position_correction)

        # keyboard shortcuts for up / down buttons
        self._mw.move_up_PushButton.setShortcut(QtCore.Qt.Key_Up)
        self._mw.move_down_PushButton.setShortcut(QtCore.Qt.Key_Down)

        # signals from logic
        self._focus_logic.sigStepChanged.connect(self.update_step)
        self._focus_logic.sigPositionChanged.connect(self.update_position)
        self._focus_logic.sigPiezoInitFinished.connect(self.piezo_init_finished)
        self._focus_logic.sigUpdateTimetrace.connect(self.update_timetrace)
        self._focus_logic.sigPlotCalibration.connect(self.plot_calibration)
        self._focus_logic.sigOffsetCalibration.connect(self.display_offset)
        self._focus_logic.sigDisplayImage.connect(self.live_display)
        self._focus_logic.sigDisplayImageAndMask.connect(self.live_display)
        self._focus_logic.sigAutofocusStopped.connect(self.autofocus_stopped)
        self._focus_logic.sigAutofocusError.connect(self.autofocus_stopped)
        self._focus_logic.sigSetpointDefined.connect(self.update_autofocus_setpoint)
        self._focus_logic.sigFocusFound.connect(self.reset_search_focus_button)
        self._focus_logic.sigPiezoPositionCorrectionFinished.connect(self.reset_position_correction_button)
        self._focus_logic.sigDisableFocusActions.connect(self.disable_focus_toolbuttons)
        self._focus_logic.sigEnableFocusActions.connect(self.enable_focus_toolbuttons)

    def on_deactivate(self):
        """ Required deactivation steps. """
        self.sigUpdateStep.disconnect()
        self._mw.move_up_PushButton.clicked.disconnect()
        self._mw.move_down_PushButton.clicked.disconnect()
        self._focus_logic.sigStepChanged.disconnect()
        self._focus_logic.sigPositionChanged.disconnect()
        # either remove the disconnections or disconnect also all the other signals
        self._mw.close()

    def show(self):
        """ Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

# =============================================
# PID settings window
# =============================================
    def init_pid_settings_ui(self):
        """ Initialize the window for the pid parameters
        """
        # Create the PID settings window
        self._w_pid = PIDSettingDialog()
        # Connect the action of the settings window with the code:
        self._w_pid.accepted.connect(self.update_pid_parameters)  # ok button
        self._w_pid.rejected.connect(self.keep_pid_parameters)  # cancel buttons

        self.keep_pid_parameters()

    def open_pid_settings(self):
        """ Opens the PID settings menu.
        """
        self._w_pid.exec_()

    def update_pid_parameters(self):
        """ Callback of ok button in PID settings dialog. Update the chosen parameters. """
        self._focus_logic._autofocus_logic._P_gain = int(self._w_pid.Pgain_doubleSpinBox.value())
        self._focus_logic._autofocus_logic._I_gain = int(self._w_pid.Igain_doubleSpinBox.value())
        # why not use SpinBox when only integer is needed ?

    def keep_pid_parameters(self):
        """ Callback of cancel button in PID settings dialog. Reestablish former PID parameters. """
        self._w_pid.Pgain_doubleSpinBox.setValue(self._focus_logic._autofocus_logic._P_gain)
        self._w_pid.Igain_doubleSpinBox.setValue(self._focus_logic._autofocus_logic._I_gain)

# =============================================
# Slots for manual piezo positioning
# =============================================

    def step_changed(self):
        """ Callback invoked when the step for piezo movement is changed. """
        step = self._mw.step_doubleSpinBox.value()
        self.sigUpdateStep.emit(step)

    def update_step(self, step):
        """ Callback of sigStepChanged sent from focus logic. """
        self._mw.step_doubleSpinBox.setValue(step)

    def update_position(self, position):
        """ Callback of sigPositionChanged sent from focus logic. Update the label displaying the current piezo position
        and the timetrace if running. """
        # update the label
        self._mw.position_Label.setText('z position (um): {:.3f}'.format(position))
        # and the timetrace
        if self._focus_logic.timetrace_enabled:
            self.update_timetrace(position)

    def move_up_button_clicked(self):
        """ Callback of the move_up_Pushbutton. Send a signal to logic to perform a piezo movement of step upwards.
        """
        step = self._mw.step_doubleSpinBox.value()
        self.sigMoveUp.emit(step)

    def move_down_button_clicked(self):
        """ Callback of the move_down_Pushbutton. Send a signal to logic to perform a piezo movement of step downwards.
        """
        step = self._mw.step_doubleSpinBox.value()
        self.sigMoveDown.emit(step)

    def piezo_init_clicked(self):
        """ Callback of the reinitialize action button. Send a signal to logic to move piezo to its initial position.
        """
        self._mw.piezo_init_Action.setEnabled(False)
        self._mw.piezo_init_Action.setText('Initialization running..')
        self._mw.piezo_init_Action.setChecked(True)
        self.sigInitPiezo.emit()

    def piezo_init_finished(self):
        """ Callback of sigPiezoInitFinished from focus_logic. Handle the state of the action button once the
        reinitialization is done. """
        self._mw.piezo_init_Action.setText('Reinitialize')
        self._mw.piezo_init_Action.setEnabled(True)
        self._mw.piezo_init_Action.setChecked(False)

    def start_tracking_clicked(self):
        """ Callback of the tracking action button. Start the timetrace, or stop it if it is already running.
        This method handles also the state of the action button. """
        if self._focus_logic.timetrace_enabled:  # timetrace already running
            self._mw.tracking_Action.setText('Start Tracking')
            self.sigTimetraceOff.emit()
        else:
            self._mw.tracking_Action.setText('Stop Tracking')
            self.sigTimetraceOn.emit()

    def update_timetrace(self, position):
        """ Callback of sigUpdateTimetrace from focus_logic. Adds a new data point to the timetrace. """
        # t data not needed, only if it is wanted that the axis labels move also. then see variant 2 from pyqtgraph.examples scrolling plot
        # self.t_data[:-1] = self.t_data[1:] # shift data in the array one position to the left, keeping same array size
        # self.t_data[-1] += 1 # add the new last element
        self.y_data[:-1] = self.y_data[1:]  # shift data one position to the left ..
        self.y_data[-1] = position

        # self._timetrace.setData(self.t_data, self.y_data) # x axis values running with the timetrace
        self._timetrace.setData(self.y_data)  # x axis values do not move

# =============================================
# Slots for autofocus
# =============================================

    def threshold_changed(self):
        """ Callback invoked when the value in the threshold spinbox is changed.
        Threshold is used for the camera based autofocus readout. """
        threshold = self._mw.threshold_SpinBox.value()
        self.sigUpdateThreshold.emit(threshold)

    def calibrate_focus_stabilization_clicked(self):
        """ Callback of the calibration pushbutton. Starts the calibration needed for autofocus (focus stabilization),
        and handles the pushbutton state.
        """
        self._mw.calibration_PushButton.setEnabled(False)
        self._mw.calibration_PushButton.setText('Calibrating..')
        self._mw.calibration_PushButton.setChecked(True)
        self.sigCalibrateFocusStabilization.emit()

    def plot_calibration(self, piezo_position, qpd_signal, fit, slope, precision):
        """ Callback of sigPlotCalibration from focus_logic. Once the calibration finished, reset the pushbutton state
        and display the calibration results in the plotwidget and display also the calculated slope. """
        # reset calibration_PushButton state
        self._mw.calibration_PushButton.setEnabled(True)
        self._mw.calibration_PushButton.setText('Launch calibration')
        self._mw.calibration_PushButton.setChecked(False)
        # display the calibration results in the plotwidget
        self._mw.calibration_PlotWidget.clear()
        self._mw.calibration_PlotWidget.plot(piezo_position, qpd_signal, symbol='o')
        self._mw.calibration_PlotWidget.plot(piezo_position, fit)
        self._mw.calibration_PlotWidget.setLabel('bottom', 'piezo position (nm)')
        self._mw.calibration_PlotWidget.setLabel('left', 'autofocus signal')
        self._mw.slope_lineEdit.setText("{:.2f}".format(slope))
        self._mw.precision_lineEdit.setText("{:.2f}".format(precision))
        # enable the piezo position correction, focus stabilization and search focus toolbuttons
        self._mw.autofocus_Action.setDisabled(False)
        self._mw.search_focus_Action.setDisabled(False)
        if self._focus_logic._setup == 'RAMM':
            self._mw.piezo_position_correction_Action.setDisabled(False)

    def calibrate_offset_clicked(self):
        """ Callback of the find offset pushbutton. Handles the pushbutton state and starts the calibration of the
        offset for the autofocus method using a reference under the sample glass slide.
        """
        self._mw.find_offset_PushButton.setEnabled(False)
        self._mw.find_offset_PushButton.setText('Calibrating..')
        self._mw.find_offset_PushButton.setChecked(True)
        self.sigCalibrateOffset.emit()

    def display_offset(self, offset):
        """ Callback of sigOffsetCalibration from focus_logic. Once the offset is found, reset the pushbutton state
        and display the offset value. """
        self._mw.find_offset_PushButton.setEnabled(True)
        self._mw.find_offset_PushButton.setText('Find offset')
        self._mw.find_offset_PushButton.setChecked(False)
        self._mw.offset_lineEdit.setText("{:.2f}".format(offset))

    def update_autofocus_setpoint(self, setpoint):
        """ Callback of sigSetpointDefined from focus_logic. Display the current setpoint on the GUI. """
        self._mw.setpoint_lineEdit.setText("{:.2f}".format(setpoint))

    def piezo_position_correction_clicked(self):
        self._mw.piezo_position_correction_Action.setDisabled(True)
        self._mw.piezo_position_correction_Action.setText('Moving piezo into central range..')
        self._mw.search_focus_Action.setDisabled(True)  # incompatible action
        self._mw.autofocus_Action.setDisabled(True)  # can be on or off, but do not allow to act on this while position correction is running
        self.sigDoPiezoPositionCorrection.emit()

    def reset_position_correction_button(self):
        """ Callback of sigPiezoPositionCorrectionFinished from logic. Reset piezo position toolbutton to callable stage """
        self._mw.piezo_position_correction_Action.setDisabled(False)
        self._mw.piezo_position_correction_Action.setText('Piezo position correction')
        self._mw.search_focus_Action.setDisabled(False)  # re-enable other autofocus actions
        self._mw.autofocus_Action.setDisabled(False)


    def start_focus_stabilization_clicked(self):
        """ When the toolbutton start/stop autofocus is triggered, this function is called. If the autofocus is
        not running yet, a signal is sent to the logic to launch it and the button text is changed to "stop autofocus".
        If the autofocus is already running, a signal is sent to the logic to stop the autofocus loop. The text of the
        button is changed back to "Start autofocus".
        """
        if self._focus_logic.autofocus_enabled:
            self._mw.autofocus_Action.setText('Start focus stabilization')
            self._mw.search_focus_Action.setDisabled(False)
            self.sigAutofocusStop.emit()
        else:
            self._mw.autofocus_Action.setText('Stop focus stabilization')
            self._mw.search_focus_Action.setDisabled(True)  # disable incompatible action
            self.sigAutofocusStart.emit()

    def search_focus_clicked(self):
        self._mw.autofocus_Action.setDisabled(True)  # do not allow both actions at the same time
        self._mw.search_focus_Action.setText('Searching focus ...')
        self._mw.search_focus_Action.setDisabled(True)
        self.sigSearchFocus.emit()

    def reset_search_focus_button(self):
        """ Callback of sigFocusFound sent from focus_logic.
        Re-enable the focus stabilization action (autofocus_Action) and reset search_focus_Action to its default state.
        """
        self._mw.autofocus_Action.setDisabled(False)
        self._mw.search_focus_Action.setChecked(False)
        self._mw.search_focus_Action.setText('Search focus')
        self._mw.search_focus_Action.setDisabled(False)

    def autofocus_stopped(self):
        """ Callback of sigAutofocusStopped or sigAutofocusError sent from focus_logic.
        Reset autofocus action button to callable state when autofocus was programmatically stopped, ended in an error
        (autofocus signal lost) or was not started because of missing calibrations.
        """
        self._mw.autofocus_Action.setText('Start focus stabilization')
        self._mw.autofocus_Action.setChecked(False)
        self._mw.autofocus_Action.setDisabled(False)
        self._mw.search_focus_Action.setText('Search focus')
        self._mw.search_focus_Action.setChecked(False)
        self._mw.search_focus_Action.setDisabled(False)


    def start_live_clicked(self):
        """ When the action button start/stop Live is triggered, this method is called. If the camera is
        not running yet, a signal is sent to the logic to launch it and the button text is changed to "Stop Live".
        If the camera is already running, a signal is sent to the logic to stop the acquisition loop. The text of the
        button is changed back to "Start Live".
        """
        if self._focus_logic.live_display_enabled:
            self._mw.start_live_Action.setText('Start live display')
            self.sigLiveOff.emit()
        else:
            self._mw.start_live_Action.setText('Stop live display')
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
            im_thresh = threshold[0]
            x = threshold[1]
            y = threshold[2]
            self.threshold_imageitem.setImage(im_thresh)
            self._mw.threshold_image_PlotWidget.removeItem(self._centroid)
            self._centroid = self._mw.threshold_image_PlotWidget.plot([x], [y], symbol='+', color='red')

    @QtCore.Slot()
    def reset_start_tracking_button(self):
        """ Reset the state of the start tracking button, for example when tracking mode is stopped when closing the
        focus window.
        """
        self._mw.tracking_Action.setText('Start Tracking')
        self._mw.tracking_Action.setChecked(False)

    @QtCore.Slot()
    def reset_start_live_button(self):
        """ Reset the state of the start live display button, for example when live mode is stopped when closing the
        focus window.
        """
        self._mw.start_live_Action.setText('Start live display')
        self._mw.start_live_Action.setChecked(False)

    @QtCore.Slot()
    def reset_start_focus_stabilization_button(self):
        """ Reset the state of the start focus stabilization button, for example when live mode is stopped when closing the
        focus window.
        """
        self._mw.autofocus_Action.setText('Start focus stabilization')
        self._mw.autofocus_Action.setChecked(False)

    @QtCore.Slot()
    def disable_focus_toolbuttons(self):
        self._mw.piezo_init_Action.setDisabled(True)
        self._mw.piezo_position_correction_Action.setDisabled(True)
        self._mw.autofocus_Action.setDisabled(True)
        self._mw.search_focus_Action.setDisabled(True)

    @QtCore.Slot()
    def enable_focus_toolbuttons(self):
        self._mw.piezo_init_Action.setDisabled(False)
        self._mw.piezo_position_correction_Action.setDisabled(False)
        self._mw.autofocus_Action.setDisabled(False)
        self._mw.search_focus_Action.setDisabled(False)

    def close_function(self):
        # stop timetrace when window is cloded
        if self._focus_logic.timetrace_enabled:
            self.start_tracking_clicked()
            self.reset_start_tracking_button()
        # stop live mode of the camera when window is closed
        if self._focus_logic.live_display_enabled:
            self.start_live_clicked()
            self.reset_start_live_button()
        # stop autofocus ?
        if self._focus_logic.autofocus_enabled:
            self.start_focus_stabilization_clicked()
            self.reset_start_focus_stabilization_button()

