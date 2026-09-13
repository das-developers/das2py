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


"""Small helpers for writing das2, das3 and Q stream packets.

Every writer takes a format token, 'das2' (the default), 'das3' or
'qstream', and spells the packet tag and the out-of-band XML the way that
stream version does.  The default stays 'das2': that format is simple, many
programs speak nothing else, and it is not going away.

Input is flexible, output is conservative.  sendException() accepts the das2
or the das3 spelling of an exception type and always writes the one token
that is correct for the format it is emitting.

All helpers write bytes through the file object's binary buffer when it has
one (sys.stdout does) and to the object itself otherwise (a file opened
'wb'), so headers, data and out-of-band packets never reorder against each
other in a text layer.
"""

import struct

# Names the package re-exports.  Helpers, stdlib imports and module
# globals stay out of 'from das3.pkt import *'.
__all__ = [
	'EXCEPT_NODATA',
	'EXCEPT_BADARG',
	'EXCEPT_SRVERR',
	'EXCEPT_NOMATCHING',
	'EXCEPT_QUERYERR',
	'fwrite',
	'HdrBuf',
	'PktBuf',
	'sendComment',
	'sendException',
	'sendTaskSize',
	'sendProgress',
]

# Exception types.  The first three are the das2.2 spellings, the last two
# are what das3 calls the same conditions.  sendException() accepts any of
# them for either format and writes the format's own token; ServerError is
# the same in both.
EXCEPT_NODATA     = "NoDataInInterval"
EXCEPT_BADARG     = "IllegalArgument"
EXCEPT_SRVERR     = "ServerError"
EXCEPT_NOMATCHING = "NoMatchingData"
EXCEPT_QUERYERR   = "QueryError"

_dExcept2to3 = {EXCEPT_NODATA: EXCEPT_NOMATCHING, EXCEPT_BADARG: EXCEPT_QUERYERR}
_dExcept3to2 = dict((v, k) for (k, v) in _dExcept2to3.items())

_lFormats = ('das2', 'das3', 'qstream')

# Check to see if we're python 2 or 3
g_nPyVer = 2
try:
	basestring
except NameError:
	g_nPyVer = 3
	basestring = str


def _checkFmt(sFmt):
	if sFmt not in _lFormats:
		raise ValueError("Unknown stream format '%s', expected one of %s"%(
			sFmt, ', '.join(_lFormats)))
	return sFmt


def _xmlEscape(sText):
	"""The five XML entities, so a message with an ampersand or angle
	bracket cannot break the packet.  Applied to attribute values and to
	element body text alike."""
	return sText.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')\
	            .replace('"', '&quot;').replace("'", '&apos;')


def _toBytes(sText):
	if isinstance(sText, bytes):
		return sText
	return sText.encode('utf-8')


# Another python 3 hack, can't just write bytes to file anymore, noooooo.
# First we have find out if it has a buffer and use that instead.  Reminds
# me of the "helpful" VAX IO system.
#
# This is NOT a compatability hack, you have to do this in pure python 3
# code, what a PITA.

def fwrite(thing, stuff):
	try:
		b = thing.buffer
	except AttributeError:
		b = thing
	b.write(stuff)


def _sendOob(fOut, sTag2, sTag3, sFmt, sXml):
	"""Write one out-of-band (comment or exception) packet in the given
	format.  sTag3 is 'Ex' or 'Cx'; das2 and qstream both use [xx]."""
	xOut = _toBytes(sXml)
	if sFmt == 'das3':
		xHdr = _toBytes('|%s||%d|'%(sTag3, len(xOut)))
	else:
		xHdr = _toBytes('[%s]%06d'%(sTag2, len(xOut)))
	fwrite(fOut, xHdr)
	fwrite(fOut, xOut)
	fOut.flush()


