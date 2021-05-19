# -*- coding: utf-8 -*-
"""
Created on Thu Mars 4 2021

@author: fbarho

This module contains the logic to control the microfluidics pump and flowrate measurement
"""
from time import sleep
import math
from simple_pid import PID

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
            daq_ao_logic: 'daq_logic.....'
    """

    # declare connectors
    pump = Connector(interface='MicrofluidicsPumpInterface')
    daq_logic = Connector(interface='DAQaoLogic')

    # signals
    sigUpdateFlowMeasurement = QtCore.Signal(float, float)
    sigUpdatePressureSetpoint = QtCore.Signal(float)
    sigUpdateVolumeMeasurement = QtCore.Signal(int, int)
    sigTargetVolumeReached = QtCore.Signal()
    sigRinsingFinished = QtCore.Signal()
    sigDisablePressureAction = QtCore.Signal()
    sigEnablePressureAction = QtCore.Signal()

    # attributes
    measuring_flowrate = False
    regulating = False
    measuring_volume = False
    total_volume = 0
    time_since_start = 0
    target_volume_reached = True
    rinsing_enabled = False

    # attributes for pid
    p_gain = 0.005
    i_gain = 0.001
    d_gain = 0
    pid_sample_time =  0.1 # in s, frequency for the PID update

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.threadpool = QtCore.QThreadPool()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # connector
        self._pump = self.pump()
        self._daq_logic = self.daq_logic()
        self.set_pressure(0.0)

        # signals from connected logic
        self._daq_logic.sigRinsingDurationFinished.connect(self.rinsing_finished)

    def on_deactivate(self):
        """ Perform required deactivation. """
        self.set_pressure(0.0)

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

    def set_pressure(self, pressures, log_entry=True, channels=None):
        """
        @param: float or float list pressures: pressure to be set to a given channel
        @param: bool log_entry: make log entry optional, for example to avoid overloading logger while running a pressure regulation loop
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
                if log_entry:
                    self.log.info(f'Pressure set to {pressures} {unit}')
                self.sigUpdatePressureSetpoint.emit(pressures)
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
        self.measuring_flowrate = True
        # monitor the pressure and flowrate, using a worker thread
        worker = MeasurementWorker()
        worker.signals.sigFinished.connect(self.flow_measurement_loop)
        self.threadpool.start(worker)

    def stop_flow_measurement(self):
        self.measuring_flowrate = False
        # get once again the latest values
        pressure = self.get_pressure()
        flowrate = self.get_flowrate()
        self.sigUpdateFlowMeasurement.emit(pressure, flowrate)

    def flow_measurement_loop(self):
        pressure = self.get_pressure()
        flowrate = self.get_flowrate()
        self.sigUpdateFlowMeasurement.emit(pressure, flowrate)
        if self.measuring_flowrate:
            # enter in a loop until measuring mode is switched off
            worker = MeasurementWorker()
            worker.signals.sigFinished.connect(self.flow_measurement_loop)
            self.threadpool.start(worker)

    def init_pid(self, setpoint):
        pid = PID(self.p_gain, self.i_gain, self.d_gain, setpoint=setpoint)
        pid.output_limits = (0, 15)
        pid.sample_time = self.pid_sample_time
        return pid

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
        print('flowrate {:.0f}'.format(flowrate))
        # if 10 != abs(flowrate - target_flowrate):  # which precision ?   #use math.isclose function instead when precision defined
        if not math.isclose(flowrate, target_flowrate, rel_tol=0.05, abs_tol=0):  # allow 5 % tolerance
            diff = target_flowrate - flowrate
            print('relative error: {:.2f}'.format(abs(diff)/max(flowrate, target_flowrate)))
            pressure = self.get_pressure(pressure_channel)
            const = 0.005  # which proportionality constant do we need ?
            new_pressure = max(min(15.0, pressure + const * diff), 0.0)
            print(f'new_pressure {new_pressure}')
            self.set_pressure(new_pressure, pressure_channel)
        else:
            pass
        # rajouter I de 0.01 (min)

    def regulate_pressure_pid(self):  # maybe add channel as argument later
        flowrate = self.get_flowrate()
        print('flowrate {:.0f}'.format(flowrate))
        new_pressure = float(self.pid(flowrate))
        print(f'new_pressure {new_pressure}')
        self.set_pressure(new_pressure, log_entry=False)

