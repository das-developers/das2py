"""Composite values through both das2py read layers.

Each das3 fixture below was written by das2C for one formalism.  The low
level read must carry the <ops> element, the internal shape, the component
labels and the array binding; the high level Dataset must keep the internal
shape trailing the dataset indices rather than folding it into them.
"""

import sys
import numpy
import das2

perr = sys.stderr.write

# fixture -> dataset shape, then per variable:
#   (dim, role) -> (array shape, internal shape, labels, ops)
# ops is compared on the keys given; None means the variable has no <ops>.
EXPECT = {
	'test/ex15_vector_frame.d3t': ((15,), {
		('time', 'center'): ((15,),   [],  ['UTC'], {'kind':'point'}),
		('EAC',  'center'): ((15,3),  [3], ['Ex','Ey','Ez'],
			{'kind':'vector', 'frame':'TSCS', 'body':'TS1', 'fixed':False,
			 'system':'cartesian', 'sysorder':'0;1;2'}),
		('gain', 'center'): ((15,),   [],  ['Gain'], {'kind':'linear'}),
	}),
	'test/ex40_rotation.d3t': ((4,), {
		('rot', 'center'): ((4,3,3), [3,3],
			['rot_xx','rot_xy','rot_xz','rot_yx','rot_yy','rot_yz','rot_zx','rot_zy','rot_zz'],
			{'kind':'rotation', 'system':'matrix', 'from':'TSCS', 'to':'GEI2000',
			 'sysorder':'0;1;2;3;4;5;6;7;8'}),
	}),
	'test/ex41_quaternion.d3t': ((4,), {
		('q_wxyz', 'center'): ((4,4), [4], ['q_wxyz_w','q_wxyz_x','q_wxyz_y','q_wxyz_z'],
			{'kind':'rotation', 'system':'quaternion', 'sysorder':'0;1;2;3'}),
		('q_xyzw', 'center'): ((4,4), [4], ['q_xyzw_x','q_xyzw_y','q_xyzw_z','q_xyzw_w'],
			{'kind':'rotation', 'system':'quaternion', 'sysorder':'1;2;3;0'}),
	}),
	# An unknown kind rides through with its parameters verbatim
	'test/ex42_plain_tensor.d3t': ((4,), {
		('cov',       'center'): ((4,3,3),   [3,3],   None, {'kind':'linear'}),
		('heat_flux', 'center'): ((4,3,3,3), [3,3,3], None,
			{'kind':'tensor', 'frame':'GSE', 'symmetry':'full'}),
	}),
	# frequency is a <sequence>, materialized on the C side
	'test/ex43_msc_complex_cal.d3t': ((64,), {
		('frequency', 'center'): ((64,),  [],  ['frequency'], {'kind':'linear'}),
		('cal_rect',  'center'): ((64,2), [2], ['real','imaginary'],
			{'kind':'complex', 'system':'rectangular'}),
		('cal_polar', 'center'): ((64,2), [2], ['cal_polar_mag','cal_polar_phase'],
			{'kind':'complex', 'system':'polar'}),
	}),
	# A composite sequence coordinate over a rank 3 dataset, degenerate in i
	'test/ex22_mag_grid_vec.d3t': ((5,2,2), {
		('time',       'center'): ((5,2,2),   [],  None, {'kind':'point'}),
		('space',      'center'): ((5,2,2,2), [2], ['space_x','space_y'],
			{'kind':'vector', 'frame':'LAB601', 'fixed':True}),
		('calibrated', 'center'): ((5,2,2,3), [3], ['Bx_cal','By_cal','Bz_cal'],
			{'kind':'vector', 'frame':'LAB601'}),
	}),
}

# Low level: which variables are stored and which are computed
LOW_LEVEL = {
	'test/ex43_msc_complex_cal.d3t': {
		('coords', 'frequency', 'center'): ('frequency.center', [0]),  # a sequence
		('data',   'cal_rect',  'center'): ('center_cal_rect',  [0]),
	},
	'test/ex22_mag_grid_vec.d3t': {
		('coords', 'time',  'center'): ('center_time',  [0, None, None]),
		('coords', 'space', 'center'): ('space.center', [None, 0, 1]),
	},
}


# Same values twice: variable width utf8 text and fixed width binary.  The
# two forms take different codec paths in das2C and different packet sizing
# in das2py's reader.  The text forms print four significant figures, the
# binary forms carry full doubles, so agreement is to the text's precision
# and not to float rounding; a stepping error in the fixed width run is
# orders of magnitude larger than that.
PAIRS = (
	('test/ex40_rotation.d3t',        'test/ex40_rotation.d3b'),
	('test/ex43_msc_complex_cal.d3t', 'test/ex43_msc_complex_cal.d3b'),
)


class Failures(object):
	def __init__(self):
		self.n = 0
	def check(self, bOkay, sMsg):
		if not bOkay:
			self.n += 1
			perr("FAIL: %s\n"%sMsg)


