from core.interface import abstract_interface_method
from core.meta import InterfaceMetaclass


class ValveInterface(metaclass=InterfaceMetaclass):
    """ This interface is used to control a microfluidic pump system
    """

    @abstract_interface_method
    def get_valve_position(self, valve):
        pass

    @abstract_interface_method
    def set_valve_position(self, valve, position):
        pass

    @abstract_interface_method
    def get_valve_dict(self):
        pass

