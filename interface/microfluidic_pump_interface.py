from core.interface import abstract_interface_method
from core.meta import InterfaceMetaclass


class MicrofluidicsPumpInterface(metaclass=InterfaceMetaclass):
    """ This interface is used to control a microfluidic pump system
    """

    @abstract_interface_method
    def set_pressure(self, value):
        pass

    @abstract_interface_method
    def get_pressure(self):
        pass

    @abstract_interface_method
    def get_pressure_unit(self):
        pass

    @abstract_interface_method
    def get_pressure_range(self):
        pass

    @abstract_interface_method
    def get_flowrate(self):
        pass

    @abstract_interface_method
    def get_sensor_unit(self):
        pass

    @abstract_interface_method
    def get_sensor_range(self):
        pass