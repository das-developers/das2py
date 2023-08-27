from os.path import basename as bname
from copy import deepcopy

import textwrap
import logging
import sys

from . import dastime

##############################################################################
# Export globals

BOOL        = "bool"
INT         = "int"
REAL        = "float"
STRING      = "str"
TIMEPT      = "timept"

DAS2_BINARY = 'application/vnd.das2.das2stream'
DAS2_TEXT   = 'text/vnd.das2.das2stream; charset=utf-8'
Q_BINARY    = 'applicaiton/vnd.das2.qstream'
Q_TEXT      = 'text/vnd.das2.qstream; charset=utf-8'

##############################################################################
# internal globals

_g_lAllSelOps = ['.eq.','.ne.','.gt.','.lt.','.ge.','.le.']

_g_lAllOutOps = ['.res.','.out.']

_g_lAllOps = _g_lAllSelOps + _g_lAllOutOps

_g_lAllowedTypes = [STRING,BOOL,INT,REAL,BOOL,TIMEPT]

##############################################################################
class DasCliError(Exception):
	"""
	Raised if there is a problem with the way various library functions
	were called.
	"""
	def __init__(self, msg):
		self.msg = msg
		
	def __str__(self):
		return self.msg

##############################################################################
def _typeCheckNotNone(sType, item):
	"""Check item against the given type"""
	
	if sType == 'str':
		return isinstance(item, str)
	
	if sType == 'int':
		return isinstance(item, int)
		
	if sType == 'float':
		return isinstance(item, float)

	if sType == 'bool':
		return isinstance(item, bool)

	if sType == 'timept':
		return isinstance(item, dastime.DasTime)
	
	assert False


def _typeCheck(sType, item):
	"""Check item against the given type, None matches anything"""
	
	if isinstance(item, type(None)):
		return True
	
	return _typeCheckNotNone(sType, item)


