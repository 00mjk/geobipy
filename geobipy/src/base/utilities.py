import numpy as np
from copy import deepcopy
from numpy import issubdtype
from math import exp as mExp
from ..classes.core import StatArray
import h5py
from sklearn.mixture import GaussianMixture
from smm import SMM

from numba import (njit, jit, float64)
_jit_settings = {'nopython': True, 'nogil': False, 'fastmath': True, 'cache': True}
_njit_settings = {'nogil': False, 'fastmath': True, 'cache': True}

from numba.pycc import CC

cc = CC('test')
cc.verbose = True
@njit(**_njit_settings)
@cc.export('bresenham', 'f8[:, :](f8[:], f8[:])')
def bresenham(x, y):
    n_segments = np.int32(len(x) - 1)
    nTmp = np.int32(0)
    for i in range(n_segments):
        nx = np.abs(x[i+1] - x[i])
        ny = np.abs(y[i+1] - y[i])
        if nx == 0:
            nx = 1
        if ny == 0:
            ny = 1
        nTmp += nx * ny

    points = np.zeros((2*nTmp, 2), dtype=np.int32)
    j = 0
    for i in range(n_segments):
        # Setup initial conditions
        x1 = x[i] 
        y1 = y[i] 
        x2 = x[i+1] 
        y2 = y[i+1]
        dx = x2 - x1
        dy = y2 - y1

        if dx == 0:
            if y1 > y2:
                y1, y2 = y2, y1
            arr = np.arange(y1, y2+1, dtype=np.int32)
            n = arr.size
            points[j:j+n, 0] = x1
            points[j:j+n, 1] = arr
            j += n

        elif dy == 0:
            if x1 > x2:
                x1, x2 = x2, x1
            arr = np.arange(x1, x2+1, dtype=np.int32)
            n = arr.size
            points[j:j+n, 0] = arr
            points[j:j+n, 1] = y1
            j += n

        if dx != 0 and dy != 0:

            # Determine how steep the line is
            is_steep = np.abs(dy) > np.abs(dx)

            # Rotate line
            if is_steep:
                x1, y1 = y1, x1
                x2, y2 = y2, x2

            # Swap start and end points if necessary and store swap state
            swapped = False
            if x1 > x2:
                x1, x2 = x2, x1
                y1, y2 = y2, y1
                swapped = True

            # Recalculate differentials
            dx = x2 - x1
            dy = y2 - y1

            # Calculate error
            error = np.int32(dx / 2.0)
            ystep = 1 if y1 < y2 else -1

            # Iterate over bounding box generating points between start and end
            iy = y1
            for ix in range(x1, x2 + 1):
                coord = (iy, ix) if is_steep else (ix, iy)
                points[j, :] = coord
                j += 1
                error -= np.abs(dy)
                if error < 0:
                    iy += ystep
                    error += dx

    return points[:j, :]

def interleave(a, b):
        """Interleave two arrays together like zip

        Parameters
        ----------
        a : array_like
            Interleave in [0::2]
        b : array_like
            Interleave in [1::2]

        Returns
        -------
        out : array_like
            Interleaved arrays

        """
        assert a.size == b.size, ValueError("other must have size {}".format(a.size))
        out = np.empty((a.size + b.size), dtype=a.dtype)
        out[0::2] = a
        out[1::2] = b
        return out


def isInt(this):
    """Check whether an entry is a subtype of an int

    Parameters
    ----------
    this : variable
        Variable to check whether an int or not

    Returns
    -------
    out : bool
        Is or is not an int

    """
    return isinstance(this, (int, np.integer))


def isIntorSlice(this):
    """Check whether an entry is a subtype of an int or a slice

    Parameters
    ----------
    this : variable
        Variable to check whether an int/slice or not

    Returns
    -------
    out : bool
        Is or is not an int/slice

    """
    if (isInt(this)):
        return True
    if isinstance(this, slice):
        return True
    return any([isinstance(x,slice) for x in this])


def str_to_raw(s):
    """Helper function for latex

    Parameters
    ----------
    s : str
        String with special latex commands.

    Returns
    -------
    out : str
        String with latex special characters.

    """
    raw_map = {8:r'\b', 7:r'\a', 12:r'\f', 10:r'\n', 13:r'\r', 9:r'\t', 11:r'\v'}
    return r''.join(i if ord(i) > 32 else raw_map.get(ord(i), i) for i in s)


