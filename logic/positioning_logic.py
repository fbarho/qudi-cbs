# -*- coding: utf-8 -*-
"""
Created on Thu Mars 4 2021

@author: fbarho

This module contains the logic to control the positioning system for the probes
"""
from time import sleep
from qtpy import QtCore
from logic.generic_logic import GenericLogic
from core.configoption import ConfigOption
from core.connector import Connector


class WorkerSignals(QtCore.QObject):
    """ Defines the signals available from a running worker thread """

    sigxyStepFinished = QtCore.Signal(dict, dict)
    sigzStepFinished = QtCore.Signal(dict)


class xyMoveWorker(QtCore.QRunnable):
    """ Worker thread to wait for the end of a translation stage movement but which preserves the possibility to abort the movement

    The worker handles only the waiting time, and emits a signal that serves to trigger the update indicators """

    def __init__(self, pos_dict_xy, pos_dict_z):
        super(xyMoveWorker, self).__init__()
        self.signals = WorkerSignals()
        self.pos_dict_xy = pos_dict_xy
        self.pos_dict_z = pos_dict_z

    @QtCore.Slot()
    def run(self):
        """ """
        sleep(0.5)  # 0.5 second as time constant
        self.signals.sigxyStepFinished.emit(self.pos_dict_xy, self.pos_dict_z)


class zMoveWorker(QtCore.QRunnable):
    """ Worker thread to wait for the end of a translation stage movement but which preserves the possibility to abort the movement

    The worker handles only the waiting time, and emits a signal that serves to trigger the update indicators """

    def __init__(self, pos_dict_z):
        super(zMoveWorker, self).__init__()
        self.signals = WorkerSignals()
        self.pos_dict_z = pos_dict_z

    @QtCore.Slot()
    def run(self):
        """ """
        sleep(0.5)  # 0.5 second as time constant
        self.signals.sigzStepFinished.emit(self.pos_dict_z)


