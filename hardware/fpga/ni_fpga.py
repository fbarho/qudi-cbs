from nifpga import Session
import numpy as np
import ctypes

# initialize bitfile
# bitfile = 'C:\\Users\\sCMOS-1\\Desktop\\LabView\\Current version\\Time lapse\\HUBBLE_FTL_v7_LabView 64bit\\FPGA\\FPGA Bitfiles\\FPGAv0_FPGATarget_FPGAinitialize_WOZhc21U0uw.lvbitx'  # specify path
# laser control bitfile
bitfile = 'C:\\Users\\sCMOS-1\\Desktop\\LabView\\Current version\\Time lapse\\HUBBLE_FTL_v7_LabView 64bit\\FPGA\\FPGA Bitfiles\\FPGAv0_FPGATarget_FPGAlasercontrol_o8wg7Z4+KAQ.lvbitx'
# bitfile = 'C:\\Users\\sCMOS-1\\Desktop\\LabView\\Current version\\Time lapse\\HUBBLE_FTL_v7_LabView 64bit\\FPGA\\FPGA Bitfiles\\FPGAv0_FPGATarget_FPGAlasercontrol_rVrWu38G2Ac.lvbitx'
# bitfile = 'C:\\Users\\sCMOS-1\\qudi-cbs\\hardware\\fpga\\FPGA\\FPGA_Bitfiles\\FPGAv0_FPGATarget_FPGAlasercontrol_rVrWu38G2Ac.lvbitx'
resource = 'RIO0'

with Session(bitfile=bitfile, resource=resource) as session:
    # Reset stops the logic on the FPGA and puts it in the default state.
    # May substitue reset with download if your bitfile doesn't support it.
    session.reset()

    # Add initialization code here!
    # Write initial values to controls while the FPGA logic is stopped.
    # laser1_control = session.registers['405']
    # laser2_control = session.registers['488']
    laser3_control = session.registers['561']
    # laser4_control = session.registers['640']
    control_val = session.registers['value']
    print(session.registers)

    # reset_counter = session.registers['Reset counter']
    # count = session.registers['Count(uSec)']
    conversion_factor = 2**16 /100
    data = 10 * conversion_factor
    print(type(data))
    data = np.int16(0 * conversion_factor)
    print(data)
    print(type(data))
    laser3_control.write(data)
    val = control_val.read()
    print(type(val))
    print(val)

    # Start the logic on the FPGA
    session.run()

    # for i in range(10):
    #     print(i)
    #     data = np.int16(i * conversion_factor)
    #     laser3_control.write(data)
    #     print(control_val.read())
    print(control_val.read())

    # # Add code that interacts with the FPGA while it is running here
    # print(laser1_control.datatype)
    # print(laser1_control.__len__())
    # print(laser1_control.name)
    # print(laser1_control._read_func)
    # print(laser1_control._write_func)
    #
    # data = np.uint32(0)
    # laser1_control.write(data)


# just some basic tests on communication with FPGA
# transform it later into a qudi compatible format