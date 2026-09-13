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


"""Classes for handling das2 datasets, which for the python adaptor are just
a thin layer on ndarrays"""

import sys
import numpy
import numpy.ma
from collections import Counter, namedtuple
import datetime

import _das3

from . import dastime
from . util import *

# Names the package re-exports.  Helpers, stdlib imports and module
# globals stay out of 'from das3.dataset import *'.
__all__ = [
	'Datum',
	'Quantity',
	'Variable',
	'Dimension',
	'Dataset',
	'ds_strip_empty',
	'ds_union',
]


g_sIdxNames = "ijklmnpqrstuvwxyz" # Printing aid

lVer = numpy.__version__.split('.')
for i in range(len(lVer)):
	sInt = ''
	for j in range(len(lVer[i])):
		if lVer[i][j].isdigit(): sInt += lVer[i][j]
		else: break
	
	lVer[i] = int(sInt, 10)
	
g_bNumpy10Hacks = ((lVer[0] == 1) and (lVer[1] < 11))

if g_bNumpy10Hacks:
	import os, time
	os.environ['TZ'] = 'UTC'
	time.tzset()

# ########################################################################### #
# Numpy timedelta64 and datetime64 are probably more trouble than they are
# worth.  Common operations such as 1 / ns = GHz are outside the scope of
# numpy.  I probably shouldn't have used either datetime64 or timedelta64,
# they just don't play well with other quantities.  Also das2 and astropy
# have thier own unit handling.  Why scipy didn't take care of units is a
# mystery.  Adding unit support should have been step 1 for SciPy, because
# as soon as you start measuring the real world, numbers start to carry
# units.  -cwp
#
# Since our Quantity class carries it's own units around, strip the
# units of timedelta64 as needed for calculations.

def _np_td_cast(value):
	if isinstance(value, numpy.timedelta64):
		return value.astype('int64')

	elif isinstance(value, numpy.ndarray):
		if str(value.dtype).startswith('timedelta'):
			return value.astype('int64')

	return value

# ########################################################################### #
# Datums added to support the vangse project, needs cleanup 

class Datum(object):
	"""A single immutable value and it's units. Numpy arrays are not use
	for the backing store"""

	__slots__ = ('value','unit')

	def __init__(self, value, unit=None, valtype=None, dimless=None):
		"""Create a datum

		A datum is an immutable value and it's units.  The value may be a int, 
		float, DasTime, or str.  The unit is always a string.

		Args:
			value (int,float,DasTime,str,Datum): This is the value, or if no
				unit is specified in the second argument, this is a thing that
				will be parsed to get a value and a unit.

			unit (str): The units of this value.  These follow all the rules
				for das2C units and may be transformed by using the convert
				function. 

				If unit == None, then value will be parsed to find the units.
				Thus to avoid value parsing, exlicitly provide units.
			
			valtype (type): Explicitly set the data type for the value
				after it's parsed.  If valtype == None, then the value parser
				will define the type choosing the first one of: int, float,
				DasTime, str
			
			dimless (str): The unit type to assign if the value turns out to
				be unitless, a.k.a. Datum.unit == ''.

		Examples:
			Datum("-123Volts")  => value:-123  units:"V"
			Datum("1.456 micrometers") => value: 1.456  units:"μm"
			Datum("New Mexico")     => value:"New" units:"Mexico" (probably not what you want)
			Datum("New Mexico", "") => value:"New Mexico" units:""
			Datum("New Mexico", "State") => value:"New Mexico", units:"State"
		"""

		# Copy construction
		if isinstance(value, Datum):
			super(Datum,self).__setattr__('value', value.value)
			super(Datum,self).__setattr__('unit', value.unit)
			return 

		# If they gave me an explicit type, don't try to figure anything out
		# just do what they said
		if valtype != None:
			if valtype == str:
				super(Datum,self).__setattr__('value', value.strip())
			elif valtype == int:
				super(Datum,self).__setattr__('value', int(value.strip()) )
			elif valtype == float:
				super(Datum,self).__setattr__('value', float(value.strip()) )
			elif valtype == dastime.DasTime:
				super(Datum,self).__setattr__('value', dastime.DasTime(value.strip()) )
			else:
				raise TypeError("Unknown value type %s"%valtype)

			if unit is None:
				if valtype == dastime.DasTime:
					super(Datum,self).__setattr__('unit', "UTC")  # UTC
				else:
					super(Datum,self).__setattr__('unit', "")  # dimensionless
			else:
				super(Datum,self).__setattr__('unit', unit)
			self._subDimLess(dimless)
			return

		# Okay switch to guess work...
		if isinstance(value, (int,float,dastime.DasTime)):      # numerics
			super(Datum,self).__setattr__('value', value)
			if unit is None:
				super(Datum,self).__setattr__('unit', "")  # dimensionless
			else:
				super(Datum,self).__setattr__('unit', unit)
			self._subDimLess(dimless)
			return

		if not isinstance(value, str):
			raise TypeError("Can not create a Datum from a %s"%type(str).__name__)

		value = value.strip()
		if len(value) == 0:
			raise ValueError("Empty value string")

		if unit is not None:
			super(Datum,self).__setattr__('value', value.strip())
			super(Datum,self).__setattr__('unit', unit)
			self._subDimLess(dimless)
			return

		# Parsing value + units, this is the likely bug nest, add unittests

		# if the string can be split on spaces take the first chunk and 
		# assume its the value, everything else is the units.  This gets:
		#
		#    1.45e-14 V**2 m**-2 Hz**-1
		#    23 counts
		#
		# But not
		#
		#    New Mexico State
		#

		lValue = value.split()
		if len(lValue) > 1:
			value = lValue[0]
			unit = ' '.join(lValue[1:])
			super(Datum,self).__setattr__('unit', unit)
			try:
				# attempt int conversion first
				value = int(value, 10)
				super(Datum,self).__setattr__('value', value)
			except ValueError:
				try:
					# Attempt float conversion 2nd
					value = float(value)
					super(Datum,self).__setattr__('value', value)
				except:
					try:
						# Time conversion 3rd
						value = dastime.DasTime(value)
						super(Datum,self).__setattr__('value', value)
					except:
						# Okay, just a string
						super(Datum,self).__setattr__('value', value)	

			self._subDimLess(dimless)		
			return
	
		# Alright, no spaces.  Try to handle stuff like:
		#
		# 124mV
		# 10dB/div
		# 2005-01-01
		#
		# by reading until a non-digit (other than an 'e' or 'E' preceeded by
		# a '+' or '-') or non-dot is found.  This should be a regular expression
		n = 0
		cPrev = ""
		while n < len(value):
			if n > 0: cPrev = value[n-1]
			if value[n].isdigit() or (value[n] in  ('.','-','+')) or \
			   ( (cPrev.isdigit() or cPrev=='.') and (value[n] in ('e','E')) ):
			   n += 1
			else:
				break

		# Didn't find recognizable number, just save as a string
		if n == 0:
			super(Datum,self).__setattr__('value', value)
			super(Datum,self).__setattr__('unit', "")
			self._subDimLess(dimless)
			return

		# Found numbers, try to convert value 
		try:
			rVal = float(value[:n])
			super(Datum,self).__setattr__('value', rVal)
			super(Datum,self).__setattr__('unit', value[n:])
		except ValueError:
			# Okay can't find numeric part, try for a time
			try:
				dt = dastime.DasTime(value[:n])
				super(Datum,self).__setattr__('value', dt)
				if n < len(value) and (value[n:].lower() != 'z'):
					super(Datum,self).__setattr__('unit', value[n:])
				else:
					super(Datum,self).__setattr__('unit', "UTC")
			except ValueError as e:
				# Won't convert to dastime, well just save as as string, if they wanted
				# to skip the chance at mistaken autoconvert, should have specified the
				# units explicitly
				super(Datum,self).__setattr__('value', value[:n])
				super(Datum,self).__setattr__('unit', value[n:])

		self._subDimLess(dimless)


	def _subDimLess(self, dimless):
		"""If unit happens to be dimensionless, sub in this value"""
		if dimless and (self.unit == ''):
			super(Datum,self).__setattr__('unit',dimless)

	def __str__(self):
		if self.unit != "":
			return ("%s"%(self.value))
		else:
			return ("%s %s"%(self.value, self.unit))

	def __repr__(self):
		if isinstance(self.value, str):
			return "<das3.Datum: value='%s' units='%s'>"%(self.value, self.unit)
		else:
			return "<das3.Datum: value=%s units='%s'>"%(self.value, self.unit)


