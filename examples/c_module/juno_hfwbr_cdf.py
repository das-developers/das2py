# das2 module example 7:
#    Processing Juno Waves downmixed dual sideband waveforms from CODMAC
#    Level 2  data into CDFs

"""
This is an example of processing Juno Waves I/Q data using the libdas2
low-level interface.  Better interfaces are on the way.  There are quite
a few steps to re-produce standard HFWBR processing on the client side.

Should work with python 2.6, 2.7, 3.4 or greater
"""

import sys
import os
import base64
import datetime
import math as M

import numpy
import das2

try:
	import spacepy.pycdf as pycdf
except ImportError:
	import das2.pycdf as pycdf # Use included copy if spacepy not installed

perr = sys.stderr.write
pout = sys.stdout.write

# You can stop das2 server password prompts by computing the HTTP basic auth
# hash in advance and telling the libdas2 when to use it.  Replace USERNAME
# and PASSWORD below, or pass the hash in from the command line or read it
# form a file, whatever you feel is appropriate.
g_sServer = 'http://jupiter.physics.uiowa.edu/das/server'
g_sRealm = 'Juno Magnetospheric Working Group'
g_sHash = base64.standard_b64encode(b"USERNAME:PASSWORD").decode('utf-8')

das2.auth_set(g_sServer, g_sRealm, g_sHash, ('dataset','Juno/WAV/Uncalibrated/HRS'))

# ########################################################################## #

g_sDataset = 'Juno/WAV/Uncalibrated/HRS'
g_sGetFmt = '%s?server=dataset&dataset=%s&start_time=%s&end_time=%s&params=%s'

def getIQ(sBeg, sEnd):
	"Returns the tuple (dataset I, dataset Q)"""

	sParams = 'hfr_I'
	sUrl = g_sGetFmt%(g_sServer, g_sDataset, sBeg, sEnd, sParams)

	print("Getting Reals from %s to %s"%(sBeg, sEnd))
	(dHdr, lReal) = das2._das2.read_server(sUrl)
	dsReal = lReal[0]

	#print(dsReal['info'])

	sParams = 'hfr_Q'
	sUrl = g_sGetFmt%(g_sServer, g_sDataset, sBeg, sEnd, sParams)

	print("Getting Imaginary from %s to %s"%(sBeg, sEnd))
	(dHdr, lImg) = das2._das2.read_server(sUrl)
	dsImg = lImg[0]

	#print(dsImg['info'])

	return (dsReal, dsImg)


# ########################################################################## #

g_psd = None

