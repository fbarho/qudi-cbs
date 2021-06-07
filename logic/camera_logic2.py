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
from astropy.io import fits
import yaml

from core.connector import Connector
from core.configoption import ConfigOption
from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic
from qtpy import QtCore

class WorkerSignals(QtCore.QObject):
    """ Defines the signals available from a running worker thread """

    sigFinished = QtCore.Signal()


class LiveImageWorker(QtCore.QRunnable):
    """ Worker thread to update the live image at the desired frame rate

    The worker handles only the waiting time, and emits a signal that serves to trigger the update indicators """

    def __init__(self, time_constant):
        super(LiveImageWorker, self).__init__()
        self.signals = WorkerSignals()
        self.time_constant = time_constant

    @QtCore.Slot()
    def run(self):
        """ """
        sleep(self.time_constant)
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
    sigSaving = QtCore.Signal()
    sigCleanStatusbar = QtCore.Signal()

    sigUpdateCamStatus = QtCore.Signal(str, str, str, str)

    sigLiveStopped = QtCore.Signal()  # informs the GUI that live mode was stopped programatically
    sigDisableCameraActions = QtCore.Signal()
    sigEnableCameraActions = QtCore.Signal()

    # timer = None

    enabled = False  # indicates if the camera is currently acquiring data
    saving = False # indicates if the camera is currently saving a movie

    has_temp = False
    has_shutter = False

    _exposure = 1.
    _gain = 1.
    _temperature = 0  # use any value it will be overwritten during on activate if sensor temperature is available
    temperature_setpoint = _temperature
    _last_image = None
    _kinetic_time = None

    _hardware = None

    fileformat_list = ['tiff', 'fits']

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
            self.temperature_setpoint = self._hardware._default_temperature
        self.has_shutter = self._hardware.has_shutter()

        # update the private variables _exposure, _gain, _temperature
        self.get_exposure()
        self.get_gain()
        self.get_temperature()

        # timer is used for refreshing the display of the camera image at rate fps
        # self.timer = QtCore.QTimer()
        # self.timer.setSingleShot(True)
        # self.timer.timeout.connect(self.loop)

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
        if self.get_name() == 'iXon Ultra 897':
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
            self.temperature_setpoint = temp  # store the desired temperature value to compare against current
            # temperature value if desired temperature already reached
            self._hardware.set_temperature(temp)

            # monitor the current temperature of the sensor, using a worker thread to avoid freezing gui actions when
            # set_temperature is called via GUI worker = Worker() worker.signals.sigFinished.connect(
            # self.update_temperature) self.threadpool.start(worker)

    def get_temperature(self):
        """ Get temperature of hardware, if accessible """
        if not self.has_temp:
            self.log.warn('Sensor temperature control not available')
        # version without acces to temperature while live is on    
#        else:
#            temp = self._hardware.get_temperature()
#            self._temperature = temp
#            idle = self._hardware.get_ready_state()
#            if not idle:
#                return 'NA'
#            else:
#                return temp
        else:
            if self.enabled:  # live mode on
#                self.interrupt_live()
                self.timer.stop() 
                self._hardware.stop_acquisition()
                
            temp = self._hardware.get_temperature()
            self._temperature = temp
            
            if self.enabled:  # restart live mode
