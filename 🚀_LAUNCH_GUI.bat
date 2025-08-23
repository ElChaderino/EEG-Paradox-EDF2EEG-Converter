@echo off
REM 🚀 EEG Paradox EDF Converter - One-Click GUI Launcher
REM This file will automatically install Python and dependencies, then launch the GUI

echo 🧠 EEG Paradox EDF Converter
echo 🚀 One-Click GUI Launcher
echo.

REM Call the auto-installer launcher
call "%~dp0Launch_GUI_Auto_Install.bat"

REM If we get here, the GUI has closed
echo.
echo 👋 Thank you for using EEG Paradox!
pause
