@echo off
setlocal
if not defined BLUEMSX_EXE set "BLUEMSX_EXE=C:\Emulator\blueMSX\blueMSX+.exe"
if not defined BLUEMSX_MACHINE set "BLUEMSX_MACHINE=NEON-V9968-TEST"
if not exist "%BLUEMSX_EXE%" goto missing
for %%I in ("%BLUEMSX_EXE%") do set "NEON_BLUE_ROOT=%%~dpI"
pushd "%NEON_BLUE_ROOT%"
"%BLUEMSX_EXE%" /rootdir "%NEON_BLUE_ROOT%." /machine "%BLUEMSX_MACHINE%" /rom1 "%~dp0outputs\NEON_REVENANT-HC-V9968-INTERNAL.rom" /romtype1 ascii8 /speed 100 /vdpspeed 100
popd
exit /b 0
:missing
echo Set BLUEMSX_EXE to your V9968-enabled blueMSX Plus executable.
pause
exit /b 1
