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

    def get_pressure(self):
        return self._pump.get_pressure()

    def set_pressure(self, pressure):
        self._pump.set_pressure(pressure)
        # maybe add a message to log ..  or handle this at the hardware level ?

    def get_pressure_range(self):
        return self._pump.get_pressure()

    def get_pressure_unit(self):
        return self._pump.get_pressure_unit()

    def get_flowrate(self):
        return self._pump.get_flowrate()

    def get_flowrate_range(self):
        return self._pump.get_sensor_range()

    def get_flowrate_unit(self):
        return self._pump.get_sensor_unit()


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





