# -*- coding: utf-8 -*-
"""
Created on Thu Mars 4 2021

@author: fbarho

This module contains the logic to control the positioning system for the merfish probes
"""
from time import sleep
from qtpy import QtCore
from logic.generic_logic import GenericLogic
from core.configoption import ConfigOption
from core.connector import Connector


class PositioningLogic(GenericLogic):
    """
    Class containing the logic to control the 3 axis positioning system for the merfish probes

    Example config for copy-paste:

    positioning_logic:
        module.Class: 'positioning_logic.PositioningLogic'
        z_safety_position: 0
        num_x: 10
        num_y: 10
        connect:
            stage: 'motor_dummy'
    """
    # declare connectors
    stage = Connector(interface='MotorInterface')

    # signals
    sigStageMoved = QtCore.Signal(tuple)  # new stage coordinates given  # tuple contains the new stage position (x, y, z)
    sigStageMovedToTarget = QtCore.Signal(tuple, int)  # target position (number of merfish probe) given # tuple contains the new stage position (x, y, z), int is the target position
    sigOriginDefined = QtCore.Signal()
    sigStageStopped = QtCore.Signal(tuple)

    # attributes
    moving = False
    origin = None
    delta_x = 2  # in mm # to be defined by config later
    delta_y = 2  # in mm # to be defined by config later
    z_safety_pos = ConfigOption('z_safety_position', 0, missing='warn')
    num_x = ConfigOption('num_x', 10, missing='warn')  # number of available probe positions in x direction
    num_y = ConfigOption('num_y', 10, missing='warn')  # number of available probe positions in y direction

    _probe_coordinates_dict = {}  # contains the mapping of probe numbers to their coordinates on the grid  {1: (0, 0), ...}
    _probe_xy_position_dict = {}  # contains the mapping the physical xy positions of the probes to their probe number  {(12.0, 10.0): 1, ..}

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # connector
        self._stage = self.stage()

        # calculate the merfish probe grid coordinates
        self._probe_coordinates_dict = self.position_to_coordinates()

    def on_deactivate(self):
        """ Perform required deactivation. """
        pass

    def position_to_coordinates(self):
        """ This method generates a mapping of merfish probe positions to x-y coordinates on a grid
        (just grid points, no metric coordinates):
        1: (0, 0), 2: (1, 0), 3: (2, 0), etc.. values in (x, y) order, x being the index that varies rapidly
        """
        num_x = self.num_x  # number of positions in x direction
        num_y = self.num_y  # number of positions in y direction
        max_probes = num_x * num_y
        # create the coordinate grid
        list_even = [(x, y) for y in range(num_y) for x in range(num_x) if y % 2 == 0]
        list_odd = [(x, y) for y in range(num_y) for x in reversed(range(num_x)) if y % 2 != 0]
        list_all = list_even + list_odd
        coords = sorted(list_all, key=self.sort_second)

        # associate a grid point to each probe position
        coord_dict = {}
        for key in range(max_probes):
            coord_dict[key+1] = coords[key]
        return coord_dict

    def sort_second(self, val):
        """ helper function for sorting a list of tuples by the second element of each tuple,
        used for setting up the serpentine grid

        @returns: the second element of value (in the context here, value is a 2dim tuple (x, y))
        """
        return val[1]

    def get_position(self):
        """ This method retrieves the current stage position from the hardware and does formatting of the return value.

        @returns: float tuple: position (x, y, z)
        """
        position = self._stage.get_pos()  # returns a dictionary {'x': x_pos, 'y': y_pos, 'z': z_pos}
        position = tuple([*position.values()])  # convert into tuple
        return position

    def move_stage(self, position):
        """ This method allows to perform a movement of the 3 axis stage to the specified stage position.
        A movement to the z safety position is performed first, before doing the xy positioning.
        Then, z is moved to its specified value. Emits a signal when finished and sends the new position.

        @param: float tuple position: (x, y, z) position
        """
        if len(position) != 3:
            self.log.warn('Stage position to set must be iterable of length 3. No movement done.')

        else:
            self.moving = True
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
            # we could add here a signal to update the coordinates displayed on GUI after this first move

            self._stage.move_abs(pos_dict_xy)
            ready_x = self._stage.get_status('x')['x']
            ready_y = self._stage.get_status('y')['y']
            while not (ready_x and ready_y):
                sleep(0.5)
                ready_x = self._stage.get_status('x')['x']
                ready_y = self._stage.get_status('y')['y']
            # we could add here a signal to update the coordinates displayed on GUI after this second move

            self._stage.move_abs(pos_dict_z)
            ready = self._stage.get_status('z')['z']
            while not ready:
                sleep(0.5)
                ready = self._stage.get_status('z')['z']

            self.moving = False
            new_pos = self.get_position()
            self.log.info(new_pos)
            self.sigStageMoved.emit(new_pos)

            # need eventually a worker thread to be able to stop movement ??









    def move_to_target(self, target_position):
        """ This method allows to perform a movement of the 3 axis stage to the specified position given by the
        target probe number.
        A movement to the z safety position is performed first, before doing the xy positioning.
        Then, z is moved to its specified value.
        Emits a signal when finished and sends the new position and the reached target number

        @param: int target_position: number of the target merfish probe
        """
        self.moving = True
        # lets assume equidistant distribution  # to be modified with real grid distribution.
        # this could be modified. we could use a lookup dictionary containing the xyz positions directly.
        # so we don't need to recalculate them each time.
        grid_coordinates = self.get_coordinates(target_position)
        x_pos = self.origin[0] + grid_coordinates[0] * self.delta_x
        y_pos = self.origin[1] + grid_coordinates[1] * self.delta_y
        z_pos = self.origin[2]
        position = (x_pos, y_pos, z_pos)
        axis_label = ('x', 'y', 'z')
        pos_dict = dict([*zip(axis_label, position)])
        # separate into xy and z movements
        pos_dict_xy = {key: pos_dict[key] for key in ['x', 'y']}
        pos_dict_z = {key: pos_dict[key] for key in ['z']}
        # do the movement
        self._stage.move_abs({'z': self.z_safety_pos})  # move to z safety position before making the xy movement
        # we could add here a signal to update the coordinates displayed on GUI after this first move
        self._stage.move_abs(pos_dict_xy)
        # we could add here a signal to update the coordinates displayed on GUI after this second move
        self._stage.move_abs(pos_dict_z)

        self.moving = False
        new_pos = self.get_position()
        self.log.info(new_pos)
        self.sigStageMovedToTarget.emit(new_pos, target_position)

    def get_coordinates(self, target):
        """ This method returns the (x, y) grid coordinates associated to the target position

        @param: int target: target position of the merfish probe
        @returns: int tuple (x, y)
        """
        return self._probe_coordinates_dict[target]

    def abort_movement(self):
        """ This method is called to abort a stage movement (either initiated by move_stage or move_to_target)
        Sends a signal to indicate that the stage was stopped and the current reached position. """
        self._stage.abort()
        self.log.info('Movement aborted!')
        pos = self.get_position()
        self.sigStageStopped.emit(pos)

    def set_origin(self, origin):
        """ Defines the origin = the metric coordinates of the position1 of the grid with the merfish probes.
        Sends a signal to indicate that the origin was set.
        """
        self.origin = origin
        # create a dictionary that allows to access the position number of the merfish probe by its metric coordinates
        probe_xy_position_dict = {}
        for key in self._probe_coordinates_dict:
            x_pos = self._probe_coordinates_dict[key][0] * self.delta_x + self.origin[0]
            y_pos = self._probe_coordinates_dict[key][1] * self.delta_y + self.origin[1]
            position = (x_pos, y_pos)
            probe_xy_position_dict[key] = position
        # invert the keys and values in the dictionary because we want to access the target position by the key
        inv_dict = dict((v, k) for k, v in probe_xy_position_dict.items())
        self._probe_xy_position_dict = inv_dict
        self.sigOriginDefined.emit()


# add the default values for position 1

# make it possible to abort a movement  (currently not supported because method gets blocked until waitontarget in hardware module reached
# same when querying the status ..

