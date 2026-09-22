@echo off
setlocal
cd /d "%~dp0"
if defined PYTHON_EXE (
 "%PYTHON_EXE%" tools\build.py
 exit /b
)
py -3 tools\build.py
