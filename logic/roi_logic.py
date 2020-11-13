#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov  9 06:22:29 2020

@author: fbarho

This module contains the ROI selection logic.
It is in large parts taken and adapted from the qudi poimanager logic, in this version reduced to 
the functionality that we need. 
(+ for future use: the possibility to add a z position control, this is why spatial coordonnates are kept as 3 dimensional (xyz)
as well as deactivated tools concerning the camera image overlay)

ROIs are regrouped into an ROI list (instead of using the terminology of POI in ROI
or, as in the current labview measurement software ROIs per embryo.) 
The chosen nomenclature is more flexible than regrouping by embryo and can be extended to other 
types of samples. Moreover, it is planned to add a serpentine scan over a sample area and 
decide which ROI belongs to which object in the analysis step.
"""


import os
import numpy as np
import time
import json

#from collections import OrderedDict
from core.connector import Connector
from core.statusvariable import StatusVar
from datetime import datetime
from logic.generic_logic import GenericLogic
from qtpy import QtCore
from core.util.mutex import Mutex


class RegionOfInterestList:
    """  
    Class containing the general information about a specific list of regions of interest,
    such as its name, the creation time, the rois as a subdictionary of ROI instances, 
    (N.B. Each individual ROI will be represented as a RegionOfInterest instance (see below).), 
    the camera image which may be overlayed on the map of ROI markers.
    The origin of a new ROI list will be defined as (0, 0, 0). ### or modify to use absolute stage position instead? for reloading several lists etc..
    
    example of a RegionOfInterestList instance in its dictionary representation
    {'name': 'roilist_20201113_1212_00_244657',
     'creation_time': '2020-11-13 12:12:00.244657',
     'cam_image': None,
     'cam_image_extent': None,
     'rois': [{'name': 'ROI_001', 'position': (0.0, 0.0, 0.0)},
              {'name': 'ROI_002', 'position': (10.0, 10.0, 0.0)},
              {'name': 'ROI_003', 'position': (20.0, 20.0, 0.0)},
              {'name': 'ROI_004', 'position': (30.0, 30.0, 0.0)}]}
    """

    def __init__(self, name=None, creation_time=None, cam_image=None,
                 cam_image_extent=None, rois=None):
        
        # Save the creation time for metadata
        self._creation_time = None
        # Optional camera image associated with this ROI
        self._cam_image = None
        # Optional initial camera image extent.
        self._cam_image_extent = None
        # Save name of the ROIlist. Create a generic, unambiguous one as default.
        self._name = None
        # dictionary of ROIs contained in this ROIlist with keys being the name
        self._rois = dict()

        self.creation_time = creation_time
        self.name = name
        #self.set_cam_image(cam_image, cam_image_extent)
        if rois is not None:
            for roi in rois:
                self.add_roi(roi)
        return None

    @property
    def name(self):
        return str(self._name)

    @name.setter
    def name(self, new_name):
        if isinstance(new_name, str) and new_name:
            self._name = str(new_name)
        elif new_name is None or new_name == '':
            self._name = self._creation_time.strftime('roilist_%Y%m%d_%H%M_%S_%f') ## modify the default roilist name ?
        else:
            raise TypeError('ROIlist name to set must be None or of type str.')
        return None
          

    @property
    def creation_time(self):
        return self._creation_time

    @property
    def creation_time_as_str(self):
        return datetime.strftime(self._creation_time, '%Y-%m-%d %H:%M:%S.%f')

    @creation_time.setter
    def creation_time(self, new_time):
        if not new_time:
            new_time = datetime.now()
        elif isinstance(new_time, str):
            new_time = datetime.strptime(new_time, '%Y-%m-%d %H:%M:%S.%f')
        if isinstance(new_time, datetime):
            self._creation_time = new_time
        return

    @property
    def origin(self):
        return np.zeros(3) # no drift correction so origin is set to 0 and does not move over time

    @property
    def cam_image(self):
        return self._cam_image

    # can be simplified when origin is kept as (0, 0, 0)
    @property
    def cam_image_extent(self):
        if self._cam_image_extent is None:
            return None
        x, y, z = self.origin
        x_extent = (self._cam_image_extent[0][0] + x, self._cam_image_extent[0][1] + x)
        y_extent = (self._cam_image_extent[1][0] + y, self._cam_image_extent[1][1] + y)
        return x_extent, y_extent

    @property
    def roi_names(self):
        return list(self._rois)

    @property
    def roi_positions(self):
        origin = self.origin
        return {name: roi.position + origin for name, roi in self._rois.items()}


    def get_roi_position(self, name):
        if not isinstance(name, str):
            raise TypeError('ROI name must be of type str.')
        if name not in self._rois:
            raise KeyError('No ROI with name "{0}" found in ROI list.'.format(name))
        return self._rois[name].position + self.origin
    

    def set_roi_position(self, name, new_pos):
        if name not in self._rois:
            raise KeyError('ROI with name "{0}" not found in ROIlist "{1}".\n'
                           'Unable to change ROI position.'.format(name, self.name))
        self._rois[name].position = np.array(new_pos, dtype=float) - self.origin
        return None


##### this method is made unavailable because only the generic name ROI_000 etc is allowed.
#    def rename_roi(self, name, new_name=None):
#        if new_name is not None and not isinstance(new_name, str):
#            raise TypeError('ROI name to set must be of type str or None.')
#        if name not in self._rois:
#            raise KeyError('Name "{0}" not found in ROI list.'.format(name))
#        if new_name in self._rois:
#            raise NameError('New ROI name "{0}" already present in current ROI list.')
#        self._rois[name].name = new_name
#        self._rois[new_name] = self._rois.pop(name)
#        return None

       
    def add_roi(self, position):
        if isinstance(position, RegionOfInterest):
            roi_inst = position
        else:
            position = position - self.origin
            
            # Create a generic name which cannot be accessed by the user
            index = len(self._rois) + 1
            str_index = str(index).zfill(3) # zero padding
            name = 'ROI_'+str_index
            
            roi_inst = RegionOfInterest(position=position, name=name)
        self._rois[roi_inst.name] = roi_inst
        return None
                                        
                                        
                                        
#    # redefine this method without allowing a name to be given # this works but could probably be simplified
#    def add_roi(self, position, name=None):
#        if isinstance(position, RegionOfInterest):
#            roi_inst = position
#        else:
#            position = position - self.origin
#            # Create a generic name 
#            index = len(self._rois)
#            while True:
#                index += 1
#                str_index = str(index).zfill(3) # zero padding 
#                name = 'ROI_'+str_index
#                if name not in self._rois:
#                    break
#            roi_inst = RegionOfInterest(position=position, name=name)
#        if roi_inst.name in self._rois:
#            raise ValueError('ROI with name "{0}" already present in ROIlist "{1}".\n'
#                             'Could not add ROI to ROIlist'.format(roi_inst.name, self.name))
#        self._rois[roi_inst.name] = roi_inst
#        return None

    def delete_roi(self, name):
        if not isinstance(name, str):
            raise TypeError('ROI name to delete must be of type str.')
        if name not in self._rois:
            raise KeyError('Name "{0}" not found in ROI list.'.format(name))
        del self._rois[name]
        return None


# can be activated and modified if camera image is added
#    def set_cam_image(self, image_arr, image_extent):
#        """
#
#        @param scalar[][] image_arr:
#        @param float[2][2] image_extent:
#        """
#        if image_arr is None:
#            self._cam_image = None
#            self._cam_image_extent = None
#        else:
#            roi_x_pos, roi_y_pos, roi_z_pos = self.origin
#            x_extent = (image_extent[0][0] - roi_x_pos, image_extent[0][1] - roi_x_pos)
#            y_extent = (image_extent[1][0] - roi_y_pos, image_extent[1][1] - roi_y_pos)
#            self._cam_image = np.array(image_arr)
#            self._cam_image_extent = (x_extent, y_extent)
#        return


    def to_dict(self):
        return {'name': self.name,
                'creation_time': self.creation_time_as_str,
                'cam_image': self.cam_image,
                'cam_image_extent': self.cam_image_extent,
                'rois': [roi.to_dict() for roi in self._rois.values()]}

    @classmethod
    def from_dict(cls, dict_repr):
        if not isinstance(dict_repr, dict):
            raise TypeError('Parameter to generate RegionOfInterestList instance from must be of type '
                            'dict.')
        if 'rois' in dict_repr:
            rois = [RegionOfInterest.from_dict(roi) for roi in dict_repr.get('rois')]
        else:
            rois = None
            
        roi_list = cls(name=dict_repr.get('name'),
                  creation_time=dict_repr.get('creation_time'),
                  cam_image=dict_repr.get('cam_image'),
                  cam_image_extent=dict_repr.get('cam_image_extent'),
                  rois=rois,
                  )
        return roi_list 


