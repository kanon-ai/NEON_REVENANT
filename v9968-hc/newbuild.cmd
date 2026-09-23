@echo off
setlocal
cd /d "%~dp0"
if defined PYTHON_EXE goto configured
py -3 tools\build.py --target=external
if errorlevel 1 exit /b 1
py -3 tools\build.py --target=internal
exit /b %ERRORLEVEL%
:configured
"%PYTHON_EXE%" tools\build.py --target=external
if errorlevel 1 exit /b 1
"%PYTHON_EXE%" tools\build.py --target=internal
exit /b %ERRORLEVEL%
