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
(base) $ wget https://saturn.physics.uiowa.edu/svn/das2/core/stable/libdas2_3/bindings/python/examples/ex02_galileo_pws_spectra.py
(base) $ python ex02_galileo_pws_spectra.py
```
If this command produces a plot similar to the following:

<img src="https://raw.githubusercontent.com/das-developers/das2py/master/examples/ex05_mex_marsis_query_by_angle.png" width="660" height="379">

Then das2py is installed and there is no need to follow the rest of these instructions.

## Prerequistes
Compilation and installation of das2py has been tested on Linux, Windows, MacOS using
both Python 2 and Python 3.  The following dependencies should be installed before
building the software.

  * **Das2C** - Version 2.3 or above, must be built )
  * **NumPy** - Version 1.10.1 or above
  * **MatplotLib++** - For plotting data
  * **SpacePy** - To write to CDF files.

Package manager commands for common operating systems follow

  * numpy-dev version 1.10 or above
  * das2c     verison 2.3

## Build and Install

More information on the way soon.  Here's the basics.

```bash
export DAS2C_INCDIR=/home/you/git/das2C
export DAS2C_LIBDIR=/home/you/git/das2C/build.GNU_Linux.x86_64
export PYVER=3.7
make
make test
make install
```