#def is_Numeric(num):
#    """Checks whether num is a number
#
#    Parameters
#    ----------
#    num: str
#        A string that could potentially contain a number
#
#    """
#    try:
#        float(num)
#        return True
#    except ValueError:
#        return False

def findNotNans(this):
    """Find the indicies to non NaN values.

    Parameters
    ----------
    this : array_like
        An array of numbers.

    Returns
    -------
    out : array_like
        Integer array to locations of non nans.

    """
    i = np.isnan(this)
    i ^= True
    return(np.argwhere(i).squeeze())


def findNans(this):
    """Find the indicies to NaN values.

    Parameters
    ----------
    this : array_like
        An array of numbers.

    Returns
    -------
    out : array_like
        Integer array to locations of nans.

    """
    i = np.isnan(this)
    return(np.argwhere(i).squeeze())


def findFirstNonZeros(this, axis, invalid_val=-1):
    """Find the indices to the first non zero values

    Parameters
    ----------
    this : array_like
        An array of numbers
    axis : int
        Axis along which to find first non zeros
    invalid_val : int
        If all values along that axis are zero, use this value

    Returns
    -------
    out : ints
        Indices of the first non zero values.

    """

    mask = this != 0
    return np.where(mask.any(axis=axis), mask.argmax(axis=axis), invalid_val)


def findLastNonZeros(this, axis, invalid_val=-1):
    """Find the indices to the last non zero values

    Parameters
    ----------
    this : array_like
        An array of numbers
    axis : int
        Axis along which to find last non zeros
    invalid_val : int
        If all values along that axis are zero, use this value

    Returns
    -------
    out : ints
        Indices of the last non zero values.

    """

    mask = this != 0
    val = this.shape[axis] - np.flip(mask, axis=axis).argmax(axis=axis) - 1
    return np.where(mask.any(axis=axis), val, invalid_val)


def findFirstLastNotValue(this, values, invalid_val=-1):
    """Find the indices to the first and last non zero values along each axis

    Parameters
    ----------
    this : array_like
        An array of numbers

    Returns
    -------
    out : array_like
        Indices of the first and last non zero values along each axisgg

    """
    values = np.atleast_1d(values)
    out = np.empty([np.ndim(this), 2], dtype=np.int32)
    mask = this != values[0]
    if values.size > 1:
        for i in range(1, values.size):
            mask = mask & (this != values[i])
    for i in range(np.ndim(this)):
        x = np.where(mask.any(axis=i), mask.argmax(axis=i), 1e9)
        out[i, 0] = np.min(x[x != invalid_val])
    for i in range(np.ndim(this)):
        val = this.shape[i] - np.flip(mask, axis=i).argmax(axis=i) - 1
        x = np.where(mask.any(axis=i), val, invalid_val)
        out[i, 1] = np.max(x[x != invalid_val])

    return out


def getName(self, default=''):
    """Tries to obtain an attached name to a variable.

    If the variable is an object with a getName() procedure, that function will take precedence.
    If the variable does not have that procedure, a variable called name will be sought.
    If this fails, the specified default will be returned.

    Parameters
    ----------
    self : any type
        Any type of variable.

    Returns
    -------
    out : str
        A string containing the variable's name or the default.

    """
    if self is None:
        return default
    try:
        if '_name' in self.__dict__:
            return default if self._name is None else self.name
        else:
            return default
    except:
        return getattr(self, '_name', default)


def getUnits(self, default=''):
    """Tries to obtain an attached units to a variable.

    If the variable is an object with a getUnits() procedure, that function will take precedence.
    If the variable does not have that procedure, a variable called units will be sought.
    If this fails, the specified default will be returned.

    Parameters
    ----------
    self : any type
        Any type of variable.

    Returns
    -------
    out : str
        A string containing the variable's units or the default.

    """
    # return getattr(self, '_name', default)

    try:
        if self is None:
            return default
        if '_units' in self.__dict__:
            return default if self._units is None else self.units
        else:
            return default
    except:
        return getattr(self, '_units', default)

def getNameUnits(self, defaultName = '', defaultUnits = ''):
    """Tries to obtain any attached name and units to a variable. Any units are surrounded by round brackets.

    Parameters
    ----------
    self : any type
        Any type of variable.

    Returns
    -------
    out : str
        A string containing the variable's name and units or the defaults.

    """
    tmp = getName(self, defaultName)
    u = getUnits(self, defaultUnits)
    if (not u == ""):
        tmp += " (" + u + ")"
    return (tmp)