# ########################################################################### #

class Quantity(namedtuple('Quantity', 'value unit')):
	"""A set of values and thier units.  Quantities are the return values from
	Variable subsetting operations.

	This is a lightweight emulation of Quantity objects from AstroPy.  Unlike
	Variables, Quantities are not members of a Dataset and may have any shape.
	Furthermore Quantities have no knowledge of thier degenericies.

	To avoid extra dependencies, the AstroPy Quantity class is not used directly
	within das2py, but users of both this library and Astropy are encouraged to
	convert das3.Quantity objects to astropy.units.Quantity objects using the
	the :meth:`das3.astro._wrap() function from the optional
	:mod:`das3.astro` module.
	"""
	__slots__ = ()


	def _trim_time(self, dt):
		s = str(dt)
		if s[:17] == "numpy.datetime64('":s = s[18:-2]
		if s.endswith('+0000'): s = s[:-5]
		while s.endswith('000'): s = s[:-3]
		if s.endswith('.'): s = s[:-1]
		while s.endswith(':00'): s = s[:-3]
		if s.endswith('T00'): s = s[:-3]
		return s

	def _trim_units(self, item):
		s = str(item)
		l = s.split()
		return l[0]

	def __str__(self):

		sUnit = self.unit
		bPrnUnits = (self.unit != None)
		if bPrnUnits: bPrnUnits = (len(self.unit) > 0)
		lItems = []

		# Specilized printing for sequences
		if isinstance(self.value, (list, numpy.ndarray, tuple)):

			for item in self.value:
				if isinstance(item, (
					numpy.datetime64, dastime.DasTime, datetime.datetime)):
					bPrnUnits = True
					sUnit = 'UTC'
					lItems.append(self._trim_time(item))

				elif isinstance(item, numpy.timedelta64):
					lItems.append(self._trim_units(item))

				else:
					lItems.append(str(item))

		else:
			if isinstance(self.value, (
				numpy.datetime64, dastime.DasTime, datetime.datetime)):
				bPrnUnits = True
				sUnit = 'UTC'
				lItems.append(self._trim_time(self.value))

			elif isinstance(self.value, numpy.timedelta64):
				lItems.append(self._trim_units(self.value))

			else:
				lItems.append(str(self.value))

		if len(lItems) > 1: sVal = "[%s]"%", ".join(lItems)
		else: sVal = lItems[0]

		if bPrnUnits: return "%s %s"%(sVal, sUnit)
		else: return sVal


	def __repr__(self):
		return "Quantity: value=%s, unit=%s"%(self.value, self.unit)

	def to_value(self, unit=None):
		"""Return the numeric value, possibly in different units.

		Deliberately snake_case, unlike the other methods here: this is the
		name AstroPy gives the same operation on its Quantity, so code that
		handles both kinds of quantity can call one method.

		Args:
			unit (str) : If None this is the same as accessing the .value member

		Returns: value : ndarray or scaler
			The value, which may be an array, in the requested units.

		Raises:
			ValueError if the units of the current Quantity are not compatible
			with the desired units
		"""
		if unit == None or unit == self.unit:
			return self.value

		if not _das3.convertible(self.unit, unit):
			raise ValueError(
				"This Quantities's units, %s, are not convertable to %s"%(
				self.unit, unit
			))

		rScale = _das3.convert(1.0, self.unit, unit)
		return rScale * self.value




	def __add__(self, other):
		if isinstance(other, Quantity):
			v = self.value + other.to_value(self.unit)
		else:
			v = self.value + other

		return Quantity(value=v, unit=self.unit)

	def __sub__(self, other):
		if isinstance(other, Quantity):
			v = self.value - other.to_value(self.unit)
		else:
			v = self.value - other

		return Quantity(value=v, unit=self.unit)

	def __truediv__(self, other):
		if isinstance(other, Quantity):
			u = _das3.unit_div(self.unit, other.unit)
			v = _np_td_cast(self.value) / _np_td_cast(other.value)
		else:
			u = self.unit
			v = _np_td_cast(self.value) / _np_td_cast(other)

		return Quantity(value=v, unit=u)

	def __rtruediv__(self, other):
		if isinstance(other, Quantity):
			u = _das3.unit_div(other.unit, self.unit)
			v = _np_td_cast(other.value) / _np_td_cast(self.value)
		else:
			u = _das3.unit_invert(self.unit)
			v = _np_td_cast(other) / _np_td_cast(self.value)

		return Quantity(value=v, unit=u)


	def __mul__(self, other):
		if isinstance(other, Quantity):
			u = _das3.unit_mul(self.unit, other.unit)
			v = self.value * other.value
		else:
			u = self.unit
			v = self.value * other

		return Quantity(value=v, unit=u)



# ############################################################################ #

# Variables could easily have been based off of Quantities in Astropy, and
# maybe that is the right way to do it.  But since I never know what external
# packages may be used with das2py and I don't want to require astropy as a
# dependency.
#
# I'm going to just go with my own class which allows for some creative
# indexing, though not a fancy as pandas dataframes.