#                self.resume_live()
                self.start_loop()
            return temp
                

    # to be removed in a future version
    @QtCore.Slot()
    def update_temperature(self):
        """ helper function to update the display on GUI after a waiting time defined in the Worker class"""
        pass
        # value = self.get_temperature()  # get the current temperature from the hardware
        # self.sigTemperatureChanged.emit(value)
        #
        # if abs(value - self.temperature_setpoint) > 3:  # the tolerance of the camera itself is 3 degree
        #     # enter in a loop until temperature setpoint reached
        #     worker = Worker()
        #     worker.signals.sigFinished.connect(self.update_temperature)
        #     self.threadpool.start(worker)

    def start_single_acquistion(self):  # watch out for the typo !!
        """ Take a single camera image
        """
        self._hardware.start_single_acquisition()
        self._last_image = self._hardware.get_acquired_data()
        self.sigUpdateDisplay.emit()
        self._hardware.stop_acquisition()  # this in needed to reset the acquisition mode to default
        self.sigAcquisitionFinished.emit()
        
    def stop_live_mode(self):  # might be included directly in prepare_camera_for_multichannel_imaging
        """ Allows to stop the live mode programmatically, for example in the preparation steps of a task
        where live mode would interfere with the new camera settings. """
        if self.enabled:
            self.stop_loop()
            self.sigLiveStopped.emit()  # to inform the GUI that live mode has been stopped programmatically

    # make these interface functions and remove the low level functions instead
    def prepare_camera_for_multichannel_imaging(self, frames, exposure, gain, save_path, file_format):
        self._hardware.prepare_camera_for_multichannel_imaging(frames, exposure, gain, save_path, file_format)

    def reset_camera_after_multichannel_imaging(self):
        self._hardware.reset_camera_after_multichannel_imaging()

    def get_progress(self):
        return self._hardware.get_progress()

    def get_acquired_data(self):
        return self._hardware.get_acquired_data()

    def stop_acquisition(self):
        self._hardware.stop_acquisition()

    def start_acquisition(self):
        self._hardware._start_acquisition()
        
    def abort_acquisition(self):
        self._hardware._abort_acquisition()

    def disable_camera_actions(self):
        """ This method provides a security to avoid all camera related actions from GUI, for example during Tasks. """
        self.sigDisableCameraActions.emit()

    def enable_camera_actions(self):
        """ This method resets all camera related actions from GUI to callable state, for example after Tasks. """
        self.sigEnableCameraActions.emit()


    ##########################

# the following functions concern the live display
    def start_loop(self):
        """ Start the live display loop.
        """
        self.enabled = True
        # self.timer.start(1000*1/self._fps)
        worker = LiveImageWorker(1/self._fps)
        worker.signals.sigFinished.connect(self.loop)
        self.threadpool.start(worker)

        if self._hardware.support_live_acquisition():
            self._hardware.start_live_acquisition()
        else:
            self._hardware.start_single_acquisition()

    def stop_loop(self):
        """ Stop the live display loop.
        """
        # self.timer.stop()
        self.enabled = False
        self._hardware.stop_acquisition()
        self.sigVideoFinished.emit()

    def loop(self):
        """ Execute step in the live display loop: save one of each control and process values
        """
        self._last_image = self._hardware.get_acquired_data()
        self.sigUpdateDisplay.emit()
        if self.enabled:
            # self.timer.start(1000 * 1 / self._fps)
            worker = LiveImageWorker(1/self._fps)
            worker.signals.sigFinished.connect(self.loop)
            self.threadpool.start(worker)

            if not self._hardware.support_live_acquisition():
                self._hardware.start_single_acquisition()  # the hardware has to check it's not busy

    def interrupt_live(self):
        """ Interrupt the live display loop, for example to update camera settings """
        self._hardware.stop_acquisition()
        # note that enabled attribute is not modified, to resume the state of the live display
        
    def resume_live(self):
        """ Restart the live display loop """
        self._hardware.start_live_acquisition()

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
        # for tests: 
