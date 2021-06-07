import numpy as np
from core.module import Base
from interface.microfluidic_pump_interface import MicrofluidicsPumpInterface
from core.configoption import ConfigOption


class PumpDummy(Base, MicrofluidicsPumpInterface):
    """ Dummy implementation of the microfluidics pump and flowrate sensor

    Example config for copy-paste:

    pump_dummy:
        module.Class: 'microfluidics.pump_dummy.PumpDummy'
        pressure_channel_IDs:
            - 0
        sensor_channel_IDs:
            - 0

    """
    pressure_channel_IDs = ConfigOption('pressure_channel_IDs', missing='error')
    sensor_channel_IDs = ConfigOption('sensor_channel_IDs', missing='error')

    # store here the values that would normally be queried from the device
    pressure_dict = {}
    pressure_unit_dict = {}
    pressure_range_dict = {}

    sensor_unit_dict = {}
    sensor_range_dict = {}

    max_pressure = 350   # in mbar
    max_flow = 11000  # in ul/min

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        for i in range(len(self.pressure_channel_IDs)):
            self.pressure_dict[i] = 0
            self.pressure_unit_dict[i] = 'mbar'
            self.pressure_range_dict[i] = self.max_pressure

        for i in range(len(self.sensor_channel_IDs)):
            self.sensor_unit_dict[i] = 'ul/min'
            self.sensor_range_dict[i] = (-self.max_flow, self.max_flow)

    def on_deactivate(self):
        pass

    def set_pressure(self, param_dict):
        """ Set new pressure value to a channel

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'pressure_channel': <the-pressure-setpoint>}.
                                 'pressure_channel' must correspond to a pressure_channel_ID given in the config
        """
        for key, value in param_dict.items():  # param_dict has the format {0: 20} for example
            if key in self.pressure_channel_IDs and value <= self.max_pressure:
                self.pressure_dict[key] = value
            else:
                self.log.info('Specified channel not available')

    def get_pressure(self, param_list=None):
        """ Gets current pressure of the corresponding channel or all channels.

        @param list param_list: optional, pressure of a specific channel
        @return dict: with keys being the channel IDs and values the pressure value
        """
        if not param_list:
            return self.pressure_dict
        else:
            for channel in param_list:
                if channel in self.pressure_channel_IDs:
                    return self.pressure_dict[channel]
                else:
                    self.log.info('Specified pressure channel not available')

    def get_pressure_unit(self, param_list=None):
        """ Gets pressure unit of the corresponding channel or all channels.

        @param list param_list: optional, pressure unit of a specific channel
        @return dict: with keys being the channel IDs and values the pressure value
        """
        if not param_list:
            return self.pressure_unit_dict
        else:
            for channel in param_list:
                if channel in self.pressure_channel_IDs:
                    return self.pressure_unit_dict[channel]
                else:
                    self.log.info('Specified pressure channel not available')

    def get_pressure_range(self, param_list=None):
        """ Gets pressure range of the corresponding channel or all channels.

        @param list param_list: optional, pressure range of a specific channel
        @return dict: with keys being the channel IDs and values the pressure range as tuple
        """
        if not param_list:
            return self.pressure_range_dict
        else:
            for channel in param_list:
                if channel in self.pressure_channel_IDs:
                    return self.pressure_range_dict[channel]
                else:
                    self.log.info('Specified pressure channel not available')

    def get_flowrate(self, param_list=None):
        """ Gets current flowrate (some simulated values here) of the corresponding sensor channel or all sensor channels.

        @param list param_list: optional, flowrate of a specific sensor channel
        @return dict: with keys being the sensor channel IDs and values the flowrates
        """
        if not param_list:
            flowrates = [self.pressure_dict[channel] * 5 + 5 * np.random.normal() for channel in self.sensor_channel_IDs]
            flowrate_dict = dict(zip(self.sensor_channel_IDs, flowrates))
            return flowrate_dict
        else:
            flowrate_dict = {}
            for channel in param_list:
                if channel in self.sensor_channel_IDs:
                    flowrate_dict[channel] = self.pressure_dict[channel] * 5 + 5 *np.random.normal()
                else:
                    self.log.info('Specified sensor channel not available')
            return flowrate_dict

    def get_sensor_unit(self, param_list=None):
        """ Gets sensor unit of the corresponding sensor channel or all sensor channels.

        @param list param_list: optional, sensor unit of a specific channel
        @return dict: with keys being the channel IDs and values the corresponding sensor unit
        """
        if not param_list:
            return self.sensor_unit_dict
        else:
            for channel in param_list:
                if channel in self.sensor_channel_IDs:
                    return self.sensor_unit_dict[channel]
                else:
                    self.log.info('Specified sensor channel not available')

    def get_sensor_range(self, param_list=None):
        """ Gets sensor range of the corresponding sensor channel or all sensor channels.

        @param list param_list: optional, sensor range of a specific sensor channel
        @return dict: with keys being the channel IDs and values the sensor range as tuple
        """
        if not param_list:
            return self.sensor_range_dict
        else:
            for channel in param_list:
                if channel in self.sensor_channel_IDs:
                    return self.sensor_range_dict[channel]
                else:
                    self.log.info('Specified sensor channel not available')
