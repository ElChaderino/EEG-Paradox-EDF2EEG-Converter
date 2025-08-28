#!/usr/bin/env python3
"""
Batch Conversion Example
========================

Example script for batch converting multiple EDF files to WinEEG format.

Usage:
    python batch_convert.py input_folder/ output_folder/
"""

import sys
import os
import glob
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from converter_core import convert_edf_to_wineeg

def batch_convert(input_folder, output_folder, patient_prefix="Patient"):
    """
    Convert all EDF files in input folder to WinEEG format
    
    Args:
        input_folder (str): Folder containing EDF files
        output_folder (str): Folder for output EEG files
        patient_prefix (str): Prefix for patient names
    """
    
    print("🧠 EEG Paradox Batch Converter")
    print("=" * 40)
    
    # Validate folders
    if not os.path.exists(input_folder):
        print(f"❌ Input folder not found: {input_folder}")
        return False
    
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    # Find all EDF files
    edf_pattern = os.path.join(input_folder, "*.edf")
    edf_files = glob.glob(edf_pattern)
    
    if not edf_files:
        print(f"❌ No EDF files found in: {input_folder}")
        return False
    
    print(f"📁 Input folder: {input_folder}")
    print(f"📁 Output folder: {output_folder}")
    print(f"📊 Found {len(edf_files)} EDF files")
    print("")
    
    # Convert each file
    successful = 0
    failed = 0
    
    for i, edf_file in enumerate(edf_files, 1):
        filename = os.path.basename(edf_file)
        base_name = os.path.splitext(filename)[0]
        
        # Generate output filename and patient name
        output_file = os.path.join(output_folder, f"{base_name}_WinEEG.eeg")
        patient_name = f"{patient_prefix}_{base_name}"
        
        print(f"[{i}/{len(edf_files)}] Converting: {filename}")
        print(f"   👤 Patient: {patient_name}")
        
        try:
            success = convert_edf_to_wineeg(edf_file, output_file, patient_name)
            
            if success:
                print(f"   ✅ Success: {base_name}_WinEEG.eeg")
                successful += 1
            else:
                print(f"   ❌ Failed: {filename}")
                failed += 1
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            failed += 1
        
        print("")
    
    # Summary
    print("=" * 40)
    print(f"📊 Batch Conversion Summary:")
    print(f"   ✅ Successful: {successful}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📄 Total: {len(edf_files)}")
    
    if successful > 0:
        print(f"\n🎉 {successful} files converted successfully!")
        print(f"   📁 Output location: {output_folder}")
        print(f"   💡 Remember: EDF data starts at 5+ seconds in WinEEG")
    
    return failed == 0

def main():
    """Main entry point"""
    
    if len(sys.argv) < 3:
        print("🧠 EEG Paradox Batch Converter")
        print("=" * 35)
        print("Usage: python batch_convert.py INPUT_FOLDER OUTPUT_FOLDER [PATIENT_PREFIX]")
        print("")
        print("Examples:")
        print("  python batch_convert.py ./edf_files/ ./wineeg_files/")
        print("  python batch_convert.py C:/Data/EDF/ C:/Data/WinEEG/ \"Study_A\"")
        print("")
        print("Features:")
        print("  • Converts all .edf files in input folder")
        print("  • Automatic output naming (filename_WinEEG.eeg)")
        print("  • Custom patient name prefixes")
        print("  • Progress tracking and error reporting")
        return 1
    
    input_folder = sys.argv[1]
    output_folder = sys.argv[2]
    patient_prefix = sys.argv[3] if len(sys.argv) > 3 else "Patient"
    
    # Normalize paths
    input_folder = os.path.abspath(input_folder)
    output_folder = os.path.abspath(output_folder)
    
    # Perform batch conversion
    success = batch_convert(input_folder, output_folder, patient_prefix)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
