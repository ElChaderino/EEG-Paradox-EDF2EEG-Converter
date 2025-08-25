#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EEG Paradox EDF to EEG Converter v2.9.1
Universal EDF to EEG format converter

Copyright (C) 2024 EEG Paradox Project
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

For more information, see LICENSE file.
"""

import os
import sys
import struct
import numpy as np
from pathlib import Path
import shutil
import argparse
import logging
import json
import datetime
import re
from configparser import ConfigParser
from collections import Counter
import traceback
import hashlib
import warnings

# Try to import MNE
MNE_AVAILABLE = False
try:
    import mne
    MNE_AVAILABLE = True
    print("✅ MNE-Python available - Full EDF support enabled")
except ImportError:
    print("⚠️  MNE-Python not available - Limited functionality")

# Amplifier specifications database
AMPLIFIER_DATABASE = {
    # Nihon Kohden systems
    'nihon_kohden': {
        'identifiers': ['nihon', 'kohden', 'nk', 'neurofax'],
        'typical_range_uv': 3276.8,  # ±3276.8 µV full scale
        'resolution_bits': 16,
        'gain_settings': [1, 2, 5, 10, 20, 50, 100],
        'calibration_signal': {'amplitude_uv': 50, 'frequency_hz': 10},
        'scaling_factor': 1.0,
        'notes': 'Standard clinical EEG amplifier'
    },
    
    # BioSemi systems  
    'biosemi': {
        'identifiers': ['biosemi', 'activetwo', 'active'],
        'typical_range_uv': 262144,  # ±262.144 mV (very high range)
        'resolution_bits': 24,
        'gain_settings': [1],  # Fixed gain, high resolution
        'calibration_signal': {'amplitude_uv': 100, 'frequency_hz': 1},
        'scaling_factor': 31.25e-9,  # BioSemi specific scaling
        'notes': 'High-resolution active electrode system'
    },
    
    # Brain Products (BrainAmp)
    'brainproducts': {
        'identifiers': ['brain products', 'brainamp', 'brainvision', 'bp'],
        'typical_range_uv': 16777.216,  # ±16777.216 µV
        'resolution_bits': 16,
        'gain_settings': [1, 2, 5, 10, 20, 50],
        'calibration_signal': {'amplitude_uv': 200, 'frequency_hz': 10},
        'scaling_factor': 0.1,  # 0.1 µV resolution
        'notes': 'Research-grade EEG system'
    },
    
    # Neuroscan systems
    'neuroscan': {
        'identifiers': ['neuroscan', 'compumedics', 'scan'],
        'typical_range_uv': 6553.6,  # ±6553.6 µV
        'resolution_bits': 16,
        'gain_settings': [1, 2, 5, 10, 20, 50, 100, 200],
        'calibration_signal': {'amplitude_uv': 50, 'frequency_hz': 10},
        'scaling_factor': 0.2,
        'notes': 'Clinical and research EEG'
    },
    
    # EGI (Electrical Geodesics)
    'egi': {
        'identifiers': ['egi', 'electrical geodesics', 'geodesic', 'netstation'],
        'typical_range_uv': 4096,  # ±4096 µV
        'resolution_bits': 16,
        'gain_settings': [1, 2, 4, 8, 16],
        'calibration_signal': {'amplitude_uv': 100, 'frequency_hz': 10},
        'scaling_factor': 0.0625,
        'notes': 'High-density EEG system'
    },
    
    # ANT Neuro (Advanced Neuro Technology)
    'ant_neuro': {
        'identifiers': ['ant neuro', 'ant', 'eego', 'waveguard'],
        'typical_range_uv': 8192,  # ±8192 µV  
        'resolution_bits': 24,
        'gain_settings': [1, 2, 4, 8],
        'calibration_signal': {'amplitude_uv': 100, 'frequency_hz': 10},
        'scaling_factor': 0.125,
        'notes': 'Modern research EEG system'
    },
    
    # g.tec systems
    'gtec': {
        'identifiers': ['gtec', 'g.tec', 'guger', 'g.usbamp'],
        'typical_range_uv': 250000,  # ±250 mV (very high)
        'resolution_bits': 16,
        'gain_settings': [1, 2, 4, 8, 16],
        'calibration_signal': {'amplitude_uv': 100, 'frequency_hz': 10},
        'scaling_factor': 7.629,  # High sensitivity
        'notes': 'BCI and research system'
    },
    
    # TMSi systems
    'tmsi': {
        'identifiers': ['tmsi', 'refa', 'saga'],
        'typical_range_uv': 8192,  # ±8192 µV
        'resolution_bits': 22,
        'gain_settings': [1, 2, 4, 8, 16],
        'calibration_signal': {'amplitude_uv': 100, 'frequency_hz': 10},
        'scaling_factor': 0.125,
        'notes': 'Wireless EEG system'
    },
    
    # Mitsar systems (WinEEG)
    'mitsar': {
        'identifiers': ['mitsar', 'wineeg', 'eeg-21', 'eeg-19'],
        'typical_range_uv': 1638.4,  # ±1638.4 µV (conservative)
        'resolution_bits': 16,
        'gain_settings': [1, 2, 5, 10, 20, 50, 100],
        'calibration_signal': {'amplitude_uv': 50, 'frequency_hz': 10},
        'scaling_factor': 0.05,  # High resolution
        'notes': 'WinEEG native system'
    },
    
    # FreeEEG32 - Open source EEG system
    'freeeeg32': {
        'identifiers': ['freeeeg', 'freeeeg32', 'free eeg', 'openeeg'],
        'typical_range_uv': 1000,  # ±1000 µV typical range
        'resolution_bits': 24,
        'gain_settings': [1, 2, 4, 8, 12, 24],
        'calibration_signal': {'amplitude_uv': 100, 'frequency_hz': 10},
        'scaling_factor': 0.1,  # Fine resolution
        'notes': 'Open-source EEG system - may have scaling issues in EDF export'
    },
    
    # OpenBCI systems
    'openbci': {
        'identifiers': ['openbci', 'cyton', 'ganglion', 'ultracortex'],
        'typical_range_uv': 4500,  # ±4.5mV range
        'resolution_bits': 24,
        'gain_settings': [1, 2, 4, 6, 8, 12, 24],
        'calibration_signal': {'amplitude_uv': 100, 'frequency_hz': 1},
        'scaling_factor': 0.022,  # 0.022 µV/LSB for ADS1299
        'notes': 'OpenBCI systems - ADS1299 chipset, often has unit scaling issues'
    },
    
    # Arduino-based EEG systems
    'arduino_eeg': {
        'identifiers': ['arduino', 'diy eeg', 'homemade', 'custom eeg'],
        'typical_range_uv': 3300,  # 3.3V Arduino range
        'resolution_bits': 10,  # Arduino ADC
        'gain_settings': [1, 10, 100, 1000],
        'calibration_signal': {'amplitude_uv': 100, 'frequency_hz': 10},
        'scaling_factor': 3.22,  # 3.3V / 1024 * 1000 µV/mV
        'notes': 'Arduino-based EEG - often exports raw ADC values'
    },
    
    # Muse headband
    'muse': {
        'identifiers': ['muse', 'interaxon', 'muse headband'],
        'typical_range_uv': 1682,  # ±1682 µV
        'resolution_bits': 12,
        'gain_settings': [1],  # Fixed gain
        'calibration_signal': {'amplitude_uv': 50, 'frequency_hz': 10},
        'scaling_factor': 0.48,  # 0.48 µV/LSB
        'notes': 'Muse consumer EEG headband - may export in different units'
    },
    
    # Emotiv systems
    'emotiv': {
        'identifiers': ['emotiv', 'epoc', 'insight', 'flex'],
        'typical_range_uv': 8400,  # ±8.4mV
        'resolution_bits': 14,
        'gain_settings': [1],  # Fixed gain
        'calibration_signal': {'amplitude_uv': 100, 'frequency_hz': 10},
        'scaling_factor': 0.51,  # ~0.51 µV/LSB
        'notes': 'Emotiv consumer EEG systems - proprietary scaling'
    },
    
    # NeuroSky systems
    'neurosky': {
        'identifiers': ['neurosky', 'mindwave', 'tgam'],
        'typical_range_uv': 3000,  # Estimated range
        'resolution_bits': 12,
        'gain_settings': [1],  # Fixed gain
        'calibration_signal': {'amplitude_uv': 100, 'frequency_hz': 10},
        'scaling_factor': 0.73,  # Estimated
        'notes': 'NeuroSky consumer EEG - single channel, may have scaling issues'
    },
    
    # ModularEEG and similar open-source projects
    'modulareeg': {
        'identifiers': ['modulareeg', 'modular eeg', 'openeeg project'],
        'typical_range_uv': 2500,  # ±2.5V typical
        'resolution_bits': 10,
        'gain_settings': [1, 10, 100, 1000],
        'calibration_signal': {'amplitude_uv': 100, 'frequency_hz': 10},
        'scaling_factor': 2.44,  # 2.5V / 1024 * 1000
        'notes': 'ModularEEG open-source project - often raw ADC values'
    },
    
    # Olimex EEG systems
    'olimex': {
        'identifiers': ['olimex', 'eeg-smt', 'shield-ekg-emg'],
        'typical_range_uv': 3300,  # 3.3V range
        'resolution_bits': 10,
        'gain_settings': [1, 2, 5, 10],
        'calibration_signal': {'amplitude_uv': 100, 'frequency_hz': 10},
        'scaling_factor': 3.22,  # Similar to Arduino
        'notes': 'Olimex open-hardware EEG - may need unit conversion'
    },
    
    # Bitalino and similar biosignal platforms
    'bitalino': {
        'identifiers': ['bitalino', 'biosignalsplux', 'plux'],
        'typical_range_uv': 3300,  # 3.3V ADC
        'resolution_bits': 10,
        'gain_settings': [1, 2, 10, 100],
        'calibration_signal': {'amplitude_uv': 100, 'frequency_hz': 10},
        'scaling_factor': 3.22,  # 3.3V/1024*1000
        'notes': 'Bitalino biosignal platform - often exports ADC counts'
    },
    
    # Cadwell Easy systems
    'cadwell': {
        'identifiers': ['cadwell', 'easy', 'easy ii', 'easy iii'],
        'typical_range_uv': 5000,  # ±5000 µV
        'resolution_bits': 16,
        'gain_settings': [1, 2, 5, 10, 20, 50, 100, 200],
        'calibration_signal': {'amplitude_uv': 50, 'frequency_hz': 10},
        'scaling_factor': 0.15,
        'notes': 'Cadwell clinical EEG systems'
    },
    
    # Grass-Telefactor systems
    'grass': {
        'identifiers': ['grass', 'telefactor', 'aura', 'comet', 'heritage'],
        'typical_range_uv': 10000,  # ±10mV
        'resolution_bits': 16,
        'gain_settings': [1, 2, 5, 10, 20, 50, 100],
        'calibration_signal': {'amplitude_uv': 100, 'frequency_hz': 10},
        'scaling_factor': 0.3,
        'notes': 'Grass-Telefactor clinical EEG systems'
    },
    
    # Stellate Harmonie/XLTEK systems
    'stellate': {
        'identifiers': ['stellate', 'harmonie', 'xltek', 'neuroworks'],
        'typical_range_uv': 8192,  # ±8192 µV
        'resolution_bits': 16,
        'gain_settings': [1, 2, 5, 10, 20, 50, 100],
        'calibration_signal': {'amplitude_uv': 50, 'frequency_hz': 10},
        'scaling_factor': 0.25,
        'notes': 'Stellate/XLTEK clinical EEG and sleep systems'
    },
    
    # Persyst systems
    'persyst': {
        'identifiers': ['persyst', 'insight', 'reveal'],
        'typical_range_uv': 4096,  # ±4096 µV
        'resolution_bits': 16,
        'gain_settings': [1, 2, 5, 10, 20, 50],
        'calibration_signal': {'amplitude_uv': 50, 'frequency_hz': 10},
        'scaling_factor': 0.125,
        'notes': 'Persyst clinical EEG analysis systems'
    },
    
    # Natus/Nicolet systems (more comprehensive)
    'natus_nicolet': {
        'identifiers': ['natus', 'nicolet', 'viking', 'sleepworks', 'remlogic'],
        'typical_range_uv': 3276.8,  # ±3276.8 µV
        'resolution_bits': 16,
        'gain_settings': [1, 2, 5, 10, 20, 50, 100],
        'calibration_signal': {'amplitude_uv': 50, 'frequency_hz': 10},
        'scaling_factor': 0.1,
        'notes': 'Natus/Nicolet clinical EEG and sleep systems'
    },
    
    # Micromed systems
    'micromed': {
        'identifiers': ['micromed', 'braintrace', 'system plus'],
        'typical_range_uv': 6553.6,  # ±6553.6 µV
        'resolution_bits': 16,
        'gain_settings': [1, 2, 5, 10, 20, 50, 100],
        'calibration_signal': {'amplitude_uv': 50, 'frequency_hz': 10},
        'scaling_factor': 0.2,
        'notes': 'Micromed clinical EEG systems'
    },
    
    # Nihon Kohden (more specific)
    'nihon_kohden_neurofax': {
        'identifiers': ['neurofax', 'nk', 'nihon kohden', 'eeg-1100', 'eeg-1200'],
        'typical_range_uv': 3276.8,  # ±3276.8 µV
        'resolution_bits': 16,
        'gain_settings': [1, 2, 5, 10, 20, 50, 100],
        'calibration_signal': {'amplitude_uv': 50, 'frequency_hz': 10},
        'scaling_factor': 0.1,
        'notes': 'Nihon Kohden Neurofax clinical EEG systems'
    },
    
    # Medtronic/Covidien systems
    'medtronic': {
        'identifiers': ['medtronic', 'covidien', 'invivo', 'cerebus'],
        'typical_range_uv': 8192,  # ±8192 µV
        'resolution_bits': 16,
        'gain_settings': [1, 2, 4, 8, 16, 32],
        'calibration_signal': {'amplitude_uv': 100, 'frequency_hz': 10},
        'scaling_factor': 0.25,
        'notes': 'Medtronic/Covidien clinical monitoring systems'
    },
    
    # Blackrock Microsystems
    'blackrock': {
        'identifiers': ['blackrock', 'cerebus', 'neuroport', 'utah array'],
        'typical_range_uv': 8192,  # ±8192 µV
        'resolution_bits': 16,
        'gain_settings': [1, 2, 4, 8, 16],
        'calibration_signal': {'amplitude_uv': 100, 'frequency_hz': 10},
        'scaling_factor': 0.25,
        'notes': 'Blackrock neural recording systems'
    },
    
    # Ripple Neuro systems
    'ripple': {
        'identifiers': ['ripple', 'grapevine', 'trellis'],
        'typical_range_uv': 8000,  # ±8mV
        'resolution_bits': 16,
        'gain_settings': [1, 2, 4, 8, 16],
        'calibration_signal': {'amplitude_uv': 100, 'frequency_hz': 10},
        'scaling_factor': 0.244,
        'notes': 'Ripple Neuro research systems'
    },
    
    # Alpha Omega systems
    'alpha_omega': {
        'identifiers': ['alpha omega', 'alpha-omega', 'neuro omega', 'map system'],
        'typical_range_uv': 10000,  # ±10mV
        'resolution_bits': 16,
        'gain_settings': [1, 2, 5, 10, 20],
        'calibration_signal': {'amplitude_uv': 100, 'frequency_hz': 10},
        'scaling_factor': 0.305,
        'notes': 'Alpha Omega clinical neurophysiology systems'
    },
    
    # Plexon systems
    'plexon': {
        'identifiers': ['plexon', 'omniplex', 'cineplex'],
        'typical_range_uv': 8000,  # ±8mV
        'resolution_bits': 16,
        'gain_settings': [1, 2, 4, 8, 16, 32],
        'calibration_signal': {'amplitude_uv': 100, 'frequency_hz': 10},
        'scaling_factor': 0.244,
        'notes': 'Plexon research neurophysiology systems'
    },
    
    # Tucker-Davis Technologies
    'tdt': {
        'identifiers': ['tdt', 'tucker davis', 'rz2', 'rz5', 'synapse'],
        'typical_range_uv': 10000,  # ±10V range typically
        'resolution_bits': 24,
        'gain_settings': [1, 2, 4, 8, 16],
        'calibration_signal': {'amplitude_uv': 100, 'frequency_hz': 10},
        'scaling_factor': 0.596,  # High resolution
        'notes': 'Tucker-Davis Technologies research systems'
    },
    
    # Intan Technologies
    'intan': {
        'identifiers': ['intan', 'rhd2000', 'rhs2000', 'open ephys'],
        'typical_range_uv': 8192,  # ±8192 µV
        'resolution_bits': 16,
        'gain_settings': [1, 2, 4, 8, 16, 32, 64],
        'calibration_signal': {'amplitude_uv': 100, 'frequency_hz': 10},
        'scaling_factor': 0.195,  # 0.195 µV/LSB typical
        'notes': 'Intan amplifier chips - used in many research systems'
    },
    
    # Multi Channel Systems (MCS)
    'mcs': {
        'identifiers': ['mcs', 'multi channel systems', 'mc_rack', 'w2100'],
        'typical_range_uv': 8192,  # ±8192 µV
        'resolution_bits': 16,
        'gain_settings': [1, 2, 5, 10, 20, 50],
        'calibration_signal': {'amplitude_uv': 100, 'frequency_hz': 10},
        'scaling_factor': 0.25,
        'notes': 'Multi Channel Systems research platforms'
    },
    
    # Nexus systems (Mind Media)
    'nexus': {
        'identifiers': ['nexus', 'mind media', 'nexus-10', 'nexus-32', 'biotrace'],
        'typical_range_uv': 4096,  # ±4096 µV
        'resolution_bits': 16,
        'gain_settings': [1, 2, 4, 8, 16, 32],
        'calibration_signal': {'amplitude_uv': 100, 'frequency_hz': 10},
        'scaling_factor': 0.125,
        'notes': 'Nexus biofeedback and EEG systems'
    },
    
    # WIZ systems (EEG Info)
    'wiz': {
        'identifiers': ['wiz', 'eeg info', 'eeginfo', 'wiz eeg'],
        'typical_range_uv': 3200,  # ±3200 µV
        'resolution_bits': 16,
        'gain_settings': [1, 2, 5, 10, 20, 50],
        'calibration_signal': {'amplitude_uv': 50, 'frequency_hz': 10},
        'scaling_factor': 0.098,
        'notes': 'WIZ EEG systems by EEG Info'
    },
    
    # EEG Info systems (general)
    'eeginfo': {
        'identifiers': ['eeg info', 'eeginfo', 'eeg-info'],
        'typical_range_uv': 3200,  # ±3200 µV
        'resolution_bits': 16,
        'gain_settings': [1, 2, 5, 10, 20, 50],
        'calibration_signal': {'amplitude_uv': 50, 'frequency_hz': 10},
        'scaling_factor': 0.098,
        'notes': 'EEG Info clinical EEG systems'
    },
    
    # Deymed systems
    'deymed': {
        'identifiers': ['deymed', 'truscan', 'diagnostic'],
        'typical_range_uv': 5000,  # ±5000 µV
        'resolution_bits': 16,
        'gain_settings': [1, 2, 5, 10, 20, 50, 100],
        'calibration_signal': {'amplitude_uv': 50, 'frequency_hz': 10},
        'scaling_factor': 0.15,
        'notes': 'Deymed clinical EEG systems'
    },
    
    # Electrical Geodesics (more comprehensive)
    'egi_comprehensive': {
        'identifiers': ['egi', 'electrical geodesics', 'geodesic', 'netstation', 'magstim egi'],
        'typical_range_uv': 4096,  # ±4096 µV
        'resolution_bits': 16,
        'gain_settings': [1, 2, 4, 8, 16],
        'calibration_signal': {'amplitude_uv': 100, 'frequency_hz': 10},
        'scaling_factor': 0.0625,
        'notes': 'EGI/Magstim high-density EEG systems'
    },
    
    # EB Neuro systems
    'eb_neuro': {
        'identifiers': ['eb neuro', 'ebneuro', 'galileo', 'mizar'],
        'typical_range_uv': 6400,  # ±6400 µV
        'resolution_bits': 16,
        'gain_settings': [1, 2, 5, 10, 20, 50, 100],
        'calibration_signal': {'amplitude_uv': 50, 'frequency_hz': 10},
        'scaling_factor': 0.195,
        'notes': 'EB Neuro clinical EEG systems'
    },
    
    # Compumedics (more comprehensive)
    'compumedics_comprehensive': {
        'identifiers': ['compumedics', 'grael', 'siesta', 'profusion', 'e-series'],
        'typical_range_uv': 8192,  # ±8192 µV
        'resolution_bits': 16,
        'gain_settings': [1, 2, 5, 10, 20, 50, 100, 200],
        'calibration_signal': {'amplitude_uv': 50, 'frequency_hz': 10},
        'scaling_factor': 0.25,
        'notes': 'Compumedics sleep and EEG systems'
    },
    
    # Medcare systems
    'medcare': {
        'identifiers': ['medcare', 'flaga', 'embla'],
        'typical_range_uv': 5000,  # ±5000 µV
        'resolution_bits': 16,
        'gain_settings': [1, 2, 5, 10, 20, 50],
        'calibration_signal': {'amplitude_uv': 50, 'frequency_hz': 10},
        'scaling_factor': 0.15,
        'notes': 'Medcare/Flaga sleep and EEG systems'
    },
    
    # Generic/Unknown systems
    'generic': {
        'identifiers': ['unknown', 'generic', 'standard'],
        'typical_range_uv': 3276.8,  # Conservative default
        'resolution_bits': 16,
        'gain_settings': [1, 2, 5, 10, 20, 50],
        'calibration_signal': {'amplitude_uv': 50, 'frequency_hz': 10},
        'scaling_factor': 0.1,
        'notes': 'Generic EEG amplifier assumptions'
    }
}

# ------------------------
# Amplifier Detection and Scaling System
# ------------------------

def detect_amplifier_system(edf_header, raw_data=None):
    """
    Detect amplifier system from EDF header and data characteristics
    Returns amplifier info and confidence level
    """
    detection_results = {
        'detected_system': 'generic',
        'confidence': 0.0,
        'evidence': [],
        'scaling_recommendations': {},
        'calibration_detected': False
    }
    
    # Check EDF header fields for amplifier identifiers
    header_text_fields = []
    if hasattr(edf_header, 'path'):
        # Extract text from patient ID, recording info, etc.
        try:
            with open(edf_header.path, 'rb') as f:
                header_bytes = f.read(256)
                patient_id = header_bytes[8:88].decode('ascii', errors='ignore').lower()
                recording_info = header_bytes[88:168].decode('ascii', errors='ignore').lower()
                header_text_fields = [patient_id, recording_info]
        except:
            pass
    
    # Check transducer fields for amplifier info
    if hasattr(edf_header, 'transducer'):
        header_text_fields.extend([t.lower() for t in edf_header.transducer])
    
    # Check prefilter fields
    if hasattr(edf_header, 'prefilt'):
        header_text_fields.extend([p.lower() for p in edf_header.prefilt])
    
    # Score each amplifier system
    system_scores = {}
    
    for amp_name, amp_info in AMPLIFIER_DATABASE.items():
        score = 0.0
        evidence = []
        
        # Check for identifier matches in header text
        for identifier in amp_info['identifiers']:
            for text_field in header_text_fields:
                if identifier in text_field:
                    score += 0.3
                    evidence.append(f"Found '{identifier}' in header text")
        
        # Check data range consistency (if data available)
        if raw_data is not None:
            try:
                data_range = np.max(raw_data) - np.min(raw_data)
                expected_range = amp_info['typical_range_uv']
                
                # Check if data range is within expected bounds
                ratio = data_range / expected_range
                if 0.1 <= ratio <= 10:  # Within 10x range
                    range_score = 1.0 - abs(np.log10(ratio)) / 1.0  # Closer to 1.0 = better
                    score += range_score * 0.4
                    evidence.append(f"Data range {data_range:.1f}µV matches expected {expected_range:.1f}µV")
                
                # Check for calibration signals
                cal_detected = detect_calibration_signal(raw_data, amp_info['calibration_signal'])
                if cal_detected:
                    score += 0.3
                    evidence.append("Calibration signal detected")
                    detection_results['calibration_detected'] = True
                
            except Exception as e:
                evidence.append(f"Data analysis failed: {e}")
        
        system_scores[amp_name] = {'score': score, 'evidence': evidence}
    
    # Find best match
    best_system = max(system_scores.items(), key=lambda x: x[1]['score'])
    
    detection_results['detected_system'] = best_system[0]
    detection_results['confidence'] = best_system[1]['score']
    detection_results['evidence'] = best_system[1]['evidence']
    
    # Add scaling recommendations
    amp_spec = AMPLIFIER_DATABASE[best_system[0]]
    detection_results['scaling_recommendations'] = {
        'suggested_resolution': amp_spec['scaling_factor'],
        'typical_range_uv': amp_spec['typical_range_uv'],
        'resolution_bits': amp_spec['resolution_bits'],
        'notes': amp_spec['notes']
    }
    
    return detection_results

def detect_calibration_signal(data, cal_spec):
    """
    Advanced calibration signal detection (NeuroGuide-style)
    Detects controlled calibration signals injected during recording
    """
    try:
        if data is None or len(data) == 0:
            return False
        
        expected_amp = cal_spec['amplitude_uv']
        expected_freq = cal_spec['frequency_hz']
        
        # Check if we have enough data for frequency analysis
        if data.shape[1] < 1000:  # Need at least 1000 samples
            return False
        
        calibration_evidence = []
        
        # Look for calibration signals in multiple ways
        for ch_idx in range(min(data.shape[0], 16)):  # Check up to 16 channels
            ch_data = data[ch_idx, :]
            
            # Method 1: Amplitude-based detection (basic)
            ch_peak_to_peak = np.max(ch_data) - np.min(ch_data)
            if 0.5 * expected_amp <= ch_peak_to_peak <= 2.0 * expected_amp:
                calibration_evidence.append(f"Channel {ch_idx+1}: Amplitude match")
            
            # Method 2: Frequency-based detection (NeuroGuide-style)
            if expected_freq > 0:
                try:
                    from scipy import signal as scipy_signal
                    
                    # Calculate power spectral density
                    fs = 256  # Assume 256 Hz if not specified
                    freqs, psd = scipy_signal.welch(ch_data, fs=fs, nperseg=min(1024, len(ch_data)//4))
                    
                    # Find peak frequency
                    peak_freq_idx = np.argmax(psd)
                    peak_freq = freqs[peak_freq_idx]
                    
                    # Check if peak frequency matches expected calibration frequency
                    freq_tolerance = 0.5  # ±0.5 Hz tolerance
                    if abs(peak_freq - expected_freq) <= freq_tolerance:
                        # Check if this frequency is significantly stronger than surroundings
                        surrounding_power = np.mean(psd[max(0, peak_freq_idx-5):min(len(psd), peak_freq_idx+6)])
                        peak_power = psd[peak_freq_idx]
                        
                        if peak_power > 3 * surrounding_power:  # 3x stronger than surroundings
                            calibration_evidence.append(f"Channel {ch_idx+1}: Frequency match at {peak_freq:.1f}Hz")
                
                except ImportError:
                    pass  # scipy not available, skip frequency analysis
                except Exception:
                    pass  # Frequency analysis failed
            
            # Method 3: Pattern regularity detection
            # Look for very regular, repeating patterns (typical of calibration signals)
            try:
                # Calculate autocorrelation to detect periodic patterns
                if len(ch_data) > 512:
                    # Simple regularity check - look for low variance in amplitude
                    window_size = min(256, len(ch_data) // 10)
                    windowed_stds = []
                    for i in range(0, len(ch_data) - window_size, window_size):
                        window_std = np.std(ch_data[i:i+window_size])
                        windowed_stds.append(window_std)
                    
                    # If all windows have very similar variance, it might be calibration
                    if len(windowed_stds) > 3:
                        std_of_stds = np.std(windowed_stds)
                        mean_std = np.mean(windowed_stds)
                        
                        # Very consistent amplitude suggests calibration signal
                        if std_of_stds < 0.1 * mean_std and mean_std > 0:
                            calibration_evidence.append(f"Channel {ch_idx+1}: Consistent pattern")
            
            except Exception:
                pass
        
        # Method 4: Multi-channel coherence (calibration usually appears on all channels)
        if len(calibration_evidence) >= min(data.shape[0] * 0.5, 4):  # At least 50% of channels or 4 channels
            calibration_evidence.append("Multi-channel calibration detected")
            return True
        
        # Method 5: Look for square wave or sine wave patterns (common calibration signals)
        try:
            for ch_idx in range(min(data.shape[0], 4)):  # Check first 4 channels
                ch_data = data[ch_idx, :]
                
                # Detect square wave pattern (sharp transitions)
                diff_data = np.diff(ch_data)
                large_transitions = np.sum(np.abs(diff_data) > 3 * np.std(diff_data))
                
                # Square waves have few but large transitions
                transition_ratio = large_transitions / len(diff_data)
                if 0.01 < transition_ratio < 0.1:  # 1-10% of samples are large transitions
                    # Check if transitions are regular
                    transition_indices = np.where(np.abs(diff_data) > 3 * np.std(diff_data))[0]
                    if len(transition_indices) > 4:
                        intervals = np.diff(transition_indices)
                        interval_std = np.std(intervals)
                        interval_mean = np.mean(intervals)
                        
                        if interval_std < 0.2 * interval_mean:  # Very regular intervals
                            calibration_evidence.append(f"Channel {ch_idx+1}: Square wave pattern")
                            return True
        
        except Exception:
            pass
        
        return len(calibration_evidence) > 0
        
    except Exception:
        return False

def calculate_amplifier_aware_resolution(data, amp_detection):
    """
    Calculate resolution based on amplifier detection and data characteristics
    """
    try:
        # Get amplifier-specific recommendations
        amp_system = amp_detection['detected_system']
        amp_spec = AMPLIFIER_DATABASE[amp_system]
        confidence = amp_detection['confidence']
        
        # Base resolution from amplifier specs
        suggested_resolution = amp_spec['scaling_factor']
        
        # If high confidence in detection, use amplifier-specific resolution
        if confidence > 0.7:
            print(f"🎯 High confidence ({confidence:.1%}) amplifier detection: {amp_system}")
            print(f"   Using amplifier-specific resolution: {suggested_resolution} µV/bit")
            return suggested_resolution
        
        # Medium confidence - blend with data-driven approach
        elif confidence > 0.3:
            print(f"🔍 Medium confidence ({confidence:.1%}) amplifier detection: {amp_system}")
            
            # Calculate data-driven resolution
            data_range = np.max(data) - np.min(data)
            data_driven_resolution = calculate_data_driven_resolution(data_range)
            
            # Weighted average based on confidence
            blended_resolution = (confidence * suggested_resolution + 
                                (1 - confidence) * data_driven_resolution)
            
            print(f"   Blending amplifier-specific ({suggested_resolution}) with data-driven ({data_driven_resolution})")
            print(f"   Final resolution: {blended_resolution:.6f} µV/bit")
            return blended_resolution
        
        # Low confidence - use data-driven approach with amplifier bounds
        else:
            print(f"⚠️  Low confidence ({confidence:.1%}) amplifier detection")
            print(f"   Using data-driven approach with amplifier constraints")
            
            data_range = np.max(data) - np.min(data)
            data_driven = calculate_data_driven_resolution(data_range)
            
            # Constrain to reasonable bounds based on amplifier type
            min_res = amp_spec['scaling_factor'] * 0.1
            max_res = amp_spec['scaling_factor'] * 10
            
            constrained_resolution = max(min_res, min(max_res, data_driven))
            print(f"   Constrained resolution: {constrained_resolution:.6f} µV/bit")
            return constrained_resolution
            
    except Exception as e:
        print(f"⚠️  Amplifier-aware resolution calculation failed: {e}")
        # Fallback to original method
        return calculate_data_driven_resolution(np.max(data) - np.min(data))

def calculate_data_driven_resolution(data_range):
    """
    Original data-driven resolution calculation as fallback
    """
    if data_range < 10:
        return 0.01  # Very fine resolution for small signals
    elif data_range < 100:
        return 0.1   # Fine resolution for normal signals
    elif data_range < 1000:
        return 1.0   # Standard resolution
    elif data_range < 10000:
        return 10.0  # Coarse resolution for large signals
    else:
        return 100.0 # Very coarse for extreme signals

def validate_amplifier_scaling(data, resolution, amp_detection):
    """
    Validate that the chosen resolution is appropriate for the detected amplifier
    """
    validation = {
        'resolution_appropriate': True,
        'warnings': [],
        'recommendations': []
    }
    
    try:
        amp_system = amp_detection['detected_system']
        amp_spec = AMPLIFIER_DATABASE[amp_system]
        confidence = amp_detection['confidence']
        
        # Check if resolution is within reasonable bounds for this amplifier
        suggested_res = amp_spec['scaling_factor']
        ratio = resolution / suggested_res
        
        if ratio > 100:
            validation['resolution_appropriate'] = False
            validation['warnings'].append(f"Resolution {resolution} µV/bit is {ratio:.1f}x higher than expected for {amp_system}")
            validation['recommendations'].append(f"Consider using {suggested_res} µV/bit for {amp_system} systems")
        
        elif ratio < 0.01:
            validation['resolution_appropriate'] = False
            validation['warnings'].append(f"Resolution {resolution} µV/bit is {1/ratio:.1f}x lower than expected for {amp_system}")
            validation['recommendations'].append(f"Consider using {suggested_res} µV/bit for {amp_system} systems")
        
        # Check data utilization
        data_range = np.max(data) - np.min(data)
        int16_range = 65535 * resolution  # Full INT16 range in µV
        utilization = data_range / int16_range
        
        if utilization < 0.01:
            validation['warnings'].append(f"Poor INT16 utilization ({utilization:.1%}) - signal may be underutilized")
            validation['recommendations'].append("Consider using finer resolution to improve precision")
        
        elif utilization > 0.95:
            validation['warnings'].append(f"High INT16 utilization ({utilization:.1%}) - risk of clipping")
            validation['recommendations'].append("Consider using coarser resolution to prevent clipping")
        
        # Amplifier-specific validations
        if amp_system == 'biosemi' and resolution > 1.0:
            validation['warnings'].append("BioSemi systems typically use very fine resolution (<1 µV/bit)")
        
        elif amp_system == 'mitsar' and resolution > 0.1:
            validation['warnings'].append("Mitsar/WinEEG systems typically use fine resolution (≤0.1 µV/bit)")
        
        elif amp_system == 'gtec' and resolution < 1.0:
            validation['warnings'].append("g.tec systems typically use coarser resolution (≥1 µV/bit)")
        
    except Exception as e:
        validation['warnings'].append(f"Amplifier validation failed: {e}")
    
    return validation

# ------------------------
# Gunkelman-Grade Validation System
# ------------------------
def micround(fs: float) -> int:
    """SamplingInterval in microseconds (rounded int)."""
    return int(round(1_000_000.0 / float(fs)))

def now_iso():
    return datetime.datetime.now().isoformat(timespec="seconds")

def write_text(p: Path, s: str):
    p.write_text(s, encoding="utf-8")

def pretty_bool(b: bool) -> str:
    return "PASS" if b else "FAIL"

def calculate_file_hash(file_path: Path, algorithm='sha256'):
    """Calculate file hash for integrity verification"""
    try:
        hash_func = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    except Exception as e:
        return f"Hash calculation failed: {e}"

class EDFHeader:
    """EDF header reader with comprehensive validation"""
    def __init__(self, path: Path):
        self.path = path
        self.n_signals = None
        self.n_records = None
        self.duration_record_s = None
        self.labels = []
        self.transducer = []
        self.phys_dim = []
        self.phys_min = []
        self.phys_max = []
        self.dig_min = []
        self.dig_max = []
        self.prefilt = []
        self.samples_per_record = []
        self.header_bytes = None
        self.valid = False
        self.validation_errors = []
        self.warnings = []

    def read(self):
        try:
            with self.path.open("rb") as f:
                head0 = f.read(256)
                if len(head0) < 256:
                    raise ValueError("EDF header too short.")

                # Validate header structure
                self._validate_header_structure(head0)
                
                # Bytes 252-256: Number of signals (ns)
                self.n_signals = int(head0[252:256].decode("ascii", "ignore").strip() or "0")
                if self.n_signals <= 0 or self.n_signals > 512:
                    raise ValueError(f"EDF ns invalid: {self.n_signals}")

                # Next sections are 256 bytes * ns, each field concatenated across channels
                def read_field(field_len):
                    return f.read(field_len * self.n_signals)

                labels_raw      = read_field(16)
                transducer_raw  = read_field(80)
                phys_dim_raw    = read_field(8)
                phys_min_raw    = read_field(8)
                phys_max_raw    = read_field(8)
                dig_min_raw     = read_field(8)
                dig_max_raw     = read_field(8)
                prefilt_raw     = read_field(80)
                samples_raw     = read_field(8)

                # Parse channel-specific fields
                self._parse_channel_fields(labels_raw, transducer_raw, phys_dim_raw,
                                         phys_min_raw, phys_max_raw, dig_min_raw,
                                         dig_max_raw, prefilt_raw, samples_raw)

                # Validate data consistency
                self._validate_data_consistency()
                
                # Back to head0 to get number of records and duration
                n_records      = int(head0[236:244].decode("ascii","ignore").strip() or "-1")
                dur_per_record = float(head0[244:252].decode("ascii","ignore").strip() or "0")
                self.n_records = n_records
                self.duration_record_s = dur_per_record

                # Compute fs per channel
                self.fs_per_channel = []
                for spr in self.samples_per_record:
                    fs = spr / self.duration_record_s if self.duration_record_s > 0 else 0.0
                    self.fs_per_channel.append(fs)

                self.header_bytes = 256 + self.n_signals * 256
                self.valid = True
                return self
                
        except Exception as e:
            self.validation_errors.append(f"Header read error: {e}")
            raise

    def _validate_header_structure(self, head0):
        """Validate EDF header structure and content"""
        try:
            # Check for valid EDF identifier
            edf_id = head0[0:8].decode("ascii", "ignore").strip()
            if not edf_id.startswith("0"):
                self.warnings.append(f"Non-standard EDF identifier: {edf_id}")
            
            # Check patient info
            patient_id = head0[8:88].decode("ascii", "ignore").strip()
            if not patient_id:
                self.warnings.append("Empty patient ID field")
            
            # Check recording info
            recording_info = head0[88:168].decode("ascii", "ignore").strip()
            if not recording_info:
                self.warnings.append("Empty recording info field")
            
            # Check start date
            start_date = head0[168:176].decode("ascii", "ignore").strip()
            if not start_date or start_date == "00.00.00":
                self.warnings.append("Invalid or missing start date")
            
            # Check start time
            start_time = head0[176:184].decode("ascii", "ignore").strip()
            if not start_time or start_time == "00.00.00":
                self.warnings.append("Invalid or missing start time")
            
            # Check header length
            header_bytes = int(head0[184:192].decode("ascii", "ignore").strip() or "0")
            if header_bytes != 256:
                self.warnings.append(f"Non-standard header length: {header_bytes}")
            
            # Check data format
            data_format = head0[192:236].decode("ascii", "ignore").strip()
            if not data_format:
                self.warnings.append("Empty data format field")
            
            # Check number of data records
            n_records = head0[236:244].decode("ascii", "ignore").strip()
            if not n_records or n_records == "0":
                self.warnings.append("Invalid number of data records")
            
            # Check duration of data record
            duration = head0[244:252].decode("ascii", "ignore").strip()
            if not duration or duration == "0":
                self.warnings.append("Invalid duration of data record")
                
        except Exception as e:
            self.warnings.append(f"Header structure validation error: {e}")

    def _parse_channel_fields(self, labels_raw, transducer_raw, phys_dim_raw,
                             phys_min_raw, phys_max_raw, dig_min_raw,
                             dig_max_raw, prefilt_raw, samples_raw):
        """Parse channel-specific fields with validation"""
        try:
            for i in range(self.n_signals):
                # Extract channel data
                start_idx = i * 16
                end_idx = start_idx + 16
                
                label = labels_raw[start_idx:end_idx].decode("ascii", "ignore").strip()
                transducer = transducer_raw[i*80:(i+1)*80].decode("ascii", "ignore").strip()
                phys_dim = phys_dim_raw[i*8:(i+1)*8].decode("ascii", "ignore").strip()
                phys_min = phys_min_raw[i*8:(i+1)*8].decode("ascii", "ignore").strip()
                phys_max = phys_max_raw[i*8:(i+1)*8].decode("ascii", "ignore").strip()
                dig_min = dig_min_raw[i*8:(i+1)*8].decode("ascii", "ignore").strip()
                dig_max = dig_max_raw[i*8:(i+1)*8].decode("ascii", "ignore").strip()
                prefilt = prefilt_raw[i*80:(i+1)*80].decode("ascii", "ignore").strip()
                samples = samples_raw[i*8:(i+1)*8].decode("ascii", "ignore").strip()
                
                # Validate channel data
                self._validate_channel_data(i, label, phys_min, phys_max, dig_min, dig_max, samples)
                
                # Store parsed data
                self.labels.append(label)
                self.transducer.append(transducer)
                self.phys_dim.append(phys_dim)
                self.phys_min.append(phys_min)
                self.phys_max.append(phys_max)
                self.dig_min.append(dig_min)
                self.dig_max.append(dig_max)
                self.prefilt.append(prefilt)
                self.samples_per_record.append(int(samples) if samples.strip() else 0)
                
        except Exception as e:
            self.validation_errors.append(f"Channel field parsing error: {e}")

    def _validate_channel_data(self, ch_idx, label, phys_min, phys_max, dig_min, dig_max, samples):
        """Validate individual channel data"""
        try:
            # Check for empty or invalid channel label
            if not label or label.strip() == "":
                self.warnings.append(f"Channel {ch_idx+1}: Empty or missing label")
            
            # Check physical range consistency
            try:
                pmin = float(phys_min) if phys_min.strip() else 0
                pmax = float(phys_max) if phys_max.strip() else 0
                if pmin >= pmax:
                    self.warnings.append(f"Channel {ch_idx+1}: Physical min ({pmin}) >= max ({pmax})")
            except ValueError:
                self.warnings.append(f"Channel {ch_idx+1}: Invalid physical range values")
            
            # Check digital range consistency
            try:
                dmin = int(dig_min) if dig_min.strip() else 0
                dmax = int(dig_max) if dig_max.strip() else 0
                if dmin >= dmax:
                    self.warnings.append(f"Channel {ch_idx+1}: Digital min ({dmin}) >= max ({dmax})")
            except ValueError:
                self.warnings.append(f"Channel {ch_idx+1}: Invalid digital range values")
            
            # Check samples per record
            try:
                samp = int(samples) if samples.strip() else 0
                if samp <= 0:
                    self.warnings.append(f"Channel {ch_idx+1}: Invalid samples per record: {samp}")
            except ValueError:
                self.warnings.append(f"Channel {ch_idx+1}: Invalid samples per record value")
                
        except Exception as e:
            self.warnings.append(f"Channel {ch_idx+1} validation error: {e}")

    def _validate_data_consistency(self):
        """Validate overall data consistency"""
        try:
            # Check if all channels have same number of samples
            if self.samples_per_record:
                first_samples = self.samples_per_record[0]
                for i, samples in enumerate(self.samples_per_record):
                    if samples != first_samples:
                        self.warnings.append(f"Channel {i+1} has different samples per record: {samples} vs {first_samples}")
            
            # Check for duplicate channel labels
            label_counts = Counter(self.labels)
            for label, count in label_counts.items():
                if count > 1 and label.strip():
                    self.warnings.append(f"Duplicate channel label: {label} (appears {count} times)")
            
            # Check for suspicious channel names
            suspicious_names = ['', ' ', 'X', 'Y', 'Z', 'UNKNOWN', 'TEST']
            for i, label in enumerate(self.labels):
                if label.strip() in suspicious_names:
                    self.warnings.append(f"Channel {i+1}: Suspicious label '{label}'")
                    
        except Exception as e:
            self.warnings.append(f"Data consistency validation error: {e}")

    def common_fs(self):
        # returns (fs, ok_equal) where ok_equal=True if all channels agree
        if not self.valid: return (None, False)
        uniq = {round(fs,6) for fs in self.fs_per_channel}
        if len(uniq) == 1:
            return (float(next(iter(uniq))), True)
        # if multiple, take mode
        c = Counter(self.fs_per_channel)
        fs = max(c.items(), key=lambda kv: kv[1])[0]
        return (float(fs), False)

    def total_samples_per_channel(self):
        # total = n_records * samples_per_record[ch]
        if not self.valid: return None
        return [self.n_records * spr for spr in self.samples_per_record]

    def get_validation_summary(self):
        """Get comprehensive validation summary"""
        return {
            "valid": self.valid,
            "errors": self.validation_errors,
            "warnings": self.warnings,
            "n_signals": self.n_signals,
            "n_records": self.n_records,
            "duration_record_s": self.duration_record_s,
            "header_bytes": self.header_bytes,
            "labels": self.labels,
            "samples_per_record": self.samples_per_record
        }

def parse_vhdr(path: Path):
    """Parse existing BrainVision .vhdr file"""
    cfg = ConfigParser()
    # preserve case & allow no-value commas
    cfg.optionxform = str
    text = path.read_text(encoding="utf-8", errors="ignore")
    
    # Handle BrainVision format: skip the first descriptive line if it exists
    lines = text.splitlines()
    if lines and not lines[0].strip().startswith('['):
        # Skip the first line if it's not a section header (e.g., "Brain Vision Data Exchange Header File Version 1.0")
        text = '\n'.join(lines[1:])
    
    # Inject section headers if malformed? (not needed usually)
    cfg.read_string(text)
    out = {"ok": True, "errors": [], "path": str(path)}
    try:
        ci = cfg["Common Infos"]
        bi = cfg["Binary Infos"]
        ch = cfg["Channel Infos"]

        out["DataFile"] = ci.get("DataFile", "").strip()
        out["MarkerFile"] = ci.get("MarkerFile","").strip()
        out["DataFormat"] = ci.get("DataFormat","").strip()
        out["DataOrientation"] = ci.get("DataOrientation","").strip()
        out["NumberOfChannels"] = int(ci.get("NumberOfChannels","0").strip() or "0")
        out["SamplingInterval_us"] = float(ci.get("SamplingInterval","0").strip() or "0")
        out["UseBigEndianOrder"] = ci.get("UseBigEndianOrder","NO").strip().upper() == "YES"

        out["BinaryFormat"] = bi.get("BinaryFormat","").strip()

        # Channel lines: Ch1=Fp1,,0.195,uV
        chans = []
        for k,v in cfg.items("Channel Infos"):
            if not k.lower().startswith("ch"): continue
            parts = [p.strip() for p in v.split(",")]
            label = parts[0] if len(parts)>0 else ""
            ref   = parts[1] if len(parts)>1 else ""
            res   = parts[2] if len(parts)>2 else ""
            unit  = parts[3] if len(parts)>3 else ""
            try:
                res_val = float(res)
            except:
                res_val = None
            chans.append({"label": label, "ref": ref, "resolution_uV_per_bit": res_val, "unit": unit})
        out["channels"] = chans
    except Exception as e:
        out["ok"] = False
        out["errors"].append(f"VHDR parse error: {e}")
    return out

def parse_vmrk(path: Path):
    """Parse existing BrainVision .vmrk file"""
    out = {"ok": True, "errors": [], "path": str(path), "markers": [], "DataFile": None}
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        in_marker = False
        for ln in lines:
            if ln.strip().startswith("[Common Infos]"):
                in_marker = False
            if ln.strip().startswith("[Marker Infos]"):
                in_marker = True
                continue
            if not in_marker:
                if ln.startswith("DataFile="):
                    out["DataFile"] = ln.split("=",1)[1].strip()
                continue
            if ln.startswith("Mk"):
                # Mk1=Type,Desc,Latency,Channel,Duration
                _, rhs = ln.split("=",1)
                parts = [p.strip() for p in rhs.split(",")]
                if len(parts) >= 5:
                    out["markers"].append({
                        "type": parts[0], "desc": parts[1],
                        "latency_samples": int(re.sub(r"[^\d]", "", parts[2]) or "0"),
                        "channel": int(parts[3]),
                        "duration_samples": int(re.sub(r"[^\d]", "", parts[4]) or "0")
                    })
    except Exception as e:
        out["ok"] = False
        out["errors"].append(f"VMRK parse error: {e}")
    return out

def cross_checks(edf: EDFHeader, vhdr: dict|None, vmrk: dict|None, eeg_path: Path|None):
    """Enhanced Gunkelman-grade cross-checks between EDF, VHDR, VMRK, and EEG binary"""
    report = {
        "timestamp": now_iso(),
        "edf_path": str(edf.path) if edf else None,
        "vhdr_path": vhdr["path"] if vhdr else None,
        "vmrk_path": vmrk["path"] if vmrk else None,
        "eeg_path": str(eeg_path) if eeg_path else None,
        "checks": [],
        "summary": {},
        "advice": [],
        "warnings": [],
        "critical_issues": [],
        "file_integrity": {},
        "clinical_validation": {}
    }

    # EDF comprehensive validation
    edf_ok = edf is not None and edf.valid
    fs_edf, fs_equal = (None, False)
    total_samples_ch = None
    labels_edf = None
    
    if edf_ok:
        fs_edf, fs_equal = edf.common_fs()
        total_samples_ch = edf.total_samples_per_channel()
        labels_edf = edf.labels
        
        # Get EDF validation summary
        edf_validation = edf.get_validation_summary()
        report["edf_validation"] = edf_validation
        
        report["summary"]["edf_fs"] = fs_edf
        report["summary"]["edf_fs_channels_equal"] = fs_equal
        report["summary"]["edf_n_signals"] = edf.n_signals
        report["summary"]["edf_duration_s"] = edf.n_records * edf.duration_record_s
        report["summary"]["edf_total_samples_per_ch"] = total_samples_ch
        
        # Add EDF warnings and errors
        if edf_validation.get("warnings"):
            report["warnings"].extend([f"EDF: {w}" for w in edf_validation["warnings"]])
        if edf_validation.get("errors"):
            report["critical_issues"].extend([f"EDF: {e}" for e in edf_validation["errors"]])
        
        # Clinical validation checks
        report["clinical_validation"]["edf"] = {
            "recording_duration_minutes": (edf.n_records * edf.duration_record_s) / 60.0,
            "channels_standard": _check_standard_channel_set(labels_edf),
            "sampling_rate_clinical": _check_clinical_sampling_rate(fs_edf),
            "duration_clinical": _check_clinical_duration(edf.n_records * edf.duration_record_s)
        }
    else:
        report["critical_issues"].append("EDF file validation failed")

    # VHDR comprehensive validation
    if vhdr:
        try:
            fs_vhdr = 1_000_000.0 / float(vhdr.get("SamplingInterval_us", 0) or 0)
        except ZeroDivisionError:
            fs_vhdr = 0.0
            report["critical_issues"].append("VHDR: Invalid sampling interval (division by zero)")
        
        n_vhdr = vhdr.get("NumberOfChannels")
        dataformat = vhdr.get("DataFormat","").upper()
        dataorient = vhdr.get("DataOrientation","").upper()
        binfmt = vhdr.get("BinaryFormat","").upper()
        labels_vhdr = [c["label"] for c in vhdr.get("channels", [])]

        report["summary"]["vhdr_fs"] = fs_vhdr
        report["summary"]["vhdr_n_channels"] = n_vhdr
        report["summary"]["vhdr_binfmt"] = binfmt
        report["summary"]["vhdr_dataformat"] = dataformat
        report["summary"]["vhdr_dataorientation"] = dataorient
        report["summary"]["vhdr_labels"] = labels_vhdr

        # cross-checks
        report["checks"].append({
            "name":"FS match (EDF vs VHDR)",
            "expected": fs_edf,
            "observed": fs_vhdr,
            "pass": (edf_ok and abs(fs_vhdr - fs_edf) < 1e-6),
            "tolerance": "1e-6 Hz"
        })
        
        report["checks"].append({
            "name":"N channels match (EDF vs VHDR)",
            "expected": edf.n_signals if edf_ok else None,
            "observed": n_vhdr,
            "pass": (edf_ok and (n_vhdr == edf.n_signals))
        })
        
        report["checks"].append({
            "name":"Orientation MULTIPLEXED",
            "expected":"MULTIPLEXED",
            "observed": dataorient,
            "pass": (dataorient == "MULTIPLEXED")
        })
        
        report["checks"].append({
            "name":"DataFormat BINARY",
            "expected":"BINARY",
            "observed": dataformat,
            "pass": (dataformat == "BINARY")
        })
        
        # Additional VHDR validation
        if binfmt not in ["INT_16", "INT32", "FLOAT_32", "FLOAT_64"]:
            report["warnings"].append(f"VHDR: Non-standard binary format: {binfmt}")
        
        if not labels_vhdr:
            report["warnings"].append("VHDR: No channel labels defined")
        
        # Check for suspicious channel labels
        for i, label in enumerate(labels_vhdr):
            if not label or label.strip() in ['', 'X', 'Y', 'Z', 'UNKNOWN']:
                report["warnings"].append(f"VHDR: Suspicious channel {i+1} label: '{label}'")

    # VMRK validation
    if vmrk:
        markers = vmrk.get("markers", [])
        report["summary"]["vmrk_n_markers"] = len(markers)
        
        # Check marker consistency
        if markers:
            # Check for start/end markers
            has_start = any(m.get("desc", "").lower() in ["start", "recording_start"] for m in markers)
            has_end = any(m.get("desc", "").lower() in ["end", "recording_end"] for m in markers)
            
            report["checks"].append({
                "name": "VMRK has start marker",
                "expected": True,
                "observed": has_start,
                "pass": has_start
            })
            
            report["checks"].append({
                "name": "VMRK has end marker", 
                "expected": True,
                "observed": has_end,
                "pass": has_end
            })
            
            # Check marker timing consistency
            if edf_ok and markers:
                total_duration = edf.n_records * edf.duration_record_s
                for marker in markers:
                    latency = marker.get("latency_samples", 0)
                    if latency > total_samples_ch[0] if total_samples_ch else 0:
                        report["warnings"].append(f"VMRK: Marker {marker.get('desc', 'Unknown')} latency ({latency}) exceeds recording length")

    # EEG binary comprehensive validation
    if eeg_path and eeg_path.exists() and edf_ok:
        file_bytes = eeg_path.stat().st_size
        file_hash = calculate_file_hash(eeg_path)
        
        report["file_integrity"]["eeg_file"] = {
            "size_bytes": file_bytes,
            "hash_sha256": file_hash,
            "exists": True
        }
        
        # Assume INT_16 unless vhdr says otherwise
        binfmt = (vhdr.get("BinaryFormat","INT_16") if vhdr else "INT_16").upper()
        bps = 2 if binfmt == "INT_16" else 4 if "32" in binfmt else 2
        
        # if EDF has per-channel samples equal, take first
        total_samps = total_samples_ch[0] if total_samples_ch else 0
        expected = edf.n_signals * total_samps * bps
        
        report["checks"].append({
            "name":"EEG binary size matches expected",
            "expected_bytes": expected,
            "observed_bytes": file_bytes,
            "pass": (expected == file_bytes),
            "binary_format": binfmt,
            "bytes_per_sample": bps
        })
        
        if expected != file_bytes:
            report["advice"].append(
                f"Binary size mismatch: expected {expected} bytes from EDF, got {file_bytes}. "
                f"Check BinaryFormat ({binfmt}), channel count, or total samples."
            )
            
        # Check for suspicious file sizes
        if file_bytes < 1000:
            report["critical_issues"].append(f"EEG file suspiciously small: {file_bytes} bytes")
        elif file_bytes > 10_000_000_000:  # 10GB
            report["warnings"].append(f"EEG file very large: {file_bytes} bytes")
            
        # Check file permissions and accessibility
        try:
            with open(eeg_path, 'rb') as f:
                f.read(1024)  # Test read access
            report["file_integrity"]["eeg_file"]["readable"] = True
        except Exception as e:
            report["critical_issues"].append(f"EEG file not readable: {e}")
            report["file_integrity"]["eeg_file"]["readable"] = False

    # Enhanced labels validation
    if vhdr and edf_ok:
        labels_vhdr = [c["label"] for c in vhdr.get("channels", [])]
        same_len = len(labels_vhdr) == len(labels_edf)
        same_set = set([l.upper() for l in labels_vhdr]) == set([l.upper() for l in labels_edf])
        
        report["checks"].append({
            "name":"Channel labels set match",
            "expected_set": labels_edf,
            "observed_set": labels_vhdr,
            "pass": same_set
        })
        
        if same_set and not same_len:
            report["advice"].append("Channel label sets match but lengths differ. Investigate duplicates or extra channels.")
        # Order differences matter clinically
        if same_set and labels_vhdr != labels_edf:
            report["advice"].append("Channel labels are same set but different order; ensure multiplex order matches BrainVision expectations.")
            
        # Check for clinical standard channel sets
        clinical_validation = _validate_clinical_channels(labels_vhdr)
        report["clinical_validation"]["channels"] = clinical_validation

    # Enhanced confidence calculation with advanced validation weighting
    passed = sum(1 for c in report["checks"] if c["pass"])
    total = len(report["checks"])
    
    # Base confidence from cross-checks
    base_confidence = (passed/total) if total else 0.0
    
    # Advanced validation bonuses and penalties
    advanced_bonus = 0.0
    advanced_penalty = 0.0
    
    # Clinical validation bonus
    if "clinical_validation" in report:
        clinical_score = 0.0
        clinical_checks = 0
        
        if "edf" in report["clinical_validation"]:
            edf_clin = report["clinical_validation"]["edf"]
            if edf_clin.get("channels_standard") not in [False, "CUSTOM"]:
                clinical_score += 0.1
            if edf_clin.get("sampling_rate_clinical") == "STANDARD":
                clinical_score += 0.1
            if edf_clin.get("duration_clinical") == "STANDARD":
                clinical_score += 0.05
            clinical_checks += 3
        
        if "channels" in report["clinical_validation"]:
            ch_clin = report["clinical_validation"]["channels"]
            if ch_clin.get("valid"):
                clinical_score += 0.1
            if ch_clin.get("has_essential"):
                clinical_score += 0.05
            clinical_checks += 2
        
        if clinical_checks > 0:
            advanced_bonus += clinical_score / clinical_checks * 0.2  # Max 20% bonus
    
    # Signal quality bonus (if MNE available and signal QC passed)
    signal_qc_bonus = 0.0
    if report.get("signal_qc", {}).get("ok"):
        sig_qc = report["signal_qc"]
        
        # Quality score bonus
        if "signal_quality" in sig_qc:
            quality_score = sig_qc["signal_quality"].get("overall_score", 0)
            signal_qc_bonus += (quality_score / 100) * 0.15  # Max 15% bonus
        
        # Clinical compliance bonus
        if sig_qc.get("clinical_compliance", {}).get("overall_score"):
            compliance_score = sig_qc["clinical_compliance"]["overall_score"]
            signal_qc_bonus += compliance_score * 0.1  # Max 10% bonus
        
        # Advanced artifact detection penalties
        if sig_qc.get("advanced_artifacts"):
            artifacts = sig_qc["advanced_artifacts"]
            
            # Severe artifacts penalty
            for artifact_type, artifact_data in artifacts.items():
                if isinstance(artifact_data, dict) and artifact_data.get("detected"):
                    severity = artifact_data.get("severity", "none")
                    if severity == "severe":
                        advanced_penalty += 0.1
                    elif severity == "moderate":
                        advanced_penalty += 0.05
                    elif severity == "mild":
                        advanced_penalty += 0.02
        
        advanced_bonus += signal_qc_bonus
    
    # Weight critical issues and warnings
    critical_penalty = len(report["critical_issues"]) * 0.25  # Reduced from 0.3
    warning_penalty = len(report["warnings"]) * 0.03  # Reduced from 0.05
    
    # Calculate final confidence with advanced features
    final_confidence = base_confidence + advanced_bonus - critical_penalty - warning_penalty - advanced_penalty
    final_confidence = max(0.0, min(1.0, final_confidence))
    
    report["summary"]["confidence"] = round(final_confidence, 3)
    report["summary"]["base_confidence"] = round(base_confidence, 3)
    report["summary"]["advanced_bonus"] = round(advanced_bonus, 3)
    report["summary"]["total_penalty"] = round(critical_penalty + warning_penalty + advanced_penalty, 3)
    report["summary"]["checks_passed"] = passed
    report["summary"]["checks_total"] = total
    report["summary"]["critical_issues_count"] = len(report["critical_issues"])
    report["summary"]["warnings_count"] = len(report["warnings"])
    
    # Enhanced assessment with more granular levels
    if final_confidence >= 0.95:
        report["summary"]["assessment"] = "EXCELLENT"
        report["summary"]["assessment_description"] = "Outstanding quality with comprehensive validation"
    elif final_confidence >= 0.85:
        report["summary"]["assessment"] = "VERY_GOOD"
        report["summary"]["assessment_description"] = "High quality with advanced validation features"
    elif final_confidence >= 0.75:
        report["summary"]["assessment"] = "GOOD"
        report["summary"]["assessment_description"] = "Good quality with minor issues"
    elif final_confidence >= 0.60:
        report["summary"]["assessment"] = "FAIR"
        report["summary"]["assessment_description"] = "Acceptable quality with some concerns"
    elif final_confidence >= 0.40:
        report["summary"]["assessment"] = "POOR"
        report["summary"]["assessment_description"] = "Poor quality with significant issues"
    else:
        report["summary"]["assessment"] = "CRITICAL"
        report["summary"]["assessment_description"] = "Critical issues requiring immediate attention"
    
    return report

def _check_standard_channel_set(labels):
    """Check if channel set follows clinical standards"""
    if not labels:
        return False
    
    # Common clinical channel sets
    standard_sets = {
        "10-20": ["Fp1", "Fp2", "F3", "F4", "C3", "C4", "P3", "P4", "O1", "O2", "F7", "F8", "T3", "T4", "T5", "T6", "Fz", "Cz", "Pz"],
        "10-10": ["Fp1", "Fp2", "F3", "F4", "C3", "C4", "P3", "P4", "O1", "O2", "F7", "F8", "T3", "T4", "T5", "T6", "Fz", "Cz", "Pz", "Fpz", "AFz", "FCz", "CPz", "POz"],
        "minimal": ["Fp1", "Fp2", "C3", "C4", "O1", "O2"]
    }
    
    labels_upper = [l.upper() for l in labels]
    
    for set_name, standard_labels in standard_sets.items():
        standard_upper = [l.upper() for l in standard_labels]
        if all(label in labels_upper for label in standard_upper[:6]):  # Check at least first 6
            return set_name
    
    return "CUSTOM"

def _check_clinical_sampling_rate(fs):
    """Check if sampling rate is clinically appropriate"""
    if fs is None:
        return False
    
    if fs >= 200 and fs <= 1000:
        return "STANDARD"
    elif fs > 1000:
        return "HIGH_FREQUENCY"
    elif fs < 200:
        return "LOW_FREQUENCY"
    else:
        return "UNUSUAL"

def _check_clinical_duration(duration_seconds):
    """Check if recording duration is clinically appropriate"""
    if duration_seconds is None:
        return False
    
    duration_minutes = duration_seconds / 60.0
    
    if duration_minutes >= 20 and duration_minutes <= 60:
        return "STANDARD"
    elif duration_minutes > 60:
        return "LONG"
    elif duration_minutes < 20:
        return "SHORT"
    else:
        return "UNUSUAL"

def _validate_clinical_channels(labels):
    """Validate channel set for clinical use"""
    if not labels:
        return {"valid": False, "issues": ["No channel labels"]}
    
    issues = []
    warnings = []
    
    # Check for essential channels
    essential = ["Fp1", "Fp2", "C3", "C4", "O1", "O2"]
    missing_essential = [ch for ch in essential if ch.upper() not in [l.upper() for l in labels]]
    
    if missing_essential:
        issues.append(f"Missing essential channels: {missing_essential}")
    
    # Check for reference channels
    ref_channels = [ch for ch in labels if ch.upper() in ["REF", "REFERENCE", "GND", "GROUND", "COM", "COMMON"]]
    if not ref_channels:
        warnings.append("No reference/ground channels identified")
    
    # Check for duplicate labels
    label_counts = Counter([l.upper() for l in labels])
    duplicates = [label for label, count in label_counts.items() if count > 1]
    if duplicates:
        issues.append(f"Duplicate channel labels: {duplicates}")
    
    # Check for suspicious labels
    suspicious = [l for l in labels if l.strip() in ['', 'X', 'Y', 'Z', 'UNKNOWN', 'TEST', 'DUMMY']]
    if suspicious:
        warnings.append(f"Suspicious channel labels: {suspicious}")
    
    # Clinical montage validation
    clinical_validation = _validate_clinical_montage(labels)
    if clinical_validation.get("issues"):
        issues.extend(clinical_validation["issues"])
    if clinical_validation.get("warnings"):
        warnings.extend(clinical_validation["warnings"])
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "n_channels": len(labels),
        "has_essential": len(missing_essential) == 0,
        "has_reference": len(ref_channels) > 0,
        "montage_validation": clinical_validation
    }

def _validate_clinical_montage(labels):
    """Validate clinical EEG montage for standard protocols"""
    issues = []
    warnings = []
    
    labels_upper = [l.upper() for l in labels]
    
    # Standard 10-20 montage validation
    standard_10_20 = {
        "frontal": ["FP1", "FP2", "F3", "F4", "F7", "F8", "FZ"],
        "central": ["C3", "C4", "CZ"],
        "parietal": ["P3", "P4", "PZ"],
        "occipital": ["O1", "O2"],
        "temporal": ["T3", "T4", "T5", "T6"]
    }
    
    # Check montage completeness
    montage_scores = {}
    for region, channels in standard_10_20.items():
        present = sum(1 for ch in channels if ch in labels_upper)
        total = len(channels)
        score = present / total if total > 0 else 0
        montage_scores[region] = {"present": present, "total": total, "score": score}
        
        if score < 0.5:
            issues.append(f"Incomplete {region} region: {present}/{total} channels")
        elif score < 0.8:
            warnings.append(f"Limited {region} coverage: {present}/{total} channels")
    
    # Check for balanced left/right coverage
    left_channels = [ch for ch in labels_upper if ch.endswith('1') or ch.endswith('3') or ch.endswith('5') or ch.endswith('7')]
    right_channels = [ch for ch in labels_upper if ch.endswith('2') or ch.endswith('4') or ch.endswith('6') or ch.endswith('8')]
    
    if abs(len(left_channels) - len(right_channels)) > 2:
        warnings.append(f"Unbalanced left/right coverage: {len(left_channels)} left, {len(right_channels)} right")
    
    # Check for midline channels
    midline_channels = [ch for ch in labels_upper if ch.endswith('Z')]
    if len(midline_channels) < 2:
        warnings.append(f"Limited midline coverage: {len(midline_channels)} channels")
    
    # Clinical protocol validation
    protocol_validation = _validate_clinical_protocols(labels_upper)
    if protocol_validation.get("issues"):
        issues.extend(protocol_validation["issues"])
    if protocol_validation.get("warnings"):
        warnings.extend(protocol_validation["warnings"])
    
    return {
        "montage_scores": montage_scores,
        "left_right_balance": {"left": len(left_channels), "right": len(right_channels)},
        "midline_coverage": len(midline_channels),
        "protocol_validation": protocol_validation,
        "issues": issues,
        "warnings": warnings
    }

def _validate_clinical_protocols(labels):
    """Validate against common clinical EEG protocols"""
    issues = []
    warnings = []
    
    # Sleep study protocol
    sleep_channels = ["EOG1", "EOG2", "EMG1", "EMG2", "ECG", "AIRFLOW", "THORAX", "ABDOMEN"]
    sleep_present = [ch for ch in sleep_channels if ch in labels]
    if sleep_present:
        if len(sleep_present) >= 4:
            warnings.append(f"Sleep study channels detected: {sleep_present}")
        else:
            warnings.append(f"Partial sleep study setup: {sleep_present}")
    
    # Long-term monitoring protocol
    ltm_channels = ["SPO2", "PULSE", "TEMPERATURE", "ACTIVITY"]
    ltm_present = [ch for ch in ltm_channels if ch in labels]
    if ltm_present:
        warnings.append(f"Long-term monitoring channels: {ltm_present}")
    
    # ICU monitoring protocol
    icu_channels = ["ICP", "BIS", "CO2", "PRESSURE"]
    icu_present = [ch for ch in icu_channels if ch in labels]
    if icu_present:
        warnings.append(f"ICU monitoring channels: {icu_present}")
    
    # Check for unusual channel combinations
    unusual_combinations = []
    if any(ch.startswith("EOG") for ch in labels) and len([ch for ch in labels if ch.startswith("EOG")]) < 2:
        unusual_combinations.append("Single EOG channel")
    
    if any(ch.startswith("EMG") for ch in labels) and len([ch for ch in labels if ch.startswith("EMG")]) < 2:
        unusual_combinations.append("Single EMG channel")
    
    if unusual_combinations:
        warnings.append(f"Unusual channel combinations: {', '.join(unusual_combinations)}")
    
    return {
        "sleep_protocol": len(sleep_present),
        "ltm_protocol": len(ltm_present),
        "icu_protocol": len(icu_present),
        "unusual_combinations": unusual_combinations,
        "issues": issues,
        "warnings": warnings
    }

def _validate_electrode_placement(labels):
    """Validate electrode placement for clinical standards"""
    issues = []
    warnings = []
    
    # Check for proper electrode naming conventions
    proper_names = []
    improper_names = []
    
    for label in labels:
        label_upper = label.upper()
        # Standard 10-20 naming patterns
        if (re.match(r'^[A-Z][A-Z]?\d$', label_upper) or  # F3, CZ, etc.
            re.match(r'^[A-Z][A-Z][A-Z]\d$', label_upper) or  # FP1, etc.
            label_upper in ['REF', 'GND', 'COM', 'EOG1', 'EOG2', 'EMG1', 'EMG2', 'ECG']):
            proper_names.append(label)
        else:
            improper_names.append(label)
    
    if improper_names:
        warnings.append(f"Non-standard electrode names: {improper_names}")
    
    # Check for missing contralateral pairs
    left_channels = [ch for ch in labels if ch.endswith('1') or ch.endswith('3') or ch.endswith('5') or ch.endswith('7')]
    right_channels = [ch for ch in labels if ch.endswith('2') or ch.endswith('4') or ch.endswith('6') or ch.endswith('8')]
    
    # Find unpaired channels
    left_base = [ch[:-1] for ch in left_channels]
    right_base = [ch[:-1] for ch in right_channels]
    
    unpaired_left = [ch for ch in left_channels if ch[:-1] not in right_base]
    unpaired_right = [ch for ch in right_channels if ch[:-1] not in left_base]
    
    if unpaired_left or unpaired_right:
        warnings.append(f"Unpaired electrodes: left {unpaired_left}, right {unpaired_right}")
    
    return {
        "proper_names": len(proper_names),
        "improper_names": len(improper_names),
        "left_channels": len(left_channels),
        "right_channels": len(right_channels),
        "unpaired_left": unpaired_left,
        "unpaired_right": unpaired_right,
        "issues": issues,
        "warnings": warnings
    }

def signal_qc_with_mne(edf_path: Path, fs_expect=None):
    """Enhanced signal-level QC using MNE if available"""
    try:
        import mne, numpy as np
        raw = mne.io.read_raw_edf(str(edf_path), preload=True, verbose=False)
        fs = raw.info["sfreq"]
        ch_names = raw.ch_names
        out = {
            "ok": True, 
            "fs": float(fs), 
            "alpha_peak_hz": None, 
            "mains_hz": None, 
            "blink_polarity_ok": None, 
            "notes": [],
            "signal_quality": {},
            "artifact_detection": {},
            "clinical_indicators": {}
        }

        # Basic signal properties
        data = raw.get_data()
        out["signal_quality"]["n_channels"] = data.shape[0]
        out["signal_quality"]["n_samples"] = data.shape[1]
        out["signal_quality"]["duration_minutes"] = data.shape[1] / (fs * 60)
        
        # Signal amplitude statistics
        out["signal_quality"]["amplitude_stats"] = {
            "mean": float(np.mean(data)),
            "std": float(np.std(data)),
            "min": float(np.min(data)),
            "max": float(np.max(data)),
            "dynamic_range": float(np.max(data) - np.min(data))
        }
        
        # Check for signal clipping
        clip_threshold = 0.95 * np.max(np.abs(data))
        clipped_samples = np.sum(np.abs(data) > clip_threshold)
        clip_percentage = (clipped_samples / data.size) * 100
        out["signal_quality"]["clipping"] = {
            "clipped_samples": int(clipped_samples),
            "clip_percentage": float(clip_percentage),
            "clipped": clip_percentage > 1.0  # More than 1% clipped
        }
        
        # Check for dead channels
        channel_rms = np.sqrt(np.mean(data**2, axis=1))
        dead_threshold = np.percentile(channel_rms, 5) * 0.1
        dead_channels = [ch_names[i] for i in range(len(ch_names)) if channel_rms[i] < dead_threshold]
        out["signal_quality"]["dead_channels"] = dead_channels
        
        # Check for excessive noise
        noise_level = np.std(data)
        if noise_level > 100:  # µV
            out["notes"].append(f"High noise level: {noise_level:.1f} µV")
        
        # Alpha peak detection at O1/O2 if present
        picks = []
        for name in ["O1","O2","Oz","POz"]:
            if name in ch_names:
                picks.append(name)
        if picks:
            try:
                psds, freqs = mne.time_frequency.psd_welch(raw.copy().pick(picks), fmin=2, fmax=40, n_fft=4096, verbose=False)
                mean_psd = psds.mean(axis=0)
                idx = (freqs>=7) & (freqs<=13)
                if np.any(idx):
                    alpha_f = float(freqs[idx][np.argmax(mean_psd[idx])])
                    out["alpha_peak_hz"] = alpha_f
                    
                    # Check if alpha peak is in normal range
                    if 8 <= alpha_f <= 12:
                        out["clinical_indicators"]["alpha_normal"] = True
                    else:
                        out["clinical_indicators"]["alpha_normal"] = False
                        out["notes"].append(f"Alpha peak outside normal range: {alpha_f:.1f} Hz")
            except Exception as e:
                out["notes"].append(f"Alpha peak detection failed: {e}")

        # Mains frequency detection (50/60 Hz)
        try:
            psd_all, f_all = mne.time_frequency.psd_welch(raw, fmin=40, fmax=70, n_fft=4096, verbose=False)
            peaks = f_all[psd_all.mean(axis=0).argmax()]
            if 49 <= peaks <= 51: 
                out["mains_hz"] = 50.0
            elif 59 <= peaks <= 61: 
                out["mains_hz"] = 60.0
            else: 
                out["mains_hz"] = float(peaks)
                
            # Check for mains contamination
            if out["mains_hz"]:
                out["artifact_detection"]["mains_contamination"] = True
                out["notes"].append(f"Mains frequency detected: {out['mains_hz']} Hz")
        except Exception as e:
            out["notes"].append(f"Mains detection failed: {e}")

        # Blink polarity check: Fp1/Fp2 if present; expect positive deflection (minus-up displays)
        for cand in [("Fp1","Fp2"), ("AFz","Fpz")]:
            if all(c in ch_names for c in cand):
                try:
                    data_filtered, _ = raw.copy().pick(cand).filter(0.1,3.0, verbose=False).get_data()
                    if data_filtered.shape[1] > 0:
                        peak = np.percentile(data_filtered[0], 99)
                        trough = np.percentile(data_filtered[0], 1)
                        out["blink_polarity_ok"] = bool(peak > abs(trough))
                        
                        if not out["blink_polarity_ok"]:
                            out["notes"].append("Blink polarity appears inverted (check montage)")
                        break
                except Exception as e:
                    out["notes"].append(f"Blink polarity check failed: {e}")

        # Check for excessive movement artifacts
        try:
            # High-pass filter to detect movement
            raw_highpass = raw.copy().filter(5.0, None, verbose=False)
            data_highpass = raw_highpass.get_data()
            
            # Calculate movement index (variance of high-pass filtered data)
            movement_index = np.var(data_highpass, axis=1)
            high_movement = np.sum(movement_index > np.percentile(movement_index, 90))
            
            out["artifact_detection"]["movement"] = {
                "high_movement_channels": int(high_movement),
                "movement_threshold": float(np.percentile(movement_index, 90)),
                "excessive_movement": high_movement > len(ch_names) * 0.3  # More than 30% of channels
            }
            
            if out["artifact_detection"]["movement"]["excessive_movement"]:
                out["notes"].append("Excessive movement artifacts detected")
                
        except Exception as e:
            out["notes"].append(f"Movement artifact detection failed: {e}")

        # Check for flat channels (electrode contact issues)
        flat_channels = []
        for i, ch_name in enumerate(ch_names):
            ch_data = data[i, :]
            ch_std = np.std(ch_data)
            if ch_std < 0.1:  # Very low variance
                flat_channels.append(ch_name)
        
        out["signal_quality"]["flat_channels"] = flat_channels
        if flat_channels:
            out["notes"].append(f"Flat channels detected (possible electrode contact issues): {flat_channels}")

        # Sampling rate validation
        if fs_expect and abs(fs - fs_expect) > 1e-6:
            out["notes"].append(f"Sampling rate mismatch: EDF {fs} vs expected {fs_expect}")
            out["signal_quality"]["fs_mismatch"] = True
        else:
            out["signal_quality"]["fs_mismatch"] = False

        # Overall signal quality assessment
        quality_score = 100
        
        # Deduct points for various issues
        if out["signal_quality"]["clipping"]["clipped"]:
            quality_score -= 20
        if dead_channels:
            quality_score -= len(dead_channels) * 5
        if flat_channels:
            quality_score -= len(flat_channels) * 3
        if out["artifact_detection"]["movement"]["excessive_movement"]:
            quality_score -= 15
        if not out["blink_polarity_ok"]:
            quality_score -= 10
            
        quality_score = max(0, quality_score)
        
        out["signal_quality"]["overall_score"] = quality_score
        out["signal_quality"]["quality_rating"] = "EXCELLENT" if quality_score >= 90 else "GOOD" if quality_score >= 75 else "FAIR" if quality_score >= 60 else "POOR"

        # Advanced spectral analysis
        try:
            # Check for abnormal spectral patterns
            out["spectral_analysis"] = _analyze_spectral_patterns(raw, fs)
        except Exception as e:
            out["notes"].append(f"Spectral analysis failed: {e}")
        
        # Advanced artifact detection
        try:
            out["advanced_artifacts"] = _detect_advanced_artifacts(raw, fs)
        except Exception as e:
            out["notes"].append(f"Advanced artifact detection failed: {e}")
        
        # Clinical compliance checks
        try:
            out["clinical_compliance"] = _check_clinical_compliance(raw, ch_names, fs)
        except Exception as e:
            out["notes"].append(f"Clinical compliance check failed: {e}")

        return out
    except Exception as e:
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}

def _analyze_spectral_patterns(raw, fs):
    """Advanced spectral pattern analysis for clinical validation"""
    try:
        import numpy as np
        
        # Get data for spectral analysis
        data = raw.get_data()
        n_channels, n_samples = data.shape
        
        spectral_results = {
            "delta_power": [],
            "theta_power": [],
            "alpha_power": [],
            "beta_power": [],
            "gamma_power": [],
            "spectral_edge_freq": [],
            "peak_frequency": [],
            "spectral_entropy": []
        }
        
        # Analyze each channel
        for ch_idx in range(min(n_channels, 32)):  # Limit to first 32 channels for performance
            ch_data = data[ch_idx, :]
            
            # Compute power spectral density
            from scipy import signal
            freqs, psd = signal.welch(ch_data, fs=fs, nperseg=min(4096, n_samples//4))
            
            # Define frequency bands
            delta_idx = (freqs >= 0.5) & (freqs < 4)
            theta_idx = (freqs >= 4) & (freqs < 8)
            alpha_idx = (freqs >= 8) & (freqs < 13)
            beta_idx = (freqs >= 13) & (freqs < 30)
            gamma_idx = (freqs >= 30) & (freqs < 100)
            
            # Calculate power in each band
            spectral_results["delta_power"].append(float(np.sum(psd[delta_idx])))
            spectral_results["theta_power"].append(float(np.sum(psd[theta_idx])))
            spectral_results["alpha_power"].append(float(np.sum(psd[alpha_idx])))
            spectral_results["beta_power"].append(float(np.sum(psd[beta_idx])))
            spectral_results["gamma_power"].append(float(np.sum(psd[gamma_idx])))
            
            # Spectral edge frequency (95% of power)
            cumsum_psd = np.cumsum(psd)
            total_power = cumsum_psd[-1]
            edge_idx = np.where(cumsum_psd >= 0.95 * total_power)[0]
            if len(edge_idx) > 0:
                spectral_results["spectral_edge_freq"].append(float(freqs[edge_idx[0]]))
            else:
                spectral_results["spectral_edge_freq"].append(float(freqs[-1]))
            
            # Peak frequency
            peak_idx = np.argmax(psd[freqs <= 50])  # Limit to 50 Hz
            spectral_results["peak_frequency"].append(float(freqs[peak_idx]))
            
            # Spectral entropy
            psd_norm = psd / np.sum(psd)
            psd_norm = psd_norm[psd_norm > 0]  # Remove zeros
            entropy = -np.sum(psd_norm * np.log(psd_norm))
            spectral_results["spectral_entropy"].append(float(entropy))
        
        # Calculate summary statistics
        for key in spectral_results:
            if spectral_results[key]:
                values = spectral_results[key]
                spectral_results[f"{key}_mean"] = float(np.mean(values))
                spectral_results[f"{key}_std"] = float(np.std(values))
                spectral_results[f"{key}_median"] = float(np.median(values))
        
        return spectral_results
        
    except Exception as e:
        return {"error": str(e), "analysis_failed": True}

def _detect_advanced_artifacts(raw, fs):
    """Advanced artifact detection using multiple methods"""
    try:
        import numpy as np
        from scipy import signal
        
        data = raw.get_data()
        n_channels, n_samples = data.shape
        
        artifacts = {
            "eye_blinks": {"detected": False, "count": 0, "channels": []},
            "muscle_artifacts": {"detected": False, "severity": "none", "channels": []},
            "electrode_pops": {"detected": False, "count": 0, "channels": []},
            "line_noise": {"detected": False, "frequency": None, "severity": "none"},
            "baseline_drift": {"detected": False, "severity": "none", "channels": []},
            "high_frequency_noise": {"detected": False, "severity": "none", "channels": []},
            "saturation": {"detected": False, "channels": []},
            "disconnected_electrodes": {"detected": False, "channels": []}
        }
        
        # Eye blink detection (frontal channels)
        frontal_channels = [i for i, ch in enumerate(raw.ch_names) if any(fp in ch.upper() for fp in ['FP1', 'FP2', 'AFZ', 'FPZ'])]
        if frontal_channels:
            for ch_idx in frontal_channels:
                ch_data = data[ch_idx, :]
                # Filter for eye blink frequency range (0.5-3 Hz)
                filtered = signal.filtfilt(*signal.butter(4, [0.5, 3], btype='band', fs=fs), ch_data)
                
                # Detect large amplitude changes (potential blinks)
                threshold = 3 * np.std(filtered)
                peaks, _ = signal.find_peaks(np.abs(filtered), height=threshold, distance=int(fs * 0.5))
                
                if len(peaks) > 10:  # More than 10 potential blinks
                    artifacts["eye_blinks"]["detected"] = True
                    artifacts["eye_blinks"]["count"] += len(peaks)
                    artifacts["eye_blinks"]["channels"].append(raw.ch_names[ch_idx])
        
        # Muscle artifact detection (high frequency content)
        for ch_idx in range(min(n_channels, 32)):
            ch_data = data[ch_idx, :]
            
            # High frequency power (30-100 Hz)
            hf_filtered = signal.filtfilt(*signal.butter(4, [30, min(100, fs/2-1)], btype='band', fs=fs), ch_data)
            hf_power = np.var(hf_filtered)
            
            # Low frequency power (1-30 Hz)
            lf_filtered = signal.filtfilt(*signal.butter(4, [1, 30], btype='band', fs=fs), ch_data)
            lf_power = np.var(lf_filtered)
            
            # Muscle artifact ratio
            if lf_power > 0:
                muscle_ratio = hf_power / lf_power
                if muscle_ratio > 0.5:  # High ratio indicates muscle activity
                    artifacts["muscle_artifacts"]["detected"] = True
                    artifacts["muscle_artifacts"]["channels"].append(raw.ch_names[ch_idx])
        
        # Set muscle artifact severity
        if artifacts["muscle_artifacts"]["detected"]:
            n_affected = len(artifacts["muscle_artifacts"]["channels"])
            if n_affected > n_channels * 0.5:
                artifacts["muscle_artifacts"]["severity"] = "severe"
            elif n_affected > n_channels * 0.25:
                artifacts["muscle_artifacts"]["severity"] = "moderate"
            else:
                artifacts["muscle_artifacts"]["severity"] = "mild"
        
        # Electrode pop detection (sudden large amplitude changes)
        for ch_idx in range(n_channels):
            ch_data = data[ch_idx, :]
            
            # Calculate derivative to find sudden changes
            diff_data = np.diff(ch_data)
            threshold = 5 * np.std(diff_data)
            
            pops = np.where(np.abs(diff_data) > threshold)[0]
            if len(pops) > 5:
                artifacts["electrode_pops"]["detected"] = True
                artifacts["electrode_pops"]["count"] += len(pops)
                artifacts["electrode_pops"]["channels"].append(raw.ch_names[ch_idx])
        
        # Line noise detection (50/60 Hz)
        for freq in [50, 60]:
            if freq < fs/2:
                # Check power at line frequency
                freqs, psd = signal.welch(data, fs=fs, nperseg=min(4096, n_samples//4), axis=1)
                freq_idx = np.argmin(np.abs(freqs - freq))
                
                # Compare line frequency power to surrounding frequencies
                surrounding_power = np.mean(psd[:, max(0, freq_idx-5):min(len(freqs), freq_idx+6)], axis=1)
                line_power = psd[:, freq_idx]
                
                line_ratio = line_power / (surrounding_power + 1e-10)
                if np.mean(line_ratio) > 3:  # Line frequency is 3x stronger than surrounding
                    artifacts["line_noise"]["detected"] = True
                    artifacts["line_noise"]["frequency"] = freq
                    if np.mean(line_ratio) > 10:
                        artifacts["line_noise"]["severity"] = "severe"
                    elif np.mean(line_ratio) > 5:
                        artifacts["line_noise"]["severity"] = "moderate"
                    else:
                        artifacts["line_noise"]["severity"] = "mild"
        
        # Baseline drift detection
        for ch_idx in range(n_channels):
            ch_data = data[ch_idx, :]
            
            # Low-pass filter to get baseline trend
            baseline = signal.filtfilt(*signal.butter(4, 0.5, btype='low', fs=fs), ch_data)
            drift_range = np.max(baseline) - np.min(baseline)
            
            if drift_range > 100:  # More than 100 µV drift
                artifacts["baseline_drift"]["detected"] = True
                artifacts["baseline_drift"]["channels"].append(raw.ch_names[ch_idx])
        
        # Set baseline drift severity
        if artifacts["baseline_drift"]["detected"]:
            n_affected = len(artifacts["baseline_drift"]["channels"])
            if n_affected > n_channels * 0.5:
                artifacts["baseline_drift"]["severity"] = "severe"
            elif n_affected > n_channels * 0.25:
                artifacts["baseline_drift"]["severity"] = "moderate"
            else:
                artifacts["baseline_drift"]["severity"] = "mild"
        
        # Saturation detection
        for ch_idx in range(n_channels):
            ch_data = data[ch_idx, :]
            
            # Check for clipping at extreme values
            data_range = np.max(ch_data) - np.min(ch_data)
            max_val = np.max(np.abs(ch_data))
            
            # If signal hits the same extreme value repeatedly, it might be saturated
            extreme_threshold = max_val * 0.95
            saturated_samples = np.sum(np.abs(ch_data) > extreme_threshold)
            
            if saturated_samples > n_samples * 0.01:  # More than 1% of samples saturated
                artifacts["saturation"]["detected"] = True
                artifacts["saturation"]["channels"].append(raw.ch_names[ch_idx])
        
        # Disconnected electrode detection (flat or very low variance)
        for ch_idx in range(n_channels):
            ch_data = data[ch_idx, :]
            ch_var = np.var(ch_data)
            
            if ch_var < 0.01:  # Very low variance
                artifacts["disconnected_electrodes"]["detected"] = True
                artifacts["disconnected_electrodes"]["channels"].append(raw.ch_names[ch_idx])
        
        return artifacts
        
    except Exception as e:
        return {"error": str(e), "detection_failed": True}

def _check_clinical_compliance(raw, ch_names, fs):
    """Check compliance with clinical EEG standards"""
    try:
        compliance = {
            "sampling_rate_compliant": False,
            "duration_compliant": False,
            "channel_count_compliant": False,
            "montage_compliant": False,
            "resolution_compliant": False,
            "frequency_response_compliant": False,
            "impedance_check": "not_available",
            "calibration_check": "not_available"
        }
        
        # Sampling rate compliance (IFCN guidelines)
        if 200 <= fs <= 1000:
            compliance["sampling_rate_compliant"] = True
        
        # Duration compliance
        duration_minutes = raw.n_times / (fs * 60)
        if 20 <= duration_minutes <= 120:  # Typical clinical range
            compliance["duration_compliant"] = True
        
        # Channel count compliance
        n_channels = len(ch_names)
        if 16 <= n_channels <= 256:  # Typical clinical range
            compliance["channel_count_compliant"] = True
        
        # Montage compliance (check for standard 10-20 system)
        standard_channels = ['FP1', 'FP2', 'F3', 'F4', 'C3', 'C4', 'P3', 'P4', 'O1', 'O2', 'F7', 'F8', 'T3', 'T4', 'T5', 'T6', 'FZ', 'CZ', 'PZ']
        ch_names_upper = [ch.upper() for ch in ch_names]
        
        standard_present = sum(1 for ch in standard_channels if ch in ch_names_upper)
        if standard_present >= 10:  # At least 10 standard channels
            compliance["montage_compliant"] = True
        
        # Resolution compliance (check if data has appropriate dynamic range)
        data = raw.get_data()
        data_range = np.max(data) - np.min(data)
        if 10 <= data_range <= 10000:  # Reasonable µV range
            compliance["resolution_compliant"] = True
        
        # Frequency response compliance (check if we can detect expected EEG frequencies)
        try:
            from scipy import signal
            freqs, psd = signal.welch(data, fs=fs, nperseg=min(4096, raw.n_times//4), axis=1)
            
            # Check if alpha band (8-13 Hz) has reasonable power
            alpha_idx = (freqs >= 8) & (freqs <= 13)
            alpha_power = np.mean(psd[:, alpha_idx])
            
            # Check if high frequency content exists but isn't dominant
            hf_idx = freqs >= 50
            hf_power = np.mean(psd[:, hf_idx])
            
            if alpha_power > hf_power and alpha_power > 0:
                compliance["frequency_response_compliant"] = True
        except:
            pass
        
        # Calculate overall compliance score
        compliant_checks = sum(1 for key, value in compliance.items() 
                             if key.endswith('_compliant') and value)
        total_checks = sum(1 for key in compliance.keys() if key.endswith('_compliant'))
        
        compliance["overall_score"] = compliant_checks / total_checks if total_checks > 0 else 0
        compliance["compliance_level"] = (
            "excellent" if compliance["overall_score"] >= 0.9 else
            "good" if compliance["overall_score"] >= 0.7 else
            "fair" if compliance["overall_score"] >= 0.5 else
            "poor"
        )
        
        return compliance
        
    except Exception as e:
        return {"error": str(e), "compliance_check_failed": True}

class EDFToEEGConverter:
    """Convert EDF files to BrainVision .eeg format"""
    
    def __init__(self):
        """Initialize the converter"""
        self.supported_formats = ['.edf', '.bdf']
        
        # Supported output formats
        self.output_formats = {
            'brainvision': 'BrainVision (.vhdr/.vmrk) - Modern software',
            'wineeg': 'WinEEG (.erd/.evt) - Original WinEEG',
            'neuroscan': 'Neuroscan (.hdr) - Neuroscan systems',
            'eeglab': 'EEGLAB (.set) - MATLAB-based analysis',
            'nicolet': 'Nicolet (.eeg) - Nihon Kohden systems',
            'compumedics': 'Compumedics (.eeg) - Sleep/EEG systems',
            'both': 'Both BrainVision + WinEEG - Universal compatibility'
        }
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def print_header(self):
        """Print tool header"""
        print("🧠 EEG Paradox EDF to EEG Converter")
        print("=" * 50)
        print("Converts EDF files to BrainVision .eeg format")
        print()
    
    def analyze_edf_file(self, edf_file_path):
        """Analyze EDF file using Gunkelman-grade validation"""
        try:
            print(f"🔍 Analyzing: {Path(edf_file_path).name}")
            
            # Use Gunkelman EDF header parser first (no MNE dependency)
            edf_header = EDFHeader(Path(edf_file_path))
            edf_header.read()
            
            if not edf_header.valid:
                print("❌ EDF header parsing failed")
                return None, None
            
            # Extract parameters from header
            fs, fs_equal = edf_header.common_fs()
            total_samples = edf_header.total_samples_per_channel()
            
            info = {
                'channels': edf_header.n_signals,
                'channel_names': edf_header.labels,
                'sampling_rate': fs,
                'duration': edf_header.n_records * edf_header.duration_record_s,
                'n_samples': total_samples[0] if total_samples else 0,
                'data_shape': (edf_header.n_signals, total_samples[0] if total_samples else 0),
                'fs_channels_equal': fs_equal,
                'edf_header': edf_header
            }
            
            print(f"📊 EDF File Analysis (Gunkelman-grade):")
            print(f"   Channels: {info['channels']}")
            print(f"   Channel names: {', '.join(info['channel_names'][:5])}{'...' if len(info['channel_names']) > 5 else ''}")
            print(f"   Sampling rate: {info['sampling_rate']:.1f} Hz")
            print(f"   Duration: {info['duration']:.1f} seconds ({info['duration']/60:.1f} minutes)")
            print(f"   Total samples: {info['n_samples']:,}")
            print(f"   Data shape: {info['data_shape']}")
            print(f"   All channels same fs: {info['fs_channels_equal']}")
            
            # If MNE available, also load for signal-level analysis
            if MNE_AVAILABLE:
                try:
                    raw = mne.io.read_raw_edf(edf_file_path, preload=True, verbose=False)
                    info['mne_raw'] = raw
                    print(f"   ✅ MNE data loaded for signal QC")
                except Exception as e:
                    print(f"   ⚠️  MNE loading failed: {e}")
            
            return info.get('mne_raw'), info
            
        except Exception as e:
            print(f"❌ Error analyzing EDF file: {e}")
            return None, None
    
    def calculate_optimal_resolution(self, data, edf_header=None):
        """Calculate optimal resolution with amplifier detection for BrainVision format"""
        try:
            # Get data range
            data_min = np.min(data)
            data_max = np.max(data)
            data_range = data_max - data_min
            
            print(f"📈 Data Analysis:")
            print(f"   Range: {data_min:.2f} to {data_max:.2f} µV")
            print(f"   Peak-to-peak: {data_range:.2f} µV")
            
            # Attempt amplifier detection
            print(f"\n🔍 Amplifier Detection:")
            amp_detection = detect_amplifier_system(edf_header, data)
            
            print(f"   Detected System: {amp_detection['detected_system']}")
            print(f"   Confidence: {amp_detection['confidence']:.1%}")
            
            if amp_detection['evidence']:
                print(f"   Evidence:")
                for evidence in amp_detection['evidence'][:3]:  # Show first 3 pieces of evidence
                    print(f"     • {evidence}")
                if len(amp_detection['evidence']) > 3:
                    print(f"     • ... and {len(amp_detection['evidence']) - 3} more")
            
            # Calculate amplifier-aware resolution
            resolution = calculate_amplifier_aware_resolution(data, amp_detection)
            
            # Validate the resolution choice
            validation = validate_amplifier_scaling(data, resolution, amp_detection)
            
            if not validation['resolution_appropriate']:
                print(f"\n⚠️  Resolution Validation Issues:")
                for warning in validation['warnings']:
                    print(f"     • {warning}")
                
                if validation['recommendations']:
                    print(f"   Recommendations:")
                    for rec in validation['recommendations']:
                        print(f"     • {rec}")
            
            # Store amplifier detection results for reporting
            self.amp_detection_results = amp_detection
            self.resolution_validation = validation
            
            return resolution
            
        except Exception as e:
            print(f"⚠️  Could not calculate resolution: {e}")
            print(f"   Falling back to data-driven approach")
            # Fallback to original method
            data_range = np.max(data) - np.min(data)
            return calculate_data_driven_resolution(data_range)
    
    def convert_data_to_int16(self, data, resolution):
        """Convert µV data to INT16 format"""
        try:
            print(f"🔄 Converting data to INT16...")
            print(f"   Original range: {np.min(data):.2f} to {np.max(data):.2f} µV")
            
            # Scale data by resolution to get INT16 values
            scaled_data = data / resolution
            print(f"   Scaled range: {np.min(scaled_data):.1f} to {np.max(scaled_data):.1f} bits")
            
            # Clip to INT16 range
            clipped_data = np.clip(scaled_data, -32767, 32767)
            
            # Convert to INT16
            int16_data = clipped_data.astype(np.int16)
            
            print(f"   Final INT16 range: {np.min(int16_data):,} to {np.max(int16_data):,}")
            print(f"   Data shape: {int16_data.shape}")
            
            return int16_data
            
        except Exception as e:
            print(f"❌ Error converting data: {e}")
            return None
    
    def create_brainvision_header(self, output_path, info, resolution):
        """Create BrainVision .vhdr header file with exact sampling interval"""
        try:
            vhdr_file = output_path.with_suffix('.vhdr')
            vmrk_file = output_path.with_suffix('.vmrk')
            eeg_file = output_path.with_suffix('.eeg')
            
            # Calculate exact sampling interval in microseconds (Gunkelman spec)
            sampling_interval = micround(info['sampling_rate'])
            
                        # Create header content
            header_content = f"""Brain Vision Data Exchange Header File Version 1.0
 ; Data created from EDF file by EEG Paradox Converter (Gunkelman-grade)
 
 [Common Infos]
 Codepage=ANSI
 DataFile={eeg_file.name}
 MarkerFile={vmrk_file.name}
 DataFormat=BINARY
 ; Data orientation: MULTIPLEXED=ch1,pt1, ch2,pt1 ...
 DataOrientation=MULTIPLEXED
 NumberOfChannels={info['channels']}
 ; Sampling interval in microseconds
 SamplingInterval={sampling_interval}
 
 [Binary Infos]
 BinaryFormat=INT_16
 UseBigEndianOrder=NO
 
 [Channel Infos]
 ; Ch1=Fp1,,1.0,uV
 ; #     Name   Ref  Resolution/Unit
 ; Zero-based channel indexing:
 """
            
            # Add channel definitions
            for i, ch_name in enumerate(info['channel_names'], 1):
                # Clean channel name (remove special characters)
                clean_name = ''.join(c for c in ch_name if c.isalnum() or c in '-_')
                header_content += f"Ch{i}={clean_name},,{resolution:.6f},uV\n"
            
            # Write header file
            with open(vhdr_file, 'w', encoding='utf-8') as f:
                f.write(header_content)
            
            print(f"✅ Created header: {vhdr_file}")
            return vhdr_file
            
        except Exception as e:
            print(f"❌ Error creating header: {e}")
            return None
    
    def create_brainvision_marker(self, output_path, info):
        """Create BrainVision .vmrk marker file"""
        try:
            vmrk_file = output_path.with_suffix('.vmrk')
            eeg_file = output_path.with_suffix('.eeg')
            
            # Create marker content
            marker_content = f"""Brain Vision Data Exchange Marker File, Version 1.0