#        return self._hardware.get_ready_state()

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
        """ retrieves an ensemble of camera status values:
        ready: if camera is idle, shutter: open / closed if available, cooler: on / off if available, temperature value.
        emits a signal containing the 4 retrieved status informations as str
        """
        ready_state = self.get_ready_state()
        shutter_state = self.get_shutter_state()
        cooler_state = self.get_cooler_state()
        temperature = str(self.get_temperature())
        self.sigUpdateCamStatus.emit(ready_state, shutter_state, cooler_state, temperature)

    def save_last_image(self, path, metadata, fileformat='.tiff'):
        """ saves a single image to disk

        @param: str path: path stem, such as /home/barho/images/2020-12-16/samplename
        @param: dict metadata: dictionary containing the metadata
        @param: str fileformat: default '.tiff' but can be modified if needed.

        @return: None
        """
        if self._last_image is None:
            self.log.warning('No image available to save')
        else:
            image_data = self._last_image

            complete_path = self._create_generic_filename(path, '_Image', 'image', fileformat, addfile=False)
            self._save_to_tiff(1, complete_path, image_data)
            self._save_metadata_txt_file(path, '_Image', metadata)


    def save_video(self, filenamestem, fileformat, n_frames, display, metadata, emit_signal=True):
        """ Saves n_frames to disk as a tiff stack

        @param: str filenamestem, such as /home/barho/images/2020-12-16/samplename
        @param: str fileformat (including the dot, such as '.tiff', '.fits')
        @param: int n_frames: number of frames to be saved
        @param: bool display: show images on live display on gui
        @param: dict metadata: meta information to be saved with the image data (in a separate txt file if tiff fileformat, or in the header if fits format)
        @param: bool emit_signal: can be set to false to avoid sending the signal for gui interaction,
                for example when function is called from ipython console or in a task
                #leave the default value True when function is called from gui
        """
        if self.enabled:  # live mode is on
            # self.timer.stop()  # display is handled differently during video saving
            self._hardware.stop_acquisition()
            # we cannot simply call stop_loop because self.enabled must be left in its state and the signal VideoFinished must not be emitted.

        self.saving = True
        # n_proxy helps to limit the number of displayed images during the video saving
        n_proxy = int(250/(self._exposure*1000))  # the factor 250 is chosen arbitrarily to give a reasonable number
        # of displayed images (every 5th for an exposure time of 50 ms for example)
        n_proxy = max(1, n_proxy)  # if n_proxy is less than 1 (long exposure time), display every image
        err = self._hardware.start_movie_acquisition(n_frames)
        if not err:
            self.log.warning('Video acquisition did not start')
            
        ready = self._hardware.get_ready_state()
        while not ready:
            progress = self._hardware.get_progress()
            self.sigProgress.emit(progress)
            ready = self._hardware.get_ready_state()
            if display:
                if progress % n_proxy == 0:  # to limit the number of displayed images 
                    self._last_image = self._hardware.get_most_recent_image()
                    self.sigUpdateDisplay.emit()
                    # sleep(0.0001)  # this is used to force enough time for a signal to be transmitted. maybe there
                    # is a better way to do this ? not needed in case the modulo operation is used to take only every
                    # n'th image

        self._hardware.wait_until_finished()  # this is important especially if display is disabled
        self.sigSaving.emit()  # for info message on statusbar of GUI
        
        image_data = self._hardware.get_acquired_data()  # first get the data before resetting the acquisition mode
        # of the camera
        self._hardware.finish_movie_acquisition()  # reset the attributes and the default acquisition mode
        self.saving = False

        # restart live in case it was activated
        if self.enabled:
            self.start_loop()

        # data handling
        complete_path = self._create_generic_filename(filenamestem, '_Movie', 'movie', fileformat, addfile=False)
        # create the PIL.Image object and save it to tiff
        if fileformat == '.tiff':
            self._save_to_tiff(n_frames, complete_path, image_data)
            self._save_metadata_txt_file(filenamestem, '_Movie', metadata)

        elif fileformat == '.fits':
            fits_metadata = self.convert_to_fits_metadata(metadata)
            self._save_to_fits(complete_path, image_data, fits_metadata)
        else:
            self.log.info(f'Your fileformat {fileformat} is currently not covered')
        if emit_signal:
            self.sigVideoSavingFinished.emit()
        else:  # needed to clean up the info on statusbar when gui is opened without calling video_saving_finished
            self.sigCleanStatusbar.emit()


    # this function is specific for andor ixon ultra camera
    def do_spooling(self, filenamestem, fileformat, n_frames, display, metadata):
        """ Saves n_frames to disk as a tiff stack without need of data handling within this function.
        Available for andor camera. Useful for large data sets which would be overwritten in the buffer

        @param: str filenamestem, such as /home/barho/images/2020-12-16/samplename
        @param: int n_frames: number of frames to be saved
        @param: bool display: show images on live display on gui
        @param: dict metadata: meta information to be saved with the image data (in a separate txt file if tiff fileformat, or in the header if fits format)
        """
        if self.enabled:  # live mode is on
            # self.timer.stop()  # display is handled differently during video saving
            self._hardware.stop_acquisition()
            # we cannot simply call stop_loop because self.enabled must be left in its state and the signal VideoFinished must not be emitted.

        self.saving = True
        # n_proxy helps to limit the number of displayed images during the video saving
        n_proxy = int(250/(self._exposure*1000))  # the factor 250 is chosen arbitrarily to give a reasonable number
        # of displayed images (every 5th for an exposure time of 50 ms for example)
        n_proxy = max(1, n_proxy)  # if n_proxy is less than 1 (long exposure time), display every image
        path = self._create_generic_filename(filenamestem, '_Movie', 'movie', '', addfile=False)  # use an empty
        # string for fileformat. this will be handled by the camera itself
        if fileformat == '.tiff':
            method = 7
        elif fileformat == '.fits':
            method = 5
        else:
            self.log.info(f'Your fileformat {fileformat} is currently not covered')
            return

        self._hardware._set_spool(1, method, path, 10)  # parameters: active (1 = yes), method (7 save as tiff,
        # 5 save as fits), filenamestem, framebuffersize
        err = self._hardware.start_movie_acquisition(n_frames)  # setting kinetics acquisition mode, make sure
        # everything is ready for an acquisition
        if not err:
            self.log.warning('Spooling did not start')
        
        ready = self._hardware.get_ready_state()
        while not ready:
            spoolprogress = self._hardware.get_progress()
            self.sigProgress.emit(spoolprogress)
            ready = self._hardware.get_ready_state()
            if display:
                if spoolprogress % n_proxy == 0:  # to limit the number of displayed images 
                    self._last_image = self._hardware.get_most_recent_image()
                    self.sigUpdateDisplay.emit()
                    # sleep(0.0001)  # this is used to force enough time for a signal to be transmitted. maybe there
                    # is a better way to do this ?

        self._hardware.wait_until_finished()
        self._hardware.finish_movie_acquisition()
        self._hardware._set_spool(0, method, path, 10)  # deactivate spooling
        self.log.info('Saved data to file {}{}'.format(path, fileformat))
        # metadata saving
        if fileformat == '.tiff':
            self._save_metadata_txt_file(filenamestem, '_Movie', metadata)
        elif fileformat == '.fits':
            try:
                complete_path = path+'.fits'
                fits_metadata = self.convert_to_fits_metadata(metadata)
                self._add_fits_header(complete_path, fits_metadata)
            except Exception as e:
                self.log.warn(f'Metadata not saved: {e}.')
        else:
            pass  # this case will never be accessed because the same if-elif-else structure was already applied above

        self.saving = False

        # restart live in case it was activated
        if self.enabled:
            self.start_loop()

        self.sigSpoolingFinished.emit()

    def _create_generic_filename(self, filenamestem, folder, file, fileformat, addfile):
        """ helper function that creates a generic filename using the following format:

        filenamestem/001_folder/file.tiff example: /home/barho/images/2020-12-16/samplename/000_Movie/movie.tiff

        filenamestem is typically generated by the save settings dialog in basic gui but can also entered manually if
        function is called in console

        @params: str filenamestem  (example /home/barho/images/2020-12-16/samplename)
        @params: str folder: specify the type of experiment (ex. Movie, Snap)
        @params: str file: filename (ex movie, image). do not specify the fileformat.
        @params: str fileformat: specify the type of file (.tiff, .txt, ..) including the dot ! 
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
        prefix = str(number_dirs+1).zfill(3)
        folder_name = prefix + folder
        path = os.path.join(filenamestem, folder_name)
        # now create this folder
        if not os.path.exists(path):  # we need this condition because metadata will be written in the same folder so
            # the folder may already exist
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
        @params str path: complete path where the object is saved to (including the suffix .tiff)
        @params data: np.array

        @returns None
        """
        # type conversion to int16
        data = data.astype('int16')
        # self.log.info('type conversion called')
        # 2D data case (no stack)
        if n_frames == 1:
            try:
                self.save_u16_to_tiff(data, (data.shape[1], data.shape[0]), path)
                self.log.info('Saved data to file {}'.format(path))
            except:
                self.log.warning('Data not saved')
            return None

        # 3D data (note: z stack is the first dimension)
        else:
            try:
                size = (data.shape[2], data.shape[1])
                self.save_u16_to_tiff_stack(n_frames, data, size, path)
                self.log.info('Saved data to file {}'.format(path))
            except:
                self.log.warning('Data not saved')
            return None

    def save_u16_to_tiff(self, u16int, size, tiff_filename):
        """
        function found at https://blog.itsayellow.com/technical/saving-16-bit-tiff-images-with-pillow-in-python/#
        Since Pillow has poor support for 16-bit TIFF, we make our own save function to properly save a 16-bit TIFF.

        modified version for numpy array only

        @param u16int: np.array with dtype int16 to be saved as tiff. make sure that the data is in int16 format !
        otherwise the conversion to bytes will not give the right result
        @param size: size of the data
        @param str tiff_filename: including the suffix '.tiff'
        """
        # write 16-bit TIFF image
        # PIL interprets mode 'I;16' as "uint16, little-endian"
        img_out = Image.new('I;16', size)
        outpil = u16int.astype(u16int.dtype.newbyteorder("<")).tobytes()
        img_out.frombytes(outpil)
        img_out.save(tiff_filename)

    def save_u16_to_tiff_stack(self, n_frames, u16int, size, tiff_filename):
        """ handles saving of 3D image data to 16 bit tiff stacks
        @param int n_frames: number of frames to be saved (1st dimension of the image data)
        @param u16int: 3D np.array with dtype int16 to be saved as tiff
        @param int tuple size: size of an individual image in the stack (x pixel, y pixel)
        @param str tiff_filename: complete path to the file, including the suffix .tiff """

        imlist = []  # this will be a list of pillow Image objects
        for i in range(n_frames):
            img_out = Image.new('I;16', size)  # initialize a new pillow object of the right size
            outpil = u16int[i].astype(
                u16int.dtype.newbyteorder("<")).tobytes()  # convert the i-th frame to bytes object
            img_out.frombytes(outpil)  # create pillow object from bytes
            imlist.append(img_out)  # create the list of pillow image objects
        imlist[0].save(tiff_filename, save_all=True, append_images=imlist[1:])

    def _save_metadata_txt_file(self, filenamestem, type, metadata):
        """"helper function to save a txt file containing the metadata

        @params: str filenamestem (example /home/barho/images/2020-12-16/samplename)
        @parms: str type: string identifier of the data type: _Movie or _Image
        @params: dict metadata: dictionary containing the annotations

        @returns None
        """
        complete_path = self._create_generic_filename(filenamestem, type, 'parameters', '.txt', addfile=True)
        with open(complete_path, 'w') as file:
            # file.write(str(metadata))  # for standard txt file
            yaml.dump(metadata, file, default_flow_style=False)  # yaml file. can use suffix .txt. change if .yaml preferred.
        self.log.info('Saved metadata to {}'.format(complete_path))

    def _save_to_fits(self, path, data, metadata):
        """ helper function to save the image data to a fits file.
        see also https://docs.astropy.org/en/latest/io/fits/index.html#creating-a-new-image-file

        Works for 2D data and stacks

        @params str path: complete path where the object is saved to, including the suffix .fits
        @params data: np.array (2D or 3D)

        @returns None
        """
        data = data.astype(np.int16)  # data conversion because 16 bit image shall be saved
        hdu = fits.PrimaryHDU(data)  # PrimaryHDU object encapsulates the data
        hdul = fits.HDUList([hdu])
        # add the header
        hdr = hdul[0].header
        for key in metadata:
            hdr[key] = metadata[key]
        # write to file
        try:
            hdul.writeto(path)
            self.log.info('Saved data to file {}'.format(path))
        except Exception as e:
            self.log.warning(f'Data not saved: {e}')

    def _add_fits_header(self, path, dictionary):
        """ After spooling to fits format, this method accesses the file and adds the metadata in the header
        @params str path: complete path where the object is saved to, including the suffix .fits
        @params dict dictionary: containing metadata with fits compatible keys and values
        """
        with fits.open(path, mode='update') as hdul:
            hdr = hdul[0].header
            for key in dictionary:
                hdr[key] = dictionary[key]

    def set_sensor_region(self, hbin, vbin, hstart, hend, vstart, vend):
        """ defines a limited region on the sensor surface, hence accelerating the acquisition

        @param int hbin: number of pixels to bin horizontally
        @param int vbin: number of pixels to bin vertically.
        @param int hstart: Start column (inclusive)
        @param int hend: End column (inclusive)
        @param int vstart: Start row (inclusive)
        @param int vend: End row (inclusive).
        """
        if self.enabled:  # live mode is on
