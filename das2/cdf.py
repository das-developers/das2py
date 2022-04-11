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


"""Helpers for CDF output"""

import sys
import numpy
import datetime
import os
import _das2

from . dataset import *

try:
	import spacepy.pycdf as pycdf
except ImportError:
	# If spacepy is not installed, use the embedded copy
	import das2.pycdf as pycdf

perr = sys.stderr.write

# ########################################################################## #
def _writeVar(cdf, var):
	#Write a single variable to the CDF object.
	
	# Get the set of indicies used by this variable
	lIdx = [i for i in range(len(var.unique)) if var.unique[i]]
	
	if var.name in ('center','mean','median','mode'): sName = var.dim.name
	else: 
		# Interaction Warning:  If the CDF name generation algorithm is changed
		# then the code in _varAttrs that attaches DELTA_PLUS/MINUS_VAR 
		# will have to be updated
		sName = "%s_%s"%(var.dim.name, var.name)
		
	bRecVary = (0 in lIdx)
	
	data = var.array[var.uniIndex()]
	
	if numpy.issubdtype(data.dtype, numpy.datetime64):
		
		# Hack in datetime64 to TT2000 convertions since pyCDF doesn't know 
		# how to handle that type
		if len(data.shape) > 1:
			raise NotImplementedError(
				"Multi-dimensional (%s) timestamp conversion not yet implemented"%list(data.shape)
			)
		
		lPyDt = [datetime.datetime.utcfromtimestamp(n/1e9) for n in data.astype('int64')]
		
		# Save as TT2000
		data = [pycdf.lib.datetime_to_tt2000(dt) for dt in lPyDt]
		sUnits = 'ns'
		sName = 'Epoch'
		nType = pycdf.const.CDF_TIME_TT2000
	else:
	
		# CDF expects min and max to be offsets from primary so re-write
		# the data values
		if (var.name == 'max') and ('center' in var.dim.vars):
			array = var.array - var.dim.vars['center']
			data = array[var.uniIndex()]
		elif (var.name == 'min') and ('center' in var.dim.vars):
			array = var.dim.vars['center'] - var.array
			data = array[var.uniIndex()]
	
		if (var.units == "") or (var.units == " "): sUnits = " "
		else: sUnits = var.units
		nType = None
	
	dims = [var.dim.ds.shape[i] for i in lIdx if i != 0]
	bVary = (0 in lIdx)
	
	zVar = cdf.new(sName, data=data, type=nType, dims=dims, recVary=bVary)
	zVar.attrs['UNITS'] = sUnits #.replace("**","^")
	zVar.attrs['FIELDNAM'] = sName
	
	# Extra items expected for Epoch variables
	if numpy.issubdtype(var.array.dtype, numpy.datetime64):
		zVar.attrs['TIME_BASE'] = 'J2000'
		zVar.attrs['TIME_SCALE'] = 'TT'
		
	return (sName, "%s:%s"%(var.dim.name, var.name), lIdx)
	
# ########################################################################## #

g_dPropTrans = {
	'summary': 'CATDESC',  'description':'VAR_NOTES', 
	'fill':    'FILLVAL',  'scaletype':  'SCALETYP',
	'validmin':'VALIDMIN', 'validmax':   'VALIDMAX',
	'label':   'LABLAXIS',  
	# Use Autoplot properties, there aren't any ISTP props for these
	'tagWidth':'CADENCE',  'cacheRange': 'CACHE_TAG'
}

g_lSkip = ['range', 'tagwidth', 'cacherange']

def _varAttrs(zVar, var, sType='c'):

	# Set the variable properties, all vars should have:
	# CATDESC, DEPEND_*, FIELDNAM, FILLVAL, FORMAT, 
	# UNITS, VALIDMIN, VALIDMAX
	
	if sType == 'c': 
		zVar.attrs['VAR_TYPE'] = 'support_data'
	else:
		if var.name in ('center','reference','offset','mean','median','mode'):
			zVar.attrs['VAR_TYPE'] = 'data'
		else:
			zVar.attrs['VAR_TYPE'] = 'support_data'
			
		if var.fill != None: 
			zVar.attrs['FILLVAL'] = var.fill
		elif 'fill' in var.dim.props:
			zVar.attrs['FILLVAL'] = var.dim.props['fill']
					
	# If this is a main variable (reference, center, mean, median, mode)
	# let it use the properties from the dimension
	if var.name in ('reference', 'center', 'mean', 'median', 'mode'):
		for sProp in var.dim.props:
			if sProp.lower() in g_lSkip: continue
			
			if sProp.lower() in g_dPropTrans: 
				sCProp = g_dPropTrans[sProp.lower()]
			else:
				sCProp = sProp
			
			zVar.attrs[sCProp] = var.dim.props[sProp]
		
		# CDF folds together the concepts of min, max and max_error, min_error
		# into the same metadat value.  Take min and max first if available
		for sRole in ('min','min_error','uncertianty','std_dev'):
			if sRole in var.dim.vars:
				zVar.attrs['DELTA_MINUS_VAR'] = var.dim.name + "_" + sRole
				break
				
		for sRole in ('max','max_error','uncertianty','std_dev'):
			if sRole in var.dim.vars:
				zVar.attrs['DELTA_PLUS_VAR'] = var.dim.name + "_" + sRole
				break
			
	# If this variable doesn't have a CATDESC, make one up.
	if 'CATDESC' not in zVar.attrs:
		zVar.attrs['CATDESC'] = "%s%s %s%s"%(
			var.dim.name[0].upper(), var.dim.name[1:],
			var.name[0].upper(), var.name[1:]
		)
		
	# Handle the Datum values, range and tagwidth
	if 'range' in var.dim.props:
		prop = var.dim.props['range']
		if isinstance(prop, Quantity):
			if len(prop.value) > 0:
				rMin = _das2.convert(prop.value[0], prop.unit, var.units)
				zVar.attrs['SCALEMIN'] = rMin
			if len(prop.value) > 1:
				rMax = _das2.convert(prop.value[1], prop.unit, var.units)
				zVar.attrs['SCALEMAX'] = rMax
		else:
			perr("WARNING: Property %s:%s -> 'range' is not of type Quantity"%(
					var.dim.name, var.name))
	
	for sProp in ('tagWidth','cacheRange'):
		if sProp in var.dim.props:
			zVar.attrs[ g_dPropTrans[sProp] ] = str(var.dim.props[sProp])
	
	

