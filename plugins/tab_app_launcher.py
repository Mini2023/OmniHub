import os
import json
import subprocess
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QGridLayout, QScrollArea, QFrame,
                               QFileDialog, QInputDialog, QMessageBox, QLineEdit)
from PySide6.QtCore import Qt

CONFIG_FILE = "launcher_config.json"

class AppLauncherTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        self.header_label = QLabel("App Launcher")
        self.header_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #5c8cbc;")
        header_layout.addWidget(self.header_label)
        
        header_layout.addStretch()
        
        self.add_btn = QPushButton("+ Add New App")
        self.add_btn.setStyleSheet("""
            QPushButton { background-color: #3cb371; color: white; padding: 8px 16px; border-radius: 8px; }
            QPushButton:hover { background-color: #2e8b57; }
        """)
        self.add_btn.clicked.connect(self.add_app)
        header_layout.addWidget(self.add_btn)
        
        self.layout.addLayout(header_layout)

        self.instruction = QLabel("One-click launch for your favorite applications. Apps are automatically saved. Click 'Add New App' to customize.")
        self.instruction.setStyleSheet("color: #666; margin-bottom: 10px;")
        self.layout.addWidget(self.instruction)

        # Scroll Area for the Grid
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background-color: transparent;")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(15)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        self.scroll.setWidget(self.grid_container)
        self.layout.addWidget(self.scroll, 1) # Give scroll area remaining space
        
        self.apps = []
        self.load_config()
        self.refresh_grid()

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            # Create default config with Chrome, VS Code, and VLC as requested
            try:
                username = os.getlogin()
            except:
                username = "Mini2023"
                
            self.apps = [
                {"name": "Google Chrome", "path": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"},
                {"name": "VS Code", "path": f"C:\\Users\\{username}\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe"},
                {"name": "VLC Media Player", "path": "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe"}
            ]
            self.save_config()
        else:
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.apps = json.load(f)
            except Exception as e:
                self.apps = []
                QMessageBox.warning(self, "Config Error", f"Failed to load launcher configs: {e}")

    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.apps, f, indent=4)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save config: {e}")

    def refresh_grid(self):
        # Clear existing grid parameters before rendering new state
        for i in reversed(range(self.grid_layout.count())): 
            widget = self.grid_layout.itemAt(i).widget()
            if widget is not None: 
                widget.setParent(None)

        # Populate grid (3 columns wide)
        columns = 3
        for index, app in enumerate(self.apps):
            row = index // columns
            col = index % columns
            
            card = self.create_app_card(app, index)
            self.grid_layout.addWidget(card, row, col)

    def create_app_card(self, app, index):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.9);
                border: 1px solid #B0C4DE;
                border-radius: 12px;
            }
            QFrame:hover {
                background-color: #F8FAFF;
                border: 2px solid #A2D2FF;
            }
        """)
        frame.setFixedSize(220, 130)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        
        name_lbl = QLabel(app["name"])
        name_lbl.setStyleSheet("font-size: 16px; font-weight: bold; border: none; background: transparent; color: #1a1a1a;")
        name_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(name_lbl)
        
        path_text = os.path.basename(app["path"])
        path_lbl = QLabel(f"➔ {path_text}")
        path_lbl.setStyleSheet("color: #888; font-size: 11px; border: none; background: transparent;")
        path_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(path_lbl)
        
        layout.addStretch()
        
        btn_layout = QHBoxLayout()
        launch_btn = QPushButton("Launch")
        launch_btn.setStyleSheet("""
            QPushButton { background-color: #B0C4DE; color: #333; font-weight: bold; border-radius: 6px; padding: 6px; border: none; }
            QPushButton:hover { background-color: #A2D2FF; }
        """)
        # We hook into subprocess
        launch_btn.clicked.connect(lambda checked, p=app["path"]: self.launch_app(p))
        
        del_btn = QPushButton("✖")
        del_btn.setStyleSheet("""
            QPushButton { background-color: transparent; color: #ff4d4d; font-weight: bold; border-radius: 6px; padding: 6px; width: 25px; border: none;}
            QPushButton:hover { background-color: #ffe6e6; }
        """)
        del_btn.clicked.connect(lambda checked, idx=index: self.remove_app(idx))
        
        btn_layout.addWidget(launch_btn)
        btn_layout.addWidget(del_btn)
        
        layout.addLayout(btn_layout)
        return frame

    def launch_app(self, path):
        if os.path.exists(path):
            try:
                subprocess.Popen(path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not launch executable:\n{e}")
        else:
            QMessageBox.warning(self, "Not Found", f"Executable not found at:\n{path}\n\nPlease check the path or remove this entry.")

    def add_app(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Application Executable", "C:\\", "Executables (*.exe *.bat *.cmd)")
        if not path:
            return
            
        name = os.path.basename(path).split('.')[0].capitalize()
        # Prompt user to edit/confirm the display name
        text, ok = QInputDialog.getText(self, "App Shortcut Name", "Enter a display name for this shortcut:", QLineEdit.Normal, name)
        
        if ok and text:
            self.apps.append({"name": text.strip(), "path": path})
            self.save_config()
            self.refresh_grid()

    def remove_app(self, index):
        reply = QMessageBox.question(self, 'Remove App', 'Are you sure you want to remove this shortcut?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.apps.pop(index)
            self.save_config()
            self.refresh_grid()
