"""Round trip for the packet writers in das3.pkt, in both stream formats.

A small stream is written with every helper, read back with PacketReader,
and the das3 one is validated against the schema the way das_verify does.
The point is agreement with the reader and with das2C's spellings: tag
grammar, byte lengths, exception token translation, XML escaping.
"""

from __future__ import print_function
import sys
import os
import io
import tempfile

import das3
import das3.pkt as pkt
from das3.reader import streamType, loadSchema
import das3.verify as verify

perr = sys.stderr.write

STREAM3 = '''<stream type="das-basic-stream" version="3.0">
  <properties>
    <p name="title">TestPkt round trip</p>
  </properties>
</stream>
'''

DATASET3 = '''<dataset name="pkt_test" rank="1" index="*">
  <coord physDim="time" name="time" axis="x">
    <scalar semantic="datetime" storage="struct" index="*" units="UTC">
      <ops kind="point"/>
      <packet numItems="1" itemBytes="24" encoding="utf8" fill="0001-01-01T00:00:00.000000"/>
    </scalar>
  </coord>
  <data physDim="amplitude" name="amp">
    <scalar semantic="real" storage="double" index="*" units="V">
      <ops kind="linear"/>
      <packet numItems="1" itemBytes="8" encoding="LEreal"/>
    </scalar>
  </data>
</dataset>
'''

STREAM2 = '''<stream version="2.2">
  <properties String:title="TestPkt round trip" />
</stream>
'''

PACKET2 = '''<packet>
  <x type="time24" units="us2000"/>
  <y type="little_endian_real8" name="amp" units="V"/>
</packet>
'''

TIMES = ('2026-09-13T00:00:00.000 ', '2026-09-13T00:00:01.000 ')
MSG = 'no data for <that> range & interval'


class Failures(object):
	def __init__(self): self.n = 0
	def check(self, bOkay, sMsg):
		if not bOkay:
			self.n += 1; perr("FAIL: %s\n"%sMsg)


def writeStream(fOut, sFmt):
	"""One stream header, one dataset header, a comment, two data packets,
	a progress pair and an exception, in the given format."""
	hdr = pkt.HdrBuf(0, sFmt)
	hdr.add(STREAM3 if sFmt == 'das3' else STREAM2)
	hdr.send(fOut)

	hdr = pkt.HdrBuf(1, sFmt)
	hdr.add(DATASET3 if sFmt == 'das3' else PACKET2)
	hdr.send(fOut)

	pkt.sendComment(fOut, 'log:info', 'starting', 'TestPkt', sFmt=sFmt)
	pkt.sendTaskSize(fOut, 'TestPkt', 2, sFmt=sFmt)

	for (i, sTime) in enumerate(TIMES):
		buf = pkt.PktBuf(1, sFmt)
		buf.add(sTime)
		buf.addDoubles(1.5 + i)
		if buf.length() != 32:
			raise ValueError("payload length %d, expected 32"%buf.length())
		buf.send(fOut)
		pkt.sendProgress(fOut, 'TestPkt', i + 1, sFmt=sFmt)

	# das2 spelling in, whatever the format needs out
	pkt.sendException(fOut, pkt.EXCEPT_NODATA, MSG, sFmt=sFmt)


def readBack(sPath):
	with open(sPath, 'rb') as fIn:
		return [(p.tag, p.id, p.length, p.content) for p in das3.PacketReader(fIn)]


