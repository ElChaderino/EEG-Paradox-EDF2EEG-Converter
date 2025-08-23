🧠 EEG Paradox EDF Converter v2.9.1

Universal EDF to EEG Format Converter with GUI (Prototype Release)

⚠️ Disclaimer – Test Tool, Not Final

This project is provided as a prototype / research utility.
It is not FDA-approved, CE-marked, or validated for clinical decision-making.

Expect bugs, incomplete format coverage, and edge-case failures.

Outputs should be cross-checked manually before use in any analysis or clinical setting.

This tool is intended for research, testing, and educational purposes only.

👉 Treat this as a proof-of-concept for format conversion and validation — not a finished medical product.

🚀 Quick Start - One Click Installation
For New Users (RECOMMENDED):

Simply double-click:

🚀_LAUNCH_GUI.bat


The launcher will automatically:

✅ Install Python (if needed)

✅ Install all dependencies (PyQt5, MNE, NumPy, etc.)

✅ Launch the EEG Paradox converter GUI

✅ Handle setup automatically

📁 Available Launchers


🎯 What This Tool Does

EEG Paradox EDF Converter converts EDF (European Data Format) files into a range of EEG software formats for research and compatibility testing.

Supported Input Formats:

✅ EDF - European Data Format

✅ BDF - BioSemi Data Format

✅ EDF+ - Extended EDF

Supported Output Formats:
Format	Extension	Software	Use Case
BrainVision	.vhdr/.vmrk	BrainVision Analyzer, EEGLAB	Research software
WinEEG	.erd/.evt	Original WinEEG	Legacy compatibility
Neuroscan	.hdr	Neuroscan systems	Research/clinical
EEGLAB	.set	MATLAB EEGLAB	Academic use
Nicolet	.hdr	Nihon Kohden	Sleep/EEG
Compumedics	.hdr	Compumedics	Sleep medicine
🔍 Advanced Features (Prototype)

Automatic Calibration Detection
Identifies scaling issues, weak signals, and asymmetric problems.

Validation Reports ("Gunkelman-Grade")
Cross-checks sampling rates, metadata consistency, and generates audit-style notes.

Multi-Channel Support
Preserves names/order, supports different resolutions per channel.

⚠️ These are experimental implementations — results should be treated as guidance only and verified independently.
---

## 🔧 **How the Auto-Installation Works**

### **Python Installation Methods (in order of preference):**

1. **winget** (Windows 10 1709+) - Fastest, most reliable
2. **Chocolatey** - Alternative package manager  
3. **Manual download** - Direct from python.org if package managers fail

### **Dependency Installation:**

1. **pip** - Python package installer
2. **PyQt5** - GUI framework
3. **MNE & NumPy** - EEG data processing
4. **requirements_gui.txt** - All dependencies in one file

---

## 📋 **System Requirements**

### **Minimum:**
- Windows 7 or later
- 2GB RAM
- 500MB free disk space
- Internet connection (for first-time installation)

### **Recommended:**
- Windows 10/11
- 4GB+ RAM
- 1GB+ free disk space
- Administrator privileges (for system-wide Python installation)

---

## 🎨 **Using the EEG Paradox Converter**

### **Step 1: Launch the Tool**
- Double-click `🚀_LAUNCH_GUI.bat`
- Wait for auto-installation to complete
- GUI opens automatically

### **Step 2: Load EDF File**
**Option A: Drag & Drop**
- Drag your `.edf` file onto the GUI
- File loads automatically

**Option B: Browse**
- Click "Browse" button
- Navigate to your `.edf` file
- Select and click "Open"

### **Step 3: Choose Output Format**
Select from the dropdown:
- **BrainVision** - Most compatible, modern software
- **WinEEG** - Legacy systems, original WinEEG
- **Neuroscan** - Clinical EEG systems
- **EEGLAB** - MATLAB-based analysis
- **Nicolet** - Sleep/EEG systems
- **Compumedics** - Sleep medicine
- **Both** - BrainVision + WinEEG for universal compatibility

### **Step 4: Set Output Directory**
- Click "Output Directory" button
- Choose where to save converted files
- Or use default location

### **Step 5: Convert**
- Click "Convert" button
- Watch progress bar
- Conversion completes automatically

---

## 📊 **What Gets Created**

### **BrainVision Format:**
```
output_folder/
├── your_file.vhdr    ← Header file
├── your_file.eeg     ← Data file  
└── your_file.vmrk    ← Marker file
```

### **WinEEG Format:**
```
output_folder/
├── your_file.erd     ← Header file
├── your_file.eeg     ← Data file
└── your_file.evt     ← Events file
```

### **Other Formats:**
```
output_folder/
├── your_file.hdr     ← Header file
├── your_file.eeg     ← Data file
└── your_file.set     ← EEGLAB file (if applicable)
```

---

## 🔍 **Advanced Features**

### **Automatic Calibration Detection:**
- ✅ Detects 10x power problems
- ✅ Identifies weak signals
- ✅ Corrects asymmetric scaling
- ✅ Optimizes resolution automatically

