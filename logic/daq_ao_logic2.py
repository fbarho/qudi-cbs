#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed March 24, 2021

@author: fbarho

A general module to control any DAQ functionality (analog input / output, digital input / output)
except the laser control which is handled by a dedicated module (lasercontrol_logic)

Used for the DAQ on RAMM setup. This module may be reorganized later into individual parts for different functionality.
"""

from core.connector import Connector
from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic
from qtpy import QtCore
from time import sleep


class WorkerSignals(QtCore.QObject):
    """ Defines the signals available from a running worker thread """

    sigFinished = QtCore.Signal()


class Worker(QtCore.QRunnable):
    """ Worker thread to monitor the pressure and the flowrate every x seconds when measuring mode is on

    The worker handles only the waiting time, and emits a signal that serves to trigger the update indicators """

    def __init__(self, duration, *args, **kwargs):
        super(Worker, self).__init__()
        self.signals = WorkerSignals()
        self.duration = duration

    @QtCore.Slot()
    def run(self):
        """ """
        sleep(self.duration)
        self.signals.sigFinished.emit()


class DAQaoLogic(GenericLogic):
    """ Controls the DAQ analog output and allows to set a digital output line for triggering
    """

    # declare connectors
    daq = Connector(interface='Base')

    # signals
    sigRinsingDurationFinished = QtCore.Signal()

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        # activate if necessary
        # self.threadlock = Mutex()

        self.threadpool = QtCore.QThreadPool()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._daq = self.daq()

    def on_deactivate(self):
        """ Perform required deactivation. """
        pass


    def read_piezo(self):
        """
        """
        return self._daq.read_piezo()

    def move_piezo(self, pos, autostart=True, timeout=10):
        """
        """
        self._daq.move_piezo(pos, autostart=True, timeout=10)

    def write_to_do_channel(self, num_samp, digital_write, channel):
        """ use the digital output as trigger """
        self._daq.write_to_do_channel(num_samp, digital_write, channel)

    def read_do_channel(self, num_samp, channel):
        return self._daq.read_do_channel(num_samp, channel)

    def write_to_pump_ao_channel(self, voltage, autostart=True, timeout=10):
        self._daq.write_to_pump_ao_channel(voltage, autostart, timeout)

    def start_rinsing(self, duration):
        self.write_to_pump_ao_channel(-3.0)
        worker = Worker(duration)
        worker.signals.sigFinished.connect(self.stop_rinsing)
        self.threadpool.start(worker)

    def stop_rinsing(self):
        self.write_to_pump_ao_channel(0.0)
        self.sigRinsingDurationFinished.emit()








