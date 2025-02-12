# Simple wrapper around PIP so that higher level tools can invoke using
# make, make test, make install etc.
#
# Asumes the following are set:
#
#  PYVENV
#  DAS2C_INCDIR
#  DAS2C_LIBDIR

ifeq ($(PYVENV),)
$(error Please set PYVENV to the root of your python virtual environment.  To use system python set PYVENV=/usr and PYVER=3.7 or similar)
endif

ifeq ($(DAS2C_INCDIR),)
$(error Please set DAS2C_INCDIR to the das2C include directory)
endif

ifeq ($(DAS2C_LIBDIR),)
$(error Please set DAS2C_LIBDIR to the das2C archive library name aka: /path/to/libdas3.0.a )
endif

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

build: dist/das2py-3.0rc4.tar.gz

dist/das2py-3.0rc4.tar.gz:$(SRC)
	DAS2C_INCDIR=$(DAS2C_INCDIR) DAS2C_LIBDIR=$(DAS2C_LIBDIR) $(PYVENV)/bin/python -m build

install:
	$(PYVENV)/bin/python$(PYVER) -m pip install ./dist/das2py*whl

clean:
	-rm -r dist *.egg-info

distclean:
	-rm -r dist *.egg-info

