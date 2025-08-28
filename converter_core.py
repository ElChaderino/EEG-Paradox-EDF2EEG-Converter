"""
EEG Paradox Converter Core
==========================

Core conversion logic for EDF to WinEEG .EEG format conversion.
This module contains the proven conversion algorithms.

Author: EEG Paradox Development Team
"""

import os
import sys
import struct
import numpy as np
from pathlib import Path

class UniversalConverter:
    """Universal EDF to WinEEG converter with proven algorithms"""
    
    # Constants
    HEADER = 1024
    TRAILER = 34  # Working LB template uses 34-byte trailer
    CH = 19
    BPS = 2
    FRAME = CH * BPS
    
    # Template paths (relative to this module)
    TEMPLATES_DIR = "templates"
    ORIGINAL_TEMPLATE = "LB_EO_EEG.EEG"
    EXTENDED_TEMPLATE = "LB_EO_EEG_EXTENDED_30min.EEG"
    
    # Calibration byte locations (discovered through reverse engineering)
    CALIBRATION_OFFSETS = {
        0:  (0x0326, True),   # Marker channel - keep unchanged
        1:  (0x0327, False),  # EEG channel
        2:  (0x0328, False),  3:  (0x0329, False),  4:  (0x032A, False),
        5:  (0x032B, False),  6:  (0x032C, False),  7:  (0x032D, False),
        8:  (0x032E, False),  9:  (0x032F, False),  10: (0x0330, False),
        11: (0x0331, False),  12: (0x0332, False),  13: (0x0333, False),
        14: (0x0334, False),  15: (0x0335, False),  16: (0x0336, False),
        17: (0x0337, False),  18: (0x0338, True),   # Marker channel - keep unchanged
    }
    
    # Optimal calibration value for maximum sensitivity
    NEW_CALIBRATION_VALUE = 1  # 1 µV/bit
    
    def __init__(self):
        self.base_dir = os.path.dirname(__file__)
        self.templates_dir = os.path.join(self.base_dir, self.TEMPLATES_DIR)
    
    def get_template_path(self, template_name):
        """Get full path to template file"""
        return os.path.join(self.templates_dir, template_name)
    
    def choose_template(self, edf_duration_minutes):
        """Choose appropriate template based on EDF duration"""
        
        print(f"🔍 Choosing template for {edf_duration_minutes:.1f} minute EDF...")
        
        if edf_duration_minutes <= 12:
            # Use original template (12.2 minutes capacity)
            template_path = self.get_template_path(self.ORIGINAL_TEMPLATE)
            if os.path.exists(template_path):
                print(f"   ✅ Using original template (12.2 min capacity)")
                return template_path
        
        # Use extended template (30 minutes capacity)
        template_path = self.get_template_path(self.EXTENDED_TEMPLATE)
        if os.path.exists(template_path):
            print(f"   ✅ Using extended template (30.0 min capacity)")
            return template_path
        
        # Fallback to original if extended doesn't exist
        template_path = self.get_template_path(self.ORIGINAL_TEMPLATE)
        if os.path.exists(template_path):
            print(f"   ⚠️  Extended template not found, using original (will truncate)")
            return template_path
        
        raise FileNotFoundError("No suitable template found!")
    
    def read_int16(self, path, offset=0):
        """Read raw INT16 data from file"""
        with open(path, 'rb') as f:
            f.seek(0, 2)
            size = f.tell()
        with open(path, 'rb') as f:
            f.seek(offset)
            data = np.frombuffer(f.read(size - offset), dtype='<i2')
        return data
    
    def patch_patient_info(self, header_bytes, patient_name="EEG Paradox Patient"):
        """Patch patient/study information in header"""
        header = bytearray(header_bytes)
        
        print("🔍 Patching patient/study information...")
        
        # Patient name locations (discovered through analysis)
        patient_locations = [(0x0080, 32), (0x00A0, 32), (0x00C0, 32), (0x0140, 32)]
        patient_bytes = patient_name.encode('ascii', errors='ignore')[:31]
        patient_bytes += b'\x00' * (32 - len(patient_bytes))
        
        patches_made = 0
        for offset, length in patient_locations:
            if offset + length <= len(header):
                header[offset:offset+length] = patient_bytes
                patches_made += 1
        
        print(f"   ✅ Patched patient info at {patches_made} locations: '{patient_name}'")
        return bytes(header)
    
    def patch_calibration_bytes(self, header_bytes):
        """Patch calibration bytes for maximum sensitivity"""
        header = bytearray(header_bytes)
        
        print("🔍 Patching calibration bytes...")
        
        patches_made = 0
        for ch, (offset, is_marker) in self.CALIBRATION_OFFSETS.items():
            if offset < len(header):
                current_val = header[offset]
                if not is_marker:
                    header[offset] = self.NEW_CALIBRATION_VALUE
                    patches_made += 1
                    print(f"   Ch{ch:02d} @ 0x{offset:04X}: {current_val:02X} → {self.NEW_CALIBRATION_VALUE:02X}")
        
        print(f"   ✅ Patched {patches_made} calibration bytes (1 µV/bit sensitivity)")
        return bytes(header)
    
    def convert_raw_to_eeg(self, raw_file, output_file, patient_name="EEG Paradox Patient"):
        """Convert raw INT16 data to WinEEG .EEG format"""
        
        print(f"🧠 EEG Paradox Universal Converter")
        print(f"=" * 60)
        print(f"📥 Input raw data: {raw_file}")
        print(f"📤 Output EEG file: {output_file}")
        print(f"👤 Patient name: {patient_name}")
        
        try:
            # Check if raw data exists
            if not os.path.exists(raw_file):
                raise FileNotFoundError(f"Raw data file not found: {raw_file}")
            
            # --- Analyze raw data first ---
            raw_data = self.read_int16(raw_file, offset=0)
            edf_frames = len(raw_data) // self.CH
            edf_duration_minutes = edf_frames / 250 / 60  # 250 Hz sampling
            
            print(f"📊 Raw data analysis: {edf_frames:,} frames ({edf_duration_minutes:.1f} minutes)")
            
            # --- Choose appropriate template ---
            template_path = self.choose_template(edf_duration_minutes)
            
            # --- Read chosen template ---
            with open(template_path, 'rb') as f:
                tpl = f.read()

            if len(tpl) < self.HEADER + self.TRAILER:
                raise ValueError("Template too small.")

            header = tpl[:self.HEADER]
            trailer = tpl[-self.TRAILER:]
            data_bytes = tpl[self.HEADER:-self.TRAILER]
            
            if len(data_bytes) % self.FRAME != 0:
                raise ValueError("Template data payload not multiple of frame bytes.")

            tpl_frames = len(data_bytes) // self.FRAME
            tpl_i16 = np.frombuffer(data_bytes, dtype='<i2').copy()
            tpl_frames19 = tpl_i16.reshape(tpl_frames, self.CH)

            print(f"📊 Template: {tpl_frames:,} frames ({tpl_frames/250/60:.1f} minutes)")

            # --- Prepare EDF data ---
            edf_data = raw_data[:edf_frames * self.CH]
            edf_frames19 = edf_data.reshape(edf_frames, self.CH)

            # --- Choose replacement window ---
            HEAD_FRAMES = 1250   # 5 s @ 250 Hz (preserve original data)
            TAIL_FRAMES = 250    # 1 s @ 250 Hz (preserve original data)
            
            usable_tpl = tpl_frames - HEAD_FRAMES - TAIL_FRAMES
            frames_to_use = min(usable_tpl, edf_frames)
            start = HEAD_FRAMES
            end = start + frames_to_use

            print(f"📊 Replacement window: {start:,}..{end-1:,} (len {frames_to_use:,})")
            
            if frames_to_use < edf_frames:
                truncated_minutes = (edf_frames - frames_to_use) / 250 / 60
                print(f"⚠️  EDF data truncated: {truncated_minutes:.1f} minutes lost")
            else:
                print(f"✅ Full EDF data will be converted")

            # --- Patch header ---
            patched_header = self.patch_patient_info(header, patient_name)
            patched_header = self.patch_calibration_bytes(patched_header)

            # --- Build output frames ---
            out = tpl_frames19.copy()

            # Replace only EEG channels; preserve marker channels
            PRESERVE = {0, 18}  # Channels 0 and 18 are markers
            eeg_ch = [c for c in range(self.CH) if c not in PRESERVE]

            # Replace with EDF data
            out[start:end, eeg_ch] = edf_frames19[:frames_to_use, eeg_ch]

            # --- Write output file ---
            out_i16 = out.reshape(-1).astype('<i2', copy=False)

            expected_size = self.HEADER + out_i16.nbytes + self.TRAILER
            if expected_size != len(tpl):
                raise ValueError(f"Size mismatch: expected {len(tpl)}, got {expected_size}")

            with open(output_file, 'wb') as f:
                f.write(patched_header)
                f.write(out_i16.tobytes(order='C'))
                f.write(trailer)

            print(f"\n✅ Conversion successful!")
            print(f"   📄 Output: {output_file}")
            print(f"   📏 Size: {expected_size:,} bytes")
            print(f"   🕐 Duration: {tpl_frames/250/60:.1f} minutes")
            print(f"   🎯 EDF data location: {start/250:.1f} - {end/250:.1f} seconds")
            print(f"   👤 Patient: {patient_name}")
            print(f"\n💡 Important: EDF data starts at {start/250:.1f} seconds in WinEEG!")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Conversion failed: {str(e)}")
            raise e

