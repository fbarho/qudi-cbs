import ctypes

from core.module import Base
from core.configoption import ConfigOption
from interface.camera_interface import CameraInterface
from .hamamatsu_python_driver import *



class HCam(Base, HamamatsuCamera):
    """ Hardware class for Hamamatsu Orca Flash Camera

    Example config for copy-paste:

    hamamatsu_camera:
        module.Class: 'camera.hamamatsu.hamamatsu.HCam'

    """
    dcam = None

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self.dcam = ctypes.windll.dcamapi
        print(self.dcam)

        paraminit = DCAMAPI_INIT(0, 0, 0, 0, None, None)
        print(paraminit._fields_)
        paraminit.size = ctypes.sizeof(paraminit)
        print(paraminit.size)
        error_code = self.dcam.dcamapi_init(ctypes.byref(paraminit))
        print(error_code)
        if (error_code != DCAMERR_NOERROR):
            raise DCAMException("DCAM initialization failed with error code " + str(error_code))

        n_cameras = paraminit.iDeviceCount
        print(n_cameras)

        print("found:", n_cameras, "cameras")

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        pass



# if (__name__ == "__main__"):
#     cam = HCam()
#     cam.on_activate()