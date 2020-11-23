from core.module import Base
from core.configoption import ConfigOption
from interface.daq_interface import DaqInterface


class DummyDaq(Base, DaqInterface):
    """ Dummy DAQ with analog output channels for the control of an OTF.

    Example config for copy-paste:
        dummy_daq:
            module.Class: 'daq.dummy_daq.DummyDaq'
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
            wavelengths:
                - '405 nm'
                - '488 nm'
                - '512 nm'
                - '633 nm'

            # please give belonging elements in the same order in each category ao_channels, voltage_ranges, wavelengths
    """

    # config
    _ao_channels = ConfigOption('ao_channels', missing='error')  # list  ['/Dev1/AO0', '/Dev1/AO1', ..]
    _ao_voltage_ranges = ConfigOption('ao_voltage_ranges', missing='error')  # list of lists [[0, 10], [0, 10], ..]
    _wavelengths = ConfigOption('wavelengths', missing='error')


    def on_activate(self):
        """ Initialization steps when module is called.
        """
        if len(self._ao_channels) > len(self._ao_voltage_ranges):
            self.log.error('Specify at least as many ao_voltage_ranges as ao_channels!')

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
