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

# Realpath is part of the POSIX standard, hopefully it's available here
ifeq ($(DAS_INCDIR),)

ifeq ($(DAS2C),)
DAS_INCDIR:=$(shell realpath $(PWD)/../das2C)
else
DAS_INCDIR:=$(DAS2C)
endif 

endif

ifeq ($(DAS_LIBDIR),)

ifeq ($(DAS2C),)
DAS_LIBDIR:=$(shell realpath $(PWD)/../das2C/build.$(N_ARCH))
else
DAS_LIBDIR:=$(shell realpath $(DAS2C)/build.$(N_ARCH))
endif

endif

# Just depend on das2C providing a working libcdf.so and copy it in, don't 
# worry about CDF_LIB

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
VDIR:=py3_venv
else
WHEEL_FILE:=das2py-$(DAS_PY_VER)-cp$(PY_VER_TOK)-cp$(PY_VER_TOK)m-linux_x86_64.whl
VENV_MOD:=virtualenv
PY_VER_WARN:=--no-python-version-warning
VDIR:=py2_venv
endif

# If you can't find libcdf.so CDF_LIBDIR then copy it in from das2C.

# ########################################################################### #

# The extension sources belong here too.  Without them a C-only edit leaves
# dist/ newer than everything make knows about, so the wheel is silently not
# rebuilt and you test the previous build.

SRC:= \
src/_das3.c \
src/py_builder.h \
src/py_catalog.h \
src/py_dft.h \
das3/__init__.py \
das3/auth.py \
das3/cdf.py \
das3/cli.py \
das3/container.py \
das3/das-basic-doc-ns-v3.0.xsd \
das3/das-basic-stream-ns-v3.0.xsd \
das3/das-basic-stream-v2.2.xsd \
das3/das-basic-stream-v3.0.xsd \
das3/dastime.py \
das3/dataset.py \
das3/mpl.py \
das3/node.py \
das3/pkt.py \
das3/reader.py \
das3/source.py \
das3/streamsrc.py \
das3/toml.py \
das3/util.py \
das3/verify.py \
das3/pycdf/__init__.py \
das3/pycdf/const.py \
das3/pycdf/LICENSE.md \
das2/__init__.py

.PHONY: build dist test install clean distclean examples

build:dist/$(WHEEL_FILE)

# The static das2C library is linked into the extension, so a das2C rebuild
# must trigger a wheel rebuild too, or you test against the previous library.
dist/$(WHEEL_FILE):$(SRC) $(DAS_LIBDIR)/libdas3.a build_$(VDIR)/bin/python
	DAS_INCDIR=$(DAS_INCDIR) DAS_LIBDIR=$(DAS_LIBDIR) build_$(VDIR)/bin/python -m build

build_$(VDIR)/bin/python:
	$(PY_BIN) -m $(VENV_MOD) build_$(VDIR)
	build_$(VDIR)/bin/python -m pip install $(PY_VER_WARN) build

test:dist/$(WHEEL_FILE)
	# Creating temporary environment for testing
	$(PY_BIN) -m $(VENV_MOD) test_$(VDIR)
	./test_$(VDIR)/bin/python -m pip install --isolated $(PY_VER_WARN) dist/$(WHEEL_FILE)
	@./test_$(VDIR)/bin/python -c 'import numpy;print("===================================");print("  Numpy Runtime Version is %s"%numpy.__version__);		print("===================================")'
	./test_$(VDIR)/bin/python test/CheckPortable.py
	./test_$(VDIR)/bin/python test/TestCatalog.py
	./test_$(VDIR)/bin/python test/TestDasTime.py
	./test_$(VDIR)/bin/python test/TestSortMinimal.py
	./test_$(VDIR)/bin/python test/TestRead.py
	./test_$(VDIR)/bin/python test/TestComposite.py
	./test_$(VDIR)/bin/python test/TestAlias.py
	./test_$(VDIR)/bin/das_verify -h
	./test_$(VDIR)/bin/das_verify test/ex05_waveform_extra.d3t
	./test_$(VDIR)/bin/das_verify test/ex40_rotation.d3t
	./test_$(VDIR)/bin/das_verify test/ex43_msc_complex_cal.d3b
	./test_$(VDIR)/bin/das_verify test/ex16_mag_grid_doc.d3x
	./test_$(VDIR)/bin/das_cdf_info -h 
	./test_$(VDIR)/bin/das_cdf_info test/vg1_pws_wf_2023-10-24T03_v1.0.cdf
	@echo "All tests ran without returning an error code"

examples:
	# Creating temporary environment for testing, verify more streams, re-gen all example plots
	$(PY_BIN) -m $(VENV_MOD) test_$(VDIR)
	./test_$(VDIR)/bin/python -m pip install --isolated $(PY_VER_WARN) dist/$(WHEEL_FILE)
	./test_$(VDIR)/bin/python -m pip install --isolated $(PY_VER_WARN)  matplotlib
	@./test_$(VDIR)/bin/python -c 'import numpy;print("===================================");print("  Numpy Runtime Version is %s"%numpy.__version__);		print("===================================")'
	./test_$(VDIR)/bin/das_verify test/ex06_waveform_binary.d3b
	./test_$(VDIR)/bin/das_verify test/ex08_dynaspec_namespace.d3t
	./test_$(VDIR)/bin/das_verify test/ex12_sounder_xyz.d3t
	./test_$(VDIR)/bin/das_verify test/ex13_object_annotation.d3t
	./test_$(VDIR)/bin/das_verify test/ex14_object_tfcat.d3t
	./test_$(VDIR)/bin/das_verify test/ex15_vector_frame.d3t
	./test_$(VDIR)/bin/das_verify test/ex16_mag_grid_doc.d3x
	./test_$(VDIR)/bin/das_verify test/ex17_vector_noframe.d3b
	./test_$(VDIR)/bin/das_verify test/ex22_mag_grid_vec.d3t
	./test_$(VDIR)/bin/das_verify test/ex40_rotation.d3b
	./test_$(VDIR)/bin/das_verify test/ex41_quaternion.d3t
	./test_$(VDIR)/bin/das_verify test/ex42_plain_tensor.d3t
	./test_$(VDIR)/bin/das_verify test/ex43_msc_complex_cal.d3t
	./test_$(VDIR)/bin/das_verify test/ex96_yscan_multispec.d2t
	./test_$(VDIR)/bin/python examples/c_module/galileo_pws_e-survey.py
	./test_$(VDIR)/bin/python examples/c_module/juno_hfwbr_cdf.py
	./test_$(VDIR)/bin/python examples/ex01_source_queries.py
	./test_$(VDIR)/bin/python examples/ex02_galileo_pws_spectra.py	
	./test_$(VDIR)/bin/python examples/ex03_cassini_rpws_multimode.py
	./test_$(VDIR)/bin/python examples/ex04_voyager_pws_query_by_time.py
	./test_$(VDIR)/bin/python examples/ex08_juno_waves_wfrm_to_cdf.py
	./test_$(VDIR)/bin/python examples/ex09_cassini_fce_ephem_ticks.py 2017-01-02
	./test_$(VDIR)/bin/python examples/ex10_manual_datasets.py
	./test_$(VDIR)/bin/python examples/ex11_catalog_listings.py
	@echo "All examples ran without returning an error code"


install:
	$(PY_BIN) -m pip uninstall -y --isolated --no-python-version-warning das2py
	$(PY_BIN) -m pip install --isolated --no-python-version-warning ./dist/$(WHEEL_FILE)

clean:
	-rm -r dist test_*_venv *.egg-info

distclean:
	-rm -r dist test_*_venv build_*_venv *.egg-info