##############################################################################
class HdrBuf(object):
	"""Accumulate a UTF-8 header and send it with the right packet tag.

	sFmt is 'das2' (default), 'das3' or 'qstream'.  In das3 a packet id of 0
	is the stream header and goes out as |Sx||len|; any other id is a packet
	header, |Hx|NN|len|.
	"""

	def __init__(self, nPktId, sFmt='das2'):
		if nPktId < 0 or nPktId > 99:
			raise ValueError("Invalid Packet ID: %s"%nPktId)

		self.sFmt = _checkFmt(sFmt)
		self.nPktId = nPktId
		self._reset()

	def _reset(self):
		if self.sFmt == 'qstream':
			self.lText = [u'<?xml version="1.0" encoding="UTF-8"?>\n']
		else:
			self.lText = []  # Always UTF-8 text

	def add(self, sTxt):
		"""Encodes a givin string as UTF-8 and appends the bytes to the
		output buffer"""
		if g_nPyVer == 2:
			self.lText.append(unicode(sTxt))
		else:
			self.lText.append(sTxt)

	def send(self, fOut):
		"""Sending clears the buffer"""
		uOut = u"".join(self.lText)
		xOut = uOut.encode('utf-8')
		nLen = len(xOut)

		if self.sFmt == 'das3':
			if self.nPktId == 0:
				sHdr = '|Sx||%d|'%nLen
			else:
				sHdr = '|Hx|%02d|%d|'%(self.nPktId, nLen)
		else:
			sHdr = '[%02d]%06d'%(self.nPktId, nLen)

		fwrite(fOut, sHdr.encode('utf-8'))
		fwrite(fOut, xOut)
		fOut.flush()
		self._reset()


##############################################################################
class PktBuf(object):
	"""Write python data values to a das2, das3 or Q stream, defaults to
	little endian.

	das2 and qstream data packets carry only a :NN: tag, das3 packets carry
	their byte length too, |Pd|N|len|, so the tag is written at send time.
	"""

	def __init__(self, nPktId, sFmt='das2'):
		if nPktId < 0 or nPktId > 99:
			raise ValueError("Invalid Packet ID: %s"%nPktId)

		self.sFmt = _checkFmt(sFmt)
		self.nPktId = nPktId
		self.lBytes = []
		self.xOut = None

	def add(self, sTxt):
		"""Add a string or bytearray to the output packet.  Strings are
		encoded as UTF-8, bytes are copied as-is with no translation."""
		self.lBytes.append(_toBytes(sTxt))
		self.xOut = None

	def _addReals(self, sFmt, lVals):
		if sFmt[0] not in ["=", "<", ">"]:
			raise ValueError("Unknown endianess indicator character '%s'"%sFmt[0]+\
			                 ", expected '=', '>', or '<'.")

		if isinstance(lVals, float):
			self.lBytes.append(struct.pack(sFmt, lVals))
		elif isinstance(lVals, int):
			self.lBytes.append(struct.pack(sFmt, float(lVals)))
		else:
			for fVal in lVals:
				self.lBytes.append(struct.pack(sFmt, fVal))

		self.xOut = None

	def addFloats(self, lVals, cEndian="<"):
		"""Adds 1 or more 32-bit floating point value in native byte order to
		the packet.  Input argument can be a single number, float, or a list or
		tuple of floats.  The optional endian argument can be used to specify
		the byte order.  By default little endian '<' is used.  Use '<' for
		least significant byte first (little endian) or '>' for most significant
		byte first (big endian).
		"""
		self._addReals("%sf"%cEndian, lVals)

	def addDoubles(self, lVals, cEndian="<"):
		"""Adds 1 or more 64-bit floating point value in native byte order to
		the packet.  Input argument can be a single number, float, or a list or
		tuple of floats.  The optional endian argument can be used to specify
		the byte order.  By default little endian '<' is used.  Use '<' for
		least significant byte first (little endian) or '>' for most significant
		byte first (big endian).
		"""
		self._addReals("%sd"%cEndian, lVals)

	def _payload(self):
		if self.xOut is None:
			self.xOut = b''.join(self.lBytes)
		return self.xOut

	def length(self):
		"""The payload size in bytes, not counting the packet tag"""
		return len(self._payload())

	def send(self, fOut):
		"""Sending clears the buffer"""
		xOut = self._payload()
		if self.sFmt == 'das3':
			sTag = '|Pd|%d|%d|'%(self.nPktId, len(xOut))
		else:
			sTag = ':%02d:'%self.nPktId

		fwrite(fOut, sTag.encode('utf-8'))
		fwrite(fOut, xOut)
		fOut.flush()

		self.lBytes = []
		self.xOut = None