def checkHigh(fails, sFile, tDsShape, dVars):
	(dHdr, lDs) = das2.read_file(sFile)
	fails.check(len(lDs) == 1, "%s: expected 1 dataset, got %d"%(sFile, len(lDs)))
	ds = lDs[0]
	fails.check(tuple(ds.shape) == tDsShape,
		"%s: dataset shape %s, expected %s"%(sFile, tuple(ds.shape), tDsShape))

	for (sDim, sRole), (tShape, lIntern, lLabels, dOps) in dVars.items():
		sWho = "%s %s:%s"%(sFile, sDim, sRole)
		dim = ds.dCoord.get(sDim) or ds.dData.get(sDim)
		if dim is None or sRole not in dim.vars:
			fails.check(False, "%s missing"%sWho)
			continue
		var = dim.vars[sRole]
		fails.check(var.array.shape == tShape,
			"%s array shape %s, expected %s"%(sWho, var.array.shape, tShape))
		fails.check(var.intrShape() == tuple(lIntern),
			"%s intrShape %s, expected %s"%(sWho, var.intrShape(), tuple(lIntern)))
		fails.check(var.subrank == len(lIntern),
			"%s subrank %d, expected %d"%(sWho, var.subrank, len(lIntern)))
		fails.check(var.extShape() == tDsShape,
			"%s external shape %s, expected %s"%(sWho, var.extShape(), tDsShape))
		if lLabels is not None:
			fails.check(var.labels == lLabels,
				"%s labels %s, expected %s"%(sWho, var.labels, lLabels))
		else:
			nComp = 1
			for n in lIntern: nComp *= n
			fails.check(var.labels is not None and len(var.labels) == nComp,
				"%s expected %d labels, got %s"%(sWho, nComp, var.labels))
		if dOps is None:
			fails.check(var.ops is None, "%s expected no ops, got %s"%(sWho, var.ops))
		else:
			fails.check(var.ops is not None, "%s expected ops %s, got None"%(sWho, dOps))
			if var.ops is not None:
				for k in dOps:
					fails.check(var.ops.get(k) == dOps[k],
						"%s ops[%s] = %r, expected %r"%(sWho, k, var.ops.get(k), dOps[k]))


def checkLow(fails, sFile, dBind):
	(dHdr, lDs) = das2._das2.read_file(sFile)
	fails.check('context' not in dHdr, "%s: stream header still carries 'context'"%sFile)
	dDs = lDs[0]
	for (sCat, sDim, sRole), (sAry, lMap) in dBind.items():
		sWho = "%s %s:%s"%(sFile, sDim, sRole)
		dVar = dDs[sCat][sDim][sRole]
		fails.check(dVar['array'] == sAry,
			"%s bound to %r, expected %r"%(sWho, dVar['array'], sAry))
		fails.check(dVar['idxmap'] == lMap,
			"%s idxmap %r, expected %r"%(sWho, dVar['idxmap'], lMap))
		fails.check(sAry in dDs['arrays'] and sAry in dDs['fill'],
			"%s array %r missing from 'arrays' or 'fill'"%(sWho, sAry))


def checkPair(fails, sText, sBinary):
	(hdr, lText) = das2.read_file(sText)
	(hdr, lBin)  = das2.read_file(sBinary)
	sWho = "%s vs %s"%(sText, sBinary)
	fails.check(len(lText) == len(lBin), "%s: dataset counts differ"%sWho)
	for (dsT, dsB) in zip(lText, lBin):
		fails.check(tuple(dsT.shape) == tuple(dsB.shape),
			"%s: shapes %s vs %s"%(sWho, dsT.shape, dsB.shape))
		for (dGrp, sGrp) in ((dsT.dCoord, 'coord'), (dsT.dData, 'data')):
			dOther = dsB.dCoord if sGrp == 'coord' else dsB.dData
			for sDim in dGrp:
				if sDim not in dOther:
					fails.check(False, "%s: %s %s missing from binary"%(sWho, sGrp, sDim))
					continue
				for sRole in dGrp[sDim].vars:
					vT = dGrp[sDim].vars[sRole]
					vB = dOther[sDim].vars.get(sRole)
					if vB is None:
						fails.check(False, "%s: %s:%s missing from binary"%(sWho, sDim, sRole))
						continue
					fails.check(vT.array.shape == vB.array.shape,
						"%s: %s:%s shapes %s vs %s"%(sWho, sDim, sRole, vT.array.shape, vB.array.shape))
					fails.check(vT.intrShape() == vB.intrShape() and vT.labels == vB.labels and vT.ops == vB.ops,
						"%s: %s:%s intrShape/labels/ops differ"%(sWho, sDim, sRole))
					if vT.array.shape != vB.array.shape:
						continue
					if vT.array.dtype.kind == 'M':
						bSame = numpy.array_equal(vT.array, vB.array)
					else:
						bSame = numpy.allclose(vT.array.astype('f8'), vB.array.astype('f8'),
						                       rtol=1e-3, atol=1e-6)
					fails.check(bSame, "%s: %s:%s values differ"%(sWho, sDim, sRole))


def main(argv):
	fails = Failures()
	for sFile in EXPECT:
		(tDsShape, dVars) = EXPECT[sFile]
		try:
			checkHigh(fails, sFile, tDsShape, dVars)
		except Exception as e:
			fails.check(False, "%s high level read: %s: %s"%(sFile, type(e).__name__, e))
	for sFile in LOW_LEVEL:
		try:
			checkLow(fails, sFile, LOW_LEVEL[sFile])
		except Exception as e:
			fails.check(False, "%s low level read: %s: %s"%(sFile, type(e).__name__, e))
	for (sText, sBinary) in PAIRS:
		try:
			checkPair(fails, sText, sBinary)
		except Exception as e:
			fails.check(False, "%s vs %s: %s: %s"%(sText, sBinary, type(e).__name__, e))

	if fails.n > 0:
		perr("%d composite checks failed\n"%fails.n)
		return 13
	print("All composite value checks passed")
	return 0

if __name__ == '__main__':
	sys.exit(main(sys.argv))
