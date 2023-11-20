from setuptools import Extension, setup
import os
from os.path import dirname as dname
from os.path import join as pjoin
# import numpy  # <-- forced to be hacky with custom build_ext
from setuptools.command.build_ext import build_ext as _build_ext
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

	if bLinkStatic:  # currently a synonym for not-conda 
		# A windows hack, since we're not allowed to import numpy
		# inside setup.py.  Any help on gitting rid of this hack
		# would be highly appreciated
		#sPyDir = dname(sys.executable)
		#lInc.append(
		#	pjoin(sPyDir, "lib", "site-packages", "numpy", "core", "include")
		#)

		sVcRoot = os.getenv("VCPKG_ROOT")
		if sVcRoot:
			sVcLibDir = pjoin(sVcRoot, "installed","x64-windows-static","lib")
			sVcIncDir = pjoin(sVcRoot, "installed","x64-windows-static","include")
		else:
			# With no other input, assume it's next door
			sVcLibDir = "..\\vcpkg\\installed\\x64-windows-static\\lib"
			sVcIncDir = "..\\vcpkg\\installed\\x64-windows-static\\include"

		print('(setup.py) VCPKG_LIBDIR = %s'%sVcLibDir)

		lLibDirs.append( sVcLibDir )
		lInc.append( sVcIncDir )
		lExObjs = ['%s/libdas2.3.lib'%sCLibDir]
		lLibs = [ 
			"fftw3", "libexpatMD", "libssl", "libcrypto", "Advapi32",
			"User32", "Crypt32", "zlib", "pthreadVC3", "ws2_32"
		]
	else:
		# Anaconda will setup the lib directories for us, but still
		# link das2C statically.  Also anaconda and vcpkg use different
		# names for expaxt library
		lExObjs = ['%s/libdas2.3.lib'%sCLibDir]
		lLibs = [ 
			"fftw3", "expat", "libssl", "libcrypto",
			"zlib", "pthreadVC3", "ws2_32"
		]

	print("setup.py: Using Headers from %s"%lInc)
	print("setup.py: Using Libs from %s"%lLibDirs)

	ext = Extension(
		"_das2"
		,sources=lSrc
		,include_dirs=lInc
		,define_macros=lDefs
		,library_dirs=lLibDirs
		,libraries=lLibs
		,extra_objects=lExObjs
	)
elif sys.platform == 'darwin':

	# A macOS hack
	#lInc.append(
	#	"/opt/homebrew/lib/python%d.%d/site-packages/numpy/core/include"%(
	#		sys.version_info.major, sys.version_info.minor
	#	)
	#)

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

# ... because import numpy at top level doesn't work anymore (yay)
# Solution from:
# https://stackoverflow.com/questions/54117786/add-numpy-get-include-argument-to-setuptools-without-preinstalled-numpy
class build_ext(_build_ext):
	def finalize_options(self):
		_build_ext.finalize_options(self)
		# Prevent numpy from thinking it is still in its setup process:
		__builtins__.__NUMPY_SETUP__ = False
		import numpy
		self.include_dirs.append(numpy.get_include())

setup(
	cmdclass={'build_ext':build_ext},
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
