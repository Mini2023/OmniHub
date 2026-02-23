from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem
from logic.clipboard_history import ClipboardManager
import pyperclip

class ClipboardHistoryTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        header_layout = QHBoxLayout()
        header_label = QLabel("Clipboard History")
        header_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #5c8cbc;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        
        self.clear_btn = QPushButton("Clear History")
        self.clear_btn.setStyleSheet("""
            QPushButton { background-color: #ff4d4d; color: white; padding: 6px 12px; border-radius: 6px; }
            QPushButton:hover { background-color: #ff1a1a; }
        """)
        self.clear_btn.clicked.connect(self.clear_history)
        header_layout.addWidget(self.clear_btn)
        layout.addLayout(header_layout)
        
        instruction = QLabel("Logs your last 20 text clips in the background. Click any item to copy it back to your clipboard.")
        instruction.setStyleSheet("color: #666;")
        layout.addWidget(instruction)
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("background-color: rgba(255, 255, 255, 0.85); font-size: 14px;")
        self.list_widget.itemClicked.connect(self.item_clicked)
        layout.addWidget(self.list_widget)
        
        self.manager = ClipboardManager()
        self.manager.history_updated.connect(self.update_list)
        self.manager.start()

    def update_list(self, history):
        self.list_widget.clear()
        for item in history:
            # truncate long clips for display
            display_text = item.replace('\n', ' ')
            if len(display_text) > 100: display_text = display_text[:100] + "..."
            list_item = QListWidgetItem(display_text)
            list_item.setData(100, item) # Store full text
            self.list_widget.addItem(list_item)
            
    def clear_history(self):
        self.manager.clear_history()

    def item_clicked(self, item):
        full_text = item.data(100)
        pyperclip.copy(full_text)
