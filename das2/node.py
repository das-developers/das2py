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


import _das2

import sys

from . util import CatalogError

# This is a node object.  It has 2-phase construction.  A minimal version
# may be in memory representing just a reference to an item from a higher
# level catalog entry.  The 2-phase construction is not mentioned in the user
# docs as it is an optimization to avoid loading unneeded nodes while still
# making it look like catalogs always contain thier full sub items, even if
# those items are not yet loaded.
#
#
#  .url      like a waveform this may have multiple values.  It's collapsed
#            by loading one of the items (too crazy?)
#  .path
#  .type
#  .version
#
#  .props,   this may be a minimal list
#
# Catalog type objects have to add
#
#  .keys()
#  .__getattr__
#
# The following operations can

GLOBAL = True
DETACHED = False

STUB   = True
FULL   = False

class Node(object):
	"""This represents a catalog node.  It has a 2-phase construction sequence
	A minimal version may be in memory representing just a referenced item from
	a higher level container, or it may be fully realized by a catalog lookup.

	Loading the full node is delayed until the functionality of a full definition
	is needed.  For example a minimal catalog entry will load itself when a list
	of sub items is called for.  A minimal data source entry will load itself
	when a data request or interface defintion request occurs.

	All Nodes have the following data members:
		* path - The Path URI of this object.  Even nodes loaded from a local
			file have a path URI.
		* type - The type

	"""

	def __init__(self, dDef, bStub, bGlobal):
		"""Define a node, either fully loaded or as a reference that will
		preform lazy loading as needed.

		Args:
		   dDef (dict): The object definition dictionary.  Basic items are
		      pulled from the definition to get the path, type, version, and name.

		   bStub (bool): If true this is just a stub listing, a full item
		       definition will have to be loaded as needed.

		   bGlobal (bool) : if True this node was loaded from the global catalog
			     and the full definition should be loaded using the '_path'.  If
				  False then the full definition should be loaded using the 'urls'
				  list.
		"""

		self.props = dDef
		self.bStub = bStub
		self.bGlobal = bGlobal

		self.path = dDef['_path']
		self.name = dDef['name']

		self.bStub = bStub

		if not bStub:
			self.url = dDef['_url']
			self.urls = None
		else:
			self.url = None
			self.urls = dDef['urls']

	def type(self):
		"""Just returns the output of self.__class__.__name__ for shorter code"""
		return self.__class__.__name__


	def load(self):
		"""Convert a stub node into a full node.

		This method does nothing if called on a fully loaded node.  Interally the
		list possible locations (self.urls) is used to load the full definition.
		If an error is encountered on the first URL, subsequent URLs are attempted
		until the list is exausted or a the node loads correctly.

		All new properties are merged into the self.props dictionary.

		Returns: None
		"""

		if not self.bStub:
			return None

		dDef = {}
		if self.bGlobal:
			try:
				dDef = _das2.get_node(self.path)
				self.url = dDef['_url']
			except _das2.Error as e:
				raise CatalogError("Couldn't load node %s: %s"%(self.path, str(e)))
		else:
			bGotIt = False
			for sUrl in self.props['urls']:
				try:
					dDef = _das2.get_node(self.path, None, sUrl)
					self.url = dDef['_url']
					bGotIt = True
					break
				except _das2.Error:
					pass

			if not bGotIt:
				raise CatalogError("Could not load node %s from any of %s"%(
					self.path, self.props['urls']))

		# Catalog sanity check, make sure full definition is the same type as
		# the sub definition
		if self.props['type'] != dDef['type']:
			raise CatalogError("Catalog inconsistency, expected type "+\
			                   "%s at url %s but type was %s"%(
									 self.props['type'], dDef['_url'], dDef['type']))

		# Over-write properties with new entries.
		for key in dDef:
			self.props[key] = dDef[key]

		self.bStub = False

		return None




















