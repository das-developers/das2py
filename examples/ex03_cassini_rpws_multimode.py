# das2 module example 3:
#    Plotting Cassini RPWS multi-mode spectra using hexbin algorithm

import numpy
import das2
import das2.mpl

import matplotlib.pyplot as pyplot
import matplotlib.colors as colors
import matplotlib.ticker as ticker

# The Cassini RPWS Survey data source is one of the most complicated das2 data
# sources at U. Iowa.  Data consist of multiple frequency sets from multiple
# recivers all attempting to cover the maximum parameter space within a limited
# telemetry alotment and on-board computing power.  This example collapses
# all the provided datasets to a single scatter set for plotting

sId = "site:/uiowa/cassini/rpws/survey/das2"
print("Getting data source definition for %s"%sId)
src = das2.get_source(sId)

print("Reading default example Cassini RPWS E-Survey data...")
lDs = src.get()

# Combining multiple spectra into one overall array set
print("Combining arrays...")
lX = []
lY = []
lZ = []
for ds in lDs:
   # As of numpy version 1.15, the numpy histogram routines won't work
   # with datetime64, and timedelta64 data types.  To Working around a
   # this problem time data are cast to the int64 type
   lX.append(ds['time']['center'].array.flatten().astype("int64"))

   lY.append(ds['frequency']['center'].array.flatten() )
   lZ.append(ds['amplitude']['center'].array.flatten() )

aX = numpy.ma.concatenate(lX)
aY = numpy.ma.concatenate(lY)
aZ = numpy.ma.concatenate(lZ)

(fig, ax0) = pyplot.subplots()

print("Plotting..")
clrscale = colors.LogNorm(vmin=aZ.min(), vmax=aZ.max())
hb = ax0.hexbin(aX, aY, aZ, yscale='log', gridsize=(400, 200),
                cmap='jet', norm=clrscale )


cbar = fig.colorbar(hb, ax=ax0)

# Since matplotlib can't bin datetime64 values, will have to do our
# own axis labeling.  das2 plot help functions are useful here.
nMinor = 60
nMajor = 6*60
ax0.xaxis.set_minor_locator(ticker.MultipleLocator(nMinor*60*int(1e9)))
ax0.xaxis.set_major_locator(ticker.MultipleLocator(nMajor*60*int(1e9)))

fmtr = das2.mpl.TimeTicker(aX.min(), aX.max())
ax0.xaxis.set_major_formatter(ticker.FuncFormatter(fmtr.label))

# Plot labels
ax0.set_xlabel(das2.mpl.ns1970_label( ax0.get_xlim() ))

sUnits = lDs[0]['frequency']['center'].units
ax0.set_ylabel("Frequency (%s)"%das2.mpl.label(sUnits))

sUnits = lDs[0]['amplitude']['center'].units
cbar.set_label("Spectral Density (%s)"%das2.mpl.label(sUnits))

# Stream didn't contain a title, use the one from the data source
ax0.set_title( src.props['title'] )

# matplotlib is a little slow displaying this one, expect ~10 sec delay
pyplot.show()
