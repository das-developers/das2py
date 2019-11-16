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
"""Looking up data sources and sub catalogs of das catalogs"""

from . node import *
from . source import *
from . streamsrc import *

try:
  basestring
except NameError:
  basestring = str

# ########################################################################### #
class Catalog(Node):
	"""
	Catalog objects.  May contain other Catalogs, Data Source Collections or
	SpaseRec objects.
	"""
	def __init__(self, dDef, sSubKey, bStub, bGlobal):
		super(Catalog, self).__init__(dDef, bStub, bGlobal)
		self.sSubKey = sSubKey

		# If I'm a fully realized node then I'll need to initialize minimal child
		# objects
		self.subs = None
		if not self.bStub:
			self._load_stubs()

	def _load_stubs(self):
		# Load stub versions of sub items

		self.subs = {}
		for sKey in self.props[self.sSubKey]:

			dDef = self.props[self.sSubKey][sKey]

			# Assign a name based on how this appeared in the subitems
			sSep = '/'
			if 'separator' in self.props:
				if self.props['separator'] == None: sSep = ''
				else: sSep = self.props['separator']

			dDef['_path'] = "%s%s%s"%(self.props['_path'], sSep, sKey)

			if 'type' not in dDef:
				raise CatalogError("'type' missing in sources sub-item %s from %s"%(
						              	sKey, self.url))

			if dDef['type'] == 'HttpStreamSrc':
				self.subs[sKey] = HttpStreamSrc(dDef, STUB, self.bGlobal)

			# Factory time:
			if dDef['type'] == 'Catalog':
				self.subs[sKey] = Catalog(dDef, 'catalog', STUB, self.bGlobal)
			elif dDef['type'] == 'HttpStreamSrc':
				self.subs[sKey] = HttpStreamSrc(dDef, STUB, self.bGlobal)
			elif dDef['type'] == 'Collection':
				self.subs[sKey] = Collection(dDef, STUB, self.bGlobal)
			elif dDef['type'] == 'FileAggSrc':
				self.subs[sKey] = FileAggSrc(dDef, STUB, self.bGlobal)

			# TODO: Add other source types here...

			else:
				raise NotImplementedError(
					"Handling of sub-source type %s has not been implemented"%dDef['type']
				)

	def load(self):
		super(Catalog, self).load()
		self._load_stubs()


	# Providing the dictionary interface, take from page:
	# https://docs.python.org/3/reference/datamodel.html?emulating-container-types#emulating-container-types

	def __len__(self):
		if self.bStub: self.load()
		return len(self.subs)

	def __getitem__(self, key):
		if not isinstance(key, basestring):
			raise TypeError("Expected a string type for sub item key")
		if self.bStub: self.load()
		return self.subs[key]


	# Not settable, skipping __setitem__, __delitem__
	def __iter__(self):
		if self.bStub: self.load()
		return self.subs.__iter__()

	def __contains__(self,key):
		if not isinstance(key, basestring):
			raise TypeError("Expected a string type for sub item key")
		if self.bStub:	self.load()
		return self.subs.__contains__(key)

	def keys(self):
		if self.bStub: self.load()
		return self.subs.keys()

# ########################################################################### #
class Collection(Catalog):
	"""
	Data Source Catalog objects.  May only contain data source definitions
	"""

	def __init__(self, dDef, bStub, bGlobal):

		if ('type' not in dDef) or (dDef['type'] != 'Collection'):
			raise CatalogError("PyClass, data mismatch, expected 'type' to be "+\
			                   "'Collection' not '%s'"%dDef)

		super(Collection, self).__init__(dDef, 'sources', bStub, bGlobal)

	def _load_stubs(self):
		# Overload _load_stub so that sub-items can't be catalog types
		self.subs = {}
		for sKey in self.props[self.sSubKey]:

			dDef = self.props[self.sSubKey][sKey]
			if 'type' not in dDef:
				raise CatalogError("'type' missing in sources sub-item %s from %s"%(
						              	sKey, self.url))

			# Assign a name based on how this appeared in the subitems
			sSep = '/'
			if 'separator' in self.props:
				if self.props['separator'] == None: sSep = ''
				else: sSep = self.props['separator']

			dDef['_path'] = "%s%s%s"%(self.props['_path'], sSep, sKey)

			if dDef['type'] == 'HttpStreamSrc':
				self.subs[sKey] = HttpStreamSrc(dDef, STUB, self.bGlobal)
			elif dDef['type'] == 'FileAggSrc':
				self.subs[sKey] = FileAggSrc(dDef, STUB, self.bGlobal)
			else:
				raise NotImplementedError(
					"Illegal sub item type %s in container from %s"%(dDef['type'],
					self.props['_url'])
				)

	def source(self, sPurpose="primary", sPrefType="HttpStreamSrc", sPrefConv="das2"):
		"""Get a query interfaces for a data collection

		Returns:
			(dict) A dictionary describing the interfaces available for this
			    data collection.
		"""

		self.load()

		dGroups = {}




# Group    Name       Units     Default      Range               Sources
# -----    -------    -------   ----------   -----------------   -------
# Time:    maximum    isotime   2016-05-02   2011-08-05 to now   das2
#          minimum    isotime   2016-05-01   2011-08-05 to now   das2
#          interval   seconds   300                              das2
#
# Efield:  units                V m**-1      raw,                das2
#                                            V m**-1,
#                                            V**2 m**2 Hz**-1,
#                                            V m**-2 H**-1
#
# Format:  das2_text            false        boolean             das2
#
# Reader:  negative             true         boolean             das2
#          noise                true         boolean             das2
#          pls                  true         boolean             das2
#          threshold            true         boolean             das2













