# -*- coding: utf-8 -*-
"""
This module contains a GUI that allows to handle the fluidics devices
(valves, pump, flow rate measurement, merfish probes positionning)
"""
import os
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy import uic

from gui.guibase import GUIBase
from core.connector import Connector


class Position1SettingDialog(QtWidgets.QDialog):
    """ Create the SettingsDialog window, based on the corresponding *.ui file."""

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_position1_settings.ui')

        # Load it
        super(Position1SettingDialog, self).__init__()
        uic.loadUi(ui_file, self)


class FluidicsWindow(QtWidgets.QMainWindow):
    """ Class defined for the main window (not the module)
    """
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_fluidics.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()


class FluidicsGUI(GUIBase):
    """ Main window that allows to handle the fluidics devices

    Example config for copy-paste:

    fluidics_gui:
        module.Class: 'fluidics.fluidics_gui.FluidicsGUI'
        connect:
            valve_logic: 'valve_logic'
            flowcontrol_logic: 'flowcontrol_logic'
            positioning_logic: 'positioning_logic'
    """

    # connector to logic module
    valve_logic = Connector(interface='ValveLogic')
    flowcontrol_logic = Connector(interface='FlowcontrolLogic')
    positioning_logic = Connector(interface='PositioningLogic')

    # Signals
    # signals for valve settings
    sigSetValvePosition = QtCore.Signal(str, int)

    # signals for flowcontrol actions
    sigSetPressure = QtCore.Signal(float)
    sigStartFlowMeasure = QtCore.Signal()
    sigStopFlowMeasure = QtCore.Signal()

    # signals for positioning actions
    sigStopMovement = QtCore.Signal()
    sigMoveStage = QtCore.Signal(tuple)
    sigMoveToTarget = QtCore.Signal(int)
    sigSetPos1 = QtCore.Signal(tuple)

    def __init__(self, config, **kwargs):
        # load connection
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Required initialization steps.
        """
        self._valve_logic = self.valve_logic()
        self._flow_logic = self.flowcontrol_logic()
        self._positioning_logic = self.positioning_logic()

        self._mw = FluidicsWindow()
        self._mw.centralwidget.hide()  # everything is in dockwidgets

        # initialize settings dialog
        self.init_position1_settings_ui()

        # menu actions
        self._mw.close_MenuAction.triggered.connect(self._mw.close)

        # initialize the valve control dockwidget
        self._mw.valve1_Label.setText(self._valve_logic.valve_names[0])
        self._mw.valve2_Label.setText(self._valve_logic.valve_names[1])
        self._mw.valve3_Label.setText(self._valve_logic.valve_names[2])
        self._mw.valve1_ComboBox.addItems(self._valve_logic.valve_positions[0])
        self._mw.valve2_ComboBox.addItems(self._valve_logic.valve_positions[1])
        self._mw.valve3_ComboBox.addItems(self._valve_logic.valve_positions[2])

        # set current index according to actual position of valve on start
        # ..

        # signals
        self._mw.valve1_ComboBox.activated[str].connect(self.change_valve1_position)
        self._mw.valve2_ComboBox.activated[str].connect(self.change_valve2_position)
        self._mw.valve3_ComboBox.activated[str].connect(self.change_valve3_position)

        # signals to logic
        self.sigSetValvePosition.connect(self._valve_logic.set_valve_position)


        # initialize the flow control dockwidget and its toolbar
        self.init_flowcontrol()

        # initialize the positioning dockwidget and its toolbar
        self.init_positioning()

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

    def init_flowcontrol(self):
        """ Initializes the labels on the flowcontrol dockwidget and the toolbar actions """
        # set text to unit labels
        self._mw.pressure_unit_Label.setText(self._flow_logic.get_pressure_unit())
        self._mw.pressure_unit_Label2.setText(self._flow_logic.get_pressure_unit())
        self._mw.flowrate_unit_Label.setText(self._flow_logic.get_flowrate_unit())

        # toolbar actions
        self._mw.set_pressure_Action.triggered.connect(self.set_pressure_clicked)
        self._mw.start_flow_measurement_Action.triggered.connect(self.measure_flow_clicked)

        # signals to logic
        self.sigSetPressure.connect(self._flow_logic.set_pressure)
        self.sigStartFlowMeasure.connect(self._flow_logic.start_flow_measurement)
        self.sigStopFlowMeasure.connect(self._flow_logic.stop_flow_measurement)

        # signals from logic
        self._flow_logic.sigUpdateFlowMeasurement.connect(self.update_flowrate_and_pressure)

    def init_positioning(self):
        """ Initializes the indicators on the positioning dockwidget and the toolbar actions """
        if self._positioning_logic.origin is None:
            self._mw.go_to_position_Action.setDisabled(True)

        # initialize indicators
        stage_position = self._positioning_logic.get_position()
        self._mw.x_axis_position_LineEdit.setText(str(stage_position[0]))
        self._mw.y_axis_position_LineEdit.setText(str(stage_position[1]))
        self._mw.z_axis_position_LineEdit.setText(str(stage_position[2]))

        self._mw.probe_position_LineEdit.setText('Please calibrate !')

        # toolbar actions
        self._mw.move_stage_Action.triggered.connect(self.move_stage_clicked)
        self._mw.set_position1_Action.triggered.connect(self.open_calibration_settings)
        self._mw.go_to_position_Action.triggered.connect(self.go_to_position_clicked)

        # signals to logic
        self.sigMoveStage.connect(self._positioning_logic.start_move_stage)
        self.sigMoveToTarget.connect(self._positioning_logic.start_move_to_target)
        self.sigSetPos1.connect(self._positioning_logic.set_origin)
        self.sigStopMovement.connect(self._positioning_logic.abort_movement)

        # signals from logic
        self._positioning_logic.sigUpdatePosition.connect(self.update_stage_position)
        self._positioning_logic.sigStageMoved.connect(self.stage_movement_finished)
        self._positioning_logic.sigOriginDefined.connect(self.origin_defined)
        self._positioning_logic.sigStageMovedToTarget.connect(self.update_target_position)
        self._positioning_logic.sigStageStopped.connect(self.stage_stopped)

    # Initialisation of the position1 settings windows
    def init_position1_settings_ui(self):
        """ Definition, configuration and initialisation of the settings dialog that allows to calibrate the position 1
        """
        # Create the settings window
        self._pos1_sd = Position1SettingDialog()
        # Connect the action of the settings window with the code:
        self._pos1_sd.accepted.connect(self.set_position1)  # ok button
        self._pos1_sd.rejected.connect(self.set_position1_canceled)  # cancel button

        self.sd_set_default_values()

    def set_position1(self):
        x_pos = self._pos1_sd.x_pos_DSpinBox.value()
        y_pos = self._pos1_sd.y_pos_DSpinBox.value()
        z_pos = self._pos1_sd.z_pos_DSpinBox.value()
        position1 = (x_pos, y_pos, z_pos)
        self.sigSetPos1.emit(position1)

    def set_position1_canceled(self):
        pass

    def sd_set_default_values(self):
        pass
    # end of position1 settings window related methods

    # slots belonging to the positioning
    @QtCore.Slot()
    def move_stage_clicked(self):
        """ Callback of move_stage toolbutton. Handles the state of the toolbutton and sends a signal to the logic
        to either do a movement or to stop it depending on the current state.
        """
        if self._positioning_logic.moving:  # stage already in movement, will be stopped by clicking the toolbutton
            self._mw.move_stage_Action.setText('Move Stage')
            if self._positioning_logic.origin is not None:  # allow access to go to target toolbutton when position 1 is already defined
                self._mw.go_to_position_Action.setDisabled(False)
            self.sigStopMovement.emit()
        else:
            self._mw.move_stage_Action.setText('Stop moving')
            self._mw.go_to_position_Action.setDisabled(True)
            x_pos = self._mw.x_axis_position_DSpinBox.value()
            y_pos = self._mw.y_axis_position_DSpinBox.value()
            z_pos = self._mw.z_axis_position_DSpinBox.value()
            position = (x_pos, y_pos, z_pos)
            self.sigMoveStage.emit(position)

    @QtCore.Slot(tuple)
    def stage_movement_finished(self, position):
        """ Callback of sigStageMoved in logic module. Movement is finished and toolbutton state needs to be reset.
        Updates the current position indicators"""
        self._mw.move_stage_Action.setChecked(False)
        self._mw.move_stage_Action.setText('Move Stage')
        if self._positioning_logic.origin is not None:
            self._mw.go_to_position_Action.setDisabled(False)
        self._mw.x_axis_position_LineEdit.setText(str(position[0]))
        self._mw.y_axis_position_LineEdit.setText(str(position[1]))
        self._mw.z_axis_position_LineEdit.setText(str(position[2]))
        # set the current position of the merfish probe to its indicator if the stage coordinates correspond to a position
        xy_pos = (position[0], position[1])
        if xy_pos in self._positioning_logic._probe_xy_position_dict.keys():
            self._mw.probe_position_LineEdit.setText(str(self._positioning_logic._probe_xy_position_dict[xy_pos]))
        elif self._positioning_logic.origin is None:
            pass  # keep the default text if position1 is not yet defined
        else:
            self._mw.probe_position_LineEdit.setText('Not at a probe XY position')

    @QtCore.Slot(tuple, int)
    def update_target_position(self, position, target_position):
        """ Callback of sigStageMovedToTarget in logic module. Movement is finished and toolbutton state needs to be reset.
        Updates the current position indicators (stage and target)"""
        self._mw.go_to_position_Action.setChecked(False)
        self._mw.go_to_position_Action.setText('Go to Target')
        self._mw.move_stage_Action.setDisabled(False)
        # set the setpoint and the indicator widgets to the current position accordingly to the target
        self._mw.x_axis_position_DSpinBox.setValue(position[0])
        self._mw.y_axis_position_DSpinBox.setValue(position[1])
        self._mw.z_axis_position_DSpinBox.setValue(position[2])
        self._mw.x_axis_position_LineEdit.setText(str(position[0]))
        self._mw.y_axis_position_LineEdit.setText(str(position[1]))
        self._mw.z_axis_position_LineEdit.setText(str(position[2]))
        self._mw.probe_position_LineEdit.setText(str(target_position))

    @QtCore.Slot(tuple)
    def update_stage_position(self, position):
        """ Callback of sigUpdatePosition in logic module. Updates the current position indicators"""
        self._mw.x_axis_position_LineEdit.setText(str(position[0]))
        self._mw.y_axis_position_LineEdit.setText(str(position[1]))
        self._mw.z_axis_position_LineEdit.setText(str(position[2]))
        # set the current position of the merfish probe to its indicator if the stage coordinates correspond to a position
        xy_pos = (position[0], position[1])
        if xy_pos in self._positioning_logic._probe_xy_position_dict.keys():
            self._mw.probe_position_LineEdit.setText(str(self._positioning_logic._probe_xy_position_dict[xy_pos]))
        elif self._positioning_logic.origin is None:
            pass  # keep the default text if position1 is not yet defined
        else:
            self._mw.probe_position_LineEdit.setText('Not at a probe XY position')

    @QtCore.Slot()
    def go_to_position_clicked(self):
        """ Callback of go_to_position toolbutton. Handles the state of the toolbutton and sends a signal to the logic
        to either do a movement to a target position (position of a merfish probe)
        or to stop the movement depending on the current state.
        """
        if self._positioning_logic.moving:  # stage already in movement
            self._mw.go_to_position_Action.setText('Go to Target')
            self._mw.move_stage_Action.setDisabled(False)
            self.sigStopMovement.emit()
        else:
            self._mw.go_to_position_Action.setText('Stop moving')
            self._mw.move_stage_Action.setDisabled(True)
            position = self._mw.target_probe_position_SpinBox.value()  # position is an integer
            self.sigMoveToTarget.emit(position)

    @QtCore.Slot(tuple)
    def stage_stopped(self, position):
        """ Callback of sigStageStopped in logic module. Movement has been aborted by user. Toolbutton state needs to be reset.
        Updates the current position indicators (stage and target)"""
        self._mw.move_stage_Action.setDisabled(False)
        self._mw.move_stage_Action.setText('Move Stage')
        self._mw.move_stage_Action.setChecked(False)
        if self._positioning_logic.origin is not None:
            self._mw.go_to_position_Action.setDisabled(False)
            self._mw.go_to_position_Action.setText('Go to Target')
            self._mw.go_to_position_Action.setChecked(False)
        self._mw.x_axis_position_LineEdit.setText(str(position[0]))
        self._mw.y_axis_position_LineEdit.setText(str(position[1]))
        self._mw.z_axis_position_LineEdit.setText(str(position[2]))
        xy_pos = (position[0], position[1])
        if xy_pos in self._positioning_logic._probe_xy_position_dict.keys():
            self._mw.probe_position_LineEdit.setText(str(self._positioning_logic._probe_xy_position_dict[xy_pos]))
        elif self._positioning_logic.origin is None:
            pass
        else:
            self._mw.probe_position_LineEdit.setText('Not at a probe XY position')

    @QtCore.Slot()
    def open_calibration_settings(self):
        """ Callback of set_position1 toolbutton. Opens a dialog to set position 1 as origin. """
        self._pos1_sd.exec_()

    @QtCore.Slot()
    def origin_defined(self):
        """ Callback of the signal sigOriginDefined in the logic module. Enables the functionality that can only be used
        when an origin is defined (addressing stage positions via the merfish probe number)"""
        self._mw.go_to_position_Action.setDisabled(False)
        position = self._positioning_logic.get_position()
        xy_pos = (position[0], position[1])
        if xy_pos in self._positioning_logic._probe_xy_position_dict.keys():
            self._mw.probe_position_LineEdit.setText(str(self._positioning_logic._probe_xy_position_dict[xy_pos]))
        else:
            self._mw.probe_position_LineEdit.setText('Not at a probe XY position')


    @QtCore.Slot()
    def set_pressure_clicked(self):
        """ Callback of the set pressure toolbutton. Retrieves the setpoint value from the spinbox and sends a
        signal to the logic.
        """
        pressure = self._mw.pressure_setpoint_DSpinBox.value()
        self.sigSetPressure.emit(pressure)

    def measure_flow_clicked(self):
        """ Callback of start flow measurement toolbutton. Handles the toolbutton state and initiates the start / stop
        of flowrate and pressure measurements
        """
        if self._flow_logic.measuring:  # measurement already running
            self._mw.start_flow_measurement_Action.setText('Start Flowrate measurement')
            self.sigStopFlowMeasure.emit()
        else:
            self._mw.start_flow_measurement_Action.setText('Stop Flowrate measurement')
            self.sigStartFlowMeasure.emit()

    @QtCore.Slot(float, float)
    def update_flowrate_and_pressure(self, pressure, flowrate):
        self._mw.pressure_LineEdit.setText('{:.2f}'.format(pressure))
        self._mw.flowrate_LineEdit.setText('{:.2f}'.format(flowrate))


    # maybe combine these slots into one and getting the valve number with lambda function
    def change_valve1_position(self):
        # get current index of the valve position combobox
        index = self._mw.valve1_ComboBox.currentIndex()
        valve_pos = index + 1  # zero indexing
        self.sigSetValvePosition.emit('a', valve_pos)

    def change_valve2_position(self):
        # get current index of the valve position combobox
        index = self._mw.valve2_ComboBox.currentIndex()
        valve_pos = index + 1  # zero indexing
        self.sigSetValvePosition.emit('b', valve_pos)

    def change_valve3_position(self):
        # get current index of the valve position combobox
        index = self._mw.valve3_ComboBox.currentIndex()
        valve_pos = index + 1  # zero indexing
        self.log.info(f'valve position c: {valve_pos}')
        self.sigSetValvePosition.emit('c', valve_pos)  #precedemment valve3


