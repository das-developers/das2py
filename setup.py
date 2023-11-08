from setuptools import Extension, setup
import os
import numpy
import sys

sCLibDir = os.getenv("DAS2C_LIBDIR")
sCHdrDir = os.getenv("DAS2C_INCDIR")

print('(setup.py) DAS2C_LIBDIR = %s'%sCLibDir)
print('(setup.py) DAS2C_INCDIR = %s'%sCHdrDir)

# Under conda we can dependend on shared objects, under system builds we can't
if os.getenv("CONDA_PREFIX"):
	bLinkStatic=False
else:
	bLinkStatic=True

lDefs = []

if sCLibDir: lLibDirs = [sCLibDir]
else: lLibDirs = []

if sCHdrDir: lInc = [sCHdrDir, numpy.get_include()]
else: lInc = [numpy.get_include()]

lSrc = ["src/_das2.c"]

if sys.platform == 'win32':
	print("setup.py: Using Headers from %s"%lInc)
	print("setup.py: Using Libs from %s"%lLibDirs)
	ext = Extension(
		"_das2"
		,sources=lSrc
		,include_dirs=lInc
		,define_macros=lDefs
		,library_dirs=lLibDirs
		,libraries=[
			"libdas2.3", "fftw3", "expat", "libssl", "libcrypto",
			"zlib", "pthreadVC3", "ws2_32"
		]
		,extra_objects=['%s/libdas2.3.a'%sCLibDir]
	)
elif sys.platform == 'darwin':

	if bLinkStatic:
		lExObjs = [
			'%s/libdas2.3.a'%sCLibDir,
			'/opt/homebrew/opt/openssl/lib/libssl.a',
			'/opt/homebrew/opt/openssl/lib/libcrypto.a',
			'/opt/homebrew/lib/libfftw3.a'
		]
		lLibs = ["expat", "z"]
	else:
		lExObjs = ['%s/libdas2.3.a'%sCLibDir]
		lLibs   = ["fftw3", "expat", "ssl", "crypto", "z"]


	ext = Extension(
		"_das2", sources=lSrc 
		,include_dirs=lInc
		,define_macros=lDefs
		,library_dirs=lLibDirs
		,libraries=lLibs
		,extra_compile_args=['-std=c99', '-ggdb', '-O0']
		,extra_objects=lExObjs
		,extra_link_args=['-Wl,-no_compact_unwind']
	)	
else:
	# Linux, also works for anaconda on macos
	ext = Extension(
		"_das2", sources=lSrc
		,include_dirs=lInc
		,define_macros=lDefs
		,library_dirs=lLibDirs
		,libraries=["fftw3", "expat", "ssl", "crypto", "z"]
		,extra_compile_args=['-std=c99', '-ggdb', '-O0']
		,extra_objects=['%s/libdas2.3.a'%sCLibDir]
	)

setup(
	name="das2py",
	version="2.3.0",
	ext_modules=[ext],
	packages=['das2', 'das2.pycdf', 'das2.xsd'],
	author="Chris Piker",
	author_email="das-developers@uiowa.edu",
	url="https://das2.org/das2py",
	scripts=['scripts/das_verify'],
	include_package_data=True,
	#package_data={'das2':['xsd/*.xsd']},
	install_requires=['lxml','numpy']
)