class Variable(object):
	"""Data arrays with a stated purpose and units

	Special members of this class are:

	  - .array - The underlying ndarray object
	  - .units - The units as a string
	  - .name  - A name for this variable, defaults to it's role in the dimension
	  - .unique - A list of indicies in which these values are (potentially)
	        unique.
	  - .ops   - None, or a dictionary describing the math formalism of a
	        composite value: 'kind' plus the parameters from the stream's
	        <ops> element under their wire names (frame, body, system, ...)
	  - .subrank - How many trailing indices of .array are internal to one
	        value (1 for a vector, 2 for a matrix), 0 for a scalar.  See
	        extShape() and intrShape() for the two halves of the shape.
	  - .labels - One label per component in storage order, or None when the
	        variable was not read from a stream

	Variables are very similar to Quantities in AstroPy.
	"""
	def __init__(self, dim, role, values, units, axis=None, fill=None, subrank=0):
		"""Create a new Variable.

		Args:
			dim (Dimension) : Parent Dimension for this Variable

			role (str) : The role this variable plays in the dimension

			values (list, tuple, ndarray) : The actual data values.  If the
				values are an array od datetime64 types, they must be in units
				of nanoseconds since 1970-01-01

			units (str) : The units for these values.  Units will be re-calculated
				automatically when Variables are combinded.

			axis (int, optional) : The first axis in the dataset in which the
			   values are unique.  For example, frequency values that map to the
				second index would have axis=1.  Defaults to 0.

			fill (float,str) : If specified, a masked array will be constructed
				using this value as mask-out flag.

			subrank (int, optional) : How many trailing indices of values are
				internal to one value (1 for a vector, 2 for a 3x3 matrix).  These
				are not dataset indices and take no part in broadcasting.
		"""

		self.dim = dim
		self.name = role
		self.units = units
		self.array = None
		self.fill = fill
		self.subrank = subrank
		self.ops = None
		self.labels = None

		# make sure we store time arrays in ns1970
		if units.upper() == 'UTC':

			# Hack to deal with old versions of numpy (ex: Centos7) that
			# absolutely refuse to convert '2001-01-01' to units of ns
			if g_bNumpy10Hacks:
				# Not robust, but 2-D date arrays are rare
				if not isinstance(values, numpy.ndarray):
					values = [str(dastime.DasTime(s)) for s in values]

			# Make sure we preserve masked arrays
			if isinstance(values, numpy.ma.MaskedArray):
				array = numpy.ma.asarray(values, dtype='M8[ns]')
			else:
				array = numpy.asarray(values, dtype='M8[ns]')

		else:
			if isinstance(values, numpy.ma.MaskedArray):
				array = values
			else:
				array = numpy.asarray(values)


		# if we recived a masked array make sure to capture it's fill value
		if (fill == None) and isinstance(array, numpy.ma.MaskedArray):
			fill = array.fill_value

		ds_shape = dim.ds.shape

		# Only the external shape takes part in index bookkeeping.  The
		# internal shape rides along at the end of every broadcast below.
		nExt = len(array.shape) - subrank
		if nExt < 0:
			raise DatasetError("Variable %s:%s has %d indices but claims %d internal"%(
				dim.name, role, len(array.shape), subrank))
		tExt = array.shape[:nExt]
		tIntern = array.shape[nExt:]

		scoot = 0                  # See if we need to scoot our indicies
		if axis != None:
			if isinstance(axis, int): scoot = axis
			else: scoot = axis[0]

		lShape = []
		self.unique = []
		if scoot:
			lShape += [None]*scoot
			self.unique += [False]*scoot

		lShape += list(tExt)
		self.unique += [True]*len(tExt)

		nMoreAx = len(ds_shape) - len(lShape)
		if nMoreAx:
			lShape += [None]*nMoreAx
			self.unique += [False]*nMoreAx

		# I may have more index positions than the dataset, if so act
		# as if the dataset has a 1 (or my size) for any missing sizes
		adj_ds_shape = []
		for i in range(len(lShape)):
			if i < len(ds_shape): adj_ds_shape.append(ds_shape[i])
			if i >= len(ds_shape):
				if lShape[i] == None: adj_ds_shape.append(1)
				else: adj_ds_shape.append(lShape[i])
		ds_shape = adj_ds_shape


		# Now my shape array looks something like this:
		#
		#  Me: [None, 14, 27, None]
		#
		#  Ds: [10,   14, 27, 73  ]

		if lShape[0] == None:
			i = 0
			while lShape[i] == None:
				lShape[i] = ds_shape[i]
				i += 1

			iLast = len(lShape) - 1
			while lShape[iLast] == None: iLast -= 1

			array = numpy.broadcast_to(array, tuple(lShape[:iLast+1]) + tIntern)
			#print("New var shape is: %s (%s)"%(lShape, array.shape))

		# Now my shape array looks something like this:
		#
		# Me:  [10,  14, 27, None]
		# DS:  [10,  14, 27, 73 ]
		# --or--
		# DS:  [ 1,  1,  27, 73 ]


		# Repeat smaller indexes and broadcast again
		if lShape.count(None) > 0:
			#print("Splitting lower indexes cause: %s and ds is %s"%(lShape, ds_shape))
			nKeep = len(lShape) - lShape.count(None)
			lSlice = [ slice(None, None, None) for i in range(nKeep) ]
			lSlice += [None]*lShape.count(None)

			# I may be bigger in the first indicies than the dataset, may it adjust
			# to me if needed.
			new_shape = ds_shape
			for i in range(len(new_shape)):
				if lShape[i] and (lShape[i] > ds_shape[i]): new_shape[i] = lShape[i]
				else: new_shape[i] = ds_shape[i]

			#print("New slice is: %s to be bcast to %s"%(lSlice, new_shape))
			array = numpy.broadcast_to(array[tuple(lSlice)], tuple(new_shape) + tIntern)

		# Callback to tell dataset to adjust it's arrays if needed
		self.array = array
		self.dim.ds._bcast(self.extShape())

		# After all is said and done make sure that the DS shape and the
		# Variable shape now match
		if (len(self.unique) != len(self.dim.ds.shape)) or \
		   (len(self.extShape()) != len(self.dim.ds.shape)):
			raise DatasetError(
				"Dataset Inconsistancy detected! %s:%s  %s %s, dateset: %s"%(
				self.dim.name, self.name, self.unique, self.array.shape, self.dim.ds.shape)
			)


	def extShape(self):
		"""The shape of this variable over the dataset indices alone, without
		the trailing internal shape of a composite value."""
		return self.array.shape[:len(self.array.shape) - self.subrank]

	def intrShape(self):
		"""The internal shape of one value: (3,) for a vector, (3, 3) for a
		matrix, () for a scalar.  These indices trail extShape() in .array.
		Mirrors DasVar_intrShape() in das2C."""
		return self.array.shape[len(self.array.shape) - self.subrank:]

	def __str__(self):
		lIdx = []
		#lRng = []

		for i in range(len(self.unique)):
			if self.unique[i]:
				lIdx.append(g_sIdxNames[i])
				#lRng.append("%s:0..%d"%(g_sIdxNames[i], self.array.shape[i]))
			else:
				lIdx.append('-')
				#lRng.append("%s:-"%g_sIdxNames[i])

		sIdx = ','.join(lIdx)
		#sRng = ', '.join(lRng)

		# Internal indices get a second bracket with capital letters, matching
		# das2C's printer, so var.array[i,j][I,J] is literally the indexing
		# the string shows.  Scalars print as they always have.
		if self.subrank > 0:
			sIdx += ']['  + ','.join(g_sIdxNames[n].upper() for n in range(self.subrank))

		#return "%s['%s'][%s] %s | %s"%(self.dim.name, self.name, sIdx, self.units, sRng)
		sOut = "%s['%s'][%s] (%s) %s"%(self.dim.name, self.name, sIdx, self.array.dtype, self.units)
		return sOut.rstrip()

	def _bcast(self, shape):
		shape = tuple(shape)
		nExt = len(self.array.shape) - self.subrank
		tIntern = self.array.shape[nExt:]
		if shape == self.array.shape[:nExt]: return

		# The bcast can't ask me to shift to the right, but it can ask me to
		# add indices to the right that I didn't have, or to repeat my self in
		# higher indices.  New indices go between the external and internal
		# shapes: numpy keeps unnamed trailing axes, so a slice tuple that
		# names only the external axes inserts there.
		nExtra = len(shape) - nExt
		if nExtra:
			lSlice = [slice(None, None, None) for i in range(nExt) ]
			lSlice += [None]*nExtra
			self.array = self.array[tuple(lSlice)]
			self.unique += [False]*nExtra

		# Okay, I have extra dimensions, now broadcast
		self.array = numpy.broadcast_to(self.array, shape + tIntern)

	def __add__(self, other):
		# Check that the units are compatable
		if not _das3.can_merge(self.units, '+', other.units):
			raise DatasetError("Operation %s + %s is invalid"%(self.units, other.units))

		# Get the scaling factor
		rFactor = 1.0
		if self.units == 'UTC' or self.units == 'ns1970':
			rFactor = _das3.convert(1.0, other.units, 'ns')
			my_ary = self.array.astype("int64", copy=False)
			other_ary = other.array * rFactor
			other_ary = other_ary.astype("int64")
			new_ary = my_ary + other_ary
			new_ary = new_ary.astype(numpy.dtype('M8[ns]'), copy=False)
		else:
			rFactor = _das3.convert(1.0, other.units, self.units)
			new_ary = self.array + (other.array * rFactor)

		var = Variable(self.dim, None, new_ary, self.units, fill=self.fill,
		               subrank=self.subrank)
		return var


	def degenerate(self, *indexes):
		"""Return true if this variable is degenerate in all the given indexes
		"""
		if len(indexes) == 0: return True

		if len(indexes) == 1:
			if isinstance(indexes[0], (tuple, list)):
				for i in indexes[0]:
					if self.unique[i]: return False
			else:
				if self.unique[ indexes[0] ]: return False
		else:
			for i in indexes:
				if self.unique[i]: return False

		return True
		
	def uniIndex(self):
		"""Get a non-degenerate slice tuple
		
		To grab the non-degenerate values of this variable use::
		
		   idx = var.uniIndex()
			aUnique = var.array[ var.uniIndex() ]
		
		Returns: tuple of slice objects and integers
		"""
		tSlice = tuple([slice(None, None, None) if b else 0 for b in self.unique])
		return tSlice

	def containsAny(self, quant):
		"""Are any of the given values within the range of this Variable

		Args:
			quant (number, Quantity) : the value to check must be of a type that
			   is comparable to the values in the backing array but not nessecarily
				in the same units.  If a Quantity is supplied than unit conversions
				are applied before comparing values.

		Returns: bool
			True if variable.max <= value <= variable.max, for all supplied
			values or False otherwise
		"""

		# Simple value case (no units)
		rMin = self.array.min()
		rMax = self.array.max()

		if isinstance(quant, Quantity):
			if not _das3.convertible(self.units, quant.unit):
				raise ValueError(
					"This Variable's units, %s, are not convertable to %s"%(
					self.units, quant.unit
				))

			if (self.units != quant.unit):
				rMin = _das3.convert(rMin, self.units, quant.unit)
				rMax = _das3.convert(rMax, self.units, quant.unit)


		# Can't use loops.
		aTest = numpy.logical_and(quant.value < rMin, quant.value > rMax)
		if numpy.any( aTest ):
			return False

		return True

	def min(self):
		return Quantity(value=self.array.min(), unit=self.units)

	def max(self):
		return Quantity(value=self.array.max(), unit=self.units)


	def __getitem__(self, tSlice):
		"""Return a Quantity of values"""
		return Quantity(value=self.array.__getitem__(tSlice), unit=self.units)


	def sorted(self):
		"""Determine if the values in this variable are sorted in Ascending
		order by index.

		For Variables built from reference and offset arrays, this function
		will return false if the data are sorted in the reference array and
		in the offset array, but the offsets bump final values past the next
		reference point.  Almost all instrument cycles prevent this from being
		the case, but it is listed here as a possible failure mode.
		"""
		aRavel = numpy.ravel(self.array)
		bRet = numpy.all( aRavel[:-1] <= aRavel[1:] )
		return bRet

