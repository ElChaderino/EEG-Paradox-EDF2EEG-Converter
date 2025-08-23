#!/usr/bin/env python3
"""
EEG Paradox EDF to EEG Converter - GUI Version
Universal converter with drag & drop support
"""

import sys
import os
import threading
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QComboBox, 
                             QTextEdit, QProgressBar, QFileDialog, QMessageBox,
                             QGroupBox, QCheckBox, QFrame, QSplitter)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QMimeData
from PyQt5.QtGui import QFont, QPixmap, QDragEnterEvent, QDropEvent, QIcon, QColor
from PyQt5.QtWidgets import QGraphicsDropShadowEffect
import traceback

# Import our converter
try:
    from edf_to_eeg_converter import EDFToEEGConverter
    CONVERTER_AVAILABLE = True
except ImportError as e:
    CONVERTER_AVAILABLE = False
    print(f"Warning: Converter not available: {e}")

class DropZone(QFrame):
    """Custom drop zone widget for drag & drop"""
    
    file_dropped = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setFrameStyle(QFrame.Box)
        self.setMinimumHeight(120)
        self.setStyleSheet("""
            QFrame {
                border: 2px dashed #00d4ff;
                border-radius: 10px;
                background-color: #2a2a2a;
                padding: 20px;
            }
            QFrame:hover {
                border-color: #00ffff;
                background-color: #3a3a3a;
            }
        """)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Drop icon and text
        icon_label = QLabel("📁")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 48px; color: #00d4ff;")
        layout.addWidget(icon_label)
        
        text_label = QLabel("Drag & Drop EDF file here\nor click to browse")
        text_label.setAlignment(Qt.AlignCenter)
        text_label.setStyleSheet("font-size: 14px; color: #e0e0e0; font-weight: bold;")
        layout.addWidget(text_label)
        
        # Browse button
        browse_btn = QPushButton("Browse Files")
        browse_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #00d4ff, stop:1 #0099cc);
                color: #000000;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #00ffff, stop:1 #00d4ff);
            }
        """)
        browse_btn.clicked.connect(self.browse_files)
        layout.addWidget(browse_btn)
        
        self.file_path = None
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                QFrame {
                    border: 2px dashed #00ff00;
                    border-radius: 10px;
                    background-color: #1a3a1a;
                    padding: 20px;
                }
            """)
    
    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            QFrame {
                border: 2px dashed #00d4ff;
                border-radius: 10px;
                background-color: #2a2a2a;
                padding: 20px;
            }
        """)
    
    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path.lower().endswith(('.edf', '.bdf')):
                self.file_path = file_path
                self.file_dropped.emit(file_path)
                self.setStyleSheet("""
                    QFrame {
                        border: 2px solid #00ff00;
                        border-radius: 10px;
                        background-color: #1a3a1a;
                        padding: 20px;
                    }
                """)
                
                # Update text to show selected file
                layout = self.layout()
                if layout.count() > 1:
                    old_label = layout.itemAt(1).widget()
                    if isinstance(old_label, QLabel):
                        old_label.setText(f"✅ {Path(file_path).name}")
                        old_label.setStyleSheet("font-size: 14px; color: #28a745; font-weight: bold;")
            else:
                QMessageBox.warning(self, "Invalid File", "Please drop an .edf or .bdf file")
        
        self.setStyleSheet("""
            QFrame {
                border: 2px dashed #00d4ff;
                border-radius: 10px;
                background-color: #2a2a2a;
                padding: 20px;
            }
        """)
    
    def browse_files(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select EDF/BDF File", "", 
            "EEG Files (*.edf *.bdf);;EDF Files (*.edf);;BDF Files (*.bdf);;All Files (*)"
        )
        if file_path:
            self.file_path = file_path
            self.file_dropped.emit(file_path)
            
            # Update text to show selected file
            layout = self.layout()
            if layout.count() > 1:
                old_label = layout.itemAt(1).widget()
                if isinstance(old_label, QLabel):
                    old_label.setText(f"✅ {Path(file_path).name}")
                    old_label.setStyleSheet("font-size: 14px; color: #28a745; font-weight: bold;")

class ConversionThread(QThread):
    """Background thread for conversion to prevent GUI freezing"""
    
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, converter, edf_file, output_dir, format_type):
        super().__init__()
        self.converter = converter
        self.edf_file = edf_file
        self.output_dir = output_dir
        self.format_type = format_type
    
    def run(self):
        try:
            self.progress.emit("Starting conversion...")
            
            # Redirect print to our progress signal
            import builtins
            original_print = builtins.print
            
            def progress_print(*args, **kwargs):
                message = " ".join(str(arg) for arg in args)
                self.progress.emit(message)
            
            builtins.print = progress_print
            
            try:
                success = self.converter.convert_file(
                    self.edf_file, 
                    self.output_dir, 
                    self.format_type
                )
                if success:
                    self.finished.emit(True, "Conversion completed successfully!")
                else:
                    self.finished.emit(False, "Conversion failed. Check the log above.")
            finally:
                builtins.print = original_print
                
        except Exception as e:
            error_msg = f"Conversion error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            self.finished.emit(False, error_msg)

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🧠 EEG Paradox - Universal EDF to EEG Converter v2.9.1")
        self.setMinimumSize(800, 600)
        
        # Set window icon if available
        try:
            icon_path = Path(__file__).parent.parent / "EP.png"
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
        except:
            pass
        
        # Set cyberpunk window styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a1a;
                border: 2px solid #00d4ff;
                border-radius: 10px;
            }
        """)
        
        # Initialize converter
        if CONVERTER_AVAILABLE:
            self.converter = EDFToEEGConverter()
        else:
            self.converter = None
        
        self.setup_ui()
        self.setup_styles()
        self.add_cyberpunk_effects()
        
    def add_cyberpunk_effects(self):
        """Add cyberpunk-style glow and shadow effects"""
        # Add glow effect to main title
        title_effect = QGraphicsDropShadowEffect()
        title_effect.setBlurRadius(20)
        title_effect.setColor(QColor(0, 212, 255, 100))
        title_effect.setOffset(0, 0)
        
        # Find the title label and apply effect
        for child in self.findChildren(QLabel):
            if "🧠 EEG Paradox" in child.text():
                child.setGraphicsEffect(title_effect)
                break
        
        # Add subtle glow to drop zone
        drop_effect = QGraphicsDropShadowEffect()
        drop_effect.setBlurRadius(15)
        drop_effect.setColor(QColor(0, 212, 255, 50))
        drop_effect.setOffset(0, 0)
        self.drop_zone.setGraphicsEffect(drop_effect)
        
    def setup_ui(self):
        """Setup the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Logo/Title
        title_label = QLabel("🧠 EEG Paradox")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #00d4ff; text-shadow: 0 0 10px #00d4ff;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Version info
        version_label = QLabel("v2.9.1")
        version_label.setStyleSheet("font-size: 12px; color: #00d4ff; padding: 5px; opacity: 0.8;")
        header_layout.addWidget(version_label)
        
        main_layout.addLayout(header_layout)
        
        # Cyberpunk accent line
        accent_line = QFrame()
        accent_line.setFrameShape(QFrame.HLine)
        accent_line.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 transparent, stop:0.3 #00d4ff, stop:0.7 #00d4ff, stop:1 transparent);
                height: 2px;
                margin: 10px 0px;
            }
        """)
        main_layout.addWidget(accent_line)
        
        # Subtitle
        subtitle = QLabel("Universal EDF to EEG Converter")
        subtitle.setStyleSheet("font-size: 16px; color: #e0e0e0; margin-bottom: 10px; text-shadow: 0 0 5px #00d4ff;")
        subtitle.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(subtitle)
        
        # Drop zone
        self.drop_zone = DropZone()
        self.drop_zone.file_dropped.connect(self.on_file_selected)
        main_layout.addWidget(self.drop_zone)
        
        # Conversion options
        options_group = QGroupBox("Conversion Options")
        options_layout = QVBoxLayout(options_group)
        
        # Format selection
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Output Format:"))
        
        self.format_combo = QComboBox()
        self.format_combo.addItems([
            "BrainVision (.vhdr/.vmrk) - Modern software",
            "WinEEG (.erd/.evt) - Original WinEEG",
            "Neuroscan (.hdr) - Neuroscan systems",
            "EEGLAB (.set) - MATLAB-based analysis",
            "Nicolet (.hdr) - Nihon Kohden systems",
            "Compumedics (.hdr) - Sleep/EEG systems",
            "Both formats - Universal compatibility"
        ])
        self.format_combo.setCurrentIndex(0)
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()
        
        options_layout.addLayout(format_layout)
        
        # Output directory
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("Output Directory:"))
        
        self.output_dir_label = QLabel("Same as input file")
        self.output_dir_label.setStyleSheet("color: #00d4ff; font-style: italic; font-weight: bold;")
        dir_layout.addWidget(self.output_dir_label)
        
        self.browse_dir_btn = QPushButton("Browse")
        self.browse_dir_btn.clicked.connect(self.browse_output_dir)
        dir_layout.addWidget(self.browse_dir_btn)
        
        options_layout.addLayout(dir_layout)
        
        main_layout.addWidget(options_group)
        
        # Convert button
        self.convert_btn = QPushButton("🚀 Convert EDF to EEG")
        self.convert_btn.setEnabled(False)
        self.convert_btn.clicked.connect(self.start_conversion)
        self.convert_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #00ff00, stop:1 #00cc00);
                color: #000000;
                border: none;
                padding: 15px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                text-shadow: 0 0 5px #00ff00;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #00ff66, stop:1 #00ff00);
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(0, 255, 0, 0.3);
            }
            QPushButton:disabled {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #666666, stop:1 #444444);
                color: #888888;
                text-shadow: none;
            }
        """)
        main_layout.addWidget(self.convert_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #00d4ff;
                border-radius: 8px;
                text-align: center;
                background-color: #1a1a1a;
                color: #00d4ff;
                font-weight: bold;
                font-size: 12px;
                height: 25px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #00d4ff, stop:0.5 #00ffff, stop:1 #00d4ff);
                border-radius: 6px;
                margin: 2px;
            }
        """)
        main_layout.addWidget(self.progress_bar)
        
        # Log area
        log_group = QGroupBox("Conversion Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #2a2a2a;
                border: 2px solid #00d4ff;
                border-radius: 5px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                color: #e0e0e0;
                selection-background-color: #00d4ff;
                selection-color: #000000;
            }
        """)
        log_layout.addWidget(self.log_text)
        
        # Clear log button
        clear_log_btn = QPushButton("Clear Log")
        clear_log_btn.clicked.connect(self.log_text.clear)
        clear_log_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ff6b6b, stop:1 #cc5555);
                color: #000000;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ff8080, stop:1 #ff6b6b);
            }
        """)
        log_layout.addWidget(clear_log_btn)
        
        main_layout.addWidget(log_group)
        
        # Status bar
        self.statusBar().setStyleSheet("""
            QStatusBar {
                background-color: #1a1a1a;
                color: #00d4ff;
                border-top: 1px solid #00d4ff;
                font-weight: bold;
            }
        """)
        self.statusBar().showMessage("Ready - Drop an EDF file to begin")
        
        # Initialize variables
        self.selected_file = None
        self.output_directory = None
        self.conversion_thread = None
        
    def setup_styles(self):
        """Setup application styles with EEG Paradox dark theme"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a1a;
                color: #e0e0e0;
            }
            
            QWidget {
                background-color: #1a1a1a;
                color: #e0e0e0;
            }
            
            QGroupBox {
                font-weight: bold;
                border: 2px solid #00d4ff;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                color: #00d4ff;
                background-color: #2a2a2a;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #00d4ff;
                background-color: #1a1a1a;
            }
            
            QLabel {
                color: #e0e0e0;
                background-color: transparent;
            }
            
            QComboBox {
                padding: 8px;
                border: 2px solid #00d4ff;
                border-radius: 6px;
                background-color: #2a2a2a;
                color: #e0e0e0;
                selection-background-color: #00d4ff;
                selection-color: #000000;
            }
            
            QComboBox:hover {
                border-color: #00ffff;
                background-color: #3a3a3a;
            }
            
            QComboBox::drop-down {
                border: none;
                background-color: #2a2a2a;
            }
            
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #00d4ff;
                margin-right: 5px;
            }
            
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #00d4ff, stop:1 #0099cc);
                color: #000000;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #00ffff, stop:1 #00d4ff);
                transform: translateY(-1px);
            }
            
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0099cc, stop:1 #006699);
            }
            
            QPushButton:disabled {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #666666, stop:1 #444444);
                color: #888888;
            }
            
            QProgressBar {
                border: 2px solid #00d4ff;
                border-radius: 6px;
                text-align: center;
                background-color: #2a2a2a;
                color: #e0e0e0;
                font-weight: bold;
            }
            
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #00d4ff, stop:1 #0099cc);
                border-radius: 4px;
            }
            
            QTextEdit {
                background-color: #2a2a2a;
                border: 2px solid #00d4ff;
                border-radius: 6px;
                color: #e0e0e0;
                selection-background-color: #00d4ff;
                selection-color: #000000;
            }
            
            QScrollBar:vertical {
                background-color: #2a2a2a;
                width: 12px;
                border-radius: 6px;
            }
            
            QScrollBar::handle:vertical {
                background-color: #00d4ff;
                border-radius: 6px;
                min-height: 20px;
            }
            
            QScrollBar::handle:vertical:hover {
                background-color: #00ffff;
            }
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            
            QFrame {
                background-color: #2a2a2a;
            }
        """)
    
    def on_file_selected(self, file_path):
        """Handle file selection"""
        self.selected_file = file_path
        self.convert_btn.setEnabled(True)
        self.statusBar().showMessage(f"File selected: {Path(file_path).name}")
        
        # Log the selection
        self.log_text.append(f"📁 Selected file: {Path(file_path).name}")
        self.log_text.append(f"   Path: {file_path}")
        self.log_text.append(f"   Size: {Path(file_path).stat().st_size / 1024 / 1024:.1f} MB")
        self.log_text.append("")
    
    def browse_output_dir(self):
        """Browse for output directory"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", 
            str(Path(self.selected_file).parent) if self.selected_file else ""
        )
        if directory:
            self.output_directory = directory
            self.output_dir_label.setText(directory)
            self.output_dir_label.setStyleSheet("color: #28a745; font-weight: bold;")
    
    def start_conversion(self):
        """Start the conversion process"""
        if not self.selected_file:
            QMessageBox.warning(self, "No File", "Please select an EDF file first")
            return
        
        if not CONVERTER_AVAILABLE:
            QMessageBox.critical(self, "Converter Error", 
                               "The EDF converter module is not available.\n"
                               "Please ensure edf_to_eeg_converter.py is in the same directory.")
            return
        
        # Get format selection
        format_map = {
            0: "brainvision",
            1: "wineeg",
            2: "neuroscan",
            3: "eeglab",
            4: "nicolet",
            5: "compumedics",
            6: "both"
        }
        format_type = format_map[self.format_combo.currentIndex()]
        
        # Get output directory
        output_dir = self.output_directory if self.output_directory else None
        
        # Disable UI during conversion
        self.convert_btn.setEnabled(False)
        self.drop_zone.setEnabled(False)
        self.format_combo.setEnabled(False)
        self.browse_dir_btn.setEnabled(False)
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        # Clear log
        self.log_text.clear()
        self.log_text.append("🚀 Starting conversion...")
        self.log_text.append(f"📁 Input: {Path(self.selected_file).name}")
        self.log_text.append(f"🎯 Format: {format_type}")
        self.log_text.append(f"📂 Output: {output_dir if output_dir else 'Same directory'}")
        self.log_text.append("")
        
        # Start conversion thread
        self.conversion_thread = ConversionThread(
            self.converter, self.selected_file, output_dir, format_type
        )
        self.conversion_thread.progress.connect(self.update_progress)
        self.conversion_thread.finished.connect(self.conversion_finished)
        self.conversion_thread.start()
    
    def update_progress(self, message):
        """Update progress log"""
        self.log_text.append(message)
        # Auto-scroll to bottom
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def conversion_finished(self, success, message):
        """Handle conversion completion"""
        # Re-enable UI
        self.convert_btn.setEnabled(True)
        self.drop_zone.setEnabled(True)
        self.format_combo.setEnabled(True)
        self.browse_dir_btn.setEnabled(True)
        
        # Hide progress bar
        self.progress_bar.setVisible(False)
        
        # Show result
        if success:
            self.log_text.append("")
            self.log_text.append("✅ " + message)
            self.statusBar().showMessage("Conversion completed successfully!")
            
            # Show success message
            QMessageBox.information(self, "Success", 
                                  "Conversion completed successfully!\n\n"
                                  "Check the output directory for generated files.")
        else:
            self.log_text.append("")
            self.log_text.append("❌ " + message)
            self.statusBar().showMessage("Conversion failed")
            
            # Show error message
            QMessageBox.critical(self, "Conversion Failed", 
                               "The conversion failed. Check the log above for details.")
    
    def closeEvent(self, event):
        """Handle application close"""
        if self.conversion_thread and self.conversion_thread.isRunning():
            reply = QMessageBox.question(
                self, "Conversion Running", 
                "A conversion is currently running. Are you sure you want to quit?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.conversion_thread.terminate()
                self.conversion_thread.wait()
                event.accept()
            else:
                event.ignore()

def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("EEG Paradox EDF Converter")
    app.setApplicationVersion("2.9.1")
    app.setOrganizationName("EEG Paradox")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Start event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
