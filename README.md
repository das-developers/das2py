# das2py
An efficient space physics data client for python.

## Anaconda Package
[![Anaconda Package](https://anaconda.org/dasdevelopers/das2py/badges/version.svg)](https://anaconda.org/DasDevelopers/das2py)

Pre-build versions of das2py are available from Anoconda.  If you're working in an 
Anoconda or Miniconda python 3 environment these are easier to install as no C 
compiler is required.   To install the conda package run the command:
```bash
(base) $ conda install -c dasdevelopers das2py
```
If this works then test using:
```bash
(base) $ wget https://raw.githubusercontent.com/das-developers/das2py/master/examples/ex05_mex_marsis_query_by_angle.py
(base) $ python ex02_galileo_pws_spectra.py
```
If this command produces a plot similar to the following:

<img src="https://raw.githubusercontent.com/das-developers/das2py/master/examples/ex05_mex_marsis_query_by_angle.png" width="660" height="379">

Then das2py is installed and there is no need to follow the rest of these instructions.

## Prerequistes
Compilation and installation of das2py has been tested on Linux, Windows, MacOS using
both Python 2 and Python 3.  The following packages are required to build das2py:

  * [Das2C](https://github.com/das-developers/das2C) - Version 2.3 or above, need not be installed, but must be built
  * **NumPy** - Version 1.10.1 or above
  * **MatplotLib++** - For plotting data (optional, recommended)
  * **SpacePy** - For writing CDF files (optional)

## Build and Install
Decide where you want to install das2py.  In the example below I've selected 
`/usr/local/lib/python3.6/site-packages` but any location is fine so long as
it is on the `PYTHONPATH` or you are willing to add it to your PYTHONPATH.

```bash
# Where to find the das2C static library
$ export DAS2C_INCDIR=$HOME/das2C
$ export DAS2C_LIBDIR=$HOME/das2C/build.GNU_Linux.x86_64

# Which python version to use
$ export PYVER=3.7

# Where you want to install the files
$ export INST_HOST_LIB=/usr/local/lib/python3.6
$ export INST_EXT_LIB=/usr/local/lib/python3.6

# Build and test
$ make
$ make test

# Check install location, then install
$ make -n install
$ make install
```

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




