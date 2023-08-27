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


FILL = -1.0e+31

__version__ = '2.3.1'

import sys
import _das2
from _das2 import Psd as PSD
from das2.dastime   import *
from das2.source    import *
from das2.streamsrc import * 
from das2.container import *
from das2.dataset   import *
from das2.auth      import *
from das2.util      import *
from das2.reader    import *

# Pull up a function or two from the C module:
from _das2 import convert
from _das2 import convertible
from _das2 import parse_epoch as from_epoch;
from _das2 import to_epoch;

import das2.toml as toml
import das2.pkt as pkt
import das2.cli as cli

# ########################################################################### #
# The basic data reading functions

def read_cmd(sCmd):
	"""Run a das2 reader command line and output a list of das2 datasets

	Args:
		sCmd (str) : The command line to run in a subshell, may contain
			pipes and other borne shell (posix) or cmd shell (windows)
			constructs.  It is the callers responsibility to check for dangerous
			shell escapes.

	Returns: list
		A list of Dataset objects created from the message body, or None if
		in error occured.  The return datasets may or may not have data depending
		on if data packetes were part of the response.

	"""

	try:
		lDs = _das2.read_cmd(sCmd)
	except Exception as e:
		sys.stderr.write("Error running '%s': %s\n"%(sCmd, str(e)))
		return None

	if lDs != None:
		lOut = []
		for ds in lDs:
			lOut.append(ds_from_raw(ds))
		return lOut

	raise _das2.Error("Unable to retrieve data using %s"%sUrl)



def read_file(sFileName):
	"""Read datasets from a file

	Args:
		sFileName (str) : the name of the file to read

	Returns: list
		A list of Dataset objects created from the message body, or None if
		in error occured.  The return datasets may or may not have data depending
		on if data packetes were part of the response.
	"""

	try:
		lDs = _das2.read_file(sFileName)
	except Exception as e:
		sys.stderr.write("Error running '%s': %s\n"%(sFileName, str(e)))
		return None

	if lDs != None:
		lOut = []
		for ds in lDs:
			lOut.append(ds_from_raw(ds))
		return lOut

	raise _das2.Error("Unable to retrieve data using %s"%sUrl)


def read_http(sUrl, rTimeOut=3.0, sAgent=None):
	"""Issue an HTTP GET command to a remote server and output a list of
	datasets.

	To prevent this function from prompting for authentication on the standard
	input terminal, you can use the das2.set_auth() or das2.load_auth()
	functions before calling das2.read_http().

	Args:
		sUrl (str) : The URL, with all GET parameters if necssary to use to
			contact the server.  Must start with either 'http' or 'https'.

		rTimeOut (float) : The maximum amount of time to wait in seconds for the
			TCP/IP connection to be established.  A value of 0.0 will wait until
			the operating system itself gives up, typically over five minutes.
			This value only specifies a maximum wait for the initial connection,
			actual data download times are not limited by this library.

		sAgent (str, options) : The user-agent string to set in the HTTP/HTTPs
			header.  If not specified a default string will be sent.

	Returns: list
		A list of Dataset objects created from the message body, or None if
		in error occured.  The return datasets may or may not have data depending
		on if data packetes were part of the response.
	"""

	try:
		if sAgent:
			lDs = _das2.read_server(sUrl, rTimeOut, sAgent)
		else:
			lDs = _das2.read_server(sUrl, rTimeOut)
	except Exception as e:
		sys.stderr.write("Error retrieving '%s': %s\n"%(sUrl, str(e)))
		return None

	if lDs != None:
		lOut = []
		for ds in lDs:
			lOut.append(ds_from_raw(ds))
		return lOut

	raise _das2.Error("Unable to retrieve data using %s"%sUrl)


g_sDefDas2SrcTag = 'tag:das2.org,2012:'

