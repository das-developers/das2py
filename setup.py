import os
import sys
import os.path
from distutils.core import setup, Extension
import numpy

sCLibDir = os.getenv("DAS2C_LIBDIR")
sCHdrDir = os.getenv("DAS2C_INCDIR")
	
lDefs = []

if sCLibDir: lLibDirs = [sCLibDir]
else: lLibDirs = []

if sCHdrDir: lInc = [sCHdrDir, numpy.get_include()]
else: lInc = [numpy.get_include()]

lSrc = ["src/_das2.c"]

if sys.platform.lower().startswith('sunos'):
	ext = Extension(
		"_das2", sources=lSrc, include_dirs=lInc, define_macros=lDefs
		,library_dirs=lLibDirs, libraries=["das2.3","fftw3", "expat", 
		                                   "ssl", "crypto", "z"]
		,extra_compile_args=["-xc99"]
	)
elif sys.platform == 'win32':
	print("setup.py: Using Headers from %s"%lInc)
	print("setup.py: Using Libs from %s"%lLibDirs)
	ext = Extension(
		"_das2", sources=lSrc, include_dirs=lInc, define_macros=lDefs
		,library_dirs=lLibDirs, 
        libraries=[
            "libdas2.3", "fftw3", "expat", "libssl", "libcrypto",
            "zlib", "pthreadVC3", "ws2_32"
		]
        ,extra_objects=['%s/libdas2.3.a'%sCLibDir]
	)

else:
	ext = Extension(
		"_das2", sources=lSrc, include_dirs=lInc, define_macros=lDefs
		,library_dirs=lLibDirs
        ,libraries=["fftw3", "expat", "ssl", "crypto", "z"]
		,extra_compile_args=['-std=c99', '-ggdb', '-O0']
        ,extra_objects=['%s/libdas2.3.a'%sCLibDir]
	)


setup(description="Das2 extensions for python",
	name="das2py",
	version="2.3.2",
	ext_modules=[ ext ],
	packages=['das2', 'das2.pycdf'],
	author="Chris Piker",
	author_email="chris-piker@uiowa.edu",
	url="https://das2.org/das2py"
)

