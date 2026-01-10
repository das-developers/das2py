# Building and installing das2py without a python wheel


First setup the system prerequisites as defined in the main [ReadMe.md](../README.md),
then proceed.  The following should work all the way back to python 2.7.

Decide where you want to install das2py.  In the example below I've selected 
`/usr/local/lib/python3.9/site-packages` but any location is fine so long as
it is on the `PYTHONPATH` or you are willing to add it to your PYTHONPATH.

First build das2C with CDF and SPICE support
```
git clone git@github.com:das-developers/das2C.git
cd das2C
env make CDF=yes SPICE=yes
env make CDF=yes SPICE=yes test
cd ../
```
Now call python build through the makefile.  This has the advantage of providing a `make test`
target.  Note that other versions of python may be specified.

```bash
make DAS_INCDIR=${PWD}/../das2C DAS_LIBDIR=${PWD}/../das2C/build. PY_BIN=$(which python3.9)
make DAS_INCDIR=${PWD}/../das2C DAS_LIBDIR=${PWD}/../das2C/build. PY_BIN=$(which python3.9) test
```

At the end of the build you'll have a `*.whl` file in `dist` similar to the standard build, but
the code will have been tested first.

To install it, make sure the desired version of python is first in your path, then issue:
```
python3 -m pip install ./dist/*.whl
```

TODO: Figure out where to put libcdf.so