# ########################################################################### #
#
# Catalog Classes:
#                     Node
#                      |
#          +-----------+-----------------+
#          |                             |
#        Source                       Catalog
#          |                             |
#      +-----------+             +--------+----------+
#      |           |             |        |          |
# HttpStreamSrc  FileAggSrc  SpaseCat  DasCat   Collection
#

def get_node(sPathId, sUrl=None):
	"""Read a single das2 catalog node from a local or remote file.

	Args:
		sPathId (str) : A string providing the catalog Path ID for the object to
			load.  Since the das2 root node at 'tag:das2.org,2012: contains the
			most commonly loaded item, any sPathId starting with 'site:/' or
			'test:/' is assumed to sub item of the das2 root node.

		.. note: This value is required even if an explicit URL is provided
			because much like files on a disk, das2 catalog objects do not embbed
			the name of node within the contents of the node.

		sUrl (str, optional) : A string providing a direct load URL.
			URLs must start with one of 'file://', 'http://', or 'https://'.

	Returns:
		Either a das2.Catalog, das2.Collection or das2.HttpStreamSrc
		object depending on the contents of the file.  If the file does not
		describe one of these object types or can't be read then None is
		returned.

	Examples:

		Load an http stream source for a das2 Voyager dataset:

			>>> src = get_node('site:/uiowa/voyager/1/pws/uncalibrated/waveform/das2')
			>>> print(src.__class__.__name__)
			HttpStreamSrc

		Load the catalog of das2 production sites:

			>>> cat = get_node('site:/uiowa')
			>>> print(cat.__class__.__name__)
			Catalog

		Load the same item as above but provide the full catalog path URI:

			>>> cat = get_node('tag:das2.org,2012:site:/uiowa')

		Load a SPASE record for the JAXA  listing

			>>> rec = get_node('tag:spase-group.org,2018:spase://GBO')
			>>> print(cat.__class__.__name__)
			SpaseRecord

		Load a data source definition from a local file:

			>>> src = get_node('tag:place.org:2019:/hidden/my_source',
			                   'file:///home/person/my_source.json')

		Load a dataset collection from a specific remote URL:

		   >>> cat = get_node('tag:place.org:2019:/hidden/my_source',
			                   'http://place.org/catalog/my_source.json')
	"""

	if sPathId and (sPathId.startswith("site:") or sPathId.startswith('test:')):
		sPathId = g_sDefDas2SrcTag + sPathId

	bGlobal = None
	if sUrl:
		# Here a new root is created, but the pointer to that root is lost!
		# (don't worry there's not a memory leak the C-bindings delete the node)
		#
		# Because of this we loose the C-code's caching ability for detached
		# roots.  For now I don't want to have to create any python objects that
		# hold the pointer for the underlying C node object, but maybe I should
		# do so because this would have the knock on effect of allowing for
		# multi-threaded catalog operations.
		#
		# For now sub items of a detached root will just have to be made by
		# walking the 'urls' key.  This triggers a split in the creation mode
		# for sub items of a catalog.  Children of the actual root can be made
		# using 'path' URIs, but children of detached roots have to do thier own
		# lookup via the 'urls' list.
		#
		# The result is sub-optimal and should be updated if time permits by
		# creating a C pyNode object.

		dDef = _das2.get_node(sPathId, None, sUrl)
		bGlobal = DETACHED
	else:
		dDef = _das2.get_node(sPathId)
		bGlobal = GLOBAL

	if dDef == None: return None

	if dDef['_url'] != None: sUrl = dDef['_url']

	# Insure that sPathId has been saved in the _path item
	if sPathId == None: sPathId = ''

	if dDef['_path'] != sPathId:
		raise AssertionError("Item ID changed during C-code call")

	# Factory time:
	if dDef['type'] == 'Catalog':       return Catalog(dDef, 'catalog', FULL, bGlobal)
	if dDef['type'] == 'HttpStreamSrc': return HttpStreamSrc(dDef, FULL, bGlobal)
	if dDef['type'] == 'Collection':    return Collection(dDef, FULL, bGlobal)
	if dDef['type'] == 'FileAggSrc':    return FileAggSrc(dDef, FULL, bGlobal)

	raise CatalogError("Data type '%s' of node from '%s' is unknown"%(
	                    dDef['type'], sUrl))

