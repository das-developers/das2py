from setuptools import Extension, setup
import os
# import numpy  # <-- apparently a big no-no now.
import sys

# Assume das2C is in a parallel directory and that N_ARCH=/ if no
# other option is set.
sCLibDir = os.getenv("DAS2C_LIBDIR")
if not sCLibDir:
	sCLibDir = "../das2C/build."
	
sCHdrDir = os.getenv("DAS2C_INCDIR")
if not sCHdrDir:
	sCHdrDir = "../das2C"

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

# Hopefully the build system knows how to add numpy headers back in
#if sCHdrDir: lInc = [sCHdrDir, numpy.get_include()]
#else: lInc = [numpy.get_include()]

if sCHdrDir: lInc = [sCHdrDir, "./src"]
else: lInc = ["./src"]

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

	# A macOS hack
	lInc.append(
		"/opt/homebrew/lib/python%d.%d/site-packages/numpy/core/include"%(
			sys.version_info.major, sys.version_info.minor
		)
	)

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
	author="C Piker",
	author_email="das-developers@uiowa.edu",
	url="https://das2.org/das2py",
	scripts=['scripts/das_verify'],
	include_package_data=True,
	#package_data={'das2':['xsd/*.xsd']},
	install_requires=['lxml','numpy']
)
