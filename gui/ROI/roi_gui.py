#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov  5 13:05:03 2020

@author: fbarho

This module contains the ROI selection user interface.
It is in large parts inspired by the qudi poimanager gui, in this version reduced to 
the functionality that we need. 
"""

import numpy as np
import os
import pyqtgraph as pg
import re

from core.connector import Connector
from core.util.units import ScaledFloat
from core.util.helpers import natural_sort
from gui.guibase import GUIBase
from qtpy import QtCore, QtGui
from qtpy import QtWidgets
from qtpy import uic
from qtwidgets.scan_plotwidget import ScanImageItem
from core.configoption import ConfigOption
from gui.validators import NameValidator


# Class representing the marker.  # adapted from POI manager module of Qudi.
class RoiMarker(pg.RectROI):
    """
    Creates a square as marker.

    @param float[2] pos: The (x, y) position of the ROI.
    @param **args: All extra keyword arguments are passed to ROI()

    Have a look at:
    http://www.pyqtgraph.org/documentation/graphicsItems/roi.html
    """
    default_pen = {'color': 'FFF', 'width': 2}  # white color as default
    select_pen = {'color': '2F3', 'width': 2}  # colored frame is the active one

    sigRoiSelected = QtCore.Signal(str)

    def __init__(self, position, width, roi_name=None, view_widget=None, **kwargs):
        """
        @param position:
        @param width:
        @param roi_name:
        @param view_widget:
        @param kwargs:
        """
        self._roi_name = '' if roi_name is None else roi_name
        self._view_widget = view_widget
        self._selected = False
        self._position = np.array(position, dtype=float)

        size = (width, width)
        super().__init__(pos=self._position, size=size, pen=self.default_pen, **kwargs)
        self.aspectLocked = True
        self.label = pg.TextItem(text=self._roi_name,
                                 anchor=(0, 1),
                                 color=self.default_pen['color'])
        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)
        self.sigClicked.connect(self._notify_clicked_roi_name)
        self.set_position(self._position)
        return

    def _addHandles(self):
        pass

    @property
    def width(self):
        return self.size()[0]

    @property
    def selected(self):
        return bool(self._selected)

    @property
    def roi_name(self):
        return str(self._roi_name)

    @property
    def position(self):
        return self._position

    @QtCore.Slot()
    def _notify_clicked_roi_name(self):
        self.sigRoiSelected.emit(self._roi_name)

    def add_to_view_widget(self, view_widget=None):
        if view_widget is not None:
            self._view_widget = view_widget
        self._view_widget.addItem(self)
        self._view_widget.addItem(self.label)
        return

    def delete_from_view_widget(self, view_widget=None):
        if view_widget is not None:
            self._view_widget = view_widget
        self._view_widget.removeItem(self.label)
        self._view_widget.removeItem(self)
        return

    def set_position(self, position):
        """
        Sets the ROI position and center the marker on that position.
        Also position the label accordingly.

        @param float[2] position: The (x,y) center position of the ROI marker
        """
        self._position = np.array(position, dtype=float)
        width = self.width
        label_offset = width / 2
        self.setPos(self._position[0] - width / 2, self._position[
            1] - width / 2)  # check if the origin is at the lower left corner, then this should be correct, else to be modified !!!
        self.label.setPos(self._position[0] + label_offset, self._position[1] + label_offset)
        return

    def set_name(self, name):
        """
        Set the roi_name of the marker and update tha label accordingly.

        @param str name:
        """
        self._roi_name = name
        self.label.setText(self._roi_name)
        return

    def set_width(self, width):
        """
        Set the size of the marker and reposition itself and the label to center it again.

        @param float width: Width of the square 
        """
        label_offset = width / 2  # to adjust
        self.setSize((width, width))
        self.setPos(self.position[0] - width / 2, self.position[1] - width / 2)
        self.label.setPos(self.position[0] + label_offset, self.position[1] + label_offset)
        return

    def select(self):
        """
        Set the markers _selected flag to True and change the marker appearance according to
        RoiMarker.select_pen.
        """
        self._selected = True
        self.setPen(self.select_pen)
        self.label.setColor(self.select_pen['color'])
        return

    def deselect(self):
        """
        Set the markers _selected flag to False and change the marker appearance according to
        RoiMarker.default_pen.
        """
        self._selected = False
        self.setPen(self.default_pen)
        self.label.setColor(self.default_pen['color'])
        return


# class representing the marker for the current stage position
class StageMarker(pg.RectROI):
    """
    Creates a square as marker for the stage.

    @param float[2] pos: The (x, y) position of the stage center.
    @param **args: All extra keyword arguments are passed to ROI()

    Have a look at:
    http://www.pyqtgraph.org/documentation/graphicsItems/roi.html
    """
    default_pen = {'color': '0FF', 'width': 2}  # color settings

    def __init__(self, position, width, view_widget=None, **kwargs):
        """
        @param position:
        @param width:
        @param view_widget:
        @param kwargs:
        """
        self._view_widget = view_widget
        self._position = np.array(position, dtype=float)
        size = (width, width)
        super().__init__(pos=self._position, size=size, pen=self.default_pen, **kwargs)
        self.aspectLocked = True
        self.label = pg.TextItem(text='Stage',
                                 anchor=(0, 1),
                                 color=self.default_pen['color'])
        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)
        self.set_position(self._position)
        return

    @property
    def width(self):
        return self.size()[0]

    @property
    def position(self):
        return self._position

    def add_to_view_widget(self, view_widget=None):
        if view_widget is not None:
            self._view_widget = view_widget
        self._view_widget.addItem(self)
        self._view_widget.addItem(self.label)
        return

    def delete_from_view_widget(self, view_widget=None):
        if view_widget is not None:
            self._view_widget = view_widget
        self._view_widget.removeItem(self.label)
        self._view_widget.removeItem(self)
        return

    def set_position(self, position):
        """
        Sets the position and centers the marker on that position.
        Also positions the label accordingly.

        @param float[2] position: The (x,y) center position of the stage marker
        """
        self._position = np.array(position, dtype=float)
        width = self.width
        label_offset = 0
        self.setPos(self._position[0] - width / 2,
                    self._position[1] - width / 2)  # draw the marker from the lower left corner of the square
        self.label.setPos(self._position[0] + label_offset, self._position[1] + label_offset)
        return

    def set_width(self, width):
        """
        Set the size of the marker and reposition itself and the label to center it again.

        @param float width: Width of the square
        """
        label_offset = 0
        self.setSize((width, width))
        self.setPos(self.position[0] - width / 2, self.position[1] - width / 2)
        self.label.setPos(self.position[0] + label_offset, self.position[1] + label_offset)
        return


class MosaicSettingDialog(QtWidgets.QDialog):
    """ Create the SettingsDialog window, based on the corresponding *.ui file."""

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_mosaic_settings.ui')

        # Load it
        super(MosaicSettingDialog, self).__init__()
        uic.loadUi(ui_file, self)


class RoiMainWindow(QtWidgets.QMainWindow):
    """ Create the Mainwindow from the ui.file
    """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_roi_gui.ui')

        # Load it
        super(RoiMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()


class RoiGUI(GUIBase):
    """ This is the GUI Class for Roi selection
    """
    # declare connectors
    roi_logic = Connector(interface='RoiLogic')
    
    # set the default save path for roi lists from config
    default_path = ConfigOption('default_path', missing='warn')
    # set the size of the stage marker
    stagemarker_width = ConfigOption('stagemarker_width', 50, missing='info')

    # declare signals
    sigRoiWidthChanged = QtCore.Signal(float)
    sigRoiListNameChanged = QtCore.Signal(str)
    sigStartTracking = QtCore.Signal()
    sigStopTracking = QtCore.Signal()
    sigAddInterpolation = QtCore.Signal(float)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self._mw = None  # QMainWindow handle
        self.roi_image = None  # ScanPlotImage (custom child of pyqtgraph PlotImage) for ROI overview image
        self._markers = {}  # dict to hold handles for the ROI markers
        self._mouse_moved_proxy = None  # Signal proxy to limit mousMoved event rate
        self.stagemarker = None

    def on_activate(self):
        """
        Initializes the overall GUI, and establishes the connectors.
        """
        self._markers = {}  # already initialized in init so maybe remove it here..

        self._mw = RoiMainWindow()

        
        # set the default save path before validator is applied: make sure that config is correct
        self._mw.save_path_LineEdit.setText(self.default_path)
        # Add validator to LineEdits
        self._mw.roi_list_name_LineEdit.setValidator(NameValidator())
        self._mw.save_path_LineEdit.setValidator(NameValidator(path=True))

        # Initialize plot
        self.__init_roi_map_image()

        # Initialize ROIs
        self._update_rois(self.roi_logic().roi_positions)
        # Initialize ROI list name
        self._update_roi_list_name(self.roi_logic().roi_list_name)

        # Initialize ROI width
        self._update_roi_width(self.roi_logic().roi_width)

        # add the stage marker
        stage_pos = self.roi_logic().stage_position[:2]
        self._add_stage_marker(stage_pos)

        # Distance Measurement: # to be added later
        # Introducing a SignalProxy will limit the rate of signals that get fired.
        self._mouse_moved_proxy = pg.SignalProxy(signal=self.roi_image.scene().sigMouseMoved,
                                                 rateLimit=30,
                                                 slot=self.mouse_moved_callback)

        # place this here so that the initialized values can be retrieved for the mosaic dialog
        self.initMosaicSettingsUI()  # initialize the Mosaic settings window in the options menu
        
        # Connect signals
        self.__connect_internal_signals()
        self.__connect_update_signals_from_logic()
        self.__connect_control_signals_to_logic()

        self._mw.show()

    def on_deactivate(self):
        """
        De-initialisation performed during deactivation of the module.
        """
        self.__disconnect_control_signals_to_logic()
        self.__disconnect_update_signals_from_logic()
        self.__disconnect_internal_signals()
        self._mw.close()

    # is it needed to have the camera image superposed with the roi markers ? 
    # in a first version: just keep the overview with the roi markers without camera image, comment everything camera image related..    
    def __init_roi_map_image(self):
        """ Initialize the ROI map """
        self.roi_image = ScanImageItem(axisOrder='row-major')
        self._mw.roi_map_ViewWidget.addItem(self.roi_image)
        self._mw.roi_map_ViewWidget.setLabel('bottom', 'x position')  # units='um'  check units ..
        self._mw.roi_map_ViewWidget.setLabel('left', 'y position')  # , units='um
        self._mw.roi_map_ViewWidget.setAspectLocked(lock=True, ratio=1.0)
        #        # Get camera image from logic and update initialize plot
        # self._update_cam_image(self.roi_logic().roi_list_cam_image, self.roi_logic().roi_list_cam_image_extent)

    def __connect_update_signals_from_logic(self):
        """ establish the connections of signals emitted in logic module """
        self.roi_logic().sigRoiUpdated.connect(self.update_roi, QtCore.Qt.QueuedConnection)
        self.roi_logic().sigActiveRoiUpdated.connect(self.update_active_roi, QtCore.Qt.QueuedConnection)
        self.roi_logic().sigRoiListUpdated.connect(self.update_roi_list, QtCore.Qt.QueuedConnection)
        self.roi_logic().sigWidthUpdated.connect(self._update_roi_width, QtCore.Qt.QueuedConnection)
        self.roi_logic().sigStageMoved.connect(self.update_stage_position, QtCore.Qt.QueuedConnection)
        self.roi_logic().sigUpdateStagePosition.connect(self.update_stage_position, QtCore.Qt.QueuedConnection)

    def __disconnect_update_signals_from_logic(self):
        """ disconnect signals emitted in logic module """
        self.roi_logic().sigRoiUpdated.disconnect()
        self.roi_logic().sigActiveRoiUpdated.disconnect()
        self.roi_logic().sigRoiListUpdated.disconnect()
        self.roi_logic().sigWidthUpdated.disconnect()
        self.roi_logic().sigStageMoved.disconnect()
        self.roi_logic().sigUpdateStagePosition.disconnect()

    def __connect_control_signals_to_logic(self):
        """ establish the connections of signals emitted with slots in logic module """
        # roi toolbar actions
        self._mw.new_roi_Action.triggered.connect(self.roi_logic().add_roi, QtCore.Qt.QueuedConnection)
        self._mw.go_to_roi_Action.triggered.connect(self.roi_logic().go_to_roi, QtCore.Qt.QueuedConnection)
        self._mw.delete_roi_Action.triggered.connect(self.roi_logic().delete_roi, QtCore.Qt.QueuedConnection)
        self._mw.add_interpolation_Action.triggered.connect(self.add_interpolation_clicked, QtCore.Qt.QueuedConnection) # this might go to connect internal signals
       


        # roi list toolbar actions
        self._mw.new_list_Action.triggered.connect(self.roi_logic().reset_roi_list, QtCore.Qt.QueuedConnection)
        self._mw.discard_all_roi_Action.triggered.connect(self.delete_all_roi_clicked,
                                                          QtCore.Qt.QueuedConnection)  # this might go to __connect_internal_signals ..

        # signals
        self.sigRoiWidthChanged.connect(self.roi_logic().set_roi_width)
        self.sigRoiListNameChanged.connect(self.roi_logic().rename_roi_list, QtCore.Qt.QueuedConnection)
        self._mw.active_roi_ComboBox.activated[str].connect(self.roi_logic().set_active_roi, QtCore.Qt.QueuedConnection)
        self.sigAddInterpolation.connect(self.roi_logic().add_interpolation, QtCore.Qt.QueuedConnection)
        self.sigStartTracking.connect(self.roi_logic().start_tracking)
        self.sigStopTracking.connect(self.roi_logic().stop_tracking)

        # something similar will be needed : to add later !!!!
        # self._mw.get_confocal_image_PushButton.clicked.connect(self.poimanagerlogic().set_scan_image, QtCore.Qt.QueuedConnection)

    def __disconnect_control_signals_to_logic(self):
        """ disconnect signals from their slots in logic module """
        self._mw.new_roi_Action.triggered.disconnect()
        self._mw.go_to_roi_Action.triggered.disconnect()
        self._mw.delete_roi_Action.triggered.disconnect()
        self._mw.add_interpolation_Action.triggered.disconnect()

        self._mw.new_list_Action.triggered.disconnect()
        self._mw.active_roi_ComboBox.activated[str].disconnect()
        self.sigAddInterpolation.disconnect()
        self.sigStartTracking.disconnect()
        self.sigStopTracking.disconnect()

        # self._mw.get_confocal_image_PushButton.clicked.disconnect()

        self.sigRoiWidthChanged.disconnect()
        self.sigRoiListNameChanged.disconnect()
        for marker in self._markers.values():
            marker.sigRoiSelected.disconnect()

    def __connect_internal_signals(self):
        """ connect signals with slots within this module """
        self._mw.roi_width_doubleSpinBox.editingFinished.connect(self.roi_width_changed)  # just emit one signal when finished and not at each modification of the value (valueChanged)
        self._mw.save_list_Action.triggered.connect(self.save_roi_list)
        self._mw.load_list_Action.triggered.connect(self.load_roi_list)
        # tracking mode toolbutton
        self._mw.tracking_mode_Action.setEnabled(True)
        self._mw.tracking_mode_Action.setChecked(self.roi_logic().tracking)
        self._mw.tracking_mode_Action.triggered.connect(self.tracking_mode_clicked)

        # file menu
        self._mw.close_MenuAction.triggered.connect(self._mw.close)
        # options menu
        self._mw.mosaic_scan_MenuAction.triggered.connect(self.open_mosaic_settings)

    def __disconnect_internal_signals(self):
        """ disconnect signals from slots within this module """
        self._mw.roi_width_doubleSpinBox.editingFinished.disconnect()
        self._mw.save_list_Action.triggered.disconnect()
        self._mw.load_list_Action.triggered.disconnect()
        self._mw.tracking_mode_Action.triggered.disconnect()
        self._mw.close_MenuAction.triggered.disconnect()
        self._mw.mosaic_scan_MenuAction.triggered.disconnect()

    def show(self):
        """Make main window visible and put it above all other windows. """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    # Initialisation of the mosaic settings windows in the options menu
    def initMosaicSettingsUI(self):
        """ Definition, configuration and initialisation of the mosaic settings GUI.

        """
        # Create the settings window
        self._mosaic_sd = MosaicSettingDialog()
        # Connect the action of the settings window with the code:
        self._mosaic_sd.accepted.connect(self.mosaic_update_settings)  # ok button
        self._mosaic_sd.rejected.connect(self.mosaic_default_settings)  # cancel button
        self._mosaic_sd.current_pos_CheckBox.stateChanged.connect(
            self.mosaic_position)  # current position checkbox updates position fields
        
        # set the default values
        self.mosaic_default_settings()

    # slots of the mosaic settings window
    def mosaic_update_settings(self):
        """ Write new settings from the gui to the roi logic 
        """
        self.roi_logic()._mosaic_x_start = self._mosaic_sd.x_pos_DSpinBox.value()
        self.roi_logic()._mosaic_y_start = self._mosaic_sd.y_pos_DSpinBox.value()
        self.roi_logic()._mosaic_roi_width = self._mosaic_sd.mosaic_roi_width_DSpinBox.value()
        self._mw.roi_width_doubleSpinBox.setValue(
            self._mosaic_sd.mosaic_roi_width_DSpinBox.value())  # synchronize the roi width spinboxes so that the marker is drawn correctly
        if self._mosaic_sd.mosaic_size1_RadioButton.isChecked():
            self.roi_logic()._mosaic_number_x = 9
            self.roi_logic()._mosaic_number_y = 9
        if self._mosaic_sd.mosaic_size2_RadioButton.isChecked():
            self.roi_logic()._mosaic_number_x = 25
            self.roi_logic()._mosaic_number_y = 25
        if self._mosaic_sd.mosaic_userdefined_RadioButton.isChecked():
            self.roi_logic()._mosaic_number_x = self._mosaic_sd.mosaic_width_SpinBox.value()
            self.roi_logic()._mosaic_number_y = self._mosaic_sd.mosaic_height_SpinBox.value()
        add_to_list = self._mosaic_sd.mosaic_add_to_list_CheckBox.isChecked()

        self.roi_logic().add_mosaic(x_center_pos=self.roi_logic()._mosaic_x_start,
                                    y_center_pos=self.roi_logic()._mosaic_y_start,
                                    z_pos = self.roi_logic().stage_position[2],
                                    roi_width=self.roi_logic()._mosaic_roi_width,
                                    width=self.roi_logic()._mosaic_number_x,
                                    height=self.roi_logic()._mosaic_number_y,
                                    add=add_to_list)

    def mosaic_default_settings(self):
        """ Restore default settings. 
        """
        # reset to default values
        # as an alternative, reset to the values that are still stored in logic attributes ? (= former settings?) to modify if .. 
        self._mosaic_sd.current_pos_CheckBox.setChecked(False)
        self._mosaic_sd.x_pos_DSpinBox.setValue(0)
        self._mosaic_sd.y_pos_DSpinBox.setValue(0)
        roi_width = self._mw.roi_width_doubleSpinBox.value()
        self._mosaic_sd.mosaic_roi_width_DSpinBox.setValue(roi_width)  
        self._mosaic_sd.mosaic_size1_RadioButton.setAutoExclusive(False)
        self._mosaic_sd.mosaic_size1_RadioButton.setChecked(False)
        self._mosaic_sd.mosaic_size1_RadioButton.setAutoExclusive(True)
        self._mosaic_sd.mosaic_size2_RadioButton.setAutoExclusive(False)
        self._mosaic_sd.mosaic_size2_RadioButton.setChecked(False)
        self._mosaic_sd.mosaic_size2_RadioButton.setAutoExclusive(True)
        self._mosaic_sd.mosaic_userdefined_RadioButton.setAutoExclusive(False)
        self._mosaic_sd.mosaic_userdefined_RadioButton.setChecked(False)
        self._mosaic_sd.mosaic_userdefined_RadioButton.setAutoExclusive(True)
        self._mosaic_sd.mosaic_add_to_list_CheckBox.setChecked(False)

    def mosaic_position(self):
        """ check state of the current position checkbox and handle position settings accordingly
        """
        if self._mosaic_sd.current_pos_CheckBox.isChecked():
            # get current stage position from logic and fill this in, then disable spinboxes
            self._mosaic_sd.x_pos_DSpinBox.setValue(self.roi_logic().stage_position[0])
            self._mosaic_sd.y_pos_DSpinBox.setValue(self.roi_logic().stage_position[1])
            self._mosaic_sd.x_pos_DSpinBox.setEnabled(False)
            self._mosaic_sd.y_pos_DSpinBox.setEnabled(False)
        else:
            self._mosaic_sd.x_pos_DSpinBox.setEnabled(True)
            self._mosaic_sd.y_pos_DSpinBox.setEnabled(True)

    # slot to open the mosaic settings window
    def open_mosaic_settings(self):
        """ Opens the settings menu. 
        """
        # retrieve the current position from the stage each time the dialog is opened and set the spinboxes accordingly
        self.mosaic_position()
        self._mosaic_sd.exec_()

    # to fix: unit display + bug when initializing a new list
    @QtCore.Slot(object)
    def mouse_moved_callback(self, event):
        """ Handles any mouse movements inside the image.
        @param event:   Event that signals the new mouse movement.
                       This should be of type QPointF.
        Gets the mouse position, converts it to a position scaled to the image axis
        and than calculates and updated the position to the current ROI.
        """

        # converts the absolute mouse position to a position relative to the axis
        mouse_pos = self.roi_image.getViewBox().mapSceneToView(event[0])
        # only calculate distance, if a ROI is selected
        active_roi = self.roi_logic().active_roi
        if active_roi:
            roi_pos = self.roi_logic().get_roi_position(active_roi)
            dx = ScaledFloat(mouse_pos.x() - roi_pos[0])
            dy = ScaledFloat(mouse_pos.y() - roi_pos[1])
            d_total = ScaledFloat(
                np.sqrt((mouse_pos.x() - roi_pos[0])**2 + (mouse_pos.y() - roi_pos[1])**2))
            self._mw.roi_distance_Label.setText(
                '{0:.2r} (dx = {1:.2r}, dy = {2:.2r})'.format(d_total, dx, dy))
        else:
            self._mw.roi_distance_Label.setText('? (?, ?)')
        pass

    @QtCore.Slot(dict)
    def update_roi_list(self, roi_dict):
        if not isinstance(roi_dict, dict):
            self.log.error('ROI parameters to update must be given in a single dictionary.')
            return

        if 'name' in roi_dict:
            self._update_roi_list_name(name=roi_dict['name'])
        # put this in comments because it will reset the image with a None type object and lead to an error in the distance measurement
        # to be reactivated when the possibility of a camera image overlay is established
        # if 'cam_image' in roi_dict and 'cam_image_extent' in roi_dict:
        #     self._update_cam_image(cam_image=roi_dict['cam_image'], cam_image_extent=roi_dict['cam_image_extent'])
        if 'rois' in roi_dict:
            self._update_rois(roi_dict=roi_dict['rois'])
        return

    @QtCore.Slot(str, str, np.ndarray)
    def update_roi(self, old_name, new_name, position):
        # Handle changed names and deleted/added POIs
        if old_name != new_name:
            self._mw.active_roi_ComboBox.blockSignals(True)
            # Remember current text
            text_active_roi = self._mw.active_roi_ComboBox.currentText()
            # sort ROI names and repopulate ComboBoxes
            self._mw.active_roi_ComboBox.clear()
            roi_names = natural_sort(self.roi_logic().roi_names)
            self._mw.active_roi_ComboBox.addItems(roi_names)
            if text_active_roi == old_name:
                self._mw.active_roi_ComboBox.setCurrentText(new_name)
            else:
                self._mw.active_roi_ComboBox.setCurrentText(text_active_roi)
            self._mw.active_roi_ComboBox.blockSignals(False)

        # Delete/add/update ROI marker to image
        if not old_name:
            # ROI has been added
            self._add_roi_marker(name=new_name, position=position)
        elif not new_name:
            # ROI has been deleted
            self._remove_roi_marker(name=old_name)
        else:
            # ROI has been renamed and/or changed position
            size = self.roi_logic.roi_width  # check if width should be changed again
            self._markers[old_name].set_name(new_name)
            self._markers[new_name] = self._markers.pop(old_name)
            self._markers[new_name].setSize((size, size))
            self._markers[new_name].set_position(position[:2])

        active_roi = self._mw.active_roi_ComboBox.currentText()
        if active_roi:
            self._markers[active_roi].select()

    @QtCore.Slot(str)
    def update_active_roi(self, name):

        # Deselect current marker
        for marker in self._markers.values():
            if marker.selected:
                marker.deselect()
                break

        # Unselect ROI if name is None or empty str
        self._mw.active_roi_ComboBox.blockSignals(True)
        if not name:
            self._mw.active_roi_ComboBox.setCurrentIndex(-1)
        else:
            self._mw.active_roi_ComboBox.setCurrentText(name)
        self._mw.active_roi_ComboBox.blockSignals(False)

        if name:
            active_roi_pos = self.roi_logic().get_roi_position(name)
            self._mw.roi_coords_label.setText(
                'x={0}, y={1}, z={2}'.format(active_roi_pos[0], active_roi_pos[1], active_roi_pos[2])
            )
        else:
            active_roi_pos = np.zeros(3)
            self._mw.roi_coords_label.setText('')

        if name in self._markers:
            self._markers[name].set_width(self.roi_logic().roi_width)
            self._markers[name].select()

    @QtCore.Slot()
    def roi_width_changed(self):
        self.sigRoiWidthChanged.emit(self._mw.roi_width_doubleSpinBox.value())
        return

    @QtCore.Slot()
    def roi_list_name_changed(self):
        """ Set the name of the current roi list."""
        self.sigRoiListNameChanged.emit(self._mw.roi_list_name_LineEdit.text())

    # To do: add a Validator on the save_path_LineEdit.
    @QtCore.Slot()
    def save_roi_list(self):
        """ Save ROI list to file, using filepath and filename given on the GUI
        """
        roi_list_name = self._mw.roi_list_name_LineEdit.text()
        path = self._mw.save_path_LineEdit.text()
        self.roi_logic().rename_roi_list(roi_list_name)
        self.roi_logic().save_roi_list(path, roi_list_name)

    @QtCore.Slot()
    def load_roi_list(self):
        data_directory = self._mw.save_path_LineEdit.text()  # we will use this as default location to look for files
        this_file = QtWidgets.QFileDialog.getOpenFileName(self._mw,
                                                          'Open ROI list',
                                                          data_directory,
                                                          'json files (*.json)')[0]
        if this_file:
            self.roi_logic().load_roi_list(complete_path=this_file)

    @QtCore.Slot()
    def delete_all_roi_clicked(self):
        result = QtWidgets.QMessageBox.question(self._mw, 'Qudi: Delete all ROIs?',
                                                'Are you sure to delete all ROIs?',
                                                QtWidgets.QMessageBox.Yes,
                                                QtWidgets.QMessageBox.No)
        if result == QtWidgets.QMessageBox.Yes:
            self.roi_logic().delete_all_roi()
            
    @QtCore.Slot()
    def add_interpolation_clicked(self):
        roi_distance = self._mw.roi_width_doubleSpinBox.value()
        self.sigAddInterpolation.emit(roi_distance)

    def _update_cam_image(self, cam_image, cam_image_extent):
        """

        @param cam_image:
        @param cam_image_extent:
        """
        if cam_image is None or cam_image_extent is None:
            self._mw.roi_map_ViewWidget.removeItem(self.roi_image)
            return
        elif self.roi_image not in self._mw.roi_map_ViewWidget.items():
            self._mw.roi_map_ViewWidget.addItem(self.roi_image)
        self.roi_image.setImage(image=cam_image)
        (x_min, x_max), (y_min, y_max) = cam_image_extent
        self.roi_image.getViewBox().enableAutoRange()
        self.roi_image.setRect(QtCore.QRectF(x_min, y_min, x_max - x_min, y_max - y_min))

    def _update_roi_list_name(self, name):
        self._mw.roi_list_name_LineEdit.blockSignals(True)
        self._mw.roi_list_name_LineEdit.setText(name)
        self._mw.roi_list_name_LineEdit.blockSignals(False)

    def _update_roi_width(self, width):
        self._mw.roi_width_doubleSpinBox.setValue(width)

    def _update_rois(self, roi_dict):
        """ Populate the dropdown box for selecting a roi. """
        self._mw.active_roi_ComboBox.blockSignals(True)

        self._mw.active_roi_ComboBox.clear()

        roi_names = natural_sort(roi_dict)
        self._mw.active_roi_ComboBox.addItems(roi_names)

        # Get two lists of ROI names. One of those to delete and one of those to add
        old_roi_names = set(self._markers)
        new_roi_names = set(roi_names)
        names_to_delete = list(old_roi_names.difference(new_roi_names))
        names_to_add = list(new_roi_names.difference(old_roi_names))

        # Delete markers accordingly
        for name in names_to_delete:
            self._remove_roi_marker(name)
        # Update positions of all remaining markers
        size = self.roi_logic().roi_width  # self.roi_logic().optimise_xy_size * np.sqrt(2)
        for name, marker in self._markers.items():
            marker.setSize((size, size))
            marker.set_position(roi_dict[name])
        # Add new markers
        for name in names_to_add:
            self._add_roi_marker(name=name, position=roi_dict[name])

        # If there is no active ROI, set the combobox to nothing (-1)
        active_roi = self.roi_logic().active_roi
        if active_roi in roi_names:
            self._mw.active_roi_ComboBox.setCurrentText(active_roi)
            self._markers[active_roi].select()
            active_roi_pos = roi_dict[active_roi]

            self._mw.roi_coords_label.setText(
                'x={0}, y={1}, z={2}'.format(active_roi_pos[0], active_roi_pos[1], active_roi_pos[2])
            )
        else:
            self._mw.active_roi_ComboBox.setCurrentIndex(-1)
            self._mw.roi_coords_label.setText('')  # no roi active

        self._mw.active_roi_ComboBox.blockSignals(False)

    def _add_roi_marker(self, name, position):
        """ Add a square ROI marker to the roi overview image. """
        if name:
            if name in self._markers:
                self.log.error('Unable to add ROI marker to image. ROI marker already present.')
                return
            marker = RoiMarker(position=position[:2],
                               view_widget=self._mw.roi_map_ViewWidget,
                               roi_name=name,
                               width=self.roi_logic()._roi_width,
                               movable=False)
            # Add to the roi overview image widget
            marker.add_to_view_widget()
            # remove the handle that can be used to resize the roi as we do not want this functionality
            marker.removeHandle(marker.getHandles()[0])
            marker.sigRoiSelected.connect(self.roi_logic().set_active_roi, QtCore.Qt.QueuedConnection)
            self._markers[name] = marker

    def _remove_roi_marker(self, name):
        """ Remove the ROI marker for a ROI that was deleted. """
        if name in self._markers:
            self._markers[name].delete_from_view_widget()
            self._markers[name].sigRoiSelected.disconnect()
            del self._markers[name]

    def _add_stage_marker(self, position=(0, 0)):
        """ Add a square marker for the current stage position to the roi overview image """
        try:
            stagemarker = StageMarker(position=position,
                                      view_widget=self._mw.roi_map_ViewWidget,
                                      width=self.stagemarker_width,  # to be defined in config
                                      movable=False)
            # add the marker to the roi overview image
            stagemarker.add_to_view_widget()
            # remove the scaling handle
            stagemarker.removeHandle(stagemarker.getHandles()[0])
            self.stagemarker = stagemarker
        except Exception:
            self.log.warn('Unable to add stage marker to image')

    @QtCore.Slot(np.ndarray)
    def update_stage_position(self, position):
        """ updates the textlabel with the current stage position and moves the stage marker """
        self._mw.stage_position_Label.setText('x={0}, y={1}, z={2}'.format(position[0], position[1], position[2]))
        self.stagemarker.set_position(position)

    @QtCore.Slot()
    def tracking_mode_clicked(self):
        """ handles the state of the tracking mode toolbutton and emits a signal """
        if self.roi_logic().tracking:  # tracking mode already on
            self._mw.tracking_mode_Action.setText('Tracking mode')
            self._mw.tracking_mode_Action.setToolTip('Start tracking mode')
            self.sigStopTracking.emit()
        else:  # tracking mode off
            self._mw.tracking_mode_Action.setText('Tracking mode off')
            self._mw.tracking_mode_Action.setToolTip('Stop tracking mode')
            self.sigStartTracking.emit()