#            self.interrupt_live()  # interrupt live to allow access to camera settings
            # new version to avoid display problem 
            # self.timer.stop()
            self._hardware.stop_acquisition()

        err = self._hardware.set_image(hbin, vbin, hstart, hend, vstart, vend)
        if err < 0:
            self.log.warn('Sensor region not set')
        else:
            self.log.info('Sensor region set to {} x {}'.format(vend-vstart+1, hend-hstart+1))

        if self.enabled:
#            self.resume_live() # restart live in case it was activated
            self.start_loop()

    def reset_sensor_region(self):
        """ reset to full sensor size """
        if self.enabled:  # live mode is on
            # self.timer.stop()
            self._hardware.stop_acquisition()  # interrupt live to allow access to camera settings
            
        width = self._hardware._full_width  # store the full_width in the hardware module because _width is
        # overwritten when image is set
        height = self._hardware._full_height  # same goes for height

        err = self._hardware.set_image(1, 1, 1, width, 1, height)
        if err < 0:
            self.log.warn('Sensor region not reset to default')
        else:
            self.log.info('Sensor region reset to default: {} x {}'.format(height, width))

        if self.enabled:
            self.start_loop()
            

    @QtCore.Slot(bool)
    def set_frametransfer(self, activate):
        """ Activate frametransfer mode for ixon ultra camera: the boolean activate is stored in a variable in the
        camera module. When an acquisition is started, frame transfer is set accordingly.

        @params: bool activate ?
        """
        if self.get_name() == 'iXon Ultra 897':
            if self.enabled:  # if live mode is on, interrupt to be able to access frame transfer setting
                self.interrupt_live()
            self._hardware._set_frame_transfer(int(activate))
            if self.enabled:  # if live mode was interrupted, restart it
                self.resume_live()
            self.log.info(f'Frametransfer mode activated: {activate}')
            # we also need to update the indicator on the gui
            exp = self.get_exposure()  # we just need to send the signal sigExposureChanged but it must carry a float
            # so we send exp as argument
            self.sigExposureChanged.emit(exp)
        # do nothing in case of cameras that do not support frame transfer
        else:
            pass

    def get_size(self):
        """ Retrieve size of the image in pixel

        @return tuple: Size (width, height)
        """
        return self._hardware.get_size()
    
    def get_max_size(self):
        """ Retrieve maximum size of the sensor in pixel

        @return tuple: Size (width, height)
        """
        return self._hardware._full_width, self._hardware._full_height

    # new functions to be tested for synchronized measurements
    # _set_trigger_mode not (yet) on camera interface !!
    def set_trigger_mode(self, mode):
        self._hardware._set_trigger_mode(mode)   # specific for andor in this version. homogenize when completing other camera's code
        # add return value for error check if needed.. _set_trigger_mode returns 0 if ok, -1 if not


    def convert_to_fits_metadata(self, metadata):
        """ Convert a dictionary in arbitrary format to fits compatible format.
        :param dict metadata: dictionary to convert to fits compatible format
        :return dict fits_metadata: dictionary converted to fits compatible format """
        fits_metadata = {}
        for key, value in metadata.items():
            key = key.replace(' ', '_')
            if isinstance(value, list):
                for i in range(len(value)):
                    fits_key = key[:7].upper()+str(i+1)
                    fits_value = (value[i], key+str(i+1))
                    fits_metadata[fits_key] = fits_value
            else:
                fits_key = key[:8].upper()
                fits_value = (value, key)
                fits_metadata[fits_key] = fits_value

        return fits_metadata
