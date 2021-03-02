# -*- coding: utf-8 -*-
"""
Created on Thu Mars 4 2021

@author: fbarho

This module contains the logic to control the microfluidics pump and flowrate measurement
"""
from qtpy import QtCore
from logic.generic_logic import GenericLogic
from core.configoption import ConfigOption


class FlowcontrolLogic(GenericLogic):
    """
    Class containing the logic to control the microfluidics pump and flowrate measurement

    Example config for copy-paste:

    flowcontrol_logic:
        module.Class: 'flowcontrol_logic.FlowcontrolLogic'
    """

    # signals

    # attributes
    measuring = False

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        pass

    def on_deactivate(self):
        """ Perform required deactivation. """
        pass

    def get_pressure(self):
        pass

    def set_pressure(self, pressure):
        pass

    def get_pressure_range(self):
        pass

    def get_pressure_unit(self):
        pass

    def get_flowrate(self):
        pass

    def get_flowrate_range(self):
        pass

    def get_flowrate_unit(self):
        pass


    def start_flow_measurement(self):
        pass

    def stop_flow_measurement(self):
        pass

    def flow_measurement_loop(self):
        pass


    # # to discuss how to regulate flowrate # add this later
    # def regulate_pressure(self, flowrate):
    #     pass
    # # regulation feedback loop to achieve a desired flowrate




    # def start_tracking(self):
    #     self.tracking = True
    #     # monitor the current stage position, using a worker thread
    #     worker = Worker()
    #     worker.signals.sigFinished.connect(self.tracking_loop)
    #     self.threadpool.start(worker)
    #
    # def stop_tracking(self):
    #     self.tracking = False
    #     # get once again the latest position
    #     position = self.stage_position
    #     self.sigUpdateStagePosition.emit(position)
    #
    # def tracking_loop(self):
    #     position = self.stage_position
    #     self.sigUpdateStagePosition.emit(position)
    #     if self.tracking:
    #         # enter in a loop until tracking mode is switched off
    #         worker = Worker()
    #         worker.signals.sigFinished.connect(self.tracking_loop)
    #         self.threadpool.start(worker)