# -*- coding: utf-8 -*-
"""
Created on Thu Mars 4 2021

@author: fbarho

This module contains the logic to control the microfluidics pump and flowrate measurement
"""
from time import sleep

from qtpy import QtCore
from logic.generic_logic import GenericLogic
from core.configoption import ConfigOption
from core.connector import Connector


class WorkerSignals(QtCore.QObject):
    """ Defines the signals available from a running worker thread """

    sigFinished = QtCore.Signal()


class Worker(QtCore.QRunnable):
    """ Worker thread to monitor the pressure and the flowrate every x seconds when measuring mode is on

    The worker handles only the waiting time, and emits a signal that serves to trigger the update indicators """

    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__()
        self.signals = WorkerSignals()

    @QtCore.Slot()
    def run(self):
        """ """
        sleep(1)  # 1 second as time constant
        self.signals.sigFinished.emit()


class FlowcontrolLogic(GenericLogic):
    """
    Class containing the logic to control the microfluidics pump and flowrate measurement

    Example config for copy-paste:

    flowcontrol_logic:
        module.Class: 'flowcontrol_logic.FlowcontrolLogic'
        connect:
            pump: 'pump_dummy'
    """

    # declare connectors
    pump = Connector(interface='MicrofluidicsPumpInterface')

    # signals
    sigUpdateFlowMeasurement = QtCore.Signal(float, float)

    # attributes
    measuring = False

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.threadpool = QtCore.QThreadPool()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # connector
        self._pump = self.pump()

    def on_deactivate(self):
        """ Perform required deactivation. """
        pass

    def get_pressure(self, channels=None):
        """
        @param: list channels: optional, list of channels from which pressure value will be measured
        """
        pressure = self._pump.get_pressure(channels)  # returns a dictionary: {0: pressure_channel_0}
        pressure = [*pressure.values()]  # retrieve only the values from the dictionary and convert into list
        if len(pressure) < 2:
            return pressure[0]
        else:
            return pressure

    def set_pressure(self, pressures, channels=None):
        """
        @param: float or float list pressures: pressure to be set to a given channel
        @param: int list channels: optional, needed in case more than one pressure channel is available
        """
        if not channels:
            if not isinstance(pressures, float):  # a list is given
                self.log.warning('Channels must be specified if more than one pressure value shall be set.')
            else:
                param_dict = {}
                param_dict[0] = pressures  # maybe modify in case another pump has a different way of addressing its channel (adapt by config; default_channel_ID ?)
                unit = self.get_pressure_unit()
                self._pump.set_pressure(param_dict)
                self.log.info(f'Pressure set to {pressures} {unit}')
        else:
            param_dict = dict(zip(channels, pressures))
            self._pump.set_pressure(param_dict)

    def get_pressure_range(self, channels=None):
        """
        @param: list channels: optional, list of channels from which pressure range value will be retrieved
        """
        pressure_range = self._pump.get_pressure_range(channels)  # returns a dictionary: {0: pressure_range_channel_0}
        pressure_range = [*pressure_range.values()]  # retrieve only the values from the dictionary and convert into list
        if len(pressure_range) < 2:
            return pressure_range[0]
        else:
            return pressure_range

    def get_pressure_unit(self, channels=None):
        """
        @param: list channels: optional, list of channels from which pressure range unit will be retrieved
        """
        pressure_unit = self._pump.get_pressure_unit(channels)  # returns a dictionary: {0: pressure_unit_channel_0}
        pressure_unit = [*pressure_unit.values()]  # retrieve only the values from the dictionary and convert into list
        if len(pressure_unit) < 2:
            return pressure_unit[0]
        else:
            return pressure_unit

    def get_flowrate(self, channels=None):
        """
        @param: list channels: optional, list of channels from which pressure value will be measured
        """
        flowrate = self._pump.get_flowrate(channels)  # returns a dictionary: {0: flowrate_channel_0}
        flowrate = [*flowrate.values()]  # retrieve only the values from the dictionary and convert into list
        if len(flowrate) < 2:
            return flowrate[0]
        else:
            return flowrate

    def get_flowrate_range(self, channels=None):
        flowrate_range = self._pump.get_sensor_range(channels)  # returns a dictionary: {0: sensor_range_channel_0}
        flowrate_range = [*flowrate_range.values()]  # retrieve only the values from the dictionary and convert into list
        if len(flowrate_range) < 2:
            return flowrate_range[0]
        else:
            return flowrate_range

    def get_flowrate_unit(self, channels=None):
        flowrate_unit = self._pump.get_sensor_unit(channels)  # returns a dictionary: {0: sensor_unit_channel_0}
        flowrate_unit = [*flowrate_unit.values()]  # retrieve only the values from the dictionary and convert into list
        if len(flowrate_unit) < 2:
            return flowrate_unit[0]
        else:
            return flowrate_unit

    def start_flow_measurement(self):
        self.measuring = True
        # monitor the pressure and flowrate, using a worker thread
        worker = Worker()
        worker.signals.sigFinished.connect(self.flow_measurement_loop)
        self.threadpool.start(worker)

    def stop_flow_measurement(self):
        self.measuring = False
        # get once again the latest values
        pressure = self.get_pressure()
        flowrate = self.get_flowrate()
        self.sigUpdateFlowMeasurement.emit(pressure, flowrate)

    def flow_measurement_loop(self):
        pressure = self.get_pressure()
        flowrate = self.get_flowrate()
        self.sigUpdateFlowMeasurement.emit(pressure, flowrate)
        if self.measuring:
            # enter in a loop until measuring mode is switched off
            worker = Worker()
            worker.signals.sigFinished.connect(self.flow_measurement_loop)
            self.threadpool.start(worker)



    # # to discuss how to regulate flowrate # add this later
    # def regulate_pressure(self, flowrate):
    #     pass
    # # regulation feedback loop to achieve a desired flowrate





