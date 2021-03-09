import numpy as np
from core.module import Base
from interface.microfluidic_pump_interface import MicrofluidicsPumpInterface


class PumpDummy(Base, MicrofluidicsPumpInterface):
    """ Dummy implementation of the microfluidics pump and flowrate sensor

    Example config for copy-paste:

    pump_dummy:
        module.Class: 'microfluidics.pump_dummy.PumpDummy'

    """
    pressure = 0
    max_pressure = 350   # in mbar
    max_flow = 11000  # in ul/min

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        pass

    def on_deactivate(self):
        pass

    def set_pressure(self, value):
        self.pressure = value

    def get_pressure(self):
        fluctuation = np.random.normal()
        return self.pressure + fluctuation

    def get_pressure_unit(self):
        return 'mbar'

    def get_pressure_range(self):
        return 0, self.max_pressure

    def get_flowrate(self):
        return np.random.normal()

    def get_sensor_unit(self):
        return 'ul/min'

    def get_sensor_range(self):
        return -self.max_flow, self.max_flow