@echo off
setlocal
if not defined OPENMSX_EXE set "OPENMSX_EXE=C:\Program Files\openMSX\openmsx.exe"
if not exist "%OPENMSX_EXE%" goto missing_emulator
if not exist "%~dp0outputs\NEON_REVENANT-HC-V9968.rom" goto missing_rom
if not exist "%~dp0work\emulator" mkdir "%~dp0work\emulator"
if not exist "%~dp0work\emulator" goto work_error
pushd "%~dp0work\emulator" || goto work_error
if not defined OPENMSX_SYSTEM_DATA for %%I in ("%OPENMSX_EXE%") do set "OPENMSX_SYSTEM_DATA=%%~dpIshare"
set "OPENMSX_HOME=./home"
if not exist "user\extensions" mkdir "user\extensions"
copy /Y "%~dp0config\HRA_V9968_OLD.xml" "user\extensions\HRA_V9968_HC.xml" >nul
set "OPENMSX_USER_DATA=./user"
if /I "%~1"=="--check" goto check
start "" "%OPENMSX_EXE%" -machine Panasonic_FS-A1ST -ext HRA_V9968_HC -cart "%~dp0outputs\NEON_REVENANT-HC-V9968.rom" -romtype ASCII8 -script "%~dp0tools\launch.tcl"
popd
exit /b 0
:check
"%OPENMSX_EXE%" -machine Panasonic_FS-A1ST -ext HRA_V9968_HC -cart "%~dp0outputs\NEON_REVENANT-HC-V9968.rom" -romtype ASCII8 -script "%~dp0tools\launcher-check.tcl"
set "DEMO_EXIT=%ERRORLEVEL%"
popd
exit /b %DEMO_EXIT%
:missing_emulator
echo V9968 openMSX was not found: "%OPENMSX_EXE%"
echo Set OPENMSX_EXE to your V9968-enabled openmsx.exe.
goto failed
:missing_rom
echo Demo ROM is missing. Keep this CMD beside the outputs and tools folders.
goto failed
:work_error
echo Cannot create or enter the local work folder.
:failed
if /I not "%~1"=="--check" pause
exit /b 1
