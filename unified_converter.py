import sys
import os
import logging
import argparse
import time
import threading
from pathlib import Path
from typing import List, Set, Dict, Optional, Tuple


def get_app_data_dir():
    app_data = os.path.join(os.environ['APPDATA'], 'FileConverter')
    os.makedirs(app_data, exist_ok=True)
    return app_data

DEFAULT_LOG_FILE = os.path.join(get_app_data_dir(), "file_converter.log")

class LoggingManager:
    def __init__(self, default_log_file=DEFAULT_LOG_FILE):
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)
        self.default_log_file = default_log_file
        self.file_handler = None
        self.console_handler = None
        self.log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self._setup_console_handler()
    
    def _setup_console_handler(self):
        if not self.console_handler:
            self.console_handler = logging.StreamHandler()
            self.console_handler.setFormatter(self.log_formatter)
            self.logger.addHandler(self.console_handler)
    
    def enable_file_logging(self, log_file=None):
        if log_file is None:
            log_file = self.default_log_file
            
        self.disable_file_logging()
        
        try:
            self.file_handler = logging.FileHandler(log_file)
            self.file_handler.setFormatter(self.log_formatter)
            self.logger.addHandler(self.file_handler)
            logging.info(f"Logging to file: {log_file}")
            return True
        except Exception as e:
            logging.error(f"Failed to set up file logging: {str(e)}")
            self.file_handler = None
            return False
    
    def disable_file_logging(self):
        if self.file_handler and self.file_handler in self.logger.handlers:
            self.logger.removeHandler(self.file_handler)
            self.file_handler = None
            logging.info("File logging disabled")
    
    def configure(self, enable_file_logging=True, log_file=None):
        if enable_file_logging:
            self.enable_file_logging(log_file)
        else:
            self.disable_file_logging()
    
    def get_log_file_path(self):
        if self.file_handler:
            return self.file_handler.baseFilename
        return None

logging_manager = LoggingManager()

from file_converter import FileConverter
from registry_manager import RegistryManager

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
        QPushButton, QLabel, QListWidget, QCheckBox, QMessageBox,
        QGroupBox, QGridLayout, QFileDialog, QStatusBar, QStyle, QFrame,
        QSizePolicy
    )
    from PyQt6.QtCore import Qt, QSize, QTimer, QPropertyAnimation, QEasingCurve, QRect, QPoint, pyqtProperty
    from PyQt6.QtGui import QIcon, QFont, QPixmap, QColor, QPainter, QPen, QBrush
    HAS_QT = True
except ImportError:
    HAS_QT = False


