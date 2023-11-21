# The MIT License
#
# Copyright 2022 Chris Piker
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


"""Pure Python das2.2 and das3.0 stream reader.  Currently only supports
das-basic-stream, but das-basic-doc is in the works.
"""

import sys
import os.path
from os.path import join as pjoin
from os.path import dirname as dname  
from io import BytesIO
import re
from typing import Union

import xml.parsers.expat  # Switch das2C to use libxml2 as well?
from lxml import etree


class HeaderError(Exception):
	def __init__(self, line, message):
		self.line = line
		self.message = message
		super().__init__(self.message)

class DataError(Exception):
	def __init__(self, pkt_type, pkt_id, pkt_number, message):
		self.pkt_type = pkt_type
		self.pkt_id = pkt_id
		self.pkt_num = pkt_number
		self.message = message
		super().__init__(self.message)	

g_lValidTags = (
	'Sx', # XML stream definition (parse for content)
	'Hx', # XML packet definition (parse for content)
	'Pd', # Packetize data, content defined by a header
	'Cx', # XML Comment packet (XML content)
	'Ex', # XML Exception packet (XML content)
	'XX'  # Extra packet, content completely unknown
)

# ########################################################################### #

g_sDas2BasicStream  = 'das-basic-stream-v2.2.xsd'
g_sDas3BasicStream  = 'das-basic-stream-v3.0.xsd'
g_sDas3BasicStreamNs = 'das-basic-stream-ns-v3.0.xsd' # Used when xmlns defined
g_sDas3BasicDoc     = 'das-basic-doc-ns-v3.0.xsd'

def getSchemaName(sContent, sVersion, bNameSpace=False):
	# If a fixed schema is given we have to load that
	if sContent == "das-basic-stream": 
		if sVersion.startswith('2'): return g_sDas2BasicStream
		if sVersion.startswith('3'): 
			if bNameSpace: 
				return g_sDas3BasicStreamNs
			else:
				return g_sDas3BasicStream

	elif sContent == "das-basic-doc":
		if sVersion.startswith('3'): return g_sDas3BasicDoc

	return None
	
def loadSchema(sContent, sVersion, bNameSpace=False):
	"""Load the appropriate das2 schema file from the package data location
	typcially this one of the files:

		$ROOT_DAS2_PKG/xsd/*.xsd

	Args:
		sContent - one of 'das-baisc-stream' or 'das-basic-doc'
		sVersion - The stream version number, typically 2.2 or 3.0

	Returns (schema, location):
		schema - An lxml.etree.XMLSchema object
		location - Where the schema was loaded from
	"""
	sMyDir = dname(os.path.abspath( __file__))
	sSchemaDir = pjoin(sMyDir, 'xsd')
	
	# If a fixed schema is given we have to load that
	sFile = getSchemaName(sContent, sVersion, bNameSpace)
	if not sFile:
		raise ValueError("Unknown stream content %s and version %s"%(
			sContent, sVersion
		))

	sPath = pjoin(sSchemaDir, sFile)	

	#print(sContent, sVersion, "-->", sPath)
	
	fSchema = open(sPath, encoding='utf-8')
	schema_doc = etree.parse(fSchema)
	schema = etree.XMLSchema(schema_doc)
	
	return (schema,sPath)

# ########################################################################### #
# Calculating expected packet lengths, required for v2.2, optional for V3.0

def _getDas2ValSz(sType, nLine):
	"""das2 type names always end in the size, just count backwards and 
	pull off the digits.  You have to get at least one digit
	"""
	sSz = ""
	for c in reversed(sType):
		if c.isdigit(): sSz += c
		else: break
	
	if len(sSz) == 0:
		raise HeaderError(nLine, "Encoding length not defined in value '%s'"%sType)

	sSz = ''.join(reversed(sSz))
	return int(sSz, 10)