class PositioningLogic(GenericLogic):
    """
    Class containing the logic to control the 3 axis positioning system for the probes

    Example config for copy-paste:

    positioning_logic:
        module.Class: 'positioning_logic.PositioningLogic'
        z_safety_position: 0
        num_x: 10
        num_y: 10
        first_axis: 'X axis'
        second_axis: 'Y axis'
        third_axis: 'Z axis'
        connect:
            stage: 'motor_dummy'
    """
    # declare connectors
    stage = Connector(interface='MotorInterface')

    # signals
    sigUpdatePosition = QtCore.Signal(tuple)  # send during movement to update coordinates on the GUI
    sigStageMoved = QtCore.Signal(tuple)  # new stage coordinates given  # tuple contains the new stage position (x, y, z)
    sigStageMovedToTarget = QtCore.Signal(tuple, int)  # target position (number of probe) given # tuple contains the new stage position (x, y, z), int is the target position
    sigOriginDefined = QtCore.Signal()
    sigStageStopped = QtCore.Signal(tuple)
    sigDisablePositioningActions = QtCore.Signal()
    sigEnablePositioningActions = QtCore.Signal()

    # attributes
    move_stage = False  # flag
    go_to_target = False  # flag
    target_position = 0  # will be overwritten when movement is started using the start_move_to_target method


    moving = False
    origin = None
    delta_x = 14.9  # in mm # to be defined by config later
    delta_y = 14.9  # in mm # to be defined by config later
    z_safety_pos = ConfigOption('z_safety_position', 0, missing='warn')
    first_axis_label = ConfigOption('first_axis', 'X axis')
    second_axis_label = ConfigOption('second_axis', 'Y axis')
    third_axis_label = ConfigOption('third_axis', 'Z axis')
    # num_x = ConfigOption('num_x', 10, missing='warn')  # number of available probe positions in x direction
    # num_y = ConfigOption('num_y', 10, missing='warn')  # number of available probe positions in y direction

    _probe_coordinates_dict = {}  # contains the mapping of probe numbers to their coordinates on the grid  {1: (0, 0), ...}
    _probe_xy_position_dict = {}  # contains the mapping the physical xy positions of the probes to their probe number  {(12.0, 10.0): 1, ..}

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self.threadpool = QtCore.QThreadPool()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # connector
        self._stage = self.stage()

        # calculate the probe grid coordinates
        self._probe_coordinates_dict = self.position_to_coordinates()

    def on_deactivate(self):
        """ Perform required deactivation. """
        pass

    def position_to_coordinates(self):
        """ This method generates a mapping of probe positions to x-y coordinates on a serpentine grid
        (just grid points, no metric coordinates):
        1: (0, 0), 2: (0, 1), 3: (0, 2), etc.. values in (x, y) order, y being the index that varies rapidly
        """
        num_x = 10  # self.num_x  # number of positions in x direction
        num_y = 10  # self.num_y  # number of positions in y direction
        max_probes = num_x * num_y
        # create the coordinate grid
        list_even = [(x, y) for x in range(num_x) for y in range(num_y) if x % 2 == 0]
        list_odd = [(x, y) for x in range(num_x) for y in reversed(range(num_y)) if x % 2 != 0]
        list_all = list_even + list_odd
        coords = sorted(list_all, key=self.sort_first)

        # associate a grid point to each probe position
        coord_dict = {}
        for key in range(max_probes):
            coord_dict[key+1] = coords[key]
        return coord_dict

    def sort_first(self, val):
        """ helper function for sorting a list of tuples by the first element of each tuple,
        used for setting up the serpentine grid

        @returns: the first element of value (in the context here, value is a 2dim tuple (x, y))
        """
        return val[0]

    def get_position(self):
        """ This method retrieves the current stage position from the hardware and does formatting of the return value.

        @returns: float tuple: position (x, y, z)
        """
        position = self._stage.get_pos()  # returns a dictionary {'x': x_pos, 'y': y_pos, 'z': z_pos}
        position = tuple([*position.values()])  # convert into tuple
        return position

    def start_move_stage(self, position):
        """ This method allows to perform a movement of the 3 axis stage to the specified stage position.
        A movement to the z safety position is performed first, before doing the xy positioning.
        xy positioning is started from this method, then a loop is entered to make a call to abort movement possible.
        Finally, the z movement is done using again a loop.

        @param: float tuple position: (x, y, z) position
        """
        if len(position) != 3:
            self.log.warn('Stage position to set must be iterable of length 3. No movement done.')

        else:
            self.move_stage = True  # flag indicating later on that the translation stage movement was initiated by start_move_stage method
            self.moving = True

            # do not allow descending z below safety position when operating by move stage (x y z coordinates given instead of target position)
            if position[2] > self.z_safety_pos:
                self.log.warning('z movement will not be made. z out of allowed range.')
                # redefine position using the z safety position instead of the user defined z position
                x = position[0]
                y = position[1]
                z = self.z_safety_pos
                position = (x, y, z)

            axis_label = ('x', 'y', 'z')
            pos_dict = dict([*zip(axis_label, position)])
            # separate movement into xy and z movements for safety
            pos_dict_xy = {key: pos_dict[key] for key in ['x', 'y']}
            pos_dict_z = {key: pos_dict[key] for key in ['z']}
            self._stage.move_abs({'z': self.z_safety_pos})  # move to z safety position before making the xy movement
            ready = self._stage.get_status('z')['z']
            while not ready:
                sleep(0.5)
                ready = self._stage.get_status('z')['z']
                # or use wait for idle (waitontarget) as non interface method .. or add it to the interface

            # start the xy movement of the translation stage
            self._stage.move_abs(pos_dict_xy)

            # start a worker thread to monitor the xy movement
            worker = xyMoveWorker(pos_dict_xy, pos_dict_z)
            worker.signals.sigxyStepFinished.connect(self.move_xy_stage_loop)
            self.threadpool.start(worker)

    def move_xy_stage_loop(self, pos_dict_xy, pos_dict_z):
        # compare the current position with the target position
        new_position = self.get_position()
        x_pos = new_position[0]
        y_pos = new_position[1]
        self.sigUpdatePosition.emit(new_position)

        if self.moving:  # make sure that movement has not been aborted
            # if x_pos != pos_dict_xy['x'] or y_pos != pos_dict_xy['y']:
            if (abs(x_pos - pos_dict_xy['x']) > 0.001) or (abs(y_pos - pos_dict_xy['y']) > 0.001):
                # enter in a loop until xy position reached
                worker = xyMoveWorker(pos_dict_xy, pos_dict_z)
                worker.signals.sigxyStepFinished.connect(self.move_xy_stage_loop)
                self.threadpool.start(worker)
            else:
                # xy position reached, start now the z movement
                self.start_move_z_stage(pos_dict_z)

    def start_move_z_stage(self, pos_dict_z):
        # start the z movement of the translation stage
        self._stage.move_abs(pos_dict_z)

        # start a worker thread to monitor the xy movement
        worker = zMoveWorker(pos_dict_z)
        worker.signals.sigzStepFinished.connect(self.move_z_stage_loop)
        self.threadpool.start(worker)

    def move_z_stage_loop(self, pos_dict_z):
        """  """
        # compare the current position with the target position
        new_position = self.get_position()
        z_pos = new_position[2]
        self.sigUpdatePosition.emit(new_position)

        if self.moving:  # make sure that movement has not been aborted
            if z_pos != pos_dict_z['z']:
                # enter in a loop until z position reached
                worker = zMoveWorker(pos_dict_z)
                worker.signals.sigzStepFinished.connect(self.move_z_stage_loop)
                self.threadpool.start(worker)

            else:
                self.moving = False
                new_pos = self.get_position()
                # self.log.info(new_pos)

                # send the signal to the GUI depending on which button triggered the stage movement
                if self.move_stage:
                    self.sigStageMoved.emit(new_pos)
                    self.move_stage = False
                elif self.go_to_target:
                    self.sigStageMovedToTarget.emit(new_pos, self.target_position)
                    self.go_to_target = False
                else:
                    pass

    def start_move_to_target(self, target_position):
        """ This method allows to perform a movement of the 3 axis stage to the specified position given by the
        target probe number.
        A movement to the z safety position is performed first, before doing the xy positioning.
        Then, z is moved to its specified value.
        Emits a signal when finished and sends the new position and the reached target number

        @param: int target_position: number of the target probe
        """
        if not self.origin:
            self.log.warn('Move to target is not possible. Please define the origin')
            return

        self.go_to_target = True  # flag indicating later on that the translation stage movement was initiated by start_move_to_target method
        self.target_position = target_position  # keep this variable accessible until movement is finished
        self.moving = True
        # lets assume equidistant distribution  # to be modified with real grid distribution.
        # this could be modified. we could use a lookup dictionary containing the xyz positions directly.
        # so we don't need to recalculate them each time.
        grid_coordinates = self.get_coordinates(target_position)
        x_pos = self.origin[0] + grid_coordinates[0] * self.delta_x + grid_coordinates[1] * -0.11  # last term: correction term
        y_pos = self.origin[1] + grid_coordinates[1] * self.delta_y + grid_coordinates[0] * -0.055
        z_pos = self.origin[2]
        position = (x_pos, y_pos, z_pos)
        axis_label = ('x', 'y', 'z')
        pos_dict = dict([*zip(axis_label, position)])
        # separate into xy and z movements
        pos_dict_xy = {key: pos_dict[key] for key in ['x', 'y']}
        pos_dict_z = {key: pos_dict[key] for key in ['z']}

        # do the z safety movement
        self._stage.move_abs({'z': self.z_safety_pos})
        ready = self._stage.get_status('z')['z']
        while not ready:
            sleep(0.5)
            ready = self._stage.get_status('z')['z']
            # or use wait for idle (waitontarget) as non interface method .. or add it to the interface

        # start the xy movement of the translation stage
        self._stage.move_abs(pos_dict_xy)

        # start a worker thread to monitor the xy movement
        worker = xyMoveWorker(pos_dict_xy, pos_dict_z)
        worker.signals.sigxyStepFinished.connect(self.move_xy_stage_loop)
        self.threadpool.start(worker)

    def get_coordinates(self, target):
        """ This method returns the (x, y) grid coordinates associated to the target position

        @param: int target: target position of the probe
        @returns: int tuple (x, y)
        """
        return self._probe_coordinates_dict[target]

    def abort_movement(self):
        """ This method is called to abort a stage movement (either initiated by move_stage or move_to_target)
        Sends a signal to indicate that the stage was stopped and the current reached position. """
        self.moving = False
        self._stage.abort()
        # reset all flags
        self.move_stage = False
        self.go_to_target = False
        self.target_position = 1

        self.log.info('Movement aborted!')
        pos = self.get_position()
        self.sigStageStopped.emit(pos)

    def set_origin(self, origin):
        """ Defines the origin = the metric coordinates of the position1 of the grid with the probes.
        Sends a signal to indicate that the origin was set.
        """
        self.origin = origin
        # create a dictionary that allows to access the position number of the probe by its metric coordinates
        probe_xy_position_dict = {}
        for key in self._probe_coordinates_dict:
            x_pos = self._probe_coordinates_dict[key][0] * self.delta_x + self.origin[0] + self._probe_coordinates_dict[key][1] * -0.11
            y_pos = self._probe_coordinates_dict[key][1] * self.delta_y + self.origin[1] + self._probe_coordinates_dict[key][0] * -0.055
            position = (x_pos, y_pos)
            probe_xy_position_dict[key] = position
        # invert the keys and values in the dictionary because we want to access the target position by the key
        inv_dict = dict((v, k) for k, v in probe_xy_position_dict.items())
        self._probe_xy_position_dict = inv_dict
        self.sigOriginDefined.emit()

    def disable_positioning_actions(self):
        """ This method provides a security to avoid using the positioning action buttons on GUI, for example during Tasks. """
        self.sigDisablePositioningActions.emit()

    def enable_positioning_actions(self):
        """ This method resets positioning action button on GUI to callable state, for example after Tasks. """
        self.sigEnablePositioningActions.emit()

