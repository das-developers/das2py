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


"""Small helpers for writing das2 and Q stream packets"""

import os
import struct

EXCEPT_NODATA = "NoDataInInterval"
EXCEPT_BADARG = "IllegalArgument"
EXCEPT_SRVERR = "ServerError"

# Check to see if we're python 2 or 3
g_nPyVer = 2
try:
	basestring
except NameError:
	g_nPyVer = 3
	basestring = str

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

##############################################################################
class HdrBuf(object):
	"""Write a Das2 or QStream UTF-8 buffer"""
	
	def __init__(self, nPktId, sFmt='das2'):
		if nPktId < 0 or nPktId > 99:
			raise ValueError("Invalid Packet ID: %s"%nPktId)
		
		self.sFmt = sFmt
		self.nPktId = nPktId
		
		if sFmt == 'qstream':
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
		sHdr = '[%02d]%06d'%(self.nPktId, nLen)
		xHdr = sHdr.encode('utf-8')
		
		fwrite(fOut, xHdr)
		fwrite(fOut, xOut)
		
		fOut.flush()
						
		if self.sFmt == 'qstream':
			self.lText = [u'<?xml version="1.0" encoding="UTF-8"?>\n']
		else:
			self.lText = []



##############################################################################
class PktBuf(object):
	"""Write python data values to a das2 or Q stream, defaults to little 
	endian"""
	def __init__(self, nPktId):
		if nPktId < 0 or nPktId > 99:
			raise ValueError("Invalid Packet ID: %s"%nPktId)
			
		self.nPktId = nPktId
		if g_nPyVer == 2:
			self.lBytes = [':%02d:'%self.nPktId]
		else:
			self.lBytes = [bytes(':%02d:'%self.nPktId, 'utf-8')]
		
		self.xOut = None
		
	def add(self, sTxt):
		"""Add a string or bytearray to the output packet.  These are copied
		as-is with no translation."""
		
		if g_nPyVer == 2:
			self.lBytes.append(sTxt)
		else:
			# For python3 we have to treat strings and bytes differently.  Seems
			# the python way is to use exceptions for normal branch control.  
			# this seems wrong, but a lot of python code does it.  Not sure why.
			try:
				self.lBytes.append(sTxt.encode('utf-8'))
			except AttributeError:
				self.lBytes.append(sTxt)
				
		self.xOut = None
		
	def _addReals(self, sFmt, lVals):
		if sFmt[0] not in ["=", "<", ">"]:
			raise ValueError("Unknown endianess indicator character '%s'"%sFmt[0]+\
			                 ", expected '=', '>', or '<'.")
		
		if isinstance(lVals, float):
			 sBytes = struct.pack(sFmt, lVals)
			 self.lBytes.append(sBytes)
		elif isinstance(lVals, int):
			sBytes = struct.pack(sFmt, float(lVals))
			self.lBytes.append(sBytes)
		else:
			for fVal in lVals:
				sBytes = struct.pack(sFmt, fVal)
				self.lBytes.append(sBytes)
				
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
		
	
	def length(self):
		"""Get the current size of the output buffer in bytes"""
		if self.xOut == None:
			if g_nPyVer == 2:
				self.xOut = ''.join(self.lText)
			else:
				self.xOut = b''.join(self.lText)
			
		# Following has to change for Python 3, but heck *everything* we do
		# has to change for python 3 since we deal with binary data all the
		# time.  Oh yea and thanks for breaking integer division truncation
		# Guido, that dosen't affect us at all (ugh).
		return len(self.xOut)
		
	def send(self, fOut):
		"""Sending clears the buffer"""
		if self.xOut == None:
			if g_nPyVer == 2:
				self.xOut = ''.join(self.lBytes)
			else:
				self.xOut = b''.join(self.lBytes)
		
		fwrite(fOut, self.xOut)	
		fOut.flush()
		
		if g_nPyVer == 2:
			self.lBytes = [':%02d:'%self.nPktId]
		else:
			self.lBytes = [bytes(':%02d:'%self.nPktId, 'utf-8')]
		
		self.xOut = None

		

##############################################################################
def sendComment(fOut, sType, sValue, sSource=""):
	sFmt = '<comment type="%s" value="%s" source="%s"/>\n'
	sOut = sFmt%(sType.replace('"', "'"), sValue.replace('"', "'"),
	             sSource.replace('"', "'"))				 
	fOut.write("[xx]%06d%s"%(len(sOut), sOut))
	
##############################################################################
def sendException(fOut, sType, sMsg):
	"""Send a formatted Das2 exception
	fOut - The file object to receive the XML error packet
	sType - The exception type. Use one of the pre-defined strings
	        EXCEPT_NODATA
	        EXCEPT_BADARG
	        EXCEPT_SRVERR
	sMsg - The error message
	"""
	
	sFmt = '<exception type="%s" message="%s" />\n'
	
	sMsg = sMsg.replace('\n', '&#13;&#10;').replace(u'"', u"'")		  
	
	sOut = sFmt%(sType.replace('"', "'"), sMsg)
	
	fOut.write("[xx]%06d%s"%(len(sOut), sOut))

##############################################################################
# Progress Messages

def sendTaskSize(fOut, sWho, nSize, err_log_func=None):
	"""Send a progress task size message.  This needs to be done first before
	calling SendProgress.
	
	fOut: A file-like object
	
	sWho: A string identifying the program or service reporting progress
	
	nSize: An integer giving the size of the overall task, 100 is commonly used
	
	err_log_func: May be None.  A callback to also write the message somewhere else. 
	       When this function is called any '<' and '>' characters are HTML
			 esacaped.
	"""
	sPkt = '<comment type="taskSize" value="%d" source="%s" />\n'%(nSize, sWho)
	if err_log_func != None:
		err_log_func(sPkt.replace("<","&lt;").replace(">","&gt;"))
		
	sOut = "[xx]%06d%s"%(len(sPkt), sPkt)
	fOut.write(sOut)
	
def sendProgress(fOut, sWho, nProg, err_log_func=None):
	"""Send a progress status update, this should be a number between 0 and 
	the size set in SendTaskSize

	fOut: A file-like object
	
	sWho: A string identifying the program or service reporting progress
	
	nProg: An integer giving the current progress, typically between 0 and 100
	
	err_log_func: May be None.  A callback to also write the message somewhere else. 
	       When this function is called any '<' and '>' characters are HTML
			 esacaped.
	"""
	sPkt = '<comment type="taskProgress" value="%d" source="%s" />\n'%(nProg, sWho)
	if err_log_func != None:
		err_log_func(sPkt.replace("<","&lt;").replace(">","&gt;"))
	sOut = "[xx]%06d%s"%(len(sPkt), sPkt)
	fOut.write(sOut)
