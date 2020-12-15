# -*- coding: utf-8 -*-

"""
A module for controlling a camera.

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
from time import sleep
import os
from PIL import Image

from core.connector import Connector
from core.configoption import ConfigOption
from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic
from qtpy import QtCore
import matplotlib.pyplot as plt
import matplotlib as mpl

import datetime
from collections import OrderedDict

class WorkerSignals(QtCore.QObject):
    """ Defines the signals available from a running worker thread """

    sigFinished = QtCore.Signal()

class Worker(QtCore.QRunnable):
    """ Worker thread to monitor the camera temperature every 5 seconds

    The worker handles only the waiting time, and emits a signal that serves to trigger the update of the temperature display"""

    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__()
        self.signals = WorkerSignals()

    @QtCore.Slot()
    def run(self):
        """ """
        sleep(5)
        self.signals.sigFinished.emit()


class CameraLogic(GenericLogic):
    """
    Control a camera.
    """

    # declare connectors
    hardware = Connector(interface='CameraInterface')
    _max_fps = ConfigOption('default_exposure', 20)
    _fps = 20

    # signals
    sigUpdateDisplay = QtCore.Signal()
    sigAcquisitionFinished = QtCore.Signal()
    sigVideoFinished = QtCore.Signal()
    sigVideoSavingFinished = QtCore.Signal()
    sigSpoolingFinished = QtCore.Signal()

    sigExposureChanged = QtCore.Signal(float)
    sigGainChanged = QtCore.Signal(float)
    sigTemperatureChanged = QtCore.Signal(float)

    sigUpdateCamStatus = QtCore.Signal(str, str, str)

    timer = None

    enabled = False
    saving = False

    has_temp = False
    has_shutter = False

    _exposure = 1.
    _gain = 1.
    _temperature = 25 # use any value it will be overwritten during on activate if sensor temperature is available
    temperature_setpoint = _temperature
    _last_image = None
    _kinetic_time = None

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.threadpool = QtCore.QThreadPool()

        # uncomment if needed:
        # self.threadlock = Mutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._hardware = self.hardware()

        self.enabled = False
        self.saving = False
        self.has_temp = self._hardware.has_temp()
        if self.has_temp:
            # self.temperature_setpoint = self._hardware.get_temperature() # to initialize
            self.temperature_setpoint = self._hardware._default_temperature  # to test. it may be more convenient.
        self.has_shutter = self._hardware.has_shutter()

        # update the private variables _exposure, _gain, _temperature and has_temp
        self.get_exposure()
        self.get_gain()
        self.get_temperature()

        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.loop)

    def on_deactivate(self):
        """ Perform required deactivation. """
        pass

    def get_name(self):
        name = self._hardware.get_name()
        return name

    def set_exposure(self, time):
        """ Set exposure of hardware """
        self._hardware.set_exposure(time)
        self.get_exposure()  # needed to update the attribute self._exposure
        # prepare signal sent to indicator on GUI:
        exp = self.get_exposure()
        self.sigExposureChanged.emit(exp)

    def get_exposure(self):
        """ Get exposure of hardware """
        self._exposure = self._hardware.get_exposure()
        self._fps = min(1 / self._exposure, self._max_fps)
        return self._exposure

    # this function is specific to andor camera
    def get_kinetic_time(self):
        if self._hardware.get_name() == 'iXon Ultra 897':
            self._kinetic_time = self._hardware.get_kinetic_time()
            return self._kinetic_time
        else:
            pass

    def set_gain(self, gain):
        """ Set gain of hardware """
        self._hardware.set_gain(gain)
        self.get_gain()  # called to update the attribute self._gain
        # prepare signal sent to indicator on GUI:
        value = self.get_gain()
        self.sigGainChanged.emit(value)

    def get_gain(self):
        """ Get gain of hardware """
        gain = self._hardware.get_gain()
        self._gain = gain
        return gain


    def set_temperature(self, temp):
        """ Set temperature of hardware, if accessible """
        if self.has_temp == False:
            pass
        else:
            # version doing as if new temperature was immediately reached
            # self._hardware.set_temperature(temp)
            # self.get_temperature() # update self._temperature attribute
            # value = self.get_temperature()
            # self.sigTemperatureChanged.emit(value)

            # make sure the cooler is on  # to be tested. or is it preferable to have a cooler on off button on the GUI ?
            if self._hardware.is_cooler_on() == 0:
                self._hardware._set_cooler(True)

            # handle the new temperature value over to the camera hardware module
            self.temperature_setpoint = temp  # store the desired temperature value to compare against current temperature value if desired temperature already reached
            self._hardware.set_temperature(temp)

            # monitor the current temperature of the sensor, using a worker thread to avoid freezing gui actions when set_temperature is called via GUI
            worker = Worker()
            worker.signals.sigFinished.connect(self.update_temperature)
            self.threadpool.start(worker)

    def get_temperature(self):
        """ Get gain of hardware, if accessible """
        if self.has_temp == False:
            self.log.warn('Sensor temperature control not available')
        else:
            temp = self._hardware.get_temperature()
            self._temperature = temp
            return temp

    @QtCore.Slot()
    def update_temperature(self):
        """ helper function to update the display on GUI after a waiting time defined in the Worker class"""

        value = self.get_temperature()  # get the current temperature from the hardware
        self.sigTemperatureChanged.emit(value)

        if abs(value - self.temperature_setpoint) > 3:  # the tolerance of the camera itself is 3 degree
            # enter in a loop until temperature setpoint reached
            worker = Worker()
            worker.signals.sigFinished.connect(self.update_temperature)
            self.threadpool.start(worker)

    def start_single_acquistion(self): # watch out for the typo !!
        """ Take a single camera image
        """
        self._hardware.start_single_acquisition()
        self._last_image = self._hardware.get_acquired_data()
        self.sigUpdateDisplay.emit()
        self.sigAcquisitionFinished.emit()


# these functions concern the live display # might be modified when the save video methods are validated
    def start_loop(self):
        """ Start the data recording loop.
        """
        self.enabled = True
        self.timer.start(1000*1/self._fps)

        if self._hardware.support_live_acquisition():
            self._hardware.start_live_acquisition()
        else:
            self._hardware.start_single_acquisition()

    def stop_loop(self):
        """ Stop the data recording loop.
        """
        self.timer.stop()
        self.enabled = False
        self._hardware.stop_acquisition()
        self.sigVideoFinished.emit()

    def loop(self):
        """ Execute step in the data recording loop: save one of each control and process values
        """
        self._last_image = self._hardware.get_acquired_data()
        self.sigUpdateDisplay.emit()
        if self.enabled:
            self.timer.start(1000 * 1 / self._fps) 
            if not self._hardware.support_live_acquisition():
                self._hardware.start_single_acquisition()  # the hardware has to check it's not busy
##########################################################3


    def get_last_image(self):
        """ Return last acquired image """
        return self._last_image


    def save_last_image(self, path, filename, fileformat='tiff'):

        if self._last_image is None:
            self.log.warning('No image available to save')
            return
        image_data = self._last_image  # alternatively it could use self._hardware.get_acquired_data() .. to check which option is better

        # check if the path exists
        if not os.path.exists(path):
            try:
                os.makedirs(path)  # recursive creation of all directories on the path
            except Exception as e:
                print('Could not create folder {}'.format(e))
                return None

        # discuss if a do not overwrite procedure should be implemented.. but this should not happen with the above generation of a number suffix
        # count the files in the directory (non recursive !) to generate an incremental suffix
        file_list = [name for name in os.listdir(path) if os.path.isfile(os.path.join(path, name))] # and name - 4 last caracters (use regex) == filename
        number_files = len(file_list)
        suffix = str(number_files).zfill(4)
        complete_filename = filename + suffix + '.' + fileformat
        # attention: if the filename is changed then it might be better to restart indexing from 0. We should define the filename generic format ..

        # create the full path name by joining the filename to the folder path
        p = os.path.join(path, complete_filename)

        # create the PIL.Image object and save it to tiff
        im = Image.fromarray(image_data)
        try:
            # conversion to 16 bit tiff
            im.convert('I;16').save(p, format='tiff')
            # unconverted version (32 bit) im.save(p, format='tiff')
            self.log.info('Saved image to file {}'.format(p))
        except:
            self.log.warning('File not saved')
        return None




    def get_ready_state(self):
        """ Is the camera ready for an acquisition ?

        @return bool: ready ?"""
        # version with yes no display
        # state = self._hardware.get_ready_state()
        # if state == True:
        #     return 'Yes'
        # return 'No'
        # version with true false display
        return str(self._hardware.get_ready_state())

    def get_shutter_state(self):
        """ retrieves the status of the shutter if there is one

        @returns str: shutter status """
        if self.has_shutter == False:
            pass
        else:
            return self._hardware._shutter

    def get_cooler_state(self):
        """ retrieves the status of the cooler if there is one (only if has_temp is True)

        @returns str: cooler on, cooler of """
        if self.has_temp == False:
            pass
        else:
            cooler_status = self._hardware.is_cooler_on()
            if cooler_status == 0:
                return 'Off'
            if cooler_status == 1:
                return 'On'

    def update_camera_status(self):
        ready_state = self.get_ready_state()
        shutter_state = self.get_shutter_state()
        cooler_state = self.get_cooler_state()
        self.sigUpdateCamStatus.emit(ready_state, shutter_state, cooler_state)

      
    def do_spooling(self, filenamestem, n_frames):
        self.enabled = True # this attribute is used to disable all the other controls which should not be used in parallel. define if instead here saving should be used 
        self._hardware._set_spool(1, 7, filenamestem, 10)  # parameters: active (1 = yes), method (7 save as tiff), filenamestem, framebuffersize
        err = self._hardware.start_movie_acquisition(n_frames)  # setting kinetics acquisition mode, make sure everything is ready for an acquisition
        if not err:
            self.log.warning('Spooling did not start')
        self._hardware.wait_until_finished()
        self._hardware.finish_movie_acquisition()
        self.enabled = False
        self.sigSpoolingFinished.emit()
            

    def save_video(self, filenamestem, n_frames):
        self.enabled = True # see comment above in do_spooling
        # self._hardware._set_spool(0)  # as security deactivate spooling. 
        err = self._hardware.start_movie_acquisition(n_frames)
        if not err:
            self.log.warning('Video acquisition did not start')
        self._hardware.wait_until_finished()
        self._hardware.finish_movie_acquisition()  # reset the attributes and the default acquisition mode
        self.enabled = False
        self.sigVideoSavingFinished.emit()

        image_data = self._hardware.get_acquired_data()
        # add here the filename handling; path etc

        # create the PIL.Image object and save it to tiff
        if n_frames == 1:  # formatting of this case needs special treatment .. remove later if not needed
            im = Image.fromarray(image_data)
            try:
                # conversion to 16 bit tiff
                im.convert('I;16').save(filenamestem, format='tiff')
                # unconverted version (32 bit) im.save(p, format='tiff')
                self.log.info('Saved movie to file {}'.format(filenamestem))
            except:
                self.log.warning('Movie not saved')
            return None

        else:
            # create the PIL.Image object and save it to tiff
            imlist = []
            for i in range(n_frames):
                im = Image.fromarray(image_data[i])
                imlist.append(im)
            try:
                # conversion to 16 bit tiff
                # im.convert('I;16').save(filenamestem, format='tiff')
                # unconverted version (32 bit)
                imlist[0].save(filenamestem, format='tiff', save_all=True, append_images=imlist[1:])
                self.log.info('Saved movie to file {}'.format(filenamestem))
            except:
                self.log.warning('Movie not saved')
            return None




