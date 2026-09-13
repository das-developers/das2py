"""Every das3 property type reaches the python model as the right object.

A das3 stream carrying one property of each type in the schema's PropType
list (single, range and array forms) is written with das3.pkt, then read
through both layers.  The das2.2 spellings ('boolean', 'int') are checked
too, since the converter serves both stream versions.
"""

from __future__ import print_function
import sys
import os
import tempfile
import numpy

import das3
import das3.pkt as pkt
from das3.dataset import _mk_prop_from_raw

perr = sys.stderr.write

STREAM = '<stream type="das-basic-stream" version="3.0"/>\n'
DATASET = '''<dataset name="props" rank="1" index="*">
  <properties>
    <p name="pBool" type="bool">true</p>
    <p name="pBoolArr" type="boolArray" term=";">true;false;</p>
    <p name="pDt" type="datetime">2026-09-13</p>
    <p name="pDtRng" type="datetimeRange">2026-09-13 to 2026-09-14</p>
    <p name="pDtArr" type="datetimeArray" term="|">2026-09-13|2026-09-14</p>
    <p name="pInt" type="integer">42</p>
    <p name="pIntRng" type="integerRange">1 to 9</p>
    <p name="pIntArr" type="integerArray" term=";">1;2;3</p>
    <p name="pReal" type="real" units="V">1.5</p>
    <p name="pRealRng" type="realRange" units="V">1.0 to 2.0</p>
    <p name="pRealArr" type="realArray" units="V" term=";">1;2</p>
    <p name="pStr" type="string">hi &amp; bye</p>
    <p name="pStrArr" type="stringArray" term=";">a;b;c;</p>
  </properties>
  <coord physDim="time" name="time" axis="x">
    <scalar semantic="datetime" storage="struct" index="*" units="UTC">
      <ops kind="point"/>
      <packet numItems="1" itemBytes="24" encoding="utf8" fill="0001-01-01T00:00:00.000000"/>
    </scalar>
  </coord>
</dataset>
'''

def dt(s): return numpy.datetime64(s, 'ns')

EXPECT = {
	'pBool':    True,
	'pBoolArr': [True, False],
	'pDt':      das3.Quantity(dt('2026-09-13'), 'UTC'),
	'pDtRng':   das3.Quantity([dt('2026-09-13'), dt('2026-09-14')], 'UTC'),
	'pDtArr':   das3.Quantity([dt('2026-09-13'), dt('2026-09-14')], 'UTC'),
	'pInt':     42,
	'pIntRng':  [1, 9],
	'pIntArr':  [1, 2, 3],
	'pReal':    das3.Quantity(1.5, 'V'),
	'pRealRng': das3.Quantity([1.0, 2.0], 'V'),
	'pRealArr': das3.Quantity([1.0, 2.0], 'V'),
	'pStr':     'hi & bye',
	'pStrArr':  ['a', 'b', 'c'],
}


class Failures(object):
	def __init__(self): self.n = 0
	def check(self, bOkay, sMsg):
		if not bOkay:
			self.n += 1; perr("FAIL: %s\n"%sMsg)


def same(a, b):
	if isinstance(a, das3.Quantity) or isinstance(b, das3.Quantity):
		if not (isinstance(a, das3.Quantity) and isinstance(b, das3.Quantity)): return False
		return a.unit == b.unit and same(a.value, b.value)
	if isinstance(a, (list, tuple)) or isinstance(b, (list, tuple)):
		return list(a) == list(b)
	return a == b


def main(argv):
	fails = Failures()
	sDir = tempfile.mkdtemp(prefix='das3props_')
	sPath = os.path.join(sDir, 'props.d3t')
	try:
		with open(sPath, 'wb') as fOut:
			h = pkt.HdrBuf(0, 'das3'); h.add(STREAM); h.send(fOut)
			h = pkt.HdrBuf(1, 'das3'); h.add(DATASET); h.send(fOut)
			b = pkt.PktBuf(1, 'das3'); b.add('2026-09-13T00:00:00.000 '); b.send(fOut)

		# Low level: multiplicity says set for arrays and the separator is
		# the one byte the header declared, nothing trailing it
		(hdr, lDs) = das3._das3.read_file(sPath)
		dRaw = lDs[0]['props']
		fails.check(dRaw['pIntArr'][4] == 3, "integerArray multiplicity %r, expected 3 (set)"%(dRaw['pIntArr'][4],))
		fails.check(dRaw['pIntRng'][4] == 2, "integerRange multiplicity %r, expected 2"%(dRaw['pIntRng'][4],))
		fails.check(dRaw['pDtArr'][3] == '|', "separator %r, expected '|'"%(dRaw['pDtArr'][3],))

		# High level
		(hdr, lDs) = das3.read_file(sPath)
		dProps = lDs[0].props
		for (sName, want) in EXPECT.items():
			if sName not in dProps:
				fails.check(False, "%s missing"%sName); continue
			fails.check(same(dProps[sName], want), "%s = %r, expected %r"%(sName, dProps[sName], want))
	except Exception as e:
		fails.check(False, "read failed: %s: %s"%(type(e).__name__, e))
	finally:
		if os.path.exists(sPath): os.remove(sPath)
		os.rmdir(sDir)

	# The das2.2 spellings still convert
	fails.check(_mk_prop_from_raw(('boolean', 'true', '', '', 1)) is True, "das2 'boolean' not converted")
	fails.check(_mk_prop_from_raw(('int', '7', '', '', 1)) == 7, "das2 'int' not converted")

	if fails.n:
		perr("%d property checks failed\n"%fails.n); return 13
	print("All das3 property types convert (%s)"%sys.version.split()[0])
	return 0


if __name__ == '__main__':
	sys.exit(main(sys.argv))
