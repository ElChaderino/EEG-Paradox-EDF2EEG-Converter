@echo off
REM EEG Paradox WinEEG Converter Launcher
REM ====================================

echo.
echo  ########     ###    ########     ###    ########   #######  ##     ##
echo  ##     ##   ## ##   ##     ##   ## ##   ##     ## ##     ## ##     ##
echo  ##     ##  ##   ##  ##     ##  ##   ##  ##     ## ##     ##  ##   ## 
echo  ########  ##     ## ########  ##     ## ##     ## ##     ##   ## ##  
echo  ##        ######### ##   ##   ######### ##     ## ##     ##    ###   
echo  ##        ##     ## ##    ##  ##     ## ########   #######     ##
echo.
echo  EEG Paradox WinEEG Converter v1.0
echo  Professional EDF to WinEEG Conversion
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python not found! Please install Python 3.7+ and try again.
    echo.
    echo Download Python from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python found
echo.

REM Check if required packages are installed
echo 🔍 Checking dependencies...
python -c "import numpy, mne, tkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  Installing required packages...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ❌ Failed to install dependencies!
        pause
        exit /b 1
    )
)

echo ✅ Dependencies ready
echo.

REM Launch the GUI
echo 🚀 Launching EEG Paradox Converter...
echo.
python EEG_Paradox_Converter_v2.py

REM Keep window open if there was an error
if %errorlevel% neq 0 (
    echo.
    echo ❌ Application exited with error code %errorlevel%
    pause
)
