# -*- coding: utf-8 -*-
"""
Qudi-CBS

This module contains the logic to control the microfluidics pump and flowrate sensor.

An extension to Qudi.

@author: F. Barho

Created on Thu Mars 4 2021
-----------------------------------------------------------------------------------

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
-----------------------------------------------------------------------------------
"""
import numpy as np
from time import sleep
import math
from simple_pid import PID

from qtpy import QtCore
from logic.generic_logic import GenericLogic
from core.configoption import ConfigOption
from core.connector import Connector


# ======================================================================================================================
# Worker classes
# ======================================================================================================================

class WorkerSignals(QtCore.QObject):
    """ Defines the signals available from a running worker thread.

    For simplicity, contains all the signals for the different child classes of QRunnable
    (although each child class uses only one of these signals). """

    sigFinished = QtCore.Signal()
    sigRegulationWaitFinished = QtCore.Signal(float)  # parameter: target_flowrate
    sigIntegrationIntervalFinished = QtCore.Signal(float, float)  # parameters: target_volume, integration_interval


class MeasurementWorker(QtCore.QRunnable):
    """ Worker thread to monitor the pressure and the flowrate every x seconds when measuring mode is on.

    The worker handles only the waiting time, and emits a signal that serves to trigger the update of indicators on GUI.
    """

    def __init__(self, *args, **kwargs):
        super(MeasurementWorker, self).__init__(*args, **kwargs)
        self.signals = WorkerSignals()

    @QtCore.Slot()
    def run(self):
        """ """
        sleep(1)  # 1 second as time constant
        self.signals.sigFinished.emit()


class RegulationWorker(QtCore.QRunnable):
    """ Worker thread to regulate the pressure every 1 second when regulation loop is on.

    The worker handles only the waiting time, and emits a signal that serves to trigger the next regulation step. """

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
    """ Worker thread to measure the injected volume of buffer or probe

    The worker handles only the waiting time, and emits a signal that serves to trigger a new sampling. """

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


# ======================================================================================================================
# Logic class
# ======================================================================================================================

class FlowcontrolLogic(GenericLogic):
    """
    Class containing the logic to control the microfluidics pump and flowrate sensor.
    The microfluidics pump can either be handled by a flowboard (if it is part of the Fluigent system) or by a DAQ.
    The pump for needle rinsing is handled by a DAQ.
    # connection to daq logic instead of daq ..

    Example config for copy-paste:

    flowcontrol_logic:
        module.Class: 'flowcontrol_logic.FlowcontrolLogic'
        connect:
            flowboard: 'flowboard_dummy'
            daq_ao_logic: 'daq_logic.....'
    """
    # declare connectors
    flowboard = Connector(interface='MicrofluidicsInterface')
    daq_logic = Connector(interface='DAQaoLogic')

    # signals
    sigUpdateFlowMeasurement = QtCore.Signal(float, float)
    sigUpdatePressureSetpoint = QtCore.Signal(float)
    sigUpdateVolumeMeasurement = QtCore.Signal(int, int)
    sigTargetVolumeReached = QtCore.Signal()
    sigRinsingFinished = QtCore.Signal()
    sigDisableFlowActions = QtCore.Signal()
    sigEnableFlowActions = QtCore.Signal()

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
    pid_sample_time = 0.1  # in s, frequency for the PID update in simple_pid package

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self.threadpool = QtCore.QThreadPool()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # connector
        self._flowboard = self.flowboard()
        self._daq_logic = self.daq_logic()
        self.set_pressure(0.0)

        # signals from connected logic
        self._daq_logic.sigRinsingDurationFinished.connect(self.rinsing_finished)

    def on_deactivate(self):
        """ Perform required deactivation. """
        self.set_pressure(0.0)

