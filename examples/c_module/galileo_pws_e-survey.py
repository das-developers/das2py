#!/usr/bin/env python2

import sys
import matplotlib.pyplot as plot
import numpy as N
import das2


##############################################################################
def getArrayAndUnits(ds, sDimType, sDim, sVar):
	"""Helper function to get the numpy arrays for a variable since das2 higher
	level module is not complete"""

	if sDimType not in ('coords','data'):
		raise ValueError("Dimension type: '"+sDimType+"', expected 'coords' or 'data")
	
	dDims = ds[sDimType]
	
	if sDim not in dDims:
		raise ValueError("%s not present among the %s dimensions of %s"%(
		                 sDim, sType, ds['id']))
		
	# If the center variable is not present, we could fake it with min, max,
	# width etc.  For this example just look for actual center variables.
	dVars = dDims[sDim]
	
	
	if sVar not in dVars:
		raise ValueError("Variable %s not present in %s -> %s -> %s"%(
		                 ds['id'], sDimType, sDim))
	
	# the element 'props' always contains the dimension properties such as
	# labels, etc.  It's never associated with an array
	if sVar == 'props':
		raise ValueError("'props' is list of dimension properites, not a variable")

	# Read the expression and find out which array is in use, note that
	# variables based on operations on other variables are not supported in
	# this simple interface.
	sExp = ds[sDimType][sDim][sVar]['expression']
	
	# Hack alert, I should be using regex, hide your eyes!
	sExp = sExp[0:sExp.find('|')].strip()
	n = sExp.rfind(']')
	sUnits = sExp[n+1:].strip()
	sAry = sExp[:n]
	sAry = sAry[:sAry.find('[')]
	
	if sAry not in ds['arrays']:
		raise ValueError("Array '%s' not included in dataset '%s'"%(sAry, ds['id']))
		
	a = ds['arrays'][sAry]
	
	return (a, sUnits)	
	

##############################################################################

