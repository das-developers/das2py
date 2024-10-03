# Building das2py PYPI wheels

Here's a command line summary of what needs to be done by operating system.  Includes
das2C steps, since they are important.

## Windows

First get a compiler, see das2C project file
[install_visual_studio](https://github.com/das-developers/das2C/blob/master/notes/install_visual_studio.txt) for help on this error prone task.

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
