_das2, libdas2 Python bindings
===============================
Functions in this module provide bindings to the das2C_ library.  Most of
the small server side programs used to reduce streams in time, compute
power spectral densities, read cache blocks are based off of libdas2.  Whenever
possible das2py wraps das2C functionality instead of creating a parallel
code base.

.. contents::

Reading Catalog Files
---------------------
Das2 catalog_ data consists of nodes defined in JSON and XML.  At present only
JSON nodes are parsable by das2C, though support for SPASE_ XML records may
be added in funture versions.  The _das2 module converts catalog data to
python dictionaries.  Higher level pure python code parses these dictionaries
to create catalog objects such as `das2.Collection` and `das2.Catalog`.

.. autofunction:: _das2.get_node

Reading Das2 Streams
--------------------
The C library handles reading parsing stream data into internal arrays that
are passed to NumPy via pointer assignment (not a copy).  At present only
stream in `das2/2.2 format`_ are supported, but other formats such as the HAPI
stream format will be supported as time permits.

.. _Low-level Dataset Output:

Low-level Dataset Output
~~~~~~~~~~~~~~~~~~~~~~~~
The main data reading functions:

  * :py:func:`_das2.read_cmd`
  * :py:func:`_das2.read_file`
  * :py:func:`_das2.read_server`

all return the same, rather complex, output.  Each function returns a python
list containing correlated datasets.  i.e.::

    [ dataset_dict_1, dataset_dict_2, ... ]

The structure and meaning of each dataset is contained in a python dictionary
with the following structure::

	{
	   'id':str,      # An identifier token usable as a C style variable name, no
	                  # spaces or special charaters allowed.

	   'group':str,   # Datasets occupying same kind and number of physical
	                  # dimensions can be part of the same group and should
	                  # usually be plotted together.  This is the group or
	                  # 'join' id.

	   'rank':int,    # Overall number of iteration dimensions for the dataset
	                  # this is it's size in index space (not physical space)

	   'shape':list,  # A list that is *rank* values long.  Provides the overall
	                  # size of the dataset with one value for each iteration
	                  # dimension.

	   'props':dict,  # A dictionary of (type, value) 2-tuples providing any
	                  # properties set on this dataset.

	   'coords':dict, # A dictionary of physical coordinate dimension objects,
	                  # (described below).

	   'data':dict,   # A dictionary of physical data dimension objects,
	                  # (described below).

	   'arrays':dict  # A dictionary of all the backing ndarrays for this dataset.
	}



Each element of the 'coords' and 'data' dicts are also dictionaries.  Each one
of these define a single physical dimension.  The dimension dictionaries
contains the following keys and items::

	{
	   'id':str,     # An identifier token usable as a C style variable name,
	                 # no spaces or special charaters allowed.

	   'type':str,   # The string 'COORD_DIM' or 'DATA_DIM'

	   'props':str,  # A dictionary of (type, value) 2-tuples providing any
	                 # properties set on this dimension.

	   role:dict     # Here *role* is the name of a variable.  There are 1-N
	                 # variables per dimension, each is named by it's role in
	                 # describing values for a given dimension.  Example roles
	                 # are "center", "offset", "reference", "minimum", etc.
	}


Each variable in a dimension is also defined by a dictionary with the following
keys and items:
::
	{
	   'role':str,   # A repeat of this variable's role (i.e. 'center', 'min' etc)

	   'units':str,  # The units string.  Note that date-time values are ususally
	                 # in non-physical units such as t1970, which is the number
	                 # of seconds since midnight, Jan. 1st 1970 ignoring leap
	                 # seconds.

	   'expression':str,  # A summary of how to get values for this variable out
	                      # of the ndarrays.  Used by higher level code to setup
	                      # accessor functions and handle array broadcasts.
	}

The upper level :py:mod:`das2` module converts this low level output into
:py:class:`das2.Dataset`, :py:class:`das2.Dimension`, and
:py:class:`das2.Variable` objects that are easier to work with since all the
array indices have been broadcast to a uniform space.


.. autofunction:: _das2.read_cmd
.. autofunction:: _das2.read_file
.. autofunction:: _das2.read_server

Server Authentication
---------------------
.. autofunction:: _das2.auth_set

Power Spectral Density
----------------------
.. autoclass:: _das2.Dft
.. autoclass:: _das2.Psd

Time Handling
-------------
.. autofunction:: _das2.parsetime
.. autofunction:: _das2.parse_epoch
.. autofunction:: _das2.emitt
.. autofunction:: _das2.ttime
.. autofunction:: _das2.tnorm


.. _SPASE:   http://spase-group.org/
.. _catalog: https://das2.org/catalog
.. _das2C:   https://github.com/das-developers/das2C
.. _das2/2.2 format: https://das2.org/Das2.2.2-ICD_2017-05-09.pdf
