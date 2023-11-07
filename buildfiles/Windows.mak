# Building python lib under anaconda on windows


LIBDAS=libdas2.3.lib

BD=build.windows

SRC=src\_das2.c

build: $(BD) $(BD)\_das2.pyd

$(BD):
	if not exist "$(BD)" mkdir "$(BD)"

$(BD)\_das2.pyd:$(SRC)
	python buildfiles\du_setup.py build -b $(BD) -t $(BD) --build-lib=$(BD)
	if exist $@ del $@
	copy $(BD)\_das2*.pyd $@

	
# to make debug version...
#	python setup.py build -g -b $(BD) -t $(BD) --build-lib=$(BD)

# Run tests
run_test:
	set PYTHONPATH=$(MAKEDIR)\$(BD)
	python test\TestRead.py
	python test\TestDasTime.py
	python test\TestCatalog.py
	python test\TestSortMinimal.py

install:
	python setup.py install --prefix=$(PREFIX)

	
	