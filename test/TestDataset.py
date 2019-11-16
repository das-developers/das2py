import das2
import numpy

import das2.cdf  # Extra functionality that depends on pycdf, will fail 

#   NOT REAL CODE, JUST IDEAS, DON'T USE
#
# These are just ideas, incase some wants to create datasets without reading
# a das2 stream.  This seems like overkill since I'd imagine that some other
# data model would handle this, such as a pandas dataframe.
#
# A prototype of manually creating das2 Datasets is given here so that basic
# functions included in the higher level das2 library don't conflict with
# creating functionality like this in the future, though it may never be
# needed.

ds = das2.Dataset()

a = numpy.array([6,5,4,3,2,2])
b = numpy.array([20,10,30,60,50,40])
c = numpy.array([a+b[0]],[a+b[1]],[a+b[2]],[a+b[3]],[a+b[4]],[a+b[5]]])

ds['coord:frequency'] = das2.Variable(a, "Hz", axis=1)
ds['coord:time'] = das2.Variable(b, "s")
ds['data:amp'] = das2.Variable(c, "V/m")

ds.sortAsc('time','freq')

# In memory conversion
cdf = das2.cdf.convert(ds)

# Write to a file
das2.cdf.write(ds, sys.stdout)