# first tests with a simple version where the channels are not specified (we would need signal overloading in the worker thread... to be explored later)
    def start_pressure_regulation_loop(self, target_flowrate):
        self.regulating = True
        # self.regulate_pressure(target_flowrate)

        # new version with simple pid
        self.pid = self.init_pid(setpoint=target_flowrate)

        # regulate the pressure, using a worker thread
        worker = RegulationWorker(target_flowrate)
        worker.signals.sigRegulationWaitFinished.connect(self.pressure_regulation_loop)
        self.threadpool.start(worker)

    def stop_pressure_regulation_loop(self):
        self.regulating = False

    def pressure_regulation_loop(self, target_flowrate):  # if simple pid works well, the target flowrate argument can be removed because not needed
        # self.regulate_pressure(target_flowrate)
        self.regulate_pressure_pid()
        if self.regulating:
            # enter in a loop until the regulating mode is stopped
            worker = RegulationWorker(target_flowrate)
            worker.signals.sigRegulationWaitFinished.connect(self.pressure_regulation_loop)
            self.threadpool.start(worker)

    def start_volume_measurement(self, target_volume, sampling_interval):
        self.measuring_volume = True
        self.total_volume = 0
        self.time_since_start = 0
        if self.total_volume < target_volume:
            self.target_volume_reached = False
        # start summing up the total volume, using a worker thread
        worker = VolumeCountWorker(target_volume, sampling_interval)
        worker.signals.sigIntegrationIntervalFinished.connect(self.volume_measurement_loop)
        self.threadpool.start(worker)

    def volume_measurement_loop(self, target_volume, sampling_interval):
        flowrate = self.get_flowrate()
        self.total_volume += flowrate * sampling_interval / 60  # abs(flowrate) ???
        self.time_since_start += sampling_interval
        self.sigUpdateVolumeMeasurement.emit(int(self.total_volume), self.time_since_start)
        print(f'Total volume: {self.total_volume:.0f} ul')
        if self.total_volume < target_volume:
            self.target_volume_reached = False
        else:
            self.target_volume_reached = True
            self.sigTargetVolumeReached.emit()

        if not self.target_volume_reached and self.measuring_volume:  # second condition is necessary to stop measurement via GUI button
            # enter in a loop until the target_volume is reached
            worker = VolumeCountWorker(target_volume, sampling_interval)
            worker.signals.sigIntegrationIntervalFinished.connect(self.volume_measurement_loop)
            self.threadpool.start(worker)

    def stop_volume_measurement(self):
        self.measuring_volume = False
        self.target_volume_reached = True  # do we need this ?


    def start_rinsing(self, duration):
        self.rinsing_enabled = True
        self._daq_logic.start_rinsing(duration)

    def stop_rinsing(self):
        """ This method is used to manually stop rinsing before specified duration (in start_rinsing) has elapsed. """
        self.rinsing_enabled = False
        self._daq_logic.stop_rinsing()

    def rinsing_finished(self):
        """ Callback of signal sigRinsingDurationFinished from connected daq logic.
        Inform the GUI that the rinsing time has elapsed. """
        self.rinsing_enabled = False
        self.sigRinsingFinished.emit()


    def disable_pressure_setting(self):
        """ This method provides a security to avoid using the set pressure button on GUI, for example during Tasks. """
        self.sigDisablePressureAction.emit()

    def enable_pressure_setting(self):
        """ This method resets set pressure button on GUI to callable state, for example after Tasks. """
        self.sigEnablePressureAction.emit()

















