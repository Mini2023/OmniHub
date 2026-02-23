import os
import zipfile
import rarfile
import py7zr
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, 
                               QFileDialog, QHBoxLayout, QMessageBox, QListWidget, QFrame)
from PySide6.QtGui import QDragEnterEvent, QDropEvent

class DragDropListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionMode(QListWidget.ExtendedSelection)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                items = [self.item(i).text() for i in range(self.count())]
                if file_path not in items:
                    self.addItem(file_path)
                    
class ArchiveMasterTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        self.header_label = QLabel("Archive Master (Supported: .zip, .rar, .7z)")
        self.header_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #5c8cbc;")
        layout.addWidget(self.header_label)

        self.instruction = QLabel("Select an archive to extract, or select multiple files to compress.")
        layout.addWidget(self.instruction)
        
        self.files_list = DragDropListWidget()
        self.files_list.setStyleSheet("background-color: #F8FAFF; border: 2px dashed #B0C4DE; border-radius: 8px; padding: 10px; color: #333;")
        layout.addWidget(self.files_list)

        btn_layout = QHBoxLayout()
        
        self.clear_list_btn = QPushButton("Clear List")
        self.clear_list_btn.setStyleSheet("background-color: #555;")
        self.clear_list_btn.clicked.connect(self.clear_list)
        btn_layout.addWidget(self.clear_list_btn)

        self.add_files_btn = QPushButton("Add Files")
        self.add_files_btn.clicked.connect(self.add_files)
        btn_layout.addWidget(self.add_files_btn)

        self.compress_btn = QPushButton("Compress to .zip")
        self.compress_btn.clicked.connect(self.compress_files)
        btn_layout.addWidget(self.compress_btn)

        self.compress_7z_btn = QPushButton("Compress to .7z")
        self.compress_7z_btn.clicked.connect(self.compress_7z)
        btn_layout.addWidget(self.compress_7z_btn)

        layout.addLayout(btn_layout)

        # Separator Line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #444;")
        layout.addWidget(line)

        # Distinct Section for Extraction
        extract_layout = QHBoxLayout()
        extract_label = QLabel("Or extract an existing archive directly:")
        extract_label.setStyleSheet("color: #aaa;")
        extract_layout.addWidget(extract_label)

        self.extract_btn = QPushButton("Extract Archive (zip, rar, 7z)")
        self.extract_btn.clicked.connect(self.extract_archive)
        self.extract_btn.setStyleSheet("""
            QPushButton {
                background-color: #2e8b57; 
                color: white; 
                border: 2px solid #3cb371; 
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #3cb371;
            }
        """)
        extract_layout.addWidget(self.extract_btn)
        
        layout.addLayout(extract_layout)
        
    def receive_global_drop(self, files):
        for f in files:
            items = [self.files_list.item(i).text() for i in range(self.files_list.count())]
            if f not in items:
                self.files_list.addItem(f)

    def get_selected_files(self):
        return [self.files_list.item(i).text() for i in range(self.files_list.count())]

    def clear_list(self):
        self.files_list.clear()

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files to Compress")
        if files:
            for f in files:
                current_items = self.get_selected_files()
                if f not in current_items:
                    self.files_list.addItem(f)

    def compress_files(self):
        files = self.get_selected_files()
        if not files:
            QMessageBox.warning(self, "Empty", "Please add files to compress first.")
            return
            
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Zip Archive", "", "ZIP Files (*.zip)")
        if save_path:
            try:
                with zipfile.ZipFile(save_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for f in files:
                        zipf.write(f, os.path.basename(f))
                QMessageBox.information(self, "Success", f"Successfully created {os.path.basename(save_path)}")
                self.files_list.clear()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to compress: {e}")

    def compress_7z(self):
        files = self.get_selected_files()
        if not files:
            QMessageBox.warning(self, "Empty", "Please add files to compress first.")
            return
            
        save_path, _ = QFileDialog.getSaveFileName(self, "Save 7z Archive", "", "7z Files (*.7z)")
        if save_path:
            try:
                with py7zr.SevenZipFile(save_path, 'w') as archive:
                    for f in files:
                        archive.write(f, os.path.basename(f))
                QMessageBox.information(self, "Success", f"Successfully created {os.path.basename(save_path)}")
                self.files_list.clear()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to compress: {e}")

    def extract_archive(self):
        archive_path, _ = QFileDialog.getOpenFileName(self, "Select Archive to Extract", "", "Archive Files (*.zip *.rar *.7z)")
        if not archive_path:
            return
            
        extract_dir = QFileDialog.getExistingDirectory(self, "Select Extraction Directory")
        if not extract_dir:
            return

        try:
            ext = archive_path.lower().split('.')[-1]
            if ext == 'zip':
                with zipfile.ZipFile(archive_path, 'r') as zipf:
                    zipf.extractall(extract_dir)
            elif ext == 'rar':
                # Note: Extracting RAR requires the unrar utility in the system PATH.
                with rarfile.RarFile(archive_path, 'r') as rarf:
                    rarf.extractall(extract_dir)
            elif ext == '7z':
                with py7zr.SevenZipFile(archive_path, 'r') as zf:
                    zf.extractall(path=extract_dir)
            else:
                QMessageBox.warning(self, "Unsupported", "Unsupported archive format.")
                return
            
            QMessageBox.information(self, "Success", f"Successfully extracted to:\n{extract_dir}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Extraction failed: {str(e)}\n\n(Note: extracting .rar requires 'unrar' installed on Windows)")
