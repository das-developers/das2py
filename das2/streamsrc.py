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


"""This module provides functions for interacting with HTTP GET services
that provide a data stream.
"""
import sys
import json
import _das2
from . dastime import DasTime
from . node import Node
from . source import Source
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

class HttpStreamSrc(Source):
	"""HttpStreamSrc source: Provides access to HTTP GET based data sources

	An example of typical usage of this class would be::

		sId = 'site:/voparis/nancay/nda/junon/junon_tag1_lh/das2'
		src = das2.get_source(sId)
		dQuery = {'time':('2017-07-01T17:14:00','2017-07-01T17:15:00',0.03)}
		lDs = src.get(dQuery)
		print(lDs[0])
	"""

	# ####################################################################### #
	def __init__(self, dDef, bStub, bGlobal):
		"""Constructor is not intended for direct use, use

			das2.get_node()
			das2.get_source()

		instead."""

		if ('type' not in dDef) or (dDef['type'] != 'HttpStreamSrc'):
			raise CatalogError("PyClass, data mismatch, expected 'type' to be "+\
			                   "'HttpStreamSrc' not '%s'"%dDef)

		super(HttpStreamSrc, self).__init__(dDef, bStub, bGlobal)

		self.lBadBase = []

	# ####################################################################### #
	def load(self):
		# Extra intialization on load.  Copy descriptions up to aspects if not
		# present.  This is done so that parts of the coordinate and data
		# properties dictionaries can just be handed off.

		super(HttpStreamSrc, self).load()

	
	# ####################################################################### #
	# Get example
	def examples(self):
		"""List the example datasets available for this source
		
		The names returned by this function may be used to get example datasets.
		All valid das2 and hapi data sources should contain at least one example.
		
		Returns:
			list of 2-tuples, (name, description), which contain the names and
			description (if any) of example datasets.  The description may be
			None
		"""
		if self.bStub: self.load()
		
		if 'protocol' not in self.props:
			return []
		
		if 'examples' not in self.props['protocol']:
			return []
			
		dExamples = self.props['protocol']['examples']
		
		lEx = list(dExamples.keys())
		lEx.sort()
		lOut = []
		for sEx in lEx:
			dEx = dExamples[sEx]
			sDesc = None
			if 'title' in dEx: 
				sDesc = dEx['title']
			else:
				dParams = dEx['http_params']
				
				# As a courtousey to under-documented hapi and das2 sources
				# try to make up a description using the parameters.  I don't
				# like doing this because it's das2 and hapi specific code. -cwp
				
				if ('start_time' in dParams) and ('end_time' in dParams):
					if 'resolution' in dParams:
						sDesc = "Data from %s to %s @ %s second resolution or better"%(
						   dParams['start_time'], dParams['end_time'], 
						   dParams['resolution']
						)
						
					elif 'interval' in dParams:
						sDesc = "Data from %s to %s @ %s second intervals"%(
							dParams['start_time'], dParams['end_time'], 
						   dParams['interval']
						)
					else:
						sDesc = "Data from %s to %s"%(
						   dParams['start_time'], dParams['end_time']
						)
				
				elif ('time.min' in dParams) and ('time.max' in dParams):
					sDesc = "Data from %s to %s"%(
					   dParams['time.min'], dParams['time.max']
					)
			
			lOut.append( (sEx, sDesc) )	
			
		return lOut
		
	# ####################################################################### #
	def _getExample(self, sName=None):
		
		if self.bStub: self.load()
		
		if 'protocol' not in self.props:
			s = self.props['_url']
			raise DatasetError('Source from %s is missing protocol section'%s)
			
		if 'examples' not in self.props['protocol']:
			s = self.props['_url']
			raise DatasetError('Source from %s is missing protocol:examples section'%s)
		
		
		dExamples = self.props['protocol']['examples'] 
		# If no name is given, just provide the last one in sort order.
		# Usually newer examples are more interesting.  Can change this to 
		# first example if that's what folks prefer.  The API doesn't specify
		# which one so it's implementation dependent. -cwp
		lEx = list(dExamples.keys())
		lEx.sort()
		sName = lEx[-1]
		
		if sName not in dExamples:
			s = self.props['_url']
			raise ValueError("Source from %s has no example named %s"%(s, sName))
		
		dEx = dExamples[sName]
		dQuery = dEx['http_params']
		
		return self.protoGet(dQuery)
		

	# ####################################################################### #
	# param      req value         units  title
	# ---------- --- ------------  -----  ------------------------------------------------------
	# ascii       F  boolean              Insure stream output is readable as UTF-8 text
	# end_time    T  isotime       UTC    Maximum Time Value to stream
	# params      F  flags," "            Optional reader arguments
	#                "--10khz"            Output only 27.8 kHz sample rate (10 kHz rolloff) data
	#                "--80khz"            Output only 222 kHz sample rate (80 kHz rolloff) data
	#                "--Ex=false"         Do not output the Ex Antenna
	#                "--Ew=false"         Do not output the Ew Antenna
	# resolution  F  real          s      Maximum resolution between output time points
	# start_time  T  isotime       UTC    Minimum time value to stream
	def protoInfo(self):
		"""Pretty print information on the HTTP GET parameters supported by this
		HttpStreamSrc object.

		It is possible for a single static file to provide all data for a source.
		An example would be a static data coverage file at a given resolution.  In
		this case the empty string will be returned.

		Returns:
			str : A string description of the get parameters suitable for printing
				which may be empty if the source has no get parameters.
		"""
		if self.bStub: self.load()
		
		if 'protocol' not in self.props: return ""
		
		if 'http_params' not in self.props['protocol']: return ""
		
		dParams = self.props['protocol']['http_params']

		lKeys = list(dParams.keys())
		lKeys.sort()

		lOut = []
		for sKey in lKeys:
			dIn = dParams[sKey]
			dOut = {'param':sKey, 'level':1}
			if ('required' in dIn) and (dIn['required'] == True):
				dOut['req'] = 'T'
			else:
				dOut['req'] = 'F'
			if 'type' in dIn:
				if dIn['type'] == 'flag_set':
					sSep = " "
					if 'flag_sep' in dIn: sSep = dIn['flag_sep']
					dOut['value'] = 'flags,"%s"'%sSep

				elif dIn['type'] == 'enum':
					dOut['value'] = 'enum'

				else:
					dOut['value'] = dIn['type']
			else:
				dOut['value'] = ""

			if 'units' in dIn: dOut['units'] = dIn['units']
			elif dOut['value'] == 'isotime': dOut['units'] = "UTC"
			else: dOut['units'] = ""

			if 'title' in dIn:  dOut['title'] = dIn['title']
			elif 'name' in dIn: dOut['title'] = dIn['name']
			else: dOut['title'] = ""

			lOut.append(dOut)

			# Now to loop through all the flag set values
			if ('type' in dIn) and (dIn['type'] == 'flag_set') and \
			   ('flags' in dIn):
				dFlags = dIn['flags']

				lFlKey = list(dFlags.keys())
				lFlKey.sort()

				for sFlag in lFlKey:
					dOut = {'param':sKey, 'level':2}
					dFlag = dFlags[sFlag]
					if 'value' in dFlag: dOut['value'] = '"%s"'%dFlag['value']
					elif 'type' in dFlag:
						dOut['type'] = dFlag['type']
						if 'units' in dFlag: dOut['units'] = dFlag['units']
					if 'title' in dFlag: dOut['title'] = dFlag['title']
					elif 'name' in dFlag: dOut['title'] = dFlag['name']
					else: dOut['title'] = ""

					lOut.append(dOut)

			# And finally the enum values
			if ('type' in dIn) and (dIn['type'] == 'enum') and ('values' in dIn):
				dVals = dIn['values']

				lValKey = list(dVals.keys())
				lValKey.sort()

				for sVal in lValKey:
					dOut = {'param':sKey, 'level':2}
					dVal = dVals[sVal]
					if 'value' in dVal: dOut['value'] = '"%s"'%dVal['value']
					if 'title' in dVal: dOut['title'] = dVal['title']
					elif 'name' in dFlag: dOut['title'] = dVal['name']
					else: dOut['title'] = ""

					lOut.append(dOut)

		# Output, 1st Determine the size of each column, must be at least as
		# long as the header
		lHdr = ('param', 'req', 'value', 'units', 'title')
		dTplt = { s : s[0].upper() + s[1:] for s in lHdr}
		lSz = [ len(s) for s in lHdr]

		for i in range(0, len(lHdr)):
			sKey = lHdr[i]
			for j in range(0, len(lOut)):
				dOut = lOut[j]
				if (sKey in dOut) and ( len(dOut[sKey]) > lSz[i] ):
					lSz[i] = len(dOut[sKey])

		lOut.sort(key=lambda dItem: "%s,%s,%s"%(dItem['param'], dItem['level'], dItem['value']) )

		sFmt = "%%(param)-%ds %%(req)-%ds %%(value)-%ds  %%(units)-%ds  %%(title)-%ds"%tuple(lSz)
		lStrs = []
		lStrs.append(sFmt%dTplt)
		for i in range(0,len(lHdr)): dTplt[lHdr[i]] = '-'*lSz[i]
		lStrs.append(sFmt%dTplt)

		for j in range(0, len(lOut)):
			if (j > 0) and (lOut[j-1]['param'] == lOut[j]['param']):
				dTplt['param'] = ""
			else:
				dTplt['param'] = lOut[j]['param']

			for sKey in lHdr[1:]:
				if sKey in lOut[j]: dTplt[sKey] = lOut[j][sKey]
				else: dTplt[sKey] = ""

			lStrs.append(sFmt%dTplt)

		sOut = "\n".join(lStrs)
		return sOut

	# ####################################################################### #
	def protoGet(self, dQuery, verbose=False):
		"""Query for data using server specific HTTP GET key,value pairs.

		This function is called by query() to communicate with an HTTP server.
		Unless you need to issue server specific GET values  (maybe due to a
		misconfigured catalog entry) use query() instead of calling this function
		directly.

		Args:
		   dQuery (dict) : A dictionary of key, value pairs to send as a GET
		      query to one of the URLs identified in .props['protocol']['base_urls'].

		Returns:
			list : A list of `das2.Dataset` objects or None if the query failed.

		Raises:
			das2.CatalogError : If there is a problem with the source definition
				itself
			das2.ServerError : If there is a problem not related to authentication
				when downloading data
		"""

		if self.bStub: self.load()
		
		if 'protocol' not in self.props:
			raise CatalogError(self.url, "'protocol' not present is data source definition")
			
		dProto = self.props['protocol']

		if ('base_urls' not in dProto) or \
			(not isinstance(dProto['base_urls'], list)):
			raise CatalogError(self.url, "'base_urls not present in protocol section, or is not a list")

		# If all the URLs are on the bad-base list, erase the list so they can
		# try again
		if len(self.lBadBase) == len(dProto['base_urls']):
			self.lBadBase = []

		# Change this up when the definition changes
		lDs = None
		for i in range(0, len(dProto['base_urls'])):
			sBaseUrl = dProto['base_urls'][i]

			if sBaseUrl in self.lBadBase: continue

			sJoin = ''
			if sBaseUrl.find('?') == -1:
				sJoin = "?"
			else:
				sJoin = '&'

			lParams = []
			for k in dQuery:
				if type(dQuery[k]) == str:
					sParam = "%s=%s"%(k, quote_plus(dQuery[k]))
				else:
					sParam = "%s=%s"%(k, dQuery[k])
				lParams.append(sParam)

			sGet = "&".join(lParams)
			sUrl = "%s%s%s"%(sBaseUrl, sJoin, sGet)

			try:
				#print("Reading %s"%sUrl)
				if verbose: perr("Requesting: %s\n"%sUrl)
				lDs = _das2.read_server(sUrl)
			except Exception as e:
				sys.stderr.write("Couldn't read URL '%s', %s\n"%(sUrl, str(e)))
				# put this URL on the naughty list
				self.lBadBase.append(sBaseUrl)

		if lDs != None:
			lOut = []
			for ds in lDs:
				lOut.append(ds_from_raw(ds))
			return lOut

		raise SourceError(sUrl, "Unable to retrieve data")


	# ######################################################################## #
	# Example Output.....
	#
	#Coordinates:
	#
	# Key                    Type     Units  Default     Values             Value description
	# ---------------------  -------  -----  ----------  -----------------  ---------------------------------
	# coord.time.minimum     isotime  UTC    2014-08-31  1977-09-05 to now
	# coord.time.maximum     isotime  UTC    2014-09-01  1977-09-05 to now
	# coord.time.resolution  real     s      43.2
	# data.efield.units      enum            V m**-1     V m**-1
	#                                                    raw
	#                                                    V**2 m**-2 Hz**-1
	#                                                    W m**-2 Hz**-1
	# opts.reader.negative   bool            true        false               Keep values negative flagged data in the output
	# opts.reader.noise      bool            true        true
	#
	# opts.format.das_text   bool            false       true                Convert output to text (utf-8) format
	#
	# Notes:
	#  - If a colum has no entries don't write it out
	#  - For boolean settings don't output the default, just the change
	#

	def _getParamTitle(self, sParam, sFlag=None):
	
		
		dParams = self.props['protocol']['http_params']
		
		if sParam not in dParams: return ""

		dParam = dParams[sParam]
		if 'type' in dParam:
			if dParam['type'] == 'flag_set':
				if 'flags' in dParam:
					dFlags = dParam['flags']
					if sFlag in dFlags:
						dFlag = dFlags[sFlag]
						if 'title' in dFlag:
							return dFlag['title']
						elif 'name' in dFlag:
							return dItem['name']

			elif dParam['type'] == 'enum':
				if 'items' in dParam:
					dItems = dParam['items']
					if sFlag in dItems:
						dItem = dItems[sFlag]
						if 'title' in dItem:
							return dItem['title']
						elif 'name' in dItem:
							return dItem['name']

			else:
				if 'title' in dParam:
					return dParam['title']
				elif 'name' in dParam:
					return dParam['name']

		return ""


	def _getDimRows(self, sKind, sDim, dDim, sAspect):
		# Could be a class function, doesn't need any instance state
		# Outputs rows of dictionaries with the following keys:
		#
		#    key, order, type, units, default, values, info

		lOut = []
		
		dHttp = self.props['protocol']['http_params']

		sUnits = ""
		if 'units' in dDim:
			if 'set' not in dDim['units']: sUnits = dDim['units']['value']

		dAspect = dDim[sAspect]

		sKey = '%s.%s.%s'%(sKind, sDim,sAspect)
		dSet = dAspect['set']
		dRow = {'key':sKey}

		if 'value' in dAspect: dRow['default'] = str(dAspect['value'])
		else: dRow['default'] = ""

		# There are two basic ways Interface values can be converted 
		# Protocol values.
		#
		# 1. Direct Pass through (the default)
		#
		# 2. Substitution (if upper item is an enum, or boolean)

		dRow['type'] = ''
		if 'enum' in dSet:
			dRow['type'] = 'enum'
		elif ('value' in dAspect) and isinstance(dAspect['value'], bool):
			dRow['type'] = 'bool'
		else:
			dRow['type'] = '?'
			if ('param' in dSet) and \
				(dSet['param'] in dHttp):
				dParam = dHttp[dSet['param']]
					
				if 'type' in dParam:
					if dParam['type'] in ('flag_set','enum'): 
						dRow['type'] = 'str'
					elif dParam['type'] == 'real':
						dRow['type'] = 'float'
					else: 
						dRow['type'] = dParam['type']
				
		if 'units' in dAspect: dRow['units'] = dAspect['units']
		else: dRow['units'] = sUnits

		if 'title' in dAspect:
			dRow['info'] = dAspect['title']
		else:
			# These are variable aspects, they have known meanings unlike the
			# generic options.  Give them descriptive names if needed
			sName = sDim
			if 'name' in dDim: sName = dDim['name']

			if sAspect == 'minimum':
				sFmt = "Minimum %s value to output"
			elif sAspect == 'maximum':
				sFmt = "Maximum %s value to output"
			elif sAspect == 'interval':
				sFmt = "Sub-select data in %s by this width"
			elif sAspect == 'resolution':
				sFmt = "Average data over %s bins with this width"
			elif sAspect == 'units':
				sFmt = "Output %s in these units"
			elif sAspect == 'enabled':
				sFmt = "Toggle %s output"
			else:
				sFmt = None

			if sFmt != None:
				dRow['info'] = sFmt%sName
			elif 'param' in dSet:
				dRow['info'] = self._getParamTitle(dSet['param'])

		if 'info' not in dRow: dRow['info'] = ''

		dRow['order'] = 0

		# Now for the infamous values column, just do the first row here
		# If there is a single alternate value to set, used that
		# If there is an enum, just use the first row of the enum.
		
		# Single value items...
		dRow['values'] = ''
		if 'enum' not in dSet:
			
			if 'range' in dSet:
				if isinstance(dSet['range'], list) and len(dSet['range']) == 2:
					dRow['values'] = '%s to %s'%tuple(dSet['range'][:2])
			
			elif 'value' in dSet:
				dRow['values'] = str(dSet['value'])
			
			elif dRow['type'] == 'bool':
				if dRow['default']: dRow['values'] = 'False'
				else: dRow['values'] = 'True'
				
			return [dRow]

		
		# Handling 1st row of an enum. 
		lOut = [dRow]

		# Now for the enum items
		
		dEnum = dSet['enum']
		n = 0
		sParam = dSet['param']
		for dEnum in dSet['enum']:
			# only the values and info change for each row
			if n > 0:
				lOut.append( {'key': sKey, 'order':n, 'type':'', 'units':'', 'default':''} )
			
			dRow = lOut[-1]

			dRow['values'] = dEnum['value']
			if 'title' in dEnum:  dRow['info'] = dEnum['title']
			elif 'name' in dEnum: dRow['info'] = dEnum['name']
			else:
				# dig for it...
				if 'flag' in dEnum:
					dRow['info'] = self._getParamTitle(sParam, dEnum['flag'])
				elif 'item' in dEnum:
					dRow['info'] = self._getParamTitle(sParam, dEnum['item'])
				else:
					dRow['info'] = self._getParamTitle(sParam)
			n += 1
			
		return lOut


	def _getOptRows(self, sPrefix, sOpt, dOpt):
	
		# Looking at things like: opts.das2_text
		#                   and:  opts.negative
		# Returns rows that look like:
		#   
		#    key, order, type, units, default, values, info

		sKey = '%s.%s'%(sPrefix, sOpt)
		dSet = dOpt['set']
		dRow = {'key':sKey}
		
		dHttp = self.props['protocol']['http_params']

		if 'value' in dOpt: dRow['default'] = str(dOpt['value'])
		else: dRow['default'] = ""

		dRow['type'] = ''
		if 'enum' in dSet:
			dRow['type'] = 'enum'
		elif ('value' in dOpt) and isinstance(dOpt['value'], bool):
			dRow['type'] = 'bool'
		else:
			# Pass through
			dRow['type'] = 'str'  # Assume string
			if ('param' in dSet) and (dSet['param'] in dHttp):
				dParam = dHttp[dSet['param']]
				if 'type' in dParam:
					dRow['type'] = dParam['type']
				if dRow['type'] == 'string': dRow['type'] = 'str'  # type name conversions
				if dRow['type'] == 'real': dRow['type'] = 'float'  # for readability
			

		if 'units' in dOpt: dRow['units'] = dOpt['units']['value']
		else: dRow['units'] = ''

		if 'title' in dOpt: dRow['info'] = dOpt['title']
		elif 'param' in dSet:
			if 'flag' in dSet:
				dRow['info'] = self._getParamTitle(dSet['param'], dSet['flag'])
			else:
				dRow['info'] = self._getParamTitle(dSet['param'])

		if dRow['type'] == 'bool':
			if dRow['default'] == 'False': dRow['values'] = 'True'
			else: dRow['values'] = 'False'
		elif dRow['type'] == 'str':
			dRow['values'] = ""
		
		dRow['order'] = 0
		
		lOut = [dRow]
		
		# Should merge this enum printing code with the one in
		# _getDimRows and make it smarter (i.e. combine items if no
		# per-enum item titles, split them otherwise)
		
		if dRow['type'] == 'enum':
			
			lEnum = dSet['enum']

			i = 0
			n = 0
			dExRow = None
			while i < len(lEnum): 
			
				sVal = ""
				iRow = 0
				while (i < len(lEnum)) and (len(sVal) < 24):
				
					if iRow == 0: sVal = "%s"%lEnum[i]['value']
					else: sVal += ", %s"%lEnum[i]['value']
					i += 1
				
				iRow += 1
				
				# If there are going to be more rows, add a trailing comma
				if i < len(lEnum): sVal = sVal + ","
					
				
				# Set existing row values or start a new one
				if n == 0:				
					dRow['values'] = sVal
				else:
					dExRow = {
						'key':sKey,'order':n, 'type':'', 'units':'', 'default':'',
						'values': sVal
					}
					lOut.append(dExRow)
					
				n += 1
				
		return lOut


	def info(self):
		"""Get human readable text describing the query parameters of this
		data source.

		Returns:
			str : A text description of the public query API for this data source
		"""

		if self.bStub: self.load()

		lHdrs = ['Key', 'Type', 'Units', 'Default', 'Values', 'Value Description']

		lRows = []
		
		if 'interface' not in self.props:
			raise CatalogError(self.url, "interface section missing")
		dIface = self.props['interface']

		# Unlike general options, coordinate options assign meanings to sub-keys
		tDimInType = ('coordinates','data')
		tDimOutType = ('coord','data')
		for i in range(0,2):

			if tDimInType[i] not in dIface: continue

			dDimType = dIface[ tDimInType[i] ]
			for sDim in dDimType:
				dDim = dDimType[sDim]

				for sAspect in dDim:
					if 'set' in dDim[sAspect]:
						lTmp = self._getDimRows(tDimOutType[i], sDim, dDim, sAspect)
						if lTmp != None: lRows += lTmp

		if 'options' in dIface:
			dOpts = dIface['options']
			for sOpt in dOpts:
				dOpt = dOpts[sOpt]
				if 'set' in dOpt:
					lTmp = self._getOptRows('option', sOpt, dOpt)
					if lTmp != None: lRows += lTmp

		lRows.sort(key=lambda dItem: "%s,%s"%(dItem['key'], dItem['order']) )


		sTplt = "%%(key)-%ds  %%(type)-%ds  %%(units)-%ds  %%(default)-%ds  " +\
		       "%%(values)-%ds  %%(info)-%ds"

		# Get the column widths
		lSz = [len(s) for s in lHdrs]

		tLoc = ('key','type','units','default','values','info')
		for dRow in lRows:
			for i in range(0,len(tLoc)):
				#print(dRow)
				if len(dRow[tLoc[i]]) > lSz[i]: lSz[i] = len(dRow[tLoc[i]])

		sFmt = sTplt%tuple(lSz)

		dHdr = { tLoc[i] : lHdrs[i] for i in range(len(tLoc)) }
		lOut = [sFmt%dHdr]

		lSep = ["-"*lSz[i] for i in range(len(tLoc)) ]
		lOut.append("  ".join(lSep))


		for i in range(len(lRows) - 1, 0, -1):
			if lRows[i]['key'] == lRows[i-1]['key']:
				lRows[i]['key'] = ""

		lOut += [ sFmt%d for d in lRows ]
		sOut = '\n'.join(lOut)

		return sOut


	# ####################################################################### #
	def _getItemParams(self, sItem, dItem):
		"""For each thing that can have settable aspects, ex a coord, a data var,
		or all of options, get the settable parameters
		"""
	
		
		if 'http_params' in self.props['protocol']:
			dParams = self.props['protocol']['http_params']
		else:
			dParams = {}
		
		bSettable = False
		for sAsp in dItem:
			if ('value' in dItem[sAsp]) and ('set' in dItem[sAsp]):
				bSettable = True
				break
		
		if not bSettable: return None
		
		dOut = {}
		for sAsp in dItem:
			dAsp = dItem[sAsp]
			if 'set' not in dAsp: continue
			
			dOut[sAsp] = {'default': dAsp['value']}
			
			for s in ('name','title','summary','type'):
				if s in dAsp: dOut[sAsp][s] = dAsp[s]
				
			if 'units' in dAsp:
				dOut[sAsp]['units'] = dAsp['units']['value']
			
			dSet = dAsp['set']
			
			if 'value' in dSet:
				dOut[sAsp]['enum'] = [ dAsp['value'], dAsp['set']['value'] ]
				
			elif 'enum' in dSet:
				lTmp = [d['value'] for d in dSet['enum']]
				if dAsp['value'] not in lTmp:
					dOut[sAsp]['enum'] = [dAsp['value']] + lTmp
				else:
					dOut[sAsp]['enum'] = lTmp
			
			else:			
				# Special handling for items with a range
				lRange = [None, None]
				if ('range' in dSet) and isinstance(dSet['range'], list) and \
				   (len(dSet['range']) == 2): 
					dOut[sAsp]['range'] = dSet['range']
			
			# Use overall item units if no specific units mentioned here
			if ('units' not in dOut[sAsp]) and ('units' in dItem):
				dOut[sAsp]['units'] = dItem['units']['value']
			
			# Make sure we have a type
			if ('type' not in dOut[sAsp]):
			
				# Try for a type given the default value
				if isinstance(dItem[sAsp]['value'], bool):
					dOut[sAsp]['type'] = 'boolean'
					
				elif isinstance(dItem[sAsp]['value'], int):
					dOut[sAsp]['type'] = 'integer'
				
				elif isinstance(dItem[sAsp]['value'], float):
					dOut[sAsp]['type'] = 'real'
				
				# Try to get type from lower parameter
				elif dSet['param'] in dParams:
					if 'type' in dParams[dSet['param']]:
						sType = dParams[dSet['param']]['type']
						if sType in ('enum','flag_set'): sType = 'string'
						dOut[sAsp]['type'] = sType
					else:
						dOut[sAsp]['type'] = 'string'
				
				# Well, just go with the default
				else:
					dOut[sAsp]['type'] = 'string'
				
					
		return dOut
		
	
	def params(self):
		"""Get a dictionary of the query parameters for this dataset.

		See :meth:`Source.params` for a description.
		"""
		if self.bStub: self.load()

		dOut = {}
		
		if 'coordinates' in self.props:
			for sVar in self.props['coordinates']:
		
				dOutVar = self._getItemParams(sVar, self.props['coordinates'][sVar])
				if dOutVar != None:
					if 'coordinates' not in dOut: dOut['coord'] = {}
					dOut['coord'][sVar] = dOutVar
	
		if 'data' in self.props:	
			for sVar in self.props['data']:
		
				dOutVar = self._getItemParams(sVar, self.props['data'][sVar])
				if dOutVar != None:
					if 'data' not in dOut: dOut['data'] = {}
					dOut['data'][sVar] = dOutVar
		
		if 'options' in self.props:
			dOutOpts = self._getItemParams('options', self.props['options'])				
			if dOutOpts != None: dOut['option'] = dOutOpts
		
		return dOut


	# ####################################################################### #
	
	def _translate(self, sAsp, dAsp, value, dProto):
		# Set a key and value in the protocol level query dictionary,
		# 
		# Args:
		#	sAsp - The name of the settable item, used for error messages.
		#	
		#	dAsp - The variable aspect or option item through which the 
		#	     given value will be interpreted.
		#		  
		#	val - The value to translate
		#	
		#	dProto - The dictionary in to which the key an value are to
		#	    be added.
		#		 
		# Returns:
		#	None : Alters argument dProto
			
		if 'set' not in dAsp:
			raise ValueError("%s from %s is not settable"%(sAsp, self.props['_url']))
		
		dSet = dAsp['set']
		
		if 'param' not in dSet:
			raise DatsetError("key 'param' missing in %s:set in datasource form %s"%(
			                  sAsp, self.props['_url']))
									
		sParam = dSet['param']
		
		if 'http_params' not in self.props['protocol']:
			raise DatasetError("protocol:http_params key missing in datasource from %s"%self.props['_url'])	
		dHttp = self.props['protocol']['http_params']
		
		dHParam = dHttp[sParam]
		
		if value == dAsp['value']:
			if ('required' not in dHParam) or (not dHParam['required']):
				return
		
		# Translate the value (if applicable) and find the flag ID (if applicable)		
		sFlag = None
		if 'flag' in dSet: sFlag = dSet['flag']
		if 'pval' in dSet: value = dSet['pval']
		
		if 'enum' in dSet:
			# Make sure the given value is one of the items in the enum
			iEnum = -1
			for i in range(len(dSet['enum'])):
				if dSet['enum'][i]['value'] == value:
					iEnum = i
					break
			
			if iEnum == -1:
				raise ValueError("Illegal value %s for enumeration %s:set:enum"%(value, sAsp))
			
			# The enum items can set a flag on it's own
			if 'flag' in dSet['enum'][iEnum]: sFlag = dSet['enum'][iEnum]['flag']
			
			# The enum items can alter the pass through value
			if 'pval' in dSet['enum'][iEnum]: value = dSet['enum'][iEnum]['pval']
		
			
		
		# Now I know the insert value and if I'm a flag or not
		if sFlag == None:
			dProto[sParam] = value
			return
		
		if ('flags' not in dHParam) or (sFlag not in dHParam['flags']):
			raise DatasetError(
				"Flag %d from %s not given in protocol:http_params:%s:flags for dataset from %s"%(
				sFlag, sAsp, sParam, self.props['_url'])
			)
		
		dFlag = dHParam['flags'][sFlag]
		
		if 'prefix' in dFlag:
			sFlagVal = "%s%s"%(dFlag['prefix'], dFlag['value'])
		else:
			sFlagVal = dFlag['value']
		
		if sParam in dProto:
			sSep = " "
			if 'flag_sep' in dHParam: sSep = 'flag_sep'
			dProto[sParam] = "%s %s"%(dProto[sParam], sFlagVal)
		else:
			dProto[sParam] = sFlagVal
					
	
	# ######################################################################## #
	def get(self, dQuery=None, verbose=False):
		"""Get data using the public API for this source.

		see :py:meth:`Source.query`
		"""

		# {'time':('2008-223T09:06', '2008-223T09:13'), '80khz':True }
		# The format is:
		#
		#  'key' : {'aspect':value, 'aspect2':value}
		#
		# or
		#
		#  'key' : (value1, value2, value3)
		#
		# or if key has only a single settable prop
		#
		#  'key' : value1

		# {
		#    "coord":{"time":{"minimum":2014-08-31, "maximum":2014-09-01, "resolution":43.2}},
		#    "data":{"efield":{"units":"raw", "filter":("negative","pls","noise")}}},
		# }
		#
		# Short cuts
		#
		# {
		#     "time":{"min":2014-08-31, "max":2014-09-01, "res":43.2},
      #     "efield":"raw"
		# }
		
		# Implementation note:  This function should be reworked so that all
		# the settable things and associated setters are in a flat namespace
		# first!  This will shorten the code quite a bit. --cwp 2019-03-29
		
		if dQuery == None:
			return self._getExample(None)
		
		if isinstance(dQuery, basestring):
			return self._getExample(dQuery)
			
		#print("Orig Query: %s"%dQuery)
		
		if 'interface' not in self.props:
			raise CatalogError(self.url, "interface section missing")
		dIface = self.props['interface']


		sC = 'coordinates'
		sD = 'data'
		sO = 'options'
				
		# 1st pass, get variable and option names in standard locations
		dCan = {sC:{}, sD:{}, sO:{}}
		dRe  = {'coord':sC, 'data':sD, 'option':sO}
		# 1st pass...
		for sItem in dQuery:
			if sItem in dRe: 
				dCan[dRe[sItem]] = dQuery[sItem]
				
			else:
				bSaved = False
				for sSection in (sC, sD, sO):
					if sSection in dIface:
						if sItem in dIface[sSection]:
							dCan[ sSection ][sItem] = dQuery[sItem]
							bSaved = True
							break
				if not bSaved:
					raise ValueError("%s not recognized as a coordinate, "%sItem +\
					                 "or data variable name, or option name")
				
		# 2nd pass handle aspects, one for each variable and then the overall
		# options
		lPairs = []
		if len(dCan[sC]) > 0:
			lPairs += [ ("%s:%s"%(sC, sVar), dCan[sC][sVar]) for sVar in dCan[sC] ]
			
		if len(dCan[sD]) > 0:
			lPairs += [ ("%s:%s"%(sD, sVar), dCan[sD][sVar]) for sVar in dCan[sD] ]
			
		if len(dCan[sO]) > 0:
			lPairs += [ (sO, dCan[sO]) ]
		
		# If the body of the item is not a dictionary, look for special aspects in
		# my item definition.  A single item is the general options section or a 
		# variable
		for (sGroup, dSetBody) in lPairs:
			dNewBody = None
			if isinstance(dSetBody, tuple):
				dNewBody = {}
				if len(dSetBody) > 0: dNewBody['minimum'] = dSetBody[0]
				if len(dSetBody) > 1: dNewBody['maximum'] = dSetBody[1]
				if len(dSetBody) > 2:
					l = sGroup.split(':')
					dAsp = dIface[l[0]][l[1]]
					if 'resolution' in dAsp: dNewBody['resolution'] = dSetBody[2]
					else: dNewBody['interval'] = dSetBody[2]
				if len(dSetBody) > 3:
					raise ValueError("Tuple too long for query item %s"%sGroup)

			if isinstance(dSetBody, bool):
				dNewBody = {'enabled':dSetBody}
			
			
			if isinstance(dSetBody, list):
				dNewBody = {}
				for sAsp in dSetBody:
					dNewBody[sAsp] = True
			
			if dNewBody != None:
				if ':' in sGroup:
					lPath = sGroup.split(':')
					dCan[lPath[0]][lPath[1]] = dNewBody
				else:
					dCan[sGroup] = dNewBody
			
		# Now we should have a connonical query, see if each settable aspect 
		# actually has a set function
		for sCat in (sC, sD):
			for sVar in dCan[sCat]:
				if sVar not in dIface[sCat]:
					raise ValueError("%s variable %s not present in data source from %s"%(
					                 sCat, sVar, self.url))
										  
				for sProp in dCan[sCat][sVar]:
					if sProp not in dIface[sCat][sVar]:
						raise ValueError("Variable %s does not have a property named %s in data source from %s"%(
					                    sVar, sProp, self.url))
			
					if 'set' not in dIface[sCat][sVar][sProp]:
						raise ValueError("Property %s, %s is not settable in data source from %s"%(
						                  sVar, sProp, self.url))
		
		for sOpt in dCan[sO]:
			if sOpt not in dIface[sO]:
				raise ValueError("Option %s not present data source from %s"%(
			                     sProp, self.url))
			
			if 'set' not in dIface[sO][sOpt]:
				raise ValueError("Option %s is not settable in data source from %s"%(
				                  sProp, self.url))
		
		
		if 'protocol' not in self.props:
			raise DatasetError("protocol key missing in datasource from %s"%self.url)	
		
		if 'http_params' not in self.props['protocol']:
			raise DatasetError("protocol:http_params key missing in datasource from %s"%self.props['_url'])	
		dHttp = self.props['protocol']['http_params']
		
		# Go through all my params and add default values to required items that
		# don't have a value
		for sCat in (sC, sD):
			if sCat in dIface:
				for sVar in dIface[sCat]:
					for sProp in dIface[sCat][sVar]:
					
						if not isinstance(dIface[sCat][sVar][sProp], dict): continue
						
						if 'set' not in dIface[sCat][sVar][sProp]: continue
						
						if 'param' not in dIface[sCat][sVar][sProp]['set']:
							raise DatasetError("'param' missing from %s:%s:%s:set in datasource form %s"%(
							                   sCat, sVar, sProp, self.url))
							
						sHParam = dIface[sCat][sVar][sProp]['set']['param']
						if sHParam not in dHttp:
							raise DatasetError("key %s missing in 'protocol:http_params' from %s"%(
								                   sHParam, self.url))
						if ('required' not in dHttp[sHParam]) or (not dHttp[sHParam]['required']):
							continue
							
						if 'value' not in dIface[sCat][sVar][sProp]:
							raise DatasetError("'value' missing in %s:%s:%s from %s"%(
							                   sCat, sVar, sProp, self.url))
						
						if sCat not in dCan: dCan[sCat] = {}
						if sVar not in dCan[sCat]: dCan[sCat][sVar] = {}
						
						if sProp not in dCan[sCat][sVar]:
							dCan[sCat][sVar][sProp] = dIface[sCat][sVar][sProp]['value']
		
		
		# due to lack of flattening, repeat above for options section
		if 'options' in dIface:
			for sProp in dIface['options']:					
				if 'set' not in dIface['options'][sProp]: continue
						
				if 'param' not in dIface['options'][sProp]['set']:
					raise DatasetError("'param' missing from options:%s:set in datasource form %s"%(
					                   sProp, self.url))
							
				sHParam = dIface['options'][sProp]['set']['param']

				if sHParam not in dHttp:
					raise DatasetError("key %s missing in 'prococol:http_params' from %s"%(
								                   sHParam, self.url))
				if ('required' not in dHttp[sHParam]) or (not dHttp[sHParam]['required']):
					continue
							
				if 'value' not in dIface['options'][sProp]:
					raise DatasetError("'value' missing in options:%s from %s"%(
							              sProp, self.url))
						
				if 'options' not in dCan: dCan['options'] = {}						
				dCan['options'][sProp] = dIface['options'][sProp]['value']
							
				
		# Translate each high-level query value into a protocol level query
		dProto = {}
		
		for sCat in (sC, sD):
			if sCat not in dCan: continue
			for sVar in dCan[sCat]:
				for sProp in dCan[sCat][sVar]:
					dMProp = dIface[sCat][sVar][sProp]	
					sName = "%s:%s:%s"%(sCat, sVar, sProp)
					self._translate(sName, dMProp, dCan[sCat][sVar][sProp], dProto)
		
		if 'options' in dCan:
			for sProp in dCan['options']:
				dMProp = dIface['options'][sProp]
				sName = 'options:%s'%sProp
				self._translate(sName, dMProp, dCan['options'][sProp], dProto)				
		
		
		#lKeys = list(dProto.keys())
		#lKeys.sort()
		#for sParam in lKeys:
		#	print(sParam, "=", dProto[sParam])
		
		return self.protoGet(dProto, verbose)
