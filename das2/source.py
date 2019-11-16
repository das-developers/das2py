# -*- coding: utf-8 -*-

# The MIT License
#
# Copyright 2019 Chris Piker
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell 
# copies of the Software, and to permit persons to whom the Software is 
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in 
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


"""This module provides functions for interacting with data sources and
the streams they emit.
"""
import sys
import json
import _das2
from . dastime import DasTime
from . node import Node
from . dataset import *
from . util import *

# Modules that moved from python2 to python3
try:
	from urllib import quote_plus
except ImportError:
	from urllib.parse import quote_plus

# Get a string type that is consistant across python 2 and 3
try:
	basestring
except NameError:
	basestring = str


perr = sys.stderr.write

# ########################################################################### #
class Source(Node):
	"""This class exists to define the interface for Source objects and to
	hook into to the 2-phase node construction mechanisim.
	"""

	def __init__(self, dDef, bStub, bGlobal):
		super(Source, self).__init__(dDef, bStub, bGlobal)

	def examples(self):
		"""Return a list of named examples.

		Every data source is required to provide at least one example dataset,
		for testing and evaluation purposes.

		Returns:
			A dictionary of example IDs and descriptions.

		note: 
		   The keys in the return dictionary can be supplied to :meth:`~get`
		   to retrieve the name example dataset.

		"""
		raise NotImplementedError("Derived class needs to implement example()")

	def protoGet(self, dConfig, verbose=False):
		raise NotImplementedError("Derived class needs to implement protoGet()")

	def protoInfo(self):
		raise NotImplementedError("Derived class needs to implement protoInfo()")

	def get(self, where=None, verbose=False):
		"""Get data from a Source.
	
	To get the list of examples by name for this data source use the 
	function :meth:`~examples`.  In addition to the queries defined below
	example names as return from :meth:`~get` can be used as the where 
	argument.  For example::
	   
	   source = das2.get_source('site:/uiowa/mars_express/marsis/spectrogram/das2')
	   examples = src.examples()
	   datasets = src.get(examples[0][0])

	For general purpose data queries supply a dictionary with the following
	form::
	
	   query = {
	      'coord':{
	         'VARIABLE_NAME':{
	            'ASPECT_NAME':ASPECT_VALUE,
	            ...
	         },
	         ...
	      }
	      'data':{
	         'VARIABLE_NAME':{
	            'ASPECT_NAME':ASPECT_VALUE,
	            ...
	         },
	         ...
	      }
	      'option':{
	         OPTION_NAME':OPTION_VALUE,
	         ...
	      }
	   })
	   source.get(query)
	
	Where unneeded sections are omitted.
	
	For example a simple query by start and stop type of a data source
	would be::
	   
	   query = {'coord':{'time':{'minimum':'2017-01-01', 'maximum':'2017-01-02'}}}
	   source.get(query)

	Gathering data in the default time range with a hypothetical filter named
	'no_spikes' for a data variable named 'electric' would be::
      
	   query = {'data':{'electric':{'no_spikes':True}}}
	   source.get(query)

	The following example sets the time range and turns on the 'no_spikes'
	filter::
	
	   query = {
	      'coord':{'time':{'minimum':'2017-01-01', 'maximum':'2017-01-02'}},
	      'data':{'electric':{'no_spikes':True}}
	   }
	   source.get(query)
	
	ShortCuts:
	   As a convienience, query dictionary keys and values can be 
	   under-specified as long as the intent is clear.
	   
	   * If a data, coordinate or general option name is unique within
	     data source definition, then the section qualifiers 'coord',
	     'data', and 'option' may be omitted.  The combined query 
	     dictionary above could thus be shortend to::
	        
	        query = {
	           'time':{'minimum':'2017-01-01', 'maximum':'2017-01-02'},
	           'electric':{'rm_spikes':True}
	        }
	        source.get(query)
	   
	   * Coordinate subset dictionaries may replaced by a tuple.
	     The members of the tuple will be taken to provide the: minimum,
	     maximum, and resolution in that order.  The value None can be used
	     skip a spot and the tuple need not be three elements long.  In
	     combination with the shortcut above, the query could be given
	     as::
		     
	        query = {'time':('2017-01-01', '2017-01-02'), 'electric':{'rm_spikes':True}}
	        source.get(query)
	        	   
	   * Boolean options can be set to True just by providing thier name
	     alone in a list::
		  
	        query = {'time':('2017-01-01', '2017-01-02'), 'electric':['rm_spikes']}
	        source.get(query)
	   
	   * And the list can be omitted if it contains only a single
	     item::
		  
	        query = {'time':('2017-01-01', '2017-01-02'), 'electric':'rm_spikes'}
	        source.get(query)
	   
	   * Finally Variables with the 'enabled' aspect may have thier
	     enabled state changed by using True or False in the place of the
	     entire aspect dictionary.  For example assume a source that can
	     output both a 'magnetic' and 'electric' data variables.  The
	     following query dictionary would enable output of 'electric' data
	     but not 'magnetic'::
		  
	        source.get({ 'magnetic':False, 'electric':True})

	Args:
	   where (str, dict, None) : Either the name of a predefined example,
	      a query dictionary, or None to indicate download of the
	      default example dataset.

	Returns:
	   List of :class:`.Dataset` objects.
	"""
		raise NotImplementedError("Derived class needs to implement get()")

	def params(self):
		"""Get a standardized dictionary describing how to query a data source.

		Each data collection in das2 defines one or more named coordinate
		variables and zero or more named data variables in those coordinates.
		For example a magnetometer collection could be defined as:

			- Time  (coordinate variable)
			- Payload_X_Magnitude  (data variable)
			- Payload_Y_Magnitude  (data variable)
			- Payload_Z_Magnitude  (data variable)

		In order to get data, Collections contain one or more data Sources
		which can be used to obtain values from the collection.  Most data
		Sources are controllable.  This function provides the control parameters
		for a data source.

		There are three sections in the Source JSON (or XML) definition that can
		define control paramaters:

		- **coord** Each sub-item in this key corresponds to a single
		  coordinate variable for the dataset.  Each variable can have one
		  or more aspects that are settable.

		- **data** Simiar to the coordinates section, except each item here
		  represets a single data variable for the overall dataset.
		  Data variables are the items measured by an instrument or the
		  values computed by a model.

		- **options** This section contains extra options for the data source
		  that are not directly associated with any particular data or
		  coordinate variable.  Items such as the output format appear
		  here.

		Each settable aspect of a variable, or settable option contains the
		sub-key 'set'.  If this sub-key is not present the aspect is not settable
		and will not appear in the query dictionary ouput by this function. 
		Though nearly any non-whitespace string can be used to name a variable
		aspect or general option, certian aspect names have a special meaning
		and may receive special handling in end user code.  Special aspect
		names are listed below:

		- **mimimum** Used to state the smallest desired value of a Variable.
		  Typically available as a settable coordinate variable aspect.

		- **maximum** Used to state the largest desired value.  Typically
		  available as a settable coordinate variable aspect.

		- **resolution** Used to state with of desired average value bins,
		  typically as a settable coordinate variable aspect.

		- **units** Used to state the desired physical units for output values.
		  This is typically available as a settable data Variable aspect.

		- **enabled** Use toggle the output state of a variable, typically
		  encountered with data variables.

		Other settable aspect are often available as well, though no attempt has
		been made to standardize thier names.  The following example output for
		the Voyager PWS Spectrum Analyzer data source demonstrates both common
		and customized variable aspects::

		  {
		    'coordinates':{
		      'time'{
		        'minimum':{
		          'name':'Min Time',
		          'title':'Minimum Time Value to stream',
		          'default':'2014-08-31',
		          'type':'isotime',
		          'range': ['1977-08-20','2019-03-01']
		        },
		        'maximum':{
		          'name':'Min Time',
		          'title':'Minimum Time Value to stream',
		          'default':'2014-09-01',
		          'type':'isotime',
		          'range': ['1977-08-20','2019-03-01']
		        },
		        'resolution':{
		          'name':'Time Bin Size',
		          'title':'Maximum width of output time bins, use 0.0 for intrinsic values',
		          'default':0.0,
		          'type':'real'
		        }
		      }
		    },
		    'data':{
		      'efield':{
		        'units':{
		           'name':'Calibration Units',
		           'title':'Set the calibration table, 'raw' means no calibration',
		           'default': 'V m**-1',
		           'type':'string',
		           'enum':['V m**-1, 'raw', 'V**2 m**-2 Hz**-1', 'W m**-2 Hz**-1']
		         }
		         'negative':{
		           'name':'Keep Negative',
		           'title':'Negative values are used as a noise flag. Use this option to keep them.',
		           'default':False,
		           'type':'boolean',
		           'enum':[True, False],
		         },
		         'channel':{
		           'name':'SA Channel'
		           'title':'Spectrum anaylzer channel to output, 'all' outputs 16 channels',
		           'default':'all',
		           'enum':['all',
		             '10.0Hz','17.8Hz','31.1Hz','56.2Hz','100Hz','178Hz','311Hz','562Hz',
		             '1.00kHz','1.78kHz','3.11kHz','5.62kHz','10.0kHz','17.8kHz','31.1kHz','56.2kHz'
		           ]
		         }
		       }
		    },
		    'option':{
		      'text':{
		        'name':'Text',
		        'title':'Ensure output stream is formatted as UTF-8 text',
		        'default':False,
		        'enum':[True, False]
		      }
		    }
		  }

		See :meth:`~get`
		"""
		raise NotImplementedError("Derived class needs to implement params()")

	def info(self):
		"""Get a pretty-print string of query options for a data Source.
		"""
		raise NotImplementedError("Derived class needs to implement info()")