def main(argv):
	"""Annotated example of using libdas2 and matplotlib to gather and plot
	a day's worth of Galileo PWS electric spectrum data using the low-level
	interface.  The das2 python module consist of a low-level C-module, _das2
	and a higher level module that acts in a more pythonic way, das2.  The
	higher level module is under construction and is thus ignored here.
	"""
	
	# Download a das2 Galileo PWS dynamic electric spectrum stream.  We're
	# downloading Galileo data since it's open and will not prompt for a
	# password.  
	
	# Also, to demonstrate one of the features of the library we are 
	# intentionally asking the wrong server for galileo data.  Since the server
	# planet knows where galileo data are it issues a redirect, which libdas2
	# follows.
	sUrl = 'http://planet.physics.uiowa.edu/das/das2Server?server=dataset&'+\
	       'dataset=Galileo/PWS/Survey_Electric&start_time=2001-001&' +\
	       'end_time=2001-002&resolution=60'
	
	print("Reading Galileo PWS spectra for 2001-001 at intrinsic resolution")
	lDs = das2._das2.read_server(sUrl)
	print("%d correlated dataset(s) downloaded\n"%len(lDs))
	
	# Here's how this will work in the near future
	# 
	# sUri = 'tag:das2.org,2012:site:/uiowa/Galileo/PWS/Survey_Electric'
	# source = das2.DataSource(sUri)
	# lDs = source.request(time=['2001-001','2001-002',60])
	# ds = lDs[0]
	# 
	# aTime = ds.coord.time['center']
	# aFreq = ds.coord.freq['center']
	# aPower  = ds.data.electric['center']
	#
	# sTitle = ds.props['title']
	# sXlabel = ds.coords.time.props['label']
	# sYlabel = ds.coords.freq.props['label']
	# sZlabel = ds.data.electric.props['label']
	
	
	# So what did we get?  The low-level interface just returns a list of 
	# dataset objects, which are just dictionaries.  A higher level interface
	# using a python class is in the works but does not exist at this time so
	# we're going to have to interact with the low-level object directly. 
	#
	# The low-level output always has the same morphology:
	# 
	# list_of_datasets (1)
	# |
	# |- Dataset (1 - N)
	#   |
	#   |- Properties  (0 - N)
	#   |
	#   |- Arrays      (1 - N)
	#   |
	#   |- Dimensions  (1 - N)
	#       |
	#       |- Properties (0 - N)
	#       |
	#       |- Variables  (1 - N)
	#
	# If a person knows what they want, they can skip the Dimension and 
	# Variable objects all together, but they are needed to support machine-
	# readable understanding of the dataset as Variables define lookup
	# functions for arrays that may include uniary and binary operation
	# trees in addition to index maps.
	
	
	# Galileo spectra are always a single mode (the frequency table doesn't
	# change) so we know up front that there will only be one dataset in the
	# list.
	ds = lDs[0]
	
	# The info element contains a string overview of the dataset
	print(ds['info'])
	
	# The rank element contains the overall iteration rank of the dataset
	# note that unlike ISTP-CDF this has nothing to do with the number of
	# physical dimensions spanned by the values.  Though we won't be working 
	# with Variables directly in this example, all Variablse in a Dataset
	# take the same set of indicies.  Typically time values are degenerate in
	# the second index and frequency values are degenerate in the first index.
	# Data values typically are not degenerate.
	print("Iteration rank is: %s"%ds['rank'])
	
	# Let's list the physical coordinate dimensions of the dataset
	sCoords = ', '.join(ds['coords'].keys())
	print("Data are located in physical dimensions:", sCoords)
	
	# Let's list the physical data dimensions of the dataset
	sData = ', '.join(ds['data'].keys())
	print("Data are defined in the physical dimensions:", sData)
	
	# Each physical dimension has 1-N variables that locate values in that
	# dimension.  Each variable that happens to be based on an array 
	# (virtual variables exist as well and are important for reducing
	# network overhead) provides a mapping between overall dataset indices
	# to array indices.  The purpose (or role) of each variable is defined
	# by it's name.  Other names are possible, but here are the built-in
	# Variable names that higher level code will know how to interpret:
	#
	#  center - Absolute point in a dimension, center of bin 
	#
	#  min    - Absolute point in a dimension, start of bin
	#
	#  max    - Absolute point in a dimension, end of bin
	#
	#  width  - Difference value in a dimesion, width of bin
	#
	#  mean   - Absolute point in a dimension, average value in a bin
	#
	#  mode   - Absolute point in a dimension, most frequent value in a bin
	#
	#  reference - Same as 'min' but is usually paired with 'offset'
	#
	#  offset - Difference value in dimenision, to be added to reference,
	#            very handy for waveforms where start time and offsets
	#            should be denoted separately for automatic power spectral
	#            density calculations.
	#
	#  max_error - Absolute point in a dimension, denotes uncertianty
	#
	#  min_error - Absolute point in a dimension, denotes uncertianty 
	#
	#  uncertianty - Difference value in a dimension, denotes uncertianty
	#            assumed to be centered on 'center'
	#
	#  std_dev - Standard deviation of values in a bin, does *not* have
	#            the same absolute or difference units as the center
	#            values.
	#
	#  point_spread - A sub-iteration array of difference values from
	#            a reference point.
	#
	#  weight - An sub-iteration array of weights for a point_spread
	#   
	# Not all of these are supplied in each dateset, in fact most of 
	# them aren't.  Typically only the center Variable is supplied.
	
	# Lets get the data arrays for the center Variables and totally
	# ignore the index map
	(aY, unitsY) = getArrayAndUnits(ds, 'coords', 'frequency', 'center')
	(aZ, unitsZ) = getArrayAndUnits(ds, 'data',  'electric', 'center')
	
	# Right now we're still stuck with the transmitted us2000 time units,
	# will be able to have these converted-on-read in the future.
	(aX, unitsX) = getArrayAndUnits(ds, 'coords', 'time', 'center')
	
	# This will convert the time units to python datetime, but those don't
	# seem to work for matplotlib
	#aXfixed = N.array( [das2.DasTime(t, unitsX).pyDateTime() for t in aX] )
	
	aY = N.log10(aY)
	aZ = N.log10(aZ.transpose())
	plot.pcolor(aX, aY, aZ, cmap='jet')
	plot.axis([aX.min(), aX.max(), aY.min(), aY.max()])
	cbar = plot.colorbar()
	cbar.set_label("log(%s)"%unitsZ)
	plot.xlabel(unitsX)
	plot.ylabel("log(%s)"%unitsY)
	plot.title(ds['props']['title'][1])
	plot.show()


if __name__ == '__main__':
	sys.exit(main(sys.argv))
