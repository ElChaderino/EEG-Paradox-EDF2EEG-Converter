# EEG Paradox WinEEG Converter

🧠 **Professional EDF to WinEEG Converter** - A standalone application for converting EDF files to WinEEG-compatible .EEG format with a modern GUI interface.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.7+-green)
![License](https://img.shields.io/badge/license-GPL--3-blue)

## ✨ Features

- **🎯 Drag & Drop Interface** - Simply drag EDF files into the application
- **🔧 Automatic Template Selection** - Chooses optimal template based on file duration
- **📏 Extended Capacity** - Handles files up to 30 minutes (expandable)
- **👤 Custom Patient Names** - Embed custom patient information in headers
- **🎨 Dark Mode UI** - Professional cyberpunk-themed interface
- **⚡ Real-time Progress** - Live conversion progress and status updates
- **🎯 Proven Algorithm** - Based on reverse-engineered WinEEG format specifications

## 🚀 Quick Start

### Prerequisites
- Python 3.7 or higher
- Windows OS (for WinEEG compatibility)

### Installation

1. **Download the converter package**
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the GUI application:**
   ```bash
   python EEG_Paradox_Converter.py
   ```

### Usage

1. **Launch the application**
2. **Load EDF file** - Click "Browse" or drag & drop
3. **Set patient name** (optional)
4. **Choose output location** (optional - auto-generated)
5. **Click "Convert to WinEEG"**
6. **Open result in WinEEG**

## 📁 File Structure

```
EEG Paradox WinEEG Converter/
├── EEG_Paradox_Converter.py    # Main GUI application
├── converter_core.py            # Core conversion algorithms
├── requirements.txt             # Python dependencies
├── README.md                   # This documentation
├── LICENSE                     # MIT License
├── templates/                  # WinEEG template files
│   ├── LB_EO_EEG.EEG          # 12-minute template
│   └── LB_EO_EEG_EXTENDED_30min.EEG  # 30-minute template
└── examples/                   # Example files and scripts
    ├── command_line_example.py
    └── batch_convert.py
```

## 🔧 Technical Details

### Conversion Process

1. **EDF Analysis** - Loads and analyzes input EDF file
2. **Template Selection** - Chooses appropriate template based on duration:
   - Files ≤12 minutes: Uses 12-minute template
   - Files >12 minutes: Uses 30-minute extended template
3. **Data Processing** - Converts EDF data to INT16 format with proper scaling
4. **Header Patching** - Updates patient information and calibration values
5. **Data Grafting** - Replaces template data with EDF data (preserving head/tail)
6. **WinEEG Output** - Generates fully compatible .EEG file

### Key Specifications

- **Input Format**: EDF (European Data Format)
- **Output Format**: WinEEG .EEG (Mitsar compatible)
- **Channel Count**: 19 channels (fixed)
- **Sampling Rate**: 250 Hz (preserved from template)
- **Data Type**: 16-bit signed integers (little-endian)
- **Calibration**: 1 µV/bit (maximum sensitivity)
- **Capacity**: Up to 30 minutes (expandable)

### Data Placement

- **Head Section** (0-5 seconds): Original template data (preserved)
- **Main Section** (5+ seconds): Your EDF data (converted)
- **Tail Section** (end): Original template data (preserved)

⚠️ **Important**: When viewing in WinEEG, your converted data starts at **5+ seconds**, not at the beginning!

## 🎯 Advanced Usage

### Command Line Interface

```bash
# Convert single file
python converter_core.py input.edf output.eeg "Patient Name"

# Batch conversion (see examples/batch_convert.py)
python examples/batch_convert.py input_folder/ output_folder/
```

### Extending Template Capacity

For files longer than 30 minutes, you can extend the template:

```bash
python extend_template.py 60  # Create 60-minute template
```

## 📊 Supported Formats

### Input (EDF)
- ✅ Standard EDF files (.edf)
- ✅ 19-channel recordings
- ✅ Any sampling rate (will be standardized to 250 Hz)
- ✅ Files up to 30 minutes (expandable)

### Output (WinEEG)
- ✅ Mitsar .EEG format
- ✅ WinEEG compatible
- ✅ Proper header structure
- ✅ Calibrated for optimal viewing

## ⚠️ Important Notes

1. **Channel Count**: Input EDF must have exactly 19 channels
2. **Duration Limit**: Current limit is 30 minutes (can be extended)
3. **Data Location**: Converted data starts at 5+ seconds in WinEEG
4. **Template Dependency**: Requires working WinEEG templates
5. **Windows Only**: Designed for WinEEG (Windows software)

## 🐛 Troubleshooting

### Common Issues

**"No traces visible in WinEEG"**
- Solution: Navigate to 10+ seconds in WinEEG (data starts at 5 seconds)
- Check: Increase gain if traces are too small

**"Seek failed" error**
- Solution: Ensure templates are present in templates/ folder
- Check: Verify EDF file has exactly 19 channels

**"Conversion failed"**
- Solution: Check that MNE can read your EDF file
- Check: Ensure sufficient disk space for output

### Getting Help

1. Check this README for common solutions
2. Verify your EDF file meets requirements (19 channels)
3. Ensure all dependencies are installed
4. Check that templates exist in templates/ folder

## 🔬 Technical Background

This converter was developed through reverse engineering of the WinEEG file format, discovering:

- **Magic numbers** and header structure
- **Calibration byte locations** (0x0326-0x0338)
- **Data organization** and frame alignment
- **Template-based approach** for guaranteed compatibility

The conversion algorithm uses proven techniques that ensure 100% WinEEG compatibility.

## 📄 License

GPL-3 License - see LICENSE file for details.

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

## 🏆 Credits

**EEG Paradox Development Team**
- Reverse engineering of WinEEG format
- Algorithm development and optimization
- GUI design and implementation

## 📈 Version History

### v1.0.0 (Current)
- ✅ Complete GUI application
- ✅ Drag & drop support
- ✅ Automatic template selection
- ✅ 30-minute capacity
- ✅ Custom patient names
- ✅ Real-time progress tracking
- ✅ Professional dark mode interface

---

**🎯 Ready to convert your EDF files to WinEEG format!**

Launch `EEG_Paradox_Converter.py` to get started.
