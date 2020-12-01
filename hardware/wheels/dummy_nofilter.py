import numpy as np
from core.module import Base
from core.configoption import ConfigOption
from interface.filterwheel_interface import FilterwheelInterface


class NoFilterDummy(Base, FilterwheelInterface):
    """ This class is used for a setup without filterwheelner

    Example config for copy-paste:

    nofilter_dummy:
        module.Class: 'wheels.dummy_nofilter.NoFilterDummy'
        num_filters: 1
        filterpositions:
            - 1
        filters:
            - 'quad-band filter'
        allowed_lasers:
            - [True, True, True, True]

            # please specify for all elements corresponding information in the same order.
    """

    _num_filters = ConfigOption('num_filters', 1)
    _filternames = ConfigOption('filters', missing='error')
    _positions = ConfigOption('filterpositions', missing='error')
    _allowed_lasers = ConfigOption('allowed_lasers', missing='error')

    position = 1


    def on_activate(self):
        if len(self._filternames) != self._num_filters or len(self._positions) != self._num_filters or len(self._allowed_lasers) != self._num_filters:
            self.log.warning('Please specify name, position, and allowed lasers for each filter')

    def on_deactivate(self):
        pass

    def get_position(self):
        """ Get the current position, from 1 to 6 (or 12) """
        return self.position

    def set_position(self, value):
        """ Set the position to a given value

        @ params: int: value: new position

        @ returns: int: error code: ok = 0
        """
        pass
        #return 0

    def get_filter_dict(self):
        """ Retrieves a dictionary with the following entries:
                    {'filter1': {'label': 'filter1', 'name': str(name), 'position': 1, 'lasers': bool list},
                     'filter2': {'label': 'filter2', 'name': str(name), 'position': 2, 'lasers': bool list},
                    ...
                    }

                    # to be modified: using position as label suffix can lead to problems when not all positions are used and gives some constraints

        @returns: filter_dict
        """
        filter_dict = {}

        for i, item in enumerate(
                self._filternames):  # use any of the lists retrieved as config option, just to have an index variable
            label = 'filter{}'.format(i + 1)  # create a label for the i's element in the list starting from 'filter1'

            dic_entry = {'label': label,
                         'name': self._filternames[i],
                         'position': self._positions[i],
                         'lasers': self._allowed_lasers[i]}

            filter_dict[dic_entry['label']] = dic_entry

        return filter_dict