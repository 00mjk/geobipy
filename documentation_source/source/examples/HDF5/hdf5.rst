
.. DO NOT EDIT.
.. THIS FILE WAS AUTOMATICALLY GENERATED BY SPHINX-GALLERY.
.. TO MAKE CHANGES, EDIT THE SOURCE PYTHON FILE:
.. "examples/HDF5/hdf5.py"
.. LINE NUMBERS ARE GIVEN BELOW.

.. only:: html

    .. note::
        :class: sphx-glr-download-link-note

        Click :ref:`here <sphx_glr_download_examples_HDF5_hdf5.py>`
        to download the full example code

.. rst-class:: sphx-glr-example-title

.. _sphx_glr_examples_HDF5_hdf5.py:


Using HDF5 within GeoBIPy
-----------------------------------------------

Inference for large scale datasets in GeoBIPy is handled using MPI and distributed memory systems.
A common bottleneck with large parallel algorithms is the input output of information to disk.
We use HDF5 to read and write data in order to leverage the parallel capabililties of the HDF5 API.

Each object within GeoBIPy has a create_hdf, write_hdf, and read_hdf routine.

.. GENERATED FROM PYTHON SOURCE LINES 12-16

.. code-block:: default

    import numpy as np
    import h5py
    from geobipy import StatArray


.. GENERATED FROM PYTHON SOURCE LINES 17-19

StatArray
+++++++++

.. GENERATED FROM PYTHON SOURCE LINES 19-34

.. code-block:: default


    # Instantiate a StatArray
    x = StatArray(np.arange(10.0), name = 'an Array', units = 'some units')

    # Write the StatArray to a HDF file.
    with h5py.File("x.h5", 'w') as f:
        x.toHdf(f, "x")

    # Read the StatArray back in.
    with h5py.File("x.h5", 'r') as f:
        y = StatArray.fromHdf(f, 'x')

    print('x', x)
    print('y', y)


.. GENERATED FROM PYTHON SOURCE LINES 35-40

There are actually steps within the "toHdf" function.
First, space is created within the HDF file and second, the data is written to that space
These functions are split because during the execution of a parallel enabled program,
all the space within the HDF file needs to be allocated before we can write to the file
using multiple cores.

.. GENERATED FROM PYTHON SOURCE LINES 40-53

.. code-block:: default


    # Write the StatArray to a HDF file.
    with h5py.File("x.h5", 'w') as f:
        x.createHdf(f, "x")
        x.writeHdf(f, "x")

    # Read the StatArray back in.
    with h5py.File("x.h5", 'r') as f:
        y = StatArray.fromHdf(f, 'x')

    print('x', x)
    print('y', y)


.. GENERATED FROM PYTHON SOURCE LINES 54-58

The create and write HDF methods also allow extra space to be allocated so that
the extra memory can be written later, perhaps by multiple cores.
Here we specify space for 2 arrays, the memory is stored contiguously as a numpy array.
We then write to only the first index.

.. GENERATED FROM PYTHON SOURCE LINES 58-72

.. code-block:: default


    # Write the StatArray to a HDF file.
    with h5py.File("x.h5", 'w') as f:
        x.createHdf(f, "x", nRepeats=2)
        x.writeHdf(f, "x", index=0)

    # Read the StatArray back in.
    with h5py.File("x.h5", 'r') as f:
        y = StatArray.fromHdf(f, 'x', index=0)

    print('x', x)
    print('y', y)



.. GENERATED FROM PYTHON SOURCE LINES 73-74

The duplication can also be a shape.

.. GENERATED FROM PYTHON SOURCE LINES 74-87

.. code-block:: default


    # Write the StatArray to a HDF file.
    with h5py.File("x.h5", 'w') as f:
        x.createHdf(f, "x", nRepeats=(2, 2))
        x.writeHdf(f, "x", index=(0, 0))

    # Read the StatArray back in.
    with h5py.File("x.h5", 'r') as f:
        y = StatArray.fromHdf(f, 'x', index=(0, 0))

    print('x', x)
    print('y', y)


.. GENERATED FROM PYTHON SOURCE LINES 88-89

Similarly, we can duplicate a 2D array with an extra 2D duplication

.. GENERATED FROM PYTHON SOURCE LINES 89-101

.. code-block:: default


    x = StatArray(np.random.randn(2, 2), name = 'an Array', units = 'some units')
    # Write the StatArray to a HDF file.
    with h5py.File("x.h5", 'w') as f:
        x.createHdf(f, "x", nRepeats=(2, 2))
        x.writeHdf(f, "x", index=(0, 0))

    # Read the StatArray back in.
    with h5py.File("x.h5", 'r') as f:
        y = StatArray.fromHdf(f, 'x', index=(0, 0))

    print('x', x)
    print('y', y)

.. rst-class:: sphx-glr-timing

   **Total running time of the script:** ( 0 minutes  0.000 seconds)


.. _sphx_glr_download_examples_HDF5_hdf5.py:


.. only :: html

 .. container:: sphx-glr-footer
    :class: sphx-glr-footer-example



  .. container:: sphx-glr-download sphx-glr-download-python

     :download:`Download Python source code: hdf5.py <hdf5.py>`



  .. container:: sphx-glr-download sphx-glr-download-jupyter

     :download:`Download Jupyter notebook: hdf5.ipynb <hdf5.ipynb>`


.. only:: html

 .. rst-class:: sphx-glr-signature

    `Gallery generated by Sphinx-Gallery <https://sphinx-gallery.github.io>`_
