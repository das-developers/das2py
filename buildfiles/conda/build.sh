#!/usr/bin/env bash

DAS2C_LIBDIR=${BUILD_PREFIX}/lib
DAS2C_INCDIR=${BUILD_PREFIX}/include

export DAS2C_LIBDIR
export DAS2C_INCDIR

#${PYTHON} -m pip -v wheel ./
${PYTHON} setup.py build
#${PYTHON} -m pip -v install --no-deps ./das2py*.whl
${PYTHON} setup.py install