def checkFormat(fails, sFmt, sDir):
	sPath = os.path.join(sDir, 'pkt_test.' + ('d3b' if sFmt == 'das3' else 'd2b'))
	with open(sPath, 'wb') as fOut:
		writeStream(fOut, sFmt)
	xRaw = open(sPath, 'rb').read()

	# Tag spelling, straight off the bytes
	if sFmt == 'das3':
		lWant = [b'|Sx||', b'|Hx|01|', b'|Cx||', b'|Cx||', b'|Pd|1|32|', b'|Cx||', b'|Pd|1|32|', b'|Cx||', b'|Ex||']
		fails.check(b'<exception type="NoMatchingData">' in xRaw, "das3: exception token not translated")
		fails.check(b'&lt;that&gt; range &amp; interval</exception>' in xRaw, "das3: message not escaped as body text")
		fails.check(b'<comment type="log:info" source="TestPkt">starting</comment>' in xRaw, "das3: comment not in body form")
	else:
		lWant = [b'[00]', b'[01]', b'[xx]', b'[xx]', b':01:', b'[xx]', b':01:', b'[xx]', b'[xx]']
		fails.check(b'<exception type="NoDataInInterval" message="' in xRaw, "das2: exception token wrong")
		fails.check(b'&lt;that&gt; range &amp; interval' in xRaw, "das2: message not escaped")
	nAt = 0
	for xTag in lWant:
		nAt = xRaw.find(xTag, nAt)
		fails.check(nAt >= 0, "%s: tag %r missing or out of order"%(sFmt, xTag))
		if nAt < 0: break
		nAt += len(xTag)

	# The reader agrees: tags, ids, and every declared length matches content
	try:
		lPkts = readBack(sPath)
	except Exception as e:
		fails.check(False, "%s: PacketReader failed: %s: %s"%(sFmt, type(e).__name__, e))
		return sPath
	lTags = [t for (t, i, n, c) in lPkts]
	lWantTags = ['Sx', 'Hx', 'Cx', 'Cx', 'Pd', 'Cx', 'Pd', 'Cx', 'Ex']
	fails.check(lTags == lWantTags, "%s: reader saw tags %s"%(sFmt, lTags))
	for (t, i, n, c) in lPkts:
		fails.check(n == len(c), "%s: %s|%d declares %d bytes, holds %d"%(sFmt, t, i, n, len(c)))
	lData = [c for (t, i, n, c) in lPkts if t == 'Pd']
	fails.check(len(lData) == 2 and lData[0][:24] == TIMES[0].encode('utf-8'),
		"%s: data packet content wrong"%sFmt)
	return sPath


def checkSchema(fails, sPath):
	"""The das3 stream passes the same validation das_verify applies"""
	with open(sPath, 'rb') as fIn:
		xFirst = fIn.read(16384)   # what das_verify sniffs
		(sContent, sVersion, sTagStyle, bUsingNs) = streamType(xFirst)
		(schema, sSchema) = loadSchema(sContent, sVersion, bUsingNs)
		fIn.seek(0)
		# checkStream prints its report through sys.stdout.buffer on python 3
		# and sys.stdout on 2; capture both ways and keep the test quiet
		class _Capture(object):
			def __init__(self): self.buffer = io.BytesIO()
			def write(self, x): self.buffer.write(x if isinstance(x, bytes) else x.encode('utf-8'))
			def flush(self): pass
		cap = _Capture()
		sys.stdout = cap
		try:
			nRet = verify.checkStream(fIn, schema, sContent, sVersion, bUsingNs, False)
		finally:
			sys.stdout = sys.__stdout__
		sReport = cap.buffer.getvalue().decode('utf-8')
	fails.check(nRet == 0, "das3 stream failed das_verify checks:\n%s"%sReport)


def main(argv):
	fails = Failures()
	sDir = tempfile.mkdtemp(prefix='das3pkt_')
	try:
		sPath3 = checkFormat(fails, 'das3', sDir)
		checkFormat(fails, 'das2', sDir)
		if fails.n == 0:
			checkSchema(fails, sPath3)
		# reverse translation: das3 spelling in, das2 token out
		f = io.BytesIO()
		pkt.sendException(f, pkt.EXCEPT_QUERYERR, 'x', sFmt='das2')
		fails.check(b'type="IllegalArgument"' in f.getvalue(), "das2: das3 token not translated back")
		f = io.BytesIO()
		pkt.sendException(f, 'MyOwnType', 'x', sFmt='das3')
		fails.check(b'type="MyOwnType"' in f.getvalue(), "unknown exception type did not pass through")
	finally:
		for s in os.listdir(sDir): os.remove(os.path.join(sDir, s))
		os.rmdir(sDir)

	if fails.n:
		perr("%d packet writer checks failed\n"%fails.n); return 13
	print("Packet writers round trip in das2 and das3 form (%s)"%sys.version.split()[0])
	return 0


if __name__ == '__main__':
	sys.exit(main(sys.argv))
