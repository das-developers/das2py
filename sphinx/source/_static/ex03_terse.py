import numpy
import das2
import matplotlib.pyplot as pyplot
import matplotlib.colors as colors
import matplotlib.ticker as ticker

# Use the federated das2 catalog to find and download data given a source ID
sSourceId = "tag:das2.org,2012:site:/uiowa/cassini/rpws/survey/das2"
src = das2.get_source(sSourceId)
lDatasets = src.get()

# Combining multiple table datasets into a single homogeneous scatter dataset
# (most datasets are homogeneous and will not require this step)
lX = []
lY = []
lZ = []
for dataset in lDatasets:
    # As of numpy version 1.15, the numpy histogram routines won't work
    # with datetime64, and timedelta64 data types.  To Working around a
    # this problem time data are cast to the int64 type giving time values
    # as integer nanoseconds since 1970.
    lX.append(dataset.coords['time']['center'][:,:].flatten().astype("int64"))

    lY.append(dataset.coords['frequency']['center'][:,:].flatten() )
    lZ.append(dataset.data['amplitude']['center'][:,:].flatten() )

aX = numpy.ma.concatenate(lX)
aY = numpy.ma.concatenate(lY)
aZ = numpy.ma.concatenate(lZ)


# Plot the data using hexbin which can handle scatter arrays
(fig, ax0) = pyplot.subplots()
clrscale = colors.LogNorm(vmin=aZ.min(), vmax=aZ.max())
hb = ax0.hexbin(aX, aY, aZ, yscale='log', gridsize=(400, 200),
                cmap='jet', norm=clrscale )

cbar = fig.colorbar(hb, ax=ax0)

# Set major ticks at 6 hours, minor ticks at 1 hour
ax0.xaxis.set_minor_locator(ticker.MultipleLocator(60*60*int(1e9)))
ax0.xaxis.set_major_locator(ticker.MultipleLocator(6*60*60*int(1e9)))

fmtr = das2.MplTimeTicker(aX.min(), aX.max())
ax0.xaxis.set_major_formatter(ticker.FuncFormatter(fmtr.label))

# Plot labels
ax0.set_xlabel(das2.ph_ns1970_range( ax0.get_xlim() ))

sUnits = lDs[0]['frequency']['center'].units
ax0.set_ylabel("Frequency (%s)"%das2.mpl_text(sUnits))

sUnits = lDs[0]['amplitude']['center'].units
cbar.set_label("Spectral Density (%s)"%das2.mpl_text(sUnits))

# Use the title of the data source for the plot title
ax0.set_title( src.props['title'] )

pyplot.show()
