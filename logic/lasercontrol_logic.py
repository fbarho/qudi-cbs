#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb 10 2021

@author: fbarho

A module to control the lasers via a DAQ (analog output and digital output line for triggering) or via an FPGA.

The DAQ / FPGA is used to control the OTF to select the laser wavelength

Modified version of daq_ao_logic. daq_ao_logic will be removed in the following and replaced by lasercontrol_logic.
"""

from core.connector import Connector
from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic
from qtpy import QtCore
from core.configoption import ConfigOption


class LaserControlLogic(GenericLogic):
    """ Controls the DAQ analog output and allows to set a digital output line for triggering
    or controls the FPGA output

    Example config for copy-paste:
        lasercontrol_logic:
        module.Class: 'lasercontrol_logic.LaserControlLogic'
        controllertype: 'daq'  # 'fpga'
        connect:
            controller: 'dummy_daq'
    """
    # config
    controllertype = ConfigOption('controllertype', missing='error')  # something similar to a flag indicating daq or fpga

    # declare connectors
    controller = Connector(interface='LaserControlInterface')  # can be a daq or an fpga # rename this interface in LasercontrolInterface

    # signals
    sigIntensityChanged = QtCore.Signal()  # if intensity dict is changed programmatically, this updates the GUI

    # attributes
    enabled = False

    # private attributes
    _intensity_dict = {}
    _laser_dict = {}

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        # activate if necessary
        # self.threadlock = Mutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._controller = self.controller()

        self.enabled = False  # attribute to handle the on-off switching of the laser-on button

        self._laser_dict = self.get_laser_dict()
        self._intensity_dict = self.init_intensity_dict(0)

    def on_deactivate(self):
        """ Perform required deactivation. """
        pass

    def get_laser_dict(self):
        """ Retrieve the dictionary containing wavelength, channel, and voltage range from the hardware.

        exemplary entry: {'laser1': {'label': 'laser1', 'wavelength': '405 nm', 'channel': '/Dev1/AO2', 'voltage_range': [0, 10]}  # DAQ
                         {'laser1': {'label': 'laser1', 'wavelength': '405 nm', 'channel': '405'}}  # FPGA. 'channel' corresponds to the registername.

        returns: dict
        """
        return self._controller.get_dict()

    def init_intensity_dict(self, value=0):
        """ creates a dictionary with the same keys as the laser dict and set an initial value for the output voltage

        example: {'laser1': 0, 'laser2': 0, 'laser3': 0, 'laser4': 0}

        returns: dict: intensity_dict
        """
        intensity_dict = {}
        for key in self._laser_dict:
            intensity_dict[key] = value

        return intensity_dict

    def reset_intensity_dict(self):
        """ resets all values of the intensity_dict to zero
        """
        # function is called from filterwheel logic before setting a new filter
        for key in self._intensity_dict:
            self._intensity_dict[key] = 0
        self.sigIntensityChanged.emit()

    def apply_voltage(self):
        """ applies the intensities defined in the _intensity_dict to the belonging channels.

        This method is used to switch lasers on from the GUI, for this reason it iterates over all defined channels
        (no individual laser on / off button but one button for all).
        """
        self.enabled = True

        if self.controllertype == 'daq':
            for key in self._laser_dict:
                self._controller.apply_voltage(self._intensity_dict[key] * self._laser_dict[key]['ao_voltage_range'][1] / 100,
                                    self._laser_dict[key]['channel'])
                # conversion factor: user indicates values in percent of max voltage
                # alternative: (to test which is faster)
                # self.apply_voltage_single_channel(self._intensity_dict[key] * self._laser_dict[key]['ao_voltage_range'][1] / 100, self._laser_dict[key]['channel'])
                # does the delay due to iteration matter ? (laser 4 switched on slightly after laser 1 ? ..)
        elif self.controllertype == 'fpga':
            for key in self._laser_dict:
                self._controller.apply_voltage(self._intensity_dict[key], self._laser_dict[key]['channel'])
        else:
            self.log.warning('your controller type is currently not covered')

    def voltage_off(self):
        """ Switches all lasers off. """
        self.enabled = False
        if self.controllertype == 'daq':
            for key in self._laser_dict:
                self._controller.apply_voltage(0.0, self._laser_dict[key]['channel'])
            # note that the intensity dict is intentionally not reset to allow easy on off switching without need to rewrite the value
        elif self.controllertype == 'fpga':
            for key in self._laser_dict:
                self._controller.apply_voltage(0, self._laser_dict[key]['channel'])
        else:
            self.log.warning('your controller type is currently not covered')

    @QtCore.Slot(str, int)  # should the decorator be removed when this method is called in a task ???
    def update_intensity_dict(self, key, value):
        """ STOP! DO NOT CALL THIS FUNCTION UNLESS YOU ARE SURE THAT THE FILTER YOU ARE USING IS ADAPTED FOR THE LASER LINE YOU WANT TO SET!
        This function updates the desired intensity value that is applied to the specified output.
        In case lasers are already on, the new value is automatically applied.
        Else, it just prepares the value that will be applied when voltage output is activated.
        As the GUI contains a security mechanism to avoid setting a value to a forbidden laser (incompatible with the current filter setting),
        there is no risk when updating intensities from the GUI. However when calling this method from the iPython console, make sure what you
        are doing.

        @params: str key: identifier present in the intensity dict, typically 'laser1', 'laser2', ..
        @params: int value: new intensity value (0 - 100 %) to be applied to the specified laser line
        """
        try:
            self._intensity_dict[key] = value
            # if laser is already on, the new value must be written to the daq output
            if self.enabled:
                self.apply_voltage()
        except KeyError:
            self.log.info('Specified identifier not available')


    # maybe put this part on daq specific interface # keep right now the daq compatible version as is
    # see if later fpga specific part should be added
    # low level functions (direct access to daq functions)
    def apply_voltage_single_channel(self, voltage, channel, autostart=True, timeout=10):
        """ this method makes the low level method from the hardware directly accessible
        Writes a voltage to the specified channel.

        @params: float voltage: voltage value to be applied
        @params: str channel: analog output line such as /Dev1/AO0
        @params: bool autostart: True = task started immediately on call of start task. autostart = False can only be used if timing is configured.
        @param: int? float? timeout: RW timeout in seconds
        """
        if self.controllertype == 'daq':
            self._controller.apply_voltage(voltage, channel, autostart, timeout)
        else:
            pass

    def send_trigger(self):
        """ """
        if self.controllertype == 'daq':
            self._controller.send_trigger()
        else:
            pass

    def set_up_do_channel(self):
        """ create a digital output channel
        """
        if self.controllertype == 'daq':
            self._controller.set_up_do_channel()
        else:
            pass

    def close_do_task(self):
        """ close the digital output channel and task if there is one """
        if self.controllertype == 'daq':
            self._controller.close_do_task()
        else:
            pass
        
        
    def set_up_ai_channel(self):
        """ create a task and its virtual channel for the analog input
        """
        if self.controllertype == 'daq':
            self._controller.set_up_ai_channel()
        else:
            pass

        
    def close_ai_task(self):
        """ close the analog input task if there is one
        """
        if self.controllertype == 'daq':
            self._controller.close_ai_task()
        else:
            pass
        
    def read_ai_channel(self):
        """
        """
        if self.controllertype == 'daq':
            ai_value = self._controller.read_ai_channel()
            return ai_value
        else:
            pass
        
        
    def send_trigger_and_control_ai(self):
        """ for multicolor imaging task : control if fire sent"""
        if self.controllertype == 'daq':
            return self._controller.send_trigger_and_control_ai()
        else:
            pass




    ### new 3 march 2021 test with tasks for ramm setup
    #low level methods directly from ni_fpga hardware module
    def close_default_session(self):
        """ This method is called before another bitfile than the default one shall be loaded

        (in this version it actually does the same as on_deactivate (we could also just call this method ..  but this might evolve)
        """
        if self.controllertype == 'fpga':
            self._controller.close_default_session()
        else:
            pass


    def restart_default_session(self):
        """ This method allows to restart the default session"""
        if self.controllertype == 'fpga':
            self._controller.restart_default_session()
        else:
            pass

    def start_task_session(self, bitfile):
        """ loads a bitfile used for a specific task """
        if self.controllertype == 'fpga':
            self._controller.start_task_session(bitfile)
        else:
            pass

    def end_task_session(self):
        if self.controllertype == 'fpga':
            self._controller.end_task_session()
        else:
            pass

    def run_test_task_session(self):  #replace this name by run_merfish_task_session etc ..
        if self.controllertype == 'fpga':
            self._controller.run_test_task_session()
        else:
            pass