class FadeAnimation(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._opacity = 0
        self.animation = QPropertyAnimation(self, b"opacity")
        self.animation.setDuration(250)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
    def get_opacity(self):
        return self._opacity
        
    def set_opacity(self, opacity):
        self._opacity = opacity
        self.update()
        
    opacity = pyqtProperty(float, get_opacity, set_opacity)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setOpacity(self._opacity)
        super().paintEvent(event)


class AnimatedButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self._hover_animation = QPropertyAnimation(self, b"styleSheet")
        self._hover_animation.setDuration(150)
        
        self._base_style = """
            background-color: #7b2cbf;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
            min-height: 20px;
        """
        
        self._hover_style = """
            background-color: #9d4edd;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
            min-height: 20px;
        """
        
        self.setStyleSheet(self._base_style)
        
    def enterEvent(self, event):
        self.setStyleSheet(self._hover_style)
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.setStyleSheet(self._base_style)
        super().leaveEvent(event)


class ContextMenuManagerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("File Converter")
        self.setMinimumSize(700, 480)
        
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'menuitem.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.reg_manager = RegistryManager()
        self.converter = FileConverter()
        self.setup_ui()
        self.refresh_extensions()
        
    def setup_ui(self):
        central_widget = FadeAnimation(self)
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 15, 20, 15)
        main_layout.setSpacing(12)
        
        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)
        content_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addLayout(content_layout)
        
        left_group = self._create_extensions_list_section()
        content_layout.addWidget(left_group)
        
        right_group = self._create_add_extensions_section()
        content_layout.addWidget(right_group)
        
        logging_group = self._create_logging_section()
        main_layout.addWidget(logging_group)
        
        self.status_bar = QStatusBar()
        self.status_bar.setSizeGripEnabled(False)
        self.setStatusBar(self.status_bar)
        
    def _create_extensions_list_section(self):
        left_group = QGroupBox("Registered Extensions")
        left_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left_layout = QVBoxLayout(left_group)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(6)
        
        self.extensions_list = QListWidget()
        self.extensions_list.setAlternatingRowColors(True)
        self.extensions_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        
        section_label = QLabel("Currently registered file extensions:")
        section_label.setStyleSheet("color: #a0a0a0; margin-bottom: 2px;")
        left_layout.addWidget(section_label)
        left_layout.addWidget(self.extensions_list)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        buttons_layout.setContentsMargins(0, 4, 0, 0)
        
        remove_btn = AnimatedButton("Remove Selected")
        remove_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogDiscardButton))
        remove_btn.clicked.connect(self.remove_selected_extensions)
        buttons_layout.addWidget(remove_btn)
        
        remove_all_btn = AnimatedButton("Remove All")
        remove_all_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogResetButton))
        remove_all_btn.clicked.connect(self.remove_all_extensions)
        buttons_layout.addWidget(remove_all_btn)
        
        left_layout.addLayout(buttons_layout)
        return left_group
        
    def _create_add_extensions_section(self):
        right_group = QGroupBox("Add Context Menu Entries")
        right_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_layout = QVBoxLayout(right_group)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(6)
        
        category_label = QLabel("Select categories to add:")
        category_label.setStyleSheet("color: #a0a0a0; margin-bottom: 2px;")
        right_layout.addWidget(category_label)
        
        checkbox_container = self._create_category_checkboxes()
        right_layout.addLayout(checkbox_container)
        
        formats_container = self._create_formats_info_section()
        right_layout.addLayout(formats_container)
        
        path_label = QLabel("Using current executable for context menu:")
        path_label.setStyleSheet("color: #a0a0a0; margin-top: 4px;")
        right_layout.addWidget(path_label)
        
        self.exe_path_label = QLabel(get_this_exe_path())
        self.exe_path_label.setWordWrap(True)
        self.exe_path_label.setProperty("customPath", True)
        self.exe_path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        right_layout.addWidget(self.exe_path_label)
        
        add_btn = AnimatedButton("Add Context Menu Entries")
        add_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder))
        add_btn.clicked.connect(self.add_extensions)
        add_btn.setStyleSheet("margin-top: 6px;")
        right_layout.addWidget(add_btn)
        return right_group
        
    def _create_category_checkboxes(self):
        checkbox_container = QVBoxLayout()
        checkbox_container.setSpacing(6)
        checkbox_container.setContentsMargins(0, 0, 0, 0)
        
        self.images_checkbox = QCheckBox("Image Formats")
        self.audio_checkbox = QCheckBox("Audio Formats")
        self.video_checkbox = QCheckBox("Video Formats")
        
        for checkbox in [self.images_checkbox, self.audio_checkbox, self.video_checkbox]:
            checkbox.setStyleSheet("font-size: 10pt;")
        
        checkbox_container.addWidget(self.images_checkbox)
        checkbox_container.addWidget(self.audio_checkbox)
        checkbox_container.addWidget(self.video_checkbox)
        return checkbox_container
        
    def _create_formats_info_section(self):
        formats_container = QVBoxLayout()
        formats_container.setSpacing(4)
        formats_container.setContentsMargins(0, 0, 0, 6)
        img_formats = ", ".join(sorted(fmt[1:] for fmt in self.converter.image_formats))
        audio_formats = ", ".join(sorted(fmt[1:] for fmt in self.converter.audio_formats))
        video_formats = ", ".join(sorted(fmt[1:] for fmt in self.converter.video_formats))
        
        formats_data = [
            ("Image formats:", img_formats, "#4dcebd"),
            ("Audio formats:", audio_formats, "#e0b346"),
            ("Video formats:", video_formats, "#e05e6d")
        ]
        
        for title, formats, color in formats_data:
            format_layout = QVBoxLayout()
            format_layout.setSpacing(2)
            
            format_title = QLabel(title)
            format_title.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 9pt;")
            format_layout.addWidget(format_title)
            
            format_info = QLabel(formats)
            format_info.setWordWrap(True)
            format_info.setStyleSheet("background-color: #2a2a2a; padding: 3px; border-radius: 3px; font-family: 'Consolas', monospace; font-size: 8pt;")
            format_layout.addWidget(format_info)
            
            formats_container.addLayout(format_layout)
        return formats_container
    
    def _create_logging_section(self):
        logging_group = QGroupBox("Logging Settings")
        logging_layout = QVBoxLayout(logging_group)
        logging_layout.setContentsMargins(8, 8, 8, 8)
        logging_layout.setSpacing(6)
        
        checkbox_layout = QHBoxLayout()
        self.file_logging_checkbox = QCheckBox("Enable File Logging")
        self.file_logging_checkbox.setChecked(logging_manager.file_handler is not None)
        self.file_logging_checkbox.toggled.connect(self.toggle_file_logging)
        checkbox_layout.addWidget(self.file_logging_checkbox)
        checkbox_layout.addStretch(1)
        
        if logging_manager.file_handler is not None:
            view_log_btn = AnimatedButton("View Log File")
            view_log_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
            view_log_btn.clicked.connect(self.view_log_file)
            checkbox_layout.addWidget(view_log_btn)
        
        logging_layout.addLayout(checkbox_layout)
        
        log_file_path = logging_manager.get_log_file_path() or DEFAULT_LOG_FILE
        self.log_file_label = QLabel(f"Log file: {log_file_path}")
        self.log_file_label.setWordWrap(True)
        self.log_file_label.setProperty("customPath", True)
        self.log_file_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        logging_layout.addWidget(self.log_file_label)
        
        return logging_group
    
    def toggle_file_logging(self, enabled):
        logging_manager.configure(enabled)
        if enabled:
            self.status_bar.showMessage("File logging enabled", 3000)
        else:
            self.status_bar.showMessage("File logging disabled", 3000)
        
        if enabled and logging_manager.file_handler:
            self.log_file_label.setText(f"Log file: {logging_manager.file_handler.baseFilename}")
        
    def refresh_extensions(self):
        self.extensions_list.clear()
        
        extensions = self.reg_manager.get_registered_extensions()
        for ext in sorted(extensions):
            self.extensions_list.addItem(ext)
        
        if extensions:
            self.status_bar.showMessage(f"{len(extensions)} extension(s) registered")
        else:
            self.status_bar.showMessage("No extensions registered")
    
    def remove_selected_extensions(self):
        selected_items = self.extensions_list.selectedItems()
        
        if not selected_items:
            QMessageBox.information(self, "No Selection", "Please select one or more extensions to remove.")
            return
        
        count = len(selected_items)
        confirm = QMessageBox.question(
            self, 
            "Confirm Removal",
            f"Remove {count} extension(s) from the context menu?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                for item in selected_items:
                    ext = item.text()
                    self.reg_manager.remove_context_menu_for_extension(ext)
                
                self.refresh_extensions()
                self.status_bar.showMessage(f"Removed {count} extension(s)", 3000)
            except Exception as e:
                logging.error(f"Error removing extensions: {e}")
                QMessageBox.critical(self, "Error", f"Failed to remove extensions: {str(e)}")
    
    def remove_all_extensions(self):
        extensions = self.reg_manager.get_registered_extensions()
        
        if not extensions:
            QMessageBox.information(self, "No Extensions", "There are no extensions registered.")
            return
        
        count = len(extensions)
        confirm = QMessageBox.question(
            self, 
            "Confirm Removal",
            f"Remove all {count} extension(s) from the context menu?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                self.reg_manager.remove_all_context_menus()
                self.refresh_extensions()
                self.status_bar.showMessage("Removed all extensions", 3000)
            except Exception as e:
                logging.error(f"Error removing all extensions: {e}")
                QMessageBox.critical(self, "Error", f"Failed to remove all extensions: {str(e)}")
    
    def add_extensions(self):
        exe_path = self.exe_path_label.text()
        
        if not os.path.exists(exe_path):
            QMessageBox.critical(self, "Invalid Path", "The converter executable does not exist.")
            return
        
        if not any([
            self.images_checkbox.isChecked(),
            self.audio_checkbox.isChecked(),
            self.video_checkbox.isChecked()
        ]):
            QMessageBox.information(self, "No Selection", "Please select at least one category of extensions.")
            return
        
        try:
            added_count = 0
            
            if self.images_checkbox.isChecked():
                for ext in self.converter.image_formats:
                    image_formats = {fmt[1:] for fmt in self.converter.image_formats}
                    self.reg_manager.add_context_menu_for_extension(ext, image_formats, exe_path)
                    added_count += 1
            
            if self.audio_checkbox.isChecked():
                for ext in self.converter.audio_formats:
                    audio_formats = {fmt[1:] for fmt in self.converter.audio_formats}
                    self.reg_manager.add_context_menu_for_extension(ext, audio_formats, exe_path)
                    added_count += 1
            
            if self.video_checkbox.isChecked():
                for ext in self.converter.video_formats:
                    video_formats = {fmt[1:] for fmt in self.converter.video_formats}
                    formats = video_formats | {'gif'}  # Add GIF as an option for videos
                    self.reg_manager.add_context_menu_for_extension(ext, formats, exe_path)
                    added_count += 1
            
            self.refresh_extensions()
            self.status_bar.showMessage(f"Added {added_count} extension(s)", 3000)
            
            QMessageBox.information(
                self, 
                "Success", 
                f"Successfully added context menu entries for {added_count} extension(s)."
            )
            
        except Exception as e:
            logging.error(f"Error adding extensions: {e}")
            QMessageBox.critical(self, "Error", f"Failed to add extensions: {str(e)}")

    def view_log_file(self):
        if logging_manager.file_handler and os.path.exists(logging_manager.file_handler.baseFilename):
            try:
                os.startfile(logging_manager.file_handler.baseFilename)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to open log file: {str(e)}")
        else:
            QMessageBox.information(self, "Log File", "Log file does not exist or logging is disabled.")


def get_this_exe_path() -> str:
    if getattr(sys, 'frozen', False):
        return str(Path(sys.executable))
    else:
        return str(Path(__file__))

# args
def parse_arguments():
    parser = argparse.ArgumentParser(description='File Converter & Context Menu Manager')
    parser.add_argument('files', nargs='*', help='Files to convert')                                                                              # Files to convert
    parser.add_argument('-f', '--format', help='Output format (e.g., jpg, png, mp3, wav, mp4, webm, gif)')                                        # Output format (e.g., jpg, png, mp3, wav, mp4, webm, gif)
    parser.add_argument('--gui', action='store_true', help='Launch the graphical user interface')                                                 # Launch the graphical user interface
    parser.add_argument('--max-gif-duration', type=float, default=15.0, help='Maximum duration (in seconds) for video to GIF conversion')         # Maximum duration (in seconds) for video to GIF conversion
    parser.add_argument('--setup', action='store_true', help='Set up context menu entries for all supported formats')                             # Set up context menu entries for all supported formats
    parser.add_argument('--remove', action='store_true', help='Remove all context menu entries created by this tool')                             # Remove all context menu entries created by this tool
    parser.add_argument('--list', action='store_true', help='List all registered extensions')                                                     # List all registered extensions
    parser.add_argument('--force', action='store_true', help='Remove existing entries before setting up (only with --setup)')                     # Remove existing entries before setting up (only with --setup)
    parser.add_argument('--no-log', action='store_true', help='Disable file logging')                                                             # Disable file logging
    
    return parser.parse_args()


def setup_context_menus(remove_existing: bool = False):
    try:
        reg_manager = RegistryManager()

        converter = FileConverter()

        exe_path = get_this_exe_path()
        if not os.path.exists(exe_path):
            raise FileNotFoundError(
                f"Converter executable not found at {exe_path}."
            )
        logging.info(f"Using converter executable: {exe_path}")
        
        if remove_existing:
            reg_manager.remove_all_context_menus()
        
        image_formats = {fmt[1:] for fmt in converter.image_formats}
        audio_formats = {fmt[1:] for fmt in converter.audio_formats}
        video_formats = {fmt[1:] for fmt in converter.video_formats}
        
        for ext in converter.image_formats:
            reg_manager.add_context_menu_for_extension(ext, image_formats, str(exe_path))
            
        for ext in converter.audio_formats:
            reg_manager.add_context_menu_for_extension(ext, audio_formats, str(exe_path))
            
        for ext in converter.video_formats:
            formats = video_formats | {'gif'}
            reg_manager.add_context_menu_for_extension(ext, formats, str(exe_path))
        
        logging.info("Context menu setup completed successfully")
        
    except Exception as e:
        logging.error(f"Failed to set up context menus: {str(e)}")
        raise


def remove_context_menus():
    try:
        reg_manager = RegistryManager()
        reg_manager.remove_all_context_menus()
        logging.info("All context menu entries removed successfully")
    except Exception as e:
        logging.error(f"Failed to remove context menus: {str(e)}")
        raise


def list_registered_extensions():
    try:
        reg_manager = RegistryManager()
        extensions = reg_manager.get_registered_extensions()
        if extensions:
            print("\nRegistered extensions:")
            for ext in sorted(extensions):
                print(f"  {ext}")
        else:
            print("\nNo extensions are currently registered")
    except Exception as e:
        logging.error(f"Failed to list extensions: {str(e)}")
        raise


def run_gui():
    if not HAS_QT:
        logging.error("PyQt6 not found. Please install it to use the GUI.")
        print("Error: PyQt6 not found. Please install it to use the GUI.")
        return 1
        
    app = QApplication(sys.argv)
    app.setApplicationName("File Converter")
    
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'menuitem.ico')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    app.setStyle("Fusion")
    
    style_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'style.qss')
    if os.path.exists(style_path):
        try:
            with open(style_path, 'r') as f:
                app.setStyleSheet(f.read())
            logging.info(f"Loaded stylesheet from {style_path}")
        except Exception as e:
            logging.error(f"Failed to load stylesheet: {str(e)}")
            app.setStyleSheet("QMainWindow, QDialog { background-color: #1e1e1e; color: #e0e0e0; }")
    else:
        logging.warning(f"Stylesheet not found at {style_path}")
        app.setStyleSheet("QMainWindow, QDialog { background-color: #1e1e1e; color: #e0e0e0; }")
    
    window = ContextMenuManagerGUI()
    window.show()
    
    return app.exec()


