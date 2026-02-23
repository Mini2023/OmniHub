from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QFileDialog, QFrame, QProgressBar)
from PySide6.QtCore import Qt
from logic.disk_heatmap import DiskScannerWorker
from pathlib import Path

class DiskHeatmapTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        header_lbl = QLabel("Disk Heatmap (Analyzer)")
        header_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #5c8cbc;")
        layout.addWidget(header_lbl)
        
        instruction = QLabel("Visualize storage used by specific file extensions in a directory.")
        instruction.setStyleSheet("color: #666;")
        layout.addWidget(instruction)

        ctrl_layout = QHBoxLayout()
        self.dir_lbl = QLabel(str(Path.home() / "Documents"))
        self.dir_lbl.setStyleSheet("border: 1px solid #dcdcdc; padding: 5px; border-radius: 4px; background: rgba(255,255,255,0.85);")
        ctrl_layout.addWidget(self.dir_lbl)
        
        change_btn = QPushButton("Change Directory")
        change_btn.clicked.connect(self.change_dir)
        ctrl_layout.addWidget(change_btn)
        
        self.scan_btn = QPushButton("Start Scan")
        self.scan_btn.setStyleSheet("background-color: #3cb371; color: white;")
        self.scan_btn.clicked.connect(self.start_scan)
        ctrl_layout.addWidget(self.scan_btn)
        
        layout.addLayout(ctrl_layout)
        
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(self.status_lbl)
        
        # Generative Heatmap Bar
        self.heatmap_frame = QFrame()
        self.heatmap_layout = QHBoxLayout(self.heatmap_frame)
        self.heatmap_layout.setContentsMargins(0,0,0,0)
        self.heatmap_layout.setSpacing(0)
        self.heatmap_frame.setFixedHeight(40)
        self.heatmap_frame.setStyleSheet("border-radius: 8px; border: 1px solid #ccc;")
        layout.addWidget(self.heatmap_frame)
        
        # Generative Legend Mapping
        self.legend_layout = QVBoxLayout()
        layout.addLayout(self.legend_layout)
        
        layout.addStretch()
        self.worker = None

    def change_dir(self):
        new_dir = QFileDialog.getExistingDirectory(self, "Select Directory", self.dir_lbl.text())
        if new_dir:
            self.dir_lbl.setText(new_dir)

    def start_scan(self):
        self.scan_btn.setEnabled(False)
        self.status_lbl.setText("Scanning... please wait. This utilizes a background thread to prevent UI freezing.")
        
        for i in reversed(range(self.heatmap_layout.count())): 
            self.heatmap_layout.itemAt(i).widget().setParent(None)
        for i in reversed(range(self.legend_layout.count())): 
            self.legend_layout.itemAt(i).widget().setParent(None)
            
        self.worker = DiskScannerWorker(self.dir_lbl.text())
        self.worker.progress.connect(self.update_status)
        self.worker.finished.connect(self.on_scan_finished)
        self.worker.start()

    def update_status(self, msg):
        self.status_lbl.setText(msg)

    def on_scan_finished(self, categories, total_bytes):
        self.scan_btn.setEnabled(True)
        if total_bytes == 0:
            self.status_lbl.setText("Scan completed. No files found or accessible.")
            return
            
        tb_mb = total_bytes / (1024*1024)
        self.status_lbl.setText(f"Scan completed. Total mapped size: {tb_mb:.2f} MB")
        
        # Render dynamic UI segments based on percentage
        for cat, data in categories.items():
            bytes_used = data["bytes"]
            if bytes_used > 0:
                percent = bytes_used / total_bytes
                
                segment = QFrame()
                segment.setStyleSheet(f"background-color: {data['color']};")
                self.heatmap_layout.addWidget(segment, max(1, int(percent * 100)))
                
                mb_used = bytes_used / (1024*1024)
                leg = QLabel()
                leg.setText(f"<span style='color:{data['color']}; font-size: 16px;'>■</span> <b>{cat}</b>: {mb_used:.2f} MB ({percent*100:.1f}%)")
                self.legend_layout.addWidget(leg)
