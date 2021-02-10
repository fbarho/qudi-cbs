from nifpga import Session
import numpy as np
import ctypes
from time import sleep

class Nifpga(object):

    def __init__(self, bitfile, resource, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bitfile = bitfile
        self.resource = resource

    def on_activate(self):
        self.session = Session(bitfile=self.bitfile, resource=self.resource)
        self.laser3_control = self.session.registers['561']
        self.control_val = self.session.registers['value']

    def on_deactivate(self):
        self.write_value(0)  # make sure to switch the laser off before closing the session
        self.session.close()

    def write_value(self, value):
        """
        @param: any numeric type, (recommended int) value: percent of maximal volts to be applied

        if value < 0 or value > 100, value will be rescaled to be in the allowed range """
        value = max(0, value)  # make sure only positive values allowed, reset to zero in case negative value entered
        conv_value = self.convert_value(value)
        self.laser3_control.write(conv_value)
        self.session.run()

    def read_value(self):
        return self.laser3_control.read()
        #return self.control_val.read()  # this is finally not needed because we can read directly the value of laser3_control register

    def convert_value(self, value):
        """ fpga needs int16 (-32768 to + 32767) data format: do rescaling of value to apply in percent of max value

        apply min function to limit the allowed range """
        return min(int(value/100*(2**15-1)), 36767)  # set to maximum in case value > 100


if __name__ == '__main__':
    bitfile = 'C:\\Users\\sCMOS-1\\Desktop\\LabView\\Current version\\Time lapse\\HUBBLE_FTL_v7_LabView 64bit\\FPGA\\FPGA Bitfiles\\FPGAv0_FPGATarget_FPGAlasercontrol_o8wg7Z4+KAQ.lvbitx'
    resource = 'RIO0'
    nifpga = Nifpga(bitfile, resource)
    nifpga.on_activate()
    nifpga.write_value(10)
    print(nifpga.read_value())
    sleep(2)
    nifpga.write_value(0)
    print(nifpga.read_value())
    sleep(2)
    nifpga.write_value(5)
    print(nifpga.read_value())
    sleep(2)
    nifpga.on_deactivate()