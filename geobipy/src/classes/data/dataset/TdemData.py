"""
.. module:: StatArray
   :platform: Unix, Windows
   :synopsis: Time domain data set

.. moduleauthor:: Leon Foks

"""
from copy import deepcopy
from pathlib import Path
from pandas import read_csv

from ...system.CircularLoop import CircularLoop
from ...system.CircularLoops import CircularLoops
from ...pointcloud.PointCloud3D import PointCloud3D
from .Data import Data
from ..datapoint.TdemDataPoint import TdemDataPoint
from ....classes.core import StatArray

from ...system.TdemSystem import TdemSystem

import numpy as np
from ....base import fileIO as fIO
from ....base import plotting as cP
from ....base import utilities as cF
from ....base import MPI as myMPI
import matplotlib.pyplot as plt
from os.path import join


class TdemData(Data):
    """Time domain electro magnetic data set

    A time domain data set with easting, northing, height, and elevation values. Each sounding in the data set can be given a receiver and transmitter loop.

    TdemData(nPoints=1, nTimes=[1], nSystems=1)

    Parameters
    ----------
    nPoints : int, optional
        Number of soundings in the data file
    nTimes : array of ints, optional
        Array of size nSystemsx1 containing the number of time gates in each system
    nSystem : int, optional
        Number of measurement systems

    Returns
    -------
    out : TdemData
        Time domain data set

    See Also
    --------
    :func:`~geobipy.src.classes.data.dataset.TdemData.TdemData.read`
        For information on file format

    """

    single = TdemDataPoint

    def __init__(self, system=None, **kwargs):
        """ Initialize the TDEM data """

        # if not systems is None:
        #     return

        self.system = system

        kwargs['components'] = kwargs.get('components', self.components)
        kwargs['channels_per_system'] = kwargs.get('channels_per_system', self.n_components * self.nTimes)
        # kwargs['components_per_channel'] = kwargs.get('components_per_channel', self.system[0].components)
        kwargs['units'] = r"$\frac{V}{m^{2}}$"

        # Data Class containing xyz and channel values
        super().__init__(**kwargs)

        self.primary_field = kwargs.get('primary_field')
        self.secondary_field = kwargs.get('secondary_field')
        self.predicted_primary_field = kwargs.get('predicted_primary_field')
        self.predicted_secondary_field = kwargs.get('predicted_secondary_field')

        # StatArray of Transmitter loops
        self.transmitter = kwargs.get('transmitter')
        # StatArray of Receiever loops
        self.receiver = kwargs.get('receiver')
        # # Loop Offsets
        # self.loopOffset = kwargs.get('loopOffset', None)

        self.channelNames = kwargs.get('channel_names')

    @Data.channelNames.setter
    def channelNames(self, values):
        if values is None:
            self._channelNames = []
            for i in range(self.nSystems):
                # Set the channel names
                for ic in range(self.n_components):
                    for iTime in range(self.nTimes[i]):
                        s = 'S{}{} time {:.3e}'.format(i, self.components[ic].upper(), self.system[i].windows.centre[iTime])
                        self._channelNames.append(s)
        else:
            assert all((isinstance(x, str) for x in values))
            assert len(values) == self.nChannels, Exception("Length of channelNames must equal total number of channels {}".format(self.nChannels))
            self._channelNames = values

    @Data.data.getter
    def data(self):

        if np.size(self._data, 0) == 0:
            self._data = StatArray.StatArray((self.nPoints, self.nChannels), "Data", self.units)

        for j in range(self.nSystems):
            for i in range(self.n_components):
                ic = self._component_indices(i, j)
                self._data[:, ic] = self.primary_field[:, i][:, None] + self.secondary_field[:, ic]

            # self._data[np.isnan(self.secondary_field)] = np.nan

        return self._data

    @property
    def loopOffset(self):

        return np.vstack([self.receiver.x - self.transmitter.x,
                          self.receiver.y - self.transmitter.y, 
                          self.receiver.z - self.transmitter.z]).T

        # offset = np.empty((self.nPoints, 3))
        # for i in range(self.nPoints):
        #     offset[i, :] = np.r_[self.receiver[i].x - self.transmitter[i].x,
        #                          self.receiver[i].y - self.transmitter[i].y,
        #                          self.receiver[i].z - self.transmitter[i].z]
        # return offset

    # @loopOffset.setter
    # def loopOffset(self, values):
    #     if (values is None):
    #         self._loopOffset = StatArray.StatArray(
    #             (self.nPoints, 3), "Loop Offset")
    #     else:
    #         if self.nPoints == 0:
    #             self.nPoints = np.size(values)
    #         assert np.all(np.shape(values) == (self.nPoints, 3)), ValueError(
    #             "loopOffset must have shape {}".format((self.nPoints, 3)))
    #         if (isinstance(values, StatArray.StatArray)):
    #             self._loopOffset = deepcopy(values)
    #         else:
    #             self._loopOffset = StatArray.StatArray(values, "Loop Offset")

    @property
    def nTimes(self):
        return np.asarray([x.nTimes for x in self.system])

    @property
    def predicted_primary_field(self):
        """The data. """
        if np.size(self._predicted_primary_field, 0) == 0:
            self._predicted_primary_field = StatArray.StatArray((self.nPoints, self.n_components * self.nSystems), "Predicted Primary field", self.units)
        return self._predicted_primary_field

    @predicted_primary_field.setter
    def predicted_primary_field(self, values):
        shp = (self.nPoints, self.n_components * self.nSystems)
        if values is None:
            self._predicted_primary_field = StatArray.StatArray(shp, "Predicted primary field", self.units)
        else:
            if self.nPoints == 0:
                self.nPoints = np.size(values, 0)
            # if self.nChannels == 0:
            #     self.channels_per_system = np.size(values, 1)
            shp = (self.nPoints, self.n_components * self.nSystems)
            assert np.allclose(np.shape(values), shp) or np.size(values) == self.nPoints, ValueError("predicted_primary_field must have shape {}".format(shp))
            self._predicted_primary_field = StatArray.StatArray(values)

    @property
    def predicted_secondary_field(self):
        """The data. """
        if np.size(self._predicted_secondary_field, 0) == 0:
            self._predicted_secondary_field = StatArray.StatArray((self.nPoints, self.nChannels), "Predicted secondary field", self.units)
        return self._predicted_secondary_field

    @predicted_secondary_field.setter
    def predicted_secondary_field(self, values):
        shp = (self.nPoints, self.nChannels)
        if values is None:
            values = shp
        else:
            if self.nPoints == 0:
                self.nPoints = np.size(values, 0)
            if self.nChannels == 0:
                self.channels_per_system = np.size(values, 1)
            shp = (self.nPoints, self.nChannels)
            assert np.allclose(np.shape(values), shp) or np.size(values) == self.nPoints, ValueError("predicted_seconday_field must have shape {}".format(shp))

        self._predicted_secondary_field = StatArray.StatArray(values, "Predicted secondary field", self.units)

    @property
    def primary_field(self):
        """The data. """
        if np.size(self._primary_field, 0) == 0:
            self._primary_field = StatArray.StatArray((self.nPoints, self.n_components * self.nSystems), "Primary field", self.units)
        return self._primary_field

    @primary_field.setter
    def primary_field(self, values):
        shp = (self.nPoints, self.n_components * self.nSystems)

        if values is None:
            self._primary_field = StatArray.StatArray(shp, "Primary field", self.units)
        else:
            if self.nPoints == 0:
                self.nPoints = np.size(values, 0)
            # if self.nChannels == 0:
            #     self.channels_per_system = np.size(values, 1)
            shp = (self.nPoints, self.n_components * self.nSystems)
            assert np.allclose(np.shape(values), shp) or np.size(values) == self.nPoints, ValueError("primary_field must have shape {}".format(shp))
            self._primary_field = StatArray.StatArray(values)  

    @property
    def receiver(self):
        return self._receiver

    @receiver.setter
    def receiver(self, values):
        if (values is None):
            self._receiver = CircularLoops()
        else:
            assert isinstance(values, CircularLoops), ValueError('receiver must have type geobipy.CircularLoops')
            if self.nPoints == 0:
                self.nPoints = values.nPoints
            assert values.nPoints == self.nPoints, ValueError("receiver must have size {}".format(self.nPoints))
            
            self._receiver = values

    @property
    def secondary_field(self):
        """The data. """
        if np.size(self._secondary_field, 0) == 0:
            self._secondary_field = StatArray.StatArray((self.nPoints, self.nChannels), "Secondary field", self.units)
        return self._secondary_field

    @secondary_field.setter
    def secondary_field(self, values):
        shp = (self.nPoints, self.nChannels)
        if values is None:
            self._secondary_field = StatArray.StatArray(shp, "Secondary field", self.units)
        else:
            if self.nPoints == 0:
                self.nPoints = np.size(values, 0)
            if self.nChannels == 0:
                self.channels_per_system = np.size(values, 1)
            shp = (self.nPoints, self.nChannels)
            assert np.allclose(np.shape(values), shp) or np.size(values) == self.nPoints, ValueError("seconday_field must have shape {}".format(shp))
            self._secondary_field = StatArray.StatArray(values)

    @Data.std.getter
    def std(self):
        if np.size(self._std, 0) == 0:
            self._std = StatArray.StatArray((self.nPoints, self.nChannels), "Standard deviation", self.units)

        if self.relative_error.max() > 0.0:
            for i in range(self.nSystems):
                j = self._systemIndices(i)
                self._std[:, j] = np.sqrt((self.relative_error[:, i][:, None] * self.secondary_field[:, j])**2 + (self.additive_error[:, i]**2.0)[:, None])

        return self._std

    @property
    def system(self):
        return self._system

    @system.setter
    def system(self, values):

        if values is None:
            self._system = None
            self.components = None
            return

        if isinstance(values, (str, TdemSystem)):
            values = [values]
        nSystems = len(values)
        # Make sure that list contains strings or TdemSystem classes
        assert all([isinstance(x, (str, TdemSystem)) for x in values]), TypeError("system must be str or list of either str or geobipy.TdemSystem")

        self._system = [None] * nSystems

        for i, s in enumerate(values):
            if isinstance(s, str):
                self._system[i] = TdemSystem.read(s)
            else:
                self._system[i] = s

        self.components = self.system[0].components
        # self.channels_per_system = np.asarray([s.n_channels for s in self.system])

    @property
    def transmitter(self):
        return self._transmitter

    @transmitter.setter
    def transmitter(self, values):

        if (values is None):
            self._transmitter = CircularLoops()
        else:
            assert isinstance(values, CircularLoops), ValueError('transmitter must have type geobipy.CircularLoops')
            if self.nPoints == 0:
                self.nPoints = values.nPoints
            assert values.nPoints == self.nPoints, ValueError("transmitter must have size {}".format(self.nPoints))
            
            self._transmitter = values

    def _as_dict(self):
        out, order = super()._as_dict()
        out['tx_pitch'] = np.squeeze(np.asarray([x.pitch for x in self.transmitter]))
        out['tx_roll'] = np.squeeze(np.asarray([x.roll for x in self.transmitter]))
        out['tx_yaw'] = np.squeeze(np.asarray([x.yaw for x in self.transmitter]))

        offset = self.loopOffset
        for i, label in enumerate(['txrx_dx','txrx_dy','txrx_dz']):
            out[label] = np.squeeze(offset[:, i])

        out['rx_pitch'] = np.squeeze(np.asarray([x.pitch for x in self.receiver]))
        out['rx_roll'] = np.squeeze(np.asarray([x.roll for x in self.receiver]))
        out['rx_yaw'] = np.squeeze(np.asarray([x.yaw for x in self.receiver]))

        order = [*order[:6], 'tx_pitch', 'tx_roll', 'tx_yaw', 'txrx_dx', 'txrx_dy', 'txrx_dz', 'rx_pitch', 'rx_roll', 'rx_yaw', *order[6:]]

        return out, order

    def append(self, other):

        super().append(self, other)

        # self.loopOffset = np.hstack([self.loopOffset, other.loopOffset])
        self.T = np.hstack([self.T, other.T])
        self.R = np.hstack(self.R, other.R)

    # def _component_indices(self, component=0, system=0):
    #     assert component < self.n_components, ValueError("component must be < {}".format(self.n_components))
    #     return np.s_[((self.nTimes*component)+(system*self.nChannels))[0]:(self.nTimes*(component+1)+(system*self.nChannels))[0]]

    @property
    def _ravel_index(self):
        return np.cumsum(np.hstack([0, np.repeat(self.nTimes, self.n_components)]))

    def _component_indices(self, component=0, system=0):
        i = np.ravel_multi_index((component, system), (self.n_components, self.nSystems))
        return np.s_[self._ravel_index[i]:self._ravel_index[i+1]]

    @classmethod
    def read_csv(cls, data_filename, system_filename):
        """Reads the data and system parameters from file

        Parameters
        ----------
        dataFilename : str or list of str
            Time domain data file names
        systemFilename : str or list of str
            Time domain system file names

        Notes
        -----
        File Format

        The data columns are read in according to the column names in the first line.  The header line should contain at least the following column names. Extra columns may exist, but will be ignored. In this description, the column name or its alternatives are given followed by what the name represents. Optional columns are also described.

        **Required columns**

        line
            Line number for the data point

        id or fid
            Id number of the data point, these be unique

        x or northing or n
            Northing co-ordinate of the data point

        y or easting or e
            Easting co-ordinate of the data point

        z or dtm or dem\_elev or dem\_np or topo
            Elevation of the ground at the data point

        alt or laser or bheight
            Altitude of the transmitter coil

        Off[0] to Off[nWindows-1]  (with the number and brackets)
           The measurements for each time specified in the accompanying system file under Receiver Window Times

        **Optional columns**

        If any loop orientation columns are omitted the loop is assumed to be horizontal.

        TxPitch
            Pitch of the transmitter loop
        TxRoll
            Roll of the transmitter loop
        TxYaw
            Yaw of the transmitter loop
        RxPitch
            Pitch of the receiver loop
        RxRoll
            Roll of the receiver loop
        RxYaw
            Yaw of the receiver loop

        OffErr[0] to ErrOff[nWindows-1]
            Error estimates for the data


        See Also
        --------
        INFORMATION ON TD SYSTEMS


        """

        # Get the number of systems to use
        if (isinstance(system_filename, str)):
            system_filename = [system_filename]

        nSystems = len(system_filename)

        # assert nDatafiles == nSystems, Exception("Number of data files must match number of system files.")

        self = cls(system=system_filename)

        self._nPoints, iC, iR, iT, iOffset, iData, iStd, iPrimary = self._csv_channels(data_filename)

        assert len(iData) == self.nChannels, Exception("Number of off time columns {} in {} does not match total number of times {} in system files \n {}".format(
            len(iData), data_filename, self.nChannels, self.fileInformation()))

        if len(iStd) > 0:
            assert len(iStd) == len(iData), Exception(
                "Number of Off time standard deviation estimates does not match number of Off time data columns in file {}. \n {}".format(data_filename, self.fileInformation()))

        # Get all readable column indices for the first file.
        channels = iC + iR + iT + iOffset + iData
        if len(iStd) > 0:
            channels += iStd
        if len(iPrimary) > 0:
            channels += iPrimary

        # Read in the columns from the first data file
        try:
            df = read_csv(data_filename, usecols=channels, skipinitialspace = True)
        except:
            df = read_csv(data_filename, usecols=channels, delim_whitespace=True, skipinitialspace = True)
        df = df.replace('NaN', np.nan)

        # Assign columns to variables
        self.lineNumber = df[iC[0]].values
        self.fiducial = df[iC[1]].values
        self.x = df[iC[2]].values
        self.y = df[iC[3]].values
        self.z = df[iC[4]].values
        self.elevation = df[iC[5]].values

        self.transmitter = CircularLoops(x=self.x, y=self.y, z=self.z,
                            pitch=df[iT[0]].values, roll=df[iT[1]].values, yaw=df[iT[2]].values,
                            radius=np.full(self.nPoints, fill_value=self.system[0].loopRadius()))

        loopOffset = df[iOffset].values

        # Assign the orientations of the acquisistion loops
        self.receiver = CircularLoops(x = self.transmitter.x + loopOffset[:, 0],
                                     y = self.transmitter.y + loopOffset[:, 1],
                                     z = self.transmitter.z + loopOffset[:, 2],
                                     pitch=df[iR[0]].values, roll=df[iR[1]].values, yaw=df[iR[2]].values,
                                     radius=np.full(self.nPoints, fill_value=self.system[0].loopRadius()))

        # Get the data values
        # iSys = self._systemIndices(0)

        self.secondary_field[:, :] = df[iData].values
        # If the data error columns are given, assign them
        self.std;
        if len(iStd) > 0:
            self._std[:, :] = df[iStd].values

        if len(iPrimary) > 0:
            self.primary_field = np.squeeze(df[iPrimary].values)

        # # Read in the data for the other systems.  Only read in the data and, if available, the errors
        # if len(data_filename) == 1:
        #     return self

        # for i in range(1, self.nSystems):

        #     nPoints, iC, iR, iT, iOffset, iData, iStd = self._csv_channels(data_filename[i])

        #     # Assign the columns to read
        #     channels = iData
        #     if len(iStd) > 0:
        #         channels += iStd

        #     # Read the columns
        #     try:
        #         df = read_csv(data_filename[i], usecols=channels, skipinitialspace = True)
        #     except:
        #         df = read_csv(data_filename[i], usecols=channels, delim_whitespace=True, skipinitialspace = True)
        #     df = df.replace('NaN',np.nan)

        #     # Assign the data
        #     iSys = self._systemIndices(i)

        #     self.secondary_field[:, iSys] = df[iData].values

        #     if len(iStd) > 0:
        #         self.std[:, iSys] = df[iStd].values
        #     else:
        #         self.std[:, iSys] = 0.1 * self.secondary_field[:, iSys]   

        self.check()

        return self


    # def readSystemFile(self, systemFilename):
    #     """ Reads in the C++ system handler using the system file name """

    #     if isinstance(systemFilename, str):
    #         systemFilename = [systemFilename]

    #     nSys = len(systemFilename)
    #     self.system = np.ndarray(nSys, dtype=TdemSystem)

    #     for i in range(nSys):
    #         self.system[i] = TdemSystem().read(systemFilename[i])

    #     # self.nSystems = nSys
    #     self.nChannelsPerSystem = np.asarray([np.int32(x.nwindows()) for x in self.system])

    #     self._systemOffset = np.append(0, np.cumsum(self.nChannelsPerSystem))

    def csv_channels(self, data_filename):

        self._nPoints, self._iC, self._iR, self._iT, self._iOffset, self._iData, self._iStd, self._iPrimary = TdemData._csv_channels(data_filename)

        self._channels = self._iC + self._iR + self._iT + self._iOffset + self._iData
        if len(self._iStd) > 0:
            self._channels += self._iStd

        if len(self._iPrimary) > 0:
            self._channels += self._iPrimary

        return self._channels

    @staticmethod
    def _csv_channels(data_filename):
        """Reads the column indices for the co-ordinates, loop orientations, and data from the TdemData file.

        Parameters
        ----------
        dataFilename : str or list of str
            Path to the data file(s)
        system : list of geobipy.TdemSystem
            System class for each time domain acquisition system.

        Returns
        -------
        indices : list of ints
            Size 6 indices to line, fid, easting, northing, height, and elevation.
        rLoopIndices : list of ints
            Size 3 indices to pitch, roll, and yaw, for the receiver loop.
        tLoopIndices : list of ints
            Size 3 indices to pitch, roll, and yaw, for the transmitter loop.
        offDataIndices : list of ints
            Indices to the off time data columns.  Size == number of time windows.
        offErrIndices : list of ints
            Indices to the off time uncertainty estimate columns.  Size == number of time windows.

        """
        # First get the number of points in each data file. They should be equal.
        rloop_names = ('rx_pitch', 'rx_roll', 'rx_yaw')
        tloop_names = ('tx_pitch', 'tx_roll', 'tx_yaw')
        offset_names = ('txrx_dx', 'txrx_dy', 'txrx_dz')

        # for k, f in enumerate(data_filename):
        # Get the column headers of the data file
        channels = fIO.get_column_name(data_filename)

        nPoints, location_channels = Data._csv_channels(data_filename)

        nr = 0
        nt = 0
        no = 0
        rLoop_channels = [None]*3
        tLoop_channels = [None]*3
        offset_channels = [None]*3
        on = []
        on_error = []
        off_channels = []
        off_error_channels = []
        primary_channels = []

        # Check for each aspect of the data file and the number of columns
        for channel in channels:
            cTmp = channel.lower()
            if cTmp in rloop_names:
                nr += 1
                rLoop_channels[rloop_names.index(cTmp)] = channel
            elif cTmp in tloop_names:
                nt += 1
                tLoop_channels[tloop_names.index(cTmp)] = channel
            elif cTmp in offset_names:
                no += 1
                offset_channels[offset_names.index(cTmp)] = channel
            elif "on_time" in cTmp:
                if 'err' in cTmp:
                    on_error.append(channel)
                else:
                    on.append(channel)
            elif any(x in cTmp for x in ("off_time", "x_time", "y_time", "z_time")):
                if 'err' in cTmp:
                    off_error_channels.append(channel)
                else:
                    off_channels.append(channel)
            elif cTmp in ('px', 'py', 'pz'):
                primary_channels.append(channel)
            
        primary_channels.sort()

        assert nr == 3, Exception(
            'Must have all three RxPitch, RxRoll, and RxYaw headers in data file {} if reciever orientation is specified. \n {}'.format(data_filename, TdemData.fileInformation()))
        assert nt == 3, Exception(
            'Must have all three TxPitch, TxRoll, and TxYaw headers in data file {} if transmitter orientation is specified. \n {}'.format(data_filename, TdemData.fileInformation()))
        assert no == 3, Exception(
            'Must have all three txrx_dx, txrx_dy, and txrx_dz headers in data file {} if transmitter-reciever loop separation is specified. \n {}'.format(data_filename, TdemData.fileInformation()))

        return nPoints, location_channels, rLoop_channels, tLoop_channels, offset_channels, off_channels, off_error_channels, primary_channels

    @classmethod
    def _initialize_sequential_reading(cls, data_filename, system_filename):
        """Special function to initialize a file for reading data points one at a time.

        Parameters
        ----------
        dataFileName : str
            Path to the data file
        systemFname : str
            Path to the system file

        """
        # Read in the EM System file
        self = cls(system_filename)
        self._data_filename = data_filename
        self._open_csv_files(data_filename)
        return self

    def _open_csv_files(self, filename):
        super()._open_csv_files(filename)
        self.csv_channels(filename)

    @property
    def nSystems(self):
        return np.size(self.channels_per_system)

    @property
    def channels_per_system(self):
        return self.n_components * self.nTimes

    def _read_record(self, record=None):
        """Reads a single data point from the data file.

        FdemData.__initLineByLineRead() must have already been run.

        """
        
        try:
            df = self._file.get_chunk()
            df = df.replace('NaN', np.nan)
            endOfFile = False
        except:
            self._file.close()
            endOfFile = True

        if endOfFile:
            return None

        secondary_field = np.squeeze(df[self._iData].values)

        if len(self._iStd) == 0:
            S = 0.1 * secondary_field
        else:
            S = np.squeeze(df[self._iStd].values)

        primary_field = None
        if len(self._iPrimary) > 0:
            primary_field = np.squeeze(df[self._iPrimary].values)

        data = np.squeeze(df[self._iC].values)

        loopOffset = np.squeeze(df[self._iOffset].values)

        tloop = np.squeeze(df[self._iT].values).astype(np.float64)
        
        T = CircularLoop(x=data[2], y=data[3], z=data[4],
                         pitch=tloop[0], roll=tloop[1],yaw=tloop[2],
                         radius=self.system[0].loopRadius())

        rloop = np.squeeze(df[self._iR].values).astype(np.float64)
        R = CircularLoop(x=T.x + loopOffset[0],
                         y=T.y + loopOffset[1],
                         z=T.z + loopOffset[2],
                         pitch=rloop[0], roll=rloop[1], yaw=rloop[2],
                         radius=self.system[0].loopRadius())

        return self.single(x=data[2], y=data[3], z=data[4], elevation=data[5],
                        secondary_field=secondary_field, std=S,
                        primary_field=primary_field,
                        system=self.system,
                        transmitter_loop=T, receiver_loop=R,
                        lineNumber=data[0], fiducial=data[1])

    def check(self):
        if (np.any(self._data[~np.isnan(self._data)] <= 0.0)):
            print("Warning: Your data contains values that are <= 0.0")

    def estimateAdditiveError(self):
        """ Uses the late times after 1ms to estimate the additive errors and error bounds in the data. """
        for i in range(self.nSystems):
            h = 'System {} \n'.format(i)
            iS = self._systemIndices(i)
            D = self._data[:, iS]
            t = self.times(i)
            i1ms = t.searchsorted(1e-3)

            if (i1ms < t.size):
                lateD = D[:, i1ms:]
                if np.all(np.isnan(lateD)):
                    j = i1ms - 1
                    d = D[:, j]
                    while np.all(np.isnan(d)) and j > 0:
                        j -= 1
                        d = D[:, j]

                    h += 'All data values for times > 1ms are NaN \nUsing the last time gate with non-NaN values.\n'
                else:
                    d = lateD
                    h += 'Using {} time gates after 1ms\n'.format(self.nTimes[i] - i1ms)

            else:
                h = 'System {} has no time gates after 1ms \nUsing the last time gate with non-NaN values. \n'.format(i)

                j = -1
                d = D[:, j]
                while np.all(np.isnan(d)) and j > 0:
                    j -= 1
                    d = D[:, j]

            s = np.nanstd(d)
            h +=    '  Minimum: {} \n'\
                    '  Maximum: {} \n'\
                    '  Median:  {} \n'\
                    '  Mean:    {} \n'\
                    '  Std:     {} \n'\
                    '  4Std:    {} \n'.format(np.nanmin(d), np.nanmax(d), np.nanmedian(d), np.nanmean(d), s, 4.0*s)
            print(h)

    def datapoint(self, index=None, fiducial=None):
        """Get the ith data point from the data set

        Parameters
        ----------
        index : int, optional
            Index of the data point to get.
        fiducial : float, optional
            Fiducial of the data point to get.

        Returns
        -------
        out : geobipy.FdemDataPoint
            The data point.

        Raises
        ------
        Exception
            If neither an index or fiducial are given.

        """
        iNone = index is None
        fNone = fiducial is None

        assert not (iNone and fNone) ^ (not iNone and not fNone), Exception("Must specify either an index OR a fiducial.")

        if not fNone:
            index = self.fiducial.searchsorted(fiducial)

        i = index

        return self.single(self.x[i], self.y[i], self.z[i], self.elevation[i],
                             self.primary_field[i, :], self.secondary_field[i, :],
                             relative_error=self.relative_error[i, :], additive_error=self.additive_error[i, :], std = self.std[i, :],
                             predicted_primary_field=None, predicted_secondary_field=None,
                             system = self.system,
                             transmitter_loop = self.transmitter[i], receiver_loop = self.receiver[i],
                             lineNumber = self.lineNumber[i], fiducial = self.fiducial[i])

    def off_time(self, system=0):
        """ Obtain the times from the system file """
        assert 0 <= system < self.nSystems, ValueError('system must be in (0, {}]'.format(self.nSystems))
        return self.system[system].off_time

    def __getitem__(self, i):
        """ Define item getter for TdemData """
        if not isinstance(i, slice):
            i = np.unique(i)
        return type(self)(self.system,
                        x=self.x[i],
                        y=self.y[i],
                        z=self.z[i],
                        elevation=self.elevation[i],
                        lineNumber=self.lineNumber[i],
                        fiducial=self.fiducial[i],
                        transmitter=self.transmitter[i],
                        receiver=self.receiver[i],
                        # loopOffset=self.loopOffset[i, :],
                        secondary_field=self.secondary_field[i, :],
                        primary_field=self.primary_field[i, :],
                        std=self.std[i, :],
                        predicted_secondary_field=self.predicted_secondary_field[i, :],
                        predicted_primary_field=self.predicted_primary_field[i, :],
                        channelNames=self.channelNames)

    @staticmethod
    def fileInformation():
        s = ('\nThe data columns are read in according to the column names in the first line \n'
             'The header line should contain at least the following column names. Extra columns may exist, but will be ignored \n'
             'In this description, the column name or its alternatives are given followed by what the name represents \n'
             'Optional columns are also described \n'
             'Required columns'
             'line \n'
             '    Line number for the data point\n'
             'id or fid \n'
             '    Id number of the data point, these be unique\n'
             'x or northing or n \n'
             '    Northing co-ordinate of the data point, (m)\n'
             'y or easting or e \n'
             '    Easting co-ordinate of the data point, (m)\n'
             'z or alt or laser or bheight \n'
             '    Altitude of the transmitter coil above ground level (m)\n'
             'dtm or dem_elev or dem_np \n'
             '    Elevation of the ground at the data point (m)\n'
             'txrx_dx \n'
             '    Distance in x between transmitter and reciever (m)\n'
             'txrx_dy \n'
             '    Distance in y between transmitter and reciever (m)\n'
             'txrx_dz \n'
             '    Distance in z between transmitter and reciever (m)\n'
             'Tx_Pitch \n'
             '    Pitch of the transmitter loop\n'
             'Tx_Roll \n'
             '    Roll of the transmitter loop\n'
             'Tx_Yaw \n'
             '    Yaw of the transmitter loop\n'
             'Rx_Pitch \n'
             '    Pitch of the receiver loop\n'
             'Rx_Roll \n'
             '    Roll of the receiver loop\n'
             'Rx_Yaw \n'
             '    Yaw of the receiver loop\n'
             'Off[0] Off[1] ... Off[nWindows]  - with the number and square brackets\n'
             '    The measurements for each time specified in the accompanying system file under Receiver Window Times \n'
             'Optional columns\n'
             'OffErr[0] OffErr[1] ... Off[nWindows]\n'
             '    Estimates of standard deviation for each off time measurement.')
        return s

    def find_best_halfspace(self, minConductivity=1e-4, maxConductivity=1e4, nSamples=100):

        conductivity = np.zeros(self.nPoints)
        for i in range(self.nPoints):
            dp = self.datapoint(i)
            mod = dp.find_best_halfspace(minConductivity, maxConductivity, nSamples)
            conductivity[i] = mod.values.value

        return conductivity



    def mapChannel(self, channel, system=0, *args, **kwargs):
        """ Create a map of the specified data channel """

        tmp = self.getChannel(system, channel)
        kwargs['c'] = tmp

        self.map(*args, **kwargs)

        cP.title(tmp.name)

    def plot(self, *args, **kwargs):
        """ Plots the data

        Parameters
        ----------
        system : int
            System to plot
        channels : sequence of ints
            Channels to plot

        """

        # legend = kwargs.pop('legend', True)
        kwargs['yscale'] = kwargs.get('yscale', 'log')
        return super().plot(*args, **kwargs)

        # x = self.getXAxis(xAxis)

        # if channels is None:
        #     i = self._systemIndices(system)
        #     ax = cP.plot(x, self.data[:, i],
        #                  label=self.channelNames[i], **kwargs)
        # else:
        #     channels = np.atleast_1d(self.channel_index(channels, system))
        #     for i in channels:
        #         ax = cP.plot(x, self.data[:, i], label=self.channelNames[i], **kwargs)

        # plt.xlabel(cF.getNameUnits(x))

        # # Put a legend to the right of the current axis
        # if legend:
        #     leg = ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), fancybox=True)
        #     leg.set_title(self.data.getNameUnits())
        
        # return ax        

    def plotLine(self, line, xAxis='index', **kwargs):

        line = self.line(line)
        kwargs['yscale'] = kwargs.get('yscale', 'log')

        x = self.getXAxis(xAxis)

        for i in range(self.nSystems):
            plt.subplot(self.nSystems, 1, i + 1)
            j = self._systemIndices(i)
            kwargs['labels'] = line.channelNames[j]
            line.data[:, j].plot(x=x, **kwargs)

    def plotPredicted(self, *args, **kwargs):
        kwargs['yscale'] = kwargs.get('yscale', 'log')
        return super().plotPredicted(*args, **kwargs)

    def plotWaveform(self, **kwargs):
        for i in range(self.nSystems):
            plt.subplot(self.nSystems, 1, i + 1)
            plt.plot(self.system[i].waveform.time,
                     self.system[i].waveform.current, **kwargs)
            if (i == self.nSystems-1):
                cP.xlabel('Time (s)')
            cP.ylabel('Normalized Current (A)')
            plt.margins(0.1, 0.1)

    def pcolor(self, component=0, system=0, yAxis='index', **kwargs):
        """ Plot the data in the given system as a 2D array
        """
        D = self.data[:, self._component_indices(component, system)]
        times = self.off_time(system)
        y = self.getXAxis(xAxis=yAxis)
        ax = D.pcolor(x=times, y=y, **kwargs)
        return ax

    @property
    def summary(self):
        """ Display a summary of the TdemData """
        msg = PointCloud3D.summary
        msg = "Tdem Data: \n"
        msg += "Number of Systems: :" + str(self.nSystems) + '\n'
        msg += self.lineNumber.summary
        msg += self.id.summary
        msg += self.elevation.summary
        return msg

    def createHdf(self, parent, myName, withPosterior=True, fillvalue=None):
        """ Create the hdf group metadata in file
        parent: HDF object to create a group inside
        myName: Name of the group
        """
        # create a new group inside h5obj
        grp = super().createHdf(parent, myName, withPosterior, fillvalue)

        grp.create_dataset('nSystems', data=self.nSystems)
        for i in range(self.nSystems):
            txt = np.string_(Path(self.system[i].filename).read_text())
            grp.create_dataset('System{}'.format(i), data=txt)

        self.transmitter.createHdf(grp, 'T', withPosterior=withPosterior, fillvalue=fillvalue)
        self.receiver.createHdf(grp, 'R', withPosterior=withPosterior, fillvalue=fillvalue)

        self.primary_field.createHdf(grp, 'primary_field', withPosterior=withPosterior, fillvalue=fillvalue)
        self.secondary_field.createHdf(grp, 'secondary_field', withPosterior=withPosterior, fillvalue=fillvalue)
        self.predicted_primary_field.createHdf(grp, 'predicted_primary_field', withPosterior=withPosterior, fillvalue=fillvalue)
        self.predicted_secondary_field.createHdf(grp, 'predicted_secondary_field', withPosterior=withPosterior, fillvalue=fillvalue)

        return grp

    def writeHdf(self, parent, name, withPosterior=True):
        """ Write the StatArray to an HDF object
        parent: Upper hdf file or group
        myName: object hdf name. Assumes createHdf has already been called
        create: optionally create the data set as well before writing
        """
        super().writeHdf(parent, name, withPosterior)

        grp = parent[name]

        self.transmitter.writeHdf(grp, 'T', withPosterior=withPosterior)
        self.receiver.writeHdf(grp, 'R', withPosterior=withPosterior)

        self.primary_field.writeHdf(grp, 'primary_field', withPosterior=withPosterior)
        self.secondary_field.writeHdf(grp, 'secondary_field', withPosterior=withPosterior)
        self.predicted_primary_field.writeHdf(grp, 'predicted_primary_field', withPosterior=withPosterior)
        self.predicted_secondary_field.writeHdf(grp, 'predicted_secondary_field', withPosterior=withPosterior)

    @classmethod
    def fromHdf(cls, grp, **kwargs):
        """ Reads the object from a HDF group """

        if kwargs.get('index') is not None:
            return cls.single.fromHdf(grp, **kwargs)

        nSystems = np.int32(np.asarray(grp.get('nSystems')))
        
        systems = [None]*nSystems
        for i in range(nSystems):
            # Get the system file name. h5py has to encode strings using utf-8, so decode it!
            txt = str(np.asarray(grp.get('System{}'.format(i))), 'utf-8')


            if '.stm' in txt:
                path = kwargs['system_file_path']
                systems[i] = join(path, txt)
            else:

                with open('System{}'.format(i), 'w') as f:
                    f.write(txt)
                systems[i] = 'System{}'.format(i)

        self = super(TdemData, cls).fromHdf(grp, system=systems)

        # sz = StatArray.StatArray.fromHdf(grp['predicted_secondary_field'])
        # print(sz.min(), sz.max())

        self.primary_field = None#StatArray.StatArray.fromHdf(grp['primary_field'])
        self.secondary_field = StatArray.StatArray.fromHdf(grp['secondary_field'])
        self.predicted_primary_field = None#StatArray.StatArray.fromHdf(grp['predicted_primary_field'])
        self.predicted_secondary_field = StatArray.StatArray.fromHdf(grp['predicted_secondary_field'])

        self.transmitter = CircularLoops.fromHdf(grp['T'])
        self.receiver = CircularLoops.fromHdf(grp['R'])

        return self

    def _BcastSystem(self, world, root=0, system=None):
        """Broadcast the TdemSystems.

        The TD systems have a c++ backend.  The only way currently to instantiate a TdemSystem class is with a file that is read in.
        Therefore, to broadcast the systems, I have to broadcast the file names of the systems and have each worker read in the system file.
        However, if not system is None, I assume that system is a list of TdemSystem classes that already exists on each worker.
        If system is provided, simply assign them when broadcasting the TdemData.

        """

        # Since the Time Domain EM Systems are C++ objects on the back end, I can't Broadcast them through C++ (Currently a C++ Noob)
        # So instead, Broadcast the list of system file names saved in the TdemData Class and read the system files in on each worker.
        # This is cumbersome, but only done once at the beginning of the MPI
        # code.

        if system is None:
            if world.rank == root:
                sfnTmp = [s.filename for s in self.system]
            else:
                sfnTmp = None
            systemFilename = world.bcast(sfnTmp, root=root)
            nSystems = len(systemFilename)

            system = [None] * nSystems
            for i in range(nSystems):
                system[i] = TdemSystem.read(systemFilename[i])

        return system

    def Bcast(self, world, root=0, system=None):
        """Broadcast the TdemData using MPI

        Parameters
        ----------

        """
        out = super().Bcast(world, root)

        out.system = self._BcastSystem(world, root=root, system=system)

        transmitter = CircularLoop()
        # Broadcast the Transmitter Loops.
        for i in range(out.nPoints):
            if (world.rank == 0):
                transmitter = self.transmitter[i]
            out.transmitter[i] = transmitter.Bcast(world, root)


        receiver = CircularLoop()
        # Broadcast the Transmitter Loops.
        for i in range(out.nPoints):
            if (world.rank == 0):
                receiver = self.receiver[i]
            out.receiver[i] = receiver.Bcast(world, root)

        out._primary_field = self.primary_field.Bcast(world, root=root)
        out._secondary_field = self.secondary_field.Bcast(world, root=root)
        out._predicted_primary_field = self.predicted_primary_field.Bcast(world, root=root)
        out._predicted_secondary_field = self.predicted_secondary_field.Bcast(world, root=root)

        return out

    def Scatterv(self, starts, chunks, world, root=0, system=None):
        """ Scatterv the TdemData using MPI """

        out = super().Scatterv(starts, chunks, world, root)

        out.system = self._BcastSystem(world, root=root, system=system)

        # Scatterv the Transmitter Loops.
        lTmp = []
        if (world.rank == 0):
            lTmp = [self.transmitter[i] for i in range(self.nPoints)]

        lTmp = myMPI.Scatterv_list(lTmp, starts, chunks, world)
        for i in range(out.nPoints):
            out.transmitter[i] = lTmp[i]

        # Scatterv the Reciever Loops.
        lTmp = []
        if (world.rank == 0):
            lTmp = [self.receiver[i] for i in range(self.nPoints)]

        lTmp = myMPI.Scatterv_list(lTmp, starts, chunks, world)
        for i in range(out.nPoints):
            out.receiver[i] = lTmp[i]

        out.primary_field = self.primary_field.Scatterv(starts, chunks, world, root=root)
        out.secondary_field = self.secondary_field.Scatterv(starts, chunks, world, root=root)
        out.predicted_primary_field = self.predicted_primary_field.Scatterv(starts, chunks, world, root=root)
        out.predicted_secondary_field = self.predicted_secondary_field.Scatterv(starts, chunks, world, root=root)

        return out


    def write(self, fileNames, std=False, predictedData=False):

        if isinstance(fileNames, str):
            fileNames = [fileNames]

        assert len(fileNames) == self.nSystems, ValueError(
            "fileNames must have length equal to the number of systems {}".format(self.nSystems))

        for i in range(self.nSystems):

            iSys = self._systemIndices(i)
            # Create the header
            header = "Line Fid Easting Northing Elevation Height txrx_dx txrx_dy txrx_dz TxPitch TxRoll TxYaw RxPitch RxRoll RxYaw "

            for x in range(self.nTimes[i]):
                header += "Off[{}] ".format(x)

            d = np.empty(self.nTimes[i])

            if std:
                for x in range(self.nTimes[i]):
                    header += "OffErr[{}] ".format(x)
                s = np.empty(self.nTimes[i])

            with open(fileNames[i], 'w') as f:
                f.write(header+"\n")
                with np.printoptions(formatter={'float': '{: 0.15g}'.format}, suppress=True):
                    for j in range(self.nPoints):

                        x = np.asarray([self.lineNumber[j], self.id[j], self.x[j], self.y[j], self.elevation[j], self.z[j],
                                        self.R[j].x-self.T[j].x, self.R[j].y-self.T[j].y, self.R[j].z-self.T[j].z,
                                        self.T[j].pitch, self.T[j].roll, self.T[j].yaw,
                                        self.R[j].pitch, self.R[j].roll, self.R[j].yaw])

                        if predictedData:
                            d[:] = self.predictedData[j, iSys]
                        else:
                            d[:] = self.data[j, iSys]

                        if std:
                            s[:] = self.std[j, iSys]
                            x = np.hstack([x, d, s])
                        else:
                            x = np.hstack([x, d])

                        y = ""
                        for a in x:
                            y += "{} ".format(a)

                        f.write(y + "\n")
