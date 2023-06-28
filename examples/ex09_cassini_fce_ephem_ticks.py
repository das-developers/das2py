#import numpy
import sys
import os.path
import numpy as np

import matplotlib.pyplot as pyplot
import matplotlib.ticker as ticker

import das2      # General data stuff
import das2.mpl  # matplotlib helpers

# ########################################################################### #
# Plot Helpers #

def dayTicks(sDay):
	"""Calculate ns1970 times at every 4 hours of a day inclusive"""
	
	dt = das2.DasTime(sDay)
	dtFloor = das2.DasTime("%04d-%02d-%02d"%(dt.year(), dt.month(), dt.dom()))
	
	lTimes = [ dtFloor.epoch('ns1970') ]
	for i in range(6):
		dtFloor.adjust(0, 0, 0, 4)
		lTimes.append(int( dtFloor.epoch('ns1970')) )
		
	return lTimes
	
	
def dayLabels(sDay, sEphemSrc):
	"""Goes with dayTicks above, just output every 4 hours but add 
	cassini location data for multi-line labels.  Assumes daily plots
	
	Args:
		sDay (str) - The day for which ticks are needed
		sEphemSrc (str) - A das2 catalog ID providing ephemers values
		
	Returns (str, list):
		The first item is a multi-line set of row labels, the second is
		a list of multi-line tick marks.  Give the list to pyplot.xticks
		and the row label to pyplot.gcf().text()
	"""
	
	dt = das2.DasTime(sDay)
	dtBeg = das2.DasTime("%04d-%02d-%02d"%(dt.year(), dt.month(), dt.dom()))
	dtEnd = dtBeg + 60*60*24 + 1 # Add 86401 seconds to get upper bound
	
	ephem_src = das2.get_source(sEphemSrc)
	print(ephem_src.info())    # Print dev info about the source
	
	# Get some help on how to query a source
	# help(das2.Source.get)
	
	# Here I'm using the Coordinate subset query shortcut as described
	# in "shortcuts" section of the help above
	dsEphem = ephem_src.get({'time':(str(dtBeg), str(dtEnd), 60*60*4)})[0]
	print(dsEphem)             # Print dev info about the dataset
	
	
	# Multi-line tick lables
	lLabels = []
	lHr = [0,4,8,12,16,20,0]
	for i in range(len(lHr)):
		lLabels.append( "%02d:00\n%.2f\n%.2f\n%.2f\n%.2f"%(
			lHr[i], 
			dsEphem['R_S']['center'][i].to_value(), 
			dsEphem['Lon']['center'][i].to_value(),
			dsEphem['Lat']['center'][i].to_value(),
			#dsEphem['LT']['center'][i].to_value(), # das2 converting LT to actual time!
			dsEphem['L']['center'][i].to_value()
		))
		
	sHdr = "SCET\n%s\n%s\n%s\n%s"%(
		das2.mpl.label( dsEphem['R_S'].props['label'] ),
		das2.mpl.label( dsEphem['Lon'].props['label'] ),
		das2.mpl.label( dsEphem['Lat'].props['label'] ),
		das2.mpl.label( dsEphem['L'].props['label'] )
	)
	
	return (sHdr, lLabels)


# ########################################################################### #

def main(lArgs):
	"""An example of making daily plots of Cassini Fce.
	
	This example is not complete as the ephemeris values need to be added
	to the tick labels.  This will require adjusting the location of the
	lower x-axis and producing multi-line labels
	"""

	if len(lArgs) != 2:
		print("Usage: %s Day"%os.path.basename(lArgs[0]))
		return 7
	
	dt = das2.DasTime(lArgs[1])
	sBeg = "%04d-%02d-%02d"%(dt.year(), dt.month(), dt.dom())
	dtEnd = das2.DasTime(sBeg)
	dtEnd.adjust(0,0,1)
	sEnd = "%04d-%02d-%02d"%(dtEnd.year(), dtEnd.month(), dtEnd.dom())
	
	
	# Gather the primary data...
	
	fce_src = das2.get_source('site:/uiowa/cassini/mag/electroncyclotron/das2')
	print(fce_src.info())      # Print dev info about the source
	
	
	dsFce = fce_src.get({'time':(sBeg, sEnd)})[0]
	print(dsFce)             # Print dev info about the dataset


	# Plot it with Cassini Saturn location values on the X-axis ...
	
	(fig, ax0) = pyplot.subplots()
	
	# The main plot item will be the electron cyclotron frequency
	
	# matplotlib axis labeling for datetime64 has traditionally been
	# poor, best bet is to just treat time as a generic int64 and 
	# label it yourself.
	
	# As an exercise for the reader

	aX = dsFce['time']['center'].array.astype('int64')
	aY = dsFce['Fce']['center'].array
	
	ax0.plot(aX, aY, linewidth=2.0)
	
	nBeg = np.datetime64(sBeg, "ns").astype('int64')
	nEnd = np.datetime64(sEnd, "ns").astype('int64')
	ax0.set_xlim(nBeg, nEnd)
	pyplot.subplots_adjust(bottom=0.25)
	
	sEphemId = 'site:/uiowa/cassini/ephemeris/saturn/das2'
	(sRowLbl, lTicLbls) = dayLabels(sBeg, sEphemId)
	
	pyplot.gcf().text(0.02,0.068, sRowLbl)
	
	pyplot.xticks(ticks=dayTicks(sBeg), labels=lTicLbls)
	ax0.xaxis.set_minor_locator(ticker.AutoMinorLocator(3))
		
	dt = das2.DasTime(sBeg)
	sDate = "%04d-%02d-%02d"%(dt.year(), dt.month(), dt.dom())
	ax0.set_xlabel("%s (%03d) UTC"%(sDate, dt.doy()))
	ax0.set_yscale('log')
	
	# das2.mpl module provides das2 -to-> mpl text formatting
	ax0.set_ylabel(das2.mpl.label(dsFce['Fce'].props['label']))
	ax0.set_title(das2.mpl.label(dsFce.props['title']))
	
	pyplot.savefig('cas_mag_fce_%s.png'%sDate)
	
	return 0
	
	
if __name__ == "__main__":
	sys.exit(main(sys.argv))



