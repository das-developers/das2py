# Simple wrapper around PIP so that higher level tools can invoke using
# make, make test, make install etc.
#
# Asumes the following are set:
#
#  PY_BIN
#  DAS2C_INCDIR
#  DAS2C_LIBDIR

# Find a way to get this from the manifest
DAS_PY_VER:=3.0rc5

ifeq ($(PY_BIN),)
PY_BIN=$(which python)

ifeq ($(PY_BIN),)
PY_BIN=$(which python3)
endif

ifeq ($(PY_BIN),)
$(error Neither python nor python3 were found, set PY_BIN to the path to your python interpreter)
endif
endif

ifeq ($(DAS2C_INCDIR),)
$(error Please set DAS2C_INCDIR to the das2C include directory)
endif

ifeq ($(DAS2C_LIBDIR),)
$(error Please set DAS2C_LIBDIR to the das2C archive library name aka: /path/to/libdas3.0.a )
endif

# ########################################################################### #
# Try to predict the wheel name.  This is a fools game but most standard tools
# will skip this makefile anyway and jump straight to a python -m build style
# command.

PY_VER_TOK:=$(shell $(PY_BIN) -c "import sys; print('%d%d'%sys.version_info[0:2])")
PY_MAJ_VER_TOK:=$(shell $(PY_BIN) -c "import sys; print(sys.version_info[0])")

ifeq ($(PY_MAJ_VER_TOK),3)
WHEEL_FILE:=das2py-$(DAS_PY_VER)-cp$(PY_VER_TOK)-cp$(PY_VER_TOK)-linux_x86_64.whl
VENV_MOD:=venv
else
WHEEL_FILE:=das2py-$(DAS_PY_VER)-cp$(PY_VER_TOK)-cp$(PY_VER_TOK)m-linux_x86_64.whl
VENV_MOD:=virtualenv
endif

# ########################################################################### #

SRC:= \
das2/__init__.py \
das2/auth.py \
das2/cdf.py \
das2/cli.py \
das2/container.py \
das2/das-basic-doc-ns-v3.0.xsd \
das2/das-basic-stream-ns-v3.0.xsd \
das2/das-basic-stream-v2.2.xsd \
das2/das-basic-stream-v3.0.xsd \
das2/dastime.py \
das2/dataset.py \
das2/mpl.py \
das2/node.py \
das2/pkt.py \
das2/reader.py \
das2/source.py \
das2/streamsrc.py \
das2/toml.py \
das2/util.py \
das2/verify.py \
das2/pycdf/__init__.py \
das2/pycdf/const.py \
das2/pycdf/LICENSE.md

.PHONY: build dist test install clean distclean

build:dist/$(WHEEL_FILE)

dist/$(WHEEL_FILE):$(SRC)
	DAS2C_INCDIR=$(DAS2C_INCDIR) DAS2C_LIBDIR=$(DAS2C_LIBDIR) $(PY_BIN) -m build

test:
	# Creating temporary environment for testing
	$(PY_BIN) -m $(VENV_MOD) dist_venv
	./dist_venv/bin/python -m pip install --isolated --no-python-version-warning dist/$(WHEEL_FILE)
	./dist_venv/bin/python test/TestCatalog.py
	./dist_venv/bin/python test/TestDasTime.py
	./dist_venv/bin/python test/TestSortMinimal.py
	./dist_venv/bin/python test/TestRead.py
	rm -r dist_venv

install:
	$(PY_BIN) -m pip uninstall -y --isolated --no-python-version-warning das2py
	$(PY_BIN) -m pip install --isolated --no-python-version-warning ./dist/$(WHEEL_FILE)

clean:
	-rm -r dist dist_venv *.egg-info

distclean:
	-rm -r dist dist_venv *.egg-info

