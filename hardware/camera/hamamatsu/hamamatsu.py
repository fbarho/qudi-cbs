import ctypes
import numpy as np
from core.module import Base
from core.configoption import ConfigOption
from interface.camera_interface import CameraInterface
from .hamamatsu_python_driver import HamamatsuCamera


class HCam(Base, CameraInterface):
    """ Hardware class for Hamamatsu Orca Flash Camera

    Example config for copy-paste:

    hamamatsu_camera:
        module.Class: 'camera.hamamatsu.hamamatsu.HCam'
        camera_id: 0
        default_exposure: 0.01
        default_acquisition_mode: 'run_till_abort'

    """
    # attributes from config
    _default_exposure = ConfigOption('default_exposure', 0.01)  # in seconds
    _default_acquisition_mode = ConfigOption('default_acquisition_mode', 'run_till_abort')
    camera_id = ConfigOption('camera_id', 0)

    # Initialize attributes
    _width = 0  # current width
    _height = 0  # current height
    _full_width = 0  # maximum width of the sensor
    _full_height = 0  # maximum height of the sensor
    _exposure = _default_exposure
    _gain = 0
    n_frames = 1

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self.camera = HamamatsuCamera(
            self.camera_id)  # the idea is to use the class HamamatsuCamera like a python wrapper for the dcamapi

        self.get_size()  # update the values _weight, _height
        self._full_width = self._width
        self._full_height = self._height

        # # set some default values
        # self.camera.setACQMode(self._default_acquisition_mode)
        self.set_exposure(self._exposure)

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self.camera.stopAcquisition()
        # close the camera
        self.camera.shutdown()
        # maybe add also the deinitialization of the dcamapi
        # ..

    def get_name(self):
        """ Retrieve an identifier of the camera that the GUI can print

        @return string: name for the camera
        """
        camera_name = self.camera.getModelInfo(self.camera_id)
        return camera_name

    def get_size(self):
        """ Retrieve size of the image in pixel

        @return tuple: Size (width, height)
        """
        self._width = self.camera.getPropertyValue('image_width')[0]
        self._height = self.camera.getPropertyValue('image_height')[0]
        return self._width, self._height

    def support_live_acquisition(self):
        """ Return whether or not the camera can take care of live acquisition

        @return bool: True if supported, False if not
        """
        return True

    def start_live_acquisition(self):
        """ Start a continuous acquisition

        @return bool: Success ?
        """
        # do we need this ? (taken from andor camera; might be needed for connections with logic module)
        # # handle the variables indicating the status
        # if self.support_live_acquisition():
        #     self._live = True
        #     self._acquiring = False
        try:
            self.camera.setACQMode('run_till_abort')
            self.camera.startAcquisition()
            return True
        except:
            return False

    def start_single_acquisition(self):
        """ Start a single acquisition

        @return bool: Success ?
        """
        try:
            self.camera.setACQMode('fixed_length', 1)
            self.camera.startAcquisition()
            return True
        except:
            return False

    def stop_acquisition(self):
        """ Stop/abort live or single acquisition

        @return bool: Success ?
        """
        try:
            self.camera.stopAcquisition()
            return True
        except:
            return False

    def get_acquired_data(self):
        """ Return an array of last acquired image in case of run till abort acquisition mode, or all data in case of fixed length acquisition mode.

        @return numpy array: image data in format [[row],[row]...]

        Each pixel might be a float, integer or sub pixels
        """
        acq_mode = self.get_acquisition_mode()

        image_array = []  # or should this be initialized as an np array ??
        [frames,
         dim] = self.camera.getFrames()  # frames is a list of HCamData objects, dim is a list [image_width, image_height]

        if acq_mode == 'run_till_abort':
            data = frames[-1].getData()  # for run_till_abort acquisition: get the last (= most recent) frame
            image_array = np.reshape(data, (dim[1], dim[
                0]))  # reshape in row major shape (height, width) # to check if image is reconstituted correctly
        elif acq_mode == 'fixed_length' and self.n_frames == 1:  # equivalent to single_scan
            data = frames[-1].getData()
            image_array = np.reshape(data, (dim[1], dim[0]))
            # this case is covered separately to guarantee the correct display for snap
            # code could be combined with case 1 above (conditions listed with 'or')
        elif acq_mode == 'fixed_length' and self.n_frames > 1:
            frames_list = [np.reshape(frames[i].getData(), (dim[1], dim[0])) for i in range(len(frames))]  # retrieve the data, reshape it and create a list of the frames
            image_array = np.stack(frames_list)
        else:
            self.log.info('Your aquisition mode is not covered yet.')
        return image_array
        # to do: add a check if data is available to avoid the index error if data has already been retrieved

    def set_exposure(self, exposure):
        """ Set the exposure time in seconds

        @param float exposure: desired new exposure time

        @return bool: Success?
        """
        new_exp = self.camera.setPropertyValue('exposure_time',
                                               exposure)  # return value new_exp: float if new exposure set (eventually corrected to be inside the allowed range); False if error
        # update the attribute
        if isinstance(new_exp, float):
            self._exposure = self.camera.getPropertyValue('exposure_time')[0]
            return True
        else:
            return False
        # is this error check sufficient ?

    def get_exposure(self):
        """ Get the exposure time in seconds

        @return float exposure time
        """
        self._exposure = self.camera.getPropertyValue('exposure_time')[
            0]  # is this needed ? or is the attribute _exposure always up to date due to the update in set_exposure ?
        return self._exposure

    def set_gain(self, gain):
        """ Set the gain - gain is not available for the hamamatsu camera

        @param float gain: desired new gain

        @return float: new gain
        """
        pass

    def get_gain(self):
        """ Get the gain

        @return float: exposure gain
        """
        return self._gain

    def get_ready_state(self):
        """ Is the camera ready for an acquisition ?

        @return bool: ready ?
        """
        return self.camera.get_ready_state()

    # new interface functions not in the original qudi version
    def has_temp(self):
        """ Does the camera support setting of the temperature?

        if this function returns true, make sure that get_temperature, set_temperature, is_cooler_on and _set_cooler
        are implemented the attribute _default_temperature should be also be set in the hardware module

        @return bool: has temperature ?
        """
        return False  # or should we make it accessible for the user ?

    def has_shutter(self):
        """ Is the camera equipped with a mechanical shutter?

        if this function returns true, the attribute _shutter should also be defined in the hardware module

        @return bool: has shutter ?
        """
        return False

    def start_movie_acquisition(self, n_frames):
        """ set the conditions to save a movie and start the acquisition

        @param int n_frames: number of frames

        @return bool: Success ?
        """
        self.n_frames = n_frames  # needed to choose the correct case in get_acquired_data method
        try:
            self.camera.setACQMode('fixed_length', n_frames)
            self.camera.startAcquisition()
            return True
        except:
            return False

    def finish_movie_acquisition(self):
        """ resets the conditions used to save a movie to default

        @return bool: Success ?
        """
        try:
            self.camera.stopAcquisition()
            self.n_frames = 1  # reset to default
            return True
        except:
            return False

    def wait_until_finished(self):
        """ waits until an acquisition is finished

        @return None
        """
        pass

    def get_most_recent_image(self):
        """ Return an array of last acquired image.

        @return numpy array: image data in format [[row],[row]...]

        Each pixel might be a float, integer or sub pixels
        """
        [frame, dim] = self.camera.getMostRecentFrame()  # frame is HCamData object, dim is a list [image_width, image_height]
        image_array = np.zeros(dim[0] * dim[1])
        data = frame.getData()
        image_array = np.reshape(data, (dim[1], dim[0]))
        return image_array


    def set_image(self, hbin, vbin, hstart, hend, vstart, vend):
        """ Sets a ROI on the sensor surface

        @param int hbin: number of pixels to bin horizontally
        @param int vbin: number of pixels to bin vertically.
        @param int hstart: Start column
        @param int hend: End column
        @param int vstart: Start row
        @param int vend: End row

        @returns: int error code: 0: ok
        """
        try:
            # only multiples of 4 are allowed for hstart, hend, vsize, hsize. Use the lower nearest multiple of 4
            hstart = int(hstart / 4) * 4
            vstart = int(vstart / 4) * 4
            vend = int(vend / 4) * 4
            hend = int(hend / 4) * 4
            vsize = vend - vstart
            hsize = hend - hstart
            self.camera.setPropertyValue('subarray_hpos', hstart)
            self.camera.setPropertyValue('subarray_vpos', vstart)
            self.camera.setPropertyValue('subarray_hsize', hsize)
            self.camera.setPropertyValue('subarray_vsize', vsize)
            self.camera.setSubArrayMode()
            self.log.info(f'Set subarray: {vsize} x {hsize} pixels (rows x cols)')  # for tests
            return 0
        except:
            return -1

        # need to check the order in which the parameters are called by the QRectF..

    def get_progress(self):
        """ retrieves the total number of acquired images during a movie acquisition"""
        return self.camera.check_frame_number()

    # put this on the interface
    def prepare_camera_for_multichannel_imaging(self, frames, exposure, gain, save_path, file_format):
        self.stop_acquisition()
        self.set_exposure(exposure)
        self._set_acquisition_mode('fixed_length', frames)
        self.n_frames = frames  # this ensures that the data retrieval format is correct
        # external trigger mode, positive polarity
        self._set_trigger_source('EXTERNAL')
        self._set_trigger_polarity('POSITIVE')
        # output trigger: trigger ready and global exposure
        self._configure_output_trigger(1, 'TRIGGER READY', 'NEGATIVE')
        self._configure_output_trigger(2, 'EXPOSURE', 'NEGATIVE')
        # self._start_acquisition()

    def reset_camera_after_multichannel_imaging(self):
        self.stop_acquisition()
        self._set_trigger_source('INTERNAL')
        self.n_frames = 1  # reset to default
        self._set_acquisition_mode('run_till_abort')





    # non interface functions
    def get_acquisition_mode(self):
        acq_mode = self.camera.acquisition_mode
        return acq_mode

    def _set_trigger_source(self, source):
        """
        Set the trigger source.
        @param string source: string corresponding to certain TriggerMode 'INTERNAL', 'EXTERNAL', 'SOFTWARE', 'MASTER PULSE'
        @return int check_val: ok: 0, not ok: -1
        """
        # the supported trigger sources can be found as follows:
        # self.camera.getPropertyText('trigger_source') returns {'INTERNAL': 1, 'EXTERNAL': 2, 'SOFTWARE': 3, 'MASTER PULSE': 4}
        check_val = self.camera.setPropertyValue('trigger_source', source)
        if isinstance(check_val, float):
            return 0
        else:
            return -1

    def _get_trigger_source(self):
        trigger_source = self.camera.getPropertyValue('trigger_source') # returns a list [value, type] such as [1, 'MODE']
        return trigger_source[0]  # would be a good idea to map the number to the description

    def _set_trigger_polarity(self, polarity):
        """ Set the trigger polarity (default is negative)
        @param: str polarity: 'NEGATIVE', 'POSITIVE'
        @return int check_val: ok: 0, not ok: -1
        """
        check_val = self.camera.setPropertyValue('trigger_polarity', polarity)  # returns a float corresponding to the polarity (1.0: negative, 2.0: positive) or bool False if not set
        if isinstance(check_val, float):
            return 0
        else:
            return -1

    def _get_trigger_polarity(self):
        trigger_polarity = self.camera_getPropertyValue('trigger_polarity')
        return trigger_polarity[0]

    def _configure_output_trigger(self, channel, output_trigger_kind, output_trigger_polarity):
        """
        Configure the output trigger for the specified output channel
        @param: int channel: index ranging up to the number of output trigger connectors - 1
        @param: str output_trigger_kind: supported values 'LOW', 'EXPOSURE', 'PROGRAMABLE', 'TRIGGER READY', 'HIGH'
        @param: str output_trigger_polarity: supported values 'NEGATIVE', 'POSITIVE'
        """
        trigger_kind = self.camera.setPropertyValue(f'output_trigger_kind[{channel}]', output_trigger_kind)
        print(trigger_kind)
        trigger_polarity = self.camera.setPropertyValue(f'output_trigger_polarity[{channel}]', output_trigger_polarity)
        print(trigger_polarity)

    def _set_acquisition_mode(self, mode, n_frames=None):
        self.camera.setACQMode(mode, n_frames)
        # add error handling etc.

    def _start_acquisition(self):
        self.camera.startAcquisition()




