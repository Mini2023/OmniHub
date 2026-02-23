from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

class ImageProTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        lbl = QLabel("Image Pro Tools")
        lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #5c8cbc;")
        layout.addWidget(lbl)
        
        desc = QLabel("Use the Global Drag & Drop menu to automatically clean or compress images.")
        desc.setStyleSheet("color: #666; font-size: 14px;")
        layout.addWidget(desc)
        layout.addStretch()