# ########################################################################## #
def _writeDim(cdf, dim, bCoord):
	#Writes a single dimension's data variables to the CDF object
	#
	# Args:
	#	cdf (pycdf.CDF) - The CDF object
	#	dim (Dimension) - A Dataset dimension
	#	bCoord (bool) - If True this is a support dimension
	

	if bCoord: sType = 'c'
	else: sType = 'd'

	# Find the main variable for this dimension.  The main may be split
	# between a reference and offset.  
	
	# The following is really hokey as there is no generic way to handle
	# reference + offset in CDF *except* for time values (and that is 
	# one heck of a kludge).  So in general we want the centers, except
	# for time where the kludge is available
	
	
	bIgnoreCenter = False
	if dim.name.lower() == 'time' and (('reference' in dim) and ('offset' in dim)):
		bIgnoreCenter = True
	
	lCreated = []
	for sVar in dim:
		var = dim[sVar]
		
		if bIgnoreCenter:
			if var.name == 'center': continue
		else:
			if var.name in ('reference', 'offset'): continue
	
		(sCdfName, sDsName, lIdx) = _writeVar(cdf, var)
		
		_varAttrs(cdf[sCdfName], var, sType)
				
		lCreated.append( (sCdfName, sDsName, lIdx, sType) )
	
		
	# If ignore center was set, that means the Epoch times are actually
	# start points and need to be marked as such
	for t in lCreated:
		if t[0] == 'Epoch':
			if bIgnoreCenter: cdf['Epoch'].attrs['BIN_LOCATION'] = 0.0
			else: cdf['Epoch'].attrs['BIN_LOCATION'] = 0.5
			break
			
	return lCreated

# ########################################################################## #

def _center(s):
	if s.find('center') > -1: return True
	if s.find('median') > -1: return True
	if s.find('mode') > -1: return True
	if s.find('mean') > -1: return True
	return False
	
def _notTime(s):
	if s.lower().find('time') > -1: return False
	return True

def _solve_depends(ds, cdf, lIdxMap):

	nRank = len(ds.shape)

	# Get the dependencies...
	llDeps = [[] for i in range(nRank)]
	
	# Gather all possible candidates for each index using in the highest level
	# index the variable depends on.
	for iDim in range(nRank):
		for sCdfName, sDsName, lIdx, sType in lIdxMap:
			if sType == 'd': continue
			
			if lIdx[-1] == iDim: llDeps[iDim].append( (sCdfName, sDsName, lIdx, sType) )
	
	
	# Since ISTP can't have more than one depend per index reduce any cases 
	# where there are more than one.
	
	for iDim in range(nRank):
		lDeps = llDeps[iDim]
		if len(lDeps) == 0:
			perr("WARNING: Can't find a coordinate value that depends on axis %d alone"%iDim)
		elif len(lDeps) == 1:
			continue
		else:
			# This is a data relationship that ISTP was not created to handle,
			# multiple variables can tag this axis.  This is because ISTP locks
			# together the concept of array dimensions and physical dimensions.
			# It's what makes scatter data incompatable with ISTP metadata (but
			# not CDFs in general). Solve the problem by just choosing one.

			# if there's only one center item use it
			lTmp = [ i for i in range(len(lDeps)) if _center(lDeps[i][1])]
			if len(lTmp) == 1:
				llDeps[iDim] = [ lDeps[lTmp[0]] ]
				continue
			
			# if one of the items is a time:offset, throw it out since we already
			# have an epoch time.
			lTmp = [ i for i in range(len(lDeps)) if _notTime(lDeps[i][1])]
			if len(lTmp) == 1:
				llDeps[iDim] = [ lDeps[lTmp[0]] ]
				continue
			
			# Just take the first one alphabetically
			lDeps.sort()
			llDeps[iDim] = [ lDeps[0] ]
	
	# Since each member of llDeps is now only one item long, collapse the lists
	lDeps = [l[0] for l in llDeps]
	
	# Okay we should have at most one dependency for each item assign them
	for iDim in range(nRank):
		for sCdfName, sDsName, lIdx, sType in lIdxMap:
			
			if iDim not in lIdx: continue  # Variable dosen't depend on this index
			
			if sDsName == lDeps[iDim][1]: continue
			
			# I depend on this index, but I might not depend on all previous indices
			# back down the index number by the value of my first index dependence.
			iDep = iDim - lIdx[0]
			
			cdf[sCdfName].attrs['DEPEND_%d'%iDep] = lDeps[iDim][0]
			
		