# ########################################################################### #

class Dimension(object):
	"""A physical or orginaziational dimension in a Dataset.

	This object does not represent an index dimensions, but rather categories,
	such as time, frequency, electric field amplitudes, cites in Austrilia, etc.

	Dimensions contain Variables.  A dimension knows which kind it is, .kind
	is 'coord' or 'data', the same split das2C's dim_type carries, so code
	that walks a dataset can sort them without reaching into the dataset:

	   lCoords = [ds[s] for s in ds if ds[s].kind == 'coord']
	"""

	KINDS = ('coord', 'data')

	def __init__(self, dataset, sName, sKind):
		# Create a new dimension for a dataset

		if sKind not in Dimension.KINDS:
			raise ValueError("Dimension kind must be one of %s, not %r"%(
				Dimension.KINDS, sKind))
		self.ds = dataset
		self.kind = sKind
		self.props = {}
		self.vars = {}
		self.name = sName

	def var(self, role, values, units, axis=None, fill=None, subrank=0):
		"""Create or replace a variable in this dimension.

		Add a variable to a dataset can trigger broadcasting of other variables
		to fill the required index space.  See :class:`das3.Variable` for the
		meaning of subrank.
		"""

		_var = Variable(self, role, values, units, axis, fill, subrank)
		self.vars[role] = _var

		# If there happens to be both a reference and offset variable
		# in this dimension, trigger creation of a center variable
		if ('reference' in self.vars) and ('offset' in self.vars) and \
		   (not ('center' in self.vars)):

			self['center'] = self.vars['reference'] + self.vars['offset']
			self['center'].name = 'center'

		return _var

	def center(self, values, units, axis=None, fill=None):
		"""Shortcut for :meth:`das3.Dimension.var` for center values"""
		var = self.var('center', values, units, axis, fill)
		return var

	def reference(self, values, units, axis=None, fill=None):
		"""Shortcut for :meth:`das3.Dimension.var` for referenece values"""
		var = self.var('reference', values, units, axis, fill)
		return var

	def offset(self, values, units, axis=None, fill=None):
		"""Shortcut for :meth:`das3.Dimension.var` for offset values"""
		var = self.var('offset', values, units, axis, fill)
		return var
		
	def primary(self):
		"""Get the primary variable for this Dimension.
		
		Returns:
			The Variable 'center' if present.  If there is no variable with
			the role 'center' in this dataset, the following are checked in
			order and returned if found: 'mean', 'median', 'mode'.
		"""
		if 'center' in self.vars: return self.vars['center']
		if 'mean' in self.vars: return self.vars['mean']
		if 'median' in self.vars: return self.vars['median']
		if 'mode' in self.vars: return self.vars['mode']
		
		return None

	def hasProp(self, sKey):
		"""Does this dimension carry the named property"""
		return sKey in self.props

	def hasPropVal(self, sKey, sValue):
		"""Does this dimension carry the named property with the given value.
		False, not an error, when the property is absent."""
		return (sKey in self.props) and (self.props[sKey] == sValue)

	def __contains__(self,key):
		if not isinstance(key, str):
			raise TypeError("String type expected for variable role name, "
			                "not %s (%s)"%(key, key.__class__.__name__))
		return self.vars.__contains__(key)

	def keys(self):
		return self.vars.keys()

	def __getitem__(self, key):
		"""Dimension acts as a dictionary of variables"""
		if not isinstance(key, str):
			raise TypeError("String type expected for variable role name, "
			                "not %s (%s)"%(key, key.__class__.__name__))
		
		if key in self.vars: return self.vars[key]
		
		# Always try to make center work if you can.
		if key == 'center':
			for _key in ('mean', 'median', 'mode'):
				if _key in self.vars: return self.vars[_key]
		
		raise KeyError("Role %s not present in dimension %s"%(key, self.name))

	def __setitem__(self, key, item):
		"""Add a Variable to the dimension"""
		if not isinstance(key, str):
			raise TypeError("String type expected for variable role name, "
			                "not %s (%s)"%(key, key.__class__.__name__))

		if not isinstance(item, Variable):
			raise TypeError("Variable object expected in assignement for key "
			                "%s, not type %s, "%(key, item.__class__.__name__))

		# Should trigger broadcasting here...
		if item.array.shape != self.ds.shape:
			raise DatasetError("Shape mismatch in assignment, var = %s, dataset = %s"%(
				item.array.shape, self.ds.shape
			))

		self.vars[key] = item


	def __iter__(self):
		return self.vars.__iter__()

# ########################################################################### #

