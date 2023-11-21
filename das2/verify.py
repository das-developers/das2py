#!/usr/bin/env python

import sys
import argparse
import re
from os.path import basename as bname


# Stuff that might not work if server is mis-configured
import xml.parsers.expat
from lxml import etree

import das2

# ########################################################################## #

def pout(item):
	"""Encode strings if needed, send binary stuff out the door as is"""
	if sys.version_info[0] == 2:
		if isinstance(item, unicode):
			sys.stdout.write(item.encode('utf-8'))
			sys.stdout.write(b'\n')
		else:
			sys.stdout.write(item)
	else:
		if isinstance(item, str):
			sys.stdout.buffer.write(item.encode('utf-8'))
			sys.stdout.buffer.write(b'\n')
		else:
			sys.stdout.buffer.write(item)


def errorExit(sOut):
	pout(sOut)
	sys.exit(5)


# ########################################################################### #
def namespace(element):
	# Credit: https://stackoverflow.com/questions/9513540/python-elementtree-get-the-namespace-string-of-an-element
	m = re.match(r'\{.*\}', element.tag)
	return m.group(0) if m else ''

# ########################################################################### #

def prnErrorContext(curPkt, nLine):
	sHdr = curPkt.content.decode('utf-8')
	lLines = sHdr.split('\n')

	for i in range(len(lLines)):
		# Trim long lines at 80 characters
		if len(lLines[i]) > 80:
			sLine = lLines[i][:76] + " ..."
		else:
			sLine = lLines[i]
			
		# If we have a valid line number only print within 6 lines each 
		# way of the header
		if (nLine > 0) and abs(nLine - (i+1)) > 6: continue
		
		if i + 1 == nLine:
			pout("    %3d---> %s"%(i+1, sLine))
		else:
			pout("    %3d     %s"%(i+1, sLine))


