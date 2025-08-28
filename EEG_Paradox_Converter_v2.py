#!/usr/bin/env python3
"""
EEG Paradox WinEEG Converter v2.0
==================================
This is a simple converter that converts EDF files to WinEEG format.
It is a simple converter that converts EDF files to WinEEG format.
It is a simple converter that converts EDF files to WinEEG format.
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
from datetime import datetime
import numpy as np
from pathlib import Path

# Add the current directory to path for imports
sys.path.append(os.path.dirname(__file__))

class EEGConverter:
    def __init__(self, root):
        self.root = root
        self.setup_ui()
        self.edf_file = None
        self.output_file = None
        self.conversion_thread = None
        
    def setup_ui(self):
        """Setup cyberpunk UI"""
        self.root.title("EEG PARADOX | WinEEG Converter v2.0 | El Chaderino")
        self.root.geometry("1000x750")
        self.root.configure(bg='#000000')
        self.root.resizable(True, True)
        
        # Create main container with terminal-style border
        main_container = tk.Frame(self.root, bg='#000000', bd=3, relief='raised')
        main_container.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Header section
        self.create_header(main_container)
        
        # Main content area
        content_frame = tk.Frame(main_container, bg='#000000')
        content_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Left panel - File operations
        left_panel = tk.Frame(content_frame, bg='#001100', bd=2, relief='solid')
        left_panel.pack(side='left', fill='both', expand=True, padx=(0, 5))
        
        # Right panel - Status and controls
        right_panel = tk.Frame(content_frame, bg='#110000', bd=2, relief='solid')
        right_panel.pack(side='right', fill='y', padx=(5, 0))
        right_panel.configure(width=300)
        
        # Setup panels
        self.setup_file_panel(left_panel)
        self.setup_control_panel(right_panel)
        
        # Footer
        self.create_footer(main_container)
        
    def create_header(self, parent):
        """Create header"""
        header_frame = tk.Frame(parent, bg='#000000', height=120)
        header_frame.pack(fill='x', pady=(10, 20))
        header_frame.pack_propagate(False)
        
        # ASCII Art Title
        title_text = """