class Dataset(object):
	"""Dataset - Sets of arrays correlated in index space.

	The Dataset object exists to unambiguously define data read from a das2
	stream (or other supported serialization protocol) in memory so that it may
	be either used directly or handed over to native structures used in larger
	analysis packages.

	Special members of this class are:

		- .id - A string identifing this dataset with it's group
		- .group - A string identifing which group this dataset belongs to.
			all datasets in a group may be plotted on the same graph
		- .shape - The overall iteration shape of all members of this dataset.

	Note: All arrays from all the Dimensions in this dataset can be used
		with the same iteration indices, no matter thier internal storage.
		The variables within this Dataset are thus correlated in index space.
		For example given the index set [i : j : k], if some set of i's are
		valid for one Variable within the Dataset, then the same range of i's
		are valid for all Variables within the dataset.  The same is true for
		j, k, and so on.  Array broadcasting is used to conserve memory.  See
		the Variable.degenerate() function for more information.

	Datasets contain Dimensions.
	"""

	def __init__(self, sId, group=None):
		"""Initialize a Dataset

		Args:
			sId (str) : The identifier for this dataset. Will be used as a
				variable identifier, so no spaces or operator characters, and
				no more than 63 bytes long.

			sGroup (str) : The name of the join group for this dataset.
		"""

		self.name = sId
		self.rank = 0
		self.group = group
		self.props = {}
		self._dCoord = {}
		self._dData = {}
		self.shape = ()  # Empty tuple

	def coord(self, sId):
		"""Create or get a coordinate dimension"""
		if sId not in self._dCoord:
			self._dCoord[sId] = Dimension(self, sId, 'coord')
		return self._dCoord[sId]

	def data(self, sId):
		"""Create or get a data dimension"""

		if sId not in self._dData:
			self._dData[sId] = Dimension(self, sId, 'data')
		return self._dData[sId]


	def dim(self, sId):
		"""Create or get a dimension.
		"""
		if not sId.startswith('data:') and not sId.startswith('coord:'):
			raise ValueError("Can't catagorize dimenison, does not start with"
			      "'coord:' or 'data:'")

		if sId.startswith('data:'):
			return self.data(sId.replace('data:',''))

		if sId.startswith('coord:'):
			return self.coord(sId.replace('coord:',''))


	def _allVars(self):
		"""Return a list of all variables in the dataset, no matter the
		dimension"""
		lDims = [self._dCoord[var] for var in self._dCoord]
		lDims += [self._dData[var] for var in self._dData]
		lVars = []
		for dim in lDims:
			for sVar in dim.vars:
				lVars.append(dim.vars[sVar])

		return lVars


	def _bcast(self, shape):
		for sDim in self._dCoord:
			dim = self._dCoord[sDim]
			for sVar in dim:
				#print("Asking coord:%s:%s to update to shape %s"%(sDim, sVar, shape))
				dim.vars[sVar]._bcast(shape)

		for sDim in self._dData:
			dim = self._dData[sDim]
			for sVar in dim:
				#print("Asking coord:%s:%s to update to shape %s"%(sDim, sVar, shape))
				dim.vars[sVar]._bcast(shape)

		self.shape = shape

	def __setitem__(self, key, item):
		if not isinstance(key, str):
			raise TypeError("String type expected for dimension name")
		if not isinstance(item, Dimension):
			raise TypeError("Dimension type expected, not %s"%item.__class__.__name__)

		if key.startswith('coord:'):
			sDim = key.replace('coord:','')
			self._dCoord[sDim] = item

		if key.startswith('data:'):
			sDim = key.replace('data:','')
			self._dData[sDim] = item


	def __getitem__(self, key):
		"""Get dataset subsets

		Args:
			key (str, tuple) : A string to get a dimension, a slice or tuple of
				slices to get a subset along an axis.

		Returns:
			Dimension or Dataset
		"""
		if isinstance(key, (slice, tuple, int)):
			#TODO: Add code here to create sub datasets by applying a tuple of
			#      slices to all the variables.
			raise NotImplementedError("Slicing whole datasets is not yet implemented (but wouldn't be hard to do if desired)")


		if key.startswith('coord:'):
			key = key.replace('coord:','')
			return self._dCoord[key]

		if key.startswith('data:'):
			key = key.replace('data:','')
			return self._dData[key]

		# Not prefixed
		if key in self._dData:
			return self._dData[key]
		else:
			return self._dCoord[key]

	def __iter__(self):
		# In a multithreaded application we would store the iteration state
		# somewhere else.  This doesn't seem to be a concern in python so
		# we'll store the iteration state here.
		self.lIter = self.keys()
		return self

	def __next__(self):
		if len(self.lIter) == 0: raise StopIteration
		return self.lIter.pop(0)

	next = __next__   # the python 2 spelling of the iterator protocol

	def __contains__(self, key):
		# Same spellings as __getitem__: bare, or prefixed by kind
		if key.startswith('coord:'):
			return key[6:] in self._dCoord
		if key.startswith('data:'):
			return key[5:] in self._dData
		return (key in self._dData) or (key in self._dCoord)

	def keys(self):
		"""Every dimension name, prefixed by kind ('coord:time', 'data:amp')
		and sorted.  See coordKeys() and dataKeys() for one kind at a time,
		unprefixed and in the order the dimensions were added."""
		lKeys = ["coord:%s"%s for s in list(self._dCoord.keys()) ]
		lKeys += ["data:%s"%s for s in list(self._dData.keys()) ]
		lKeys.sort()
		return lKeys

	def coordKeys(self):
		"""Names of the coordinate dimensions, in the order they were added
		(the stream's order on python 3.7 and later).  Fetch one with
		coord(name) or ds[name]."""
		return list(self._dCoord.keys())

	def dataKeys(self):
		"""Names of the data dimensions, in the order they were added (the
		stream's order on python 3.7 and later).  Fetch one with data(name)
		or ds[name]."""
		return list(self._dData.keys())

	def _check_shape(self):

		for sD in self._dData:
			for sV in self._dData[sD].vars:
				shape = self._dData[sD].vars[sV].array.shape
				if shape != self.shape:
					sMsg = "Invalid Variable %s shape %s, expected %s"%(
							  sV, shape, self.shape)
					raise DatasetError(self.group, self.name, sMsg)

		for sC in self._dCoord:
			for sV in self._dCoord[sC].vars:
				shape = self._dCoord[sC].vars[sV].array.shape
				if shape != self.shape:
					sMsg = "Invalid Variable %s shape %s, expected %s"%(
							  sV, shape, self.shape)
					raise DatasetError(self.group, self.name, sMsg)


	def _dimStrs(self, sType, dim):
		lLines = []
		lLines.append("   %s Dimension : %s"%(sType, dim.name))
		for sProp in dim.props:
			lLines.append("      Property: %s | %s"%(sProp, dim.props[sProp]))
		if len(dim.props): lLines.append("")

		lVars = list(dim.vars.keys())
		lVars.sort()
		lLines += ["      Variable: %s"%str(dim.vars[sVar]) for sVar in lVars]
		return lLines

	def __str__(self):
		"""Get a string summarizing the dataset"""
		lLines = []
		lAxes = range(len(self.shape))
		nAxes = len(lAxes)
		lShape = ["%s:0..%d"%(g_sIdxNames[i], self.shape[i]) for i in lAxes]
		sShape = ""
		if nAxes: sShape = " | " + ", ".join(lShape)
		s = "Dataset: '%s' from group '%s'%s"%(self.name, self.group, sShape)
		lLines.append(s)

		for sProp in self.props:
			lLines.append("   Property: %s | %s"%(sProp, self.props[sProp]))
		if len(self.props): lLines.append("")

		lDims = list(self._dData.keys())
		lDims.sort()
		for sDim in lDims:
			dim = self._dData[sDim]
			lLines += self._dimStrs("Data", dim)
			lLines.append("")

		lDims = list(self._dCoord.keys())
		lDims.sort()
		for sDim in lDims:
			dim = self._dCoord[sDim]
			lLines += self._dimStrs("Coordinate", dim)
			lLines.append("")

		return "\n".join(lLines)



	def getVar(self, sVar):
		"""Get a variable from a dateset using a Variable path string

		Args:
			sVar (str) : The variable path string.  These have the form:

					[CATEGORY:]DIMENSION[:VARIABLE]

				for example:

					coords:time:center

				would specify the center positions of time coordinate.
				If the CATEGORY portion is not supplied both coords and data are
				searched for the given DIMENSION, which will be used if it's
				unique within the dataset.  If the VARIABLE portion is not supplied,
				'center' is assumed.

		Returns: tuple(sAbsPath, Variable)
			A tuple containing the expanded path name and the Variable

		Raises:
			KeyError : if the no variable can be found with the given name.
		"""
		lPath = sVar.split(':')

		if lPath[0] == 'coords' and (len(lPath) > 1):
			if lPath[1] in self._dCoord:
				if len(lPath) > 2:
					if lPath[2] in self._dCoord[ lPath[1] ]:
						sPath = 'coords:%s:%s'%(lPath[1], lPath[2])
						return (sPath, self._dCoord[ lPath[1] ][ lPath[2] ])
				else:
					if 'center' in self._dCoord[ lPath[1] ]:
						sPath = 'coords:%s:center'%(lPath[1])
						return (sPath, self._dCoord[ lPath[1] ][ 'center' ])

		if lPath[0] == 'data' and (len(lPath) > 1):
			if lPath[1] in self._dData:
				if len(lPath) > 2:
					if lPath[2] in self._dData[ lPath[1] ]:
						sPath = 'data:%s:%s'%(lPath[1], lPath[2])
						return (sPath, self._dData[ lPath[1] ][ lPath[2] ])
				else:
					if 'center' in self._dData[ lPath[1] ]:
						sPath = 'data:%s:center'%(lPath[1])
						return (sPath, self._dData[ lPath[1] ][ 'center' ])

		# Okay, looks like they left the coords, data part out.
		if (lPath[0] in self._dCoord) and not (lPath[0] in self._dData):
			if len(lPath) > 1:
				if lPath[1] in self._dCoord[ lPath[0] ]:
					sPath = 'coords:%s:%s'%(lPath[0], lPath[1])
					return (sPath, self._dCoord[ lPath[0] ][ lPath[1] ])
			else:
				if 'center' in self._dCoord[ lPath[0] ]:
					sPath = 'coords:%s:center'%(lPath[0])
					return (sPath, self._dCoord[ lPath[0] ][ 'center' ])


		if (lPath[0] in self._dData) and not (lPath[0] in self._dCoord):
			if len(lPath) > 1:
				if lPath[1] in self._dData[ lPath[0] ]:
					sPath = 'data:%s:%s'%(lPath[0], lPath[1])
					return (sPath, self._dData[ lPath[0] ][ lPath[1] ])
			else:
				if 'center' in self._dData[ lPath[0] ]:
					sPath = 'data:%s:center'%(lPath[0])
					return (sPath, self._dData[ lPath[0] ][ 'center' ])


		raise KeyError("Variable %s not present or not unique in Dataset %s"%(
		                 sVar, self.name))


	# Sorting is a pain because sorting this:
	#
	#    A   B   C          A[i], B[i], C[i]
	#   --- --- ---
	#    1   2   *          # sort tuples of (A[i], B[i]) using the
	#    1   3   *          # resulting index map to reorder A, B and C
	#    1   1   *
	#    2   2   *
	#    2   3   *
	#    2   1   *
	#
	# Is fundamentally different from sorting this:
	#
	#          B            A[i], B[j], C[i,j]
	#   A   2  3  1
	#  ---  -------
	#   1   *  *  *         # sort A, use the resulting index map to reorder
	#   2   *  *  *         # A and then rows of C.  Then sort B using the
	#                       # resulting index map to reorder B and the
	#                       # columns of C
	#
	# from an algorithm view, but *NOT* from a human view.  Sorting should
	# JUST WORK without das2py users needing to know the details of the storage
	# arrays.
	#
	# It gets even weirder if we're to sort on A[i] and B[i,j] for data arrays
	# of C[i,j,k].  So now a sort index is determined based on tuples of
	# ( A[i,j], B[i,j] ) where A is broadcast to repeat in j.  Then the j=0 slice
	# of the resulting index is used to reorder A and the entire i,j index set is
	# then used to reorder B, and C must be re-ordered in two axes, but without
	# affecting it ordering in k.... whew!
	#
	# For now I'm only handling sorting on variables that are degenerate in
	# all but one dimension.  Will add capability later as needed.

	def array(self, sVar):
		return self.getVar(sVar)[1].array

	def sort(self, *tSortOn, **kwargs):
		"""Sort ascending all values in all variables in a dataset based on the
		values in a single variable, and then on the values in a second variable
		and so on.

		The sorting algorithm varies depending on the data layout.  Variables that
		are degenerate in axis will not alter ordering of other variables along
		that axis.  For example in a common time, frequency 2-D cube.  Sorting on
		time will not affect frequency values and vice versa.

		Args:
			lSortOn (str) : A list of Variable path strings stating the first sort
			   parameter, the second sort parameter and so on.  Variable path
				strings have the form:

					CATEGORY:DIMENSION:VARIABLE

				for example:

					coords:time:center

				would specify the center positions of time coordinate.  To sort
				first on one variable and then on another specify more than one
				string.  For example:

					['coords:time:center','coords:frequency:center']

				would sort first on time and then on frequency depending on the
				limits specified above

		Returns: None
			There is no return value, data are sorted in place.
		"""

		# Wierd sort group issue:
		#
		#  A(i), B(j), C(i,j), D(k), E(i,k)

		# First check to see if there's anything to sort
		perr = None
		if ('verbose' in kwargs) and (kwargs['verbose']):
			perr = sys.stderr.write
			perr("INFO: Solving sort method for vars: %s\n"%list(tSortOn))

		bShutup = ('nowarn' in kwargs) and (kwargs['nowarn'])


		VarInfo = namedtuple('VarInfo', 'nOrder sName var')
		GrpInfo = namedtuple('GrpInfo', 'lVi lUni')

		lNames = []
		lSort = []
		iOrder = 0
		for s in tSortOn:
			(name, var) = self.getVar(s)
			#if var.sorted():  BUG! Have to keep sorted items in case we are doing
			#	continue        a lexsort. (i.e. by column A then B then C etc.)
			#                  TODO: Drop already sorted vars when not doing a
			#                        lex sort

			lSort.append(VarInfo(iOrder, name.replace(':','_'), var))
			iOrder += 1

		if len(lSort) == 0:
			return None  # Nothing to sort

		# Make groups of sort variables based on thier unique indicies

		var_info = lSort.pop(0)
		lGroups = [ GrpInfo(lVi=[var_info], lUni=[b for b in var_info.var.unique]) ]

		while len(lSort) > 0:

			grp = lGroups[-1]  # Building the last group

			while True:   # Loop until no variables are added to the group
				nAdded = 0

				lUnGrouped = []
				for i in range(len(lSort)):
					vi = lSort[i]

					# If any unique indicies between the group and the var overlap
					# add it to the group and make a merged unique index list
					if any( [a and b for a,b in zip(grp.lUni, vi.var.unique)] ):
						grp.lVi.append(vi)
						merge = [a or b for a,b in zip(grp.lUni, vi.var.unique)]
						for i in range(len(merge)): grp.lUni[i] = merge[i]
						nAdded += 1
					else:
						lUnGrouped.append(vi)

				if nAdded == 0: break
				else: lSort = lUnGrouped

			# This group is done, start the next one with the next available
			# variable
			if len(lSort) > 0:
				var_info = lSort.pop(0)
				lGroups.append(GrpInfo(lVi=[var_info], lUni=[b for b in var_info.var.unique]) )

		# Order the variables in each group
		for grp in lGroups: grp.lVi.sort()

		# Print my sort groups
		if perr:
			perr("INFO: Running a %d stage sort...\n"%len(lGroups))
			for i in range(len(lGroups)):
				grp = lGroups[i]
				lTmp = []
				for j in range(len(grp.lUni)):
					if grp.lUni[j]: lTmp.append(g_sIdxNames[j])

				perr("INFO:   Stage %d in %s, sort tuple is:\n"%(i+1, ",".join(lTmp)))
				for vi in grp.lVi:
					perr("INFO:     %d %s\n"%(vi.nOrder, vi.var))


		# Setup identity indicies for axis that is not touched.
		# The indicies makes an array where the first index is the
		# dimension number.  For each dimension there is a sub array
		# of the same shape as 'dataset.shape', that gives the identity
		# index of an array value for fancy indexing.
		#
		#  So:
		#	  aIndices = numpy.indices(ary.shape)
		#
		#  Provides indexes such that this:
		#
		#    ary == ary[ aIndices[0], aIndices[1], aIndices[2] ]
		#
		# Is true


		# Make a list of all vars in dataset, we'll need this at least once
		lVars = self._allVars()
		aIdentOrig = None
		bMkIdentOrig = True

		# Sort each group. Groups are non-intersecting sets of indices.
		for grp in lGroups:

			# Single index sorts, these are straight forward
			if grp.lUni.count(True) == 1:

				if bMkIdentOrig:
					aIdentOrig = numpy.indices(self.shape)
					bMkIdentOrig = False

				lIdx = [aIdentOrig[i] for i in range(len(self.shape))]
				iSort = grp.lUni.index(True)

				# Single item in single index, these are real easy
				if len(grp.lVi) == 1:
					aSortMe = grp.lVi[0].var.array

				# Multiple items in a single index, need a record array
				else:
					lArrays = [ vi.var.array for vi in grp.lVi]
					lNames = [ vi.sName for vi in grp.lVi]
					aSortMe = numpy.rec.fromarrays(lArrays, names=lNames)

				# The actual sort
				lIdx[iSort] = numpy.argsort(aSortMe, kind="mergesort", axis=iSort)

				for var in lVars:
					var.array = var.array[tuple(lIdx)]


			# Multiple index sorts:
			else:

				# First determine our new shape, make sure all raveled indicies
				# are continuous can't have this:  False, True, True, False, True
				nSwitch = 0
				for i in range(1, len(self.shape)):
					if grp.lUni[i] != grp.lUni[i-1]: nSwitch += 1

				if nSwitch > 2:
					raise DatasetError(
						"Can't sort on variables that are unique in discontinuous"
						"index positions.  You'll need to use Pandas"
					)

				lReshape = []
				nRavel = 1
				bRaveling = False
				iSort = None
				for i in range(len(self.shape)):
					if grp.lUni[i]:
						if iSort == None:  iSort = i
						bRaveling = True
						nRavel *= self.shape[i]
					else:
						if bRaveling:
							lReshape.append(nRavel)
							bRaveling = False
						lReshape.append(self.shape[i])

				if bRaveling: lReshape.append(nRavel)

				if perr:
					perr("INFO: Reshaping for multi-index sort: %s -> %s\n"%(
					     list(self.shape), lReshape))

				# Make the identity array for this new shape
				aIdent = numpy.indices(lReshape)
				lIdx = [aIdent[i] for i in range(len(lReshape))]

				# Single item multi index.
				if len(grp.lVi) == 1:
					aReshaped = grp.lVi[0].var.array.reshape(lReshape)

				# The biggest difficulty, multi-items multi-indexes
				else:
					lArrays = [ vi.var.array for vi in grp.lVi]
					lNames = [ vi.sName for vi in grp.lVi]
					aReshaped = numpy.rec.fromarrays(lArrays, names=lNames).reshape(lReshape)

				# Issue a warning if duplicates are detected in multi-index
				# sorting arrays.  This usually means axes are going to get
				# mushed, which is typically not what people want!
				if not bShutup:
					lDupSlice = [slice(1)]*len(lReshape)
					lDupSlice[iSort] = slice(None)
					aDupTest = aReshaped[lDupSlice].squeeze()
					lDup = [item for item,count in Counter(aDupTest).items() if count > 1]
					if len(lDup) > 0:
						sys.stderr.write("WARNING: For dataset %s! Duplicate items detected in "
						                 "multi-index sort array. Your data may no "
											  "longer make sense!\n"%self.name)

				# The actual sort
				lIdx[iSort] = numpy.argsort(aReshaped, kind="mergesort", axis=iSort)

				for var in lVars:
					var.array = var.array.reshape(lReshape)[lIdx].reshape(self.shape)


	def ravel(self):
		"""Force internal arrays to be rank 1.

		If the internal arrays of a dataset are already rank 1, this is a no-op
		"""
		if len(self.shape) < 2:  return None

		bSet = True
		for sDim in self.keys():
			dDim = self[sDim]
			for sVar in dDim:
				dVar = dDim[sVar]
				dVar.array = dVar.array.ravel()
				dVar.unique = [True]
				#sys.stderr.write("DEBUG: raveled var: %s %s\n"%(str(dVar), dVar.array.shape))
				if bSet:
					self.shape = list(dVar.array.shape)
					self.shape = tuple(self.shape)
					bSet = False

		self._check_shape()