# ########################################################################### #
def checkStream(fIn, schema, sContent, sVersion, bUsingNs, bPrnHdr):
	"""Check a given file-like object to see if the contents match a schema

	Args:
		fIn (file-like) The input file to read
		schema (lxml.etree.XMLSchema) - A schema object, used for header packets.
		sContent (str) - The content as determined by the pre-reader
		sVersion (str) - The version as determined by the pre-reader
		bUsingNs (bool) - Are namespaces in use, as determined by the pre-reader

	Returns (int): Shell return value, 0 if it works, positive int < 128 if not.

	Throws:
		Should throw nothing, but IOErrors can happen and aren't trapped
	"""

	# Same parsing state info to help with exception output
	curPkt = None
	sCurType = None
	dDataPktCount = {}
	dExpectPktSize = {}

	try:
		# Go for packet read...
		reader = das2.PacketReader(fIn)
		for pkt in reader:
			curPkt = pkt
			
			if isinstance(pkt, das2.DataPkt):
				dDataPktCount[pkt.id] += 1
				if dExpectPktSize[pkt.id]:
					if pkt.length != dExpectPktSize[pkt.id]:
						raise das2.DataError(pkt.tag, pkt.id, dDataPktCount[pkt.id], 
							"Packet size mismatch, expected %d read %d"%(
							dExpectPktSize[pkt.id], pkt.length
						))
				continue
		
			if (not isinstance(pkt, das2.HdrPkt) ):
				raise ValueError("Unknown packet type '%s' encountered"%pkt.tag)
			if bPrnHdr:
				pout(pkt.content)
							
			docTree = pkt.docTree()
			elRoot = docTree.getroot()
			sCurType = elRoot.tag
			
			schema.assertValid(docTree)
		
			if isinstance(pkt, das2.DataHdrPkt):
				dDataPktCount[pkt.id] = 0
				dExpectPktSize[pkt.id] = pkt.dataLen()

				if dExpectPktSize[pkt.id] == None:
					pout("|%s| ID %s %s header [OKAY] (variable packet size)"%(
						pkt.tag, pkt.id, sCurType
					))
				else:
					pout("|%s| ID %s %s header [OKAY] (data size %d bytes)"%(
						pkt.tag, pkt.id, sCurType, pkt.dataLen()
					))
			else:
				pout("|%s| ID %s %s header [OKAY]"%(pkt.tag, pkt.id, sCurType))
				
			curPkt = None
			sCurType = None
			
	except (
		das2.HeaderError, etree.XMLSyntaxError, etree.DocumentInvalid, 
		xml.parsers.expat.ExpatError
	) as e:
		if curPkt:
			if sCurType:
				pout("|%s| ID %s %s header [ERROR] (context follows)"%(curPkt.tag, curPkt.id, sCurType))
			else:
				pout("|%s| ID %s data [ERROR]"%(pkt.tag, pkt.id))

			
		# Try to get last line with an error
		nLine = -1
		if isinstance(e, (etree.XMLSyntaxError, etree.DocumentInvalid)):
			nLine = e.error_log[0].line
					
		elif isinstance(e, xml.parsers.expat.ExpatError):
			nLine = e.lineno
		elif isinstance(e, das2.HeaderError):
			nLine = e.line
				
		# Print context if we can get it
		if curPkt and isinstance(curPkt, das2.HdrPkt):
			try:
				prnErrorContext(curPkt, nLine)
			except:
				# Assumption here
				pout("Header packet %s%d is not valid UTF-8 text"%(curPkt.tag, curPkt.id))
			
		# Hack the non-existent 'p' element back out of any das2.2 error messages
		sErr = str(e)
		if sVersion == '2.2' and sErr.startswith("Element 'p',"):
			sFind ="Element 'p', attribute 'type': [facet 'enumeration'] The value"
			sRep = "Element 'properties', the attribute qualifier"
			sErr = sErr.replace(sFind, sRep)
		pout(sErr)
		if not curPkt:
			pout("No current packet, this usually means the packet tag length value is incorrect.")
			
		#pout(type(e), "\n   dir:", dir(e.error_log[-1]), '\n   msg:', e.error_log[-1].message)
		#pout("Error in %s:\n%s"%(sFile, str(e)))
		return 5
	except das2.DataError as e:
		pout("|%s| ID %d packet %d, %s [ERROR]"%(
			e.pkt_type, e.pkt_id, e.pkt_num, e.message))
		return 5
	except ValueError as e:
		pout("%s [ERROR]"%str(e))
		return 5
				
	for nId in dDataPktCount:
		pout("|Pd| ID %d data packets %d [OKAY]"%(nId, dDataPktCount[nId]))
		
	if bUsingNs:
		pout('Stream validates as a %s version %s with a defined namespace'%(
				sContent, sVersion))
	else:	
		pout('Stream validates as a %s version %s'%(sContent, sVersion))

	return 0