def calcPsd(dsReal, dsImg, nDFT, nSlide):
	"""Returns the numpy arrays: (time, freq, spec)"""
	global g_psd

	# Using the info printed dsImg[info], get the ndarrays.  Future higher level
	# interface will make this more friendly, and more compatable with CDF

	aReal = dsReal['arrays']['hfr_I']
	aRealRefTime = dsReal['arrays']['time']

	aImg = dsImg['arrays']['hfr_Q']
	aImgRefTime = dsImg['arrays']['time']

	# We could read all the time offsets, but we know these are regularly sampled
	# data so just get the difference between the 0th and 1st values for the real
	# time offset array
	
	aRealOffsetTime = dsReal['arrays']['offset']
	nTotalPeriod = (aRealOffsetTime[-1] - aRealOffsetTime[0])
	
	# Get period (no matter the original units) as raw ratio to 1 microsecond
	# removing any time units
	rPeriod = (nTotalPeriod / numpy.timedelta64(1, 'us')) / float(aRealOffsetTime.size - 1)

	rFreqDelta = 1.0 / (rPeriod * nDFT)  # In MHz since period is microseconds
	
	pout("Delta T = %.6e microsec, Delta F = %.6e MHz\n"%(rPeriod, rFreqDelta))

	# Frequencies are an offset as well, though current das2 streams don't have a
	# way to make this explicit so the mixer_freq just shows up as an independent
	# coordinate.  Das2 v2.3 basic streams will solve this, but for now just
	# grab the array and use it
	aMixerMHz = dsReal['arrays']['mixer_freq']
	aFreqOff = numpy.array([ (i - nDFT//2)*rFreqDelta for i in range(0, nDFT)] )

	if g_psd == None:
		# We're going to use the das2 power spectral density estimator since
		# we know it satisfies Parseval's theorem, so set up the estimator
		# object
		g_psd = das2._das2.Psd(nDFT, True, 'HANN')


	# Setup the output arrays, the number of output rows is per input row is:
	# 1 + (waveform_len - dft)/slide
	nOutPerIn = 1 + (aReal.shape[1] - nDFT) // nSlide
	nOutRows = aReal.shape[0] * nOutPerIn

	# The number of output put rows depends on our FFT size and slide fraction
	# save output epoch array in same units as reference time arrays
	aOutEpoch = numpy.empty(nOutRows, dtype=aRealRefTime.dtype)

	# Trim data outside the pass-band.  For Juno Waves HFWBR this is +/- 550 KHz
	# off the mixing frequency.  Calculated the number of freqs we'll actually
	# keep.  Use this to trim down aFreqOff
	nDiffIdxRoll = int(0.550/rFreqDelta)
	iMinFreqOut  = nDFT//2 - nDiffIdxRoll
	iMaxFreqOut  = nDFT//2 + nDiffIdxRoll

	aFreqOff = aFreqOff[iMinFreqOut : iMaxFreqOut + 1]
	nOutFreqs = (iMaxFreqOut - iMinFreqOut) + 1

	# ISTP CDFs don't have a reference and offset concept so we have to explicitly
	# write each frequency value for each amplitude value.  Almost doubles the size
	# of the output array, but I don't see any other good options.
	aOutFreq  = numpy.empty((nOutRows, nOutFreqs), dtype='f4')

	aOutPsd   = numpy.empty((nOutRows, nOutFreqs), dtype='f8')

	# Loop running sliding power spectral density estimates over the given dataset.
	# Since Waves I and Q channel data are not continuous across packet boundaries
	# we're going to only slide as long as we are in a single packet.
	nRowsOut = 0
	for i in range(0, aReal.shape[0]):

		# Make sure the time values line up, we don't want to accidentally
		# combine I's and Q's from different times.  Fail fast so we know
		# there's a problem in the data and that the algorithm needs to be
		# more sophisticated
		if aRealRefTime[i] != aImgRefTime[i]:
			perr("I/Q data from different sample times, I was %s, Q was %s"%(
			     aRealRefTime[i], aImgRefTime[i]
			))
			perr("bailing out\n")
			sys.exit(13)

		for j in range(0, nOutPerIn):

			jStart = j*nSlide
			jEnd   = jStart + nDFT
			aRealSnip = aReal[i, jStart:jEnd]
			aImgSnip = aImg[i, jStart:jEnd]

			g_psd.calculate(aRealSnip, aImgSnip)

			aPsd = g_psd.get()

			# Reorder so that the 0th and N-1 value are at the center
			aNeg = aPsd[0:       nDFT//2][::-1]
			aPos = aPsd[nDFT//2: nDFT   ][::-1]
			aSpec = numpy.concatenate([aNeg, aPos])

			# Save the data in the output arrays
			iOut = i*nOutPerIn + j

			# Offset the start time to the middle index used in the snippet
			aOutEpoch[iOut] = aRealRefTime[i] +  \
			          numpy.timedelta64(int(rPeriod*(jStart + nDFT/2)), 'us')

			aOutFreq[iOut, :] = aFreqOff + aMixerMHz[i]
			aOutPsd[iOut, : ] = aSpec[iMinFreqOut : iMaxFreqOut + 1]


			if (nRowsOut != 0) and (nRowsOut % 10000 == 0):
				pout("%d spectra calculated\n"%nRowsOut)
			nRowsOut += 1

			j += nSlide

	return (aOutEpoch, aOutFreq, aOutPsd)

# ########################################################################## #

def timeUnits(aSomeAry):
	"""Get the units from an array of timedelta or datetime objects."""
	s = str(aSomeAry.dtype)
	
	# This is cheezy, but I can't find a way around it
	if s.find('[') > -1:
		return s[s.find('[')+ 1 : s.rfind(']')]  
	else:
		return None

def writeCdf(aEpoch, aFreq, aSpec, sBeg, sEnd, nDFT, nSlide):
	"""Not a generic CDF writing function, specific to this program"""

	sCdfFile = "wav_hfrIQ_psd%d_slide%d_%s_%s.cdf"%(nDFT, nDFT//nSlide, sBeg, sEnd)

	pout("Finished generating spectra from %s to %s\n"%(sBeg, sEnd))
	pout("Writing %s\n"%sCdfFile)

	if os.path.isfile(sCdfFile): os.remove(sCdfFile)

	# Write the data
	pycdf.lib.set_backward(backward=False)
	cdf = pycdf.CDF(sCdfFile, '')
	
	# pycdf can't yet handle datetime64 type, so do a SLOW conversion to
	# a python datetime array.  numpy.fromiter can't be used here becasue
	# we have an object array.  Basically numpy's and pycdf's datetime handling
	# functions just aren't finished yet.
	oneSec = numpy.timedelta64(1, 's')
	oneUnit = numpy.timedelta64(1, timeUnits(aEpoch))
	rToSec = float( oneUnit / oneSec )
	lEpoch = [ datetime.datetime.utcfromtimestamp(n * rToSec) for n in aEpoch.astype('int64') ]
	
	# The generic variable setter doesn't allow for selecting the CDF data
	# type.  So we can't use: cdf['Epoch'] = aEpoch here if we want TT2000
	cdf.new('Epoch', lEpoch, pycdf.const.CDF_TIME_TT2000)
	cdf['Freqs'] = aFreq
	cdf['PSD'] = aSpec

	# Set some CDF attributes so that autoplot knows how to represent the arrays
	cdf['Epoch'].attrs['VAR_TYPE'] = 'support_data'

	if len(aFreq.shape) > 1:
		cdf['Freqs'].attrs['DEPEND_0'] = 'Epoch'

	cdf['Freqs'].attrs['VAR_TYPE'] = 'support_data'
	cdf['Freqs'].attrs['UNITS'] = 'MHz'

	nDenom = nDFT // nSlide
	sTitle = 'Waves HFR I/Q %d DFT, %d/%d overlap'%(nDFT, nDenom - 1, nDenom)

	cdf['PSD'].attrs['FIELDNAM'] = sTitle
	cdf['PSD'].attrs['DEPEND_0'] = 'Epoch'
	cdf['PSD'].attrs['DEPEND_1'] = 'Freqs'
	cdf['PSD'].attrs['VAR_TYPE'] = 'data'
	cdf['PSD'].attrs['UNITS'] = 'dn^2 / Hz'

	cdf.close()


# ########################################################################## #

def main(lArgs):

	sBeg = '2016-12-11T16:21'  # inbound to Perijove 3
	sEnd = '2016-12-11T16:29'
	nDFT = 512
	nSlide = 128

	# Reading Das2 streams
	(dsReal, dsImg) = getIQ(sBeg, sEnd)

	# Calculating power spectral densities
	(aTime, aFreq, aSpec) = calcPsd(dsReal, dsImg, nDFT, nSlide)

	# Writing CDF files
	writeCdf(aTime, aFreq, aSpec, sBeg, sEnd, nDFT, nSlide)

	return 0


# ########################################################################## #
if __name__ == '__main__':
	sys.exit(main(sys.argv))


