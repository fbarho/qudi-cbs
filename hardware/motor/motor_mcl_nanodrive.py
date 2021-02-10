"""
Created on Mon Feb 1 2021

@author: fbarho

This file contains a class for the Mad city labs piezo controller.

It is an extension to the hardware code base of Qudi software
obtained from <https://github.com/Ulm-IQO/qudi/>
"""
import ctypes

from core.module import Base
from interface.motor_interface import MotorInterface
from core.configoption import ConfigOption


# error codes  # maybe transform into error dict
MCL_SUCCESS             = 0   # Task has been completed successfully.
MCL_GENERAL_ERROR       = -1  # These errors generally occur due to an internal sanity check failing.
MCL_DEV_ERROR		    = -2  # A problem occurred when transferring data to the Nano-Drive.  It is likely that the Nano-Drive will have to be 	 power cycled to correct these errors.
MCL_DEV_NOT_ATTACHED	= -3  # The Nano-Drive cannot complete the task because it is not attached.
MCL_USAGE_ERROR		    = -4  # Using a function from the library which the Nano-Drive does not support causes these errors.
MCL_DEV_NOT_READY	    = -5  # The Nano-Drive is currently completing or waiting to complete another task.
MCL_ARGUMENT_ERROR	    = -6  # An argument is out of range or a required pointer is equal to NULL.
MCL_INVALID_AXIS		= -7  # Attempting an operation on an axis that does not exist in the Nano-Drive.
MCL_INVALID_HANDLE	    = -8  # The handle is not valid.  Or at least is not valid in this instance of the DLL.


class MCLNanoDrive(Base, MotorInterface):
    """ Class representing the MCL Nano-Drive (Piezo controller).

    Example config for copy-paste:

    mcl:
        module.Class: 'motor.motor_mcl_nanodrive.MCLNanoDrive'
        dll_location: 'C:\\Program Files\\Mad City Labs\\NanoDrive\\Madlib.dll'   # path to library file
        pos_min: 0  # in um
        pos_max: 80  # in um
        max_step: 1  # in um

    """

    dll_location = ConfigOption('dll_location', missing='error')

    handle = None

    # attributes for get_constraints method
    _axis_label = None
    _axis_ID = None
    _pos_min = ConfigOption('pos_min', 0, missing='warn')  # in um
    _pos_max = ConfigOption('pos_max', 80, missing='warn')  # in um
    _max_step = ConfigOption('max_step', 1, missing='warn')  # in um

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        self.dll = ctypes.cdll.LoadLibrary(self.dll_location)

        # define return type for some dll functions
        self.dll.MCL_SingleReadZ.restype = ctypes.c_float

        # get handle of connected Nanodrive
        handle = self.dll.MCL_InitHandle()
        if handle == 0:
            self.log.warning('Failed to initialize Nanodrive.')
        else:
            self.handle = handle

        num = self.dll.MCL_NumberOfCurrentHandles()
        self.log.debug(f'{num} Nanodrives connected.')

        self._axis_label = 'Z'  # one axis controller. Set this arbitrarily to be conform with motor interface
        self._axis_ID = self.handle  # not really needed .. just for conformity with pifoc get_constraints function. maybe remove ..

    def on_deactivate(self):
        handle = ctypes.c_int(self.handle)
        self.dll.MCL_ReleaseHandle(handle)

    def get_constraints(self):
        """ Retrieve the hardware constrains from the motor device.

        @return dict constraints
        """
        constraints = {}

        axis0 = {'label': self._axis_label,
                 'ID': self._axis_ID,
                 'unit': 'um',
                 'pos_min': self._pos_min,
                 'pos_max': self._pos_max,
                 'max_step': self._max_step}

        # assign the parameter container for to a name which will identify it
        constraints[axis0['label']] = axis0

        return constraints


    def move_rel(self, param_dict):
        """ Moves stage in given direction (relative movement)

        @param dict param_dict: Dictionary with axis name and step (in um units) as key - value pairs

        @return bool: error code (True: ok, False: not ok)   or modify to return position ??
        """
        # this version works for a param_dict with one entry.
        constraints = self.get_constraints()
        # this is not the good return format ..
        position = self.get_pos().values()  # get_pos returns a dict {axis_label: position}

        (axis, step) = param_dict.popitem()

        if axis == self._axis_label and abs(step) <= constraints[axis]['max_step'] and constraints[axis]['pos_min'] <= position + step <= constraints[axis]['pos_max']:
            new_pos = ctypes.c_double(position + step)
            err = self.dll.MCL_SingleWriteZ(new_pos, self.handle)
            if err == 'MCL_SUCCESS':
                return True
            else:
                self.log.warning(f'Could not move axis {axis} by {step}: {err}.')
                return False

    def move_abs(self, param_dict):
        """ Moves stage to absolute position (absolute movement)

        @param dict param_dict: Dictionary with axis name and target position (in um units) as key - value pairs

        @return bool: error code (True: ok, False: error)       - or modify to return the new position ??
        """
        pass

    def abort(self):
        """ Stops movement of the stage

        @return bool: error code (True: ok, False: error)
        """
        pass

    def get_pos(self):
        """ Gets current position of the stage

        @return dict: with keys being the axis labels and item the current position.
        """
        cur_pos = self.dll.MCL_SingleReadZ(self.handle)
        pos = {}
        pos[self._axis_label] = cur_pos
        return pos
        # add check that pos is not an error code
        # note that pifoc returns ordered dict. check if this gives problems for interface.

    def get_status(self, param_list=None):
        """ Get the status of the position

        @param list param_list: optional, if a specific status of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                status is asked.

        @return bool err
        """
        pass

    def calibrate(self, param_list=None):
        """ Calibrates the stage.

        @param dict param_list: param_list: optional, if a specific calibration
                                of an axis is desired, then the labels of the
                                needed axis should be passed in the param_list.
                                If nothing is passed, then all connected axis
                                will be calibrated.

        @return int: error code (0:OK, -1:error)
        """
        pass

    def get_velocity(self, param_list=None):
        """ Gets the current velocity for all connected axes.

        @param dict param_list: optional, if a specific velocity of an axis
                                is desired, then the labels of the needed
                                axis should be passed as the param_list.
                                If nothing is passed, then from each axis the
                                velocity is asked.

        @return dict : with the axis label as key and the velocity as item.
        """
        self.log.info('get velocity not available')

    def set_velocity(self, param_dict):
        """ Write new value for velocity.

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-velocity-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.

        @return int: error code (0:OK, -1:error)
        """
        self.log.info('set velocity not available')
