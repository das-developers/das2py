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

import numpy as np
import das2
import das2.cdf  # Non default module to assit with writing CDFs

perr = sys.stderr.write

# You can stop das2 server password prompts by creating the file:
#
#  $HOME/.das2_auth
#
# and following the instructions for the das2.load_auth() function.
# Other file names can be used as well, see das2.load_auth() for details.
das2.auth_load()

# ########################################################################## #

def test_load_data(tBeg, tEnd, SrcId):
   """tests whether data exists for the given time range to avoid IndexError issue."""
	try:
		src = das2.get_source(SrcId)
		dQuery = {'time':(tBeg, tEnd), 'hfr_i':True}
		dsReal = src.get(dQuery)[0]
	
	except (IndexError):
		return False
	
	else:
		return True

# ########################################################################## #

def getIQ(sSrcId, sBeg, sEnd):
   "Returns the tuple (dataset I, dataset Q)"""

   src = das2.get_source(sSrcId)

   print("Getting Reals from %s to %s"%(sBeg, sEnd))
   dQuery = {'time':(sBeg, sEnd), 'hfr_i':True}
   dsReal = src.get(dQuery)[0]
   print(dsReal)

   print("Getting Imaginary from %s to %s"%(sBeg, sEnd))
   dQuery = {'time':(sBeg, sEnd), 'hfr_q':True}
   dsImg = src.get(dQuery)[0]
   #print(dsImg)

   return (dsReal, dsImg, src)

# ########################################################################## #

g_psd = None

def calcPsd(dsReal, dsImg, nDFT, nSlide):
   """Transform matched Real and Imaginary Juno Waves down-mixed
   waveforms into a frequency shifted power spectral density.
   """
   global g_psd

   # Define an empty output epoch array
   nOutPerIn = 1 + (dsReal.shape[1] - nDFT) // nSlide
   nOutRows = dsReal.shape[0] * nOutPerIn
   aOutEpoch = np.empty(nOutRows, dtype='M8[ns]')

   # Define an empty reference frequency variable that will map along axis0
   aOutMixer = np.empty(nOutRows, np.dtype(float))

   # Define output frequency offset array that trims data outside the pass-band
   # For Juno Waves HFWBR this is +/- 550 KHz off the mixing frequency.
   qPeriod = dsReal['time']['offset'][0,1] - dsReal['time']['offset'][0,0]
   qFreqDelta = 1.0 / (qPeriod * nDFT)
   aOutFreqOff = np.array([ (i - nDFT//2)*qFreqDelta.value for i in range(0, nDFT)] )

   nDiffIdxRoll = int(0.550//qFreqDelta.to_value('MHz') )
   iMinFreqOut  = nDFT//2 - nDiffIdxRoll
   iMaxFreqOut  = nDFT//2 + nDiffIdxRoll

   aOutFreqOff = aOutFreqOff[iMinFreqOut : iMaxFreqOut + 1]
   nOutFreq = len(aOutFreqOff)

   # Define an empty power spectral density variable
   aOutPsd = np.empty((nOutRows, nOutFreq), np.dtype(float))

   if g_psd == None:
      # We're going to use the das2 power spectral density estimator since we
      # know it satisfies Parseval's theorem, so set up the estimator object
      g_psd = das2.PSD(nDFT, True, 'HANN')

   # Get variables from the input dataset
   vRealAmp  = dsReal['hfr_I']['center']
   vRealTime = dsReal['time']['center']

   vImgAmp = dsImg['hfr_Q']['center']
   vImgTime = dsImg['time']['center']

   vMixer = dsReal['mixer_freq']['center']

   # Loop running sliding power spectral density estimates over the given
   # dataset.  Since Waves I and Q channel data are not continuous across packet
   # boundarieswe're going to only slide as long as we are in a single packet.
   nRowsOut = 0
   for i in range(0, dsReal.shape[0]):

      # Make sure the time values line up, we don't want to accidentally
      # combine I's and Q's from different times.
      if vRealTime[i,0] != vImgTime[i,0]:
         perr("I/Q data from different sample times, I was %s, Q was %s"%(
            vRealTime[i,0], vImgTime[i,0]
         ))
         sys.exit(13)

      for j in range(0, nOutPerIn):

         jStart = j*nSlide
         jEnd   = jStart + nDFT
         aRealSnip = vRealAmp[i, jStart:jEnd].value
         aImgSnip = vImgAmp[i, jStart:jEnd].value

         g_psd.calculate(aRealSnip, aImgSnip)
         aRawPsd = g_psd.get()
         
         # The PSD code does not scale the 

         # Reorder so that the 0th and N-1 value are at the center
         aNeg = aRawPsd[0:       nDFT//2][::-1]
         aPos = aRawPsd[nDFT//2: nDFT   ][::-1]
         aPsd = np.concatenate([aNeg, aPos])

         # Save the data in the output array, pick the time from the middle
         # index of the input as the output epoch
         iOut = i*nOutPerIn + j
         
         aOutEpoch[iOut] = vRealTime[i, jStart + nDFT // 2].value
         
         aOutMixer[iOut] = vMixer[i,0].value
         aOutPsd[iOut] = aPsd[iMinFreqOut : iMaxFreqOut + 1]

         if (nRowsOut != 0) and (nRowsOut % 10000 == 0):
            print("%d spectra calculated"%nRowsOut)
         nRowsOut += 1

         j += nSlide

   # Package the arrays into a dataset and return
   dsPsd = das2.Dataset('shifted_psd')

   dsPsd.coord('time').center(aOutEpoch, 'UTC', axis=0)

   units = dsReal['mixer_freq']['center'].units
   dsPsd.coord('frequency').reference(aOutMixer, units, axis=0)
   dsPsd.coord('frequency').offset(aOutFreqOff, qFreqDelta.unit, axis=1)
   
   # Dev Note: not sure about the units here...
   dsPsd.data('psd').center(aOutPsd, "dn**2/Hz")  

   nDenom = nDFT // nSlide
   sTitle = 'Raw Waves HFWBR - Perijove 3 Inbound - %d DFT, %d/%d overlap'%(nDFT, nDenom - 1, nDenom)
   dsPsd['psd'].props['summary'] = sTitle

   return dsPsd

# ########################################################################## #

def main(lArgs):

   sBeg = '2016-12-11T16:21'  # inbound to Perijove 3
   sEnd = '2016-12-11T16:29'
   nDFT = 512
   nSlide = 128
   sSrcId = 'site:/uiowa/juno/wav/uncalibrated/hrs/das2'
   
   # Testing Das2 streams answer (dataset or not for the wanted date)
   if test_load_data(sBeg, sEnd, sSrcId) == False:
      print("### There is no HFR-High subreceiver data in burst mode for the selected time range ###")
      return
   
   # Reading Das2 streams
   (dsReal, dsImg, src) = getIQ(sSrcId, sBeg, sEnd)

   # Calculating power spectral densities
   dsPsd = calcPsd(dsReal, dsImg, nDFT, nSlide)

   # Writing CDF file
   sCdfFile = "wav_hfrIQ_psd%d_slide%d_%s_%s.cdf"%(nDFT, nDFT//nSlide, sBeg, sEnd)
   print("Finished generating spectra from %s to %s"%(sBeg, sEnd))
   print("Writing %s"%sCdfFile)

   cdf = das2.cdf.write(dsPsd, sCdfFile, src=src, derived=True)
   cdf.close()   
   return 0

# ########################################################################## #
if __name__ == '__main__':
   sys.exit(main(sys.argv))