def cosSin1(x, y, a, p):
    """Simple function for creating tests. """
    return x * (1.0 - x) * np.cos(a * np.pi * x) * np.sin(a * np.pi * y**p)**p

@njit(**_njit_settings)
def reorder_3d_for_pyvista(values):
    shp = np.shape(values)
    arr = np.zeros(shp[0] * shp[1] * shp[2], dtype=float64)
    ii = 0
    for i in range(shp[0]): #z
        for k in range(shp[2]): #x
            for j in range(shp[1]): #y
                arr[ii] = values[i, j, k]
                ii += 1
    return arr

def rosenbrock(x, y, a, b):
    """ Generates values from the Rosenbrock function. """
    return (a - x**2.0)**2.0 + b * (y - x**2.0)**2.0


def Inv(A):
    """Custom matrix inversion upto 2 dimensions.

    Parameters
    ----------
    A : float or ndarray of floats
        A scalar, 1D array, or 2D array.
        If A is scalar, assume it represents a diagonal matrix with constant value and take the reciprocal.
        If A is 1D, assume it is the diagonal of a matrix: take reciprocal of entries.
        If A is 2D, invert using linalg.

    Returns
    -------
    out : float or ndarray of floats
        The inversion of A.

    """

    ndim = np.ndim(A)

    assert ndim <= 2, TypeError('The number of dimesions of A must be <= 2')

    if (ndim == 2):
        return np.linalg.inv(A)

    return 1.0 / A


def isNumpy(x):
    """Test that the variable is a compatible numpy type with built ins like .ndim

    Parameters
    ----------
    x : anything
        A variable to check

    Returns
    -------
    out : bool
        Whether the variable is a compatible numpy type

    """
    try:
        x.ndim
        return True
    except:
        return False


def Ax(A, x):
    """Custom matrix vector multiplication for different representations of the matrix.

    Parameters
    ----------
    A : float or ndarray of floats
        A scalar, 1D array, or 2D array.
        If A is scalar, assume it represents a diagonal matrix with constant value.
        If A is 1D, assume it represents a diagonal matrix and do an element wise multiply.
        If A is 2D, take the dot product.
    x : numpy.ndarray
        The 1D vector to multiply A with.

    Returns
    -------
    out : ndarray of floats
        Resultant matrix vector multiplication.
    """

    ndim = np.ndim(A)

    assert ndim <= 2, TypeError('The number of dimesions of A must be <= 2')

    if (ndim == 2):
        return np.dot(A, x)

    return A * x


def Det(A, N=1.0):
    """Custom function to compute the determinant of a matrix.

    Parameters
    ----------
    A : float or ndarray of floats
        If A is 2D: Use numpy.linalg.det obtain determinant. Uses LU factorization.
        If A is 1D: Take the cumulative product of the numbers, assumes A represents a diagonal matrix.
        If A is scalar: Take the number to power N, assumes A represents a diagonal matrix with constant value.

    N : int, optional
        If A is a scalar, N is the number of elements in the constant valued diagonal.

    Returns
    -------
    out : float
        The determinant of the matrix.

    """

    ndim = np.ndim(A)
    assert ndim <= 2, TypeError('The number of dimesions of A must be <= 2')

    if (ndim == 0):
        return A**N

    if (ndim == 1):
        return np.prod(A)

    if (ndim == 2):
        return np.linalg.det(A)


def LogDet(A, N=1.0):
    """Custom function to get the natural logarithm of the determinant.

    Parameters
    ----------
    A : float or numpy.ndarray of floats
        If A is 2D: Use linalg.to obtain determinant. Uses LU factorization.
        If A is 1D: Take the cumulative product of the numbers, assumes A represents a diagonal matrix.
        If A is scalar: Take the number to power N, assumes A represents a diagonal matrix with constant value.

    N : int, optional
        If A is a scalar, N is the number of elements in the constant valued diagonal.

    Returns
    -------
    out : float
        The logged determinant of the matrix.

    """

    ndim = np.ndim(A)
    assert ndim <= 2, TypeError('The number of dimesions of A must be <= 2')

    if (ndim == 0):
        return np.log(A**N)

    if (ndim == 1):
        return np.float64(np.linalg.slogdet(np.diag(A))[1])

    if (ndim == 2):
        d = np.linalg.slogdet(A)
        return d[0] * d[1]

@njit(**_njit_settings)
def set_rows_at(values, indices, out):
    for i in range(len(indices)):
        out[indices[i], :] = values[i, :]
    return out

