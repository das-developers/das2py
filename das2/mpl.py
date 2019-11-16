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


"""Small helpers for matplotlib, mostly with plot labels"""

import numpy

from . import dataset
from . import dastime


#def ph_binavg(varX, varY, varZ,

def range_label(item, units=None, nPrec=0):
	"""Given a das2 dataset dimension or ndarray, create a range string suitable
		for annotating a plot

		There is an optional argument of the precision.  For timestamps this
		is taken as the precision of the seconds field
	"""

	# TODO: Make this more robust.  It fails if the center variable is
	#       not present, it also doesn't account attempt to produce an
	#       exclusive upper bound like most of the rest of the ranges in
	#       das2

	# If input is a dimension, get the 1s index and last index of the center
	# variable
	if isinstance(item, dataset.Dimension):
		aCent = item.vars['center'].array
		_units = item.vars['center'].units
	else:
		aCent = item
		_units = units

	beg = aCent.min()
	end = aCent.max()

	if aCent.dtype.type == numpy.datetime64:
		dtBeg = dastime.DasTime(beg)
		dtEnd = dastime.DasTime(end)

		sBegDate = "%04d-%02d-%02d (%03d)"%(
			dtBeg.year(), dtBeg.month(), dtBeg.dom(), dtBeg.doy())

		sBegTime = "%02d:%02d:%02d"%(dtBeg.hour(), dtBeg.minute(), int(dtBeg.sec()))

		sEndDate = "%04d-%02d-%02d (%03d)"%(
			dtEnd.year(), dtEnd.month(), dtEnd.dom(), dtEnd.doy())

		sEndTime = "%02d:%02d:%02d"%(	dtEnd.hour(), dtEnd.minute(), int(dtEnd.sec()))

		if sBegDate == sEndDate:
			return "%s %s to %s UTC"%(sBegDate, sBegTime, sEndTime)
		else:
			return "%s %s to %s %s UTC"%(sBegDate, sBegTime, sEndDate, sEndTime)

		# TODO: Add in subseconds if nPrec > 0

	else:
		return "%.3e to %.3e %s"%(beg, end, units)

def ns1970_label(beg, end=None):
	"""Given an integer representing time since 1970-01-01, create a plot
	time range label
	"""

	if end==None:
		end = beg[1]
		beg = beg[0]

	# TODO: Make this round off if data are near the edge

	try:
		dtBeg = dastime.DasTime(numpy.datetime64(long(beg), 'ns'))
		dtEnd = dastime.DasTime(numpy.datetime64(long(end), 'ns'))
	except NameError:
		dtBeg = dastime.DasTime(numpy.datetime64(int(beg), 'ns'))
		dtEnd = dastime.DasTime(numpy.datetime64(int(end), 'ns'))

	sBegDate = "%04d-%02d-%02d (%03d)"%(
		dtBeg.year(), dtBeg.month(), dtBeg.dom(), dtBeg.doy())

	sBegTime = "%02d:%02d:%02d"%(dtBeg.hour(), dtBeg.minute(), int(dtBeg.sec()))

	sEndDate = "%04d-%02d-%02d (%03d)"%(
		dtEnd.year(), dtEnd.month(), dtEnd.dom(), dtEnd.doy())

	sEndTime = "%02d:%02d:%02d"%(	dtEnd.hour(), dtEnd.minute(), int(dtEnd.sec()))

	if sBegDate == sEndDate:
		return "%s %s to %s UTC"%(sBegDate, sBegTime, sEndTime)
	else:
		return "%s %s to %s %s UTC"%(sBegDate, sBegTime, sEndDate, sEndTime)

	# TODO: Add in subseconds if nPrec > 0



def label(sStr):
	"""Given a das2 property string convert Granny text to
	tex math strings
	"""

	# The full set of replacement strings are:
	#
	# !A - Shift up 1/2 line
	# !B - Shift down 1/2 line
	# !C - newline
	# !D - subscript
	# !U - superscript
	# !E - little super script
	# !I - little subscript
	# !N - Return to normal
	# !R - restore last saved position
	# !S - save current position
	# !K - reduce the font size
	# !! - Just an exclamation

	# TODO: We should handle property substitution here ex: %xCacheRange

	# This is a hack for initial examples, need to convert IDL/Das2 style
	# formatting to tex in general

	sOrig = sStr
	sNew = sStr

	sNew = sNew.replace("!a",'^{').replace('!A','^{')
	sNew = sNew.replace("!a",'^{').replace('!U','^{')
	sNew = sNew.replace("!b",'_{').replace('!B','_{')
	sNew = sNew.replace("!d",'_{').replace('!D','_{')
	sNew = sNew.replace("!n",'}').replace('!N','}')
	sNew = sNew.replace("!c", '\n').replace('!C','\n')

	if sOrig == sNew:
		return sOrig
	else:
		if '{' not in sNew:
			return sNew   # incase all that's changed are newlines
		else:
			sNew = sNew.replace(' ','\\ ')
			return '$\mathregular{' + sNew + '}$'


class TimeTicker(object):
	"""As of numpy 1.15 and matplotlib 2.2 the datetime64 is not supported
	in any data binning functions.  Because of this the recomendation is to
	cast the values as 'int64' and then label use this tick formatter to
	label the any datetime axes.

	All time values in das2 streams are be presented to python an numpy
	datetime64 values in units of nanoseconds.  The numpy epoch is always
	1970-01-01 regardless of the units.
	"""

	def __init__(self, beg, end=None):
		"""The start time and end time as int64 casts of datetime64 'ns'
		objects.
		"""

		if end==None:
			end = beg[1]
			beg = beg[0]

		# python 2/3 compatability:
		try:
			self.dtBeg = dastime.DasTime(numpy.datetime64(long(beg), 'ns'))
			self.dtEnd = dastime.DasTime(numpy.datetime64(long(end), 'ns'))
		except NameError:
			self.dtBeg = dastime.DasTime(numpy.datetime64(int(beg), 'ns'))
			self.dtEnd = dastime.DasTime(numpy.datetime64(int(end), 'ns'))

		self.interval = self.dtEnd - self.dtBeg


	def label(self, val, pos):
		"""Pass this function to Matplotlib, example usage:

		   fmtr = MplInt64DateFmt(x_array.min(), x_array.max())
		   ax.xaxis.set_major_formatter( FuncFormatter(fmtr.label) )

		"""
		#Assume no more than 10 major tics
		try:
			dt = dastime.DasTime(numpy.datetime64(long(val), 'ns'))
		except NameError:
			dt = dastime.DasTime(numpy.datetime64(int(val), 'ns'))

		if self.interval < 0.0001:
			# To nanosec
			return "%02d:%02d:%0.9f"%(dt.hour(), dt.minute(), dt.sec())

		elif self.interval < 0.01:
			# To microisec
			return "%02d:%02d:%0.6f"%(dt.hour(), dt.minute(), dt.sec())

		elif self.interval < 10.0:
			# To millisec
			return "%02d:%02d:%0.3f"%(dt.hour(), dt.minute(), dt.sec())

		elif self.interval < 600:
			# To seconds
			return "%02d:%02d:%0.0f"%(dt.hour(), dt.minute(), dt.sec())

		elif self.interval < 86400*4:
			# To minutes, with date
			return "%04d-%02d-%02d %02d:%02d"%(
				  dt.year(), dt.month(), dt.dom(), dt.hour(), dt.minute()
			)

		elif self.interval < 86400*4*365:
			# To day
			return "%04d-%02d-%02d"%(dt.year(), dt.month(), dt.dom())

		return "%04d"%(dt.year())


