def run_converter(files: List[str], output_format: Optional[str], max_gif_duration: float):
    converter = FileConverter(max_gif_duration=max_gif_duration)
    
    if files:
        if output_format:
            logging.info(f"Converting {len(files)} file(s) to .{output_format} format")
        else:
            logging.info(f"Converting {len(files)} file(s) with auto format detection")
    
    for file_path in files:
        converter.add_file(Path(file_path), output_format)
    time.sleep(0.2)


def main():
    args = parse_arguments()
    
    logging_manager.configure(not args.no_log)
    
    if args.gui or (len(sys.argv) == 1):
        return run_gui()
        
    if args.setup:
        try:
            setup_context_menus(remove_existing=args.force)
            return 0
        except Exception as e:
            logging.error(str(e))
            return 1
            
    if args.remove:
        try:
            remove_context_menus()
            return 0
        except Exception as e:
            logging.error(str(e))
            return 1
            
    if args.list:
        try:
            list_registered_extensions()
            return 0
        except Exception as e:
            logging.error(str(e))
            return 1
    
    if args.files:
        try:
            run_converter(args.files, args.format, args.max_gif_duration)
            return 0
        except Exception as e:
            logging.error(f"Error during conversion: {str(e)}")
            return 1
    
    print("No action specified. Run with --gui to open the graphical interface.")
    return 1
    

if __name__ == "__main__":
    sys.exit(main()) 