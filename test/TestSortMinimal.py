"""Testing Dataset sorting algorithms"""

import sys
import numpy as np
import das2

# Make a test dataset in the style of a sweep frequency radar sounder.
# This dataset will have values occupying the parameter spaces:
#
#     Time, Pulse Frequency, Range, and Spectral Density
#
# That will be mapped to dataset indicies in the following manner:
#
# A    +--------------+
# x  R |\  Spectral    \
# i  a | \   Density    \
# s  n |  \      at      \
#    g |   \    Antenna   \
# 2  e |    \              \
#      |     +--------------+
#      +     |              |
#  A  T \    |              |
#   x  i \   |              |
#    i  m \  |              |
#     s  e \ |              |
#           \|              |
#       0    +--------------+
#              Pulse Freq,
#              Offset Time
#                Axis 1


ds = das2.Dataset('sounder')

time = ds.coord('time')

lPulse0 = ['2015-08-27','2015-08-26','2015-08-29','2015-08-26']
time.reference(lPulse0, 'UTC')
time.offset( [0,10,20], 'ms', axis=1)

ds.coord('pulse_freq').center([4,3,5], 'MHz', axis=1)

ds.coord('range').center(np.arange(5)*13.71 + 25.10, 'km',  axis=2)

lAmp = [
	[  [321,322,323,324,325],
		[311,312,313,314,315],
		[331,332,333,334,335]	],
	[	[121,122,123,124,125],
		[111,112,113,114,115],
		[131,132,133,134,135]	],
	[  [421,422,423,424,425],
		[411,412,413,414,415],
		[431,432,433,434,435]	],
	[	[221,222,223,224,225],
		[211,212,213,214,215],
		[231,232,233,234,235]	]
]
ds.data('spec_dens').center(lAmp, 'V**2 m**-2 Hz**-1', fill=0.0)

print(ds)

#ds.sort('time:reference','time:offset')
ds.sort('time:reference', 'pulse_freq')
#ds.sort('time')
#ds.sort('spec_dens')

cent = ds['time']['center'].array
print("Time:")
for i in range(4):
	print(" ".join([ str(t)[:23] for t in cent[i,:,0]]))

freq = ds['pulse_freq']['center'].array
print("Freq\n%s"%freq)

amp = ds['spec_dens']['center'].array
print("Amplitude:\n%s"%amp)

ampTest = np.array([
 [[111, 112, 113, 114, 115],
  [121, 122, 123, 124, 125],
  [131, 132, 133, 134, 135]],

 [[211, 212, 213, 214, 215],
  [221, 222, 223, 224, 225],
  [231, 232, 233, 234, 235]],

 [[311, 312, 313, 314, 315],
  [321, 322, 323, 324, 325],
  [331, 332, 333, 334, 335]],

 [[411, 412, 413, 414, 415],
  [421, 422, 423, 424, 425],
  [431, 432, 433, 434, 435]]
])

if np.all(amp == ampTest):
	print("INFO: Multidimensional sort test passed")
	sys.exit(0)
else:
	print("ERROR: Sort test failure")
	sys.exit(13)

