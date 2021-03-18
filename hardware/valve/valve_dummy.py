import numpy as np
from core.module import Base
from interface.valvepositioner_interface import ValveInterface


class ValveDummy(Base, ValveInterface):
    """ Dummy implementation of the microfluidics pump and flowrate sensor

    Example config for copy-paste:

    valve_dummy:
        module.Class: 'valve.valve_dummy.ValveDummy'

    """
    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        pass

    def on_deactivate(self):
        pass

    def get_valve_position(self, valve):
        pass

    def set_valve_position(self, valve, position):
        pass

    def get_valve_dict(self):
        pass