# ----------------------------------------------------------------------------------------------------------------------
# Low level methods for pressure settings
# ----------------------------------------------------------------------------------------------------------------------

    def get_pressure(self, channels=None):
        """ Get current pressure value of the corresponding list of channel or all channels.

        :param: list channels: optional, list of channels of which pressure value will be measured
        :return: float or list of floats: pressure value of the single queried channel or all channels
        """
        if len(self._flowboard.pressure_channel_IDs) > 0:  # pump is controlled by flowboard
            pressure = self._flowboard.get_pressure(channels)  # returns a dictionary: {0: pressure_channel_0}
            pressure = [*pressure.values()]  # retrieve only the values from the dictionary and convert into list
            if len(pressure) == 1:
                return pressure[0]
            else:
                return pressure
        else:
            pressure = 0.0 # add here the steps needed to read the pressure if the pump is controlled by a daq
            return pressure

    def set_pressure(self, pressures, log_entry=True, channels=None):
        """
        @param: float or float list pressures: pressure to be set to a given channel
        @param: bool log_entry: make log entry optional, for example to avoid overloading logger while running a pressure regulation loop
        @param: int list channels: optional, needed in case more than one pressure channel is available
        """
        if len(self._flowboard.pressure_channel_IDs) > 0:  # pump is controlled by flowboard
            if not channels:
                if not isinstance(pressures, float):  # a list is given  # to do: modify so that this message is not raised when int format is used for pressrue value
                    self.log.warning('Channels must be specified if more than one pressure value shall be set.')
                else:
                    param_dict = {}
                    param_dict[0] = pressures  # maybe modify in case another pump has a different way of addressing its channel (adapt by config; default_channel_ID ?)
                    unit = self.get_pressure_unit()
                    self._flowboard.set_pressure(param_dict)
                    if log_entry:
                        self.log.info(f'Pressure set to {pressures} {unit}')
                    self.sigUpdatePressureSetpoint.emit(pressures)
            else:
                param_dict = dict(zip(channels, pressures))
                self._flowboard.set_pressure(param_dict)
        else:
            pass # add here the steps needed to set pressure if pump is controlled by a daq

    def get_pressure_range(self, channels=None):
        """
        @param: list channels: optional, list of channels from which pressure range value will be retrieved
        """
        if len(self._flowboard.pressure_channel_IDs) > 0:  # pump is controlled by flowboard
            pressure_range = self._flowboard.get_pressure_range(channels)  # returns a dictionary: {0: pressure_range_channel_0}
            pressure_range = [*pressure_range.values()]  # retrieve only the values from the dictionary and convert into list
            # if len(pressure_range) < 2: # to reorganize for airyscan setup
            if len(pressure_range) == 1:
                return pressure_range[0]
            else:
                return pressure_range
        else:
            return 10  # arbitrary value for the moment # add here the steps needed to set pressure if pump is controlled by a daq

    def get_pressure_unit(self, channels=None):
        """
        @param: list channels: optional, list of channels from which pressure range unit will be retrieved
        """
        if len(self._flowboard.pressure_channel_IDs) > 0:  # pump is controlled by flowboard
            pressure_unit = self._flowboard.get_pressure_unit(channels)  # returns a dictionary: {0: pressure_unit_channel_0}
            pressure_unit = [*pressure_unit.values()]  # retrieve only the values from the dictionary and convert into list
            # if len(pressure_unit) < 2: # to reorganize for airyscan setup
            if len(pressure_unit) == 1:
                return pressure_unit[0]
            else:
                return pressure_unit
        else:
            return 'mbar'  # add here the corresponding unit if pump is controlled by a daq

# ----------------------------------------------------------------------------------------------------------------------
# Low level methods for flowrate measurement
# ----------------------------------------------------------------------------------------------------------------------

    def get_flowrate(self, channels=None):
        """ Get the current flowrate of the corresponding sensor channel(s) or all sensor channels.

        :param list channels: optional, flowrate of a specific channel or a list of channels.
                                If None, all channels are queried.
        :return float or list of floats flowrate: flowrate of a single queried channel
                                                  or a list of flowrates of all channels
                                                  or a list of the channels specified as parameter.
        """
        flowrate = self._flowboard.get_flowrate(channels)  # returns a dictionary: {0: flowrate_channel_0}
        flowrate = [*flowrate.values()]  # retrieve only the values from the dictionary and convert into list
        if len(flowrate) == 1:
            return flowrate[0]
        else:
            return flowrate

    def get_flowrate_range(self, channels=None):
        """ Get the flowrate range of the corresponding sensor channel(s) or all sensor channels.

        :param list channels: optional, flowrate range of a specific channel or a list of channels.
                                If None, all channels are queried.
        :return float or list of floats flowrate_range: flowrate  range of a single queried channel
                                                        or a list of flowrate ranges of all channels
                                                        or a list of the channels specified as parameter.
        """
        flowrate_range = self._flowboard.get_sensor_range(channels)  # returns a dictionary: {0: sensor_range_channel_0}
        flowrate_range = [*flowrate_range.values()]  # retrieve only the values from the dictionary and convert into list
        if len(flowrate_range) == 1:
            return flowrate_range[0]
        else:
            return flowrate_range

    def get_flowrate_unit(self, channels=None):
        """ Get the flowrate unit of the corresponding sensor channel(s) or all sensor channels.

        :param list channels: optional, flowrate unit of a specific channel or a list of channels.
                                If None, all channels are queried.
        :return float or list of floats flowrate_unit: flowrate unit of a single queried channel
                                                        or a list of flowrate units of all channels
                                                        or a list of the channels specified as parameter.
        """
        flowrate_unit = self._flowboard.get_sensor_unit(channels)  # returns a dictionary: {0: sensor_unit_channel_0}
        flowrate_unit = [*flowrate_unit.values()]  # retrieve only the values from the dictionary and convert into list
        if len(flowrate_unit) == 1:
            return flowrate_unit[0]
        else:
            return flowrate_unit