███████╗███████╗ ██████╗     ██████╗  █████╗ ██████╗  █████╗ ██████╗  ██████╗ ██╗  ██╗
██╔════╝██╔════╝██╔════╝     ██╔══██╗██╔══██╗██╔══██╗██╔══██╗██╔══██╗██╔═══██╗╚██╗██╔╝
█████╗  █████╗  ██║  ███╗    ██████╔╝███████║██████╔╝███████║██║  ██║██║   ██║ ╚███╔╝ 
██╔══╝  ██╔══╝  ██║   ██║    ██╔═══╝ ██╔══██║██╔══██╗██╔══██║██║  ██║██║   ██║ ██╔██╗ 
███████╗███████╗╚██████╔╝    ██║     ██║  ██║██║  ██║██║  ██║██████╔╝╚██████╔╝██╔╝ ██╗
╚══════╝╚══════╝ ╚═════╝     ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝  ╚═════╝ ╚═╝  ╚═╝"""
        
        title_label = tk.Label(header_frame, text=title_text.strip(), 
                              bg='#000000', fg='#ff0080', 
                              font=('Consolas', 7, 'bold'))
        title_label.pack(pady=(5, 0))
        
        # Subtitle
        subtitle_frame = tk.Frame(header_frame, bg='#000000')
        subtitle_frame.pack(fill='x', pady=(5, 0))
        
        subtitle1 = tk.Label(subtitle_frame, text="[=] Modded EDF >> WinEEG CONVERTER [=]", 
                             bg='#000000', fg='#00ff41', font=('Consolas', 11, 'bold'))
        subtitle1.pack()
        
        subtitle2 = tk.Label(subtitle_frame, text="[+] Format Modded by El Chaderino | v2.0 [+]", 
                             bg='#000000', fg='#ffff00', font=('Consolas', 9))
        subtitle2.pack()
        
        # Animated separator
        separator = tk.Frame(header_frame, height=3, bg='#00ff41')
        separator.pack(fill='x', pady=(5, 0))
        
    def setup_file_panel(self, parent):
        """Setup file operations panel"""
        # Panel title
        title_frame = tk.Frame(parent, bg='#001100')
        title_frame.pack(fill='x', pady=(5, 10))
        
        title_label = tk.Label(title_frame, text="[FILE OPERATIONS]", 
                              bg='#001100', fg='#00ff41', 
                              font=('Consolas', 12, 'bold'))
        title_label.pack()
        
        # EDF Input Section
        input_section = tk.LabelFrame(parent, text="[INPUT] EDF FILE", 
                                     bg='#001100', fg='#00ff41', 
                                     font=('Consolas', 10, 'bold'),
                                     bd=2, relief='solid')
        input_section.pack(fill='x', padx=10, pady=(0, 10))
        
        # File path display
        self.file_path_var = tk.StringVar(value="[NO FILE SELECTED]")
        file_display = tk.Entry(input_section, textvariable=self.file_path_var,
                               bg='#002200', fg='#00ff41', 
                               font=('Consolas', 9),
                               state='readonly', bd=1, relief='solid')
        file_display.pack(fill='x', padx=10, pady=5)
        
        # File buttons
        file_buttons = tk.Frame(input_section, bg='#001100')
        file_buttons.pack(fill='x', padx=10, pady=(0, 10))
        
        browse_btn = tk.Button(file_buttons, text="[BROWSE]", 
                              command=self.browse_edf_file,
                              bg='#003300', fg='#00ff41', 
                              font=('Consolas', 9, 'bold'),
                              bd=2, relief='raised',
                              activebackground='#00ff41', activeforeground='#000000')
        browse_btn.pack(side='left', padx=(0, 5))
        
        clear_btn = tk.Button(file_buttons, text="[CLEAR]", 
                             command=self.clear_file,
                             bg='#330000', fg='#ff4444', 
                             font=('Consolas', 9, 'bold'),
                             bd=2, relief='raised',
                             activebackground='#ff4444', activeforeground='#000000')
        clear_btn.pack(side='left')
        
        # Drop zone
        drop_frame = tk.Frame(input_section, bg='#002200', bd=2, relief='ridge')
        drop_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        drop_label = tk.Label(drop_frame, text="[DRAG & DROP EDF FILE HERE]", 
                             bg='#002200', fg='#888888', 
                             font=('Consolas', 10))
        drop_label.pack(pady=15)
        
        # Output Section
        output_section = tk.LabelFrame(parent, text="[OUTPUT] WinEEG FILE", 
                                      bg='#001100', fg='#00ff41', 
                                      font=('Consolas', 10, 'bold'),
                                      bd=2, relief='solid')
        output_section.pack(fill='x', padx=10, pady=(0, 10))
        
        # Output path
        self.output_path_var = tk.StringVar(value="[AUTO-GENERATED]")
        output_display = tk.Entry(output_section, textvariable=self.output_path_var,
                                 bg='#002200', fg='#00ff41', 
                                 font=('Consolas', 9),
                                 state='readonly', bd=1, relief='solid')
        output_display.pack(fill='x', padx=10, pady=5)
        
        # Output buttons
        output_buttons = tk.Frame(output_section, bg='#001100')
        output_buttons.pack(fill='x', padx=10, pady=(0, 10))
        
        save_as_btn = tk.Button(output_buttons, text="[SAVE AS]", 
                               command=self.browse_output_file,
                               bg='#003300', fg='#00ff41', 
                               font=('Consolas', 9, 'bold'),
                               bd=2, relief='raised',
                               activebackground='#00ff41', activeforeground='#000000')
        save_as_btn.pack(side='left')
        
        # Patient Info Section
        patient_section = tk.LabelFrame(parent, text="[PATIENT] IDENTIFICATION", 
                                       bg='#001100', fg='#00ff41', 
                                       font=('Consolas', 10, 'bold'),
                                       bd=2, relief='solid')
        patient_section.pack(fill='x', padx=10, pady=(0, 10))
        
        # Patient name
        patient_label = tk.Label(patient_section, text="Patient Name:", 
                                bg='#001100', fg='#00ff41', 
                                font=('Consolas', 9))
        patient_label.pack(anchor='w', padx=10, pady=(5, 0))
        
        self.patient_var = tk.StringVar(value="EEG_PARADOX_PATIENT_001")
        patient_entry = tk.Entry(patient_section, textvariable=self.patient_var,
                                bg='#002200', fg='#00ff41', 
                                font=('Consolas', 9),
                                bd=1, relief='solid')
        patient_entry.pack(fill='x', padx=10, pady=(0, 10))
        
    def setup_control_panel(self, parent):
        """Setup control and status panel"""
        # Panel title
        title_frame = tk.Frame(parent, bg='#110000')
        title_frame.pack(fill='x', pady=(5, 10))
        
        title_label = tk.Label(title_frame, text="[CONTROL PANEL]", 
                              bg='#110000', fg='#ff4444', 
                              font=('Consolas', 12, 'bold'))
        title_label.pack()
        
        # Status section
        status_section = tk.LabelFrame(parent, text="[STATUS]", 
                                      bg='#110000', fg='#ff4444', 
                                      font=('Consolas', 10, 'bold'),
                                      bd=2, relief='solid')
        status_section.pack(fill='x', padx=10, pady=(0, 10))
        
        # Status display
        self.status_var = tk.StringVar(value="[READY] Load EDF file to begin")
        status_display = tk.Text(status_section, height=8, width=35,
                                bg='#220000', fg='#ff4444', 
                                font=('Consolas', 8),
                                bd=1, relief='solid',
                                state='disabled')
        status_display.pack(fill='both', padx=5, pady=5)
        self.status_display = status_display
        
        # Progress bar
        self.progress_var = tk.StringVar(value="READY")
        progress_label = tk.Label(status_section, textvariable=self.progress_var,
                                 bg='#110000', fg='#ffff00', 
                                 font=('Consolas', 9, 'bold'))
        progress_label.pack(pady=5)
        
        # Main convert button
        convert_section = tk.LabelFrame(parent, text="[EXECUTE]", 
                                       bg='#110000', fg='#ff4444', 
                                       font=('Consolas', 10, 'bold'),
                                       bd=2, relief='solid')
        convert_section.pack(fill='x', padx=10, pady=(0, 10))
        
        # THE CONVERT BUTTON (finally!)
        self.convert_btn = tk.Button(convert_section, 
                                    text="[MOD AND CONVERT]\nEDF >> WinEEG", 
                                    command=self.start_conversion,
                                    bg='#003300', fg='#00ff41', 
                                    font=('Consolas', 11, 'bold'),
                                    bd=3, relief='raised',
                                    height=3,
                                    activebackground='#00ff41', 
                                    activeforeground='#000000',
                                    state='disabled')
        self.convert_btn.pack(fill='x', padx=10, pady=10)
        
        # System info
        info_section = tk.LabelFrame(parent, text="[SYSTEM INFO]", 
                                    bg='#110000', fg='#ff4444', 
                                    font=('Consolas', 10, 'bold'),
                                    bd=2, relief='solid')
        info_section.pack(fill='x', padx=10, pady=(0, 10))
        
        info_text = f"""Python: {sys.version_info.major}.{sys.version_info.minor}
