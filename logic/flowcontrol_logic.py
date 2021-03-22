# -*- coding: utf-8 -*-
"""
Created on Thu Mars 4 2021

@author: fbarho

This module contains the logic to control the microfluidics pump and flowrate measurement
"""
from time import sleep
import math

from qtpy import QtCore
from logic.generic_logic import GenericLogic
from core.configoption import ConfigOption
from core.connector import Connector

# put all signals for the different subclasses of QRunnable here even though each subclass only uses one of these signals
class WorkerSignals(QtCore.QObject):
    """ Defines the signals available from a running worker thread """

    sigFinished = QtCore.Signal()
    sigRegulationWaitFinished = QtCore.Signal(float)  # carries the target_flowrate as parameter
    sigIntegrationIntervalFinished = QtCore.Signal(float, float)  #carries the target_volume as parameter and the integration interval


class MeasurementWorker(QtCore.QRunnable):
    """ Worker thread to monitor the pressure and the flowrate every x seconds when measuring mode is on

    The worker handles only the waiting time, and emits a signal that serves to trigger the update indicators """

    def __init__(self, *args, **kwargs):
        super(MeasurementWorker, self).__init__()
        self.signals = WorkerSignals()

    @QtCore.Slot()
    def run(self):
        """ """
        sleep(1)  # 1 second as time constant
        self.signals.sigFinished.emit()


class RegulationWorker(QtCore.QRunnable):
    """ Worker thread to regulate the pressure every x seconds when regulation loop is started

    The worker handles only the waiting time, and emits a signal that serves to trigger new regulation step """

    def __init__(self, target_flowrate):
        super(RegulationWorker, self).__init__()
        self.signals = WorkerSignals()
        self.target_flowrate = target_flowrate

    @QtCore.Slot()
    def run(self):
        """ """
        sleep(1)  # 1 second as time constant
        self.signals.sigRegulationWaitFinished.emit(self.target_flowrate)


class VolumeCountWorker(QtCore.QRunnable):
    """ Worker thread to measure the consumed volume of buffer or probe

    The worker handles only the waiting time, and emits a signal that serves to trigger a new sampling """

    def __init__(self, target_volume, sampling_interval):
        super(VolumeCountWorker, self).__init__()
        self.signals = WorkerSignals()
        self.target_volume = target_volume
        self.sampling_interval = sampling_interval

    @QtCore.Slot()
    def run(self):
        """ """
        sleep(self.sampling_interval)
        self.signals.sigIntegrationIntervalFinished.emit(self.target_volume, self.sampling_interval)


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
    regulating = False
    total_volume = 0
    target_volume_reached = True

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
        worker = MeasurementWorker()
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
            worker = MeasurementWorker()
            worker.signals.sigFinished.connect(self.flow_measurement_loop)
            self.threadpool.start(worker)


    def regulate_pressure(self, target_flowrate, sensor_channel=None, pressure_channel=None):
        """
        @param: float target_flowrate
        @param: int sensor_channel: ID of the sensor channel
        (use this method only for a single channel so that flowrate is returned as float and not as float list,
        but you can indicate which channel in case there are more than one)
        @param: int pressure_channel: ID of the pressure channel
        (use this method only for a single channel so that pressure is returned as float and not as float list,
        but you can indicate which channel in case there are more than one)
        """
        flowrate = self.get_flowrate(sensor_channel)
        print(f'flowrate {flowrate}')
        # if 10 != abs(flowrate - target_flowrate):  # which precision ?   #use math.isclose function instead when precision defined
        if not math.isclose(flowrate, target_flowrate, rel_tol=0.1, abs_tol=0):  # allow 10 % tolerance
            diff = target_flowrate - flowrate
            print(f'relative error: {abs(diff)/max(flowrate, target_flowrate)}')
            pressure = self.get_pressure(pressure_channel)
            const = 1  # which proportionality constant do we need ?
            new_pressure = max(min(50.0, pressure + const * diff), 0.0)
            print(f'new_pressure {new_pressure}')
            self.set_pressure(new_pressure, pressure_channel)
        else:
            pass
        # rajouter I de 0.01 (min)

# first tests with a simple version where the channels are not specified (we would need signal overloading in the worker thread... to be explored later)
    def start_pressure_regulation_loop(self, target_flowrate):
        self.regulating = True
        self.regulate_pressure(target_flowrate)
        # regulate the pressure, using a worker thread
        worker = RegulationWorker(target_flowrate)
        worker.signals.sigRegulationWaitFinished.connect(self.pressure_regulation_loop)
        self.threadpool.start(worker)

    def stop_pressure_regulation_loop(self):
        self.regulating = False

    def pressure_regulation_loop(self, target_flowrate):
        self.regulate_pressure(target_flowrate)
        if self.regulating:
            # enter in a loop until the regulating mode is stopped
            worker = RegulationWorker(target_flowrate)
            worker.signals.sigRegulationWaitFinished.connect(self.pressure_regulation_loop)
            self.threadpool.start(worker)

    def start_volume_measurement(self, target_volume, sampling_interval):
        self.total_volume = 0
        if self.total_volume < target_volume:
            self.target_volume_reached = False
        # start summing up the total volume, using a worker thread
        worker = VolumeCountWorker(target_volume, sampling_interval)
        worker.signals.sigIntegrationIntervalFinished.connect(self.volume_measurement_loop)
        self.threadpool.start(worker)

    def volume_measurement_loop(self, target_volume, sampling_interval):
        flowrate = self.get_flowrate()
        self.total_volume += flowrate * sampling_interval / 60  # abs(flowrate) ???
        print(self.total_volume)
        if self.total_volume < target_volume:
            self.target_volume_reached = False
        else:
            self.target_volume_reached = True

        if not self.target_volume_reached:
            # enter in a loop until the target_volume is reached
            worker = VolumeCountWorker(target_volume, sampling_interval)
            worker.signals.sigIntegrationIntervalFinished.connect(self.volume_measurement_loop)
            self.threadpool.start(worker)

    def stop_volume_measurement(self):
        self.target_volume_reached = True

