@njit(**_njit_settings)
def set_columns_at(values, indices, out):
    for i in range(len(indices)):
        out[:, indices[i]] = values[:, i]
    return out

def rolling_window(a, window):
    shape = a.shape[:-1] + (a.shape[-1] - window + 1, window)
    strides = a.strides + (a.strides[-1],)
    return np.lib.stride_tricks.as_strided(a, shape=shape, strides=strides)

@njit(**_njit_settings)
def smooth(x, a):
    """Smooth x by an LTI gaussian filter, forwards and backwards pass.

    Parameters
    ----------
    x : array_like
        signal to process
    a : scalar between 0.0 and 1.0
        Weight

    Returns
    -------
    out : array_like
        Smoothed signal
    """
    n = len(x)
    b = 1.0 - a
    sx = 1.0
    sy = a
    yi = 0.0
    y = np.zeros(n)
    yi = (sy * yi) + (sx * x[0])
    y[0] = yi
    for i in range(1, n-1):
        yi = (a * yi) + (b * x[i])
        y[i] = yi

    sx = sx / (1.0 + a)
    sy = sy / (1.0 + a)
    yi = (sy * yi) + (sx * x[n-1])
    y[n-1] = yi
    for i in range(n-2, -1, -1):
        yi = (a * yi) + (b * y[i])
        y[i] = yi
    return y

def splitComplex(this):
    """Splits a vector of complex numbers into a vertical concatenation of the real and imaginary components.

    Parameters
    ----------
    this : numpy.ndarray of complex128
        1D array of complex numbers.

    Returns
    -------
    out : numpy.ndarray of float64
        Vertically concatenated real then imaginary components of this.

    """
    n2 = this.size
    N = 2*n2
    out = np.ndarray(N, dtype=np.float64)
    out[:n2] = np.real(this)
    out[n2:] = np.imag(this)
    return out


def mergeComplex(this):
    """Merge a 1D array containing a vertical concatenation of N real then N imaginary components   into an N/2 complex 1D array.

    Parameters
    ----------
    this : numpy.ndarray of float64
        1D array containing the vertical concatentation of real then imaginary values.

    Returns
    -------
    out : numpy.ndarray of complex128
        The combined real and imaginary components into a complex 1D array.

    """
    N = this.size
    n2 = (N / 2)
    out = np.ndarray(n2, dtype=np.complex128)
    out = this[:n2] + 1j * this[n2:]
    return out


def expReal(this):
    """Custom exponential of a number to allow a large negative exponent, overflow truncates without warning message.

    Parameters
    ----------
    this : float
        Real number to take exponential to.

    Returns
    -------
    out : float
        exp(this).

    """
    # if this < -746.0:
    #     return 0.0

    if this > 709.0:
        return np.inf

    return np.float128(np.exp(this))


def tanh(this):
    """ Custom hyperbolic tangent, return correct overflow. """
#    return np.tanh(this)
    tmp = np.exp(-2.0 * this)
    return (np.divide((1.0 - tmp), (1.0 + tmp)))


def _logLabel(log=None):
    """Returns a LateX string of log_{base} so that auto labeling is easier.

    Parameters
    ----------
    log : 'e' or float, optional
        Take the log of the colour to base 'e' if log = 'e', and a number e.g. log = 10.
        Values in c that are <= 0 are masked.

    Returns
    -------
    out : str
        Label for logged data.

    """

    if log is None:
        return ''

    assert not isinstance(log, bool), TypeError('log must be either "e" or a number')

    if (log == 'e'):
        return 'ln'

    assert log > 0, ValueError('logBase must be a positive number')

    if (log == 10):
        return 'log$_{10}$'

    if (log == 2):
        return 'log$_{2}$'

    if (log > 2):
        return 'log$_{'+str(log)+'}$'

    assert False, ValueError("log must be 'e' or a positive number")


def _log(values, log=None):
    """Take the log of something with the given base.

    Uses mask arrays for robustness and warns when masking occurs
    Also returns a LateX string of log_{base} so that auto labeling is easier.

    Parameters
    ----------
    values : scalar or array_like
        Take the log of these values.
    log : 'e' or float, optional
        Take the log of the colour to base 'e' if log = 'e', and a number e.g. log = 10.
        Values in c that are <= 0 are masked.

    Returns
    -------
    out : array_like
        The logged values

    """

    if np.size(values) == 1:
        return _logScalar(values, log)
    else:
        return _logArray(values, log)



