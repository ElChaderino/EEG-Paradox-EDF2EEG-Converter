#!/usr/bin/env python3
"""
Command Line Conversion Example
===============================

Example script showing how to use the EEG Paradox Converter from command line.

Usage:
    python command_line_example.py input.edf output.eeg "Patient Name"
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from converter_core import convert_edf_to_wineeg

def main():
    """Main command line interface"""
    
    print("🧠 EEG Paradox Converter - Command Line Example")
    print("=" * 50)
    
    if len(sys.argv) < 3:
        print("Usage: python command_line_example.py INPUT.edf OUTPUT.eeg [PATIENT_NAME]")
        print("")
        print("Examples:")
        print("  python command_line_example.py patient.edf patient_wineeg.eeg")
        print("  python command_line_example.py data.edf result.eeg \"John Doe\"")
        print("")
        print("Features:")
        print("  • Automatic template selection")
        print("  • Supports up to 30-minute files")
        print("  • Custom patient names")
        print("  • Optimal calibration")
        return 1
    
    # Get arguments
    edf_file = sys.argv[1]
    output_file = sys.argv[2]
    patient_name = sys.argv[3] if len(sys.argv) > 3 else "EEG Paradox Patient"
    
    # Validate input
    if not os.path.exists(edf_file):
        print(f"❌ Error: Input file not found: {edf_file}")
        return 1
    
    if not edf_file.lower().endswith('.edf'):
        print(f"⚠️  Warning: Input file doesn't have .edf extension")
    
    # Perform conversion
    print(f"📥 Input:  {edf_file}")
    print(f"📤 Output: {output_file}")
    print(f"👤 Patient: {patient_name}")
    print("")
    
    try:
        success = convert_edf_to_wineeg(edf_file, output_file, patient_name)
        
        if success:
            print(f"\n🎉 SUCCESS!")
            print(f"   📄 WinEEG file created: {output_file}")
            print(f"   💡 Remember: EDF data starts at 5+ seconds in WinEEG")
            return 0
        else:
            print(f"\n❌ CONVERSION FAILED!")
            return 1
            
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
