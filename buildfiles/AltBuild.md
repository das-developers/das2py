# Alternate build instructions for das2py

In various incarnations this module has been run on Windows, Linux & MacOS
over the last decade and it still continues to support python2 for older
projects.

## Building Wheels on Windows

First get a compiler.  **Stop** reading here and go follow the instructions
in the das2C project file
[install_visual_studio](https://github.com/das-developers/das2C/blob/master/notes/install_visual_studio.txt)
for help on this error prone task.
When you have a working compiler, linker, etc.  Come back.

```batch
rem clone repos

git clone git@github.com:microsoft/vcpkg.git
git clone git@github.com:das-developers/das2C.git
git clone git@github.com:das-developers/das2py.git

rem Initialize visual studio tools
vcvarsall.bat x64

rem build vcpkg
cd vcpkg
.\boostrap-vcpkg.bat -disableMetrics
.\vcpk install openssl fftw3 expat pthreads --trilet x64-windows-static
cd ..\

rem build das2C
cd das2C
git checkout tags/v3.0-pre1
set VCPKG_ROOT=C:\Users\you\git\vcpkg # Adjust as needed
set LIBRARY_INC=%VCPKG_ROOT%\installed\x64-windows-static\include
set LIBRARY_LIB=%VCPKG_ROOT%\installed\x64-windows-static\lib

nmake.exe /nologo /f buildfiles\Windows.mak build
nmake.exe /nologo /f buildfiles\Windows.mak run_test
cd ..\

rem build das2py (reuses VCPKG_ROOT setting from above)
cd das2py
git checkout tags/v3.0-pre1  # Or stay on main if testing
python -m pip install numpy
python -m pip install wheel
python -m pip install --upgrade build
python -m pip install --upgrade twain
set DAS2C_LIBDIR=..\das2C\build.windows
set DAS2C_INCDIR=..\das2C
python -m build -w
cd ..\

rem test das2py
python -m pip install matplotlib
python -m pip install .\das2py\dist\das2py-2.3.0-cp310-cp310-win_amd64.whl

python das2py\examples\ex09_cassini_fce_ephem_ticks.py 2017-09-14
rem OTHER TESTS HERE

rem upload to pypi
cd das2py
python -m twine upload dist/*
username: __token__
password: (the 170+ character token value that you saved somewhere)
```

## Linux RPMs (outdated)

Wheels and virtual environments are recommended, but if you want to build packages
for the system python RPM instructions are provided here.  Note that these are
quite old and could use a refresh.

First setup your build environment, including an rpmbuild tree in your home 
directory:
```bash
$ yum install gcc rpm-build rpm-devel rpmlint make python bash coreutils diffutils patch rpmdevtools
$ rpmdev-setuptree
```

Copy the included spec and patch files to locations within your rpmbuild tree.  The
destdir patch is needed because version `v2.3-pre4` did not have the DESTDIR macro
and thus the install targets were not relocatable for two-stage installs.  Future releases (aka v2.3-pre5, etc.) will not need this file.
```bash
cp makefiles/rpm/das2py.spec $HOME/rpmbuild/SPECS/
```

Install dependencies as usual, but also include the das2C rpms:
```bash
yum install expat-devel fftw-devel openssl-devel
yum localinstall das2C-2.3~pre4-1.el7.x86_64.rpm
yum localinstall das2C-devel-2.3~pre4-1.el7.x86_64.rpm  # build dependency
```

In general the das2C version numbers track with the das2py version numbers, but
not necessarily.  The `das2py.spec` file should handle dependency tracking and will
complain if the version of das2C you installed won't work for some reason.

Build the RPMs and the SRPM:
```bash
$ rpmbuild -bs $HOME/rpmbuild/SPECS/das2py.spec  # Source RPM
$ rpmbuild -bb $HOME/rpmbuild/SPECS/das2py.spec  # lib, devel & debug RPMs
```

Install the binary RPMs
```bash
$ sudo yum localinstall $HOME/rpmbuild/RPMS/x86_64/das2py*.rpm
```

A basic test:
```bash
$ python3 /usr/lib64/python3.6/site-packages/das2/examples/ex01_source_queries.py
```

Test das2 federated catalog node walking:
```bash
$ python3 /usr/lib64/python3.6/site-packages/das2/examples/ex11_catalog_listings.py
```

Test plot creation (requires matplotlib):
```bash
# Getting matplotlib (CentOS 7)
$ sudo yum install libjpeg-turbo-devel 
$ pip3.6 install matplotlib --user      # CentOS 7

# Getting matplotlib (CentOS 8)
$ sudo yum install python3-matplotlib   # CentOS 8

# Now make a plot file and show it
$ python3 /usr/lib64/python3.6/site-packages/das2/examples/ex02_galileo_pws_spectra.py
$ eog ex02_galileo_pws_spectra.png
```

## Building the Python2 Interpreter from Source

Regardless of anyone's ideology, it is a fact of life in Space Physics
that many old programs exist which are useful but for which there are no
maintenence resources (i.e. time/money/talent). This library depends on
numpy 1.11 or higher, but does not need python 3. If you have to run older,
unported software that requires python 2, try building the interpreter
from sources.  It's relatively straightforward on Linux and MacOS.  

### Building Python2 from source on Linux

*TODO: Add notes from Juno/Waves support here*

### Building Python2 from source on MacOS

#### Get a compiler
You will need a C compiler.  To see if one is already installed open a terminal
and run:
```bash
$ cc --version
```
If this produces nothing, then you'll need to install the C compiler first.  On
MacOS the standard compiler is supplied by the xcode package.  Run the command
```bash
xcode-select --install
```
to install it if needed.

#### Select an install location
There a few places you don't want to install your legacy version of python.
*Don't* put it under `/usr/local` as [homebrew](https://brew.sh/) uses that
location.  *Don't* put it in `/usr` as the system python uses that location.
In these notes we are supporting old Juno Mission project code on MacOS.
The top level project directory will be:

```bash
/project/juno/opt/darwin13
```

everything will be installed relative to that location.  Choose a suitable 
replacement directory for your project.  Furthermore we are on a shared NFS
system so OS specific binaries must be in a different path from general items.
Since these notes were generated on a Mac OS 10.13 system, I'll use the name
`darwin13` to denote host OS specific items.

```bash
$ export PY_PRE=/project/juno/opt/darwin13
```

### Build the Interpreter

```bash
$ cd $HOME
$ curl https://www.python.org/ftp/python/2.7.18/Python-2.7.18.tgz > Python-2.7.18.tgz
$ mkdir tmp && cd tmp
$ tar -xvzf ../Python-2.7.18.tgz
$ cd Python-2.7.18

$ ./configure --prefix=$PY_PRE --enable-ipv6 --enable-shared \
   --with-ensurepip=install LDFLAGS="-W1,-rpath=$PYTHON_PREFIX/lib"

$ make
$ make install
```
Make sure at least something works.  Run make test, you don't have to wait
for the entire test battery to finish, though it's a good idea.

```bash
$ make test
```
Finally symlink the python binary to some location on your project path.

```bash
$ cd /project/juno/bin/darwin13
$ ln -s /project/juno/opt/darwin13/bin/python2.7
$ ln -s /project/juno/opt/darwin13/bin/python2
$ ln -s /project/juno/opt/darwin13/bin/python
```

### Building numpy 1.17

First we'll need the prerequisites:
```bash
$ brew install fftw
$ brew install 
```

Next get the source code for the last version of NumPy to support python 2.7.
```bash
$ cd $HOME
$ cd tmp
# curl doesn't work for github, download via browser or issue:
$ wget https://github.com/numpy/numpy/releases/download/v1.16.6/numpy-1.16.6.tar.gz
$ tar -xvzf numpy-1.16.6.tar.gz
$ cd numpy-1.16.6.tar.gz
```

Make sure that your getting the version of python that was built above. This is
just a sanity check to make sure you're not running `/usr/bin/python`,
`/usr/local/bin/python` or some other system location.  

```bash
$ which python
/project/juno/bin/darwin13/python  # Specific example, yours will be different
```

Now build/install numpy 1.17.
```bash
$ python setup.py build
$ python setup.py install
```
