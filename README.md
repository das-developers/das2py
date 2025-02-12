# das2py
Das2 servers typically provide data relevant to space plasma and magnetospheric
physics research. To retrieve data, an HTTP GET request is posted to a das2
server by a client program and a self-describing stream of data values covering
the requested time range, at the requested time resolution, is provided in the
response body. This package, *das2py* provides an efficient space physics data
client for python.  Streams are parsed and stored as NumPy arrays using a C
extension, avoiding data copies and conversions.

## Anaconda Package
[![Anaconda Package](https://anaconda.org/dasdevelopers/das2py/badges/version.svg)](https://anaconda.org/DasDevelopers/das2py)

Pre-build versions of das2py are available from Anaconda.  If you're working in an 
Anoconda or Miniconda python 3 environment these are easier to install as no C 
compiler is required.   To install the conda package run the command:
```bash
(base) $ conda install -c dasdevelopers das2py
```
The anaconda package automatically pulls in [das2C](https://anaconda.org/dasdevelopers/das2c), 
[pycdf](https://anaconda.org/dasdevelopers/pycdf), and [pthreads4w](https://anaconda.org/dasdevelopers/pthreads4w) as needed.

If this works then test using:
```bash
(base) $ wget https://raw.githubusercontent.com/das-developers/das2py/master/examples/ex05_mex_marsis_query_by_angle.py
(base) $ python ex02_galileo_pws_spectra.py
```
If this command produces a plot similar to the following\.\.\.

<img src="https://raw.githubusercontent.com/das-developers/das2py/master/examples/ex05_mex_marsis_query_by_angle.png" width="660" height="379">

\.\.\.then das2py is installed, and you can skip building the software and
head straight the example program below.

## Prerequisite
Compilation and installation of das2py has been tested on Linux, Windows, MacOS using
both Python 2 and Python 3.  The following packages are required to build das2py:

  * [Das2C](https://github.com/das-developers/das2C) - Version 3.0 or above.  Need not be installed, but must be built
  * **NumPy** - Version 1.10.1 or above
  * **MatplotLib++** - For plotting data (optional, recommended)
  * **[CDF](https://spdf.gsfc.nasa.gov/pub/software/cdf/dist/cdf38_1/cdf38_1-dist-cdf.tar.gz)** - For writing CDF files (optional)

Pre-requisite package install commands are give below.
```bash
$ sudo apt install python3-setuptools python3-dev python3-numpy # debian
```

## New build instructions (wheel)

In this version, almost no environment variables are needed  Below, das2C
is built adjacent to das2py so that it can be included in das2py.
```bash
# (Works on Linux, more steps needed on Windows & MacOS. 
#  See buildfiles/pypi/ReadMe.md for details)

# First build and test das2C, installation is not necessary
git clone git@github.com:das-developers/das2C.git
cd das2C
env N_ARCH=/ make 
env N_ARCH=/ make test
cd ../

# make sure the build and venv packages are installed
apt install python3-build python3-venv  #<-- Or use PIP

# Now build das2py using the PIP of your choice in an adjacent directory
git clone git@github.com:das-developers/das2py.git
cd das2py
env DAS2C_LIBDIR=$PWD/../das2C/build. DAS2C_INCDIR=$PWD/../das2C python3.9 -m build
```
That's it!  Now you have a wheel file that can be installed where ever you
like.  The included setup.py instructs the python setuptools module to staticlly
link das2C. So the wheel is self contained.

To install your new wheel into the user-local area:
```bash
pip3.9 install ./dist/das2py-2.3.0-cp310-cp310-linux_x86_64.whl
ls .local/bin/das_verify
ls .local/lib/python3.9/site-packages/das2
ls .local/lib/python3.9/site-packages/_das2*
```

To test it by validating one of the example files...
```bash
das_verify das2py/test/ex96_yscan_multispec.d2t
```
and to generate a plot of Cassini electron cyclotron frequencies.
```bash
python3.9 das2py/examples/ex09_cassini_fce_ephem_ticks.py 2017-09-14
okular cas_mag_fce_2017-09-14.png # Or whatever PNG viewer you like
```

## Building without PIP

See older instructions in [buildfiles/ReadMe.md](buildfiles/ReadMe.md)

## First program

The following small program demonstrates how to query for data and generate a plot 
using das2py.

### Query a URI for reduced resolution data
```python
import das2
src = das2.get_source( 'tag:das2.org,2012:site:/uiowa/galileo/pws/survey_electric/das2' )
dataset = src.get( {'time' : ('1997-05-07T15:00', '1997-05-07T17:00', 4.0)} )[0] 
```
  * Servers come and go.  The federated catalog provides stability for 
    application code by maping URIs to data sources.
  * Browse for URIs using a [das2 catalog](https://das2.org/browse) browser,
    or using das2py to get the root node (see [example 11](https://raw.githubusercontent.com/das-developers/das2py/master/examples/ex11_catalog_listings.py)).

### Access quantities by physical dimensions
```python
print(dataset)

vX = dataset['time']['center']
vY = dataset['frequency']['center']
vZ = dataset['electric']['center'] 
```
  * Datasets contain dimensions. Dimensions contain variables. Each variable in a 
    dimension serves a purpose, the most common is to define the center point of a
    coordinate or measurement. 
  * Array dimensions are not confused with physical dimensions. Dataset meaning is
    not tied to any particular array morphology.

### Use Matplotlib to generate an image.
```python
import matplotlib.pyplot as pyplot
import matplotlib.colors as colors

fig, ax = pyplot.subplots()
scaleZ = colors.LogNorm(vmin=vZ.array.min(), vmax=vZ.array.max())
ax.pcolormesh(vX.array, vY.array, vZ.array, norm=scaleZ, cmap='jet')
pyplot.show() 
```
## Reporting bugs
Please use the github.com [issue tracker](https://github.com/das-developers/das2py/issues) 
report any problems with the library.  If you've fixed a bug, 1) thanks!, 2) please send
a pull request so that your updates can be merged into the main project.




