# Simple wrapper around PIP so that higher level tools can invoke using
# make, make test, make install etc.
#
# Asumes the following are set:
#
#  PY_BIN
#  DAS_INCDIR
#  DAS_LIBDIR

# Find a way to get this from the manifest
DAS_PY_VER:=3.0rc5

ifeq ($(PY_BIN),)
PY_BIN=$(shell which python)

ifeq ($(PY_BIN),)
PY_BIN=$(shell which python3)
endif

ifeq ($(PY_BIN),)
$(error Neither python nor python3 were found, set PY_BIN to the path to your python interpreter)
endif
endif

ifeq ($(DAS_INCDIR),)
ifneq ($(DAS2C),)
DAS_INCDIR:=$(DAS2C)
else
$(error Please set DAS_INCDIR to the das2C include directory)
endif
endif

# Realpath is part of the POSIX standard, hopefully it's available here
ifeq ($(DAS_LIBDIR),)
ifneq ($(DAS2C),)
DAS_LIBDIR:=$(shell realpath $(DAS2C)/build.$(N_ARCH))
else
$(error Please set DAS_LIBDIR to the das2C archive library name aka: /path/to/libdas3.0.a )
endif
endif

ifeq ($(CDF_LIB),)
CDF_LIB:=$(shell realpath $(DAS_LIBDIR))
export CDF_LIB
$(info CDF_LIB set to $(shell realpath $(CDF_LIB)))
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
PY_VER_WARN:=
else
WHEEL_FILE:=das2py-$(DAS_PY_VER)-cp$(PY_VER_TOK)-cp$(PY_VER_TOK)m-linux_x86_64.whl
VENV_MOD:=virtualenv
PY_VER_WARN:=--no-python-version-warning
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
	DAS_INCDIR=$(DAS_INCDIR) DAS_LIBDIR=$(DAS_LIBDIR) $(PY_BIN) -m build

test:
	# Creating temporary environment for testing
	$(PY_BIN) -m $(VENV_MOD) dist_venv
	./dist_venv/bin/python -m pip install --isolated $(PY_VER_WARN) dist/$(WHEEL_FILE)
	@./dist_venv/bin/python -c 'import numpy;print("===================================");print("  Numpy Runtime Version is %s"%numpy.__version__);		print("===================================")'
	./dist_venv/bin/python test/TestCatalog.py
	./dist_venv/bin/python test/TestDasTime.py
	./dist_venv/bin/python test/TestSortMinimal.py
	./dist_venv/bin/python test/TestRead.py
	./dist_venv/bin/das_verify -h
	./dist_venv/bin/das_verify test/ex05_waveform_extra.d3t
	./dist_venv/bin/das_cdf_info -h 
	./dist_venv/bin/das_cdf_info test/vg1_pws_wf_2023-10-24T03_v1.0.cdf
	rm -r dist_venv

test_more:
	# Creating temporary environment for testing, verify more streams, re-gen all example plots
	$(PY_BIN) -m $(VENV_MOD) dist_venv
	./dist_venv/bin/python -m pip install --isolated $(PY_VER_WARN) dist/$(WHEEL_FILE)
	./dist_venv/bin/python -m pip install --isolated $(PY_VER_WARN)  matplotlib
	@./dist_venv/bin/python -c 'import numpy;print("===================================");print("  Numpy Runtime Version is %s"%numpy.__version__);		print("===================================")'
	./dist_venv/bin/das_verify test/ex06_waveform_binary.d3b
	./dist_venv/bin/das_verify test/ex08_dynaspec_namespace.d3t
	./dist_venv/bin/das_verify test/ex12_sounder_xyz.d3t
	./dist_venv/bin/das_verify test/ex13_object_annotation.d3t
	./dist_venv/bin/das_verify test/ex14_object_tfcat.d3t
	./dist_venv/bin/das_verify test/ex15_vector_frame.d3b
	./dist_venv/bin/das_verify test/ex16_mag_grid_doc.d3x
	./dist_venv/bin/das_verify test/ex96_yscan_multispec.d2t
	./dist_venv/bin/python examples/c_module/galileo_pws_e-survey.py
	./dist_venv/bin/python examples/c_module/juno_hfwbr_cdf.py
	./dist_venv/bin/python examples/ex01_source_queries.py
	./dist_venv/bin/python examples/ex02_galileo_pws_spectra.py	
	./dist_venv/bin/python examples/ex03_cassini_rpws_multimode.py
	./dist_venv/bin/python examples/ex04_voyager_pws_query_by_time.py
	./dist_venv/bin/python examples/ex08_juno_waves_wfrm_to_cdf.py
	./dist_venv/bin/python examples/ex09_cassini_fce_ephem_ticks.py 2017-01-02
	./dist_venv/bin/python examples/ex10_manual_datasets.py
	./dist_venv/bin/python examples/ex11_catalog_listings.py

install:
	$(PY_BIN) -m pip uninstall -y --isolated --no-python-version-warning das2py
	$(PY_BIN) -m pip install --isolated --no-python-version-warning ./dist/$(WHEEL_FILE)

clean:
	-rm -r dist dist_venv *.egg-info

distclean:
	-rm -r dist dist_venv *.egg-info

