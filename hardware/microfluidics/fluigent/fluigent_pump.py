import Fluigent.SDK as fgt  # only supported on Windows
from core.module import Base
from interface.microfluidic_pump_interface import MicrofluidicsPumpInterface
from core.configoption import ConfigOption


class FluigentController(Base, MicrofluidicsPumpInterface):
    """ Hardware class representing the Fluigent Microfluidics Controllers

    Example config for copy-paste:

    fluigent_microfluidics:
        module.Class: 'microfluidics.fluigent.fluigent_pump.FluigentController'
        pressure_channel_IDs:
            - 0
        sensor_channel_IDs:
            - 0

    """
    pressure_channel_IDs = ConfigOption('pressure_channel_IDs', missing='error')
    sensor_channel_IDs = ConfigOption('sensor_channel_IDs', missing='error')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):

        # Detect all controllers
        SNs, types = fgt.fgt_detect()
        controller_count = len(SNs)
        self.log.debug('Number of controllers detected: {}'.format(controller_count))

        # initialize controllers
        fgt.fgt_init()
        # add here the check if an error was raised during fgt_init and write a comprehensible error message to the log.

        num_pressure_channels = fgt.fgt_get_pressureChannelCount()
        if num_pressure_channels < len(self.pressure_channel_IDs):
            self.log.warning('Less pressure channels detected than given in config file!')

        num_sensor_channels = fgt.fgt_get_sensorChannelCount()
        if num_sensor_channels < len(self.sensor_channel_IDs):
            self.log.warning('Less sensor channels detected than given in config file!')

        # ## Get detailed information about all controllers
        #
        # controllerInfoArray = fgt.fgt_get_controllersInfo()
        # for i, controllerInfo in enumerate(controllerInfoArray):
        #     print('Controller info at index: {}'.format(i))
        #     print(controllerInfo)
        #
        # ## Get detailed information about all pressure channels
        #
        # pressureInfoArray = fgt.fgt_get_pressureChannelsInfo()
        # for i, pressureInfo in enumerate(pressureInfoArray):
        #     print('Pressure channel info at index: {}'.format(i))
        #     print(pressureInfo)
        # #
        # # ## Get detailed information about all sensor channels
        # #
        # sensorInfoArray, sensorTypeArray = fgt.fgt_get_sensorChannelsInfo()
        # for i, sensorInfo in enumerate(sensorInfoArray):
        #     print('Sensor channel info at index: {}'.format(i))
        #     print(sensorInfo)
        #     print("Sensor type: {}".format(sensorTypeArray[i]))
        #



    def on_deactivate(self):
        fgt.fgt_close()

    # methods for pressure channels
    def set_pressure(self, param_dict):
        """ Set new pressure value to a channel

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'pressure_channel': <the-pressure-setpoint>}.
                                 'pressure_channel' must correspond to a pressure_channel_ID given in the config
        """
        # add also a check that new value in allowed range
        for key, value in param_dict.items():  # param_dict has the format {0: 20} for example
            if key in self.pressure_channel_IDs:
                fgt.fgt_set_pressure(key, value)
            else:
                self.log.info('Specified channel not available')

    def get_pressure(self, param_list=None):
        """ Gets current pressure of the corresponding channel or all channels.

        @param list param_list: optional, pressure of a specific channel
        @return dict: with keys being the channel IDs and values the pressure value
        """
        if not param_list:
            pressures = [fgt.fgt_get_pressure(channel) for channel in self.pressure_channel_IDs]
            pressure_dict = dict(zip(self.pressure_channel_IDs, pressures))
            return pressure_dict
        else:
            pressure_dict = {}
            for channel in param_list:
                if channel in self.pressure_channel_IDs:
                    pressure = fgt.fgt_get_pressure(channel)
                    pressure_dict[channel] = pressure
                else:
                    self.log.info('Specified pressure channel not available')
            return pressure_dict

    def get_pressure_unit(self, param_list=None):
        """ Gets pressure unit of the corresponding channel or all channels.

        @param list param_list: optional, pressure unit of a specific channel
        @return dict: with keys being the channel IDs and values the pressure value
        """
        if not param_list:
            pressure_units = [fgt.fgt_get_pressureUnit(channel) for channel in self.pressure_channel_IDs]
            pressure_unit_dict = dict(zip(self.pressure_channel_IDs, pressure_units))
            return pressure_unit_dict
        else:
            pressure_unit_dict = {}
            for channel in param_list:
                if channel in self.pressure_channel_IDs:
                    pressure_unit = fgt.fgt_get_pressureUnit(channel)
                    pressure_unit_dict[channel] = pressure_unit
                else:
                    self.log.info('Specified pressure channel not available')
            return pressure_unit_dict

    def get_pressure_range(self, param_list=None):
        """ Gets pressure range of the corresponding channel or all channels.

        @param list param_list: optional, pressure range of a specific channel
        @return dict: with keys being the channel IDs and values the pressure range as tuple
        """
        if not param_list:
            pressure_range = [fgt.fgt_get_pressureRange(channel) for channel in self.pressure_channel_IDs]
            pressure_range_dict = dict(zip(self.pressure_channel_IDs, pressure_range))
            return pressure_range_dict
        else:
            pressure_range_dict = {}
            for channel in param_list:
                if channel in self.pressure_channel_IDs:
                    pressure_range = fgt.fgt_get_pressureRange(channel)
                    pressure_range_dict[channel] = pressure_range
                else:
                    self.log.info('Specified pressure channel not available')
            return pressure_range_dict

    # methods for sensor channels
    def get_flowrate(self, param_list=None):
        """ Gets current flowrate of the corresponding sensor channel or all sensor channels.

        @param list param_list: optional, flowrate of a specific sensor channel
        @return dict: with keys being the sensor channel IDs and values the flowrates
        """
        if not param_list:
            flowrates = [fgt.fgt_get_sensorValue(channel) for channel in self.sensor_channel_IDs]
            flowrate_dict = dict(zip(self.sensor_channel_IDs, flowrates))
            return flowrate_dict
        else:
            flowrate_dict = {}
            for channel in param_list:
                if channel in self.sensor_channel_IDs:
                    flowrate = fgt.fgt_get_sensorValue(channel)
                    flowrate_dict[channel] = flowrate
                else:
                    self.log.info('Specified sensor channel not available')
            return flowrate_dict

    def get_sensor_unit(self, param_list=None):
        """ Gets sensor unit of the corresponding sensor channel or all sensor channels.

        @param list param_list: optional, sensor unit of a specific channel
        @return dict: with keys being the channel IDs and values the corresponding sensor unit
        """
        if not param_list:
            sensor_units = [fgt.fgt_get_sensorUnit(channel) for channel in self.sensor_channel_IDs]
            sensor_unit_dict = dict(zip(self.sensor_channel_IDs, sensor_units))
            return sensor_unit_dict
        else:
            sensor_unit_dict = {}
            for channel in param_list:
                if channel in self.sensor_channel_IDs:
                    sensor_unit = fgt.fgt_get_sensorUnit(channel)
                    sensor_unit_dict[channel] = sensor_unit
                else:
                    self.log.info('Specified sensor channel not available')
            return sensor_unit_dict

    def get_sensor_range(self, param_list=None):
        """ Gets sensor range of the corresponding sensor channel or all sensor channels.

        @param list param_list: optional, sensor range of a specific sensor channel
        @return dict: with keys being the channel IDs and values the sensor range as tuple
        """
        if not param_list:
            sensor_range = [fgt.fgt_get_sensorRange(channel) for channel in self.sensor_channel_IDs]
            sensor_range_dict = dict(zip(self.sensor_channel_IDs, sensor_range))
            return sensor_range_dict
        else:
            sensor_range_dict = {}
            for channel in param_list:
                if channel in self.sensor_channel_IDs:
                    sensor_range = fgt.fgt_get_sensorRange(channel)
                    sensor_range_dict[channel] = sensor_range
                else:
                    self.log.info('Specified sensor channel not available')
            return sensor_range_dict

    # to do: use of error codes and exception handlling
