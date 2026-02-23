import os
import qtawesome as qta
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                QPushButton, QFileDialog, QTextEdit, QFrame,
                                QListWidget, QListWidgetItem, QMenu, QMessageBox)
from PySide6.QtCore import Qt, QSize
from logic.folder_watcher import WatchdogManager

class FolderWatcherTab(QWidget):
    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.setStyleSheet("background-color: #F8FAFC; font-family: 'Inter';")
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)

        # Connect signals
        self.manager.log_signal.connect(self.log_message)

        # --- LEFT COLUMN: Monitoring ---
        left_pane = QVBoxLayout()
        
        main_box = QGroupBoxUI("Main Monitoring", "#3182CE")
        main_layout = main_box.layout()
        
        self.main_path_lbl = QLabel(self.manager.config["main_path"])
        self.main_path_lbl.setWordWrap(True)
        self.main_path_lbl.setStyleSheet("color: #4A5568; font-size: 11px; padding: 5px; border: 1px solid #E2E8F0; border-radius: 6px; background: white;")
        main_layout.addWidget(self.main_path_lbl)
        
        m_btns = QHBoxLayout()
        self.btn_change_main = QPushButton(" Change Folder")
        self.btn_change_main.setIcon(qta.icon('fa5s.folder-open', color="white"))
        self.btn_change_main.setStyleSheet("background: #A2D2FF; color: white; padding: 8px; border-radius: 8px; font-weight: bold;")
        self.btn_change_main.clicked.connect(self.change_main_folder)
        
        self.btn_toggle_main = QPushButton(" Enable")
        self.btn_toggle_main.setIcon(qta.icon('fa5s.play', color="white"))
        self.btn_toggle_main.setStyleSheet("background: #48BB78; color: white; padding: 8px; border-radius: 8px; font-weight: bold;")
        self.btn_toggle_main.clicked.connect(self.toggle_main)
        
        m_btns.addWidget(self.btn_change_main)
        m_btns.addWidget(self.btn_toggle_main)
        main_layout.addLayout(m_btns)
        left_pane.addWidget(main_box)

        # Sub Directories
        sub_box = QGroupBoxUI("Additional Folders", "#718096")
        sub_layout = sub_box.layout()
        self.sub_list = QListWidget()
        self.sub_list.setStyleSheet("border: 1px solid #E2E8F0; border-radius: 8px; background: white;")
        sub_layout.addWidget(self.sub_list)
        
        s_btns = QHBoxLayout()
        btn_add_sub = QPushButton("+")
        btn_add_sub.setStyleSheet("background: #EDF2F7; border-radius: 6px; padding: 5px; font-weight: bold;")
        btn_add_sub.clicked.connect(self.add_sub_folder)
        btn_rem_sub = QPushButton("-")
        btn_rem_sub.setStyleSheet("background: #EDF2F7; border-radius: 6px; padding: 5px; font-weight: bold;")
        btn_rem_sub.clicked.connect(self.remove_sub_folder)
        s_btns.addWidget(btn_add_sub)
        s_btns.addWidget(btn_rem_sub)
        s_btns.addStretch()
        sub_layout.addLayout(s_btns)
        left_pane.addWidget(sub_box)

        # Live Log Console
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("background: #2D3748; color: #A0AEC0; border-radius: 12px; font-family: Consolas; font-size: 10px; padding: 10px;")
        self.console.setPlaceholderText("Live logs appear here...")
        left_pane.addWidget(self.console, 1)
        
        self.main_layout.addLayout(left_pane, 4)

        # --- RIGHT COLUMN: Actions & Settings ---
        right_pane = QVBoxLayout()
        
        # Quick Actions
        qa_box = QGroupBoxUI("Quick Actions", "#E53E3E")
        qa_layout = qa_box.layout()
        
        actions = [
            ("⚡ Sort Now", self.manager.sort_now),
            ("🔍 Deep Check (Correct Location)", self.manager.deep_check),
            ("📂 Scan External Directory", self.scan_external),
            ("↩️ Undo Last Action", self.manager.undo_last)
        ]
        
        for name, func in actions:
            btn = QPushButton(name)
            btn.setStyleSheet("text-align: left; padding: 10px; border: none; border-radius: 6px; color: #4A5568;")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(func)
            qa_layout.addWidget(btn)
        right_pane.addWidget(qa_box)

        # Settings
        set_box = QGroupBoxUI("Settings", "#4A5568")
        set_layout = set_box.layout()
        
        settings = [
            ("⚙️ Change Sorting Algorithm", self.edit_sorting),
            ("🏷️ Change Target Names", lambda: None),
            ("🚚 Move Whole Watchdog Folder", self.move_watchdog)
        ]
        
        for name, func in settings:
            btn = QPushButton(name)
            btn.setStyleSheet("text-align: left; padding: 10px; border: none; border-radius: 6px; color: #4A5568;")
            btn.clicked.connect(func)
            set_layout.addWidget(btn)
        right_pane.addWidget(set_box)

        # Quick Open
        open_box = QGroupBoxUI("Quick Open", "#3182CE")
        open_layout = QHBoxLayout()
        open_box.layout().addLayout(open_layout)

        open_layout.setSpacing(10)
        
        open_btns = [
            ('fa5s.home', "Main", lambda: os.startfile(self.manager.config["main_path"])),
            ('fa5s.image', "Images", lambda: self.open_sub("Images")),
            ('fa5s.file-pdf', "Docs", lambda: self.open_sub("Documents")),
            ('fa5s.video', "Videos", lambda: self.open_sub("Videos"))
        ]
        
        for icon, tip, func in open_btns:
            btn = QPushButton()
            btn.setIcon(qta.icon(icon, color="#4A5568"))
            btn.setToolTip(tip)
            btn.setFixedSize(45, 45)
            btn.setStyleSheet("background: white; border: 1px solid #E2E8F0; border-radius: 10px;")
            btn.clicked.connect(func)
            open_layout.addWidget(btn)
        right_pane.addWidget(open_box)
        
        right_pane.addStretch()
        self.main_layout.addLayout(right_pane, 3)
        self.update_ui_state()

    def log_message(self, msg):
        self.console.append(f"> {msg}")
        self.console.ensureCursorVisible()

    def update_ui_state(self):
        active = self.manager.config["active"]
        self.btn_toggle_main.setText(" Stop" if active else " Start")
        self.btn_toggle_main.setIcon(qta.icon('fa5s.stop' if active else 'fa5s.play', color="white"))
        self.btn_toggle_main.setStyleSheet(f"background: {'#FC8181' if active else '#48BB78'}; color: white; padding: 8px; border-radius: 8px; font-weight: bold;")
        self.main_path_lbl.setText(self.manager.config["main_path"])

    def toggle_main(self):
        if self.manager.config["active"]:
            self.manager.stop_main()
        else:
            self.manager.start_main()
        self.update_ui_state()

    def change_main_folder(self):
        p = QFileDialog.getExistingDirectory(self, "Select Main Watchdog Folder", self.manager.config["main_path"])
        if p:
            self.manager.config["main_path"] = p
            self.manager.save_config()
            self.update_ui_state()

    def add_sub_folder(self):
        p = QFileDialog.getExistingDirectory(self, "Add Additional Folder to Watch")
        if p and p not in self.manager.config["sub_paths"]:
            self.manager.config["sub_paths"].append(p)
            self.manager.save_config()
            self.sub_list.addItem(p)
            self.manager.start_observer(p)

    def remove_sub_folder(self):
        cur = self.sub_list.currentItem()
        if cur:
            path = cur.text()
            self.manager.stop_observer(path)
            self.manager.config["sub_paths"].remove(path)
            self.manager.save_config()
            self.sub_list.takeItem(self.sub_list.row(cur))

    def scan_external(self):
        p = QFileDialog.getExistingDirectory(self, "Select External Directory to Import & Sort")
        if p: self.manager.scan_external(p)

    def open_sub(self, name):
        p = os.path.join(self.manager.config["main_path"], name)
        if os.path.exists(p): os.startfile(p)

    def edit_sorting(self):
        QMessageBox.information(self, "Editor", "Sorting Algorithm editor coming in v4.0 Patch.")

    def move_watchdog(self):
        p = QFileDialog.getExistingDirectory(self, "Select New Location for Watchdog Folder")
        if p:
            self.log_message(f"Moving Watchdog to {p}...")
            # Logic to move subfolders could go here

class QGroupBoxUI(QFrame):
    def __init__(self, title, color="#3182CE", parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: white; border-radius: 12px; border: 1px solid #E2E8F0;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        lbl = QLabel(title)
        lbl.setStyleSheet(f"font-weight: bold; color: {color}; font-size: 13px; border: none;")
        layout.addWidget(lbl)
        
    def addLayout(self, l):
        self.layout().addLayout(l)
    def addWidget(self, w):
        self.layout().addWidget(w)
