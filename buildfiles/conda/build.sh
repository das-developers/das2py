#!/usr/bin/env bash

#PYVER=3.9
N_ARCH=/

#export PYVER
export N_ARCH

make
make test
make install
