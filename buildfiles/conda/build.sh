#!/usr/bin/env bash

PREFIX=${BUILD_PREFIX}
export PREFIX

PYVER=$(${PYTHON} -c "import sys; print('.'.join( sys.version.split()[0].split('.')[:2] ))")
N_ARCH=/
H_ARCH=/

# Two stage lib setting so that variables can be subsituted
INST_HOST_LIB="${PREFIX}/lib/${PYTHON}${PYVER}/site-packages"

echo ">>>>HOST LIB INST:${INST_HOST_LIB}<<<<<"

export PYVER
export N_ARCH
export H_ARCH
export INST_HOST_LIB

# Tired of python's "choose your own adventure" install methods.  Getting a
# straight answer out of python for binary extensions is like pulling teeth,
# just use make until we hit the v3.0 dev branch.
make
make test
make install