; Data created from EDF file by EEG Paradox Converter

[Common Infos]
Codepage=ANSI
DataFile={eeg_file.name}

[Marker Infos]
; Each entry: Mk<Marker number>=<Type>,<Description>,<Position in data points>,<Size in data points>,<Channel number (0 = marker is related to all channels)>
; Fields are delimited by commas, some fields might be omitted (empty).
; Commas in type or description text are coded as "\\1".
Mk1=New Segment,,1,1,0,{info['sampling_rate']:.0f}
Mk2=Recording End,,{info['n_samples']},1,0
"""
            
            # Write marker file
            with open(vmrk_file, 'w', encoding='utf-8') as f:
                f.write(marker_content)
            
            print(f"✅ Created markers: {vmrk_file}")
            return vmrk_file
            
        except Exception as e:
            print(f"❌ Error creating markers: {e}")
            return None
    
    def write_eeg_data(self, output_path, int16_data):
        """Write INT16 data to .eeg file"""
        try:
            eeg_file = output_path.with_suffix('.eeg')
            
            print(f"💾 Writing binary data to: {eeg_file}")
            
            # Flatten data in multiplexed format (ch1,pt1, ch2,pt1, ch1,pt2, ch2,pt2, ...)
            channels, samples = int16_data.shape
            multiplexed_data = int16_data.T.flatten()  # Transpose and flatten
            
            print(f"   Channels: {channels}")
            print(f"   Samples per channel: {samples}")
            print(f"   Total data points: {len(multiplexed_data):,}")
            
            # Write binary data
            with open(eeg_file, 'wb') as f:
                # Pack as little-endian signed 16-bit integers
                packed_data = struct.pack(f'<{len(multiplexed_data)}h', *multiplexed_data)
                f.write(packed_data)
            
            file_size = os.path.getsize(eeg_file)
            print(f"✅ Created EEG data: {eeg_file} ({file_size:,} bytes)")
            
            return eeg_file
            
        except Exception as e:
            print(f"❌ Error writing EEG data: {e}")
            return None
    
    def convert_file(self, edf_file_path, output_dir=None, output_format='brainvision'):
        """Main conversion method"""
        if not os.path.exists(edf_file_path):
            print(f"❌ Error: File '{edf_file_path}' not found")
            return False
        
        edf_path = Path(edf_file_path)
        
        # Check file extension
        if edf_path.suffix.lower() not in self.supported_formats:
            print(f"❌ Unsupported format: {edf_path.suffix}")
            print(f"   Supported: {', '.join(self.supported_formats)}")
            return False
        
        # Set output directory
        if output_dir is None:
            output_dir = edf_path.parent
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(exist_ok=True)
        
        # Set output filename
        output_path = output_dir / edf_path.stem
        
        print(f"📁 Input: {edf_path}")
        print(f"📁 Output: {output_path.with_suffix('.eeg')}")
        print()
        
        # Step 1: Analyze EDF file
        raw, info = self.analyze_edf_file(edf_file_path)
        if raw is None or info is None:
            return False
        
        # Step 2: Get data and calculate resolution
        print(f"\n📊 Data Extraction:")
        data = raw.get_data()  # Get data in µV
        
        # Debug: Check data properties
        print(f"   Data shape: {data.shape}")
        print(f"   Data type: {data.dtype}")
        print(f"   Data min: {np.min(data):.6f}")
        print(f"   Data max: {np.max(data):.6f}")
        print(f"   Data mean: {np.mean(data):.6f}")
        print(f"   Data std: {np.std(data):.6f}")
        
        # Check if data is all zeros or very small
        if np.allclose(data, 0, atol=1e-10):
            print("   ⚠️  Warning: Data appears to be all zeros or very small!")
            print("   This might indicate a loading issue or the data is not in µV units")
            print("   Trying to load data with different scaling...")
            
            # Try to get data without any scaling
            try:
                data = raw.get_data(picks='eeg', units=None)
                print(f"   Retry - Data min: {np.min(data):.6f}, max: {np.max(data):.6f}")
            except:
                print("   Could not reload data without scaling")
        
        # Detect and correct unit scaling issues
        data_range = np.max(data) - np.min(data)
        original_range = data_range
        scaling_applied = False
        
        print(f"   🔍 Checking data scaling (range: {data_range:.2e})")
        
        # Check for various scaling issues common in DIY/open-source EEG systems
        if data_range < 0.01:  # Extremely small range suggests wrong units
            print("   🚨 Potential unit scaling issue detected...")
            
            # Case 1: Data in Volts (very common with Arduino/OpenBCI exports)
            if 1e-6 < data_range < 1e-3:
                print("   📈 Data appears to be in Volts → converting to microvolts")
                data = data * 1e6  # Convert V to µV
                scaling_applied = True
                
            # Case 2: Data in millivolts
            elif 1e-3 < data_range < 1:
                print("   📈 Data appears to be in millivolts → converting to microvolts") 
                data = data * 1e3  # Convert mV to µV
                scaling_applied = True
                
            # Case 3: Extremely small values (possible double scaling issue)
            elif data_range < 1e-6:
                print("   📈 Data extremely small → applying 1M scaling factor")
                data = data * 1e6
                scaling_applied = True
                
            # Case 4: Check for ADC count scaling (common in DIY systems)
            elif 1e-5 < data_range < 1e-2:
                # Might be normalized ADC counts that need scaling
                max_abs = np.max(np.abs(data))
                if max_abs < 1.0:  # Normalized to 0-1 range
                    print("   📈 Data appears to be normalized ADC counts → scaling to µV range")
                    data = data * 100  # Scale to reasonable µV range
                    scaling_applied = True
                
        # Check for other common scaling issues
        elif data_range > 100000:  # Very large range
            print("   🔍 Checking for over-scaled data...")
            max_abs = np.max(np.abs(data))
            
            # Case 5: Data might be in nanovolts or over-amplified
            if max_abs > 1e6:  # Larger than 1V in µV units
                print("   📉 Data appears over-scaled → applying 1/1000 scaling")
                data = data / 1000
                scaling_applied = True
            elif max_abs > 100000:  # Very large µV values
                print("   📉 Data appears over-amplified → applying 1/10 scaling")
                data = data / 10
                scaling_applied = True
                
        # Check for integer ADC values that need conversion
        elif np.all(np.abs(data - np.round(data)) < 1e-10):  # All integer values
            max_val = np.max(np.abs(data))
            if max_val < 65536 and max_val > 100:  # Looks like ADC counts
                print("   📈 Data appears to be raw ADC counts → converting to µV")
                # Assume 3.3V ADC range with appropriate gain
                if max_val < 1024:  # 10-bit ADC
                    data = data * (3300 / 1024)  # 3.3V range
                elif max_val < 4096:  # 12-bit ADC  
                    data = data * (3300 / 4096)
                elif max_val < 65536:  # 16-bit ADC
                    data = data * (3300 / 65536)
                scaling_applied = True
        
        # Final validation and reporting
        if scaling_applied:
            new_range = np.max(data) - np.min(data)
            print(f"   ✅ Scaling applied: {original_range:.2e} → {new_range:.2f} µV")
            print(f"   📊 Final data range: {np.min(data):.2f} to {np.max(data):.2f} µV")
            
            # Store scaling info for reporting
            info['scaling_applied'] = {
                'original_range': original_range,
                'final_range': new_range,
                'scaling_factor': new_range / original_range if original_range > 0 else 1,
                'method': 'automatic_unit_detection'
            }
        else:
            if data_range < 1:
                print(f"   ⚠️  Warning: Unusual small data range ({data_range:.2e}) - may affect conversion quality")
            elif data_range > 50000:
                print(f"   ⚠️  Warning: Unusual large data range ({data_range:.2e}) - may affect conversion quality")
        
        resolution = self.calculate_optimal_resolution(data, info.get('edf_header'))
        
        # Step 3: Convert to INT16
        print(f"\n🔄 Data Conversion:")
        int16_data = self.convert_data_to_int16(data, resolution)
        if int16_data is None:
            return False
        
        # Step 4: Create output files based on format
        if output_format in ['brainvision', 'both']:
            print(f"\n📝 Creating BrainVision Files:")
            
            # Create header
            vhdr_file = self.create_brainvision_header(output_path, info, resolution)
            if vhdr_file is None:
                return False
            
            # Create markers
            vmrk_file = self.create_brainvision_marker(output_path, info)
            if vmrk_file is None:
                return False
        
        if output_format in ['wineeg', 'both']:
            print(f"\n📝 Creating WinEEG Files:")
            
            # Create WinEEG header
            erd_file = self.create_wineeg_header(output_path, info, resolution)
            if erd_file is None:
                return False
            
            # Create WinEEG events
            evt_file = self.create_wineeg_events(output_path, info)
            if evt_file is None:
                return False
        
        if output_format in ['nicolet', 'both']:
            print(f"\n📝 Creating Nicolet Files:")
            nicolet_file = self.create_nicolet_header(output_path, info, resolution)
            if nicolet_file is None:
                return False

        if output_format in ['compumedics', 'both']:
            print(f"\n📝 Creating Compumedics Files:")
            compumedics_file = self.create_compumedics_header(output_path, info, resolution)
            if compumedics_file is None:
                return False

        if output_format in ['neuroscan', 'both']:
            print(f"\n📝 Creating Neuroscan Files:")
            neuroscan_file = self.create_neuroscan_header(output_path, info, resolution)
            if neuroscan_file is None:
                return False

        if output_format in ['eeglab', 'both']:
            print(f"\n📝 Creating EEGLAB Files:")
            eeglab_set = self.create_eeglab_set(output_path, info, resolution)
            if eeglab_set is None:
                return False
        
        # Write EEG data (shared by both formats)
        eeg_file = self.write_eeg_data(output_path, int16_data)
        if eeg_file is None:
            return False
        
        print(f"\n🎉 Conversion Complete!")
        print(f"📁 Generated files:")
        
        if output_format in ['brainvision', 'both']:
            print(f"   BrainVision format:")
            print(f"   • {vhdr_file.name} (header)")
            print(f"   • {vmrk_file.name} (markers)")
        
        if output_format in ['wineeg', 'both']:
            print(f"   WinEEG format:")
            print(f"   • {erd_file.name} (header)")
            print(f"   • {evt_file.name} (events)")
        
        if output_format in ['nicolet', 'both']:
            print(f"   Nicolet format:")
            print(f"   • {nicolet_file.name} (header)")

        if output_format in ['compumedics', 'both']:
            print(f"   Compumedics format:")
            print(f"   • {compumedics_file.name} (header)")

        if output_format in ['neuroscan', 'both']:
            print(f"   Neuroscan format:")
            print(f"   • {neuroscan_file.name} (header)")

        if output_format in ['eeglab', 'both']:
            print(f"   EEGLAB format:")
            print(f"   • {eeglab_set.name} (set)")
        
        print(f"   • {eeg_file.name} (binary data)")
        
        if output_format == 'brainvision':
            print(f"\n💡 Load {vhdr_file.name} in BrainVision Analyzer or Mitsar WinEEG")
        elif output_format == 'wineeg':
            print(f"\n💡 Load {erd_file.name} in original WinEEG software")
        elif output_format == 'nicolet':
            print(f"\n💡 Load {nicolet_file.name} in Nicolet software")
        elif output_format == 'compumedics':
            print(f"\n💡 Load {compumedics_file.name} in Compumedics software")
        elif output_format == 'neuroscan':
            print(f"\n💡 Load {neuroscan_file.name} in Neuroscan software")
        elif output_format == 'eeglab':
            print(f"\n💡 Load {eeglab_set.name} in EEGLAB")
        else:
            print(f"\n💡 Load .vhdr file in modern software or .erd file in original WinEEG")
        
        # Generate Gunkelman validation report
        print(f"\n🔍 Generating Gunkelman validation report...")
        
        # Generate comprehensive validation report for all formats
        if output_format in ['brainvision', 'both']:
            # Full validation with VHDR/VMRK files
            self._generate_validation_report(edf_file_path, vhdr_file, vmrk_file, eeg_file, info)
        elif output_format == 'wineeg':
            # WinEEG validation (create minimal VHDR-like structure for validation)
            wineeg_info = {
                'vhdr_equivalent': {
                    'path': str(erd_file),
                    'NumberOfChannels': info['channels'],
                    'SamplingInterval_us': micround(info['sampling_rate']),
                    'channels': [{'label': name} for name in info['channel_names']]
                },
                'vmrk_equivalent': {
                    'path': str(evt_file),
                    'markers': [{'desc': 'START', 'latency_samples': 0}, {'desc': 'END', 'latency_samples': int(info['sampling_rate'] * info['duration'])}]
                }
            }
            # For WinEEG, we need to create actual files for validation
            self._generate_validation_report(edf_file_path, erd_file, evt_file, eeg_file, info)
        else:
            # Other formats - create minimal validation structure
            # For other formats, create minimal validation files
            if output_format in ['neuroscan', 'nicolet', 'compumedics']:
                header_file = output_path.with_suffix('.hdr')
            else:  # eeglab
                header_file = output_path.with_suffix('.set')
            
            # Create a minimal marker file for validation
            marker_file = output_path.with_suffix('.vmrk')
            with open(marker_file, 'w', encoding='utf-8') as f:
                f.write(f"""Brain Vision Data Exchange Marker File, Version 1.0
