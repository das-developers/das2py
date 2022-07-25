export DAS2C_LIBDIR
export DAS2C_INCDIR

LIBDAS=das2.3

# Project definitions #########################################################
BD=build.$(N_ARCH)

SRC=_das2.c
PYSRC=util.py __init__.py dastime.py toml.py source.py dataset.py \
 container.py pkt.py mpl.py auth.py node.py streamsrc.py cdf.py reader.py

SCRIPTS=das_verify

CDFSRC=__init__.py const.py

SCHEMA=das-basic-stream-v2.2.xsd das-basic-stream-v3.0.xsd \
 das-basic-stream-ns-v3.0.xsd das-basic-doc-ns-v3.0.xsd

BUILT_PYSRC=$(patsubst %,$(BD)/das2/%,$(PYSRC))
INSTALLED_PYSRC=$(patsubst %.py,$(INST_HOST_LIB)/das2/%.py,$(PYSRC))

INSTALLED_CDFSRC=$(patsubst %.py,$(INST_HOST_LIB)/das2/pycdf/%.py,$(CDFSRC))

# Treat schemas as package data
INSTALLED_SCHEMA=$(patsubst %.xsd,$(INST_HOST_LIB)/das2/xsd/%.xsd,$(SCHEMA))

INSTALLED_SCRIPTS=$(patsubst %,$(INST_BIN)/%, $(SCRIPTS))

# Pattern Rules #############################################################

$(INST_HOST_LIB)/das2/%.py:$(BD)/das2/%.py
	install -D -m 664 $< $@
	
$(INST_HOST_LIB)/das2/pycdf/%.py:$(BD)/das2/pycdf/%.py
	install -D -m 664 $< $@
	
$(INST_HOST_LIB)/das2/xsd/%.xsd:$(BD)/das2/xsd/%.xsd
	install -D -m 664 $< $@

$(INST_BIN)/%:$(BD)/scripts-$(PYVER)/%
	install -D -m 775 $< $@	

# Explicit Rules #############################################################

.PHONY: test

build: $(BD) $(BD)/_das2.so $(DAS2C_LIBDIR)/lib$(LIBDAS).a

$(BD):
	@if [ ! -e "$(BD)" ]; then echo mkdir $(BD); \
        mkdir $(BD); chmod g+w $(BD); fi

$(BD)/_das2.so:src/_das2.c
	python$(PYVER) setup.py build -g -b $(BD) -t $(BD) --build-lib=$(BD)
	@if [ ! -e "$(BD)/_das2.so" ]; then mv $(BD)/_das2.cpython-*.so $@ ; fi

# Run tests
test:
	env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) test/TestRead.py
	env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) test/TestDasTime.py
	env PYVER=$(PYVER) PYTHONPATH=$(PWD)/$(BD) test/das2_dastime_test1.sh $(BD)
	env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) test/TestCatalog.py
	env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) test/TestSortMinimal.py
	env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) scripts/das_verify test/ex05_waveform_extra.d3t
	env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) scripts/das_verify test/ex06_waveform_binary.d3t
	env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) scripts/das_verify test/ex08_dynaspec_namespace.d3t
	env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) scripts/das_verify test/ex12_sounder_xyz.d3t
	env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) scripts/das_verify test/ex13_object_annotation.d3t
	env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) scripts/das_verify test/ex96_yscan_multispec.d2t


# Install purelib and extensions (python setup.py is so annoyingly
# restrictive that we'll just do this ourselves)
install:$(INST_EXT_LIB)/_das2.so  $(INSTALLED_PYSRC) $(INSTALLED_CDFSRC) \
 $(INSTALLED_SCHEMA) $(INSTALLED_SCRIPTS)

doc:
	cd sphinx_doc && $(MAKE) html


$(INST_EXT_LIB)/_das2.so:$(BD)/_das2.so
	install -D -m 775 $(BD)/_das2.so $(INST_EXT_LIB)/_das2.so

clean:
	if [ -d "$(BD)" ]; then rm -r $(BD); fi

distclean:
	if [ -d "$(BD)" ]; then rm -r $(BD); fi