def _getDas2PktLen(elDs, nPktId, bThrow=True):
	nSize = 0

	for child in elDs:
		nItems = 1
		
		# das2.2 had no extra XML elements in packet even in non-strict mode,
		# so everything should have a type attribute at this level
		if 'type' not in child.attrib:

			if bThrow:
				raise ValueError(
					"Attribute 'type' missing for element %s in packet ID %d"%(
					child.tag, nPktId
				))
			else:
				return None

		nSzEa = _getDas2ValSz(child.attrib['type'], child.sourceline)
		
		if child.tag == 'yscan':
			if 'nitems' in child.attrib:
				nItems = int(child.attrib['nitems'], 10)
		
		nSize += nSzEa * nItems
	
	return nSize

def _getDas3PktLen(elDs, nPktId, bThrow=True) -> Union[int, None]:
	
	# Das v3.0 data can have variable length array values in each packet
	# If the higher dimensional sizes are "*" then just return None
	#
	# This function does not throw on obvious schema errors, that's up to
	# the schema checker stage to worry about.
	nSize = 0


	# Look for general size, or fall back to specifics
	if "size" in elDs.attrib:
		sSize = elDs.attrib["size"]
		lSize = sSize.split(";")
		if (len(lSize) > 1) and ("*" in lSize[1:]):
			return None  # Variable length records
	else:
		dRecDims = {'jSize':0,'kSize':0}
		for sIdx in dRecDims:
			if sIdx not in elDs.attrib: continue
			else: sSize = dRecDims[sIdx]
		
			if sSize == "*": return None
			elif sSize == "": pass
			else:
				try:
					dRecDims[sIdx] = int(elDs.attrib[sIdx])
				except:
					return None

	nBytes = 0
	for axis in elDs:
			
		# das v3.0 all packet values are defined in <packet> elements.
		if axis.tag in ('extension','properties'): continue

		for array in axis:
			if array.tag not in ('scalar','vector','object'): continue

			for pkt in array:
				if pkt.tag != 'packet':  continue

				if 'numItems' not in pkt.attrib: return None
				if pkt.attrib['numItems'] == '*': return None
				if 'itemBytes' not in pkt.attrib: return None
				if pkt.attrib['itemBytes'] == '*': return None

				try:
					nBytesEa = int(pkt.attrib['itemBytes'], 10)
					if nBytesEa < 1: raise ValueError("Value < 1")
				except ValueError:
					if bThrow:  # Don't bother to throw here if doing validation pass
						raise HeaderError(pkt.sourceline,
							"Improper 'itemBytes' for element %s in packet ID %d"%()
						)
				try:
					nItems = int(pkt.attrib['numItems'], 10)
					if nBytesEa < 1: raise ValueError("Value < 1")
				except ValueError:
					if bThrow:  # Don't bother to throw here if doing validation pass
						raise HeaderError(pkt.sourceline,
							"Improper 'itemBytes' for element %s in packet ID %d"%()
						)

				nSize += nItems*nBytesEa
	
	return nSize

def _getPktLen(elDs, sStreamVer, nPktId, bThrow=True):

	"""Given a das <packet> element, or a das <dataset> element, recurse
	through top children and figure out the data length.

	returns: The number of bytes in each packet for fixed length packets,
		None otherwise.
	"""

	if sStreamVer < "3":
		return _getDas2PktLen(elDs, nPktId, bThrow)
	else:
		return _getDas3PktLen(elDs, nPktId, bThrow)



# ########################################################################### #
# def checkShape3(elDs, nPktId) -> None:
# 	"""Check that the array items (i.e. scaler, vector, object) have array 
# 	dimesions that will properly broadcast to the dataset dimensions.
# 
# 	Args:
# 		elDs (lxml.etree.Element) - A das-basic-*-v3.x <dataset> element. Works
# 			with either packetized streams or documents
# 
# 		nPktId (int,None) - The packet ID tag for this element. Only used for
# 			Exception messages.
# 	"""
# 
# 	for axis in elDs:
# 		for array in axis:
# 			if array.tag not in ('scalar', 'vector', 'object'): continue
# 
# 	if ('jSize' in elVar) and (len(elVar.attrib['jSize']) > 0):
# 		if int(elVar.attrib['jSize']) != jSize:
# 			raise HeaderError(elVar.sourceline,
# 			"Attribute iSize in %s must be empty ")


