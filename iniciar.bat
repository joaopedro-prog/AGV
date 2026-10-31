@echo off
setlocal
cd /d "%~dp0scripts"
call menu_agv.bat
if errorlevel 1 pause
