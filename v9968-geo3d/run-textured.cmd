@echo off
setlocal
cd /d "%~dp0"
if not defined OPENMSX_EXE set "OPENMSX_EXE=openmsx.exe"
if not defined OPENMSX_MACHINE set "OPENMSX_MACHINE=Panasonic_FS-A1ST_V9968"
"%OPENMSX_EXE%" -machine "%OPENMSX_MACHINE%" -ext geo3d -cart "%~dp0outputs\NEON_REVENANT-HC-Geo3D-textured-v0.1.0.rom" -romtype ASCII16 -script "%~dp0interactive.tcl"