class RegionOfInterest:
    """
    The actual individual roi is saved in this generic object.
    A RegionOfInterest object corresponds to a dictionary of the following format {'name': roi_name, 'position': roi_position}
    for example {'name': ROI_OO1, 'position': (10, 10, 0)}
    """

    def __init__(self, position, name=None):
        # Name of the ROI
        self._name = ''
        # Relative ROI position within the ROIlist (x,y,z) 
        self._position = np.zeros(3)
        # Initialize properties
        self.position = position
        self.name = name

    @property
    def name(self):
        return str(self._name)

    # redefined the name.setter so that it can be called from the RegionOfInterestList instance 
    # it will always be called with a new_name corresponding to the generic format. the if not new_name part would produce the same name
    @name.setter
    def name(self, new_name):
        if new_name is not None and not isinstance(new_name, str):
            raise TypeError('Name to set must be either None or of type str.')
        if not new_name: 
            index = len(self._rois) + 1 
            str_index = str(index).zfill(3)
            new_name = 'ROI_'+str_index
        self._name = new_name
        return None
        
    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, pos):
        if len(pos) != 3:
            raise ValueError('ROI position to set must be iterable of length 3 (X, Y, Z).')
        self._position = np.array(pos, dtype=float)
        return None

    def to_dict(self):
        return {'name': self.name, 'position': tuple(self.position)}

    @classmethod
    def from_dict(cls, dict_repr):
        return cls(**dict_repr)


