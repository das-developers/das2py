"""Testing Dataset sorting algorithms"""

import sys
import numpy as np
import das2

# Get around numpy printing bugs
import os, time
os.environ['TZ'] = 'UTC'
time.tzset()

prn = sys.stdout.write

lDs = das2.read_file('test/test_sort.d2t')

##############################################################################
# Sort manually a 6x6 dataset of time, freq and amplitude

print("6x6 case...\n")

ds = lDs[0]

# Reshaping .... 

shape = ds.shape()

aT = ds['time']['center'].array
aF = ds['frequency']['center'].array
aA = ds['amp']['center'].array

aI = aT.argsort(kind='mergesort', axis=0)
aJ = aF.argsort(kind='mergesort', axis=1)
aIdent = np.arange(shape[1])

ds['time']['center'].array = aT[aI, aJ]
ds['frequency']['center'].array = aF[aI, aJ]
ds['amp']['center'].array = aA[aI, aJ]

# Printing...
aT = ds['time']['center'].array[:,0]
aF = ds['frequency']['center'].array[0,:]
aA = ds['amp']['center'].array

# Header
prn(" "*len(str(aT[0])[:-24]))
for j in range(ds.shape()[1]):
	prn(" %s"%aF[j])
prn(' %s\n'%ds['frequency']['center'].units)

for i in range(ds.shape()[0]):
	prn(str(aT[i])[:-24])
	for j in range(ds.shape()[1]):
		prn(" %s"%aA[i,j])
	prn(' %s\n'%ds['amp']['center'].units)
	
	
print(" \n ")

##############################################################################
# Sort manually a 36 x 1 dataset of time, freq and amplitude

print("36 x 1 case...\n")

ds = lDs[1]

# Reshaping ...
shape = ds.shape()

aT = ds['time']['center'].array
aF = ds['frequency']['center'].array
aA = ds['amp']['center'].array

aRecs = np.rec.fromarrays([aT,aF], names=['time','frequency'])
aI = aRecs.argsort(kind='mergesort', order=['time','frequency'])

ds['time']['center'].array = aT[aI]
ds['frequency']['center'].array = aF[aI]
ds['amp']['center'].array = aA[aI]


# Printing...

aT = ds['time']['center'].array
aF = ds['frequency']['center'].array
aA = ds['amp']['center'].array

# Header
prn(" "*len(str(aT[0])[:-24]))
for i in range(6):
	prn(" %s"%aF[i])
prn(' %s\n'%ds['frequency']['center'].units)

for i in range(6):
	prn(str(aT[i*6])[:-24])
	for j in range(6):
		prn(" %s"%aA[i*6 + j])
	prn(' %s\n'%ds['amp']['center'].units)

print(" \n ")

##############################################################################
# Now for something odd, sort on amplitude which is a 6x6 array

print("6 x 6, 2-D flaten case...\n")

lDs = das2.read_file('test/test_sort.d2t')
ds = lDs[0]

shape = ds.shape()

aAflat = ds['amp']['center'].array.reshape(-1)
aTflat = ds['time']['center'].array.reshape(-1)
aFflat = ds['frequency']['center'].array.reshape(-1)

aI = aAflat.argsort(kind='mergesort', axis=None)

ds['time']['center'].array      = aTflat[aI].reshape(shape)
ds['frequency']['center'].array = aFflat[aI].reshape(shape)
ds['amp']['center'].array       = aAflat[aI].reshape(shape)

# Now print as in the first case
# Printing...
aT = ds['time']['center'].array[:,0]
aF = ds['frequency']['center'].array[0,:]
aA = ds['amp']['center'].array

# Header
prn(" "*len(str(aT[0])[:-24]))
for j in range(ds.shape()[1]):
	prn(" %s"%aF[j])
prn(' %s\n'%ds['frequency']['center'].units)

for i in range(ds.shape()[0]):
	prn(str(aT[i])[:-24])
	for j in range(ds.shape()[1]):
		prn(" %s"%aA[i,j])
	prn(' %s\n'%ds['amp']['center'].units)
	
print(" \n ")














