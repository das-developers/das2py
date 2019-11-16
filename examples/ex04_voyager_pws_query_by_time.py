# das2 module example 4
#   Reading Voyager PWS 16-channel data and plotting peaks and averages
#   based on command line time ranges
import sys
import das2
import das2.mpl

import matplotlib.pyplot as pyplot
import matplotlib.dates  as dates
import matplotlib.ticker as ticker

# Default to Jupiter encounter period with 5-minute time bins...
if len(sys.argv) == 1: 
   subset = ('1979-03-14', '1979-03-16', 300)

# ...or display an error message
elif len(sys.argv) == 2:
   sys.stderr.write("Usage: %s BEGIN_TIME END_TIME"%bname(sys.argv[0]))
   sys.exit(13)

# ...or request 100 time bins in an arbitrary range
else:
   resolution = das2.Dastime(sys.argv[2]) - das2.Dastime(sys.argv[2])
   resolution /= 100.0
   subset = (sys.argv[0], sys.argv[1], resolution)

sId = 'site:/uiowa/voyager/1/pws/specanalyzer-4s-efield/das2'
src = das2.get_source(sId)

ds = src.get({'time':subset})[0]
print(ds)

time = ds['time']
freq = ds['frequency']
amp  = ds['amplitude']

aTime = time['center'].array
aAvg  = amp['mean'].array
aPeak = amp['max'].array
aAbove = aPeak - aAvg

fig, ax = pyplot.subplots(ds.shape[1], 1, sharex=True)
fig.subplots_adjust(hspace=0)  # Rm space between axis
fig.autofmt_xdate()  # Fix date formating

sAmpLbl = das2.mpl.label(amp.props['label'])

# plot all the channels as a Y-stack
for j in range(ds.shape[1]):
   
   iPlot = (ds.shape[1] - 1) - j
   
   ax[iPlot].set_ylim(aAvg.min(), aPeak.max())
   
   clrs = ['black','gray']
   ax[iPlot].stackplot(aTime[:,j], aAvg[:,j], aAbove[:,j], colors=clrs)
                    
   ax[iPlot].set_yscale('log')
   ax[iPlot].yaxis.tick_right()
   ax[iPlot].yaxis.set_label_coords(-0.05, 0.3)
   
   #Optional, get rid of Y-axis values
   #ax[iPlot].yaxis.set_major_formatter(pyplot.NullFormatter())

   qChan = freq['center'][0,j]
   
   if qChan.value < 1000.0: sLabel = "%s %s"%(qChan.value, qChan.unit)
   else: sLabel = "%s k%s"%(qChan.value / 1000.0, qChan.unit)
         
   ax[iPlot].set_ylabel(sLabel, rotation=0)


# overall plot labels
(iTop, iBot) = (0, ds.shape[1] - 1)
ax[iTop].set_title("Voyager 1 PWS - Jupiter Encounter")

ax[iBot].fmt_xdata = dates.DateFormatter("%Y-%m-%dT%H:%M")  # mouse over dates
ax[iBot].xaxis.set_minor_locator(dates.HourLocator(interval=1)) # add minor ticks
ax[iBot].set_xlabel(das2.mpl.range_label(time) )

pyplot.show()