# ########################################################################### #
# das2C wrapper to high level interface conversion functions

def _mk_prop_from_raw(tProp):
	"""Make a property dictionary value given a :mod:_das3 property string

	Low level properties are the tuples:

	 (sType, sValue, sUnits, sSep, nMultiFlag)

	Conversions are as follows, anything with units becomes a quantity:
		- 'string'          -> str,  Quantity(str, units)
		- 'stringArray'     -> [str] Quantity([str], units)
		- 'bool'            -> True | False
		- 'boolArray'       -> [bool]
		- 'integer'         -> int,  Quantity(int, units)
		- 'intrange,array'  -> [int], Quantity([int], units)
		- 'realrange,array' -> [float], Quantity([float], units)
		- 'datetime'        -> datetime64(ns), Quantity(datetime64(ns), units)
		- 'dt range, array' -> [datetime64(ns)], Quantity([datetime64(ns)], units)
		
		- 'datumrange' -> Quantity (2 elements) ([float, float], units)
		
	The datatype strings are defined in the PropType element of das-basic-stream-v3.0.xsd
	which is authoritative but datatype strings from das-basic-stream-v2.2.xsd are also
	acceptable.

	Args:
		tProp (str, str): The first string is the data type as used in libdas2,
			the second string is the value.  The first string must be one of those
			listed above in Conversions.

	Returns: Object
		A python object representation of the given type an value stirings.
	"""

	#print("Checking: tProp[%s] = '%s'"%(key, prop))

	sType  = tProp[0].lower()
	sValue = tProp[1]
	sUnits = tProp[2]
	sSep   = tProp[3]
	nMulti = tProp[4]

	# Both vocabularies: das2.2 said 'boolean' and 'int', das3 says 'bool'
	# and 'integer'.  Range and array types carry the base type as a prefix.
	sBase = sType
	for sSuffix in ('array', 'range'):
		if sBase.endswith(sSuffix):
			sBase = sBase[:-len(sSuffix)]
	if sBase == 'boolean': sBase = 'bool'
	if sBase == 'int':     sBase = 'integer'
	if sBase == 'double':  sBase = 'real'

	# One item, a 'to' separated pair, or a separated list.  A list may end
	# with its terminator (das3 stringArrays often do), which is not an item.
	if nMulti == 1:
		lItems = [sValue]
	elif nMulti == 2:
		lItems = [t.strip() for t in sValue.split(' to ')]
	elif nMulti == 3:
		lItems = sValue.split(sSep) if sSep else sValue.split()
		lItems = [t.strip() for t in lItems]
		if lItems and lItems[-1] == '':
			lItems = lItems[:-1]
	else:
		raise ValueError("Unexpected property tuple from _das3, multiplicity = %d"%nMulti)

	def _one(sItem):
		if sBase == 'string':
			return sItem
		if sBase == 'bool':
			return sItem.lower() in ('true', '1', 'yes')
		if sBase == 'integer':
			return int(sItem)
		if sBase == 'real':
			return float(sItem)
		if sBase == 'datetime':
			# UTC (or nothing) is a calendar string; TT2000 is a count; any
			# other units are an epoch offset and stay a plain number
			if sUnits in ('', 'UTC', 'utc'):
				return numpy.datetime64(dastime.DasTime(sItem).isoc(9), 'ns')
			if sUnits == 'TT2000':
				t = _das3.tt2k_utc(int(sItem))
				return numpy.datetime64(dastime.DasTime(t).isoc(9), 'ns')
			return float(sItem)
		raise ValueError("Unknown property data type: %s in %s"%(sType, str(tProp)))

	lVals = [_one(t) for t in lItems]
	val = lVals[0] if nMulti == 1 else lVals

	# Anything with units is a Quantity; calendar datetimes always are, in
	# UTC, so they carry their units like every other quantity
	if sBase == 'datetime' and sUnits in ('', 'UTC', 'utc'):
		return Quantity(val, 'UTC')
	if sUnits == '':
		return val
	return Quantity(val, sUnits)