# ########################################################################### #

class Das22HdrParser:
	"""Deal with original das2's bad choices on properties elements.  Convert
	a single properties element into a container with sub elements so that
	it can be checked by schema documents.
	"""

	def __init__(self):
		self._builder = etree.TreeBuilder() # Save the parse tree here
		
		psr = xml.parsers.expat.ParserCreate('UTF-8') # Don't use namesapaces!
		psr.StartElementHandler  = self._elBeg
		psr.EndElementHandler    = self._elEnd
		psr.CharacterDataHandler = self._elData
		
		self._parser = psr
			
	def _elBeg(self, sName, dAttrs):
		# If we are beginning a properties element, then turn the attributes
		# into individual properties
		
		# Don't let the stream actually contain 'p' elements
		if sName == 'p':
			raise ValueError("Unknown element 'p' at line %d, column %d"%(
				self._parser.ErrorLineNumber, self._parser.ErrorColumnNumber
			))
				
		if sName != 'properties':
			el = self._builder.start(sName, dAttrs)
			el.sourceline = self._parser.CurrentLineNumber
			return el
		
		# Break out weird properity attributes into sub elements.  Fortunatly
		# lxml has a sourceline property we can set manually on elements since
		# we are creating them directly instead of the SAX parser.
		# (Thanks lxml!, Ya'll rock!)
		el = self._builder.start('properties', {})
		el.sourceline = self._parser.CurrentLineNumber
		
		for sKey in dAttrs:
			d = {'name':None}
			v = dAttrs[sKey]
			
			if ':' in sKey:
				l = [s.strip() for s in sKey.split(':')]
				
				if len(l) != 2 or (len(l[0]) == 0) or (len(l[1]) == 0):
					raise ValueError(
						"Malformed <property> attribute '%s' at line %d, column %d"%(
						sKey, self._parser.ErrorLineNumber, 
						self._parser.ErrorColumnNumber
					))
				
				d['name'] = l[1]
				if l[0] != 'String': # Strings are the default, drop the type
					d['type'] = l[0]
				
			else:
				d['name'] = sKey
			
			# Put the 'p' elements directly into the tree.  This keeps real
			# p elements from getting included, don't forget the sourceline
			el = self._builder.start('p', d)
			el.sourceline = self._parser.CurrentLineNumber
			self._builder.data(dAttrs[sKey].strip())
			self._builder.end('p')
		
	def _elData(self, sData):
		sData = sData.strip()		
		self._builder.data(sData)
	
	def _elEnd(self, sName):
		return self._builder.end(sName)
		
	def parse(self, fIn):
		if hasattr(fIn, 'read'):
			self._parser.ParseFile(fIn)
		else:
			self._parser.Parse(fIn, 1)
			
		elRoot = self._builder.close()
		return etree.ElementTree(elRoot)

# ########################################################################## #

class Packet(object):
	"""Represents a single packet from a das2 or qstream.

	Properties:
		sver - The version of the stream that produced the packet, should be
		   one of: 2.2, 2.3/basic or qstream

	   tag - The 2-character content tag, see g_lValidTags for a list of
	   	valid tags
			  
	   id - The packet integer ID.  Stream and pure dataset packets
		     are always ID 0.  Otherwise the ID is 1 or greater.
			
		length - The original length of the packet before decoding UTF-8
		     strings.
			
		content - Exther a bytestr (data packets) or a string (header 
		     packets.  If the packet is a header then the bytes are 
			  decode as utf-8. If the packet contains data the a raw
			  bytestr is returned.
	"""

	def __init__(self, sver, tag, id, length, content):
		self.sver    = sver
		self.tag     = tag
		self.id      = id
		self.length  = length
		self.content = content


