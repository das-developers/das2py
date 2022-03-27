#!/usr/bin/env bash


PYVER=$PY_VER
N_ARCH=/

export PYVER
export N_ARCH

make
make pylib
make pylib_install