def checkDoc(fIn, schema, bPrnHdr):
	"""Check a file to see if it matches a given schema, experts pure XML
	not a packetized stream

	Args:
		fIn (file-like) The input file to read
		schema (lxml.etree.XMLSchema) - A schema object, used for header packets.

	Returns (int): Shell return value, 0 if it works, positive int < 128 if not.

	Throws:
		Should throw nothing, but IOErrors can happen and aren't trapped
	"""
	if bPrnHdr:
		pout("Header printing disabled for documents")
	elRoot = None
	sContent = None
	sVersion = None
	try:
		# Don't have to worry about any das 2.2 mistakes, it's just 
		# a straight forward check

		tree = etree.parse(fIn)
		elRoot = tree.getroot()
		sContent = elRoot.attrib['type']
		sVersion = elRoot.attrib['version']
		schema.assertValid(tree)

	except (etree.XMLSyntaxError, etree.DocumentInvalid) as e:
		# Try to get last line with an error
		nLine = e.error_log[0].line

		# Strip the namespace in the errors, it just makes them more verbose
		sMsg = str(e)
		sNamespace = namespace(elRoot)
		if (elRoot != None) and len(sNamespace) > 0:
			sMsg = sMsg.replace(sNamespace,'')
		pout("Error in document at line %d: %s"%(nLine, sMsg))
		
		fIn.seek(0)
		xDoc = fIn.read()       # <-- FixMe: dangerous
		sHdr = xDoc.decode('utf-8')
		lLines = sHdr.split('\n')

		for i in range(len(lLines)):
			# Trim long lines at 80 characters
			if len(lLines[i]) > 80:
				sLine = lLines[i][:76] + " ..."
			else:
				sLine = lLines[i]
			
			# If we have a valid line number only print within 6 lines each 
			# way of the header
			if i > (nLine + 6): 
				break

			if (nLine > 0) and abs(nLine - (i+1)) > 6: continue
		
			if i + 1 == nLine:
				pout("    %3d---> %s"%(i+1, sLine))
			else:
				pout("    %3d     %s"%(i+1, sLine))

		return 5

	pout('Document validates as a %s version %s with a defined namespace'%(
				sContent, sVersion))
	return 0


# ########################################################################### #
def main():

	argv = sys.argv

	# Ignore confusing help formatting for now.  (I think newline character
	# insertion in help output is the most requested feature of argparse.)
		
	psr = argparse.ArgumentParser(
		description="das2 stream identifier and validator"
	)
	
	psr.add_argument(
		'-s','--schema', default=None, help="Full path to a specific XSD "+\
		"schema file to load instead of autoloading a schema from internal "+\
		"package data.", dest='sSchema', metavar='schema'
	)
	
	psr.add_argument(
		'-e','--expect', default=None, dest="sExpect", metavar="version",
		help="Don't auto-detect the stream version.  Only streams that match "+\
		"VERSION are validated.  Use one of '2.3/basic', '2.2'."
	)
	
	
	psr.add_argument(
		'-p', '--prn-hdrs', default=False, action="store_true",
		help="Print each das2 header encountered in the stream prior to "+\
		"schema validation.", dest='bPrnHdr'
	)
	
	# End command line with list of files to validate...
	psr.add_argument(
		'lFiles', help='The file(s) to validate', nargs='+', metavar='file'
	)
	
	opts = psr.parse_args()	
	
	for sFile in opts.lFiles:	
		try:
			
			fIn = open(sFile, 'rb')

			pout("Validating: %s"%sFile)

			# Pre-read to try and determine stream type, might not need a packet
			# reader at all. 16K *should* find the version attribute in almost all 
			# cases.
			xFirst = fIn.read(16384)  
			sStreamContent, sStreamVer, sTagStyle, bUsingNs = das2.streamType(xFirst)
			fIn.seek(0)

			if not sStreamContent.startswith('das'):
				pout("This is a %s, expected a das stream or das document"%sStreamContent)
				return 5
			
			if opts.sExpect and (opts.sExpect != sStreamVer):
				pout("%s: is a %s stream, but %s was expected"%(
					sFile, sStreamVer, opts.sExpect
				))
				return 5
			
			if opts.sSchema:
				fSchema = open(opts.sSchema)
				schema_doc = etree.parse(fSchema)
				schema = etree.XMLSchema(schema_doc)
			else:
				(schema, opts.sSchema) = das2.loadSchema(sStreamContent, sStreamVer, bUsingNs)
			pout("Loaded XSD: %s"%bname(opts.sSchema))

			if sTagStyle == 'none': # Should use real None here? Not sure.
				return checkDoc(fIn, schema, opts.bPrnHdr)
			else:
				return checkStream(
					fIn, schema, sStreamContent, sStreamVer, bUsingNs, opts.bPrnHdr
				)

		except (ValueError, IOError) as e:
			pout("%s [ERROR]"%str(e))
			return 13
			
	return 0	

# ########################################################################## #
if __name__ == "__main__":
	sys.exit(main())