class HdrPkt(Packet):

	def __init__(self, sver, tag, id, length, content):
		super(HdrPkt, self).__init__(sver, tag, id, length, content)
		self.tree    = None  # Cache the tree if one is created

	def docTree(self):
		"""Get an element tree from header packets
		
		Returns:
			An ElementTree object that may be used directly or run through
			a schema checker.

		Note, the parser ALTERS das2.2 headers to make them conform to standard
		XML conventions.  Namely the weird properties attributes are converted
		to sub elements.  For example this das2.2 properties input:

			<properties Datum:xTagWidth="128.000000 s"
		     double:zFill="-1.000000e+31" sourceId="das2_from_tagged_das1"
			/>

		Would be returned as if the following were read:

			<properties>
			  <p name="xTagWidth" type="Datum">128.000000 s</p>
			  <p name="zFill" type="double">-1.000000e+31</p>
			  <p name="sourceId">das2_from_tagged_das1</p>
			</properties>
		"""

		if not self.tree:

			fPkt = BytesIO(self.content)

			if self.sver == '2.2':
				parser = Das22HdrParser()
				self.tree = parser.parse(fPkt)
			else:
				self.tree = etree.parse(fPkt)

		return self.tree

class DataHdrPkt(HdrPkt):
	"""A header packet that describes data to be encountered later in the stream"""

	def __init__(self, sver, tag, id, length, content):
		super(DataHdrPkt, self).__init__(sver, tag, id, length, content)
		self.nDatLen = None

	def dataLen(self) -> Union[int,None]:
		"""The das v2 parsable data length of each packet.  Das v3 streams
		require that all packets have an explicit length and thus allows
		for variable length arrays in packets.

		Returns: The packet size for fixed length packets, None for variable
			length items.
		"""
		if not self.nDatLen:
			tree = self.docTree()
			elRoot = tree.getroot()

			# Returns None for variable length v3 streams or XML documents
			self.nDatLen = _getPktLen(elRoot, self.sver, self.id)
		
		return self.nDatLen

class DataPkt(Packet):
	"""A packet of data to display or otherwise use"""
	def __init__(self, sver, tag, id, length, content):
		super(DataPkt, self).__init__(sver, tag, id, length, content)

	# Nothing special defined for data packets yet

# ########################################################################## #
def streamType(xFirst):
	"""Read the first bytes of the stream and try to determine the stream 
	type.  Should be able to detect the packetized streams for das v2.2, 
	das v3.0 and q-stream as well as a das v3.0 document

	Args:
		xFirst (bytearray) - Initial bytes of the stream, at least 28 bytes
		   must be provided, to get the exact version number 16K is 
		   recommended.

	Returns: The tuple (content_name, version_string, tag_style, using_namespaces)
		where:
		   content_name - is one of 'das-basic-stream', 'das-basic-doc', 'q-stream'

		   version_string - the content of the 'version' attribute in the stream
		      header element

			tag_style - is one of 'none', 'var', 'fixed'

			using_namespaces - is one of True, or False

	Exceptions:
		If the content can't be recognized a ValueError is thrown
	"""

	sContent = "das-basic-stream"
	sVersion = "2.2"
	sTagStyle = "fixed"  # Other choices are "var" and "none"
	bUsingNs = False # True if explicit namespaces in use

	if len(xFirst) < 8:
		raise ValueError(
			"%d bytes are not enough to detect the stream type"%len(xFirst)
		)

	if xFirst[0:4] == b'|Sx|':
		# Can't use single index for bytestring or it jumps over to an
		# integer return. Hence [0:1] instead of [0]. Yay python3 :-\
		sTagStyle = "var"
	elif xFirst[0:4] == b'[00]':
		sTagStyle = "fixed"
	else:
		# Assume XML, search for <?xml
		sTagStyle = "none"
		sContent = "das-basic-doc"
		ptrn = re.compile(b'<\\?xml')
		l = ptrn.findall(xFirst)
		if len(l) == 0:
			raise ValueError(
				"Content is not a packtize stream, but XML document prolog is missing"
			)

	# So we think it's a stream, try to get the version number if you can
	ptrn = re.compile(b'<\\s*stream')
	m = ptrn.search(xFirst)
	if not m:
		raise ValueError("Can not find <stream> element in first %d bytes"%len(xFirst));
	
	iStart = m.start() + 7

	ptrn = re.compile(b'version\\s*=\\s*\\"(.*?)\\"')
	l = ptrn.findall(xFirst[iStart:])

	if len(l) == 0:
		# Just assume version 2.2 stream or qstream with fixed tags.
		if xFirst.find(b'dataset_id') != -1:	
			sContent = 'q-stream'
			sVersion = None
	else:
		sVersion = l[0].decode('utf-8').strip()
	
	ptrn = re.compile(b'xmlns[:][a-zA-Z0-9_\\-]*?\\s*=\\s*\\"(.*?)\\"')
	l = ptrn.findall(xFirst[iStart:])
	if len(l) > 0:
		bUsingNs = True
		
	return (sContent, sVersion, sTagStyle, bUsingNs)