# ########################################################################## #
def write(ds, path, src=None, derived=False):
	"""Write a das2 Dataset to a CDF file.

	The return value of this function must be closed by the caller for example::

		import das2.cdf
		cdf = das2.cdf.write(dataset, 'my_path.cdf')
		cdf.close()

	This function calls pycdf.lib.set_backward(backward=false) internally.
	To save other CDF files in a backwards compatible fashion calling code will
	need to reset the backwards compatability flag of the library.

	Args:
		ds (Dataset) : The dataset to write to the output file
		
		path (str) : The name of the file to write, can include directories
		
		src (Source, list, optional) : The Source objects from which data for
			this dataset were retreived.  Maybe None, a single source or
			multiple sources.  The ID values of these sources will be copied
			into the global CDF metadata if present.
		
		derived (bool, optional) : If true indicates that these data have
		   been processed after delivery via the Source object listed above
		

	Returns:
		The created CDF object which must be closed by the caller.

	Raises:
		ValueError:
			If the given Dataset cannot be represented in the ISTP metadata
			model and the parameter istp is True (the default).
	"""

	if os.path.isfile(path): os.remove(path)

	# Write the data
	pycdf.lib.set_backward(backward=False)
	cdf = pycdf.CDF(path, '')

	# This is a list of dependencies provided by each dimension
	# Each item is ds rank in length, and contains the sub items
	#
	#  [  (cdf_var, ds_var, lIdxUsed, 'c'/'d'),  
	#     (cdf_var, ds_var, lIdxUsed, 'c'/'d'), 
	#     ...  
	#  ]
	lIdxMap = []
	lDims = list(ds.dCoord.keys())
	lDims.sort()
	for sDim in lDims:
		lIdxMap += _writeDim(cdf, ds.dCoord[sDim], True)
		
	lDims = list(ds.dData.keys())
	lDims.sort()
	for sDim in lDims:
		lIdxMap += _writeDim(cdf, ds.dData[sDim], False)

	_solve_depends(ds, cdf, lIdxMap)
	
	# If we have an epoch variable see if it's data are monotonic.
	if 'Epoch' in cdf:
		bMono = numpy.all(cdf['Epoch'][1:] >= cdf['Epoch'][:-1])
		if bMono: cdf['Epoch'].attrs['MONOTON'] = 'INCREASE'
	
	
	# Set the display type for each data variable:
	for tMap in lIdxMap:
		if tMap[3] != 'd': continue
		
		zVar = cdf[tMap[0]]
		lIdx = tMap[2]
		
		sDisplay = 'time_series'
		
		if len(lIdx) == 1:
			if 'Epoch' not in cdf: sDisplay = 'series'
		
		elif len(lIdx) == 2:
			sDisplay = 'spectrogram'
			# If the depend 1 of a data variable is a time:offset, set the
			# display type to waveform
			if ('DEPEND_1' in zVar.attrs) and ('DEPEND_0' in zVar.attrs):
				z0 = cdf[ zVar.attrs['DEPEND_0'] ]
				z1 = cdf[ zVar.attrs['DEPEND_1'] ]
				
				if pycdf.const.CDF_TIME_TT2000 == z0.type():
					if das2._das2.convertable(z1.attrs['UNITS'], 's'):
						sDisplay = 'waveform'		
			
		else:
			sDisplay = 'stack_plot'
		
		zVar.attrs['DISPLAY_TYPE'] = sDisplay
		
	# Write dataset level properties into the CDF
	for sProp in ds.props:
		cdf.attrs[sProp] = str(ds.props[sProp])
	
	# Add in das2 stuff
	sPathKey = "SourcePathURI"
	sUriKey = "SourceURI"
	if derived:
		sPathKey = "ResourcePathURI"
		sUriKey  = "ResourceURI"
		
	
	if src != None:
		if isinstance(src, (list,tuple)):
			cdf.attrs[sPathKey] = [item.path for item in src]
			#cdf.attrs['das2_ResourceURL'] = [item.url for item in src]
			lURIs = []
			for item in src:
				if 'uris' in item.props: lURIs += item.props['uris']
					
			if len(lURIs) > 0: cdf.attrs[sUriKey] = lURIs
		else:
			cdf.attrs[sPathKey] = [src.path]
			#cdf.attrs['das2_ResourceURL'] = [src.url]
			if 'uris' in src.props:
				cdf.attrs[sUriKey] = src.props['uris']
		
	return cdf

