@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

echo.
echo ========================================
echo   🧠 EEG Paradox EDF Converter - GUI
echo   🚀 Auto-Install & Launch
echo ========================================
echo.

REM Check if we're running as administrator
net session >nul 2>&1
if !errorlevel! neq 0 (
    echo ⚠️  This script may need administrator privileges for Python installation
    echo.
)

echo 🔍 Checking system requirements...
echo.

REM Check if Python is available
python --version >nul 2>&1
if !errorlevel! neq 0 (
    echo ❌ Python not found! Installing Python...
    echo.
    
    REM Try to install Python using winget (Windows 10 1709+)
    winget --version >nul 2>&1
    if !errorlevel! equ 0 (
        echo 📦 Installing Python using winget...
        winget install Python.Python.3.11 --accept-source-agreements --accept-package-agreements
        if !errorlevel! equ 0 (
            echo ✅ Python installed successfully via winget
            echo 🔄 Refreshing PATH...
            call refreshenv.cmd 2>nul
        ) else (
            echo ⚠️  winget installation failed, trying alternative method...
        )
    )
    
    REM If winget failed or not available, try Chocolatey
    if !errorlevel! neq 0 (
        choco --version >nul 2>&1
        if !errorlevel! equ 0 (
            echo 📦 Installing Python using Chocolatey...
            choco install python311 --yes
            if !errorlevel! equ 0 (
                echo ✅ Python installed successfully via Chocolatey
                echo 🔄 Refreshing PATH...
                call refreshenv.cmd 2>nul
            ) else (
                echo ⚠️  Chocolatey installation failed
            )
        )
    )
    
    REM If both package managers failed, download directly
    if !errorlevel! neq 0 (
        echo 📥 Downloading Python directly from python.org...
        echo.
        echo Please download and install Python 3.11+ from:
        echo https://www.python.org/downloads/
        echo.
        echo Make sure to check "Add Python to PATH" during installation
        echo.
        pause
        echo.
        echo After installing Python, please run this script again.
        pause
        exit /b 1
    )
    
    REM Verify Python installation
    python --version >nul 2>&1
    if !errorlevel! neq 0 (
        echo ❌ Python installation verification failed
        echo.
        echo Please restart your computer and try again, or install Python manually.
        pause
        exit /b 1
    )
    
    echo ✅ Python installation verified
    echo.
) else (
    echo ✅ Python found
    python --version
    echo.
)

REM Check if pip is available
python -m pip --version >nul 2>&1
if !errorlevel! neq 0 (
    echo ❌ pip not found! Installing pip...
    python -m ensurepip --upgrade
    if !errorlevel! neq 0 (
        echo ❌ pip installation failed
        pause
        exit /b 1
    )
    echo ✅ pip installed successfully
    echo.
)

REM Check if PyQt5 is available
echo 🔍 Checking PyQt5...
python -c "import PyQt5" >nul 2>&1
if !errorlevel! neq 0 (
    echo ⚠️  PyQt5 not found! Installing PyQt5...
    echo.
    
    REM Try to install PyQt5
    python -m pip install PyQt5
    if !errorlevel! neq 0 (
        echo ❌ PyQt5 installation failed
        echo.
        echo Trying alternative installation method...
        python -m pip install --user PyQt5
        if !errorlevel! neq 0 (
            echo ❌ PyQt5 installation completely failed
            echo.
            echo Please try installing manually:
            echo pip install PyQt5
            echo.
            pause
            exit /b 1
        )
    )
    echo ✅ PyQt5 installed successfully
    echo.
) else (
    echo ✅ PyQt5 found
    echo.
)

REM Check if other required packages are available
echo 🔍 Checking other dependencies...
python -c "import mne, numpy" >nul 2>&1
if !errorlevel! neq 0 (
    echo ⚠️  Some dependencies missing! Installing requirements...
    echo.
    
    REM Install from requirements file if it exists
    if exist "%~dp0requirements_gui.txt" (
        echo 📦 Installing from requirements_gui.txt...
        python -m pip install -r "%~dp0requirements_gui.txt"
    ) else (
        echo 📦 Installing core dependencies...
        python -m pip install mne numpy
    )
    
    if !errorlevel! neq 0 (
        echo ❌ Dependency installation failed
        echo.
        echo Please try installing manually:
        echo pip install mne numpy
        echo.
        pause
        exit /b 1
    )
    echo ✅ Dependencies installed successfully
    echo.
) else (
    echo ✅ All dependencies found
    echo.
)

REM Check if converter module exists
if not exist "%~dp0edf_to_eeg_converter.py" (
    echo ❌ Converter module not found!
    echo.
    echo Please ensure edf_to_eeg_converter.py is in the same directory.
    echo.
    pause
    exit /b 1
)

REM Check if GUI module exists
if not exist "%~dp0gui_converter.py" (
    echo ❌ GUI module not found!
    echo.
    echo Please ensure gui_converter.py is in the same directory.
    echo.
    pause
    exit /b 1
)

echo 🎉 All requirements satisfied!
echo 🚀 Launching EEG Paradox GUI...
echo.

REM Launch the GUI
python "%~dp0gui_converter.py"

REM Check if GUI exited with error
if !errorlevel! neq 0 (
    echo.
    echo ❌ GUI exited with error code: !errorlevel!
    echo.
    echo This might indicate a runtime issue. Please check:
    echo - All dependencies are properly installed
    echo - Python version is 3.7 or higher
    echo - No antivirus blocking the application
    echo.
    pause
)

echo.
echo 👋 GUI closed. You can run this script again anytime!
pause
