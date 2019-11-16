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
print("Initial dataset shape: %s"%list(ds.shape))

# Add a time dimension to the dataset
time = ds.coordDim('time')

# Add a reference point in the time dimension that correlates with dataset
# axis 0.  This is the start of the pulse train

starts = ['2015-08-27','2015-08-26','2015-08-29','2015-08-26']
ref = time.reference(starts, 'UTC')
print("Shape with start times: %s"%list(ds.shape))

# Add an offset variable in the time dimension that correlates with dataset
# axis 1.  This is the time between pulses

offset = time.offset( [0,10,20], 'ms', axis=1)
print("Shape with orthogonal time offsets: %s"%list(ds.shape))


# Add a center point variable in the pulse_freq dimension who's values should
# map along dataset axis 1

ds.coordDim('pulse_freq').center([4,3,5], 'MHz', axis=1)
print("Shape with pulse frequencies: %s"%list(ds.shape))

# Add a center points in the range dimension who's values should map along
# dateset axis 2

ds.coordDim('range').center(np.arange(5)*13.71 + 25.10, 'km',  axis=2)
print("Shape with echo return ranges: %s"%list(ds.shape))

# Add center points in the spectral density dimension.
ds.dataDim('spec_dens').center(
	[	[  [321,322,323,324,325],
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
	],
	'V**2 m**-2 Hz**-1', fill=0.0
)

# Get the shape of the resulting dataset
print("Shape with return intensities: %s"%list(ds.shape))

# Get a single ionogram pulse return:
print("The 2nd pulse from 2nd Ionogram...")
for i in range(ds.shape[2]):
	print("%s, %s, %s, %s"%(
		ds['time']['center'][2,2,i],
		ds['pulse_freq']['center'][2,2,i],
		ds['range']['center'][2,2,i],
		ds['spec_dens']['center'][2,2,i]
	))

# Sort on time and then range
ds.sortAsc('time','range')
