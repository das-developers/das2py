:: set PYVER=%PY_VER%
:: set N_ARCH=/

set DAS2C_LIBDIR=%BUILD_PREFIX%\lib
set DAS2C_INCDIR=%BUILD_PREFIX%\include

%PYTHON% setup.py build
%PYTHON% setup.py install

:: nmake.exe /nologo /f makefiles\Windows.mak clean
:: 
:: if %ERRORLEVEL% NEQ 0 (
:: 	EXIT /B 1
:: )
:: 
:: nmake.exe /nologo /f makefiles\Windows.mak build
:: 
:: if %ERRORLEVEL% NEQ 0 (
:: 	EXIT /B 2
:: )
:: 
:: nmake.exe /nologo /f makefiles\Windows.mak run_test
:: 
:: if %ERRORLEVEL% NEQ 0 (
:: 	EXIT /B 3
:: )
:: 
:: nmake.exe /nologo /f makefiles\Windows.mak install
:: 
:: if %ERRORLEVEL% NEQ 0 (
:: 	EXIT /B 4
:: )
:: 
:: nmake.exe /nologo /f makefiles\Windows.mak pylib
:: 
:: if %ERRORLEVEL% NEQ 0 (
:: 	EXIT /B 5
:: )
:: 
:: 
:: nmake.exe /nologo /f makefiles\Windows.mak pylib_test
:: 
:: if %ERRORLEVEL% NEQ 0 (
:: 	EXIT /B 6
:: )
:: 
:: nmake.exe /nologo /f makefiles\Windows.mak pylib_install
:: 
:: if %ERRORLEVEL% NEQ 0 (
:: 	EXIT /B 7
:: )
