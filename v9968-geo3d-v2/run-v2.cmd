@echo off
setlocal
cd /d "%~dp0"
if not defined OPENMSX_EXE set "OPENMSX_EXE=openmsx.exe"
"%OPENMSX_EXE%" -machine Panasonic_FS-A1ST_V9968 -ext geo3d -cart "%~dp0outputs\NEON_REVENANT-HC-Geo3D-v2-test-v0.3.0.rom" -romtype ASCII16 -script "%~dp0interactive.tcl"
endlocal