##############################################################################
def sendComment(fOut, sType, sValue, sSource="", sFmt='das2'):
	"""Send a comment packet.  das2 carries the value as an attribute, das3
	as the element body, and das3 omits an empty source attribute."""
	_checkFmt(sFmt)
	sType = _xmlEscape(sType); sValue = _xmlEscape(sValue); sSource = _xmlEscape(sSource)
	if sFmt == 'das3':
		if sSource:
			sOut = '<comment type="%s" source="%s">%s</comment>\n'%(sType, sSource, sValue)
		else:
			sOut = '<comment type="%s">%s</comment>\n'%(sType, sValue)
	else:
		sOut = '<comment type="%s" value="%s" source="%s"/>\n'%(sType, sValue, sSource)
	_sendOob(fOut, 'xx', 'Cx', sFmt, sOut)


##############################################################################
def sendException(fOut, sType, sMsg, sFmt='das2'):
	"""Send a formatted das exception

	fOut - The file object to receive the XML error packet
	sType - The exception type.  Any of the pre-defined strings, in the das2
	        spelling (EXCEPT_NODATA, EXCEPT_BADARG, EXCEPT_SRVERR) or the das3
	        one (EXCEPT_NOMATCHING, EXCEPT_QUERYERR); the token written is
	        the one correct for sFmt.  Other strings pass through as given.
	sMsg - The error message
	sFmt - 'das2' (default) writes the message as an attribute, 'das3' as the
	       element body
	"""
	_checkFmt(sFmt)
	if sFmt == 'das3':
		sType = _dExcept2to3.get(sType, sType)
	else:
		sType = _dExcept3to2.get(sType, sType)

	sType = _xmlEscape(sType)
	if sFmt == 'das3':
		sOut = '<exception type="%s">%s</exception>\n'%(sType, _xmlEscape(sMsg))
	else:
		# das2 readers expect newlines in the attribute as character references
		sMsg = _xmlEscape(sMsg).replace('\n', '&#13;&#10;')
		sOut = '<exception type="%s" message="%s" />\n'%(sType, sMsg)
	_sendOob(fOut, 'xx', 'Ex', sFmt, sOut)


##############################################################################
# Progress Messages

def _sendProgressPkt(fOut, sType, nVal, sWho, err_log_func, sFmt):
	_checkFmt(sFmt)
	sPkt = '<comment type="%s" value="%d" source="%s" />\n'%(
		sType, nVal, _xmlEscape(sWho))
	if err_log_func != None:
		err_log_func(sPkt.replace("<","&lt;").replace(">","&gt;"))
	_sendOob(fOut, 'xx', 'Cx', sFmt, sPkt)

def sendTaskSize(fOut, sWho, nSize, err_log_func=None, sFmt='das2'):
	"""Send a progress task size message.  This needs to be done first before
	calling SendProgress.

	fOut: A file-like object

	sWho: A string identifying the program or service reporting progress

	nSize: An integer giving the size of the overall task, 100 is commonly used

	err_log_func: May be None.  A callback to also write the message somewhere else.
	       When this function is called any '<' and '>' characters are HTML
	       esacaped.

	sFmt: 'das2' (default) or 'das3'; the comment element is the same in
	       both, only the packet tag differs.
	"""
	_sendProgressPkt(fOut, 'taskSize', nSize, sWho, err_log_func, sFmt)

def sendProgress(fOut, sWho, nProg, err_log_func=None, sFmt='das2'):
	"""Send a progress status update, this should be a number between 0 and
	the size set in SendTaskSize

	fOut: A file-like object

	sWho: A string identifying the program or service reporting progress

	nProg: An integer giving the current progress, typically between 0 and 100

	err_log_func: May be None.  A callback to also write the message somewhere else.
	       When this function is called any '<' and '>' characters are HTML
	       esacaped.

	sFmt: 'das2' (default) or 'das3'
	"""
	_sendProgressPkt(fOut, 'taskProgress', nProg, sWho, err_log_func, sFmt)
