_das3, libdas2 Python bindings
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
be added in funture versions.  The _das3 module converts catalog data to
python dictionaries.  Higher level pure python code parses these dictionaries
to create catalog objects such as `das3.Collection` and `das3.Catalog`.

.. autofunction:: _das3.get_node

Reading Das Streams
-------------------
The C library parses stream data into internal arrays that are handed to
NumPy by pointer assignment, not by copy.  Both das2.2 and das3 streams are
read; a das3 stream may carry composite values (vectors, matrices, complex
pairs) and sequences, and both come through here.

.. _Low-level Dataset Output:

Low-level Dataset Output
~~~~~~~~~~~~~~~~~~~~~~~~
The main data reading functions:

  * :py:func:`_das3.read_cmd`
  * :py:func:`_das3.read_file`
  * :py:func:`_das3.read_server`

all return the same, rather complex, output: a 2-tuple of a stream header
dictionary and a list of correlated datasets::

    (header_dict, [ dataset_dict_1, dataset_dict_2, ... ])

The header dictionary has two keys, ``'props'``, the stream level properties
as (type, value) tuples, and ``'info'``, a summary string.

Each dataset is a dictionary with the following structure::

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

	   'arrays':dict, # A dictionary of all the backing ndarrays for this dataset,
	                  # keyed by array id.  A sequence or constant variable is
	                  # computed into an array named DIMENSION.ROLE.

	   'fill':dict,   # The fill value for each array, same keys as 'arrays'.

	   'info':str     # A summary of the dataset, as das2C prints it.
	}

Each element of the 'coords' and 'data' dicts is also a dictionary.  Each one
defines a single physical dimension and contains the following keys::

	{
	   'type':str,   # The string 'COORD_DIM' or 'DATA_DIM'

	   'props':dict, # A dictionary of (type, value) 2-tuples providing any
	                 # properties set on this dimension.

	   role:dict     # Here *role* is the name of a variable.  There are 1-N
	                 # variables per dimension, each is named by it's role in
	                 # describing values for a given dimension.  Example roles
	                 # are "center", "offset", "reference", "minimum", etc.
	}

Each variable in a dimension is defined by a dictionary with the following
keys::

	{
	   'role':str,     # A repeat of this variable's role (i.e. 'center', 'min' etc)

	   'units':str,    # The units string.  Date-time values are always given in
	                   # 'ns1970', nanoseconds since 1970-01-01 ignoring leap
	                   # seconds, and time offsets in 'ns', to match the numpy
	                   # datetime64 and timedelta64 arrays that hold them.

	   'valtype':str,  # The das2C value type name ('double', 'das_time',
	                   # 'composite', ...)

	   'expression':str, # A description of the variable for people.  Nothing
	                   # in das2py parses it.

	   'array':str,    # The key in 'arrays' of the ndarray backing this variable.
	                   # None for reference + offset, which the higher level
	                   # Dimension derives itself.

	   'idxmap':list,  # One entry per dataset index: the array index it maps
	                   # to, or None where this variable does not vary.  None
	                   # as a whole when 'array' is None.

	   'ops':dict,     # None, or the <ops> formalism: 'kind' plus each
	                   # parameter under its wire attribute name (frame, body,
	                   # fixed, system, sysorder, surface, from, to).  An
	                   # unknown kind arrives with its parameters verbatim.

	   'intern':list,  # The internal shape of one value, [] for a scalar, [3]
	                   # for a vector, [3, 3] for a matrix.  These indices trail
	                   # the dataset indices in the array.  None marks a ragged
	                   # level such as a variable length string.

	   'labels':list   # One label per component in storage order, or one
	                   # label for a scalar.  Same preference order as das3_cdf.
	}

The upper level :py:mod:`das3` module converts this low level output into
:py:class:`das3.Dataset`, :py:class:`das3.Dimension`, and
:py:class:`das3.Variable` objects that are easier to work with since all the
array indices have been broadcast to a uniform space.  Composite values keep
their internal shape trailing the dataset shape there; see
:py:meth:`das3.Variable.intrShape`.


.. autofunction:: _das3.read_cmd
.. autofunction:: _das3.read_file
.. autofunction:: _das3.read_server

Server Authentication
---------------------
.. autofunction:: _das3.auth_set

Power Spectral Density
----------------------
.. autoclass:: _das3.Dft
.. autoclass:: _das3.Psd

Time Handling
-------------
.. autofunction:: _das3.parsetime
.. autofunction:: _das3.parse_epoch
.. autofunction:: _das3.emitt
.. autofunction:: _das3.ttime
.. autofunction:: _das3.tnorm


.. _SPASE:   http://spase-group.org/
.. _catalog: https://das2.org/catalog
.. _das2C:   https://github.com/das-developers/das2C
.. _das2/2.2 format: https://das2.org/Das2.2.2-ICD_2017-05-09.pdf