def _logScalar(value, log=None):
    """Take the log of a number with the given base.

    Uses mask arrays for robustness and warns when masking occurs
    Also returns a LateX string of log_{base} so that auto labeling is easier.

    Parameters
    ----------
    values : scalar
        Take the log of the value.
    log : 'e' or float, optional
        Take the log of the colour to base 'e' if log = 'e', and a number e.g. log = 10.
        Values in c that are <= 0 are masked.

    Returns
    -------
    out : array_like
        The logged values

    """
    if log is None:
        return value, ''

    assert not isinstance(log, bool), TypeError('log must be either "e" or a number')

    # Let the user know that values were masked in order to take the log
    if (value <= 0.0):
        print(Warning('Value <= 0.0 have been masked before taking their log'))

    if (log == 'e'):
        tmp = np.log(value)
        label = 'ln'
        return tmp, label

    assert log > 0, ValueError('logBase must be a positive number')

    if (log == 10):
        tmp = np.log10(value)
        label = 'log$_{10}$'
        return tmp, label

    if (log == 2):
        tmp = np.log2(value)
        label = 'log$_{2}$'
        return tmp, label

    if (log > 2):
        tmp = np.log10(value)/np.log10(log)
        label = 'log$_{'+str(log)+'}$'
        return tmp, label

    assert False, ValueError("log must be 'e' or a positive number")


def _logArray(values, log=None):
    """Take the log of an array with the given base.

    Uses mask arrays for robustness and warns when masking occurs
    Also returns a LateX string of log_{base} so that auto labeling is easier.

    Parameters
    ----------
    values : array_like
        Take the log of these values.
    log : 'e' or float, optional
        Take the log of the colour to base 'e' if log = 'e', and a number e.g. log = 10.
        Values in c that are <= 0 are masked.

    Returns
    -------
    out : array_like
        The logged values

    """

    if log is None:
        return values, ''

    assert not isinstance(log, bool), TypeError('log must be either "e" or a number')

    # Let the user know that values were masked in order to take the log
    i = np.s_[:]

    if np.all(np.isnan(values)):
        raise Exception("Entire array is nan")

    if (np.nanmin(values) <= 0.0):
        i = np.where(values > 0.0)
        # print(Warning('Values <= 0.0 have been masked before taking their log'))

    tmp = deepcopy(values)
    tmp[:] = np.nan

    if (log == 'e'):
        tmp[i] = np.log(values[i])
        label = 'ln'
        return tmp, label

    assert log > 0, ValueError('logBase must be a positive number')

    if (log == 10):
        tmp[i] = np.log10(values[i])
        label = 'log$_{10}$'
        return tmp, label

    if (log == 2):
        tmp[i] = np.log2(values[i])
        label = 'log$_{2}$'
        return tmp, label

    if (log > 2):
        tmp[i] = np.log10(values[i])/np.log10(log)
        label = 'log$_{'+str(log)+'}$'
        return tmp, label

    assert False, ValueError("log must be 'e' or a positive number")


def histogramEqualize(values, nBins=256):
    """Equalize the histogram of the values so that all colours have an equal amount

    Parameters
    ----------
    values : array_like
        Values to be equalized.
    nBins : int
        Number of bins to use.

    Returns
    -------
    res : array_like
        Equalized values
    cdf : array_like
        Cumulative Density Function.

    """
    # get image histogram
    tmp = values.flatten()
    i = np.isfinite(tmp)
    flat = tmp[i]
    H, bins = np.histogram(flat, nBins, density=True)
    cdf = H.cumsum() # cumulative distribution function
    cdf = (nBins - 1) * cdf / cdf[-1] # normalize

    # use linear interpolation of cdf to find new pixel values
    equalized = np.interp(tmp, bins[:-1], cdf)
    # Reapply any nans
    equalized[~i] = np.nan
    # Apply any masks from isfinite
    try:
        equalized = np.ma.masked_array(equalized, i.mask)
    except:
        pass

    # Get the centers of the bins
    tmp = bins[:-1] + 0.5 * np.diff(bins)

    # Scale back the equalized image to the bounds of the histogram
    a1 = np.nanmin(equalized)
    a2 = np.nanmax(equalized)
    b1 = tmp.min()
    b2 = tmp.max()

    if a1 == a2:
        return None, None

    # Shifting the vector so that min(x) == 0
    equalized = (equalized - a1) / (a2 - a1)

    # Scaling to the needed amplitude
    equalized = (equalized * (b2 - b1)) + b1

    res = StatArray.StatArray(equalized.reshape(values.shape), getName(values), getUnits(values))

    return res, cdf