# ----------------------------------------------------------------------------------------------------------------------
# Methods for continuous processes (flowrate measurement loop, pressure regulation loop, volume count, needle rinsing)
# ----------------------------------------------------------------------------------------------------------------------

# Flowrate measument loop ----------------------------------------------------------------------------------------------

    # in case multiplexing shall be implemented, the signal sigUpdateFlowMeasurement could be overloaded,
    # such as sigUpdateFlowrate = QtCore.Signal(list, list), pressure and flowrate would be lists in this case.
    def start_flow_measurement(self):
        """ Start a continuous measurement of the flowrate and the pressure.
        :param: None
        :return: None
        """
        self.measuring_flowrate = True
        # monitor the pressure and flowrate, using a worker thread
        worker = MeasurementWorker()
        worker.signals.sigFinished.connect(self.flow_measurement_loop)
        self.threadpool.start(worker)

    def flow_measurement_loop(self):
        """ Continous measuring of the flowrate and the pressure at a defined sampling rate using a worker thread.
        :param: None
        :return: None
        """
        pressure = self.get_pressure()
        flowrate = self.get_flowrate()
        self.sigUpdateFlowMeasurement.emit(pressure, flowrate)
        if self.measuring_flowrate:
            # enter in a loop until measuring mode is switched off
            worker = MeasurementWorker()
            worker.signals.sigFinished.connect(self.flow_measurement_loop)
            self.threadpool.start(worker)

    def stop_flow_measurement(self):
        """ Stops the measurement of flowrate and pressure.
        Emits a signal to update the GUI with the most recent values.
        :param: None
        :return: None
        """
        self.measuring_flowrate = False
        # get once again the latest values
        pressure = self.get_pressure()
        flowrate = self.get_flowrate()
        self.sigUpdateFlowMeasurement.emit(pressure, flowrate)

# Pressure regulation loop ----------------------------------------------------------------------------------------------
    def init_pid(self, setpoint):
        pid = PID(self.p_gain, self.i_gain, self.d_gain, setpoint=setpoint)
        pid.output_limits = (0, 15)
        pid.sample_time = self.pid_sample_time
        return pid

    # def regulate_pressure(self, target_flowrate, sensor_channel=None, pressure_channel=None):
    #     """
    #     @param: float target_flowrate
    #     @param: int sensor_channel: ID of the sensor channel
    #     (use this method only for a single channel so that flowrate is returned as float and not as float list,
    #     but you can indicate which channel in case there are more than one)
    #     @param: int pressure_channel: ID of the pressure channel
    #     (use this method only for a single channel so that pressure is returned as float and not as float list,
    #     but you can indicate which channel in case there are more than one)
    #     """
    #     flowrate = self.get_flowrate(sensor_channel)
    #     print('flowrate {:.0f}'.format(flowrate))
    #     # if 10 != abs(flowrate - target_flowrate):  # which precision ?   #use math.isclose function instead when precision defined
    #     if not math.isclose(flowrate, target_flowrate, rel_tol=0.05, abs_tol=0):  # allow 5 % tolerance
    #         diff = target_flowrate - flowrate
    #         print('relative error: {:.2f}'.format(abs(diff)/max(flowrate, target_flowrate)))
    #         pressure = self.get_pressure(pressure_channel)
    #         const = 0.005  # which proportionality constant do we need ?
    #         new_pressure = max(min(15.0, pressure + const * diff), 0.0)
    #         print(f'new_pressure {new_pressure}')
    #         self.set_pressure(new_pressure, pressure_channel)
    #     else:
    #         pass
    #     # rajouter I de 0.01 (min)

    def regulate_pressure_pid(self):  # maybe add channel as argument later
        flowrate = self.get_flowrate()
        print('flowrate {:.0f}'.format(flowrate))
        new_pressure = float(self.pid(flowrate))
        print(f'new_pressure {new_pressure}')
        self.set_pressure(new_pressure, log_entry=False)

