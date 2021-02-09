from nifpga import Session
import numpy as np
import ctypes

# initialize bitfile
# bitfile = 'C:\\Users\\sCMOS-1\\Desktop\\LabView\\Current version\\Time lapse\\HUBBLE_FTL_v7_LabView 64bit\\FPGA\\FPGA Bitfiles\\FPGAv0_FPGATarget_FPGAinitialize_WOZhc21U0uw.lvbitx'  # specify path
# laser control bitfile
bitfile = 'C:\\Users\\sCMOS-1\\Desktop\\LabView\\Current version\\Time lapse\\HUBBLE_FTL_v7_LabView 64bit\\FPGA\\FPGA Bitfiles\\FPGAv0_FPGATarget_FPGAlasercontrol_rVrWu38G2Ac.lvbitx'
# bitfile = 'C:\\Users\\sCMOS-1\\qudi-cbs\\hardware\\fpga\\FPGA\\FPGA_Bitfiles\\FPGAv0_FPGATarget_FPGAlasercontrol_rVrWu38G2Ac.lvbitx'
resource = 'RIO0'

with Session(bitfile=bitfile, resource=resource) as session:
    # Reset stops the logic on the FPGA and puts it in the default state.
    # May substitue reset with download if your bitfile doesn't support it.
    session.reset()

    # Add initialization code here!
    # Write initial values to controls while the FPGA logic is stopped.
    laser1_control = session.registers['405']
    laser2_control = session.registers['488']
    laser3_control = session.registers['561']
    laser4_control = session.registers['640']


    # Start the logic on the FPGA
    session.run()

    # # Add code that interacts with the FPGA while it is running here
    print(laser1_control.datatype)
    print(laser1_control.__len__())
    print(laser1_control.name)
    # print(laser1_control._read_func)
    # print(laser1_control._write_func)

    data = np.single(0)
    laser1_control.write(data)


# just some basic tests on communication with FPGA
# transform it later into a qudi compatible format