### **Gunkelman-Grade Validation:**
- ✅ Cross-checks metadata consistency
- ✅ Validates signal integrity
- ✅ Ensures sampling rate accuracy
- ✅ Generates audit reports

### **Multi-Channel Support:**
- ✅ Handles any number of channels
- ✅ Preserves channel names
- ✅ Maintains channel order
- ✅ Supports different resolutions per channel

---

## 🚨 **Troubleshooting**

### **Common Issues:**

#### **"Python installation failed"**
- **Solution**: Run launcher as Administrator
- **Alternative**: Install Python manually from python.org

#### **"PyQt5 installation failed"**
- **Solution**: Launcher will try alternative methods
- **Fallback**: Manual installation with `pip install PyQt5`

#### **"Dependencies missing"**
- **Solution**: Launcher will install all required packages
- **Check**: Ensure internet connection is working

#### **"GUI won't start"**
- **Solution**: Check if antivirus is blocking the application
- **Alternative**: Run from command line to see error messages

### **Advanced Troubleshooting:**

#### **Skip Python Check:**
```powershell
.\Launch_GUI_Auto_Install.ps1 -SkipPython
```

#### **Skip Dependency Check:**
```powershell
.\Launch_GUI_Auto_Install.ps1 -SkipDependencies
```

#### **Force Reinstall:**
```powershell
.\Launch_GUI_Auto_Install.ps1 -Force
```

---

## 📱 **Desktop Shortcut Setup**

### **Create Desktop Shortcut:**
1. Run `Create_Desktop_Shortcut.bat`
2. Shortcut appears on desktop
3. Double-click shortcut anytime
4. No need to navigate to folder

### **Shortcut Features:**
- Custom icon (EP.png)
- Proper working directory
- Descriptive tooltip
- Easy access from anywhere

---

## 🔒 **Security Considerations**

### **What Gets Installed:**
- **Python 3.11** - Official Python distribution
- **PyQt5** - Qt framework for GUI
- **MNE & NumPy** - Scientific computing libraries

### **Installation Sources:**
- **winget** - Microsoft's official package manager
- **Chocolatey** - Community package manager
- **pip** - Python's official package installer

### **Permissions Required:**
- **User mode**: Can install to user directory
- **Admin mode**: Can install system-wide (recommended)

---

## 📞 **Support & Help**

### **If Auto-Installation Fails:**
1. **Check the error messages** - They provide specific guidance
2. **Try running as Administrator** - Right-click → "Run as Administrator"
3. **Check internet connection** - Required for package downloads
4. **Disable antivirus temporarily** - Some security software blocks installations

### **Manual Installation Fallback:**
If all else fails, you can:
1. Download Python from python.org
2. Install PyQt5 manually: `pip install PyQt5`
3. Install other dependencies: `pip install mne numpy`
4. Run the GUI directly: `python gui_converter.py`

---

## 🎉 **Success Indicators**

### **You'll know it's working when you see:**
```
✅ Python found
✅ PyQt5 found  
✅ All dependencies found
🎉 All requirements satisfied!
🚀 Launching EEG Paradox GUI...
```

### **The GUI will then:**
- Open with the cyberpunk dark theme
- Show the drag-and-drop interface
- Be ready to convert EDF files immediately

---

## 📚 **Additional Documentation**

### **Build Executables:**
- **🚀_BUILD_EXE.bat** - Create standalone .exe files
- **AUTO_PY_TO_EXE_CONFIG.md** - Detailed build configuration
- **EXECUTABLE_BUILD_SUMMARY.md** - Build process overview

### **Format Support:**
- **SUPPORTED_EEG_FORMATS.md** - Complete format documentation
- **AUTO_INSTALLER_LAUNCHERS_README.md** - Launcher details
- **LAUNCHER_OPTIONS_SUMMARY.md** - All launcher options

---

🚀 Ready to Convert?

Just double-click 🚀_LAUNCH_GUI.bat and start exploring.

This project is designed to:

🧠 Demonstrate universal format conversion

🚀 Showcase an automated GUI approach

🎨 Provide a usable but experimental research tool

✅ Highlight validation logic that clinicians/researchers can review

Perfect for:

Researchers & students – Exploring EEG format conversion

Clinicians (non-clinical use) – Testing compatibility in lab setups

Technicians – Bridging data formats across systems

Developers – Extending EEG conversion pipelines

---

## 🎯 **Quick Reference**

| Action | Method |
|--------|--------|
| **Install & Launch** | Double-click `🚀_LAUNCH_GUI.bat` |
| **Load File** | Drag & drop `.edf` file |
| **Choose Format** | Select from dropdown menu |
| **Convert** | Click "Convert" button |
| **Find Output** | Check selected output directory |
| **Create Shortcut** | Run `Create_Desktop_Shortcut.bat` |

**Your EEG Paradox converter is ready to handle any EDF file and convert it to any major EEG software format!** 🎉