# first tests with a simple version where the channels are not specified (we would need signal overloading in the worker thread... to be explored later)
    def start_pressure_regulation_loop(self, target_flowrate):
        self.regulating = True
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

# Volume count ---------------------------------------------------------------------------------------------------------

    # in case multiplexing shall be implemented, the signal sigUpdateVolumeMeasurement could be overloaded,
    # such as sigVolumeMeasurement = QtCore.Signal(list, int), self.total_volume would be a list in this case
    # and the calculation of self.total_volume in volume_measurement_loop would need to be modified.
    def start_volume_measurement(self, target_volume, sampling_interval):
        """ Start a continuous measurement of the injected volume.
        :param: int target_volume: target volume to be injected.
                                Volume measurement will be stopped when target volume is reached (necessary for tasks).
        :param: float: sampling interval: time in seconds as sampling period.
        :return: None
        """
        self.measuring_volume = True
        self.total_volume = 0.0
        self.time_since_start = 0
        if self.total_volume < target_volume:
            self.target_volume_reached = False
        # start summing up the total volume, using a worker thread
        worker = VolumeCountWorker(target_volume, sampling_interval)
        worker.signals.sigIntegrationIntervalFinished.connect(self.volume_measurement_loop)
        self.threadpool.start(worker)

    def volume_measurement_loop(self, target_volume, sampling_interval):
        """ Perform a step in the volume count loop.
        :param: int target_volume: target volume to be injected.
                                Volume measurement will be stopped when target volume is reached (necessary for tasks).
        :param: float: sampling interval: time in seconds as sampling period.
        :return: None
        """
        flowrate = self.get_flowrate()
        self.total_volume += flowrate * sampling_interval / 60
        self.total_volume = np.round(self.total_volume, decimals=3)  # as safety to avoid entering into the else part when target volume is not yet reached due to data overflow
        self.time_since_start += sampling_interval
        # print(self.total_volume, self.time_since_start, target_volume)
        self.sigUpdateVolumeMeasurement.emit(int(self.total_volume), self.time_since_start)
        if self.total_volume < target_volume:
            self.target_volume_reached = False
        else:
            self.target_volume_reached = True
            self.measuring_volume = False
            self.sigTargetVolumeReached.emit()

        if not self.target_volume_reached and self.measuring_volume:  # second condition is necessary to stop measurement via GUI button
            # enter in a loop until the target_volume is reached
            worker = VolumeCountWorker(target_volume, sampling_interval)
            worker.signals.sigIntegrationIntervalFinished.connect(self.volume_measurement_loop)
            self.threadpool.start(worker)

        # when using np.inf as target_volume, the comparison ended sometimes up in the wrong branch (else) because np.inf was sometimes a large negative number

    def stop_volume_measurement(self):
        """ Stops the volume count. This method is used to stop the volume count using the GUI buttons,
        when no real target volume is provided.
        :param: None
        :return: None
        """
        self.measuring_volume = False
        self.target_volume_reached = True

# Rinse needle ---------- ----------------------------------------------------------------------------------------------
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

# ----------------------------------------------------------------------------------------------------------------------
# Methods to handle the user interface state
# ----------------------------------------------------------------------------------------------------------------------

    def disable_flowcontrol_actions(self):
        """ This method provides a security to avoid using the set pressure, start volume measurement and start rinsing
        button on GUI, for example during Tasks. """
        self.sigDisableFlowActions.emit()

    def enable_flowcontrol_actions(self):
        """ This method resets flowcontrol action buttons on GUI to callable state, for example after Tasks. """
        self.sigEnableFlowActions.emit()