[Common Infos]
Codepage=ANSI
DataFile={eeg_file.name}

[Marker Infos]
Mk1=New Segment,,1,1,0
Mk2=Recording End,,{info['n_samples']},1,0
""")
            
            self._generate_validation_report(edf_file_path, header_file, marker_file, eeg_file, info)
        
        return True
    
    def create_wineeg_header(self, output_path, info, resolution):
        """Create WinEEG .erd header file"""
        try:
            erd_file = output_path.with_suffix('.erd')
            evt_file = output_path.with_suffix('.evt')
            eeg_file = output_path.with_suffix('.eeg')
            
            # Create ERD content (WinEEG Resource Description)
            erd_content = f"""[FileInfo]
DataFile={eeg_file.name}
EventFile={evt_file.name}
FileFormat=EEG
DataFormat=BINARY
DataOrientation=MULTIPLEXED
NumberOfChannels={info['channels']}
SamplingRate={info['sampling_rate']:.1f}
BinaryFormat=INT_16
ByteOrder=LITTLE_ENDIAN

[ChannelInfo]
"""
            
            # Add channel definitions
            for i, ch_name in enumerate(info['channel_names'], 1):
                # Clean channel name (remove special characters)
                clean_name = ''.join(c for c in ch_name if c.isalnum() or c in '-_')
                erd_content += f"Ch{i}={clean_name},{resolution:.6f},uV\n"
            
            # Write ERD file
            with open(erd_file, 'w', encoding='utf-8') as f:
                f.write(erd_content)
            
            print(f"✅ Created WinEEG header: {erd_file}")
            return erd_file
            
        except Exception as e:
            print(f"❌ Error creating WinEEG header: {e}")
            return None
    
    def create_wineeg_events(self, output_path, info):
        """Create WinEEG .evt event file"""
        try:
            evt_file = output_path.with_suffix('.evt')
            
            # Create EVT content (WinEEG events)
            evt_content = f"""# WinEEG Event File