##############################################################################
class Selector(object):
	"""See function DasCli.addSelector for constructor documentation"""
	
	_typeMeta = {'str':'STRING','int':'INTEGER','float':'REAL',
	             'bool':'BOOL', 'timept':'TIME_POINT'}
	
	def __init__(self, sKey, sName, dArgs):
		
		self.key = sKey
		self.name = sName
		self.intype = 'str'
		self.summary = '(No summary provided)'
		self.min = None
		self.max = None
		self.enum = None
		self.compare = None
		self.default = None
		self.required = False
		self.data = None
		self._units = None
		self.config = False
		
		self.lVals = None  
		
		if sKey == None or len(sKey) < 1 or sKey != sKey.lower() or \
			len(sKey.split()) > 1 or sKey != sKey.strip():
			raise ValueError("Invalid key value: '%s'"%sKey)
		
		
		for sParam in ['intype', 'summary', 'min', 'max', 'flags', 'compare', 
		               'default', 'enum', 'required', 'data', '_units',
							'config']:
			if sParam in dArgs:
				self.__setattr__(sParam, dArgs[sParam])
				
		if not isinstance(self.required, bool):
			DasCliError("Expecting a boolean for 'required'")
						
		# Check the type string
		self.intype = self.intype.lower()
		if self.intype not in _g_lAllowedTypes:
			raise DasCliError("Type %s is unknown"%(self.intype))
		
		typeNone = type(None)
		
		if not isinstance(self.summary, (str, typeNone)):
			raise DasCliError("Summary must be a string (or None)")
			
		# Handle comparison lists differently from enumerations
		if self.enum != None:

			if not isinstance(self.enum, (list, typeNone)):
				raise DasCliError("enum argument should be a list (or None)")

			# Note that both compare and enum can't be set for the same selector
			# it will either act in one mode or the other
			if self.compare != None:
				raise DasCliError("The comparison operator for an enumeration "+\
				                  "is always .eq., the 'compare' argument is not "+\
										"needed")
			
			if len(self.enum) < 1:
				raise DasCliError("enum is an empty list")
			
			# make sure the enum's values match the type
			for item in self.enum:
				if not _typeCheckNotNone(self.intype, item):
					raise DasCliError("Invalid type: %s isn't a '%s' value"%(
					                  item, self.intype))
				
			self.compare = ['.eq.']
			
		else:
				
			# Up convert simple strings
			if isinstance(self.compare, str):
				self.compare = [ self.compare ]
			
			# A comparison set needed for non-booleans
			if self.intype == 'bool':
				if self.compare != None and self.compare != ['.eq.']:
					DasCliError("'comparison' is not needed for 'bool' selectors")
					
				self.compare = ['.eq.']
			
			else:
				if self.compare == None:
					self.compare = deepcopy(_g_lAllSelOps)
					
					if self.default != None:
						DasCliError("Operator list missing, can't assign default "+\
						            "baundaries.")
					
				else:
					# 1st lo-case everything
					self.compare = [s.lower() for s in self.compare]
					
					# Replace beg and end
					for i in range(0, len(self.compare)):
						self.compare[i] = self.compare[i].replace('beg','ge')
						self.compare[i] = self.compare[i].replace('end','lt')
					
					for i in range(0, len(self.compare)):
						sOp = self.compare[i]
						if sOp not in _g_lAllSelOps:
							self.compare[i] = ".%s."%self.compare[i]
							if self.compare[i] not in _g_lAllSelOps:
								raise KeyError("Operation '%s' is unknown"%sOp)
								
		
		if self.default == None:
			self.default = [ None ]*len(self.compare)
		else:
			
			if isinstance(self.default, str) or isinstance(self.default, bool):
				self.default = [ self.default ]
			
			if len(self.default) != len(self.compare):
				DasCliError("Expected %d default values, one "%len(self.compare)+\
				            "for each comparison in %s"%self.compare)
			
		for sDef in self.default:
			if not _typeCheck(self.intype, sDef):
				raise DasCliError("Invalid type: %s isn't a '%s' value"%(
					                  sDef, self.intype))
			
		# If all defaults are non-null, this CAN'T be a required selector
		nNonNull = 0
		for d in self.default:
			if d != None:
				nNonNull += 1
		
		if self.required and nNonNull > 0:
			DasCliError("All defaults are specified, 'required' does nothing")
		
		
		# Initalize the boundary list to have the same length as the 
		# comparison operator list
		self.lVals = [None] * len(self.compare)
		
	########################################################################
	def __str__(self):
		
		lOut = []
		for i in range(0, len(self.compare)):
			if self.lVals[i] != None:
				lOut.append("%s%s%s"%(self.key, self.compare[i], self.lVals[i]))
			elif self.default[i] != None:
				lOut.append("%s%s%s"%(self.key, self.compare[i], self.default[i]))
		
		if len(lOut) != 0:
			return " ".join(lOut)
		else:
			return "%s.eq.ANY_VALUE"%self.key
	
	########################################################################
	def typeMeta(self):	
		return self._typeMeta[self.intype]
					
		
	########################################################################
	def supportsOp(self, sOp):
		return sOp in self.compare 
	
	########################################################################
	def getDefault(self, sOp):
		i = self.compare.find(sOp)
		
		if i == -1:
			DasCliError("There is no default value for comparison %s"%sOp)
		else:
			return self.default[i]
	
	########################################################################
	# Convert the given value to the type for this selector
	def _typeConv(self, val):
	
		#print "_typeConv: ", self.intype, val
		
		if self.intype == 'str':
			if isinstance(val, str):
				return val
				
			else:
				return str(val)
		
		elif self.intype == 'int':
			if isinstance(val, int):
				return val
				
			elif isinstance(val, str):
				# Special handling for strings, look for the 0x prefix
				if val.startswith('0x'):
					return int(val, 16)
				else:
					return int(val)
		
		elif self.intype == 'float':
			if isinstance(val, float):
				return val
				
			else:
				return float(val)
		
		elif self.intype == 'bool':
			if isinstance(val, bool):
				return val
			
			elif isinstance(val, str):
				# Special handling for strings, make '0' and 'false' eval to false
				if val.lower() in ['true','1']:
					return True
				elif val.lower() in ['false', '0']:
					return False
				else:
					raise ValueError("Can't convert %s to a boolean value"%val)
	
			else:
				return bool(val)
				
		elif self.intype == 'timept':
			if isinstance(val, dastime.DasTime):
				return val
			elif isinstance(val, (list, tuple, str)):
				try:
					return dastime.DasTime(val)
				except OverflowError as e:
					raise ValueError(str(e))
			else:
				raise ValueError("Can't convert %s to a DasTime"%val)
			
		else:
			assert False
	

	########################################################################
	def setBound(self, sOp, val):
		
		assert self.compare.count(sOp) == 1
				
		if sOp == '.beg.':
			sOp = '.ge.'
		if sOp == '.end.':
			sOp = '.lt.'
		
		idx = self.compare.index(sOp)
		
		self.lVals[idx] = self._typeConv(val)
			
		# Okay, now that the value has been set, see if it has to be in
		# an enum list
		
		if self.enum != None:
			if self.lVals[idx] not in self.enum:
				raise ValueError("bad value '%s', expected one of %s"%(self.lVals[idx], self.enum))
	
	########################################################################
	def __getitem__(self, sOp):
			
		if not sOp.startswith('.'):
			sOp = "."+sOp
		
		if not sOp.endswith('.'):
			sOp = sOp + "."
	
		if sOp == '.beg.':
			sOp = '.ge.'
		if sOp == '.end.':
			sOp = '.lt.'
	
		if self.compare.count(sOp) == 0:
			raise KeyError("Boundary comparison operator '%s' "%sOp+\
			               "is not allowed for selector '%s'."%self.key)
		
		idx = self.compare.index(sOp)
				
		if self.lVals[idx] != None:
			return self.lVals[idx]
		else:
			return self.default[idx]
	
	
	########################################################################
	def isReady(self, log):
	
		if not self.required:
			return True
		
		for i in range(0, len(self.compare)):
			if self.lVals[i] == None:
				if self.default[i] == None:
					log.error("Required parameter \"%s%sVALUE\""%(self.key, self.compare[i])+\
					          " is missing.")
					return False
		
		return True
		
	#######################################################################
	def inRange(self, val):
		"""Is the value, val, in the selector range for this item?
		
		val must be of the same data type as the selector, or it must be 
		   a string.  Strings are auto converted to the proper type.
			
		Returns False if the given selector boundaries rule out the value
		        otherwise True is returned.  Missing boundaries are not
				  checked.  If no boundaries were specified for this selector
				  true is returned.
		"""
		
		perr = sys.stderr.write
		
		# A value type of None, is never in range, nor is an empty string.
		if val == None:
			return False
		
		if isinstance(val, str) and val == '':
			return False
		
		_val = self._typeConv(val)
		
		for i in range(0, len(self.compare)):
		
			#perr(" cmp: %s%s%s %s:%s (%s) -> "%(
			#          self.key, self.compare[i], self.lVals[i], val, self.intype, _val))
			
			_cmpTo = self.lVals[i]
			if _cmpTo == None:
				_cmpTo = self.default[i]
				if _cmpTo == None:
					bRet = True
					#perr("%s\n"%bRet)
					continue
			
			# Go in order of likely comarison usage	
			if self.compare[i] == '.eq.':
				bRet = (_val == _cmpTo)
				#perr("%s\n"%bRet)
				if not bRet:
					return False
			
			elif self.compare[i] == '.ge.':
				bRet = _val >= _cmpTo
				#perr("%s\n"%bRet)
				if not bRet:
					return False
			
			elif self.compare[i] == '.lt.':
				bRet = _val < _cmpTo
				#perr("%s\n"%bRet)
				if not bRet:
					return False
			
			elif self.campare[i] == '.ne.':
				bRet = _val != _cmpTo
				#perr("%s\n"%bRet)
				if not bRet:
					return False
			
			elif self.compare[i] == '.gt.':
				bRet = _val > _cmpTo
				#perr("%s\n"%bRet)
				if not bRet:
					return False
			
			elif self.compare[i] == '.le.':
				bRet = _val <= _cmpTo
				#perr("%s\n"%bRet)
				if not bRet:
					return False
		
		return True
		

