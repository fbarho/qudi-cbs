# -*- coding: utf-8 -*-
"""
Created on Tue Jan 12 12:56:10 2021

@author: barho

This file contains a class for the PIFOC z axis positioning stage.

It is an extension to the hardware code base of Qudi software 
obtained from <https://github.com/Ulm-IQO/qudi/> 
"""

from core.module import Base
from interface.motor_interface import MotorInterface
from core.configoption import ConfigOption

from pipython import GCSDevice


# first version without context manager
# try to add it in a way similar to andor camera on github using @contextlib.contextmanager

class PIFOC(Base, MotorInterface):
    """ Class representing the PIFOC z axis positioning stage
    
    Example config for copy-paste:
        
    pifoc:
        module.Class: 'motor.motor_pifoc.PIFOC'
        controllername: 'E816'
        serialnumber: '110059675'
        pos_min: 0  # in um
        pos_max: 100  # in um
        max_step: 5  # in um


    """

    _controllername = ConfigOption('controllername', missing='error')  # 'E-816'
    _serialnum = ConfigOption('serialnumber', missing='error')  # 110059675'

    axes = None
    pidevice = None

    # private attributes read from config or from hardware and used for the constraints settings
    _axis_label = None
    _axis_ID = None
    _pos_min = ConfigOption('pos_min', 0, missing='warn')  # in um
    _pos_max = ConfigOption('pos_max', 100, missing='warn')  # in um
    _max_step = ConfigOption('max_step', 5, missing='warn')  # in um

    # _vel_min = ConfigOption('vel_min', ??, missing='warn')
    # _vel_max = ConfigOption('vel_max', ??, missing='warn')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initialization
        """
        # open the connection
        # with GCSDevice(self._controllername) as pidevice:

        self.pidevice = GCSDevice(self._controllername)
        self.pidevice.ConnectUSB(serialnum=self._serialnum)
        self.log.info('connected: {}'.format(self.pidevice.qIDN().strip()))

        self.axes = self.pidevice.axes  # this returns a list
        self.log.info('available axes: {}'.format(self.axis))

        self._axis_label = self.axes[0]
        # self._axis_ID = self.pidevice.GetControllerID()  # to test if this is the right function call

    def on_deactivate(self):
        """ 
        """
        self.pidevice.CloseConnection()

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
                 # 'vel_min': self._vel_min,
                 # 'vel_max': self._vel_max}

        # assign the parameter container for x to a name which will identify it
        constraints[axis0['label']] = axis0

        return constraints

    def move_rel(self, param_dict):
        """ Moves stage in given direction (relative movement)

        @param dict param_dict: Dictionary with axis name and step (in um units) as key - value pairs

        @return int: error code (True: ok, False: not ok)   or modify to return position ??
        """
        constraints = self.get_constraints()
        position = self.get_pos()  # check the return format of this call
        err = False

        for i in range(len(
                param_dict)):  # potentially a list of axes. real case: list of length 1 because pifoc only has one axis
            (axis, step) = param_dict.popitem()
            if axis in self.axes:  # control if the right axis is addressed  # and step step < constraints[axis]['max_step'] and condition that position stays in allowed range
                err = self.pidevice.MRT(axis, step)
                if not err:
                    error_code = self.pidevice.GetError()
                    error_msg = self.pidevice.TranslateError(error_code)
                    self.log.warning(f'Could not move axis {axis} by {step} : {error_msg}.')
        return err

        # do we need a security mechanism to only do the movement if the step is smaller than max step size and
        # pos + step does not leave the allowed range ?
        # add this in the try- block before call to MOV or as and .. after if axis in self.axes

        # note that there is a different function available for simultaneous multi axes movement. (MVR)

    def move_abs(self, param_dict):
        """ Moves stage to absolute position (absolute movement)

        @param dict param_dict: Dictionary with axis name and target position (in um units) as key - value pairs

        @return int: error code (True: ok, False: error)       - or modify to return position ??
        """
        # first draft:
        # axes =list(param_dict.keys())    #
        # # add later the security mechanism to check if the right axis is given
        # target = param_dict[axes[0]]  # access the target value for the specified axis   # just use the single axis for this first version
        # self.pidevice.MOV(axes[0], target)

        constraints = self.get_constraints()
        err = False

        for i in range(len(
                param_dict)):  # potentially a list of axes. real case: list of length 1 because pifoc only has one axis
            (axis, target) = param_dict.popitem()
            if axis in self.axes and constraints[axis]['min_pos'] <= target <= constraints[axis]['max_pos']:  # control if the right axis is addressed
                err = self.pidevice.MOV(axis, target)
                if not err:
                    error_code = self.pidevice.GetError()
                    error_msg = self.pidevice.TranslateError(error_code)
                    self.log.warning(f'Could not move axis {axis} to {target} : {error_msg}.')
        return err

        # note that there is a different function available for simultaneous multi axes movement. (MVE)

    def abort(self):
        """ Stops movement of the stage

        @return int: error code (True: ok, False: error)
        """
        err = self.pidevice.HLT()  # needs eventually controller ID as argument  # HLT or STP ?
        errorcode = self.pidevice.GetError()
        errormsg = self.pidevice.TranslateError(errorcode)
        if not err:
            self.log.warning(f'Error calling abort: {errormsg}')
        return err

    def get_pos(self, param_list=None):
        """ Gets current position of the controller

        @param list param_list: optional, if a specific position of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                position is asked.

        @return dict: with keys being the axis labels and item the current
                      position.

                      update docstring after tests !
        """
        pos = self.pidevice.qPOS(self.axis)

        # do some formatting if needed

        #        with GCSDevice(self._controllername) as pidevice:
        #            pos = pidevice.qPOS(self.axis)

        return pos

    def get_status(self, param_list=None):
        """ Get the status of the position

        @param list param_list: optional, if a specific status of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                status is asked.

        @return bool err
        """
        err = self.pidevice.IsControllerReady()  # might need controller id as argument - to test
        return err

    def calibrate(self, param_list=None):
        """ Calibrates the stage.

        @param dict param_list: param_list: optional, if a specific calibration
                                of an axis is desired, then the labels of the
                                needed axis should be passed in the param_list.
                                If nothing is passed, then all connected axis
                                will be calibrated.

        @return int: error code (0:OK, -1:error)

        After calibration the stage moves to home position which will be the
        zero point for the passed axis. The calibration procedure will be
        different for each stage.
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
        # vel = self.pidevice.q???(self.axis)  # test which query is the right one here..

        # do some formatting if needed

        # return vel

    def set_velocity(self, param_dict):
        """ Write new value for velocity.

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-velocity-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.

        @return int: error code (0:OK, -1:error)
        """
        pass
        # should it be possible to set the velocity else just send a message that this function is not available for the controller
