# -*- coding: utf-8 -*-
"""
Created on Wed March 30 2021

@author: fbarho

This file is an extension to Qudi software
obtained from <https://github.com/Ulm-IQO/qudi/>

Merfish Experiment for the RAMM setup

Config example pour copy-paste:
    HiMTask:
        module: 'HiM_task_RAMM'
        needsmodules:
            fpga: 'lasercontrol_logic'
            cam: 'camera_logic'
            daq: 'nidaq_6259_logic'
            piezo: 'focus_logic'
            roi: 'roi_logic'
            valves: 'valve_logic'
            pos: 'positioning_logic'
            flow: 'flowcontrol_logic'
        config:
            path_to_user_config: 'C:/Users/sCMOS-1/qudi_data/qudi_task_config_files/hi_m_task_RAMM.yaml'
"""

import numpy as np
import os
import time
from logic.generic_task import InterruptableTask


class Task(InterruptableTask):  # do not change the name of the class. it is always called Task !
    """ This task iterates over all roi given in a file and does an acquisition of a series of planes in z direction
    using a sequence of lightsources for each plane, for each roi.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print('Task {0} added!'.format(self.name))

    def startTask(self):
        """ """
        self.log.info('started Task')
        # control if experiment can be started : origin defined in position logic ?
        if not self.ref['pos'].origin:
            self.log.warning('No position 1 defined for injections. Experiment can not be started. Please define position 1')
            return

        # set stage velocity
        self.ref['roi'].set_stage_velocity({'x': 1, 'y': 1})

        # close default FPGA session
        self.ref['fpga'].close_default_session()

        # read all user parameters from config
        self.load_user_parameters()

        bitfile = 'C:\\Users\\sCMOS-1\\qudi-cbs\\hardware\\fpga\\FPGA\\FPGA Bitfiles\\FPGAv0_FPGATarget_FPGAmerFISHtrigg_jtu2knQ4gk8.lvbitx'
        self.ref['fpga'].start_task_session(bitfile)

        # start the session on the fpga using the user parameters
        self.ref['fpga'].run_multicolor_imaging_task_session(self.num_z_planes, self.wavelengths, self.intensities, self.num_laserlines)

        # prepare the camera
        self.num_frames = self.num_z_planes * self.num_laserlines
        self.ref['cam'].prepare_camera_for_multichannel_imaging(self.num_frames, self.exposure, None, None, None)

        # initialize a counter to iterate over the number of probes to inject
        self.probe_counter = 0

        # add here the initialization of the autofocus (relative movement of stage and piezo to have travel range in both directions)






    def runTaskStep(self):
        """ Implement one work step of your task here.
        @return bool: True if the task should continue running, False if it should finish.
        """
        # control steps
        if not self.ref['pos'].origin:
            return False

        # info message
        self.probe_counter += 1
        print(f'Probe number {self.probe_counter}')

        # position the needle in the probe
        self.ref['pos'].start_move_to_target(self.probe_counter)

        # start hybridization:
        # position the valves for hybridization sequence
        self.ref['valves'].set_valve_position('b', 2)  # RT rinsing valve: inject probe
        self.ref['valves'].wait_for_idle()
        self.ref['valves'].set_valve_position('c', 2)  # Syringe valve: towards pump
        self.ref['valves'].wait_for_idle()

        # iterate over the steps in the hybridization sequence
        for step in range(len(self.hybridization_list)):
            print(f'Hybridisation step {step+1}')

            if self.hybridization_list[step]['product'] is not None:  # then it is an injection step
                # set the 8 way valve to the position corresponding to the product
                product = self.hybridization_list[step]['product']
                valve_pos = self.buffer_dict[product]
                self.ref['valves'].set_valve_position('a', valve_pos)
                self.ref['valves'].wait_for_idle()

                # as an initial value, set the pressure to 0 mbar
                self.ref['flow'].set_pressure(0.0)
                # start the pressure regulation
                self.ref['flow'].start_pressure_regulation_loop(self.hybridization_list[step]['flowrate'])
                # start counting the volume of buffer or probe
                sampling_interval = 0.5  # in seconds
                self.ref['flow'].start_volume_measurement(self.hybridization_list[step]['volume'],
                                                          sampling_interval)

                # put this thread to sleep until the target volume is reached
                # is it a problem that this thread becomes inresponsive when using sleep function ?
                ready = self.ref['flow'].target_volume_reached
                while not ready:
                    time.sleep(2)
                    ready = self.ref['flow'].target_volume_reached
                self.ref['flow'].stop_pressure_regulation_loop()
                time.sleep(2)  # waiting time to wait until last regulation step is finished, afterwards reset pressure to 0
                self.ref['flow'].set_pressure(0.0)
            else:  # product is none: then it is an incubation step
                t = self.hybridization_list[step]['time']
                print(f'Incubation time.. {t} s')
                self.ref['valves'].set_valve_position('c', 1)
                self.ref['valves'].wait_for_idle()
                time.sleep(self.hybridization_list[step]['time'])
                # maybe it is better to split into small intervals to keep the thread responsive ?????
                self.ref['valves'].set_valve_position('c', 2)
                self.ref['valves'].wait_for_idle()
                print('Incubation time finished')
        # hybridization finished
        # how do the valves need to be set at the end ?

        # start imaging:
        # iterate over all ROIs
        for item in self.roi_names:
            # set the active_roi to none to avoid having two active rois displayed
            self.ref['roi'].active_roi = None
            # go to roi
            self.ref['roi'].set_active_roi(name=item)
            self.ref['roi'].go_to_roi()
            self.log.info('Moved to {}'.format(item))
            # waiting time needed ???
            time.sleep(1)  # replace maybe by wait for idle

            # create a folder for each roi
            cur_save_path = os.path.join(self.save_path, item)
            # create the complete path
            complete_path = self.ref['cam']._create_generic_filename(cur_save_path, '_Scan', 'Scan', '.'+self.file_format, addfile=False)
            self.log.info(f'complete path: {complete_path}')

            # imaging sequence:
            # prepare the daq: set the digital output to 0 before starting the task
            self.ref['daq'].write_to_do_channel(1, np.array([0], dtype=np.uint8), self.ref['daq']._daq.DIO3_taskhandle)

            # # prepare the camera
            # self.num_frames = self.num_z_planes * 2  # len(self.wavelengths)
            # self.ref['cam'].prepare_camera_for_multichannel_imaging(self.num_frames, self.exposure, None, None, None)
            # # # maybe reorganize the prepare_camera_.. method to avoid resetting the triggers all over again at each iteration
            self.ref['cam'].stop_acquisition()   # for safety
            self.ref['cam'].start_acquisition()

            for plane in range(self.num_z_planes):
                print(f'plane number {plane + 1}')

                # position the piezo
                position = self.start_position + plane * self.z_step
                self.ref['piezo'].go_to_position(position)
                print(f'target position: {position} um')
                time.sleep(0.03)
                cur_pos = self.ref['piezo'].get_position()
                print(f'current position: {cur_pos} um')

                # send signal from daq to FPGA connector 0/DIO3 ('piezo ready')
                self.ref['daq'].write_to_do_channel(1, np.array([1], dtype=np.uint8), self.ref['daq']._daq.DIO3_taskhandle)
                time.sleep(0.005)
                self.ref['daq'].write_to_do_channel(1, np.array([0], dtype=np.uint8), self.ref['daq']._daq.DIO3_taskhandle)

                # wait for signal from FPGA to DAQ ('acquisition ready')
                fpga_ready = self.ref['daq'].read_do_channel(1, self.ref['daq']._daq.DIO4_taskhandle)[0]
                t0 = time.time()

                while not fpga_ready:
                    time.sleep(0.001)
                    fpga_ready = self.ref['daq'].read_do_channel(1, self.ref['daq']._daq.DIO4_taskhandle)[0]

                    t1 = time.time() - t0
                    if t1 > 5:  # for safety: timeout if no signal received within 5 s
                        break

            # get acquired data from the camera and save it to file
            image_data = self.ref['cam'].get_acquired_data()
            print(image_data.shape)

            if self.file_format == 'fits':
                metadata = {}  # to be added
                self.ref['cam']._save_to_fits(complete_path, image_data, metadata)
            else:  # use tiff as default format
                self.ref['cam']._save_to_tiff(self.num_frames, complete_path, image_data)
                # add metadata saving

        # imaging (for all ROIs) finished

        # start photobleaching:
        # position the valves for photobleaching sequence
        # self.ref['valves'].set_valve_position('b', 2)  # RT rinsing valve: inject probe
        # self.ref['valves'].wait_for_idle()
        # to add: do the rinsing of the needle

        self.ref['valves'].set_valve_position('c', 2)  # Syringe valve: towards pump
        self.ref['valves'].wait_for_idle()

        # iterate over the steps in the hybridization sequence
        for step in range(len(self.photobleaching_list)):
            print(f'Photobleaching step {step+1}')

            if self.photobleaching_list[step]['product'] is not None:  # then it is an injection step
                # set the 8 way valve to the position corresponding to the product
                product = self.photobleaching_list[step]['product']
                valve_pos = self.buffer_dict[product]
                self.ref['valves'].set_valve_position('a', valve_pos)
                self.ref['valves'].wait_for_idle()

                # as an initial value, set the pressure to 0 mbar
                self.ref['flow'].set_pressure(0.0)
                # start the pressure regulation
                self.ref['flow'].start_pressure_regulation_loop(self.photobleaching_list[step]['flowrate'])
                # start counting the volume of buffer or probe
                sampling_interval = 0.5  # in seconds
                self.ref['flow'].start_volume_measurement(self.photobleaching_list[step]['volume'],
                                                          sampling_interval)

                # put this thread to sleep until the target volume is reached
                # is it a problem that this thread becomes inresponsive when using sleep function ?
                ready = self.ref['flow'].target_volume_reached
                while not ready:
                    time.sleep(2)
                    ready = self.ref['flow'].target_volume_reached
                self.ref['flow'].stop_pressure_regulation_loop()
                time.sleep(2)  # waiting time to wait until last regulation step is finished, afterwards reset pressure to 0
                self.ref['flow'].set_pressure(0.0)
            else:  # product is none: then it is an incubation step
                t = self.photobleaching_list[step]['time']
                print(f'Incubation time.. {t} s')
                self.ref['valves'].set_valve_position('c', 1)
                self.ref['valves'].wait_for_idle()
                time.sleep(self.photobleaching_list[step]['time'])
                # maybe it is better to split into small intervals to keep the thread responsive ?????
                self.ref['valves'].set_valve_position('c', 2)
                self.ref['valves'].wait_for_idle()
                print('Incubation time finished')
        # photobleaching finished
        # how do the valves need to be set at the end ?

        return self.probe_counter < len(self.probe_list)

    def pauseTask(self):
        """ """
        self.log.info('pauseTask called')

    def resumeTask(self):
        """ """
        self.log.info('resumeTask called')

    def cleanupTask(self):
        """ """
        self.log.info('cleanupTask called')
        # reset the camera to default state
        self.ref['cam'].reset_camera_after_multichannel_imaging()
        # close the fpga session
        self.ref['fpga'].end_task_session()
        self.ref['fpga'].restart_default_session()
        self.log.info('restarted default session')
        # reset stage velocity to default
        self.ref['roi'].set_stage_velocity({'x': 7, 'y': 7})  # 5.74592
        self.log.info('cleanupTask finished')

    def load_user_parameters(self):
        # define user parameters  # to be read from config later
        self.exposure = 0.1
        self.num_z_planes = 10
        self.z_step = 0.25  # in um
        self.centered_focal_plane = True
        self.start_position = self.calculate_start_position(self.centered_focal_plane)
        self.imaging_sequence = [('561 nm', 5), ('640 nm', 50)]
        self.save_path = 'C:\\Users\\sCMOS-1\\Desktop\\2021_03_31'  # to be defined how the default folder structure should be set up
        self.file_format = 'tiff'
        self.roi_list_path = 'C:\\Users\\sCMOS-1\\Desktop\\roilist.json'

        # self.injections_path = ''  # use this later on to load buffer dict etc.
        #
        buffer_dict = {1: 'Buffer1', 2: 'Buffer2', 3: 'Buffer3', 4: 'Buffer4', 7: 'Probe'}  # later version: read this from file
        # invert the buffer dict to address the valve by the product name as key
        self.buffer_dict = dict([(value, key) for key, value in buffer_dict.items()])
        print(self.buffer_dict)

        self.probe_dict = {1: 'Probe1', 2: 'Probe2'}
        self.probe_list = [key for key in self.probe_dict]

        self.hybridization_list = [
            {'step_number': 1,
             'procedure': 'Hybridization',
             'product': 'Buffer4',
             'volume': 100,
             'flowrate': 250,
             'time': None},
            {'step_number': 2,
             'procedure': 'Hybridization',
             'product': None,
             'volume': None,
             'flowrate': None,
             'time': 20},
            {'step_number': 3,
             'procedure': 'Hybridization',
             'product': 'Buffer1',
             'volume': 120,
             'flowrate': 150,
             'time': None}
        ]

        self.photobleaching_list = [
            {'step_number': 1,
             'procedure': 'Photobleaching',
             'product': 'Buffer4',
             'volume': 100,
             'flowrate': 250,
             'time': None},
            {'step_number': 2,
             'procedure': 'Photobleaching',
             'product': None,
             'volume': None,
             'flowrate': None,
             'time': 10},
            {'step_number': 3,
             'procedure': 'Photobleaching',
             'product': 'Buffer1',
             'volume': 120,
             'flowrate': 100,
             'time': None}
        ]






        # create a list of roi names
        self.ref['roi'].load_roi_list(self.roi_list_path)
        # get the list of the roi names
        self.roi_names = self.ref['roi'].roi_names

        # convert the imaging_sequence given by user into format required by the bitfile
        lightsource_dict = {'BF': 0, '405 nm': 1, '488 nm': 2, '561 nm': 3, '640 nm': 4}
        self.num_laserlines = len(self.imaging_sequence)
        wavelengths = [self.imaging_sequence[i][0] for i, item in enumerate(self.imaging_sequence)]
        wavelengths = [lightsource_dict[key] for key in wavelengths]
        for i in range(self.num_laserlines, 5):
            wavelengths.append(0)  # must always be a list of length 5: append zeros until necessary length reached
        self.wavelengths = wavelengths

        self.intensities = [self.imaging_sequence[i][1] for i, item in enumerate(self.imaging_sequence)]
        for i in range(self.num_laserlines, 5):
            self.intensities.append(0)




    def calculate_start_position(self, centered_focal_plane):
        """
        @param bool centered_focal_plane: indicates if the scan is done below and above the focal plane (True) or if the focal plane is the bottommost plane in the scan (False)
        """
        current_pos = 20  # for tests until we have the autofocus #self.ref['piezo'].get_position()  # lets assume that we are at focus (user has set focus or run autofocus)

        if centered_focal_plane:  # the scan should start below the current position so that the focal plane will be the central plane or one of the central planes in case of an even number of planes
            # even number of planes:
            if self.num_z_planes % 2 == 0:
                start_pos = current_pos - self.num_z_planes / 2 * self.z_step  # focal plane is the first one of the upper half of the number of planes
            # odd number of planes:
            else:
                start_pos = current_pos - (self.num_z_planes - 1)/2 * self.z_step
            return start_pos
        else:
            return current_pos  # the scan starts at the current position and moves up
