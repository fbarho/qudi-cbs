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


class WorkerSignals(QtCore.QObject):
    """ Defines the signals available from a running worker thread """

    sigFinished = QtCore.Signal()


class Worker(QtCore.QRunnable):
    """ Worker thread to monitor the camera temperature every 5 seconds

    The worker handles only the waiting time, and emits a signal that serves to trigger the update of the temperature
    display """

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
    sigProgress = QtCore.Signal(int)  # sends the number of already acquired images

    sigUpdateCamStatus = QtCore.Signal(str, str, str, str)

    timer = None

    enabled = False

    has_temp = False
    has_shutter = False

    _exposure = 1.
    _gain = 1.
    _temperature = 25  # use any value it will be overwritten during on activate if sensor temperature is available
    temperature_setpoint = _temperature
    _last_image = None
    _kinetic_time = None

    _hardware = None

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
        self.has_temp = self._hardware.has_temp()
        if self.has_temp:
            # self.temperature_setpoint = self._hardware.get_temperature() # to initialize
            self.temperature_setpoint = self._hardware._default_temperature  # to test. this may be more convenient.
        self.has_shutter = self._hardware.has_shutter()

        # update the private variables _exposure, _gain, _temperature and has_temp
        self.get_exposure()
        self.get_gain()
        self.get_temperature()

        # timer is used for refreshing the display of the camera image
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
        """ Get kinetic time (Andor camera only) """
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
        if not self.has_temp:
            pass
        else:
            # make sure the cooler is on
            if self._hardware.is_cooler_on() == 0:
                self._hardware._set_cooler(True)

            # hand the new temperature value over to the camera hardware module
            self.temperature_setpoint = temp  # store the desired temperature value to compare against current temperature value if desired temperature already reached
            self._hardware.set_temperature(temp)

            # monitor the current temperature of the sensor, using a worker thread to avoid freezing gui actions when set_temperature is called via GUI
            worker = Worker()
            worker.signals.sigFinished.connect(self.update_temperature)
            self.threadpool.start(worker)

    def get_temperature(self):
        """ Get temperature of hardware, if accessible """
        if not self.has_temp:
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

    def start_single_acquistion(self):  # watch out for the typo !!
        """ Take a single camera image
        """
        self._hardware.start_single_acquisition()
        self._last_image = self._hardware.get_acquired_data()
        self.sigUpdateDisplay.emit()
        self.sigAcquisitionFinished.emit()

