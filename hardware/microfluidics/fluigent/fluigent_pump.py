import Fluigent.SDK as fgt  # only supported on Windows
from time import sleep


class FluigentController(object):

    def __init__(self, *args, **kwargs):
        super().__init__()

    def on_activate(self):
        # Detect all controllers
        SNs, types = fgt.fgt_detect()
        controllerCount = len(SNs)
        print('Number of controllers detected: {}'.format(controllerCount))

        # List all found controllers' serial number and type
        for i, sn in enumerate(SNs):
            print('Detected instrument at index: {}, ControllerSN: {}, type: {}' \
                  .format(i, sn, str(types[i])))

        ## Initialize specific instruments
        # Initialize only specific instrument controllers here If you do not want
        # a controller in the list or if you want a specific order (e.g. LineUP
        # before MFCS instruments), rearrange parsed SN table
        fgt.fgt_init(SNs)

        ## Get the number of channels of each type

        # Get total number of initialized pressure channels
        print('Total number of pressure channels: {}'.format(fgt.fgt_get_pressureChannelCount()))

        # Get total number of initialized pressure channels
        print('Total number of sensor channels: {}'.format(fgt.fgt_get_sensorChannelCount()))

        # Get total number of initialized TTL channels
        print('Total number of TTL channels: {}'.format(fgt.fgt_get_TtlChannelCount()))

        ## Get detailed information about all controllers

        controllerInfoArray = fgt.fgt_get_controllersInfo()
        for i, controllerInfo in enumerate(controllerInfoArray):
            print('Controller info at index: {}'.format(i))
            print(controllerInfo)

        ## Get detailed information about all pressure channels

        pressureInfoArray = fgt.fgt_get_pressureChannelsInfo()
        for i, pressureInfo in enumerate(pressureInfoArray):
            print('Pressure channel info at index: {}'.format(i))
            print(pressureInfo)

        ## Get detailed information about all sensor channels

        sensorInfoArray, sensorTypeArray = fgt.fgt_get_sensorChannelsInfo()
        for i, sensorInfo in enumerate(sensorInfoArray):
            print('Sensor channel info at index: {}'.format(i))
            print(sensorInfo)
            print("Sensor type: {}".format(sensorTypeArray[i]))
        #
        # ## Get detailed information about all TTL channels
        #
        # ttlInfoArray = fgt.fgt_get_TtlChannelsInfo()
        # for i, ttlInfo in enumerate(ttlInfoArray):
        #     print('TTL channel info at index: {}'.format(i))
        #     print(ttlInfo)

        # # initialization
        # fgt.fgt_init()

    def on_deactivate(self):
        fgt.fgt_close()

    def set_pressure(self, channel, value):
        fgt.fgt_set_pressure(channel, value)

    def get_pressure(self, channel):
        return fgt.fgt_get_pressure(channel)




if __name__ == '__main__':
    mcfs = FluigentController()
    mcfs.on_activate()
    unit = fgt.fgt_get_sensorUnit(0)
    print(unit)
    min_sensor, max_sensor = fgt.fgt_get_sensorRange(0)
    print("Range {:0.2f} to {:0.2f} {}".format(min_sensor, max_sensor, unit))
    meas = fgt.fgt_get_sensorValue(0)
    print('meaured {:0.2f} {}'.format(meas, unit))

    p_unit = fgt.fgt_get_pressureUnit(0)
    p_min,  p_max = fgt.fgt_get_pressureRange(0)
    print("Pressure range: {}, {} {}".format(p_min, p_max, p_unit))
    p = fgt.fgt_get_pressure(0)
    print('pressure: {}'.format(p))
    fgt.fgt_set_pressure(0, 0.5)
    print('waiting..')
    sleep(7)
    p = fgt.fgt_get_pressure(0)
    print('pressure: {}'.format(p))

    # mcfs.set_pressure(0, 10)  # pressure in mbar
    # sleep(5)
    # p = mcfs.get_pressure(0)
    # print(p)
    # mcfs.set_pressure(0, 0)
    # sleep(5)
    # p = mcfs.get_pressure(0)
    # print(p)
    mcfs.on_deactivate()



## also play a bit with the examples on Fluigents Github repo :
# https://github.com/Fluigent/fgt-SDK/blob/master/Python/examples/