##############################################################################
class Output(object):
	"""See function DasCli.addOutput for constructor documentation"""
	
	def __init__(self, sKey, sName, dArgs):
		
		self.key = sKey
		self.name = sName
		self.summary = None
		self.units = None
		self.label = None
		self.optional = False
		self.data = None
		self.varres = False
		self.defres = None
		self.resunits = None
		self.rRes = None
		

		# Can be changed by the command line paramenters
		self.resolution = None
		self.enabled = None

		if sKey == None or len(sKey) < 1 or sKey != sKey.lower() or \
			len(sKey.split()) > 1 or sKey != sKey.strip():
			raise ValueError("Invalid key value: '%s'"%sKey)
		
		
		for sParam in ['summary','units','label','optional', 'enabled',
		               'varres', 'data', 'defres', 'resunits']:
			if sParam in dArgs:
				self.__setattr__(sParam, dArgs[sParam])
		
		typeNone = type(None)
			
		if not isinstance(self.summary, (str, typeNone)):
			raise DasCliError("Value for summary must be a string (or None)")
			
		if not isinstance(self.units, (str, typeNone)):
			raise DasCliError("Value for units must be a string (or None)")
			
		if not isinstance(self.resunits, (str, typeNone)):
			raise DasCliError("Value for units must be a string (or None)")
			
		if not isinstance(self.label, (str, typeNone)):
			raise DasCliError("Value for label must be a string (or None)")
			
		if not isinstance(self.optional, (bool)):
			DasCliError("Value for 'optional' must be a boolean, or None")
		
		if not isinstance(self.enabled, (bool, typeNone)):
			DasCliError("Value for 'enabled' must be a boolean, or None")
		
		if not isinstance(self.varres, (bool, typeNone)):
			DasCliError("Value for 'varres' must be a boolean, or None")
		

		if self.enabled == None:
			self.enabled = not self.optional
			
		if self.label == None:
			if not self.units == None:
				self.label = self.units
				
		if self.varres:
			if self.defres == None:
				DasCliError("Default resolution missing for variable resolution"+\
				            " output '%s'"%self.key)
	
	def setEnabled(self, sVal):
		if sVal.lower() in ['on', '1', 'true']:
			self.enabled = True
		else:
			self.enabled = False
			
	def setResolution(self, sRes):
		self.rRes = float(sRes)
		
	def __getitem__(self, sOp):
		
		if not sOp.startswith('.'):
			sOp = "."+sOp
		
		if not sOp.endswith('.'):
			sOp = sOp + "."
			
		if sOp == '.out.':
			return self.enabled
		
		if sOp == '.res.':
			return self.rRes
			
		raise KeyError("No such output property %s "%sOp)
	
#	def enabled(self):
#		return self.enabled
#	
#	def name(self):
#		return self.name
#		
#	def key(self):
#		return self.key
#		
#	def label(self):
#		return self.label
#	
#	def hasVarRes(self):
#		return self.varres


##############################################################################
class DasCliSet(dict):
	"""The set of selectors, supports both list and dictionary symantics
	   for lookup
	"""
	
	def __init__(self):
		self._keyList = []
		
		
	def add(self, item):
				
		# Make sure we don't already have as selector with that name
		if item.key in self:
			raise DasCliError("Dulicate selector name %s"%sKey)			
		
		self._keyList.append(item.key)
		self[item.key] = item
		
		setattr( self, item.key, item)

	# Allow getting items by integers so that selectors can be pulled
	# in a known order without resorting to sorting the keys
	def __getitem__(self, key):
		
		if isinstance(key, slice):
			(iStart, iStop, iStride) = key.indices(len(self._keyList))
			return [self[i] for i in range(iStart, iStop, iStride) ]
		
		if isinstance(key, int):
			key = self._keyList[key]
		
		return dict.__getitem__(self, key)
		
	# How to support slicing?
		

##############################################################################
def _text_wrap(sPrefix, sText):
	tw = textwrap.TextWrapper(initial_indent=sPrefix, subsequent_indent=sPrefix,
	                          width=80, replace_whitespace=True)
	return tw.fill(sText)


def _text_wrap2(sFirstLine, sSubsequent, sText):
	tw = textwrap.TextWrapper(initial_indent=sFirstLine, replace_whitespace=True,
	                          subsequent_indent=sSubsequent, width=80)
	return tw.fill(sText)