# #########################

def _mk_var_from_raw(dim, dRawDs, sRole, dRaw, bMask=False):
	"""Bind one raw variable dictionary to a Variable in dim.

	Returns the new Variable, or None when the raw variable is not backed by
	an array and so is not modeled here.
	"""
	sUnits = dRaw['units']

	# Only array backed variables are built here.  A computed variable
	# (reference + offset, a sequence, a constant) has no 'array' and is
	# skipped: the dimension makes its own center from reference and offset,
	# and the other generators are not modeled on the python side yet.
	sName = dRaw['array']
	if sName is None:
		return None

	array = dRawDs['arrays'][sName]

	# If I'm supposed to mask fill values do so (unless it's already been done)
	# note this modifies dRawDs
	fill = None
	if bMask and not isinstance(array, numpy.ma.MaskedArray):
		fill = dRawDs['fill'][sName]

		if array.dtype.name.startswith('timedelta64'):
			fill = numpy.timedelta64(fill, 'ns')
		try:
			# The default tollerance values for isclose must be scaled when fill is
			# a small value (especially 0)
			if fill == 0.0: abs_toller=0.0  # default doesn't work if fill is 0
			else: abs_toller=1e-08          # numpy default

			dRawDs['arrays'][sName] = numpy.ma.masked_values(
				array, fill, atol=abs_toller, copy=False
			)
		except TypeError as e:
			raise DatasetError(
				"array: %s, dimension: %s, fill: %s, msg: %s"%(
				sName, dim.name, fill, str(e)))

	array = dRawDs['arrays'][sName]

	# The dataset index that feeds the array's first index is where this
	# variable's values start; earlier dataset indices are degenerate.  A
	# constant maps nothing and starts at zero like anything else.
	lMap = dRaw['idxmap']
	nAxis = lMap.index(0) if 0 in lMap else 0

	# Array indices past the mapped ones are internal to one value
	nMapped = sum(1 for i in lMap if i is not None)
	nSubRank = len(array.shape) - nMapped

	return dim.var(sRole, array, sUnits, axis=nAxis, fill=fill, subrank=nSubRank)

