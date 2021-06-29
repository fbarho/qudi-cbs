# from hardware.motor.aptmotor import APTMotor
import thorlabs_apt as apt
from time import sleep

class ThorlabsFastFilterWheel:
    """ Hardware class representing the Thorlabs motorized filterwheel.
    6 positions

    Example config for copy-paste:

    thorlabs_fast_wheel:
        module.Class: 'wheels.thorlabs_fast_filter_wheel.ThorlabsFastFilterWheel'
        serial_num: 40846334
        num_filters: 6
        filterpositions:
            - 1
            - 2
            - 3
            - 4
            - 5
            - 6
        filters:
            - '700 +/- 37 nm'
            - '600 +/- 25 nm'
            - '488 - 491 / 561 nm'
            - '525 +/- 22.5 nm'
            - '617 +/- 36 nm'
            - '460 +/- 25 nm'
        allowed_lasers:
            - [True, True, True, True]
            - [True, True, True, True]
            - [True, True, True, True]
            - [True, True, True, True]
            - [True, True, True, False]
            - [True, False, True, True]
    """
    serial_number = 40846334

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._motor = None

    def on_activate(self):
        """ Module activation method. """
        # devices = apt.list_available_devices()
        # print(devices)
        self._motor = apt.Motor(self.serial_number)
        self.move_home()

    def on_deactivate(self):
        """ Disconnect from hardware on deactivation. """
        pass

    def move_home(self):
        self._motor.move_home(True)

    def move_by(self, angle):
        self._motor.move_by(angle, blocking=True)

    def move_to(self, position):
        self._motor.move_to(position)

    def get_motor_position(self):
        motor_pos = self._motor.position
        return motor_pos

# ----------------------------------------------------------------------------------------------------------------------
# Filterwheel interface functions
# ----------------------------------------------------------------------------------------------------------------------

    def get_position(self):
        """ Get the current position, from 1 to 6 (or 12).
         :return int position: number of the filterwheel position that is currently set """
        # position = self._query('pos?')
        # return int(position)
        pass

    def set_position(self, target_position):
        """ Set the position to a given value.
        The wheel will take the shorter path. If upward or downward are equivalent, the wheel take the upward path.

        :param: int target_position: position number
        :return: int error code: ok = 0
        """
        # if target_position < self._num_filters + 1:
        #     res = self._write("pos={}".format(int(target_position)))
        #     err = 0
        # else:
        #     self.log.error('Can not go to filter {0}. Filterwheel has only {1} positions'.format(target_position, self._num_filters))
        #     err = -1
        # return err
        pass

    def get_filter_dict(self):
        """ Retrieves a dictionary with the following entries:
                    {'filter1': {'label': 'filter1', 'name': str(name), 'position': 1, 'lasers': bool list},
                     'filter2': {'label': 'filter2', 'name': str(name), 'position': 2, 'lasers': bool list},
                    ...
                    }

                    # all positions of the filterwheel must be defined even when empty.
                    Match the dictionary key 'filter1' to the position 1 etc.

        :return: dict filter_dict
        """
        # filter_dict = {}
        #
        # for i, item in enumerate(
        #         self._filternames):  # use any of the lists retrieved as config option, just to have an index variable
        #     label = 'filter{}'.format(i + 1)  # create a label for the i's element in the list starting from 'filter1'
        #
        #     dic_entry = {'label': label,
        #                  'name': self._filternames[i],
        #                  'position': self._positions[i],
        #                  'lasers': self._allowed_lasers[i]}
        #
        #     filter_dict[dic_entry['label']] = dic_entry
        #
        # return filter_dict
        pass


if __name__ == '__main__':
    wheel = ThorlabsFastFilterWheel()
    wheel.on_activate()
    # wheel.move_home()
    # print('moved to home position')
    # for i in range(6):
    #     wheel.move_by(360/6)
    #     pos = wheel.get_motor_position()
    #     print(f'position {i}: {pos}')
    #     sleep(1)
    wheel.move_to(0)  # 0: filter 1 ;  -60 : filter 2  ; -120 : filter 3 ; filter 4 : -180 ; filter 5 : -240 ; filter 6 : -300



