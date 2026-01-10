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
target, and it allows you to specify the exact version of python you are using.

```bash
make DAS2C=${PWD}/../das2C          # Just get's python3 from path
make DAS2C=${PWD}/../das2C test
make DAS2C=${PWD}/../das2C examples # Insures all examples work successfully
```
or for a specific python version:
```bash
make DAS2C=${PWD}/../das2C PY_BIN=$(which python3.9)
make DAS2C=${PWD}/../das2C PY_BIN=$(which python3.9) test
make DAS2C=${PWD}/../das2C PY_BIN=$(which python3.9) examples
```
To build against python2 you'll have to provide the path to the interpreter.

At the end of the build you'll have a `*.whl` file in `dist` similar to the standard build, but
the code will have been tested first.

To install it, make sure the desired version of python is first in your path, then issue:
```
python3 -m pip install ./dist/*.whl
```
or for a specific version of python:
```
$PY_BIN -m pip install ./dist/*.whl
```


