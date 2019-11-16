
LIBDAS=das2.3

# Project definitions #########################################################
BD=build.$(N_ARCH)

SRC=_das2.c
PYSRC=util.py __init__.py dastime.py toml.py source.py dataset.py \
 container.py pkt.py mpl.py auth.py node.py streamsrc.py cdf.py

BUILT_PYSRC=$(patsubst %,$(BD)/das2/%,$(PYSRC))
INSTALLED_PYSRC=$(patsubst %.py,$(INST_HOST_LIB)/das2/%.py,$(PYSRC))

# Pattern Rules #############################################################

$(INST_HOST_LIB)/das2/%.py:$(BD)/das2/%.py
	install -d -m 775 $(INST_HOST_LIB)/das2
	install -m 664 $< $(INST_HOST_LIB)/das2

# Explicit Rules #############################################################

.PHONY: test

build: $(BD) $(BD)/_das2.so $(C_BUILD_DIR)/lib$(LIBDAS).a

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


# Install purelib and extensions (python setup.py is so annoyingly
# restrictive that we'll just do this ourselves)
install:$(INST_EXT_LIB)/_das2.so  $(INSTALLED_PYSRC)

doc:
	cd sphinx_doc && $(MAKE) html


$(INST_EXT_LIB)/_das2.so:$(BD)/_das2.so
	install -d -m 775 $(INST_EXT_LIB)
	install -m 775 $< $(INST_EXT_LIB)

clean:
	if [ -d "$(BD)" ]; then rm -r $(BD); fi

distclean:
	if [ -d "$(BD)" ]; then rm -r $(BD); fi