# ########################################################################## #

class PacketReader:
	"""This packet reader can handle either das v2.2 or v3.0 streams as
	well as das v3.0 documents
	"""
	
	def __init__(self, fIn):
		self.fIn = fIn
		self.lPktSize = [None]*1000
		self.lPktDef  = [False]*1000
		self.nOffset = 0
		self.sContent = "das-basic-stream"
		self.sVersion = "2.2"
		self.sTagStyle = "fixed"  # Other choices are "var" and "none"
		self.bUsingNs = False # True if explicit namespaces in use
		
		# See if this stream is using variable tags and try to guess the content
		# using the first 1024 bytes.  Assume a das2.2 stream unless we see
		# otherwise.  The reason we read so many bytes up front is that the
		# stream header may have many xml schema and namespace references for
		# the all-in-one XML documents
		
		self.xFirst = fIn.read(65536)

		(self.sContent, self.sVersion, self.sTagStyle, self.bUsingNs) = streamType(self.xFirst)

		if self.sContent not in ('das-basic-stream', 'das-basic-doc'):
			raise ValueError("Support stream type '%s' has not been implemented"%self.sContent)

		if self.sTagStyle == 'none':
			raise ValueError(
				"Support for reading documents instead of packetize streams has not been implemented"
			)
			
	def streamType(self):
		return (self.sContent, self.sVersion, self.sTagStyle, self.bUsingNs)		
		
	def _read(self, nBytes):
		xOut = b''
		if len(self.xFirst) > 0:
			xOut = self.xFirst[0:nBytes]
			self.xFirst = self.xFirst[nBytes:]
			
		if len(xOut) < nBytes:
			xOut += self.fIn.read(nBytes - len(xOut))

		return xOut

	def setDataSize(self, nPktId, nBytes):
		"""Callback used when parsing das2.2 and earlier streams.  These had
		no length values for the data packets.
		"""
		
		if nPktId < 1 or nPktId > 99:
			raise ValueError("Packet ID %d is invalid"%nPktid)
		if nBytes <= 0:
			raise ValueError("Data packet size %d is invalid"%nBytes)
		
		self.lPktSize[nPktId] = nBytes
		
	def __iter__(self):
		return self
		
	def next(self):
		return self.__next__()

		
	def __next__(self):
		"""Get the next packet on the stream. Each iteration returns a Packet
		object.  One of:

			Packet: For unknown items
			HdrPkt: For known header packets of a general nature
			DataHdrPkt: For known data header packets
			DataPkt: For known data containing packets
					
		The reader can iterate over all das2 streams, unless it has been
		set to strict mode
		"""
		x4 = self._read(4)
		if len(x4) != 4:
			raise StopIteration
					
		self.nOffset += 4
		
		# Try for a das v3 packet wrappers, fall back to v2.2 unless prevented
		if x4[0:1] == b'|':
			return self._nextVarTag(x4)
			
		elif (x4[0:1] == b'[') or (x4[0:1] == b':'):

			# In das v3, don't allow static tags
			if self.sVersion != "2.2":
				raise ValueError(
					"Das version 2 packet tag '%s' detected in a version 3 stream"%x4
				)

			return self._nextStaticTag(x4)
			
		raise ValueError(
			"Unknown packet tag character %s at offset %d, %s"%(
			str(x4[0:1]), self.nOffset - 4, 
			"(Hint: are the type lengths correct in the data header packet?)"
		))
	

	def _nextStaticTag(self, x4):
		"""Return a das2.2 packet, this is complicated by the fact that pre das3
		data packets don't have length value, parsing the associated header is required.
		"""
		
		try:
			nPktId = int(x4[1:3].decode('utf-8'), 10)
		except ValueError:
			raise ValueError("Invalid packet ID '%s'"%x4[1:3].decode('utf-8'))
			
		if (nPktId < 0) or (nPktId > 99):
			raise ValueError("Invalid packet ID %s at byte offset %s"%(
				x4[1:3].decode('utf-8'), self.nOffset
			))
			
		if self.nOffset == 4 and (x4 != b'[00]'):
			raise ValueError("Input does not start with '[00]' does not appear to be a das2 stream")
		
		if x4[0:1] == b'[' and x4[3:4] == b']':
		
			x6 = self._read(6)	
			if len(x6) != 6:
				raise ValueError("Premature end of packet %s"%x4.decode('utf-8'))
				
			self.nOffset += 6
			
			nLen = 0
			try:
				nLen = int(x6.decode('utf-8'), 10)
			except ValueError:
				raise ValueError("Invalid header length %s for packet %s"%(
					x6.decode('utf-8'), x4.decode('utf-8')
				))
				
			if nLen < 1:
				raise ValueError(
					"Packet length (%d) is to short for packet %s"%(
					nLen, x4.decode('utf-8')
				))
					
			xDoc = self._read(nLen)
			self.nOffset += nLen
			sDoc = None
			try:
				sDoc = xDoc.decode("utf-8")
			except UnicodeDecodeError:
				ValueError("Header %s (length %d bytes) is not valid UTF-8 text"%(
					x4.decode('utf-8'), nLen
				))
			
			self.lPktDef[nPktId] = True
			
			# Higher level parser will have to give us the length.  This is an
			# oversight in the das2 stream format that has been around for a while.
			# self.lPktSize = ? 
			
			# Also comment and exception packets are not differentiated, in das2.2
			# so we have to read ahead to get the content tag
			if x4 == b'[00]': 
				sTag = 'Sx'
				return HdrPkt(self.sVersion, sTag, nPktId, nLen, xDoc)

			elif nPktId > 0: 
				sTag = 'Hx'
				
				# Here's where das2.2 DROPPED THE BALL.  We have to know about
				# the higher level information just to get the size of a packet.
				# Every other networking protocol in the world knows to include
				# either lengths or terminators.  Geeeze.  Well... go parse it.
				parser = Das22HdrParser()
				fPkt = BytesIO(xDoc)
				docTree = parser.parse(fPkt)
				elRoot = docTree.getroot()
				self.lPktSize[nPktId] = _getPktLen(elRoot, self.sVersion, nPktId, False)

				return DataHdrPkt(self.sVersion, sTag, nPktId, nLen, xDoc)

			elif (x4 == b'[xx]') or (x4 == b'[XX]'):
				if sDoc.startswith('<exception'): sTag = 'Ex'
				elif sDoc.startswith('<comment'): sTag = 'Cx'
				elif sDoc.find('comment') > 1: sTag = 'Cx'
				elif sDoc.find('except') > 1: sTag = 'Ex'
				else: sTag = 'Cx'		

			return HdrPkt(self.sVersion, sTag, nPktId, nLen, xDoc)
		
		elif (x4[0:1] == b':') and  (x4[3:4] == b':'):
			# The old das2.2 packets which had no length, you had to parse the header.
			
			if not self.lPktDef[nPktId]:
				raise ValueError(
					"Undefined data packet %s encountered at offset %d"%(
					x4.decode('utf-8'), self.nOffset
				))
			
			if self.lPktSize[nPktId] == None:
				raise RuntimeError(
					"Internal error, unknown length for data packet %d"%nPktId
				)
			
			xData = self._read(self.lPktSize[nPktId])
			self.nOffset += len(xData)
			
			if len(xData) != self.lPktSize[nPktId]:
				raise ValueError("Premature end of packet data for id %d"%nPktId)
			
			return DataPkt(self.sVersion, 'Pd', nPktId, len(xData), xData)

		raise ValueError(
			"Expected the start of a header or data packet at offset %d"%self.nOffset
		)


	def _nextVarTag(self, x4):
		"""Return the next packet on the stream assuming das v3 packaging."""
				
		# Das v3 uses '|' for tag separators since they are not used by
		# almost any other language and won't be confused as xml elements or
		# json elements.
		
		nBegOffset = self.nOffset - 4
		
		# Accumulate the packet tag
		xTag = x4
		nPipes = 2
		while nPipes < 4:
			x1 = self._read(1)
			if len(x1) == 0: break
			self.nOffset += 1
			xTag += x1
			
			if x1 == b'|':
				nPipes += 1
			
			if len(xTag) > 38:
				raise ValueError(
					"Sanity limit of 38 bytes exceeded for packet tag '%s'"%(
						str(xTag)[2:-1])
				)
		
		try:
			lTag = [x.decode('utf-8') for x in xTag.split(b'|')[1:4] ]
			#print(lTag)
		except UnicodeDecodeError:
			raise ValueError(
				"Packet tag '%s' is not utf-8 text at offset %d"%(xTag, nBegOffset)
			)
		
		sTag = lTag[0]
		if sTag not in g_lValidTags:
			raise ValueError("Invalid packet tag '%s', expected one of %s"%(
				sTag, str(g_lValidTags)
			))

		nPktId = 0
		
		if len(lTag[1]) > 0:  # Empty packet IDs are the same as 0
			try:
				nPktId = int(lTag[1], 10)
			except ValueError:
				raise ValueError("Invalid packet ID '%s'"%lTag[1])
			
		if (nPktId < 0):
			raise ValueError("Invalid packet ID %d in tag at byte offset %d"%(
				nPktId, nBegOffset
			))
		
		try:
			nLen = int(lTag[2])
		except ValueError:
			raise ValueError(
				"Invalid length '%s' in packet tag at offset %d"%(lTag[2], nBegOffset)
			)
			
		if nLen < 2:
			raise ValueError(
				"Invalid packet length %d bytes at offset %d"%(nLen, nBegOffset)
			)
					
		xDoc = self._read(nLen)
		self.nOffset += len(xDoc)
			
		if len(xDoc) != nLen:
			raise ValueError("Pre-mature end of packet %s|%d at offset %d"%(
				sTag, nPktId, self.nOffset
			))
			
		if sTag not in ('Pd','XX'):
			# In a header packet, insure it decodes to text
			sDoc = None
			try:
				sDoc = xDoc.decode("utf-8")
			except UnicodeDecodeError:
				ValueError("Header %s|%d (length %d bytes) is not valid UTF-8 text"%(
					sTag, nPktId, nLen
				))
			
			# Have to differentiate between general header packet and data 
			# header packet here
			if sTag == 'Hx':

				# Sanity check, make sure packet is big enough to hold minimum
				# size das3/basic data.
				fPkt = BytesIO(xDoc)
				docTree = etree.parse(fPkt)
				elRoot = docTree.getroot()

				# Note, this can be None!
				self.lPktSize[nPktId] = _getPktLen(elRoot, self.sVersion, nPktId, False)

				return DataHdrPkt(self.sVersion, sTag, nPktId, nLen, xDoc)
			else:
				return HdrPkt(self.sVersion, sTag, nPktId, nLen, xDoc)
		else:
			# If this packet is below minimum necessary size fail it
			if self.lPktSize[nPktId] and (nLen < self.lPktSize[nPktId]):
				raise ValueError(
					"Short data packet expected %d bytes found %d for |%s|%d| at offset %d"%(
					self.lPktSize[nPktId], nLen, sTag, nPktId, self.nOffset
				))

			# Return the bytes
			return DataPkt(self.sVersion, 'Pd', nPktId, nLen, xDoc)
