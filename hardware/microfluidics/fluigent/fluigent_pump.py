import Fluigent.SDK as fgt  # only supported on Windows
from core.module import Base
from interface.microfluidic_pump_interface import MicrofluidicsPumpInterface


class FluigentController(Base, MicrofluidicsPumpInterface):
    """ Hardware class representing the Fluigent Microfluidics Controllers

    Example config for copy-paste:

    fluigent_microfluidics:
        module.Class: 'microfluidics.fluigent.fluigent_pump.FluigentController'

    """

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        # Detect all controllers
        SNs, types = fgt.fgt_detect()
        controller_count = len(SNs)
        self.log.debug('Number of controllers detected: {}'.format(controller_count))

        # initialize controllers
        fgt.fgt_init()

        self.pressure_channel = 0  # or from config ?
        self.sensor_channel = 0
        #
        # ## Get the number of channels of each type
        #
        # # Get total number of initialized pressure channels
        # print('Total number of pressure channels: {}'.format(fgt.fgt_get_pressureChannelCount()))
        #
        # # Get total number of initialized pressure channels
        # print('Total number of sensor channels: {}'.format(fgt.fgt_get_sensorChannelCount()))
        #
        # # Get total number of initialized TTL channels
        # print('Total number of TTL channels: {}'.format(fgt.fgt_get_TtlChannelCount()))
        #
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
    def set_pressure(self, value):
        channel = self.pressure_channel
        fgt.fgt_set_pressure(channel, value)

    def get_pressure(self):
        channel = self.pressure_channel
        return fgt.fgt_get_pressure(channel)

    def get_pressure_unit(self):
        channel = self.pressure_channel
        return fgt.fgt_get_pressureUnit(channel)

    def get_pressure_range(self):
        channel = self.pressure_channel()
        p_min,  p_max = fgt.fgt_get_pressureRange(channel)
        return p_min, p_max

    # methods for sensor channels
    def get_flowrate(self):
        channel = self.sensor_channel
        return fgt.fgt_get_sensorValue(channel)

    def get_sensor_unit(self):
        channel = self.sensor_channel
        return fgt.fgt_get_sensorUnit(channel)

    def get_sensor_range(self):
        channel = self.sensor_channel
        min_sensor, max_sensor = fgt.fgt_get_sensorRange(channel)
        return min_sensor, max_sensor


    # version for one pressure channel and one sensor channel only. should be improved
    # maybe interate over the number of channels and use a dictionary as return value for measurements ?
    # like for the motors

    #also improve to have error codes and handle exceptions.