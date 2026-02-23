import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                QPushButton, QListWidget, QListWidgetItem, 
                                QFileDialog, QLineEdit, QComboBox, QFrame, 
                                QTextEdit, QMessageBox, QGroupBox)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
import qtawesome as qta
from logic.universal_converter import ConversionWorker, get_supported_targets

class DragDropList(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionMode(QListWidget.ExtendedSelection)
        self.setStyleSheet("background: white; border-radius: 10px; border: 1px solid #E2E8F0;")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
        else: event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
        else: event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path):
                self.addItem(path)
        self.parent().check_queue()

class UniversalConverterTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #F8FAFC; font-family: 'Inter';")
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)

        self.output_folder = os.path.expanduser("~\\Documents")

        # --- LEFT SECTION: Queue ---
        left_pane = QVBoxLayout()
        q_label = QLabel("📥 Conversion Queue")
        q_label.setStyleSheet("font-weight: bold; color: #4A5568; font-size: 14px;")
        left_pane.addWidget(q_label)

        self.file_list = DragDropList(self)
        left_pane.addWidget(self.file_list)

        l_btns = QHBoxLayout()
        self.btn_add = QPushButton(" Add File")
        self.btn_add.setIcon(qta.icon('fa5s.plus', color="white"))
        self.btn_add.setStyleSheet("background: #A2D2FF; color: white; padding: 10px; border-radius: 8px; font-weight: bold;")
        self.btn_add.clicked.connect(self.manual_add)
        
        self.btn_clear = QPushButton(" Clear List")
        self.btn_clear.setIcon(qta.icon('fa5s.trash-alt', color="#4A5568"))
        self.btn_clear.setStyleSheet("background: white; border: 1px solid #E2E8F0; padding: 10px; border-radius: 8px; color: #4A5568;")
        self.btn_clear.clicked.connect(self.file_list.clear)
        
        l_btns.addWidget(self.btn_add)
        l_btns.addWidget(self.btn_clear)
        left_pane.addLayout(l_btns)
        
        self.main_layout.addLayout(left_pane, 3)

        # --- MIDDLE SECTION: Config ---
        mid_pane = QVBoxLayout()
        cfg_label = QLabel("⚙️ Configuration")
        cfg_label.setStyleSheet("font-weight: bold; color: #4A5568; font-size: 14px;")
        mid_pane.addWidget(cfg_label)

        cfg_box = QFrame()
        cfg_box.setStyleSheet("background: white; border-radius: 15px; border: 1px solid #E2E8F0;")
        cfg_vbox = QVBoxLayout(cfg_box)
        
        cfg_vbox.addWidget(QLabel("Target Format:"))
        self.combo_format = QComboBox()
        self.combo_format.addItem("Detecting...")
        self.combo_format.setStyleSheet("padding: 8px; border-radius: 6px; border: 1px solid #CBD5E0;")
        cfg_vbox.addWidget(self.combo_format)

        cfg_vbox.addWidget(QLabel("Custom Name (optional):"))
        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("New filename...")
        self.edit_name.setStyleSheet("padding: 8px; border-radius: 6px; border: 1px solid #CBD5E0;")
        cfg_vbox.addWidget(self.edit_name)
        
        cfg_vbox.addStretch()
        
        # Quick Actions
        qa_label = QLabel("Quick Actions:")
        qa_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        cfg_vbox.addWidget(qa_label)
        
        qas = [
            ("🖼️ To PNG", "PNG"),
            ("📄 To PDF", "PDF"),
            ("🎬 To MP4", "MP4"),
            ("🎵 To MP3", "MP3")
        ]
        for name, fmt in qas:
            btn = QPushButton(name)
            btn.setStyleSheet("text-align: left; padding: 10px; border: none; border-radius: 6px; color: #4A5568;")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda chk, f=fmt: self.quick_convert(f))
            cfg_vbox.addWidget(btn)
        
        mid_pane.addWidget(cfg_box)
        self.main_layout.addLayout(mid_pane, 2)

        # --- RIGHT SECTION: Output & Console ---
        right_pane = QVBoxLayout()
        out_label = QLabel("🚀 Output & Status")
        out_label.setStyleSheet("font-weight: bold; color: #4A5568; font-size: 14px;")
        right_pane.addWidget(out_label)

        # Destination Manager
        dest_box = QFrame()
        dest_box.setStyleSheet("background: white; border-radius: 15px; border: 1px solid #E2E8F0;")
        dest_vbox = QVBoxLayout(dest_box)
        
        self.dest_lbl = QLabel(f"Target: ...{self.output_folder[-25:]}")
        self.dest_lbl.setStyleSheet("font-size: 11px; color: #718096;")
        dest_vbox.addWidget(self.dest_lbl)
        
        self.btn_dest = QPushButton("📁 Select Folder")
        self.btn_dest.setStyleSheet("background: white; border: 1px solid #A2D2FF; padding: 8px; border-radius: 8px; color: #3182CE;")
        self.btn_dest.clicked.connect(self.select_dest)
        dest_vbox.addWidget(self.btn_dest)
        
        self.btn_current = QPushButton("📍 Current Folder")
        self.btn_current.setStyleSheet("background: #EDF2F7; padding: 8px; border-radius: 8px; color: #4A5568;")
        self.btn_current.clicked.connect(self.set_current_as_dest)
        dest_vbox.addWidget(self.btn_current)
        
        right_pane.addWidget(dest_box)

        # Console
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("background: #2D3748; color: #A0AEC0; border-radius: 12px; font-family: Consolas; font-size: 11px; padding: 10px;")
        self.console.setPlaceholderText("Console ready...")
        right_pane.addWidget(self.console)

        self.btn_convert = QPushButton("🔥 START CONVERSION")
        self.btn_convert.setStyleSheet("background: #3182CE; color: white; padding: 15px; border-radius: 10px; font-weight: bold; font-size: 14px;")
        self.btn_convert.clicked.connect(self.start_conversion)
        right_pane.addWidget(self.btn_convert)

        self.main_layout.addLayout(right_pane, 3)

        self.worker = None

    def receive_global_drop(self, files):
        for f in files:
            items = [self.file_list.item(i).text() for i in range(self.file_list.count())]
            if f not in items:
                self.file_list.addItem(f)
        self.check_queue()

    def check_queue(self):
        if self.file_list.count() > 0:
            first_file = self.file_list.item(0).text()
            targets = get_supported_targets(first_file)
            self.combo_format.clear()
            self.combo_format.addItems(targets)
        else:
            self.combo_format.clear()
            self.combo_format.addItem("Queue empty")

    def manual_add(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Add Files to Converter")
        if files:
            for f in files: self.file_list.addItem(f)
            self.check_queue()

    def select_dest(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder", self.output_folder)
        if folder:
            self.output_folder = folder
            self.dest_lbl.setText(f"Target: ...{folder[-25:]}")

    def set_current_as_dest(self):
        if self.file_list.count() > 0:
            self.output_folder = os.path.dirname(self.file_list.item(0).text())
            self.dest_lbl.setText(f"Target: ...{self.output_folder[-25:]}")

    def quick_convert(self, fmt):
        self.combo_format.setCurrentText(fmt)
        self.start_conversion()

    def log(self, text):
        self.console.append(f"> {text}")
        self.console.ensureCursorVisible()

    def start_conversion(self):
        files = [self.file_list.item(i).text() for i in range(self.file_list.count())]
        if not files:
            QMessageBox.warning(self, "Queue Empty", "Please add files to convert first.")
            return

        fmt = self.combo_format.currentText().split(' ')[0]
        name = self.edit_name.text()
        
        self.btn_convert.setEnabled(False)
        self.btn_convert.setText("Converting...")
        self.log(f"Starting batch conversion to {fmt}...")
        
        self.worker = ConversionWorker(files, fmt, self.output_folder, name if name else None)
        self.worker.progress.connect(self.log)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, success, msg):
        self.btn_convert.setEnabled(True)
        self.btn_convert.setText("🔥 START CONVERSION")
        self.log(msg)
        if success:
            QMessageBox.information(self, "Conversion Success", msg)
            self.file_list.clear()
            self.edit_name.clear()
            self.check_queue()
