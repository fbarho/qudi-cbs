from nifpga import Session

bitfile = 'C:\\Users\\sCMOS-1\\Desktop\\LabView\\Current version\\Time lapse\\HUBBLE_FTL_v7_LabView 64bit\\FPGA\\FPGA Bitfiles\\FPGAv0_FPGATarget_FPGAinitialize_WOZhc21U0uw.lvbitx'  # specify path
resource = 'RIO0'

with Session(bitfile=bitfile, resource=resource) as session:
    # Reset stops the logic on the FPGA and puts it in the default state.
    # May substitue reset with download if your bitfile doesn't support it.
    session.reset()

    # Add initialization code here!
    # Write initial values to controls while the FPGA logic is stopped.

    # Start the logic on the FPGA
    session.run()

    # Add code that interacts with the FPGA while it is running here


# just some basic tests on communication with FPGA
# transform it later into a qudi compatible format