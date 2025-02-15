""" @_userParameters_Class
Parent handler for user defined parameters. Checks that the input user parameters match for a given data point.
This provides a bit more robust checking when the user is new to the codes, and must modify an input parameter class file.
"""
#from ..base import Error as Err
from ..classes.core.myObject import myObject
from copy import deepcopy
from ..classes.core import StatArray
from ..classes.data.dataset.FdemData import FdemData
from ..classes.data.dataset.TdemData import TdemData
from ..classes.data.dataset.TempestData import TempestData
from ..classes.data.datapoint.FdemDataPoint import FdemDataPoint
from ..classes.data.datapoint.TdemDataPoint import TdemDataPoint
from ..classes.data.datapoint.Tempest_datapoint import Tempest_datapoint
# from ..classes.statistics.Hitmap2D import Hitmap2D
import numpy as np
from ..base.utilities import isInt


global_dict = {'FdemData': FdemData,
               'TdemData': TdemData,
               'TempestData':TempestData,
               'FdemDataPoint':FdemDataPoint,
               'TdemDataPoint':TdemDataPoint,
               'TempestDataPoint':Tempest_datapoint}


class user_parameters(dict):
    """ Handler class to user defined parameters. Allows us to check a users input parameters in the backend """

    def __init__(self, **kwargs):

        missing = [ x for x in self.required_keys if not x in kwargs ]
        if len(missing) > 0:
            raise ValueError("Missing {} from the user parameter file".format(missing))

        for key, value in kwargs.items():
            self[key] = value

        self._data_filename = [value] if isinstance(value, str) else value

        self['multiplier'] = kwargs.get('multiplier', np.float64(1.0))
        if self['multiplier'] is None:
            self['multiplier'] = np.float64(1.0)
        
        self['stochastic_newton'] = ~kwargs.get('ignore_likelihood', False)
        self['factor'] = kwargs.get('factor', np.float64(10.0))
        if self['factor'] is None:
            del self['factor']

        # self['prng'] = None

    def __deepcopy__(self, memo={}):
        return deepcopy(self)

    @property
    def required_keys(self):
        return ('data_type',
                'data_filename',
                'system_filename',
                'n_markov_chains',
                'interactive_plot',
                'update_plot_every',
                'save_png',
                'save_hdf5',
                'solve_parameter',
                'solve_gradient',
                'solve_relative_error',
                'solve_additive_error',
                'solve_height',
                'maximum_number_of_layers',
                'minimum_depth',
                'maximum_depth',
                'initial_relative_error',
                'initial_additive_error',
                'probability_of_birth',
                'probability_of_death',
                'probability_of_perturb',
                'probability_of_no_change'
                )

    @classmethod
    def read(cls, filename):
        options = {}
        # Load user parameters
        with open(filename, 'r') as f:
            f = '\n'.join(f.readlines())
            exec(f, global_dict, options)

        return cls(**options)