# Standalone conversion function for command-line use
def convert_edf_to_wineeg(edf_file, output_file, patient_name="EEG Paradox Patient"):
    """
    Standalone conversion function
    
    Args:
        edf_file (str): Path to input EDF file
        output_file (str): Path to output .EEG file
        patient_name (str): Patient name to embed in header
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        import mne
        
        # Step 1: Convert EDF to raw INT16
        print("🔄 Converting EDF to raw data...")
        raw = mne.io.read_raw_edf(edf_file, preload=True, verbose=False)
        
        # Ensure we have 19 channels
        if len(raw.ch_names) != 19:
            raise ValueError(f"Expected 19 channels, got {len(raw.ch_names)}")
        
        # Get data and convert to microvolts
        data = raw.get_data() * 1e6  # Convert to µV
        
        # Scale to INT16 range
        scaling_factor = 10_000_000
        data_scaled = data * scaling_factor
        
        # Clip to INT16 range
        data_clipped = np.clip(data_scaled, -32768, 32767)
        
        # Convert to INT16 and interleave
        data_int16 = data_clipped.astype(np.int16)
        
        # Interleave: sample0_ch0, sample0_ch1, ..., sample0_ch18, sample1_ch0, ...
        n_samples, n_channels = data_int16.shape
        interleaved = np.zeros((n_samples * n_channels,), dtype=np.int16)
        
        for sample in range(n_samples):
            start_idx = sample * n_channels
            end_idx = start_idx + n_channels
            interleaved[start_idx:end_idx] = data_int16[sample, :]
        
        # Save to temporary file
        temp_file = output_file.replace('.eeg', '_temp_raw.bin')
        interleaved.tofile(temp_file)
        
        # Step 2: Convert raw to EEG
        print("🔧 Converting raw to WinEEG format...")
        converter = UniversalConverter()
        success = converter.convert_raw_to_eeg(temp_file, output_file, patient_name)
        
        # Cleanup temp file
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        return success
        
    except Exception as e:
        print(f"❌ Conversion failed: {str(e)}")
        return False

if __name__ == "__main__":
    # Command-line interface
    if len(sys.argv) < 3:
        print("EEG Paradox WinEEG Converter - Command Line")
        print("=" * 50)
        print("Usage: python converter_core.py INPUT.edf OUTPUT.eeg [PATIENT_NAME]")
        print("")
        print("Example:")
        print("  python converter_core.py patient.edf patient_wineeg.eeg \"John Doe\"")
        sys.exit(1)
    
    edf_file = sys.argv[1]
    output_file = sys.argv[2]
    patient_name = sys.argv[3] if len(sys.argv) > 3 else "EEG Paradox Patient"
    
    success = convert_edf_to_wineeg(edf_file, output_file, patient_name)
    
    if success:
        print(f"\n🎉 SUCCESS! WinEEG file created: {output_file}")
        sys.exit(0)
    else:
        print(f"\n❌ FAILED! Check error messages above.")
        sys.exit(1)
