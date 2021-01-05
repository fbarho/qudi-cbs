# -*- coding: utf-8 -*-

"""
This file contains the Qudi Interface for a camera.


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

from core.interface import abstract_interface_method
from core.meta import InterfaceMetaclass


class CameraInterface(metaclass=InterfaceMetaclass):
    """ This interface is used to manage and visualize a simple camera
    """

    # set the internal attributes _full_width, _full_height,
    # and, if has_temp returns true: _default_temperature
    # if has_shutter returns true: _shutter

    @abstract_interface_method
    def get_name(self):
        """ Retrieve an identifier of the camera that the GUI can print

        @return string: name for the camera
        """
        pass

    @abstract_interface_method
    def get_size(self):
        """ Retrieve size of the image in pixel

        @return tuple: Size (width, height)
        """
        pass

    @abstract_interface_method
    def support_live_acquisition(self):
        """ Return whether or not the camera can take care of live acquisition

        @return bool: True if supported, False if not
        """
        pass

    @abstract_interface_method
    def start_live_acquisition(self):
        """ Start a continuous acquisition

        @return bool: Success ?
        """
        pass

    @abstract_interface_method
    def start_single_acquisition(self):
        """ Start a single acquisition

        @return bool: Success ?
        """
        pass

    @abstract_interface_method
    def stop_acquisition(self):
        """ Stop/abort live or single acquisition

        @return bool: Success ?
        """
        pass

    @abstract_interface_method
    def get_acquired_data(self):
        """ Return an array of last acquired image.

        @return numpy array: image data in format [[row],[row]...]

        Each pixel might be a float, integer or sub pixels
        """
        pass

    @abstract_interface_method
    def set_exposure(self, exposure):
        """ Set the exposure time in seconds

        @param float exposure: desired new exposure time

        @return float: set new exposure time
        """
        pass

    @abstract_interface_method
    def get_exposure(self):
        """ Get the exposure time in seconds

        @return float exposure time
        """
        pass

    @abstract_interface_method
    def set_gain(self, gain):
        """ Set the gain

        @param float gain: desired new gain

        @return float: new exposure gain
        """
        pass

    @abstract_interface_method
    def get_gain(self):
        """ Get the gain

        @return float: exposure gain
        """
        pass

    @abstract_interface_method
    def get_ready_state(self):
        """ Is the camera ready for an acquisition ?

        @return bool: ready ?
        """
        pass

    # new interface functions not in the original qudi version
    @abstract_interface_method
    def has_temp(self):
        """ Does the camera support setting of the temperature?

        if this function returns true, make sure that get_temperature, set_temperature, is_cooler_on and _set_cooler
        are implemented the attribute _default_temperature should be also be set in the hardware module
        
        @return bool: has temperature ?
        """
        pass

    @abstract_interface_method
    def has_shutter(self):
        """ Is the camera equipped with a mechanical shutter?

        if this function returns true, the attribute _shutter should also be defined in the hardware module

        @return bool: has shutter ?
        """
        pass

    @abstract_interface_method
    def start_movie_acquisition(self, n_frames):
        """ set the conditions to save a movie and start the acquisition

        @param int n_frames: number of frames

        @return bool: Success ?
        """
        pass

    @abstract_interface_method
    def finish_movie_acquisition(self):
        """ resets the conditions used to save a movie to default

        @return bool: Success ?
        """
        pass

    @abstract_interface_method
    def wait_until_finished(self):
        """ waits until an acquisition is finished

        @return None
        """
        pass

    @abstract_interface_method
    def get_most_recent_image(self):
        """ Return an array of last acquired image.

        @return numpy array: image data in format [[row],[row]...]

        Each pixel might be a float, integer or sub pixels
        """
        pass

    @abstract_interface_method
    def set_image(self, hbin, vbin, hstart, hend, vstart, vend):
        """ Sets a ROI on the sensor surface

        @param int hbin: number of pixels to bin horizontally
        @param int vbin: number of pixels to bin vertically.
        @param int hstart: Start column (inclusive)
        @param int hend: End column (inclusive)
        @param int vstart: Start row (inclusive)
        @param int vend: End row (inclusive).
        """
        pass
