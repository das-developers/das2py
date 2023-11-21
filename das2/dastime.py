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


import time
import numpy
import datetime
import sys
import math as M


import _das2


# Check to see if we're python 2 or 3
g_nPyVer = 2
try:
	basestring
except NameError:
	g_nPyVer = 3
	basestring = str
	
##############################################################################
# Wrapper class for libdas2 das_time structure

g_dDt64Scale = {'D':86400.0, 'h':3600.0, 'm':60.0, 's':1.0, 'ms':1e-3, 
                'us': 1e-6, 'ns': 1e-9 }

class DasTime(object):
	"""A wrapper for the old daslib functions, parsetime and tnorm,
	as well as adding features that let one do comparisons on dastimes
	as well as use them for dictionary keys.
	"""

	@classmethod
	def from_string(cls, sTime):
		"""Static method to generate a DasTime from a string, uses the
		   C parsetime to get the work done"""
		t = _das2.parsetime(sTime)
		return cls(t[0], t[1], t[2], t[4], t[5], t[6])
		
	@classmethod
	def now(cls):
		"""Static method to generate a DasTime for right now."""
		#print t
		t = time.gmtime()
		#print t[6]
		rSec = time.time()
		#print rSec
		fSec = t[5] + (rSec - int(rSec))
		#print fSec
		return cls(t[0], t[1], t[2], t[3], t[4], fSec)
		
		
	dDaysInMon = (
		(0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31),
		(0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
	)		
			
	def __init__(self, nYear=0, nMonth=0, nDom=0, nHour=0, nMin=0, fSec=0.0):
		"""Initalize from field values
		
		Note: If nYear is a string, and all other values are zero, then 
		      parsetime is called to generate the field values from the time
				string.
		"""
		
		# Handle bytes to string conversion up front
		if (sys.version_info[0] > 2) and isinstance(nYear, bytes):
			nYear = nYear.decode('utf-8')
		
		# Initialize from any type of string
		if isinstance(nYear, basestring):
			try:	
				tTmp = _das2.parsetime(nYear)
				(nYear, nMonth, nDom, nDoy, nHour, nMin, fSec) = tTmp
			except ValueError as e:
				raise ValueError("String '%s' was not parseable as a datetime"%nYear)
			
		# Initialize from a python datetime
		elif isinstance(nYear, datetime.datetime):
			pdt = nYear
			nYear = pdt.year
			nMonth = pdt.month
			nDom = pdt.day
			nHour = pdt.hour
			nMin = pdt.minute
			fSec = float(pdt.second) + (pdt.microsecond / 1000000.0)
			
		# initialize form a numpy datetime64
		elif isinstance(nYear, numpy.datetime64):
			
			# Numpy's decision to print local time is very irritating.  Get epoch seconds
			nEpoch = nYear.astype(int)
			sType = nYear.dtype.str
			sType = sType[sType.find('[') + 1 : sType.find(']') ] # Gives timestamp units
			
			# datetime64 always uses the unix epoch, but at different units.
			r1970 = nEpoch * g_dDt64Scale[sType]
			
			tTmp = _das2.parse_epoch(r1970, "t1970")
			(nYear, nMonth, nDom, nDoy, nHour, nMin, fSec) = tTmp
			
			
		# Initialize float plus das2 epoch units 
		elif isinstance(nMonth, str):
			tTmp = _das2.parse_epoch(nYear, nMonth)
			(nYear, nMonth, nDom, nDoy, nHour, nMin, fSec) = tTmp
			
		elif isinstance(nYear, DasTime):
			# Just work as a copy constructor
			nMonth = nYear.t[1]
			nDom = nYear.t[2]
			nHour = nYear.t[4]
			nMin = nYear.t[5]
			fSec = nYear.t[6]
			nYear = nYear.t[0]
			
		
		# Assume years less than 100 but greater than 57 are old 2 digit years
		# that need to be incremented.  I don't like this but what can
		# you do when reading old data.
			
		if isinstance(nYear, (tuple, list)):
			self.t = [0, 0, 0, 0, 0, 0, 0.0]
			for i in xrange(0, len(nYear)):
				j = i
				if i >= 3:
					j = i+1
				self.t[j] = nYear[i]
				
			if self.t[0] < 100 and self.t[0] > 57:
				self.t[0] = self.t[0] + 1900
			
			self.t = list( _das2.tnorm(t[0], t[1], t[2], t[4], t[5], t[6]) )
		else:
			if nYear < 100 and nYear >= 57:
				nYear += 1900
						
			self.t = list( _das2.tnorm(nYear, nMonth, nDom, nHour, nMin, fSec) )
		
		if abs(self.t[0]) > 9999:
			raise OverflowError("Year value is outside range +/- 9999")
	
	def __repr__(self):
		return "DasTime('%s')"%self.__str__()
		        
	def __str__(self):
		"""Prints an ISO 8601 standard day-of-month time string to microsecond
		resolution."""
		return '%04d-%02d-%02dT%02d:%02d:%09.6f'%(self.t[0], self.t[1],
		           self.t[2], self.t[4], self.t[5], self.t[6])

	def isoc(self, nSecPrec):
		"""Returns an ISO 8601 standard day-of-month time string to arbitrary
		seconds precision"""
		if nSecPrec < 0:
			raise ValueError("Precision must be >= 0");
		elif nSecPrec == 0:
			return '%04d-%02d-%02dT%02d:%02d:%02d'%(
				self.t[0], self.t[1], self.t[2], self.t[4], self.t[5], 
				round(self.t[6])
			)
		else:
			sFmt = '%%04d-%%02d-%%02dT%%02d:%%02d:%%0%d.%df'%(nSecPrec+3, nSecPrec)
			return sFmt%(
				self.t[0], self.t[1], self.t[2], self.t[4], self.t[5], self.t[6]
			)

	def isod(self, nSecPrec):
		"""Returns an ISO 8601 standard day-of-year time string to arbitrary
		seconds precision"""
		if nSecPrec < 0:
			raise ValueError("Precision must be >= 0");
		elif nSecPrec == 0:
			return '%04d-%03dT%02d:%02d:%02d'%(
				self.t[0], self.t[3], self.t[4], self.t[5], round(self.t[6])
			)
		else:
			sFmt = '%%04d-%%03dT%%02d:%%02d:%%0%d.%df'%(nSecPrec+3, nSecPrec)
			return sFmt%(
				self.t[0], self.t[3], self.t[4], self.t[5], self.t[6]
			)
	
	# This is only useful for Python 2.x
	
	# Have to go the long way by Laura's house to to get the same thing on
	# python 3.  Python didn't used to be so hung up on idelogical purity,
	# what happened?
	def __cmp__(self, other):
		if not isinstance(other, DasTime):
			return 1
			
		nCmp = cmp(self.t[0], other.t[0])
		if nCmp != 0:
			return nCmp
			
		nCmp = cmp(self.t[1], other.t[1])
		if nCmp != 0:
			return nCmp

		nCmp = cmp(self.t[2], other.t[2])
		if nCmp != 0:
			return nCmp

		nCmp = cmp(self.t[4], other.t[4])
		if nCmp != 0:
			return nCmp

		nCmp = cmp(self.t[5], other.t[5])
		if nCmp != 0:
			return nCmp
	
		return cmp(self.t[6], other.t[6])
		
	# Well, let's go work in the GD salt mines.  Jeeze, this is irritating.
	# Thanks Python 3
	def __eq__(self, other):
		if not isinstance(other, DasTime):
			return False
		a = (self.t[0], self.t[1], self.t[2], self.t[4], self.t[5], self.t[6])
		b = (other.t[0], other.t[1], other.t[2], other.t[4], other.t[5], other.t[6])
		return a == b

	
	def __ne__(self, other):
		if not isinstance(other, DasTime):
			return True
		a = (self.t[0], self.t[1], self.t[2], self.t[4], self.t[5], self.t[6])
		b = (other.t[0], other.t[1], other.t[2], other.t[4], other.t[5], other.t[6])
		return a != b

	
	def __lt__(self, other):
		if not isinstance(other, DasTime):
			return NotImplemented
		a = (self.t[0], self.t[1], self.t[2], self.t[4], self.t[5], self.t[6])
		b = (other.t[0], other.t[1], other.t[2], other.t[4], other.t[5], other.t[6])
		return a < b
		
	def __gt__(self, other):
		if not isinstance(other, DasTime):
			return NotImplemented
		a = (self.t[0], self.t[1], self.t[2], self.t[4], self.t[5], self.t[6])
		b = (other.t[0], other.t[1], other.t[2], other.t[4], other.t[5], other.t[6])
		return a > b
		
	def __le__(self, other):
		if not isinstance(other, DasTime):
			return NotImplemented
		a = (self.t[0], self.t[1], self.t[2], self.t[4], self.t[5], self.t[6])
		b = (other.t[0], other.t[1], other.t[2], other.t[4], other.t[5], other.t[6])
		return a <= b
	
	def __ge__(self, other):
		if not isinstance(other, DasTime):
			return NotImplemented
		a = (self.t[0], self.t[1], self.t[2], self.t[4], self.t[5], self.t[6])
		b = (other.t[0], other.t[1], other.t[2], other.t[4], other.t[5], other.t[6])
		return a >= b

	
	def __hash__(self):
		"""Compute a 64-bit hash that is useable down to microsecond
		resolution over the years +/- 9,999.  So, not great for geologic 
		time, nor for signal propagation times on microchips"""
		return self.__long__()
	
	
	def __long__(self):
		"""Cast the dastime to a long value, mostly only good as
		a hash key, but placed here so that you can get the hash easily"""
		
		lHash = self.t[0] * 100000000000000
		
		# Use doy in the hash to save digits
		lHash += self.t[3] *   100000000000
		
		nSecOfDay = self.t[4] * 3600
		nSecOfDay += self.t[5] * 60
		nSecOfDay += int(self.t[6])
		
		lHash += nSecOfDay *        1000000
		
		nMicroSec = int( (int(self.t[6]) - self.t[6] ) * 1000000 )
		
		lHash += nMicroSec
		return lHash
		
	
	def __nonzero__(self):
		"""Used for the boolean 'is true' test"""
		for i in [0,1,2,4,5,6]:
			if self.t[i] != 0:
				return True
		
		return False
		
			
	def norm(self):
		"""Normalize the time fields so that all contain legal values."""
		tNew = _das2.tnorm(self.t[0], self.t[1], self.t[2], self.t[4], self.t[5],
		               self.t[6])
		self.t = list( tNew )
		
	def mj1958(self):
		"""Get the current time value as seconds since January 1st 1958, ignoring
		leap seconds"""
		return _das2.ttime(self.t[0], self.t[1], self.t[2], self.t[4], self.t[5],
		               self.t[6])
							
	def t2000(self):
		return self.mj1958() - _das2.ttime(2000, 1, 1)


	def epoch(self, sUnits):
		"""Get a ticks-from-the-epoch value for this DasTime.

		Args:
			sUnits - The time offset units.  One of: 
			'mj1958' - Floating point days since midnight, Jan. 1st 1958 (no leapseconds)
			't1970'  - POSIX Time, non-leap seconds since midnight, Jan. 1st 1970
			'ns1970' - NumPy Time, non-leap nanoseconds since midnight, Jan. 1st 1970
			't2000'	- Non-leap Seconds since midnight, Jan. 1st 2000
			'us2000' - Non-leap microseconds since midnight, Jan. 1st 2000
			'TT2000' - ALL nanoseconds since 2000-01-01T11:58:55.816

		Note: Of the systems above, *only* TT2000 is leap-second aware.
		"""
		return _das2.to_epoch(
			sUnits, self.t[0], self.t[1], self.t[2], 
			        self.t[4], self.t[5], self.t[6]
		)
		
		
	def adjust(self, nYear, nMonth=0, nDom=0, nHour=0, nMin=0, fSec=0.0):
		"""Adjust one or more of the field, either positive or negative,
		calls self.norm internally"""
		
		if nYear == 0 and nMonth == 0 and nDom == 0 and nHour == 0 and \
		   nMin == 0 and fSec == 0.0:
			return
			
		t = [self.t[0] + nYear, 
		     self.t[1] + nMonth,
		     self.t[2] + nDom,
		     self.t[4] + nHour,
		     self.t[5] + nMin,
		     self.t[6] + fSec]
			  		
		self.t = list( _das2.tnorm(t[0], t[1], t[2], t[3], t[4], t[5]) )
				
	
	def copy(self, inc_yr=0, inc_mon=0, inc_dom=0, inc_hr=0, inc_min=0, inc_sec=0.0):
		return DasTime(
			self.year()   + inc_yr, 
			self.month()  + inc_mon, 
			self.dom()    + inc_dom, 
			self.hour()   + inc_hr,
			self.minute() + inc_min, 
			self.sec()    + inc_sec
		)
							
	###########################################################################
	def floor(self, nSecs):
		'''Find the nearest time, evenly divisable by nSec, that is 
		less that the current time value.
		'''
		
		if nSecs - int(nSecs) != 0:
			raise ValueError("%s is not an integer"%nSecs)		
		nSecs = int(nSecs)
		
		if nSecs < 1:
			raise ValueError("%s is < 1"%nSecs)
		
		elif nSecs == 1:
			self.t[6] = int(self.t[6])
		
		elif nSecs < 86400:
			
			nFloor = self.t[4]*60*60 + self.t[5]*60 + int(self.t[6])
			
			nFloor = (nFloor // nSecs) * nSecs
			
			self.t[4] = nFloor // (60*60)
			nRem = nFloor - (self.t[4]*60*60)
			
			self.t[5] = nRem // 60
			self.t[6] = float( nRem - (self.t[5] * 60) )
			
		elif nSec == 86400:
			self.t[4] = 0
			self.t[5] = 0
			self.t[6] = 0.0
			
		else:
			raise ValueError("Can't yet provide floor values for times > 1 day")
		
		
		self.t = list( _das2.tnorm(self.t[0], self.t[1], self.t[2], 
		                           self.t[4], self.t[5], self.t[6]) )
		
	###########################################################################
	def ceil(self, nSecs):
		"""Find the nearest time, evenly divisible by nSec that is greater
		than the current time value."""
		
		if nSecs - int(nSecs) != 0:
			raise ValueError("%s is not an integer"%nSecs)		
		nSecs = int(nSecs)
		
		if nSecs < 1:
			raise ValueError("%s is < 1"%nSecs)
		
		elif nSecs == 1:
			rFrac = self.t[6] - int(self.t[6])
			if rFrac > 0.0:
				self.t[6] = int(self.t[6]) + 1
		
		elif nSecs < 86400:
			
			nSecOfDay = self.t[4]*60*60 + self.t[5]*60 + int(M.ceil(self.t[6]))
			
			nFloor = (nSecOfDay // nSecs) * nSecs
			
			if nSecOfDay - nFloor == 0:
				nCeil = nFloor
			else:
				nCeil = nFloor + nSecs
				
			self.t[4] = nCeil // (60*60)
			nRem = nCeil - (self.t[4]*60*60)
			
			self.t[5] = nRem // 60
			nRem = nRem - (self.t[5]*60)
			
			self.t[6] = float(nRem)
			
		elif nSecs == 86400:
			if (self.t[4] > 0) or (self.t[5] > 0) or (self.t[6] > 0.0):
				self.t[2] += 1
			
			self.t[4] = 0
			self.t[5] = 0
			self.t[6] = 0.0	
			
		else:
			raise ValueError("Can't yet provide floor values for times > 1 day")
			
		
		self.t = list( _das2.tnorm(self.t[0], self.t[1], self.t[2], 
		                           self.t[4], self.t[5], self.t[6]) )
		
	
	###########################################################################
		
	def year(self):
		"""Get the year value for the time"""
		return self.t[0]
	
	def month(self):
		"""Get the month of year, january = 1"""
		return self.t[1]
	
	def dom(self):
		"""Get the calendar day of month"""
		return self.t[2]
	
	def doy(self):
		"""Get the day of year, Jan. 1st = 1"""
		return self.t[3]
	
	def hour(self):
		"""Get the hour of day on a 24 hour clock (no am/pm)"""
		return self.t[4]
	
	def minute(self):
		"""Get the minute of the hour"""
		return self.t[5]
	
	def sec(self):
		"""Get floating point seconds of the minute"""
		return self.t[6]
		
	def set(self, **dArgs):
		"""Set one or more fields, call self.norm internally keywords are
		
		  year  = integer
		  month = integer
		  dom   = integer (day of month)
		  doy   = integer (day of year, can't be used with month and dom)
		  hour  = integer 
		  minute = integer
		  seconds = float 
		"""
		for sKey in dArgs:
			if sKey == 'year':
				self.t[0] = dArgs['year']
			
			elif sKey == 'month':
				if 'doy' in dArgs:
					raise ValueError("Use either month or day of year but not both")
				self.t[1] = dArgs['month']
				
			elif sKey == 'dom':
				if 'doy' in dArgs:
					raise ValueError("Use either day of month or day of year but not both")
				self.t[2] = dArgs['dom']
			
			elif sKey == 'doy':
				if 'dom' in dArgs:
					raise ValueError("Use either day of month or day of year but not both")
				if 'month' in dArgs:
					raise ValueError("Use either month or day of year but not both")
				self.t[2] = dArgs['doy']
				self.t[1] = 1
				
			elif sKey == 'hour':
				self.t[4] = dArgs['hour']
				
			elif sKey == 'minute':
				self.t[5] = dArgs['minute']
				
			elif sKey == 'seconds':
				self.t[6] = dArgs['seconds']
			
			else:
				raise ValueError("Unknown keyword argument %s"%sKey)	
			
			
		self.norm()
	
	# Converting to a datetime	
	def pyDateTime(self):
	
		nSec = int(self.t[6])
		nMicroSec = int( 1000000.0 * (self.t[6] - float(nSec) ) )
	
		pdt = datetime.datetime(self.t[0], self.t[1], self.t[2], 
		                       self.t[4], self.t[5], nSec, nMicroSec)
		return pdt
		
	# Rounding with field bump
	
	
	def domLeapIdx(self, nYear):
	
		if (nYear % 4) != 0:
			return 0
		
		if (nYear % 400) == 0:
			return 1
			
		if (nYear % 100) == 0:
			return 0
		else:
			return 1

	
	# Arguments for round
	YEAR = 1
	MONTH = 2
	DOM = 3
	DOY = 13
	HOUR = 4
	MINUTE = 5
	SEC = 6
	MILLISEC = 7
	MICROSEC = 8
	
	def _getTimePart(self, nWhich):
		
		if nWhich not in (DasTime.MILLISEC, DasTime.SEC, DasTime.MICROSEC):
			raise ValueError("Seconds precision unknown, expected one of"+\
			                 " DasTime.SEC, DasTime.MILLISEC, or DasTime.MICROSEC")
		
		nRnd = 0
		if nWhich >= DasTime.SEC:
			nFracDig = 0
			if nWhich >= DasTime.MILLISEC:
				nFracDig += 3
			if nWhich >= DasTime.MICROSEC:
				nFracDig += 3
			
			if nFracDig > 0:
				sFmt = "%%0%d.%df"%(nFracDig + 3, nFracDig)
			else:
				sFmt = "%02.0d"
			
			sSec = sFmt%self.sec()
			
			if sSec[0] == '6':
				sSec = '0'+sSec[1:]
				nRnd += 1
			
		nMin = self.minute() + nRnd
		nRnd = 0
		
		if nMin > 59:
			nMin -= 60
			nRnd += 1
		
		nHour = self.hour() + nRnd
		nRnd = 0
		
		if nHour > 23:
			nHour -= 24
			nRnd += 1
		
		return ("%02d:%02d:%s"%(nHour, nMin, sSec), nRnd)
		
	
	def round(self, nWhich):
		"""Round off times to Seconds, Milliseconds, or Microseconds
		nWhich - One of the constants: SEC, MILLISEC, MICROSEC
		returns as string to the desired precision in Year-Month-Day format
		"""
		
		(sTime, nRnd) = self._getTimePart(nWhich)
		
		nDom = self.dom() + nRnd
		nRnd = 0
		
		nYear = self.year()
		nMonth = self.month()
		
		nDaysInMonth = DasTime.dDaysInMon[self.domLeapIdx(nYear)][nMonth]
		
		if nDom > nDaysInMonth:
			nDom -= nDaysInMonth
			nMonth += 1
		
		if nMonth > 12:
			nMonth -= 12
			nYear += 1
				
		return "%04d-%02d-%02dT%s"%(nYear, nMonth, nDom, sTime)
	
	
	def round_doy(self, nWhich):
		"""Round off times to Seconds, Milliseconds, or Microseconds
		nWhich - One of the constants: SEC, MILLISEC, MICROSEC
		returns as string to the desired precision in Year-Day format
		"""
		
		(sTime, nRnd) = self._getTimePart(nWhich)
		
		nDoy = self.doy() + nRnd
		
		nYear = self.year()
		
		nDaysInYear = 365
		if self.domLeapIdx(nYear) == 1:
			nDaysInYear = 366
		
		if nDoy > nDaysInYear:
			nYear += 1
			nDoy -= nDaysInYear
						
		return "%04d-%03dT%s"%(nYear, nDoy, sTime)
	
	
	def isLeapYear(self):
		"""Returns true if the year field indicates a leap year on the 
		gregorian calendar, otherwise return false.
		"""
		raise ValueError("Not yet implemented")
	
		
	###########################################################################
	# Operator overloads
	
	# This date to interger calculation isn't good for anything except
	# differencing taken form Tyler Durden's algorithm on stackoverflow
	#
	#  http://stackoverflow.com/questions/12862226/the-implementation-of-calculating-the-number-of-days-between-2-dates
	#
	
	def _subHelper(self):
		
		y = self.t[0]
		m = self.t[1]
		d = self.t[2]
		
		m = (m + 9) % 12
		y = y - m//10
		return 365*y + y//4 - y//100 + y//400 + (m*306 + 5)//10 + ( d - 1 )
		
	
	def __sub__(self, other):
		"""WARNING: This function works very differently depending on the
		type of the other object.  If the other item is a DasTime, then
		the difference in floating point seconds is returned.  
		
		If the other type is a simple numeric type than a new DasTime 
		is returned which is smaller than the initial one by 'other' seconds.
		
		Time subtractions between two DasTime objects are handled in a way
		that is sensitive to small differences.  Diferences a small as the 
		smalleset possible positive floating point value times 60 should be 
		preserved. 
		
		Time difference in seconds is returned.  This method should be valid
		as long as you are using the gegorian calendar, but *doesn't* account
		for leap seconds.  Leap second handling could be added via a table
		if needed.
		"""
		
		if isinstance(other, DasTime):
		
			fDiff = (self.t[4]*3600 + self.t[5]*60 + self.t[6])  - \
			        (other.t[4]*3600 + other.t[5]*60 + other.t[6])
		
			# Now convert days since 1970 as a unit, fastest way is to convert
			# to a julian date and subtract those.
			nDiff = self._subHelper() - other._subHelper()
			fDiff += nDiff * 86400.0
	
			return fDiff
		
		else:
			t = [self.t[0], self.t[1], self.t[2], self.t[4], self.t[5], 
		     self.t[6] - other]
		
			return DasTime( t[0], t[1], t[2], t[3], t[4], t[5] )
			
	
	
	def __isub__(self, other):
		
		t = [self.t[0], self.t[1], self.t[2], self.t[4], self.t[5], 
		     self.t[6] - other]
			  
		self.t = list( _das2.tnorm(t[0], t[1], t[2], t[3], t[4], t[5]) )
		
		return self

		
	def __add__(self, other):
		"""Add a floating point time in seconds to the current time point"""
		
		t = [self.t[0], self.t[1], self.t[2], self.t[4], self.t[5], 
		     self.t[6] + other]
		
		return DasTime( t[0], t[1], t[2], t[3], t[4], t[5] )
	
	def __radd__(self, other):
		return self.__add__(other)
		
	
	def __iadd__(self, other):
		
		t = [self.t[0], self.t[1], self.t[2], self.t[4], self.t[5], 
		     self.t[6] + other]
			  
		self.t = list( _das2.tnorm(t[0], t[1], t[2], t[3], t[4], t[5]) )
		
		return self
		
		
###############################################################################

import unittest
	
	
	
	
	
	
	
	