# #########################

def _init_dim_from_raw(dim, dRawDs, dRawDim, bMask=False):

	# The raw data sets through variables in with type and property keys since
	# there are only a handful of variable roles.  We have to filter these out

	for sVar in dRawDim:
		if sVar == 'type':
			continue
		elif sVar == 'props':
			dRawProps = dRawDim['props']
			for sProp in dRawProps:
				dim.props[sProp] = _mk_prop_from_raw(dRawProps[sProp])
		else:
			dRaw = dRawDim[sVar]
			sRole = dRaw['role'].lower()

			# mask fill values in data arrays
			var = _mk_var_from_raw(dim, dRawDs, sRole, dRaw, bMask)

			# None when the expression is reference + offset, the dimension
			# makes that center variable itself and it has no formalism
			if var is not None:
				var.ops    = dRaw.get('ops')
				var.labels = dRaw.get('labels')

# #########################

def _ds_from_raw(dRawDs):
	"""Create a Dataset from a set of nested dictionaries.

	The low-level _das3 madule returns datasets created by libdas2 in the form
	of a list of nested dictionaries.  This function creates a Dataset object
	and all it's sub-objects given a nested dictionary from _das3.read_file,
	_das3.read_cmd, or _das3.read_server.
	"""

	ds = Dataset(dRawDs['id'], dRawDs['group'])

	for sProp in dRawDs['props']:
		ds.props[sProp] = _mk_prop_from_raw(dRawDs['props'][sProp])

	ds.shape = dRawDs['shape']

	for sDim in dRawDs['data']:
		dRawDim = dRawDs['data'][sDim]

		dim = ds.data(sDim)
		_init_dim_from_raw(dim, dRawDs, dRawDim, True) # Data arrays mask fill

	for sDim in dRawDs['coords']:
		dRawDim = dRawDs['coords'][sDim]

		dim = ds.coord(sDim)
		_init_dim_from_raw(dim, dRawDs, dRawDim, False) # Coord arrays don't have fill

	return ds

# ############################################################################ #
# Dataset utilities

def ds_strip_empty(lDatasets):
	"""Strip empty datasets from a list of datasets

	Args:
		lDatasets (list) : A list of Dataset Objects or None

	Returns: list
		Returns a list object containing all datasets that contained at least
		a single coordinate or data point.  If the given list contains only
		empty datasets (or is null) then an empty list object is returned.
	"""

	lOut = []
	if lDatasets == None: return lOut

	for ds in lDatasets:
		#sys.stderr.write("Shape of ds %s is %s\n"%(ds.name, ds.shape))
		for n in ds.shape:
			if n > 0:
				lOut.append(ds)
				break

	return lOut


def ds_union(lDs, bAllowRankReduce=True):
	"""Concatenate a list of datasets from the same group into a single
	dataset.

	If the input arrays do not have the same number of axes or the
	shape in axis 1 and all higher axes are not the same, the data will be
	joined as scatter data and the rank of the resulting dataset will be 1.

	Args:
		lDs (list) : A list of datasets which must have the same physical
			dimensions and variables, but not the same shape in index space.

		bAllowRankReduce (boolean, optional) : If False, arrays may not be
			concatenated via rank reduction.   If reshaping is required to
			create the union dataset and exception will be thrown instead.

	Returns:
		Dataset : A new dataset consisting of a union of all the provided
		datasets is returned.  If only one dataset is provided it is returned
		un-altered.

	Rasies:
		DatasetError: If the datasets do not have the same physical dimensions
			and the same variables.  Optionally the same shape is required as
			well.

	"""
	if len(lDs) == 0: raise ValueError("No datasets in group")
	if len(lDs) == 1: return lDs[0]

	ds0 = lDs[0]

	dsOut = Dataset(ds0.group if ds0.group else 'merged', group=ds0.group)

	# Add all the properties from all the groups
	dsOut.props = ds0.props.copy()
	for ds in lDs[1:]: dsOut.props.update(ds.props)

	bFlatten = False

	# Make sure the datasets have the same shape and units:
	for ds in lDs[1:]:

		if len(ds.shape) != len(ds0.shape): bFlatten = True
		else:
			for iAx in range(1, len(ds.shape)):
				if ds.shape[iAx] != ds0.shape[iAx]: bFlatten = True

		if bFlatten and (not bAllowRankReduce):
				raise DatasetError(
					"Rank Reduction prohibited, can not merging dataset shape"
					" %s with dataset shape %s"%(ds0.shape, ds.shape))

		if ds.keys() != ds0.keys():
			raise DatasetError("Incompatable dimensions, %s vs %s"%(
			                 list(ds.keys()), list(ds0.keys())))

		for sDim in ds:
			if ds0[sDim].keys() != ds[sDim].keys():
				raise DatasetError("Incompatable variables, %s vs %s"%(
			                 list(ds[sDim].keys()), list(ds0[sDim].keys())))

			for sVar in ds[sDim]:
				if ds0[sDim][sVar].units != ds[sDim][sVar].units:
					raise DatasetError("Incompatable units for %s:%s: %s vs %s"%(
					                 sDim, sVar, ds0[sDim][sVar].units,
										  ds[sDim][sVar].units))


	# Merge all the property dictionaries
	for sDim in ds0:
		dimOut = dsOut.dim(sDim)

		dimOut.props = ds0[sDim].props.copy()

		for ds in lDs[1:]:
			dimOut.props.update(ds[sDim].props)


	# Merge all the arrays
	for sDim in ds0:
		dimOut = dsOut[sDim]

		for sVar in ds0[sDim]:

			if bFlatten:
				lArys = [ds[sDim][sVar].array.ravel() for ds in lDs]
			else:
				lArys = [ds[sDim][sVar].array for ds in lDs]

			aOut = numpy.concatenate(lArys, axis=0)

			sUnits = ds0[sDim][sVar].units

			dsOut[sDim].var(sVar, aOut, sUnits)

	return dsOut

