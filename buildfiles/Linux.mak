export DAS2C_LIBDIR
export DAS2C_INCDIR

# This is important or web-services will end up bound to numpy in .local
NOUSERSITE:=-s

LIBDAS=das3.0

# Project definitions #########################################################
BD=build.$(N_ARCH)

SRC=_das2.c
PYSRC=util.py __init__.py dastime.py toml.py source.py dataset.py \
 container.py pkt.py mpl.py auth.py node.py streamsrc.py cdf.py reader.py \
 cli.py verify.py

SCRIPTS=das_verify

CDFSRC=__init__.py const.py

SCHEMA=das-basic-stream-v2.2.xsd das-basic-stream-v3.0.xsd \
 das-basic-stream-ns-v3.0.xsd das-basic-doc-ns-v3.0.xsd

BUILT_PYSRC=$(patsubst %,$(BD)/das2/%,$(PYSRC))
INSTALLED_PYSRC=$(patsubst %.py,$(INST_HOST_LIB)/das2/%.py,$(PYSRC))

INSTALLED_CDFSRC=$(patsubst %.py,$(INST_HOST_LIB)/das2/pycdf/%.py,$(CDFSRC))

# Treat schemas as package data
INSTALLED_SCHEMA=$(patsubst %.xsd,$(INST_HOST_LIB)/das2/xsd/%.xsd,$(SCHEMA))

INSTALLED_SCRIPTS=$(patsubst %,$(INST_HOST_BIN)/%, $(SCRIPTS))

# Pattern Rules #############################################################

$(INST_HOST_LIB)/das2/%.py:$(BD)/das2/%.py
	install -D -m 664 $< $@
	
$(INST_HOST_LIB)/das2/pycdf/%.py:$(BD)/das2/pycdf/%.py
	install -D -m 664 $< $@
	
$(INST_HOST_LIB)/das2/xsd/%.xsd:$(BD)/das2/xsd/%.xsd
	install -D -m 664 $< $@

$(INST_HOST_BIN)/%:$(BD)/scripts-$(PYVER)/%
	install -D -m 775 $< $@	

# Explicit Rules #############################################################

.PHONY: test examples
	
build: $(BD) $(BD)/_das2.so $(DAS2C_LIBDIR)/lib$(LIBDAS).a

vars:
	@echo $(INSTALLED_SCRIPTS) $(PYVER)

local: $(BD) src/*.c das2/*.py das2/pycdf/*.py das2/xsd/*.xsd
	python$(PYVER) buildfiles/du_setup.py build -g -b $(BD) -t $(BD) --build-lib=$(BD)
	@if [ ! -e "$(BD)/_das2.so" ]; then mv $(BD)/_das2.cpython-*.so $@ ; fi
	

$(BD):
	@if [ ! -e "$(BD)" ]; then echo mkdir $(BD); \
        mkdir $(BD); chmod g+w $(BD); fi

$(BD)/_das2.so:src/*.c
	python$(PYVER) $(NOUSERSITE) buildfiles/du_setup.py build -g -b $(BD) -t $(BD) --build-lib=$(BD)
	@if [ ! -e "$(BD)/_das2.so" ]; then mv $(BD)/_das2.cpython-*.so $@ ; fi

# Run tests
test: verify
	env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) test/TestRead.py
	env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) test/TestDasTime.py
	env PYVER=$(PYVER) PYTHONPATH=$(PWD)/$(BD) test/das2_dastime_test1.sh $(BD)
	env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) test/TestCatalog.py
	env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) test/TestSortMinimal.py

verify:
	env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) scripts/das_verify test/ex05_waveform_extra.d3t
	env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) scripts/das_verify test/ex06_waveform_binary.d3b
	env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) scripts/das_verify test/ex08_dynaspec_namespace.d3t
	env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) scripts/das_verify test/ex12_sounder_xyz.d3t
	env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) scripts/das_verify test/ex13_object_annotation.d3t
	env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) scripts/das_verify test/ex14_object_tfcat.d3t
	env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) scripts/das_verify test/ex15_vector_frame.d3b
	env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) scripts/das_verify test/ex16_mag_grid_doc.d3x
	env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) scripts/das_verify test/ex96_yscan_multispec.d2t

# All the planet based test are broken right now
examples:
	env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) examples/ex01_source_queries.py
	env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) examples/ex03_cassini_rpws_multimode.py
	env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) examples/ex04_voyager_pws_query_by_time.py
	env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) examples/ex08_juno_waves_wfrm_to_cdf.py
	env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) examples/ex10_manual_datasets.py
	env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) examples/ex09_cassini_fce_ephem_ticks.py 2017-02-01
	env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) examples/ex11_catalog_listings.py
	env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) examples/ex02_galileo_pws_spectra.py

# TODO: Revive this
# env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) examples/ex05_mex_marsis_query_by_angle.py

#env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) examples/ex06_astro_lwa1_multiscale.py
#env PYTHONPATH=$(PWD)/$(BD) python$(PYVER) examples/ex07_cassini_rpws_query_opts.py

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

