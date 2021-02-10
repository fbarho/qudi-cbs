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

from pipython import GCSDevice, pitools


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
        max_step: 1  # in um


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
        self.log.info('available axes: {}'.format(self.axes))

        # remove log entries later on
        self._axis_label = self.axes[0]
        self.log.info(self._axis_label)
        self._axis_ID = self.pidevice.GetID() 
        self.log.info(self._axis_ID)

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

        @return bool: error code (True: ok, False: not ok)   or modify to return position ??
        """
        constraints = self.get_constraints()
        position = self.get_pos()  # check the return format of this call
        err = False

        for i in range(len(
                param_dict)):  # potentially a list of axes. real case: list of length 1 because pifoc only has one axis
            (axis, step) = param_dict.popitem()
            cur_pos = position[axis]  # returns just the float value of the axis
            # self.log.info(cur_pos)
            if axis in self.axes and abs(step) <= constraints[axis]['max_step'] and constraints[axis]['pos_min'] <= cur_pos + step <= constraints[axis]['pos_max']: # and condition that position stays in allowed range
                self.pidevice.MVR(axis, step)
                err = True
                if not err:
                    error_code = self.pidevice.GetError()
                    error_msg = self.pidevice.TranslateError(error_code)
                    self.log.warning(f'Could not move axis {axis} by {step}: {error_msg}.')
                    # it might be needed to print a pertinent error message in case the movement was not performed because the conditions above were not met,
                    # that is, if the error does not come from the controller but due to the coded conditions 
        return err
        # note that there is a different function available for simultaneous multi axes movement. 

    def move_abs(self, param_dict):
        """ Moves stage to absolute position (absolute movement)

        @param dict param_dict: Dictionary with axis name and target position (in um units) as key - value pairs

        @return bool: error code (True: ok, False: error)       - or modify to return the new position ??
        """
        constraints = self.get_constraints()
        err = False

        for i in range(len(
                param_dict)):  # potentially a list of axes. real case: list of length 1 because pifoc only has one axis
            (axis, target) = param_dict.popitem()
            # self.log.info(f'axis: {axis}; target: {target}')
            if axis in self.axes and constraints[axis]['pos_min'] <= target <= constraints[axis]['pos_max']:  # control if the right axis is addressed
                self.pidevice.MOV(axis, target)  # MOV has no return value
                err = True  
                if not err:
                    error_code = self.pidevice.GetError()
                    error_msg = self.pidevice.TranslateError(error_code)
                    self.log.warning(f'Could not move axis {axis} to {target} : {error_msg}.')
                    # it might be needed to print a pertinent error message in case the movement was not performed because the conditions above were not met,
                    # that is, if the error does not come from the controller but due to the coded conditions 
        return err

        # note that there is a different function available for simultaneous multi axes movement. (MVE)

    def abort(self):
        """ Stops movement of the stage

        @return bool: error code (True: ok, False: error)
        """
        # err = self.pidevice.HLT()  # needs eventually controller ID as argument  # HLT or STP ?
        # errorcode = self.pidevice.GetError()
        # errormsg = self.pidevice.TranslateError(errorcode)
        # if not err:
        #     self.log.warning(f'Error calling abort: {errormsg}')
        # return err
        pass 

    def get_pos(self, param_list=None):
        """ Gets current position of the controller

        @param list param_list: optional, if a specific position of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                position is asked.

        @return OrderedDict: with keys being the axis labels and item the current
                      position.

                      update docstring after tests !
        """
        pos = self.pidevice.qPOS(self.axes)  # this returns an OrderedDict

        # do some formatting if needed -- this is done in logic module ! 

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
        err = self.pidevice.IsControllerReady()  
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
        self.log.info('get_velocity not available')

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
        # should it be possible to set the velocity else just send a message that this function is not available for the controller

# not on the interface 
    def wait_for_idle(self):
        """ first draft for a wait for idle function
        
        checks if on target 
        
        problem: seems to return too fast, so that the position is not yet the right one.. 
        although this function is actually meant to not wait until the target position is reached.. 
        
        it works when the two log entries are activated. this seems to take some additional time, allowing 
        the stage to reach the target 
        """
        # self.log.info('old position: {}'.format(self.get_pos()))
        pitools.waitontarget(self.pidevice)
        # self.log.info('new position: {}'.format(self.get_pos()))
        return




################### class with context manager #################################3

class PIFOCV2(Base, MotorInterface):
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
        self.pidevice = GCSDevice(self._controllername)

    def on_activate(self):
        """ Initialization
        """
        # open the connection
        # with GCSDevice(self._controllername) as pidevice:

        with self.pidevice:  # is it possible to use this as context manager and also to call the dll functions therein ??
            self.pidevice.ConnectUSB(serialnum=self._serialnum)
            self.log.info('connected: {}'.format(self.pidevice.qIDN().strip()))

            self.axes = self.pidevice.axes  # this returns a list
            self.log.info('available axes: {}'.format(self.axes))

            # remove log entries later on
            self._axis_label = self.axes[0]
            self.log.info(self._axis_label)
            self._axis_ID = self.pidevice.GetID()
            self.log.info(self._axis_ID)

    def on_deactivate(self):
        """
        """
        with self.pidevice:
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

        @return bool: error code (True: ok, False: not ok)   or modify to return position ??
        """
        constraints = self.get_constraints()
        position = self.get_pos()  # check the return format of this call
        err = False

        for i in range(len(
                param_dict)):  # potentially a list of axes. real case: list of length 1 because pifoc only has one axis
            (axis, step) = param_dict.popitem()
            cur_pos = position[axis]  # returns just the float value of the axis
            # self.log.info(cur_pos)
            if axis in self.axes and abs(step) <= constraints[axis]['max_step'] and constraints[axis][
                'pos_min'] <= cur_pos + step <= constraints[axis][
                'pos_max']:  # and condition that position stays in allowed range
                with self.pidevice:
                    self.pidevice.ConnectUSB(serialnum=self._serialnum)
                    self.pidevice.MVR(axis, step)
                    err = True
                    if not err:
                        error_code = self.pidevice.GetError()
                        error_msg = self.pidevice.TranslateError(error_code)
                        self.log.warning(f'Could not move axis {axis} by {step}: {error_msg}.')
                        # it might be needed to print a pertinent error message in case the movement was not performed because the conditions above were not met,
                        # that is, if the error does not come from the controller but due to the coded conditions
        return err
        # note that there is a different function available for simultaneous multi axes movement.

    def move_abs(self, param_dict):
        """ Moves stage to absolute position (absolute movement)

        @param dict param_dict: Dictionary with axis name and target position (in um units) as key - value pairs

        @return bool: error code (True: ok, False: error)       - or modify to return the new position ??
        """
        constraints = self.get_constraints()
        err = False

        for i in range(len(
                param_dict)):  # potentially a list of axes. real case: list of length 1 because pifoc only has one axis
            (axis, target) = param_dict.popitem()
            # self.log.info(f'axis: {axis}; target: {target}')
            if axis in self.axes and constraints[axis]['pos_min'] <= target <= constraints[axis][
                'pos_max']:  # control if the right axis is addressed
                with self.pidevice:
                    self.pidevice.MOV(axis, target)  # MOV has no return value
                    err = True
                    if not err:
                        error_code = self.pidevice.GetError()
                        error_msg = self.pidevice.TranslateError(error_code)
                        self.log.warning(f'Could not move axis {axis} to {target} : {error_msg}.')
                        # it might be needed to print a pertinent error message in case the movement was not performed because the conditions above were not met,
                        # that is, if the error does not come from the controller but due to the coded conditions
        return err

        # note that there is a different function available for simultaneous multi axes movement. (MVE)

    def abort(self):
        """ Stops movement of the stage

        @return bool: error code (True: ok, False: error)
        """
        # err = self.pidevice.HLT()  # needs eventually controller ID as argument  # HLT or STP ?
        # errorcode = self.pidevice.GetError()
        # errormsg = self.pidevice.TranslateError(errorcode)
        # if not err:
        #     self.log.warning(f'Error calling abort: {errormsg}')
        # return err
        pass

    def get_pos(self, param_list=None):
        """ Gets current position of the controller

        @param list param_list: optional, if a specific position of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                position is asked.

        @return OrderedDict: with keys being the axis labels and item the current
                      position.

                      update docstring after tests !
        """
        with self.pidevice:
            self.pidevice.ConnectUSB(serialnum=self._serialnum)
            pos = self.pidevice.qPOS(self.axes)  # this returns an OrderedDict

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
        with self.pidevice:
            err = self.pidevice.IsControllerReady()
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
        self.log.info('get_velocity not available')

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
        # should it be possible to set the velocity else just send a message that this function is not available for the controller

    # not on the interface
    def wait_for_idle(self):
        """ first draft for a wait for idle function

        checks if on target

        problem: seems to return too fast, so that the position is not yet the right one..
        although this function is actually meant to not wait until the target position is reached..

        it works when the two log entries are activated. this seems to take some additional time, allowing
        the stage to reach the target
        """
        # self.log.info('old position: {}'.format(self.get_pos()))
        pitools.waitontarget(self.pidevice)
        # self.log.info('new position: {}'.format(self.get_pos()))
        return



        