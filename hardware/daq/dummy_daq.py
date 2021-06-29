from core.module import Base
from core.configoption import ConfigOption
from interface.daq_interface import DaqInterface
from interface.lasercontrol_interface import LasercontrolInterface


class DummyDaq(Base, LasercontrolInterface, DaqInterface):
    """ Dummy DAQ with analog output channels for the control of an OTF.

    Example config for copy-paste:
        dummy_daq:
            module.Class: 'daq.dummy_daq.DummyDaq'
            wavelengths:
                - '405 nm'
                - '488 nm'
                - '512 nm'
                - '633 nm'
            ao_channels:
                - '/Dev1/AO0'
                - '/Dev1/AO1'
                - '/Dev1/AO2'
                - '/Dev1/AO3'
            ao_voltage_ranges:
                - [0, 10]
                - [0, 10]
                - [0, 10]
                - [0, 10]


            # please give belonging elements in the same order in each category ao_channels, voltage_ranges, wavelengths
    """

    # config
    _ao_channels = ConfigOption('ao_channels', missing='error')  # list  ['/Dev1/AO0', '/Dev1/AO1', ..]
    _ao_voltage_ranges = ConfigOption('ao_voltage_ranges', missing='error')  # list of lists [[0, 10], [0, 10], ..]
    _wavelengths = ConfigOption('wavelengths', missing='error')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initialization steps when module is called.
        """
        if (len(self._ao_channels) != len(self._ao_voltage_ranges)) or (len(self._ao_channels) != len(self._wavelengths)):
            self.log.error('Specify equal numbers of ao channels, voltage ranges and OTF input channels!')

    def on_deactivate(self):
        """ Required deactivation.
        """
        pass

    def get_dict(self):
        """ Retrieves the channel name and the corresponding voltage range for each analog output from the
        configuration file and associates it to the laser wavelength which is controlled by this channel.

        Make sure that the config contains all the necessary elements.

        @returns: laser_dict
        """
        laser_dict = {}

        for i, item in enumerate(
                self._wavelengths):  # use any of the lists retrieved as config option, just to have an index variable
            label = 'laser{}'.format(i + 1)  # create a label for the i's element in the list starting from 'laser1'

            dic_entry = {'label': label,
                         'wavelength': self._wavelengths[i],
                         'channel': self._ao_channels[i],
                         'ao_voltage_range': self._ao_voltage_ranges[i]}

            laser_dict[dic_entry['label']] = dic_entry

        return laser_dict

    def apply_voltage(self, voltage, channel):
        """
        """
        print(f'Applied {voltage} V to channel {channel}.')

    def set_up_do_channel(self):
        """ create a task and its virtual channel for the digital output

        @return: int error code: ok = 0, error = -1
        """
        return 0

    def close_do_task(self):
        """ close the digital output task if there is one
        """
        pass

    def send_trigger(self):
        self.log.info('Send trigger called')

    # mock methods for different functionality such as on RAMM setup
    def write_to_pump_ao_channel(self, voltage, autostart, timeout):
        pass