##############################################################################
class DasCli(object):
	"""Handles the das 2.2 command line interface with backwards compatibilty
	to das 2.1.  Use this in place of optparse, getopt, etc. for das readers
	"""
	
	########################################################################
	def __init__(self, **dArgs):
		"""Provide overall information for the program.  The following keywords
		are recognized:

		  prog        - A program name, please always supply this or the help
		                looks pretty marginal

		  description - Stuff to put after the usage statement but before the
		                option descriptions

		  footer      - Stuff to put at the end of the help output

		  version     - A version string

		  tech_contact - How to get a hold of the programmer responsible for
		                 this reader
							  
		  sci_contact - Which scientist knows about these data
		  
		  mime        - A string providing the mime type of the data output 
		                format, or a dictionary of output fomats if more than
							 one is supported.
							 
		  mimedef     - If a mime dictorary was supplied, define a default 
		                format using this key.
		
		Vertical tab characters can be inserted anywhere to force a line 
		break.  Otherwise all text is wrapped on work boundaries to 80 
		characters.
		"""
		
		if 'prog' in dArgs:
			self.sProgName = dArgs['prog']
		else:
			import __main__
			if dir(__main__).count('__name__') > 0:
				self.sProgName = bname( __main__.__name__ )
			else:
				self.sProgName = "SET_PROG_NAME"
		
		if 'description' in dArgs:
			self.sDesc = dArgs['description'] 
		else:
			self.sDesc = "(No desciption provided)"
		
		if 'footer' in dArgs:
			self.sFooter = dArgs['footer']
		else:
			self.sFooter = None
		
		if 'version' in dArgs:
			self.sVersion = dArgs['version']
		else:
			self.sVersion = "   (unknown version)"
			
		if 'tech_contact' in dArgs:
			self.sTechContact = dArgs['tech_contact']
		else:
			self.sTechContact = "(not provided)"
			
		if 'sci_contact' in dArgs:
			self.sSciContact = dArgs['sci_contact']
		else:
			self.sSciContact = "(not provided)"
			
			
		if 'mime' in dArgs:
			dMime = dArgs['mime']
			if isinstance(dMime, str):
				dMime = {None: dMime }
				self.dMime = dMime
				self.sDefMime = None
				
			elif isinstance(dMime, dict):
				self.dMime = dMime
				if len(dMime) == 1:
					self.sDefMime = dMime.keys()[0]
				else:
					if not ('mimedef' in dArgs):
						raise DasCliError("mimedef missing, but more that one mime"+\
						                  " specified for the reader")
					self.sDefMime = dArgs['mimedef']
					if not (self.sDefMime in self.dMime):
						raise DasCliError("mimedef '%s' isn't a "%self.sDefMime+\
						                  "keyword in the mime dictonary")
			else:
				DasCliError("mime value must be a dictorary or a string")
						                  
		else:
			self.dMime = {None: '(output mime-type not specified)'}
			
		self.sels = DasCliSet()
		self.outs = DasCliSet()
		
		# Start at info level, change if a -l or --log parameter are seen
		# on the command line
		
		sConFmt = '%(levelname)-8s: %(message)s'
		sDateFmt = '%Y-%m-%dT%H:%M:%S'
		
		self.log = logging.getLogger('')
		self.log.setLevel(logging.INFO)
		
		conHdlr = logging.StreamHandler(sys.stderr)
		formatter = logging.Formatter(sConFmt, sDateFmt)
		conHdlr.setFormatter(formatter)
		self.log.addHandler(conHdlr)
		
		self.sQuery = None  # Save off the normalized (not das2.1) 
		                    # command line query
				
	
	########################################################################
	def addSelector(self, sKey, sName, **dArgs):
		"""Add a data selector to the command line parser.  It is possible
		for a reader to have no selectors, but this rare to nonexisitant.
		
		sKey - a key value for this selector, must be all lower case, with no
		      spaces. examples would be 'scet', 'long', 'lat', 'filter'.
				
		sName - A more proper name for this selector
		
		intype - The value type for the selector must be one of 
		      'bool', 'int', 'real', 'str', 'timept'
		
		config - If True, this is not a general selector, but a configuration
		      parameter
				
		min - Allowed minimum for the selector value, not valid if type='bool'
		      or an enum list is set
		
		max - Allowed maximim for the selector value, not valid if type='bool'
		      or an enum list is set
		
		summary - A human readable description of the data selector
		 
		compare - A list of allowed comparison operators.  One or more of
		      '.eq.', '.ne.', '.lt.', '.gt.', '.le.', '.ge.' may be specified.
				If this parameter is not given all comparison operators are
				allowed.  Unless the type is 'bool' or the an 'enum' list is set.
		
		enum - A list of exact values the selector can take, the values will
		      be converted to the type listed in 'type'.
		
		default - A list of default boundaries, one for each comparison.  For
		      example to set a default start time, but no default end time
				use:
				
				   compare=['ge','lt'], default=[DasTime('2013-001'), None]
					
				Boolean and enumeration selectors have a single implicit 
				comparison, 'eq'.  So you can set a default for an enumeration
				like so:
				
				   enum=['cat','dog','rat'], default="dog"
					
		required - If true, this selector must be specified for a valid
		      data query.  The use of required selectors is discouraged.
				If all comparisons have a default this must be False (or
				not specified)
				
		data - Any user data object to be accessible from the selector object
		      defaults to None
		"""		
		sel = Selector(sKey, sName, dArgs)
		self.sels.add(sel)
		

	########################################################################
	def addOutput(self, sKey, sName, **dArgs):
		"""Add an output for this reader.  An output corresponds to 
		an axis.  For single value outputs (i.e. a scaler) one call to this
		function is needed.  An example would be a reader that provides the
		current temperature in a given room.  For two-value outputs (i.e. 
		poly-lines) two calls are needed.  An example would be Fce versus time.
		For three-value outputs three calls are needed.  An example would be
		spectral density versus frequency bin center and time.
		
		sKey - A name for this output, must be a lowercase token (no spaces or
		       weird characters)
					
		sName - A human readable name for this output
					
		summary - A string describing the output
		
		units - A string providing the units.  The preferred form is:
				 
				   units := UNIT [SPACE UNIT [ SPACE UNIT [ ... ] ] ]
				 
               UNIT := SI_UNIT**POWER | '[' NON_SI_UNIT ']'**POWER
				 
               SI_UNIT := SI unit strings (i.e. Kg KHz m s V W)
				 
               NON_SI_UNIT := any string
				 				 
               POWER := non-zero integer
				 
				 Examples:
				 
				   "V**2 m**-2 Hz**-1"
					
				   "[counts] Hz**-1"
					
					"[hamburgers] [tray]**-1 s**-1"
		
		label - A plot label for this output dimension, many das2 clients
		        will understand Grandle and Nystrom (1980) formatting
				  characters, this is a good place to use them.
				  If not specified this will default to units.
		
		optional - True|False, if True then an argument of the form:
		
		       skey.out.off
				 
				 can be used to turn off this output.
				 
		enabled - True|False, set the default state of the output, note
		        that if optional=False then enabled defaults to True, and
				  when optional=True enabled defaults to false.  Us this 
				  keyword to change the default behavior.
				  
		varres - True|False, defaults to false.  Set to true to enable
		       arguments of the form:
				 
				   skey.res.60
					
				 to set the output resolution of a dimension.  The expected
				 command line parameter is a float in the specified units.
				 
				 TODO: Allow for a specified set of output points on standard
				       input someday.
				  
		data -  Any user data object to be accessible from the output object,
		        defaults to None
				  
		Returns: An Output object
		"""
		
		# Label format is defined in:  "A method for usage of a large calligraphy
		#  set under RSX-11M. Grandle, R.E. and Nystrom, P.A. Proceedings of the
		# Digital Equipment Computer Users Society, November 1980, 391-395."
		
		out = Output(sKey, sName, dArgs)
		self.outs.add(out)
		
		return out
	
	########################################################################
	def makeSelector(self, out, **dArgs):
		"""Add a data selector that corresponds to a reader output value.
		
		Manditory arguments:
		
		out - An Output object, generated via addOutput()
		
		Keyword arguments:
		
		intype - The value type for the selector must be one of 
		      'bool', 'int', 'real', 'string', 'timept', 'enum'
				
		min - Allowed minimum for the selector value, not valid if type='bool'
		      or an enum list is set
		
		max - Allowed maximim for the selector value, not valid if type='bool'
		      or an enum list is set
		
		summary - A human readable description of the data selector
		 
		compare - A list of allowed comparison operators.  One or more of
		      '.eq.', '.ne.', '.lt.', '.gt.', '.le.', '.ge.' may be specified.
				If this parameter is not given all comparison operators are
				allowed.  Unless the type is 'bool' or the an 'enum' list is set.
		
		enum - A list of exact values the selector can take, the values will
		      be converted to the type listed in 'type'.
		
		default - A list of default boundaries, one for each comparison.  For
		      example to set a default start time, but no default end time
				use:
				
				   compare=['ge','lt'], default=[DasTime('2013-001'), None]
					
				Boolean and enumeration selectors have a single implicit 
				comparison, 'eq'.  So you can set a default for an enumeration
				like so:
				
				   enum=['cat','dog','rat'], default="dog"
					
		required - If true, this selector must be specified for a valid
		      data query.  The use of required selectors is discouraged.
				If all comparisons have a default this must be False (or
				not specified)
				
		data - Any user data object to be accessible from the selector object
		      defaults to None
		
		"""
		
		sKey = out.key
		sName = out.name
		dArgs['_units'] = out.units
		if not ('data' in dArgs):
			dArgs['data'] = out.data
		
		sel = Selector(sKey, sName, dArgs)
		self.sels.add(sel)
		
	
	########################################################################
	def printHelp(self):
	
		pout = sys.stdout.write
		
		# Das 2.1 compatibility: See if we have suitable begin end selectors
		nBegEndSels = 0
		sBegEndKey = ""
		for i in range(0, len(self.sels)):
			sel = self.sels[i]
			if sel.supportsOp('.ge.') and sel.supportsOp('.lt.'):
				nBegEndSels += 1
				sBegEndKey = sel.key
		
	
		# Das 2.1 compatibility: See if we have and adjustable resolution output
		nAdjRes = 0
		sResKey = ""
		sResHelp = ""
		for i in range(0, len(self.outs)):
			if self.outs[i].varres:
				nAdjRes += 1
				sResKey = self.outs[i].key
				if nAdjRes == 1:
					sResHelp = " --das2res=" + sResKey
				else:
					sResHelp = " --das2res=OUT"
			
		sMimeHelp = ""	
		if len(self.dMime) > 1:
			sMimeHelp = " --format=FMT"
	
		print("""
%s - A Das 2.1 and Das 2.2 compatible reader

Usage:
   %s -h [-? --help]
   %s%s KEY.OP.VAL KEY.OP.VAL KEY.OP.VAL ...
   %s%s --das2times=SEL START STOP KEY.OP.VAL ..."""%(
	self.sProgName, 
	self.sProgName, self.sProgName, sMimeHelp, self.sProgName, sMimeHelp))
	
		if nAdjRes > 0:
			print("""   %s%s --das2times=SEL%s START STOP RES KEY.OP.VAL ..."""%(
			      self.sProgName, sMimeHelp, sResHelp))
		
		print("")
		print("Description:")
		print( _text_wrap("   ", self.sDesc))
		print("")
		print( _text_wrap("   ", "%s outputs the following "%self.sProgName +\
		                 "correlated data values:\n"))
		print("")
		
		for i in range(0, len(self.outs)):
			out = self.outs[i]
			
			sWrap = out.name
			if out.units != None:
				sWrap += " in %s"%out.units
				
			if out.optional:
				sWrap += "  (optional, "
				if out.enabled:
					sWrap += "ON)"
				else:
					sWrap += "off)"
				
			print(_text_wrap2("   * ", "     ", sWrap))
			
			if out.summary != None:
				print(_text_wrap("     ", out.summary))
			pout('\n')
		
		if len(self.dMime) == 1:
			pout("   Data are output in the format:\n")
		else:
			pout("   Data are output in one of the following formats:\n")
			
		for sKey in self.dMime.keys():
			pout(_text_wrap("      ", "'%s' "%self.dMime[sKey]))
			pout('\n')
			
		if len(self.dMime) > 1:
			pout('   selectable by the --format option below.\n')
		
		pout('\n')
		
		
		print("""General Options:
   -h,-?,--help
      Print reader overview information and exit.""")

		print("""
   -v,--version
      Print reader version information and exit.""")
		
		print("""
   -l LEVEL,--log=LEVEL
      Select the logging level for the reader.  Here LEVEL is one of 'critical',
      'error','warning','info','debug'.  The default is 'info'.""")

		if nBegEndSels > 0:
			sSelVal = "SELECTOR"
			sTmp = "the named SELECTOR."
			if nBegEndSels == 1:
				sSelVal = sBegEndKey
				sTmp = "selector '%s'"%sBegEndKey

			print("""
   --das2times=%s
      Turn on Das 2.1 time range selection compatibility.  This will cause the
      first two command line parameters that do not contain operater tokens, to
      be treated as the '.ge.' and '.lt.' values for %s"""%(sSelVal, sTmp))
		
		if nAdjRes > 0:
			sOutVal = "OUTPUT"
			sTmp = "the named OUTPUT."
			if nAdjRes == 1:
				sOutVal = sResKey
				sTmp = "output '%s'"%sOutVal
				
			print("""
   --das2res=%s
      Turn on Das 2.1 resolution selection compatibility.  This will cause the
      third command line argument that does not contain an operator token, and
      which is not recognized as a special directive, to be treated as the
      resoluion value for %s
"""%(sOutVal, sTmp))

		
		if len(self.dMime) > 1:
			sWrap = "--format=[%s]"%' | '.join(self.dMime.keys())
			print(_text_wrap2("   ", "      ", sWrap))
			print("      Selects a data output format, choices are:")

			for sKey in self.dMime.keys():
				sWrap = "%s - '%s'"%(sKey, self.dMime[sKey])
				print(_text_wrap2("         ", "            ", sWrap))
			
			print("      The default is %s."%self.sDefMime)


		print("\nData Selection Options:")
		
		if len(self.sels) == 0:
			print("   This reader has no data selection options, you get what "+\
			      "you get.")
		else:
			for i in range(0, len(self.sels)):
				sel = self.sels[i]
				
				if len(sel.compare) == 1:
					pout("   %s%s%s"%(sel.key, sel.compare[0], sel.typeMeta()) )
				else:
					pout('   %s.OP.%s'%(sel.key, sel.typeMeta()))
					
				if sel.required:
					pout('  (required)')
				pout('\n')
				
				sWrap = "Select data using the %s. "%sel.name
				
				# Give the where clauses				
				if sel.enum != None:
					sWrap = "Where %s is one of [ %s ].\n"%(sel.typeMeta(), 
					          ", ".join( [ str(n) for n in sel.enum ] ) )
					
				elif sel.intype == 'bool':
					sWrap = "Where %s is one of 'true', 'false'.\n"%sel.typeMeta()

				else:
					if len(sel.compare) > 1:
						sWrap += "Here .OP. is one of: '%s'"%"', '".join( sel.compare) 
					
					if sel.min != None and sel.max != None:
						sWrap += ", and %s is between %s and %s."%(sel.typeMeta(), sel.min, sel.max)
					elif sel.min != None:
						sWrap += ", and %s is greater than or equal to %s."%(sel.typeMeta(), sel.min)
					elif sel.max != None:
						sWrap += ", and %s is less than %s."%(sel.typeMeta(), sel.max)
					else:	
						if len(sel.compare) > 1:
							sWrap += "."
							
				if sel.intype == 'timept':
					sWrap += " %s is any parseable UTC time string."%sel.typeMeta()
				elif sel._units != None:
					sWrap += " %s is in units of %s."%(sel.typeMeta(), sel._units)
									
				pout( _text_wrap("      ", sWrap))
				pout('\n')
				pout( _text_wrap("      ", sel.summary))
				pout('\n\n')
		
		# A check in the parse_args function makes sure we have at least one
		# output defined
		bHasOutOpt = False
		for i in range(0, len(self.outs)):
			if self.outs[i].optional or self.outs[i].varres:
				bHasOutOpt = True
				break
		
		if bHasOutOpt:
			print("Data Output Options:")
		
			for i in range(0, len(self.outs)):
				out = self.outs[i]
				
				if out.optional:
					if out.enabled:
						pout("   %s.out.off\n"%out.key)
						sWrap = "Turn off %s output."%out.name
					else:
						pout("   %s.out.on\n"%out.key)
						sWrap = "Turn on %s output."%out.name
												
					pout(_text_wrap("      ", sWrap))
					pout('\n\n')
					
				if out.varres:
					pout("   %s.res.REAL\n"%out.key)
					sWrap = "Set how often %s values are output"%out.name
					if out.resunits != None:
						sWrap += " in units of %s."%out.resunits
					else:
						sWrap += "."
					if out.defres != None:
						sWrap += "  By default REAL is %s."%out.defres
							
					pout(_text_wrap("      ", sWrap))
					pout('\n\n')
					
		if self.sFooter:
			pout(_text_wrap2("", "   ", self.sFooter))
			pout('\n')
		
		if self.sVersion:
			pout("Version:\n")
			for sLine in self.sVersion.split('\n'):
				pout(_text_wrap("   ", sLine))
				pout('\n')
			pout('\n')
		
		pout("Maintainer:\n")
		sWrap = "If you have problems with this reader or questions about "+\
		        "it's output contact:"
		pout(_text_wrap("   ", sWrap))
		print("")
		       
		if self.sTechContact != self.sSciContact:
			pout(_text_wrap("   ", "Technical: %s"%self.sTechContact))
			print("")
			pout(_text_wrap("   ", "Scientific: %s"%self.sSciContact))
		else:
			pout(_text_wrap("   ", self.sSciContact))
			
		pout('\n\n')
	
	########################################################################
	def writeDsid(self, fOut):
		"""Write a template DSID file based on the command line parameters
		to the file fOut
		"""
		fOut.write( \
'''<?xml version="1.0"?>
<!-- Schema File download: http://www-pw.physics.uiowa.edu/das2/das_dsid-2.2.xsd -->
<dasDSID xmlns="http://www.das2.org/dsid/2.2" name="UNKNOWN" >
  <summary>
    UNKNOWN
  </summary>

  <description>
    %s
  </description>

  <categories>
    <category type="Spacecraft" name="UNKNOWN" ref="UNKNOWN" >
	   <category type="Instrument" name="UKNOWN" ref="UNKNOWN" />
	 </category>
    <category type="Investigator" name="%s" />
  </categories>
  
  <maintainer name="%s" email="UNKNOWN" />
  
'''%(_text_wrap("    ", self.description), self.teck_contact, self.sci_contact)
	)
	
		fOut.write( '  <reader keepalive="false">\n')
		for skey in self.dMime.keys():
			fOut.write("  <formats>\n")
			fOut.write("    <format name='%s' mime='%s' />\n"%(sKey, self.dMime[sKey]))
			fOut.write("  </formats>\n")
	
		# Find out how I was invoked
			
		fOut.write('    <externalProcess interfaceVersion="2.2">\n')
		fOut.write('      <exec>%s</exec>\n')
		
	
	########################################################################
	def _hasOperator(self, sArg):
		lTmp = ['.beg.','.end.']
		lTmp += _g_lAllOps
	
		for op in lTmp:
			if sArg.find(op) != -1:
				return True
		
		return False

	
	########################################################################
	def _handleSpecialArgs(self, argv):
		
		lArgs = argv
		
		if len(argv) == 0:
			return []
		
		# help and exit
		for sArg in lArgs:
			if sArg in ['-h','--help','-?']:
				self.printHelp()
				sys.exit(0)
		
		# Version and exit
		for sArg in lArgs:
			if sArg in ['-v','--version']:
				self.printVersion()
				sys.exit(0)
		
		# Log level
		sLevel = ""
		i = 0
		while i < len(lArgs):
			
			# Eat all the -l and --log args
			if lArgs[i] == '-l':
				if i == (len(lArgs) - 1):
					self.log.error("Missing logging level value after '-l' option")
					sys.exit(14)
				sLevel = lArgs[i+1]
				lArgs.pop(i)
				lArgs.pop(i)
						
			elif lArgs[i].startswith('--log='):
				sLevel = lArgs[i].replace('--log=','')
				if sLevel == '':
					self.log.error("Missing logging level value after --log=")
					sys.exit(14)
				lArgs.pop(i)
			else:
				i += 1			
				
		# maybe set a new log level
		if sLevel != '':
			if sLevel.startswith("c"):
				nLevel = logging.CRITICAL
			elif sLevel.startswith("e"):
				nLevel = logging.ERROR
			elif sLevel.startswith("i"):
				nLevel = logging.INFO
			elif sLevel.startswith("d"):
				nLevel = logging.DEBUG
			else:
				self.log.error("Unknown log level value: %s"%sLevel)
				sys.exit(14)
			
			self.log.setLevel(nLevel)
		
		
		# Handle --dsid here
		i = 0
		while i < len(lArgs):
			if lArgs[i] in ['-d','--dsid']:
				self.writeDsid(sys.stdout)
				sys.exit(0)
			i += 1
		
		
		# Handle --das2res if present, 
		i = 0
		sResSel = ''
		while i < len(lArgs):
			
			if lArgs[i].startswith('--das2res='):
				sResSel = lArgs[i].replace('--das2res=', '')
				if sResSel == '':
					self.log.error("Missing output name after --das2res=")
					sys.exit(14)
				lArgs.pop(i)
			else:
				i += 1
		
		if sResSel != '':
			for i in range(0, len(lArgs)):
				if not lArgs[i].startswith('-') and not self._hasOperator(lArgs[i]):
					# note a common failure case is to not actually use a resolution
					# even though --das2res= was specified. Check to see if the
					# first value not das2.2 arg is just a time, if so skip 
					# the update to the argument
					
					try:
						float(lArgs[i])
						lArgs[i] = "%s.res.%s"%(sResSel, lArgs[i])
					except ValueError:
						self.log.warning("Cowardly refusing to set the resolution to the"
						                 " non-float %s"%lArgs[i])
					break
					
							
		# Handle --das2times if present
		i = 0
		sTimeSel = ''
		while i < len(lArgs):
			
			if lArgs[i].startswith('--das2times='):
				sTimeSel = lArgs[i].replace('--das2times=','')
				if sTimeSel == '':
					self.log.error("Missing selector name after --das2times=")
					sys.exit(14)
				lArgs.pop(i)
			else:
				i += 1
		
		if sTimeSel != '':
			# find two non specials, and change them
			nChanges = 0
			for i in range(0, len(lArgs)):
				if not lArgs[i].startswith('-') and not self._hasOperator(lArgs[i]):
					if nChanges == 0:
						lArgs[i] = "%s.ge.%s"%(sTimeSel, lArgs[i])
					else:
						lArgs[i] = "%s.lt.%s"%(sTimeSel, lArgs[i])
					nChanges += 1
				
				if nChanges == 2:
					break
					
		
		# Finally, take the last argument and unpack it if it's been crammed
		# together in das1 / das2.1 style.
		if len(lArgs) > 0:
			lLast = lArgs[-1].split()
			lArgs.pop(-1)
			lArgs += lLast
		
		return lArgs
		
	
	########################################################################
	def _parseArg(self, sArg):
		
		iOp = 0
		sLoArg = sArg.lower()
		sOp = ""
		for sOp in _g_lAllOps + ['.beg.','.end.']:
			iOp = sLoArg.find(sOp)
			if iOp != -1:
				break
		
		if iOp == -1:
			self.log.error("Operator missing in parameter %s"%sArg)
			sys.exit(14)
		
		if (iOp + len(sOp)) >= len(sArg):
			self.log.error("Value missing in parameter %s"%sArg)
			sys.exit(14)
		
		if iOp == 0:
			self.log.error("Selector or Output name missing in parameter %s"%sArg)
			sys.exit(14)
			
		# Convert .beg., .end.
		if sOp == '.beg.':
			_sOp = '.ge.'
		elif sOp == '.end.':
			_sOp = '.lt.'
		else:
			_sOp = sOp
		
		return (sArg[:iOp], _sOp, sArg[iOp + len(sOp):])
		
	
	########################################################################
	def parseArgs(self, argv):
		"""Parse a command line give the current set of selectors and outputs
		If -h, --help, or -? are encountered as options this function 
		prints help information to standard output and exits.
		
		Returns a three tuple containing the objects:
		   (SelectorSet, OutputSet, Logger)
			
		Five special argument sets are understood:
		
		 -l, --log=  (the logging level)
		 
		 -h,-?,--help (print help)
		 
		 -v, --version
		   Print the reader version and exit
			
       -d, --dsid
         Instead of querying for, and sending data, output a template
         DSID file to standard output.
		
		 --das2res=OUTPUT
		   Use the first non-special, non KEYWORD.OP.VAL parameter as 
			being the .res. setting for output OUTPUT
			
		 --das2times=SELECTOR
		   Use the first two non-special, non KEYWORD.OP.VAL parameter
			as being the .ge. and .lt. comparisons for selector KEYWORD.
			If --das2res is also specified, the second and third non
			special arguments become the times
		 
		 --format=FORMAT
		   Set the output format for the reader.  This is only usable
			if a value-to-mime type dictionary has been provided to the
			DasCli object constructor, and that dictionary contains more
			than one entry.
		"""
				
		if not isinstance(argv, list):
			raise ValueError("Expecting a list for argv")
			
		# At least one output has to be defined, but selectors aren't needed
		if len(self.outs) < 1:
			raise DasCliError("No outputs have been defined for this reader")
		
		
		lArgs = self._handleSpecialArgs(argv)
		self.sQuery = " ".join(lArgs)
		
		# Okay, we should have pure THING.OP.VALUE items now...
		for sArg in lArgs:
			(sKey, sOp, sVal) = self._parseArg(sArg)
			
			# Sel or out?
			bSel = False
			if (sKey in self.sels) and (sKey in self.outs):
				if sOp in _g_lAllOutOps:
					bOut = True
				elif sOp in _g_lAllSelOps:
					bSel = True
			elif sKey in self.sels:
				bSel = True
			elif sKey in self.outs:
				pass
			else:
				self.log.error("Keyword %s doesn't correspond to "%sKey +\
				               "any of the selectors or outputs.")
				sys.exit(14)

			if bSel:
				if not self.sels[sKey].supportsOp(sOp):
					self.log.error("Comparison operator %s is not "%sOp+\
					               "supported for selector %s"%sKey)
					sys.exit(14)
				
				try:
					self.sels[sKey].setBound(sOp, sVal)
				except ValueError as e:
					self.log.error("In parameter '%s': %s"%(sArg, str(e)))
					sys.exit(14)
			
			else:
				if sOp == '.res.':
					self.outs[sKey].setResolution(sVal)
				
				elif sOp == '.out.':
					self.outs[sKey].setEnabled(sVal)
				else:
					assert False
							
			
		
		bReady = True
		for sKey in self.sels.keys():
			if not self.sels[sKey].isReady(self.log):
				bReady = False
				
		if not bReady:
			sys.exit(14)
		
		return (self.sels, self.outs, self.log)
		
	
	########################################################################
	def getQuery(self):
		"""Returns the normalized query string provided from the command
		line (along with any non-null defaults that were given??)"""
		
		sQuery = self.sQuery
		
		return sQuery
