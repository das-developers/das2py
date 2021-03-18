##############################################################################
# Generic definitions for: Native Programs + Hosted Python
#
ifeq ($(PREFIX),)
ifeq ($(HOME),)
PREFIX:=$(USERPROFILE)
else
PREFIX=$(HOME)
endif
endif

ifeq ($(N_ARCH),)
N_ARCH=$(shell uname -s).$(shell uname -p)
endif

ifeq ($(DAS2C_INCDIR),)
DAS2C_INCDIR=$(PREFIX)/include/$(N_ARCH)
endif

ifeq ($(DAS2C_LIBDIR),)
DAS2C_LIBDIR=$(PREFIX)/lib/$(N_ARCH)
endif

ifeq ($(INST_SHARE),)
INST_SHARE=$(PREFIX)/share
endif

ifeq ($(INST_DOC),)
INST_DOC=$(INST_SHARE)/doc
endif

ifeq ($(PYVER),)
PYVER=$(shell python -c "import sys; print('.'.join( sys.version.split()[0].split('.')[:2] ))")
endif

ifeq ($(H_ARCH),)
H_ARCH=python$(PYVER)
endif

ifeq ($(INST_HOST_LIB),)
INST_HOST_LIB=$(PREFIX)/lib/$(H_ARCH)
endif

ifeq ($(INST_EXT_LIB),)
INST_EXT_LIB=$(PREFIX)/lib/$(N_ARCH)/$(H_ARCH)
endif

BUILD_DIR:=build.$(N_ARCH)

##############################################################################
# Native Platform specific include

UNAME = $(shell uname)

include makefiles/$(UNAME).mak