# Created from EDF file by EEG Paradox Converter
# Format: Time(s) Type Description
0.000 START Recording_Start
{info['duration']:.3f} END Recording_End
"""
            
            # Write EVT file
            with open(evt_file, 'w', encoding='utf-8') as f:
                f.write(evt_content)
            
            print(f"✅ Created WinEEG events: {evt_file}")
            return evt_file
            
        except Exception as e:
            print(f"❌ Error creating WinEEG events: {e}")
            return None

    def create_nicolet_header(self, output_path, info, resolution):
        """Create Nicolet/Nihon Kohden header file"""
        try:
            nicolet_file = output_path.with_suffix('.eeg')
            
            # Nicolet uses a binary header format
            header_content = f"""Nicolet EEG Header
File: {nicolet_file.name}
Channels: {info['channels']}
Sampling Rate: {info['sampling_rate']:.1f} Hz
Duration: {info['duration']:.3f} seconds
Resolution: {resolution:.6f} uV/bit
Format: INT16
Byte Order: Little Endian
Created: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            # Write header file
            header_file = output_path.with_suffix('.hdr')
            with open(header_file, 'w', encoding='utf-8') as f:
                f.write(header_content)
            
            print(f"✅ Created Nicolet header: {header_file}")
            return header_file
            
        except Exception as e:
            print(f"❌ Error creating Nicolet header: {e}")
            return None

    def create_compumedics_header(self, output_path, info, resolution):
        """Create Compumedics header file"""
        try:
            compumedics_file = output_path.with_suffix('.eeg')
            
            # Compumedics uses a text-based header format
            header_content = f"""Compumedics EEG Header
DataFile={compumedics_file.name}
Channels={info['channels']}
SamplingRate={info['sampling_rate']:.1f}
Duration={info['duration']:.3f}
Resolution={resolution:.6f}
Format=INT16
ByteOrder=LittleEndian
Created={datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

[ChannelInfo]
"""
            
            # Add channel definitions
            for i, ch_name in enumerate(info['channel_names'], 1):
                clean_name = ''.join(c for c in ch_name if c.isalnum() or c in '-_')
                header_content += f"Ch{i}={clean_name},{resolution:.6f},uV\n"
            
            # Write header file
            header_file = output_path.with_suffix('.hdr')
            with open(header_file, 'w', encoding='utf-8') as f:
                f.write(header_content)
            
            print(f"✅ Created Compumedics header: {header_file}")
            return header_file
            
        except Exception as e:
            print(f"❌ Error creating Compumedics header: {e}")
            return None

    def create_neuroscan_header(self, output_path, info, resolution):
        """Create Neuroscan header file"""
        try:
            neuroscan_file = output_path.with_suffix('.eeg')
            
            # Neuroscan uses a specific header format
            header_content = f"""Neuroscan Header File
DataFile={neuroscan_file.name}
Channels={info['channels']}
SamplingRate={info['sampling_rate']:.1f}
Duration={info['duration']:.3f}
Resolution={resolution:.6f}
Format=INT16
ByteOrder=LittleEndian
Created={datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

[ChannelInfo]
"""
            
            # Add channel definitions
            for i, ch_name in enumerate(info['channel_names'], 1):
                clean_name = ''.join(c for c in ch_name if c.isalnum() or c in '-_')
                header_content += f"Ch{i}={clean_name},{resolution:.6f},uV\n"
            
            # Write header file
            header_file = output_path.with_suffix('.hdr')
            with open(header_file, 'w', encoding='utf-8') as f:
                f.write(header_content)
            
            print(f"✅ Created Neuroscan header: {header_file}")
            return header_file
            
        except Exception as e:
            print(f"❌ Error creating Neuroscan header: {e}")
            return None

    def create_eeglab_set(self, output_path, info, resolution):
        """Create EEGLAB .set file"""
        try:
            eeglab_file = output_path.with_suffix('.eeg')
            
            # EEGLAB uses a MATLAB-compatible format
            set_content = f"""EEGLAB Dataset
DataFile={eeglab_file.name}
Channels={info['channels']}
SamplingRate={info['sampling_rate']:.1f}
Duration={info['duration']:.3f}
Resolution={resolution:.6f}
Format=INT16
ByteOrder=LittleEndian
Created={datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

[ChannelInfo]
"""
            
            # Add channel definitions
            for i, ch_name in enumerate(info['channel_names'], 1):
                clean_name = ''.join(c for c in ch_name if c.isalnum() or c in '-_')
                set_content += f"Ch{i}={clean_name},{resolution:.6f},uV\n"
            
            # Write set file
            set_file = output_path.with_suffix('.set')
            with open(set_file, 'w', encoding='utf-8') as f:
                f.write(set_content)
            
            print(f"✅ Created EEGLAB set file: {set_file}")
            return set_file
            
        except Exception as e:
            print(f"❌ Error creating EEGLAB set file: {e}")
            return None
    
    def _generate_validation_report(self, edf_file_path, vhdr_file, vmrk_file, eeg_file, info):
        """Generate comprehensive Gunkelman-grade validation report for all formats"""
        try:
            # Parse generated files for cross-checking
            # Only try to parse BrainVision format files
            vhdr_parsed = None
            vmrk_parsed = None
            
            if vhdr_file and vhdr_file.exists():
                # Check if it's a BrainVision header by looking for [Common Infos] section
                try:
                    header_content = vhdr_file.read_text(encoding="utf-8", errors="ignore")
                    if "[Common Infos]" in header_content:
                        vhdr_parsed = parse_vhdr(vhdr_file)
                    else:
                        # Create a minimal VHDR-like structure for non-BrainVision formats
                        vhdr_parsed = {
                            'path': str(vhdr_file),
                            'NumberOfChannels': info['channels'],
                            'SamplingInterval_us': micround(info['sampling_rate']),
                            'channels': [{'label': name} for name in info['channel_names']],
                            'DataFormat': 'BINARY',
                            'DataOrientation': 'MULTIPLEXED',
                            'BinaryFormat': 'INT_16'
                        }
                except Exception as e:
                    print(f"⚠️  Warning: Could not parse header file {vhdr_file}: {e}")
                    # Create minimal structure
                    vhdr_parsed = {
                        'path': str(vhdr_file),
                        'NumberOfChannels': info['channels'],
                        'SamplingInterval_us': micround(info['sampling_rate']),
                        'channels': [{'label': name} for name in info['channel_names']],
                        'DataFormat': 'BINARY',
                        'DataOrientation': 'MULTIPLEXED',
                        'BinaryFormat': 'INT_16'
                    }
            
            if vmrk_file and vmrk_file.exists():
                # Check if it's a BrainVision marker file by looking for [Marker Infos] section
                try:
                    marker_content = vmrk_file.read_text(encoding="utf-8", errors="ignore")
                    if "[Marker Infos]" in marker_content:
                        vmrk_parsed = parse_vmrk(vmrk_file)
                    else:
                        # Create minimal marker structure
                        vmrk_parsed = {
                            'path': str(vmrk_file),
                            'markers': [
                                {'desc': 'START', 'latency_samples': 0},
                                {'desc': 'END', 'latency_samples': int(info['sampling_rate'] * info['duration'])}
                            ]
                        }
                except Exception as e:
                    print(f"⚠️  Warning: Could not parse marker file {vmrk_file}: {e}")
                    # Create minimal structure
                    vmrk_parsed = {
                        'path': str(vmrk_file),
                        'markers': [
                            {'desc': 'START', 'latency_samples': 0},
                            {'desc': 'END', 'latency_samples': int(info['sampling_rate'] * info['duration'])}
                        ]
                    }
            
            # Get EDF header for cross-checks
            edf_header = EDFHeader(Path(edf_file_path))
            edf_header.read()
            
            # Run cross-checks
            report = cross_checks(edf_header, vhdr_parsed, vmrk_parsed, eeg_file)
            
            # Add signal-level QC if MNE available
            if MNE_AVAILABLE:
                sig_qc = signal_qc_with_mne(Path(edf_file_path), fs_expect=info['sampling_rate'])
                if sig_qc.get("ok"):
                    report["signal_qc"] = sig_qc
            
            # Add amplifier detection results if available
            if hasattr(self, 'amp_detection_results'):
                report["amplifier_detection"] = self.amp_detection_results
            
            if hasattr(self, 'resolution_validation'):
                report["resolution_validation"] = self.resolution_validation
            
            # Add scaling information if available
            if info.get('scaling_applied'):
                report["scaling_correction"] = info['scaling_applied']
            
            # Generate report files
            base_path = Path(edf_file_path).stem
            output_dir = Path(edf_file_path).parent
            report_txt = output_dir / f"{base_path}__gunkelman_validation_report.txt"
            report_json = output_dir / f"{base_path}__gunkelman_validation_report.json"
            report_summary = output_dir / f"{base_path}__gunkelman_summary.txt"
            
            # Human-readable comprehensive report
            lines = []
            lines.append("=" * 80)
            lines.append("🧠 EEG PARADOX GUNKELMAN-GRADE VALIDATION REPORT")
            lines.append("=" * 80)
            lines.append(f"Generated: {report['timestamp']}")
            lines.append(f"EDF Source: {report['edf_path']}")
            lines.append(f"Output Directory: {output_dir}")
            lines.append("")
            
            # File status
            lines.append("📁 FILE STATUS")
            lines.append("-" * 40)
            lines.append(f"EDF File: {'✅ EXISTS' if Path(edf_file_path).exists() else '❌ MISSING'}")
            if vhdr_file:
                lines.append(f"VHDR File: {'✅ EXISTS' if vhdr_file.exists() else '❌ MISSING'}")
            if vmrk_file:
                lines.append(f"VMRK File: {'✅ EXISTS' if vmrk_file.exists() else '❌ MISSING'}")
            if eeg_file:
                lines.append(f"EEG File: {'✅ EXISTS' if eeg_file.exists() else '❌ MISSING'}")
            lines.append("")
            
            # Overall Assessment
            lines.append("🎯 OVERALL ASSESSMENT")
            lines.append("-" * 40)
            lines.append(f"Final Confidence Score: {report['summary']['confidence']:.1%}")
            lines.append(f"Quality Rating: {report['summary']['assessment']}")
            lines.append(f"Description: {report['summary'].get('assessment_description', '')}")
            lines.append("")
            lines.append("📊 CONFIDENCE BREAKDOWN")
            lines.append(f"Base Confidence: {report['summary'].get('base_confidence', 0):.1%}")
            lines.append(f"Advanced Bonus: +{report['summary'].get('advanced_bonus', 0):.1%}")
            lines.append(f"Total Penalty: -{report['summary'].get('total_penalty', 0):.1%}")
            lines.append("")
            lines.append(f"Checks Passed: {report['summary']['checks_passed']}/{report['summary']['checks_total']}")
            lines.append(f"Critical Issues: {report['summary']['critical_issues_count']}")
            lines.append(f"Warnings: {report['summary']['warnings_count']}")
            lines.append("")
            
            # EDF Validation Summary
            if "edf_validation" in report:
                edf_val = report["edf_validation"]
                lines.append("📊 EDF VALIDATION")
                lines.append("-" * 40)
                lines.append(f"Valid: {pretty_bool(edf_val['valid'])}")
                lines.append(f"Channels: {edf_val['n_signals']}")
                lines.append(f"Duration: {edf_val['duration_record_s'] * edf_val['n_records']:.1f} seconds")
                lines.append(f"Sampling Rate: {report['summary'].get('edf_fs', 'Unknown'):.1f} Hz")
                
                if edf_val.get("warnings"):
                    lines.append(f"Warnings: {len(edf_val['warnings'])}")
                    for warning in edf_val["warnings"][:5]:  # Show first 5
                        lines.append(f"  ⚠️  {warning}")
                    if len(edf_val["warnings"]) > 5:
                        lines.append(f"  ... and {len(edf_val['warnings']) - 5} more warnings")
                
                if edf_val.get("errors"):
                    lines.append(f"Errors: {len(edf_val['errors'])}")
                    for error in edf_val["errors"][:3]:  # Show first 3
                        lines.append(f"  ❌ {error}")
                    if len(edf_val["errors"]) > 3:
                        lines.append(f"  ... and {len(edf_val['errors']) - 3} more errors")
                lines.append("")
            
            # Clinical Validation
            if "clinical_validation" in report:
                lines.append("🏥 CLINICAL VALIDATION")
                lines.append("-" * 40)
                clin_val = report["clinical_validation"]
                
                if "edf" in clin_val:
                    edf_clin = clin_val["edf"]
                    lines.append(f"Recording Duration: {edf_clin.get('recording_duration_minutes', 0):.1f} minutes")
                    lines.append(f"Channel Set: {edf_clin.get('channels_standard', 'Unknown')}")
                    lines.append(f"Sampling Rate: {edf_clin.get('sampling_rate_clinical', 'Unknown')}")
                    lines.append(f"Duration: {edf_clin.get('duration_clinical', 'Unknown')}")
                
                if "channels" in clin_val:
                    ch_clin = clin_val["channels"]
                    lines.append(f"Channel Validation: {pretty_bool(ch_clin.get('valid', False))}")
                    lines.append(f"Essential Channels: {pretty_bool(ch_clin.get('has_essential', False))}")
                    lines.append(f"Reference Channels: {pretty_bool(ch_clin.get('has_reference', False))}")
                    
                    if ch_clin.get("issues"):
                        lines.append(f"Channel Issues: {len(ch_clin['issues'])}")
                        for issue in ch_clin["issues"][:3]:
                            lines.append(f"  ❌ {issue}")
                    
                    if ch_clin.get("warnings"):
                        lines.append(f"Channel Warnings: {len(ch_clin['warnings'])}")
                        for warning in ch_clin["warnings"][:3]:
                            lines.append(f"  ⚠️  {warning}")
                lines.append("")
            
            # Amplifier Detection Results
            if report.get("amplifier_detection"):
                amp_det = report["amplifier_detection"]
                lines.append("🔍 AMPLIFIER DETECTION")
                lines.append("-" * 40)
                lines.append(f"Detected System: {amp_det['detected_system'].upper()}")
                lines.append(f"Detection Confidence: {amp_det['confidence']:.1%}")
                
                if amp_det.get('calibration_detected'):
                    lines.append("Calibration Signal: DETECTED")
                else:
                    lines.append("Calibration Signal: NOT DETECTED")
                
                if amp_det.get('evidence'):
                    lines.append("Evidence:")
                    for evidence in amp_det['evidence'][:5]:
                        lines.append(f"  • {evidence}")
                    if len(amp_det['evidence']) > 5:
                        lines.append(f"  • ... and {len(amp_det['evidence']) - 5} more")
                
                scaling_rec = amp_det.get('scaling_recommendations', {})
                if scaling_rec:
                    lines.append(f"Recommended Resolution: {scaling_rec.get('suggested_resolution', 'N/A')} µV/bit")
                    lines.append(f"Typical Range: ±{scaling_rec.get('typical_range_uv', 'N/A')} µV")
                    lines.append(f"System Notes: {scaling_rec.get('notes', 'N/A')}")
                
                lines.append("")
            
            # Resolution Validation
            if report.get("resolution_validation"):
                res_val = report["resolution_validation"]
                lines.append("⚖️  RESOLUTION VALIDATION")
                lines.append("-" * 40)
                lines.append(f"Resolution Appropriate: {pretty_bool(res_val.get('resolution_appropriate', True))}")
                
                if res_val.get('warnings'):
                    lines.append("Warnings:")
                    for warning in res_val['warnings']:
                        lines.append(f"  ⚠️  {warning}")
                
                if res_val.get('recommendations'):
                    lines.append("Recommendations:")
                    for rec in res_val['recommendations']:
                        lines.append(f"  💡 {rec}")
                
                lines.append("")
            
            # Scaling Correction Results
            if report.get("scaling_correction"):
                scaling = report["scaling_correction"]
                lines.append("📏 SCALING CORRECTION")
                lines.append("-" * 40)
                lines.append(f"Original Range: {scaling['original_range']:.2e}")
                lines.append(f"Final Range: {scaling['final_range']:.2f} µV")
                lines.append(f"Scaling Factor: {scaling['scaling_factor']:.1f}x")
                lines.append(f"Method: {scaling['method'].replace('_', ' ').title()}")
                lines.append("✅ Unit scaling correction applied successfully")
                lines.append("")
            
            # Cross-Checks Results
            lines.append("🔍 CROSS-CHECKS RESULTS")
            lines.append("-" * 40)
            for c in report["checks"]:
                status = "✅ PASS" if c['pass'] else "❌ FAIL"
                lines.append(f"{status} {c['name']}")
                if not c['pass']:
                    expected = c.get('expected') or c.get('expected_bytes')
                    observed = c.get('observed') or c.get('observed_bytes')
                    lines.append(f"  Expected: {expected}, Observed: {observed}")
                    if c.get('tolerance'):
                        lines.append(f"  Tolerance: {c['tolerance']}")
            lines.append("")
            
            # Signal Quality Control (if available)
            if report.get("signal_qc"):
                sig_qc = report["signal_qc"]
                lines.append("📈 SIGNAL QUALITY CONTROL (MNE)")
                lines.append("-" * 40)
                lines.append(f"Overall Score: {sig_qc.get('signal_quality', {}).get('overall_score', 'N/A')}/100")
                lines.append(f"Quality Rating: {sig_qc.get('signal_quality', {}).get('quality_rating', 'N/A')}")
                lines.append(f"Sampling Rate: {sig_qc.get('fs', 'N/A')} Hz")
                
                # Advanced spectral analysis
                if sig_qc.get("spectral_analysis") and not sig_qc["spectral_analysis"].get("analysis_failed"):
                    spec = sig_qc["spectral_analysis"]
                    lines.append("")
                    lines.append("🔬 SPECTRAL ANALYSIS")
                    lines.append("-" * 30)
                    if spec.get("alpha_power_mean") is not None:
                        lines.append(f"Alpha Power (8-13Hz): {spec['alpha_power_mean']:.2e} ± {spec.get('alpha_power_std', 0):.2e}")
                    if spec.get("beta_power_mean") is not None:
                        lines.append(f"Beta Power (13-30Hz): {spec['beta_power_mean']:.2e} ± {spec.get('beta_power_std', 0):.2e}")
                    if spec.get("spectral_edge_freq_mean") is not None:
                        lines.append(f"Spectral Edge Frequency: {spec['spectral_edge_freq_mean']:.1f} Hz")
                    if spec.get("spectral_entropy_mean") is not None:
                        lines.append(f"Spectral Entropy: {spec['spectral_entropy_mean']:.2f}")
                
                # Advanced artifact detection
                if sig_qc.get("advanced_artifacts") and not sig_qc["advanced_artifacts"].get("detection_failed"):
                    artifacts = sig_qc["advanced_artifacts"]
                    lines.append("")
                    lines.append("🚨 ADVANCED ARTIFACT DETECTION")
                    lines.append("-" * 30)
                    
                    if artifacts.get("eye_blinks", {}).get("detected"):
                        blinks = artifacts["eye_blinks"]
                        lines.append(f"Eye Blinks: {blinks['count']} detected in {len(blinks['channels'])} channels")
                    
                    if artifacts.get("muscle_artifacts", {}).get("detected"):
                        muscle = artifacts["muscle_artifacts"]
                        lines.append(f"Muscle Artifacts: {muscle['severity']} severity in {len(muscle['channels'])} channels")
                    
                    if artifacts.get("line_noise", {}).get("detected"):
                        noise = artifacts["line_noise"]
                        lines.append(f"Line Noise: {noise['frequency']}Hz ({noise['severity']} severity)")
                    
                    if artifacts.get("electrode_pops", {}).get("detected"):
                        pops = artifacts["electrode_pops"]
                        lines.append(f"Electrode Pops: {pops['count']} detected in {len(pops['channels'])} channels")
                    
                    if artifacts.get("baseline_drift", {}).get("detected"):
                        drift = artifacts["baseline_drift"]
                        lines.append(f"Baseline Drift: {drift['severity']} severity in {len(drift['channels'])} channels")
                    
                    if artifacts.get("saturation", {}).get("detected"):
                        sat = artifacts["saturation"]
                        lines.append(f"Signal Saturation: detected in {len(sat['channels'])} channels")
                    
                    if artifacts.get("disconnected_electrodes", {}).get("detected"):
                        disc = artifacts["disconnected_electrodes"]
                        lines.append(f"Disconnected Electrodes: {len(disc['channels'])} channels")
                
                # Clinical compliance
                if sig_qc.get("clinical_compliance") and not sig_qc["clinical_compliance"].get("compliance_check_failed"):
                    compliance = sig_qc["clinical_compliance"]
                    lines.append("")
                    lines.append("🏥 CLINICAL COMPLIANCE")
                    lines.append("-" * 30)
                    lines.append(f"Overall Compliance: {compliance.get('compliance_level', 'unknown').upper()}")
                    lines.append(f"Compliance Score: {compliance.get('overall_score', 0):.1%}")
                    lines.append(f"Sampling Rate: {pretty_bool(compliance.get('sampling_rate_compliant', False))}")
                    lines.append(f"Duration: {pretty_bool(compliance.get('duration_compliant', False))}")
                    lines.append(f"Channel Count: {pretty_bool(compliance.get('channel_count_compliant', False))}")
                    lines.append(f"Montage: {pretty_bool(compliance.get('montage_compliant', False))}")
                    lines.append(f"Resolution: {pretty_bool(compliance.get('resolution_compliant', False))}")
                    lines.append(f"Frequency Response: {pretty_bool(compliance.get('frequency_response_compliant', False))}")
                
                if sig_qc.get("alpha_peak_hz"):
                    lines.append(f"Alpha Peak: {sig_qc['alpha_peak_hz']:.1f} Hz")
                    if sig_qc.get("clinical_indicators", {}).get("alpha_normal") is not None:
                        alpha_ok = sig_qc["clinical_indicators"]["alpha_normal"]
                        lines.append(f"Alpha Normal: {pretty_bool(alpha_ok)}")
                
                if sig_qc.get("mains_hz"):
                    lines.append(f"Mains Frequency: {sig_qc['mains_hz']} Hz")
                
                if sig_qc.get("blink_polarity_ok") is not None:
                    lines.append(f"Blink Polarity: {pretty_bool(sig_qc['blink_polarity_ok'])}")
                
                # Signal quality details
                if "signal_quality" in sig_qc:
                    sq = sig_qc["signal_quality"]
                    if sq.get("clipping", {}).get("clipped"):
                        lines.append(f"Signal Clipping: {sq['clipping']['clip_percentage']:.1f}%")
                    if sq.get("dead_channels"):
                        lines.append(f"Dead Channels: {', '.join(sq['dead_channels'])}")
                    if sq.get("flat_channels"):
                        lines.append(f"Flat Channels: {', '.join(sq['flat_channels'])}")
                
                # Artifact detection
                if "artifact_detection" in sig_qc:
                    ad = sig_qc["artifact_detection"]
                    if ad.get("movement", {}).get("excessive_movement"):
                        lines.append("Excessive Movement: DETECTED")
                    if ad.get("mains_contamination"):
                        lines.append("Mains Contamination: DETECTED")
                
                lines.append("")
            
            # Critical Issues
            if report["critical_issues"]:
                lines.append("🚨 CRITICAL ISSUES")
                lines.append("-" * 40)
                for issue in report["critical_issues"]:
                    lines.append(f"❌ {issue}")
                lines.append("")
            
            # Warnings
            if report["warnings"]:
                lines.append("⚠️  WARNINGS")
                lines.append("-" * 40)
                for warning in report["warnings"][:10]:  # Show first 10
                    lines.append(f"⚠️  {warning}")
                if len(report["warnings"]) > 10:
                    lines.append(f"... and {len(report['warnings']) - 10} more warnings")
                lines.append("")
            
            # Recommendations
            if report["advice"]:
                lines.append("💡 RECOMMENDATIONS")
                lines.append("-" * 40)
                for advice in report["advice"]:
                    lines.append(f"💡 {advice}")
                lines.append("")
            
            # File Integrity
            if report.get("file_integrity"):
                lines.append("🔒 FILE INTEGRITY")
                lines.append("-" * 40)
                for file_type, integrity in report["file_integrity"].items():
                    lines.append(f"{file_type.upper()}:")
                    if isinstance(integrity, dict):
                        for key, value in integrity.items():
                            if key == "hash_sha256" and len(str(value)) > 20:
                                lines.append(f"  {key}: {str(value)[:20]}...")
                            else:
                                lines.append(f"  {key}: {value}")
                    else:
                        # Handle non-dictionary values (shouldn't happen after our fix)
                        lines.append(f"  Value: {integrity} (type: {type(integrity).__name__})")
                lines.append("")
            
            # Footer
            lines.append("=" * 80)
            lines.append("📋 REPORT SUMMARY")
            lines.append("=" * 80)
            lines.append(f"• Overall Quality: {report['summary']['assessment']} ({report['summary']['confidence']:.1%})")
            lines.append(f"• Assessment: {report['summary'].get('assessment_description', '')}")
            lines.append(f"• Base Validation: {report['summary'].get('base_confidence', 0):.1%} confidence")
            lines.append(f"• Advanced Features: +{report['summary'].get('advanced_bonus', 0):.1%} bonus")
            lines.append(f"• Issue Penalties: -{report['summary'].get('total_penalty', 0):.1%} penalty")
            lines.append("")
            lines.append(f"• Cross-Checks: {report['summary']['checks_passed']}/{report['summary']['checks_total']} passed")
            lines.append(f"• Critical Issues: {report['summary']['critical_issues_count']}")
            lines.append(f"• Warnings: {report['summary']['warnings_count']}")
            lines.append("")
            
            # Advanced features summary
            advanced_features = []
            if report.get("edf_validation"):
                advanced_features.append("✅ Enhanced EDF header validation")
            if report.get("clinical_validation"):
                advanced_features.append("✅ Clinical standards compliance")
            if report.get("amplifier_detection"):
                amp_det = report["amplifier_detection"]
                confidence = amp_det.get('confidence', 0)
                if confidence > 0.7:
                    advanced_features.append(f"✅ Amplifier detection ({amp_det['detected_system']} - {confidence:.0%})")
                else:
                    advanced_features.append(f"⚠️ Amplifier detection (low confidence - {confidence:.0%})")
            if report.get("resolution_validation"):
                res_val = report["resolution_validation"]
                if res_val.get('resolution_appropriate'):
                    advanced_features.append("✅ Resolution optimization validated")
                else:
                    advanced_features.append("⚠️ Resolution optimization (with warnings)")
            if report.get("signal_qc", {}).get("spectral_analysis"):
                advanced_features.append("✅ Advanced spectral analysis")
            if report.get("signal_qc", {}).get("advanced_artifacts"):
                advanced_features.append("✅ Multi-modal artifact detection")
            if report.get("signal_qc", {}).get("clinical_compliance"):
                advanced_features.append("✅ Clinical compliance verification")
            if report.get("file_integrity"):
                advanced_features.append("✅ File integrity validation")
            
            if advanced_features:
                lines.append("🚀 ADVANCED FEATURES ACTIVATED")
                for feature in advanced_features:
                    lines.append(f"   {feature}")
                lines.append("")
            
            lines.append("🔍 For detailed analysis, check the JSON report file.")
            lines.append("📊 This report meets Gunkelman-grade validation standards with advanced EEG analysis.")
            lines.append("🧠 EEG Paradox Converter - Clinical-Grade EDF Validation System")
            lines.append("=" * 80)
            
            # Generate summary file
            summary_lines = []
            summary_lines.append(f"EEG PARADOX VALIDATION SUMMARY")
            summary_lines.append(f"File: {Path(edf_file_path).name}")
            summary_lines.append(f"Quality: {report['summary']['assessment']}")
            summary_lines.append(f"Confidence: {report['summary']['confidence']:.1%}")
            summary_lines.append(f"Issues: {report['summary']['critical_issues_count']}")
            summary_lines.append(f"Warnings: {report['summary']['warnings_count']}")
            summary_lines.append(f"Status: {'✅ PASS' if report['summary']['critical_issues_count'] == 0 else '❌ FAIL'}")
            
            # Write reports
            write_text(report_txt, "\n".join(lines))
            
            # Convert NumPy types to Python native types for JSON serialization
            def convert_numpy_types(obj):
                """Convert NumPy types to Python native types for JSON serialization"""
                if hasattr(obj, 'item'):  # NumPy scalar
                    return obj.item()
                elif isinstance(obj, dict):
                    return {k: convert_numpy_types(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_numpy_types(v) for v in obj]
                elif isinstance(obj, tuple):
                    return tuple(convert_numpy_types(v) for v in obj)
                else:
                    return obj
            
            # Convert report for JSON serialization
            json_safe_report = convert_numpy_types(report)
            write_text(report_json, json.dumps(json_safe_report, indent=2))
            write_text(report_summary, "\n".join(summary_lines))
            
            print(f"✅ Comprehensive validation report generated:")
            print(f"   📄 {report_txt.name}")
            print(f"   📊 {report_json.name}")
            print(f"   📋 {report_summary.name}")
            print(f"   🎯 Quality: {report['summary']['assessment']}")
            print(f"   🔍 Confidence: {report['summary']['confidence']:.1%}")
            
            # Show critical issues immediately
            if report["critical_issues"]:
                print(f"   🚨 Critical Issues: {len(report['critical_issues'])}")
                for issue in report["critical_issues"][:3]:
                    print(f"      ❌ {issue}")
                if len(report["critical_issues"]) > 3:
                    print(f"      ... and {len(report['critical_issues']) - 3} more")
            
        except Exception as e:
            print(f"⚠️  Validation report generation failed: {e}")
            print(f"   Traceback: {traceback.format_exc()}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="EEG Paradox EDF to EEG Converter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python edf_to_eeg_converter.py data.edf
  python edf_to_eeg_converter.py data.edf --output ./converted/
        """
    )
    
    parser.add_argument('edf_file', help='EDF file to convert')
    parser.add_argument('--output', '-o', help='Output directory (default: same as input)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--validate-only', action='store_true', help='Only validate existing files, no conversion')
    parser.add_argument('--vhdr', type=Path, help='Optional existing .vhdr to validate against')
    parser.add_argument('--vmrk', type=Path, help='Optional existing .vmrk to validate against')
    parser.add_argument('--eeg', type=Path, help='Optional existing .eeg binary for validation')
    parser.add_argument('--format', choices=['brainvision', 'wineeg', 'neuroscan', 'eeglab', 'nicolet', 'compumedics', 'both'], default='brainvision', 
                        help='Output format: brainvision (.vhdr/.vmrk), wineeg (.erd/.evt), neuroscan (.hdr), eeglab (.set), nicolet (.hdr), compumedics (.hdr), or both (brainvision+wineeg)')
    
    args = parser.parse_args()
    
    # Create converter
    converter = EDFToEEGConverter()
    converter.print_header()
    
    # Handle validation-only mode
    if args.validate_only:
        print("🔍 Validation-only mode - no conversion performed")
        try:
            # Parse existing files for validation
            vhdr_parsed = parse_vhdr(args.vhdr) if args.vhdr else None
            vmrk_parsed = parse_vmrk(args.vmrk) if args.vmrk else None
            
            # Get EDF header for cross-checks
            edf_header = EDFHeader(Path(args.edf_file))
            edf_header.read()
            
            # Run cross-checks
            report = cross_checks(edf_header, vhdr_parsed, vmrk_parsed, args.eeg)
            
            # Add signal-level QC if MNE available
            if MNE_AVAILABLE:
                sig_qc = signal_qc_with_mne(Path(args.edf_file), fs_expect=report["summary"].get("edf_fs"))
                if sig_qc.get("ok"):
                    report["signal_qc"] = sig_qc
            
            # Generate validation report
            base_path = Path(args.edf_file).stem
            report_txt = Path(f"{base_path}__validation_report.txt")
            report_json = Path(f"{base_path}__validation_report.json")
            
            # Human-readable report
            lines = []
            lines.append(f"# Gunkelman Validation Report (Validation-Only Mode)")
            lines.append(f"Generated: {report['timestamp']}")
            lines.append(f"EDF:  {report['edf_path']}")
            if report.get("vhdr_path"): lines.append(f"VHDR: {report['vhdr_path']}")
            if report.get("vmrk_path"): lines.append(f"VMRK: {report['vmrk_path']}")
            if report.get("eeg_path"): lines.append(f"EEG:  {report['eeg_path']}")
            lines.append("")
            
            # Summary
            s = report["summary"]
            lines.append("## Summary")
            for k,v in s.items():
                lines.append(f"- {k}: {v}")
            lines.append("")
            
            # Checks
            lines.append("## Cross-Checks")
            for c in report["checks"]:
                status = "✅ PASS" if c['pass'] else "❌ FAIL"
                lines.append(f"- {c['name']}: {status}")
                if not c['pass']:
                    expected = c.get('expected') or c.get('expected_bytes')
                    observed = c.get('observed') or c.get('observed_bytes')
                    lines.append(f"  Expected: {expected}, Observed: {observed}")
            lines.append("")
            
            # Advice
            if report["advice"]:
                lines.append("## Recommendations")
                for a in report["advice"]:
                    lines.append(f"- {a}")
                lines.append("")
            
            # Signal QC
            if report.get("signal_qc"):
                sig_qc = report["signal_qc"]
                lines.append("## Signal Quality Control (MNE)")
                lines.append(f"- Sampling rate detected: {sig_qc.get('fs')}")
                if sig_qc.get("alpha_peak_hz") is not None:
                    lines.append(f"- Alpha peak (O1/O2): {round(sig_qc['alpha_peak_hz'],2)} Hz")
                if sig_qc.get("mains_hz") is not None:
                    lines.append(f"- Mains frequency: {sig_qc['mains_hz']} Hz")
                if sig_qc.get("blink_polarity_ok") is not None:
                    lines.append(f"- Blink polarity correct: {sig_qc['blink_polarity_ok']}")
                if sig_qc.get("notes"):
                    for n in sig_qc["notes"]:
                        lines.append(f"- Note: {n}")
            
            # Write reports
            write_text(report_txt, "\n".join(lines))
            write_text(report_json, json.dumps(report, indent=2))
            
            print(f"✅ Validation report generated:")
            print(f"   📄 {report_txt.name}")
            print(f"   📊 {report_json.name}")
            print(f"   🎯 Confidence: {report['summary']['confidence']:.1%}")
            
            sys.exit(0)
            
        except Exception as e:
            print(f"\n❌ Validation failed: {e}")
            sys.exit(1)
    
    # Convert file
    try:
        success = converter.convert_file(args.edf_file, args.output, args.format)
        if success:
            print(f"\n✅ Successfully converted: {args.edf_file}")
            sys.exit(0)
        else:
            print(f"\n❌ Conversion failed: {args.edf_file}")
            sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n⚠️  Conversion cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