OS: Windows
Time: {datetime.now().strftime("%H:%M:%S")}
User: El Chaderino"""
        
        info_label = tk.Label(info_section, text=info_text,
                             bg='#110000', fg='#888888', 
                             font=('Consolas', 8),
                             justify='left')
        info_label.pack(padx=10, pady=5)
        
    def create_footer(self, parent):
        """Create footer with credits"""
        footer_frame = tk.Frame(parent, bg='#000000', height=40)
        footer_frame.pack(fill='x', side='bottom')
        footer_frame.pack_propagate(False)
        
        # Separator
        separator = tk.Frame(footer_frame, height=2, bg='#ff0080')
        separator.pack(fill='x', pady=(5, 5))
        
        # Credits
        credits = tk.Label(footer_frame, 
                          text="[Modded] WinEEG Format | [BY] El Chaderino | [LICENSE] GPL-3",
                          bg='#000000', fg='#888888', 
                          font=('Consolas', 8))
        credits.pack()
        
    def log_status(self, message, color='#ff4444'):
        """Add message to status log"""
        self.status_display.configure(state='normal')
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {message}\n"
        self.status_display.insert(tk.END, formatted_msg)
        self.status_display.configure(state='disabled')
        self.status_display.see(tk.END)
        self.root.update()
        
    def browse_edf_file(self):
        """Browse for EDF file"""
        file_path = filedialog.askopenfilename(
            title="Select EDF File",
            filetypes=[("EDF files", "*.edf"), ("All files", "*.*")]
        )
        
        if file_path:
            self.load_edf_file(file_path)
    
    def load_edf_file(self, file_path):
        """Load and analyze EDF file"""
        try:
            self.edf_file = file_path
            filename = os.path.basename(file_path)
            self.file_path_var.set(f"[LOADED] {filename}")
            
            self.log_status(f"EDF file loaded: {filename}", '#00ff41')
            self.log_status("Analyzing file structure...", '#ffff00')
            
            # Try to analyze with MNE
            try:
                import mne
                raw = mne.io.read_raw_edf(file_path, preload=False, verbose=False)
                duration_sec = raw.times[-1]
                duration_min = duration_sec / 60
                n_channels = len(raw.ch_names)
                sfreq = raw.info['sfreq']
                
                self.log_status(f"Channels: {n_channels} | Duration: {duration_min:.1f}min | Rate: {sfreq:.0f}Hz", '#00ff41')
                
                if n_channels != 19:
                    self.log_status(f"WARNING: Expected 19 channels, got {n_channels}", '#ffff00')
                
            except ImportError:
                self.log_status("MNE not available, using basic analysis", '#ffff00')
            
            # Set default output filename
            base_name = os.path.splitext(filename)[0]
            output_name = f"{base_name}_PARADOX_WinEEG.eeg"
            output_dir = os.path.dirname(file_path)
            self.output_file = os.path.join(output_dir, output_name)
            self.output_path_var.set(f"[AUTO] {output_name}")
            
            # Enable convert button
            self.convert_btn.configure(state='normal', bg='#004400')
            self.log_status("READY TO CONVERT", '#00ff41')
            self.progress_var.set("LOADED - READY")
            
        except Exception as e:
            self.log_status(f"ERROR loading file: {str(e)}", '#ff0000')
            self.progress_var.set("ERROR")
    
    def clear_file(self):
        """Clear loaded file"""
        self.edf_file = None
        self.output_file = None
        self.file_path_var.set("[NO FILE SELECTED]")
        self.output_path_var.set("[AUTO-GENERATED]")
        self.convert_btn.configure(state='disabled', bg='#003300')
        self.log_status("Files cleared", '#ffff00')
        self.progress_var.set("READY")
    
    def browse_output_file(self):
        """Browse for output location"""
        file_path = filedialog.asksaveasfilename(
            title="Save WinEEG File As",
            defaultextension=".eeg",
            filetypes=[("EEG files", "*.eeg"), ("All files", "*.*")]
        )
        
        if file_path:
            self.output_file = file_path
            filename = os.path.basename(file_path)
            self.output_path_var.set(f"[CUSTOM] {filename}")
            self.log_status(f"Output set: {filename}", '#00ff41')
    
    def start_conversion(self):
        """Start the conversion process"""
        if not self.edf_file:
            messagebox.showerror("No Input", "Please select an EDF file first.")
            return
            
        if not self.output_file:
            messagebox.showerror("No Output", "Please specify an output file.")
            return
        
        # Disable convert button during conversion
        self.convert_btn.configure(state='disabled', text="[CONVERTING...]", bg='#333300')
        self.progress_var.set("CONVERTING")
        
        # Start conversion in separate thread
        self.conversion_thread = threading.Thread(target=self.convert_file)
        self.conversion_thread.daemon = True
        self.conversion_thread.start()
    
    def convert_file(self):
        """Perform the actual conversion"""
        try:
            self.log_status("Starting conversion process...", '#00ff41')
            self.log_status("Phase 1: EDF >> Raw INT16", '#ffff00')
            
            # Step 1: Convert EDF to raw INT16
            raw_file = self.edf_to_raw(self.edf_file)
            
            self.log_status("Phase 2: Template integration", '#ffff00')
            
            # Step 2: Convert raw to EEG
            success = self.raw_to_eeg(raw_file, self.output_file, self.patient_var.get())
            
            # Cleanup temp file
            if os.path.exists(raw_file):
                os.remove(raw_file)
            
            if success:
                self.log_status("CONVERSION COMPLETE!", '#00ff41')
                self.log_status(f"Output: {os.path.basename(self.output_file)}", '#00ff41')
                self.progress_var.set("SUCCESS")
                
                # Show success dialog
                result = messagebox.askquestion(
                    "Conversion Complete", 
                    f"EDF successfully Modded to WinEEG format!\n\nOutput: {self.output_file}\n\nOpen output folder?",
                    icon='question'
                )
                
                if result == 'yes':
                    output_dir = os.path.dirname(self.output_file)
                    os.startfile(output_dir)
            else:
                self.log_status("CONVERSION FAILED", '#ff0000')
                self.progress_var.set("FAILED")
                
        except Exception as e:
            self.log_status(f"CRITICAL ERROR: {str(e)}", '#ff0000')
            self.progress_var.set("ERROR")
        
        finally:
            # Re-enable convert button
            self.convert_btn.configure(state='normal', text="[Mod and CONVERT]\nEDF >> WinEEG", bg='#004400')
    
    def edf_to_raw(self, edf_file):
        """Convert EDF to raw INT16 format using PROVEN scaling algorithm"""
        import mne
        
        self.log_status("Loading EDF with MNE-Python...", '#ffff00')
        raw = mne.io.read_raw_edf(edf_file, preload=True, verbose=False)
        
        # Ensure we have 19 channels
        if len(raw.ch_names) != 19:
            raise ValueError(f"Expected 19 channels, got {len(raw.ch_names)}")
        
        self.log_status("Converting to microvolts...", '#ffff00')
        data = raw.get_data() * 1e6  # Convert to µV
        
        self.log_status("Applying FINAL scaling algorithm...", '#ffff00')
        # Final scaling to match template amplitude perfectly
        # User needs 500µV for EDF data vs ~50µV for template = 10x difference
        scaling_factor = 20  # Reduced 10x more to match template exactly
        data_scaled = data * scaling_factor
        
        # Clip to INT16 range (same as working version)
        data_clipped = np.clip(data_scaled, -32768, 32767)
        
        # Convert to INT16 
        data_int16 = data_clipped.astype(np.int16)
        
        self.log_status("Interleaving channels (frame-by-frame)...", '#ffff00')
        # Transpose to get (samples, channels) shape for frame-by-frame interleaving
        n_channels, n_samples = data_int16.shape
        data_transposed = data_int16.T  # Now (samples, channels)
        
        # Flatten to interleaved format: S0C0, S0C1, ..., S0C18, S1C0, S1C1, ...
        interleaved = data_transposed.flatten()
        
        # Save to temporary file
        temp_file = os.path.join(os.path.dirname(self.output_file), "temp_raw_data.bin")
        interleaved.tofile(temp_file)
        
        self.log_status(f"Raw data: {n_samples:,} samples × {n_channels} channels", '#00ff41')
        self.log_status(f"Interleaved size: {len(interleaved):,} INT16 values", '#00ff41')
        return temp_file
    
    def raw_to_eeg(self, raw_file, output_file, patient_name):
        """Convert raw data to EEG using template"""
        try:
            from converter_core import UniversalConverter
            
            self.log_status("Loading converter core...", '#ffff00')
            converter = UniversalConverter()
            
            self.log_status("Applying WinEEG template...", '#ffff00')
            success = converter.convert_raw_to_eeg(raw_file, output_file, patient_name)
            
            if success:
                self.log_status("Template integration successful", '#00ff41')
            
            return success
            
        except ImportError as e:
            self.log_status(f"Converter core error: {str(e)}", '#ff0000')
            return False

def main():
    """Main entry point"""
    root = tk.Tk()
    app = EEGConverter(root)
    
    # Center the window
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")
    
    # Start the GUI
    root.mainloop()

if __name__ == "__main__":
    main()