# ########################################################################### #
def get_source(sPathId, sUrl=None):
	"""Read a single data source definition from a local or remote files.

	This function is essentially a wrapper around get_node() that makes sure
	the returned object has the get() method.

	Args:
		sPathId (str) : Provides the catalog Path ID for the object to load
		   Since the das2 root node at 'tag:das2.org,2012: contains the
			most commonly loaded item, any sPathId starting with 'site:/' or
			'test:/' is assumed to sub item of the das2 root node.

			Note: This value is required even if an explicit URL is provided
		      because much like files on a disk, das2 catalog objects do not
			   embed the name of node within the contents of the node.

		sUrl (str,optional) : A string providing a direct load URL.
		   URLs must start with one of 'file://', 'http://', or 'https://'.

	Returns:
		Node: Either a HttpStreamSrc or FileAggSrc object is returned depending
		on the contents of the file.

	Raises:
		CatalogError : If the file does not describe one of these object types.
		_das2.error : If a low-level read error occurs.

	"""

	node = get_node(sPathId, sUrl)
	if node.__class__.__name__ not in ('Collection','HttpStreamSrc','FileAggSrc'):
		raise CatalogError("Node type '%s' from '%s' is not a data source object"%(
		                   node.__class__.__name__, node['_url']))
	return node

# ########################################################################### #
def get_catalog(sPathId=None, sUrl=None):
	"""Read a single directory definition from a local or remote file.

	This function is essentially a wrapper around get_node() that makes sure
	the returned object has the sub() method.

	Args: 
		sPathId (str, optional): A string providing the catalog Path ID for
			the object to load.  Since the das2 root node at 'tag:das2.org,2012:'
			contains the most commonly loaded items, any sPathId starting with
			'site:/' or 'test:/' is assumed to sub item of the das2 root node.

		sUrl (str,optional): A string providing a direct load URL.
			URLs must start with one of 'file://', 'http://', or 'https://'.

	Returs: Either a Catalog or Collection object is returned depending
		   on the contents of the file.

	Raises: 
		CatalogError: If the file does not describe one of these object types.
		_das2.error: If a low-level read error occurs.
	"""
	
	node = get_node(sPathId, sUrl)
	if node.__class__.__name__ not in ('Catalog','Collection'):
		raise CatalogError("Node type '%s' from '%s' is not a data source object"%(
		                   node.__class__.__name__, node['_url']))

	return node
	
# ########################################################################### #
#
# Need to think this through, I don't like the implication that sampling a 
# signal for different sampling periods (all above the Nyquist) produces
# different spectral densities
#
#def psd_units(time, amp):
#	"""Calculate Power Spectral Density units
#	
#	Args:
#		time (Variable, str) : The time variable used in the calculation or just
#			a units string for the sample period.
#		amp  (Variable, str) : The amplitude variable over which the power spectral
#			density was calculated or just the amplitude units string.
#	
#	Returns:
#		str : The units of a power spectral density calculation which are
#		   amp**2 / 1/period
#	"""
#	
#
#
#	sTime = time
#	if isinstance(time, Variable): 
#		sTime = time.units
#		# If I have a variable I can adjust the SI prefixes to put this in
#		# a nicer range
#		r = time.array.max()
#		
#		
#	sAmp = amp
#	if isinstance(amp, Variable):
#		sAmp = amp.units
#	
#	sFreq = _das2.unit_invert(sTime)
#	
#	sPow  = _das2.unit_pow(sAmp, 2)
#	if len(sPow) == 0:
#		return "%s-1"%sFreq
#	else:
#		return "%s %s-1"%(sPow, sFreq)
#	
#	return sSD
	
	

