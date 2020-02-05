Welcome to GeoBIPy: Geophysical Bayesian Inference in Python
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Citation:

Foks, N. L., and Minsley, B. J. 2020. Geophysical Bayesian Inference in Python (GeoBIPy). 10.5066/P9K3YH9O

Background scientific references
::::::::::::::::::::::::::::::::

Minsley, B. J. 2011. A trans-dimensional Bayesian Markov chain Monte Carlo algorithm for model assessment using frequency-domain electromagnetic data. Geophys. J. Int. 187, 252–272. 10.1111/j.1365-246X.2011.05165.x

`Documentation is here! <https://usgs.github.io/geobipy/>`_

This package uses a Bayesian formulation and Markov chain Monte Carlo sampling methods to 
derive posterior distributions of subsurface and measured data properties. 
The current implementation is applied to time and frequency domain electro-magnetic data. 
Application outside of these data types is well within scope.

Currently there are two types of data that we have implemented; frequency domain electromagnetic data, 
and time domain electromagnetic data. 
The package comes with a frequency domain forward modeller, but it does not come with a time domain forward modeller.  
See the section :ref:`Installing_time_domain_forward_modeller` for more information.


Using GeoBIPy on Yeti
:::::::::::::::::::::::::::
There is no need to install GeoBIPy on Yeti.  Simply type "module load python/geobipy" for the serial version of the code, mainly used for plotting results, or "module load python/pGeobipy" for a parallel enabled version.
