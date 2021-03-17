from core.interface import abstract_interface_method
from core.meta import InterfaceMetaclass


class MicrofluidicsPumpInterface(metaclass=InterfaceMetaclass):
    """ This interface is used to control a microfluidic pump system
    """

    @abstract_interface_method
    def set_pressure(self, param_dict=None):
        """ Set new pressure value to a channel

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'pressure_channel': <the-pressure-setpoint>}.
                                 'pressure_channel' must correspond to a pressure_channel_ID given in the config
        """
        pass

    @abstract_interface_method
    def get_pressure(self, param_list=None):
        """ Gets current pressure of the corresponding channel or all channels.

        @param list param_list: optional, pressure of a specific channel
        @return dict: with keys being the channel IDs and values the pressure value
        """
        pass

    @abstract_interface_method
    def get_pressure_unit(self, param_list=None):
        """ Gets pressure unit of the corresponding channel or all channels.

        @param list param_list: optional, pressure unit of a specific channel
        @return dict: with keys being the channel IDs and values the pressure value
        """
        pass

    @abstract_interface_method
    def get_pressure_range(self, param_list=None):
        """ Gets pressure range of the corresponding channel or all channels.

        @param list param_list: optional, pressure range of a specific channel
        @return dict: with keys being the channel IDs and values the pressure range as tuple
        """
        pass

    @abstract_interface_method
    def get_flowrate(self, param_list=None):
        """ Gets current flowrate of the corresponding sensor channel or all sensor channels.

        @param list param_list: optional, flowrate of a specific sensor channel
        @return dict: with keys being the sensor channel IDs and values the flowrates
        """
        pass

    @abstract_interface_method
    def get_sensor_unit(self, param_list=None):
        """ Gets sensor unit of the corresponding sensor channel or all sensor channels.

        @param list param_list: optional, sensor unit of a specific channel
        @return dict: with keys being the channel IDs and values the corresponding sensor unit
        """
        pass

    @abstract_interface_method
    def get_sensor_range(self, param_list=None):
        """ Gets sensor range of the corresponding sensor channel or all sensor channels.

        @param list param_list: optional, sensor range of a specific sensor channel
        @return dict: with keys being the channel IDs and values the sensor range as tuple
        """
        pass


