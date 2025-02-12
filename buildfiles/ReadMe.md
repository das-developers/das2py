# Building and installing das2py without PIP


First setup the system prerequisites as defined in the main [ReadMe.md](../README.md),
then proceed.  The following should work back to python 2.7.

Decide where you want to install das2py.  In the example below I've selected 
`/usr/local/lib/python3.9/site-packages` but any location is fine so long as
it is on the `PYTHONPATH` or you are willing to add it to your PYTHONPATH.

First install LIB CDF and NAIF CSpice from:
```
https://spdf.gsfc.nasa.gov/pub/software/cdf/dist/cdf39_1/linux/cdf39_1-dist-cdf.tar.gz
https://naif.jpl.nasa.gov/pub/naif/toolkit/C/PC_Linux_GCC_64bit/packages/cspice.tar.Z
```
The rest assumes you've unzipped these in /usr/local, so adjust paths as necessary.

```bash
# First build and test das2C, installation is not necessary
git clone git@github.com:das-developers/das2C.git
cd das2C

export N_ARCH=/
export PREFIX=/usr/local
export CSPICE_INC=/usr/local/cspice/include
export CSPICE_LIB=/usr/local/cspice/lib/cspice.a
export CDF_INC=/usr/local/cdf/include
export CDF_LIB=/usr/local/cdf/lib/libcdf.a
env make SPICE=yes CDF=yes
env make SPICE=yes CDF=yes test
cd ../

# Where to find the das2C static library
$ export DAS2C_INCDIR=${PWD}/das2C
$ export DAS2C_LIBDIR=${PWD}/das2C/build.  #last dot is not a typo

# Which python version to use
$ export PYVER=3.9

# Where you want to install the files
$ export INST_HOST_LIB=/usr/local/lib/python3.9
$ export INST_EXT_LIB=/usr/local/lib/python3.9

# Build and test
$ make -f buildfiles/Makefile           # <-- If only using system packages
$ make -f buildfiles/Makefile local     # <-- If using numpy or others from $HOME/.local
$ make -f buildfiles/Makefile test

# Check install location, then install
$ make -f buildfiles/Makefile -n install
$ make -f buildfiles/Makefile install
```

To run das2py you'll have to insure that
```
PYTHONPATH=/usr/local/lib/python3.9
```
or equivalent is set in your environment.

