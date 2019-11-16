# das2py example 10:
#    Creating datasets manually and observing automatic dataset shape
#    adjustments.
#
# Make a test dataset in the style of a sweep frequency radar sounder.
# This dataset will have values occupying the parameter spaces:
#
#     Time, Pulse Frequency, Range, and Spectral Density
#
# That will be mapped to dataset indicies in the following manner:
#
#         A    +--------------+
#         x  R |\  Spectral    \
#         i  a | \   Density    \
#         s  n |  \      at      \
#            g |   \    Antenna   \
#         2  e |    \              \
#              |     +--------------+
#              +     |              |
#          A  T \    |              |
#           x  i \   |              |
#            i  m \  |              |
#             s  e \ |              |
#                   \|              |
#               0    +--------------+
#                      Pulse Freq &
#                      Offset Time
#                        Axis 1

import numpy as np
import das2

ds = das2.Dataset('sounder')
print("Initial dataset shape: %s"%list(ds.shape))

# State that the dataset has a time dimension, but don't define any variables
# in the new dimension yet.

time = ds.coord('time')

# Add a reference point in the time dimension that correlates with dataset
# axis 0.  This is the start of the pulse train

pulse0 = ['2015-08-27','2015-08-26','2015-08-29','2015-08-26']
ref = time.reference(pulse0, 'UTC')
print("Shape with start times: %s"%list(ds.shape))

# Add an offset variable in the time dimension that correlates with dataset
# axis 1.  This is the time between pulses in milliseconds.  Since the new
# array is orthogonal to the first, the dataset becomes rank 2.

offset = time.offset( [0,10,20], 'ms', axis=1)
print("Shape with orthogonal time offsets: %s"%list(ds.shape))

# Add a center point variable in the pulse_freq dimension who's values should
# map along dataset axis 1.  Make these out of order in offset time.
#
# We will now have two arrays that 'tag' axis 1.  With ISTP metadata CDFs this
# is a bit of an issue since you can't have two 'DEPEND_1' variables, but here
# it's no problem.  Note, it's not a problem in the base CDF specification
# either, just the ISTP metadata.

ds.coord('pulse_freq').center([4,3,5], 'MHz', axis=1)
print("Shape with pulse frequencies: %s"%list(ds.shape))

# Add center points in the range dimension.  Have thes values map along
# dateset axis 2.  Since the new array is orthoganal to both of the existing
# arrays the dataset becomes rank 3.

ds.coord('range').center(np.arange(5)*10 + 25, 'km',  axis=2)
print("Shape with echo return ranges: %s"%list(ds.shape))

# Add center points in the spectral density dimension.  We're adding a
# rank 3 array to the dataset without an axis shift so the shape remains
# unchanged.
ds.data('spec_dens').center(
   [   [  [321,322,323,324,325],
         [311,312,313,314,315],
         [331,332,333,334,335]   ],
      [   [121,122,123,124,125],
         [111,112,113,114,115],
         [131,132,133,134,135]   ],
      [  [421,422,423,424,425],
         [411,412,413,414,415],
         [431,432,433,434,435]   ],
      [   [221,222,223,224,225],
         [211,212,213,214,215],
         [231,232,233,234,235]   ]
   ],
   'V**2 m**-2 Hz**-1', fill=0.0
)
print("Shape with return intensities: %s"%list(ds.shape))

# Print a single slice of a single ionogram.  The same indices can be used
# with every array since all variables use numpy array broadcasting to match
# the shape of the overall dataset.

print("The 2nd pulse from 2nd Ionogram...")
for i in range(ds.shape[2]):
   print("%s, %s, %s, %s"%(
      ds['time']['center'][2,2,i],
      ds['pulse_freq']['center'][2,2,i],
      ds['range']['center'][2,2,i],
      ds['spec_dens']['center'][2,2,i]
   ))

# Sort on pulse0 times and then range
ds.sort('time:reference','range')