class RoiLogic(GenericLogic):
    """
    This is the Logic class for selecting regions of interest.
    """

    # declare connectors
    stage = Connector(interface='MotorInterface') 
    
    # status vars
    _roi_list = StatusVar(default=dict())  # Notice constructor and representer further below
    _active_roi = StatusVar(default=None)
    _roi_width = StatusVar(default=20) # check if unit is correct when used with real translation stage. Value corresponds to FOV ??

    # Signals for connecting modules
    sigRoiUpdated = QtCore.Signal(str, str, np.ndarray)  # old_name, new_name, current_position
    sigActiveRoiUpdated = QtCore.Signal(str)
    sigRoiListUpdated = QtCore.Signal(dict)  # Dict containing ROI parameters to update
    sigWidthUpdated = QtCore.Signal(float)


    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # not needed in this version but remember to use it when starting to handle threads
        # threading
        self._threadlock = Mutex()
        
        return None

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """

        # Initialise the ROI camera image (xy image) if not present
        #if self._roi_list.cam_image is None:
            #self.set_cam_image(False)

        self.sigRoiListUpdated.emit({'name': self.roi_list_name,
                                 'rois': self.roi_positions,
                                 'cam_image': self.roi_list_cam_image,
                                 'cam_image_extent': self.roi_list_cam_image_extent
                                 })
        self.sigActiveRoiUpdated.emit('' if self.active_roi is None else self.active_roi)
        return None

    def on_deactivate(self):
        pass


    @property
    def active_roi(self):
        return self._active_roi

    @active_roi.setter
    def active_roi(self, name):
        self.set_active_roi(name)
        return None

    @property
    def roi_names(self):
        return self._roi_list.roi_names

    @property
    def roi_positions(self):
        return self._roi_list.roi_positions

    @property
    def roi_list_name(self):
        return self._roi_list.name

    @roi_list_name.setter
    def roi_list_name(self, name):
        self.rename_roi_list(new_name=name)


    @property
    def roi_list_origin(self):
        return self._roi_list.origin

    @property
    def roi_list_creation_time(self):
        return self._roi_list.creation_time

    @property
    def roi_list_creation_time_as_str(self):
        return self._roi_list.creation_time_as_str

    @property
    def roi_list_cam_image(self):
        return self._roi_list.cam_image

    @property
    def roi_list_cam_image_extent(self):
        return self._roi_list.cam_image_extent

    @property
    def roi_width(self):
        return float(self._roi_width)

    @roi_width.setter
    def roi_width(self, new_width):
        self.set_roi_width(new_width)
        return None
  
    @property
    def stage_position(self):
        pos = self.stage().get_pos() # this returns a dictionary of the format {'x': pos_x, 'y': pos_y} 
        return list(pos.values())[:3] # get only the dictionary values as a list. [:3] as safety to get only the x y axis and empty z value, in case more axis are configured (such as for the motor_dummy)


# even if called with a name not None, a generic name is set. The specified one is not taken into account. This is handled in the add_roi method of RegionOfInterestList class
    @QtCore.Slot()
    @QtCore.Slot(np.ndarray)
    def add_roi(self, position=None, name=None, emit_change=True):
        """
        Creates a new ROI and adds it to the current ROI list.
        ROI can be optionally initialized with position and name.

        @param str name: Name for the ROI (must be unique within ROI list).
                         None (default) will create generic name.
        @param scalar[3] position: Iterable of length 3 representing the (x, y, z) position with
                                   respect to the ROI list origin. None (default) causes the current
                                   crosshair position to be used.
        @param bool emit_change: Flag indicating if the changed ROI set should be signaled.
        """
        # Get current stage position from motor interface if no position is provided.
        if position is None:
            position = self.stage_position

        current_roi_set = set(self.roi_names)

        # Add ROI to current ROI list
        self._roi_list.add_roi(position=position, name=name)

        # Get newly added ROI name from comparing ROI names before and after addition of new ROI
        roi_name = set(self.roi_names).difference(current_roi_set).pop()

        # Notify about a changed set of ROIs if necessary
        if emit_change:
            self.sigRoiUpdated.emit('', roi_name, self.get_roi_position(roi_name))

        # Set newly created ROI as active roi
        self.set_active_roi(roi_name)
        return None

# delete_roi can be called with a name present in the list (which will only be the generic names)
    @QtCore.Slot()
    def delete_roi(self, name=None):
        """
        Deletes the given roi from the roi list.

        @param str name: Name of the roi to delete. If None (default) delete active roi.
        @param bool emit_change: Flag indicating if the changed roi set should be signaled.
        """
        if len(self.roi_names) == 0:
            self.log.warning('Can not delete ROI. No ROI present in ROI list.')
            return None
        if name is None:
            if self.active_roi is None:
                self.log.error('No ROI name to delete and no active ROI set.')
                return None
            else:
                name = self.active_roi

        self._roi_list.delete_roi(name) # see method defined in RegionOfInterestList class

        if self.active_roi == name:
            if len(self.roi_names) > 0:
                self.set_active_roi(self.roi_names[0])
            else:
                self.set_active_roi(None)

        # Notify about a changed set of ROIs if necessary
        self.sigRoiUpdated.emit(name, '', np.zeros(3))
        return None

    @QtCore.Slot()
    def delete_all_roi(self):
        self.active_roi = None
        for name in self.roi_names:
            self._roi_list.delete_roi(name)
            self.sigRoiUpdated.emit(name, '', np.zeros(3))
        return None



    @QtCore.Slot(str)
    def set_active_roi(self, name=None):
        """
        Set the name of the currently active ROI
        @param name:
        """
        if not isinstance(name, str) and name is not None:
            self.log.error('ROI name must be of type str or None.')
        elif name is None or name == '':
            self._active_roi = None
        elif name in self.roi_names:
            self._active_roi = str(name)
        else:
            self.log.error('No ROI with name "{0}" found in ROI list.'.format(name))

        self.sigActiveRoiUpdated.emit('' if self.active_roi is None else self.active_roi)
        return None

    def get_roi_position(self, name=None):
        """
        Returns the ROI position of the specified ROI or the active ROI if none is given.

        @param str name: Name of the ROI to return the position for.
                             If None (default) the active ROI position is returned.
        @return float[3]: Coordinates of the desired ROI (x,y,z)
        """
        if name is None:
            name = self.active_roi
        return self._roi_list.get_roi_position(name)


    @QtCore.Slot(str)
    def rename_roi_list(self, new_name):
        if not isinstance(new_name, str) or new_name == '':
            self.log.error('ROI list name to set must be str of length > 0.')
            return None
        self._roi_list.name = new_name
        self.sigRoiListUpdated.emit({'name': self.roi_list_name})
        return None


    @QtCore.Slot()
    def go_to_roi(self, name=None):
        """
        Move translation stage to the given roi.

        @param str name: the name of the ROI, default is the active roi
        """
        if name is None:
            name = self.active_roi
        if not isinstance(name, str):
            self.log.error('ROI name to move to must be of type str.')
            return None
        self._move_stage(self.get_roi_position(name))
        return None

    def _move_stage(self, position):
        """ 
        Move the translation stage to position.
        
        @param float position: tuple (x, y, z)
        """
        # this functions accepts a tuple (x, y, z) as argument because it will be called with the roi position as argument. 
        # Hence, the input argument has to be converted into a dictionary of format {'x': x, 'y': y} to be passed to the translation stage function.
        if len(position) != 3: # modify later to use only 2 coordinates but ask before ..
            self.log.error('Stage position to set must be iterable of length 3.')
            return None
        axis_label = ('x', 'y', 'z')
        pos_dict = dict([*zip(axis_label, position)])
        self.stage().move_abs(pos_dict) 
        return None

#    @QtCore.Slot()
#    def set_cam_image(self, emit_change=True):
#        """ Get the current xy scan data and set as scan_image of ROI. """
#        self._roi_list.set_scan_image() # add the camera logic as connector to get the image ?? or do not show image on ROI map ?
#
#        if emit_change:
#            self.sigRoiListUpdated.emit({'scan_image': self.roi_list_scan_image,
#                                     'scan_image_extent': self.roi_scan_image_extent})
#        return None

    @QtCore.Slot()
    def reset_roi_list(self):
        self._roi_list = RegionOfInterestList() # create an instance of the RegionOfInterestList class
        #self.set_cam_image(False)
        self.sigRoiListUpdated.emit({'name': self.roi_list_name,
                                 'rois': self.roi_positions,
                                 'cam_image': self.roi_list_cam_image,
                                 'cam_image_extent': self.roi_list_cam_image_extent
                                 })
        self.set_active_roi(None)
        return None


    @QtCore.Slot(float)
    def set_roi_width(self, width):
        self._roi_width = float(width)
        self.sigWidthUpdated.emit(width)
        return None


    def save_roi_list(self, path, filename):
        """
        Save the current roi_list to a file. A dictionary format is used.
        """
        # convert the roi_list to a dictionary
        roi_list_dict = self.roi_list_to_dict(self._roi_list)
        
        if not os.path.exists(path):
            try:
                os.makedirs(path) # recursive creation of all directories on the path
            except Exception as err:
                self.log.error('Error {0}'.format(err))
                
        p = os.path.join(path, filename)
        
        with open(p+'.json', 'w') as file:
            json.dump(roi_list_dict, file)
            
        return None
        
    
    
    # to solve: problem with marker size when loading a new list 
    def load_roi_list(self, complete_path=None):
        """ 
        Load a selected roi_list from .json file. 
        """
        # if no path given do nothing
        if complete_path is None:
            return None
        
        with open(complete_path, 'r') as file:
            roi_list_dict = json.load(file) 
            
        self._roi_list = self.dict_to_roi(roi_list_dict)

        
        self.sigRoiListUpdated.emit({'name': self.roi_list_name,
                                 'rois': self.roi_positions,
                                 'cam_image': self.roi_list_cam_image,
                                 'cam_image_extent': self.roi_list_cam_image_extent
                                 })     
        self.set_active_roi(None if len(self.roi_names) == 0 else self.roi_names[0])
        return None
        
        
            
        

    @_roi_list.constructor
    def dict_to_roi(self, roi_dict):
        return RegionOfInterestList.from_dict(roi_dict)

    @_roi_list.representer
    def roi_list_to_dict(self, roi_list):
        return roi_list.to_dict()

