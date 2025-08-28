# EEG Paradox WinEEG Converter - Setup Guide

## 🚀 Quick Setup (Recommended)

**Just double-click:** `Launch_EEG_Paradox_Converter.bat`

This will:
- ✅ Check Python installation
- ✅ Install required packages automatically
- ✅ Launch the GUI application

## 📋 Manual Setup

### 1. Prerequisites
- **Python 3.7+** - Download from [python.org](https://www.python.org/downloads/)
- **Windows OS** (for WinEEG compatibility)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Launch Application
```bash
python EEG_Paradox_Converter.py
```

## 🔧 Verification

After setup, verify everything works:

1. **Launch the GUI** - You should see the dark-themed interface
2. **Load a test EDF** - Browse or drag & drop an EDF file
3. **Check templates** - Should show "✅ Using [template type]" 
4. **Convert a file** - Try converting a small EDF file

## 📁 File Structure Check

Ensure you have these files:
```
EEG Paradox WinEEG Converter/
├── ✅ EEG_Paradox_Converter.py
├── ✅ converter_core.py
├── ✅ requirements.txt
├── ✅ Launch_EEG_Paradox_Converter.bat
└── templates/
    ├── ✅ LB_EO_EEG.EEG
    └── ✅ LB_EO_EEG_EXTENDED_30min.EEG
```

## ⚠️ Troubleshooting

**"Python not found"**
- Install Python from [python.org](https://www.python.org/downloads/)
- Make sure to check "Add Python to PATH" during installation

**"Module not found"**
- Run: `pip install -r requirements.txt`
- If using conda: `conda install numpy mne`

**"Template not found"**
- Verify `templates/` folder contains the .EEG files
- Re-extract the complete package if files are missing

**"No module named tkinter"**
- On Ubuntu/Debian: `sudo apt-get install python3-tk`
- On other systems: tkinter should be included with Python

## 🎯 Ready to Use!

Once setup is complete:
1. **Launch:** Double-click `Launch_EEG_Paradox_Converter.bat`
2. **Load:** Drag & drop your EDF file
3. **Convert:** Click "Convert to WinEEG"
4. **Open:** Use the result in WinEEG (data starts at 5+ seconds)

## 📞 Support

If you encounter issues:
1. Check this setup guide
2. Verify all files are present
3. Ensure Python 3.7+ is installed
4. Check that your EDF has exactly 19 channels