def trim_by_percentile(values, percent):
    """Trim an array by a given percentile from either end

    Parameters
    ----------
    values : array_like
        Values to trim
    percent : float
        Percent from 0.0 to 100.0

    Returns
    -------
    out : array_like
        Trimmed values

    """

    low = np.nanpercentile(values, percent)
    high = np.nanpercentile(values, 100 - percent)

    tmp = values.copy()

    i = np.where(tmp > high)
    tmp[i] = high
    i = np.where(tmp < low)
    tmp[i] = low

    return tmp


def _power(values, exponent=None):
    """Take values to a power.

    Uses mask arrays for robustness and warns when masking occurs
    Also returns a LateX string of log_{base} so that auto labeling is easier.

    Parameters
    ----------
    values : scalar or array_like
        Take the log of these values.
    exponent : 'e' or float, optional
        * If exponent = 'e': use np.exp(values)
        * If exponent is float: use np.power(values)

    Returns
    -------
    out : array_like
        The values to power exponent

    """
    if exponent is None:
        return values
    if exponent == 'e':
        return np.exp(values)
    else:
        return np.power(exponent, values)


def safeEval(string):

    # Backwards compatibility
    if ('NdArray' in string):
        string = string.replace('NdArray', 'StatArray')
        return string
    if ('StatArray' in string):
        string = string.replace('StatArray', 'StatArray.StatArray')
        return string
    if ('EmLoop' in string):
        string = string.replace('EmLoop', 'CircularLoop')
        return string

    allowed = (
    'Histogram',
    'Model',
    'Model1D',
    'TempestData',
    'TdemData',
    'FdemData',
    'TdemDataPoint',
    'Tempest_datapoint',
    'FdemDataPoint',
    'TdemSystem',
    'FdemSystem',
    'CircularLoop',
    'CircularLoops',
    'RectilinearMesh')

    if (any(x in string for x in allowed)):
        return string

    raise  ValueError("Problem evaluating string "+string)

def save_gmm(gmm, filename):
    with h5py.File(filename, 'w') as f:
        f.create_dataset('weights', data=gmm.weights_)
        f.create_dataset('means', data=gmm.means_)
        f.create_dataset('covariances', data=gmm.covariances_)

def set_gmm(weights, means, covariances):
    out = GaussianMixture(n_components = len(means), covariance_type='full')
    out.means_ = means
    out.precisions_cholesky_ = np.linalg.cholesky(np.linalg.inv(covariances))
    out.weights_ = weights
    out.covariances_ = covariances
    return out

def load_gmm(filename, sort_by_means=True):
    with h5py.File(filename, 'r') as f:
        weights = np.asarray(f['weights'])
        means = np.asarray(f['means'])
        covariances = np.asarray(f['covariances'])

    if sort_by_means:
        order = np.argsort(means[:, 0])
        weights = weights[order]
        means = means[order, :]
        covariances = covariances[order, :, :]

    return set_gmm(weights, means, covariances)

def save_smm(gmm, filename):
    with h5py.File(filename, 'w') as f:
        f.create_dataset('weights', data=gmm.weights_)
        f.create_dataset('means', data=gmm.means_)
        f.create_dataset('covariances', data=gmm.covars_)
        f.create_dataset('degrees', data=gmm.degrees_)

def set_smm(weights, means, covariances, degrees):
    out = SMM(n_components = len(means))
    out.means_ = means
    out.weights_ = weights
    out.covars_ = covariances
    out.degrees_ = degrees
    return out

def load_smm(filename, sort_by_means=True):
    with h5py.File(filename, 'r') as f:
        weights = np.asarray(f['weights'])
        means = np.asarray(f['means'])
        covariances = np.asarray(f['covariances'])
        degrees = np.asarray(f['degrees'])

    if sort_by_means:
        order = np.argsort(means[:, 0])
        weights = weights[order]
        means = means[order, :]
        covariances = covariances[order, :, :]
        degrees = degrees[order]

    return set_smm(weights, means, covariances, degrees)

def reslice(slic, start=None, stop=None, step=None):
    if all(x is None for x in [start, stop, step]):
        return slic
    
    sta = slic.start
    if start is not None:
        if slic.start is not None:
            sta = slic.start + start
        else:
            sta = start

    stp = slic.stop
    if stop is not None:
        if slic.stop is not None:
            stp = slic.stop + stop
        else:
            stp = stop
        
    ic = slic.step if step is not None else step
    
    return slice(sta, stp, ic)