# -*- coding: utf-8 -*-

"""
Dummy implementation for camera_interface.

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import numpy as np
import time
from core.module import Base
from core.configoption import ConfigOption
from interface.camera_interface import CameraInterface


class CameraDummy(Base, CameraInterface):
    """ Dummy hardware for camera interface

    Example config for copy-paste:

    camera_dummy:
        module.Class: 'camera.camera_dummy.CameraDummy'
        support_live: True
        camera_name: 'Dummy camera'
        resolution: (1280, 720)
        exposure: 0.1 
        gain: 1.0
    """

    _support_live = ConfigOption('support_live', True)
    _camera_name = ConfigOption('camera_name', 'iXon Ultra 897')  # 'Dummy camera' 'iXon Ultra 897'
    _resolution = ConfigOption('resolution', (720, 1280))  # indicate (nb rows, nb cols) because row-major config is used in gui module

    _live = False
    _acquiring = False
    _exposure = ConfigOption('exposure', .1) 
    _gain = ConfigOption('gain', 1.)
    _has_temp = False
    _has_shutter = False

    # uncomment if _has_temp = True
    # temperature = 17
    # _default_temperature = 12

    image_size = _resolution
    n_frames = 1

    _full_width = 0
    _full_height = 0

    _progress = 0

    _frame_transfer = False

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._full_width = self._resolution[1]
        self._full_height = self._resolution[0]

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self.stop_acquisition()

    def get_name(self):
        """ Retrieve an identifier of the camera that the GUI can print

        @return string: name for the camera
        """
        return self._camera_name

    def get_size(self):
        """ Retrieve size of the image in pixel

        @return tuple: Size (width, height)
        """
        return self.image_size

    def support_live_acquisition(self):
        """ Return whether or not the camera can take care of live acquisition

        @return bool: True if supported, False if not
        """
        return self._support_live

    def start_live_acquisition(self):
        """ Start a continuous acquisition

        @return bool: Success ?
        """
        if self._support_live:
            self._live = True
            self._acquiring = False

    def start_single_acquisition(self):
        """ Start a single acquisition

        @return bool: Success ?
        """
        if self._live:
            return False
        else:
            self._acquiring = True
            time.sleep(float(self._exposure+10/1000))
            self._acquiring = False
            return True

    def stop_acquisition(self):
        """ Stop/abort live or single acquisition

        @return bool: Success ?
        """
        self._live = False
        self._acquiring = False

    def get_acquired_data(self):
        """ Return an array of last acquired image.

        @return numpy array: image data in format [[row],[row]...]

        Each pixel might be a float, integer or sub pixels
        """
        if self.n_frames > 1:
            data = self._data_generator(size=(self.n_frames, self.image_size[0], self.image_size[1])) # * self._exposure * self._gain
        else:
            data = self._data_generator(size=self.image_size) #  * self._exposure * self._gain
        # data = data.astype(np.int16)
        return data

    def set_exposure(self, exposure):
        """ Set the exposure time in seconds

        @param float exposure: desired new exposure time

        @return float: newly set exposure time
        """
        self._exposure = exposure
        return self._exposure

    def get_exposure(self):
        """ Get the exposure time in seconds

        @return float exposure time
        """
        return self._exposure

    def set_gain(self, gain):
        """ Set the gain

        @param float gain: desired new gain

        @return float: new exposure gain
        """
        self._gain = gain
        return self._gain

    def get_gain(self):
        """ Get the gain

        @return float: exposure gain
        """
        return self._gain

    def get_ready_state(self):
        """ Is the camera ready for an acquisition ?

        @return bool: ready ?
        """
        return not (self._live or self._acquiring)
    
    def has_temp(self):
        """ Does the camera support setting of the temperature?
        
        @return bool: has temperature ?
        """
        return self._has_temp

    # for tests do as if temperature available..
    # uncomment if needed
    # def set_temperature(self, temp):
    #     self.temperature = temp
    #
    # def get_temperature(self):
    #     return self.temperature
    #
    # def is_cooler_on(self):
    #     return 1

    def has_shutter(self):
        """ Is the camera equipped with a shutter?

        @return bool: has shutter ?
        """
        return self._has_shutter

    def start_movie_acquisition(self, n_frames):
        """ set the conditions to save a movie and start the acquisition

        @param int n_frames: number of frames

        @return bool: Success ?
        """
        # handle the variables indicating the status
        if self.support_live_acquisition():
            self._live = True   # allow the user to select if image should be shown or not; set self._live accordingly
            self._acquiring = False
        self.n_frames = n_frames
        self.log.info('started movie acquisition')
        return True

    def finish_movie_acquisition(self):
        """ resets the conditions used to save a movie to default

        @return bool: Success ?
        """
        self._live = False
        self._acquiring = False
        self.n_frames = 1
        self.log.info('movie acquisition finished')
        return True

    def wait_until_finished(self):
        """ waits until an acquisition is finished

        @return None
        """
        time.sleep(1)

    def get_most_recent_image(self):
        """ Returns an np array of the most recent image.

        Used for live display on gui during save procedures"""
        data = np.random.normal(size=self.image_size) # * self._exposure * self._gain
        # data = data.astype(np.int16)  # type conversion
        return data

    def set_image(self, hbin, vbin, hstart, hend, vstart, vend):
        """ Allows to reduce the actual sensor size We don't use the binning parameters but they are needed in the
        function call to be conform with syntax of andor camera """
        self.image_size = (abs(vend-vstart)+1, abs(hend-hstart)+1, )  # rows, cols
        return 0

    # mock method to get data which is equivalent to kinetic series (n_frames > 1 allowed)
    def _data_generator(self, size):
        """ Allows to generate 2D or 3D data
        @param: int tuple size (width, height) or (depth, width, height)
        @return: np.array(float) data
        """
        data = np.random.normal(size=size)
        return data

    # just for tests of the gui  # pseudo-interface functions specific to andor camera
    def _set_spool(self, active, mode, filenamestem, framebuffer):
        """ Simulates the spooling functionality of the andor camera.
         This function must be available if camera name is set to iXon Ultra 897
         """
        self.log.info('camera dummy: started spooling')

    def get_kinetic_time(self):
        """ Simulates kinetic time method of andor camera
        This function must be available if camera name is set to iXon Ultra 897"""
        if self._frame_transfer:
            return self._exposure + 0.123
        else:
            return self._exposure + 0.765421

    def get_progress(self):
        """ retrieves the total number of acquired images during a movie acquisition"""
        n_frames = self.n_frames
        self._progress += 1
        progress = self._progress
        if progress == n_frames:
            self._live = False
            self._progress = 0
            return n_frames
        return progress


    def _set_frame_transfer(self, transfer_mode):
        if transfer_mode == 1:
            self._frame_transfer = True
            self.log.info('Camera dummy: activated frame transfer mode, transfer_mode {}'.format(transfer_mode))
        elif transfer_mode == 0:
            self._frame_transfer = False
            self.log.info('Camera dummy: deactivated frame transfer mode, transfer_mode {}'.format(transfer_mode))
        else:
            self.log.info('Camera dummy: specify the transfer_mode to set frame transfer, transfer_mode {}'.format(transfer_mode))