#  #################################################
# the following functions concern the live display # might be modified when the save video methods are validated
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
#  #########################################################3

    def get_last_image(self):
        """ Return last acquired image """
        return self._last_image

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
        if not self.has_shutter:
            pass
        else:
            return self._hardware._shutter

    def get_cooler_state(self):
        """ retrieves the status of the cooler if there is one (only if has_temp is True)

        @returns str: cooler on, cooler of """
        if not self.has_temp:
            pass
        else:
            cooler_status = self._hardware.is_cooler_on()
            idle = self._hardware.get_ready_state()
            # first check if camera is recording
            if not idle:
                return 'NA'
            else:   # _hardware.is_cooler_on only returns an adapted value when camera is idle
                if cooler_status == 0:
                    return 'Off'
                if cooler_status == 1:
                    return 'On'

    def update_camera_status(self):
        """ retrieves an ensemble of camera status values
        ready: if camera is idle, shutter open / closed if available, cooler on / off if available, temperature value
        emits a signal containing the 4 retrieved status informations as str
        """
        ready_state = self.get_ready_state()
        shutter_state = self.get_shutter_state()
        cooler_state = self.get_cooler_state()
        temperature = str(self.get_temperature())
        self.sigUpdateCamStatus.emit(ready_state, shutter_state, cooler_state, temperature)

    def save_last_image(self, path, fileformat='.tiff'):
        """ saves a single image to disk

        @param: str path: path stem, such as /home/barho/images/2020-12-16/samplename
        @param: str fileformat: default '.tiff' but can be modified if needed. make sure not to forget the dot """

        if self._last_image is None:
            self.log.warning('No image available to save')
            return
        image_data = self._last_image  # alternatively it could use self._hardware.get_acquired_data() .. to check which option is better

        complete_path = self._create_generic_filename(path, '_Image', 'image', fileformat, addfile=False)
        self._save_to_tiff(1, complete_path, image_data)

    def save_video(self, filenamestem, n_frames, display):
        """ Saves n_frames to disk as a tiff stack

        @param: str filenamestem, such as /home/barho/images/2020-12-16/samplename
        @param: int n_frames: number of frames to be saved
        @param: bool display: show images on live display on gui """
        self.enabled = True  # this attribute is used to disable all the other controls which should not be used in parallel
        err = self._hardware.start_movie_acquisition(n_frames)
        if not err:
            self.log.warning('Video acquisition did not start')
        if display:
            self.log.info('display activated')
            # in this first version this might be specific to andor camera
            for i in range(n_frames):
                i += 1
                # self.log.info('image {}'.format(i))  # only for debugging. avoid using this, it slows everything down
                self._last_image = self._hardware.get_most_recent_image()
                self.sigUpdateDisplay.emit()  # try DirectConnection when working on the setup
                sleep(0.01)  # this is used to force enough time for a signal to be transmitted. To be modified using a proper method
            # self.log.info('display loop finished')

        self._hardware.wait_until_finished()  # this is important especially if display is disabled
        image_data = self._hardware.get_acquired_data()  # first get the data before resetting the acquisition mode of the camera
        self._hardware.finish_movie_acquisition()  # reset the attributes and the default acquisition mode
        self.enabled = False

        # data handling
        complete_path = self._create_generic_filename(filenamestem, '_Movie', 'movie', '.tiff', addfile=False)
        # create the PIL.Image object and save it to tiff
        self._save_to_tiff(n_frames, complete_path, image_data)
        self.sigVideoSavingFinished.emit()

    # this function is specific for andor ixon ultra camera
    def do_spooling(self, filenamestem, n_frames, display):
        """ Saves n_frames to disk as a tiff stack without need of data handling within this function.
        Available for andor camera. Useful for large data sets which would be overwritten in the buffer

        @param: str filenamestem, such as /home/barho/images/2020-12-16/samplename
        @param: int n_frames: number of frames to be saved
        @param: bool display: show images on live display on gui """
        self.enabled = True  # this attribute is used to disable all the other controls which should not be used in parallel
        path = self._create_generic_filename(filenamestem, '_Movie', 'movie', '', addfile=False)  # use an empty string for fileformat. this will be handled by the camera itself
        self._hardware._set_spool(1, 7, path, 10)  # parameters: active (1 = yes), method (7 save as tiff), filenamestem, framebuffersize
        err = self._hardware.start_movie_acquisition(n_frames)  # setting kinetics acquisition mode, make sure everything is ready for an acquisition
        if not err:
            self.log.warning('Spooling did not start')
        if display:
            self.log.info('display activated')
            # in this first version this might be specific to andor camera
            for i in range(n_frames):
                i += 1
                # self.log.info('image {}'.format(i))
                self._last_image = self._hardware.get_most_recent_image()
                self.sigUpdateDisplay.emit()
                sleep(0.01)  # this is used to force enough time for a signal to be transmitted. To be modified using a proper method
            # self.log.info('display loop finished')

        # to be tested:
        # while not self._hardware.get_ready_state():
        #     spoolprogress = self._hardware._get_spool_progress()  ## replace this by a more general method get_progress which should be on the interface
        #     self.log.info('progress: {}'.format(spoolprogress))
        #     self.sigProgress.emit(spoolprogress)
        self._hardware.wait_until_finished()
        self._hardware.finish_movie_acquisition()
        self._hardware._set_spool(0, 7, path, 10)  # deactivate spooling
        self.enabled = False
        self.sigSpoolingFinished.emit()

    def _create_generic_filename(self, filenamestem, folder, file, fileformat, addfile):
        """ helper function that creates a generic filename using the following format:

        filenamestem/000_folder/file.tiff
        example: /home/barho/images/2020-12-16/samplename/000_Movie/movie.tiff
        filenamestem is typically generated by the save settings dialog in basic gui but can also entered manually if function is called in console

        @params: str folder: specify the type of experiment (ex. Movie, Snap)
        @params: str file: filename (ex movie, image). do not specify the fileformat.
        @params: str fileformat: specify the type of file (.tiff, .txt, ..). don't forget the point before the type
        @params: bool addfile: if True, the last created folder will again be accessed (needed for metadata saving)

        @returns str complete path
        """
        # check if folder filenamestem exists, if not create it
        if not os.path.exists(filenamestem):
            try:
                os.makedirs(filenamestem)  # recursive creation of all directories on the path
            except Exception as e:
                self.log.error('Error {0}'.format(e))

        # count the subdirectories in the directory filenamestem (non recursive !) to generate an incremental prefix
        dir_list = [name for name in os.listdir(filenamestem) if os.path.isdir(os.path.join(filenamestem, name))]
        number_dirs = len(dir_list)
        if addfile:
            number_dirs -= 1
        prefix = str(number_dirs).zfill(3)
        folder_name = prefix + folder
        path = os.path.join(filenamestem, folder_name)
        # now create this folder
        if not os.path.exists(path):  # we need this condition because metadata will be written in the same folder so the folder may already exist
            try:
                os.makedirs(path)
            except Exception as e:
                self.log.error('Error creating the target folder: {}'.format(e))
        filename = '{0}{1}'.format(file, fileformat)
        complete_path = os.path.join(path, filename)
        return complete_path

    def _save_to_tiff(self, n_frames, path, data):
        """ helper function to save the image data to a tiff file

        creates the PIL.Image object and saves it to tiff

        @params int n_frames: number of frames (needed to distinguish between 2D and 3D data)
        @params str path: complete path where the object is saved to
        @params data: np.array

        @returns None
        """
        # 2D data case (no stack)
        if n_frames == 1:  # formatting of this case needs special treatment .. remove later if not needed
            im = Image.fromarray(data)
            try:
                # conversion to 16 bit tiff
                im.convert('I;16').save(path, format='tiff')
                # unconverted version (32 bit) im.save(path, format='tiff')
                self.log.info('Saved data to file {}'.format(path))
            except:
                self.log.warning('Data not saved')
            return None

        # 3D data (note: z stack is the first dimension)
        else:
            # create the PIL.Image object and save it to tiff
            imlist = []
            for i in range(n_frames):
                im = Image.fromarray(data[i])
                imlist.append(im)
            try:
                # conversion to 16 bit tiff
                # im.convert('I;16').save(path, format='tiff')
                # unconverted version (32 bit)
                imlist[0].save(path, format='tiff', save_all=True, append_images=imlist[1:])
                self.log.info('Saved data to file {}'.format(path))
            except:
                self.log.warning('Data not saved')
            return None
        
    def set_sensor_region(self, hbin, vbin, hstart, hend, vstart, vend):
        """ defines a limited region on the sensor surface, hence accelerating the acquisition

        @param int hbin: number of pixels to bin horizontally
        @param int vbin: number of pixels to bin vertically.
        @param int hstart: Start column (inclusive)
        @param int hend: End column (inclusive)
        @param int vstart: Start row (inclusive)
        @param int vend: End row (inclusive).
        """
        err = self._hardware.set_image(hbin, vbin, hstart, hend, vstart, vend)
        if err < 0:
            self.log.warn('Sensor region not set')
        else:
            self.log.info('Sensor region set to {} x {}'.format(hend-hstart+1, vend-vstart+1))

    def reset_sensor_region(self):
        """ reset to full sensor size """
        width = self._hardware._full_width  # store the full_width in the hardware moduel because _width is overwritten when image is set
        height = self._hardware._full_height  # same goes for height
        err = self._hardware.set_image(1, 1, 1, width, 1, height)
        if err < 0:
            self.log.warn('Sensor region not reset to default')
        else:
            self.log.info('Sensor region reset to default: {} x {}'.format(width, height))
