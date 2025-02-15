"""
2D Posterior analysis of the Bayesian inference
-----------------------------------------------

All plotting in GeoBIPy can be carried out using the 3D inference class

"""
#%%
import matplotlib.pyplot as plt
from geobipy import Inference2D
import numpy as np


#%%
# Inference for a line of inferences
# ++++++++++++++++++++++++++++++++++
#
# We can instantiate the inference handler by providing a path to the directory containing
# HDF5 files generated by GeoBIPy.
#
# The InfereceXD classes are low memory.  They only read information from the HDF5 files
# as and when it is needed.
#
# The first time you use these classes to create plots, expect long initial processing times.
# I precompute expensive properties and store them in the HDF5 files for later use.

################################################################################
results_2d = Inference2D(hdf5_file_path='../../supplementary/inversions/10010.0.h5', 
                         system_file_path="../../Data")

################################################################################
# Plot a location map of the data point locations along the line
plt.figure()
results_2d.scatter2D()

################################################################################
# Before we start plotting cross sections, lets set some common keywords
xAxis = 'x'
kwargs = { 
           "reciprocateParameter" : True, # Plot resistivity instead?
        #    "vmin" : 1.0, # Set the minimum colour bar range in log space
        #    "vmax" : np.log10(500.0), # Set the maximum colour bar range in log space
           "log" : 10, # I want to plot the log conductivity
           "xAxis" : xAxis, # Set the axis along which to display attributes
        #    "equalize" : True
           }
# sphinx_gallery_thumbnail_number = 2

################################################################################
# We can show a basic cross-section of the parameter inverted for
# plt.figure()
# plt.subplot(311)
# results_2d.plotMeanModel(**kwargs);
# results_2d.plotDataElevation(linewidth=0.3, xAxis=xAxis);
# results_2d.plotElevation(linewidth=0.3, xAxis=xAxis);

# # By adding the useVariance keyword, we can make regions of lower confidence more transparent
# plt.subplot(312)
# results_2d.plotMeanModel(useVariance=True, **kwargs);
# results_2d.plotDataElevation(linewidth=0.3, xAxis=xAxis);
# results_2d.plotElevation(linewidth=0.3, xAxis=xAxis);

# # We can also choose to keep parameters above the DOI opaque.
# plt.subplot(313)
# results_2d.plotMeanModel(useVariance=True, only_below_doi=True, **kwargs);
# results_2d.plotDataElevation(linewidth=0.3, xAxis=xAxis);
# results_2d.plotElevation(linewidth=0.3, xAxis=xAxis);

# ################################################################################
# # We can plot the parameter values that produced the highest posterior
# plt.figure()
# plt.subplot(311)
# results_2d.plotBestModel(**kwargs);
# results_2d.plotDataElevation(linewidth=0.3, xAxis=xAxis);
# results_2d.plotElevation(linewidth=0.3, xAxis=xAxis);
# plt.ylim([900.0, 1400.0]);

# # By adding the useVariance keyword, we can shade regions of lower confidence
# plt.subplot(312)
# results_2d.plotBestModel(useVariance=True, **kwargs);
# results_2d.plotDataElevation(linewidth=0.3, xAxis=xAxis);
# results_2d.plotElevation(linewidth=0.3, xAxis=xAxis);
# plt.ylim([900.0, 1400.0]);

# # We can also choose to keep parameters above the DOI opaque.
# plt.subplot(313)
# results_2d.plotBestModel(useVariance=True, only_below_doi=True, **kwargs);
# results_2d.plotDataElevation(linewidth=0.3, xAxis=xAxis);
# results_2d.plotElevation(linewidth=0.3, xAxis=xAxis);
# plt.ylim([900.0, 1400.0]);

################################################################################
# Now we can start plotting some more interesting posterior properties.
# How about the confidence?
# plt.figure(figsize=(12, 4))
# results_2d.plotConfidence(xAxis=xAxis);
# results_2d.plotDataElevation(linewidth=0.3, xAxis=xAxis);
# results_2d.plotElevation(linewidth=0.3, xAxis=xAxis);

################################################################################
# We can take the interface depth posterior for each data point,
# and display an interface probability cross section
# This posterior can be washed out, so the clim_scaling keyword lets me saturate
# the top and bottom 0.5% of the colour range
plt.figure(figsize=(12, 4))
results_2d.plotInterfaces(xAxis=xAxis, cmap='Greys', clim_scaling=0.5);
results_2d.plotDataElevation(linewidth=0.3, xAxis=xAxis);
results_2d.plotElevation(linewidth=0.3, xAxis=xAxis);

################################################################################
# We can plot the posteriors along the line as a shaded histogram

# results_2d.nLayers


################################################################################

################################################################################

plt.show()