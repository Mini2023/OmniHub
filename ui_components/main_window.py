import os
import json
import subprocess
from PySide6.QtCore import Qt, QSize, QFileInfo, QTimer
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QColor, QCursor, QAction, QDesktopServices, QIcon
from PySide6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
                                QPushButton, QStackedWidget, QLabel, QFrame, 
                                QGridLayout, QComboBox, QProgressBar,
                                QMessageBox, QMenu, QLineEdit, QScrollArea,
                                QFileIconProvider, QGraphicsDropShadowEffect)
import qtawesome as qta

from plugins.tab_universal_converter import UniversalConverterTab
from plugins.tab_archive_master import ArchiveMasterTab
from plugins.tab_ai_assistant import AIAssistantTab
from plugins.tab_folder_watcher import FolderWatcherTab
from plugins.tab_encryption_vault import EncryptionVaultTab
from plugins.tab_clipboard_history import ClipboardHistoryTab
from plugins.tab_disk_heatmap import DiskHeatmapTab
from plugins.tab_system_health import SystemHealthTab
from plugins.tab_pdf_docs import PdfDocsTab
from plugins.tab_image_pro import ImageProTab
from logic.folder_watcher import WatchdogManager

class SystemHealthWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(160, 35)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            SystemHealthWidget { 
                background-color: #FFFFFF; border-radius: 12px; border: 1px solid #D0D7DE;
            }
            SystemHealthWidget:hover { border: 1px solid #3182CE; background-color: #F7FAFC; }
            QLabel { background: transparent; border: none; padding: 2px; }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        
        self.icon_lbl = QLabel()
        self.icon_lbl.setPixmap(qta.icon('fa5s.heartbeat', color="#E53E3E").pixmap(16, 16))
        layout.addWidget(self.icon_lbl)
        
        self.val_lbl = QLabel("Health: --%")
        self.val_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #4A5568; background: transparent;")
        layout.addWidget(self.val_lbl)
        layout.addStretch()

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_score)
        self.timer.start(5000)
        self.refresh_score()

    def refresh_score(self):
        try:
            from logic.system_health import get_system_vitals
            c, r, d = get_system_vitals()
            score = 100 - (c*0.2 + r*0.3)
            self.val_lbl.setText(f"Health: {int(max(0, score))}%")
        except: pass

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.window().go_to_tool(2) # System Health index

class WatchdogWidget(QFrame):
    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.setFixedSize(200, 35)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            WatchdogWidget {
                background-color: #FFFFFF; border-radius: 12px; border: 1px solid #D0D7DE;
            }
            WatchdogWidget:hover { border: 1px solid #3182CE; background-color: #F7FAFC; }
            QLabel { background: transparent; border: none; padding: 2px; }
        """)
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 0, 10, 0)
        
        self.dot = QLabel()
        self.dot.setFixedSize(10, 10)
        self.update_dot(False)
        self.layout.addWidget(self.dot)
        
        self.lbl = QLabel("Watchdog: Inactive")
        self.lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #4A5568; background: transparent;")
        self.layout.addWidget(self.lbl)
        self.layout.addStretch()

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        self.manager.status_changed.connect(self.on_status_changed)
        self.on_status_changed(self.manager.config["active"], self.manager.config["main_path"])

    def update_dot(self, active):
        color = "#48BB78" if active else "#CBD5E0"
        self.dot.setStyleSheet(f"background-color: {color}; border-radius: 5px;")

    def on_status_changed(self, active, path):
        self.update_dot(active)
        folder = os.path.basename(path) if path else "None"
        self.lbl.setText(f"Watchdog: {folder}" if active else "Watchdog: Inactive")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.show_popup()

    def show_popup(self):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background: white; border: 1px solid #E2E8F0; border-radius: 8px; padding: 5px; }")
        
        path = self.manager.config["main_path"]
        header = QAction(f"Active Dir: {os.path.basename(path)}", self)
        header.setEnabled(False)
        menu.addAction(header)
        menu.addSeparator()
        
        active = self.manager.config["active"]
        toggle_text = "🔴 Disable Watchdog" if active else "🟢 Enable Watchdog"
        toggle_act = QAction(toggle_text, self)
        toggle_act.triggered.connect(self.toggle)
        menu.addAction(toggle_act)
        
        view_act = QAction("🔍 View in Module", self)
        view_act.triggered.connect(lambda: self.window().go_to_tool(9)) # Watchdog is index 9
        menu.addAction(view_act)
        
        menu.exec(QCursor.pos())

    def toggle(self):
        if self.manager.config["active"]:
            self.manager.stop_main()
        else:
            self.manager.start_main()


class ContextMemoryWidget(QFrame):
    """Live compact widget in the Dashboard status bar.
    Polls the AI Assistant's conversation history every 3 s and shows
    a colour-coded fill bar. Click to jump straight to the AI module."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ai_tab = None
        self.setFixedSize(210, 35)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            ContextMemoryWidget {
                background-color: #FFFFFF; border-radius: 12px; border: 1px solid #D0D7DE;
            }
            ContextMemoryWidget:hover { border: 1px solid #3182CE; background-color: #F7FAFC; }
            QLabel { background: transparent; border: none; padding: 1px; }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(6)

        self.icon_lbl = QLabel()
        self.icon_lbl.setPixmap(qta.icon('fa5s.brain', color="#805AD5").pixmap(14, 14))
        layout.addWidget(self.icon_lbl)

        txt_col = QVBoxLayout()
        txt_col.setSpacing(1)
        txt_col.setContentsMargins(0, 2, 0, 2)

        self.title_lbl = QLabel("AI Memory")
        self.title_lbl.setStyleSheet(
            "font-size: 10px; font-weight: 700; color: #4A5568; background: transparent;"
        )
        txt_col.addWidget(self.title_lbl)

        self.mem_bar = QProgressBar()
        self.mem_bar.setRange(0, 100)
        self.mem_bar.setValue(0)
        self.mem_bar.setTextVisible(False)
        self.mem_bar.setFixedHeight(5)
        self.mem_bar.setStyleSheet("""
            QProgressBar { background: #E2E8F0; border-radius: 2px; border: none; }
            QProgressBar::chunk {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #9F7AEA, stop:0.7 #805AD5, stop:1 #E53E3E);
                border-radius: 2px;
            }
        """)
        txt_col.addWidget(self.mem_bar)
        layout.addLayout(txt_col)

        self.pct_lbl = QLabel("0 %")
        self.pct_lbl.setStyleSheet(
            "font-size: 10px; font-weight: 700; color: #805AD5; background: transparent;"
        )
        layout.addWidget(self.pct_lbl)

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAutoFillBackground(False)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(3000)

    def bind_ai_tab(self, ai_tab):
        """Assign the AIAssistantTab instance after tool registration."""
        self._ai_tab = ai_tab
        self._refresh()

    def _refresh(self):
        if self._ai_tab is None:
            return
        try:
            from logic.ai_engine import get_context_fill_ratio
            ratio = get_context_fill_ratio(self._ai_tab._conversation_history)
            pct = int(ratio * 100)
            self.mem_bar.setValue(pct)
            self.pct_lbl.setText(f"{pct} %")
            colour = "#48BB78" if ratio < 0.5 else ("#ED8936" if ratio < 0.75 else "#E53E3E")
            self.pct_lbl.setStyleSheet(
                f"font-size:10px;font-weight:700;color:{colour};background:transparent;"
            )
        except Exception:
            pass

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.window().go_to_tool(4)  # AI Assistant is always at index 4


LAUNCHER_CONFIG = "launcher_config.json"

class LauncherSlot(QPushButton):
    def __init__(self, key, parent=None):
        super().__init__(parent)
        self.key = key
        self.app_path = ""
        self.app_name = ""
        self.setFixedSize(80, 80)
        self.setCursor(Qt.PointingHandCursor)
        self.refresh()
        
    def refresh(self):
        if not os.path.exists(LAUNCHER_CONFIG):
            self.app_path = ""
        else:
            try:
                with open(LAUNCHER_CONFIG, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if isinstance(config, list) and len(config) > self.key:
                        self.app_path = config[self.key].get("path", "")
                        self.app_name = config[self.key].get("name", "")
            except:
                self.app_path = ""

        if self.app_path and os.path.exists(self.app_path):
            self.setText("")
            # Native Icon Extraction
            info = QFileInfo(self.app_path)
            icon = QFileIconProvider().icon(info)
            self.setIcon(icon)
            self.setIconSize(QSize(42, 42))
            self.setToolTip(f"Start: {self.app_name}")
            self.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF; border: 1px dashed #E1E4E8; border-radius: 8px;
                }
                QPushButton:hover { background-color: #EDF2F7; border: 1px solid #3182CE; }
            """)
        else:
            self.setText("+")
            self.setIcon(qta.icon('fa5s.plus', color="#718096"))
            self.setIconSize(QSize(24, 24))
            self.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF; border: 1px dashed #E1E4E8; border-radius: 8px;
                    color: #718096; font-size: 20px; font-weight: bold;
                }
                QPushButton:hover { background-color: #F7FAFC; border: 1px solid #3182CE; color: #3182CE; }
            """)
            self.setToolTip("Slot belegen")
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAutoFillBackground(False)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.app_path and os.path.exists(self.app_path):
                subprocess.Popen(self.app_path)
            else:
                self.select_app()
        super().mousePressEvent(event)

    def select_app(self):
        from PySide6.QtWidgets import QFileDialog, QInputDialog
        path, _ = QFileDialog.getOpenFileName(self, "App wählen", "C:\\", "Executables (*.exe)")
        if path:
            name, ok = QInputDialog.getText(self, "Name", "Anzeigename:", QLineEdit.Normal, os.path.basename(path).split('.')[0])
            if ok and name:
                config = []
                if os.path.exists(LAUNCHER_CONFIG):
                    try:
                        with open(LAUNCHER_CONFIG, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                    except:
                        config = []
                
                new_entry = {"name": name, "path": path}
                if len(config) > self.key:
                    config[self.key] = new_entry
                else:
                    while len(config) <= self.key:
                        config.append({"name": "Empty", "path": ""})
                    config[self.key] = new_entry
                
                with open(LAUNCHER_CONFIG, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=4)
                self.refresh()

class ToolTile(QFrame):
    def __init__(self, title, description, icon_name, index, parent=None):
        super().__init__(parent)
        self.index = index
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            ToolTile {
                background-color: #FFFFFF; border-radius: 12px; border: 1px solid #D0D7DE;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.setContentsMargins(20, 15, 20, 15)
        
        self.icon_lbl = QLabel()
        self.icon_lbl.setPixmap(qta.icon(icon_name, color="#3182CE").pixmap(32, 32))
        self.icon_lbl.setAlignment(Qt.AlignLeft)
        self.icon_lbl.setStyleSheet("background: transparent; border: none; margin-left: -2px;")
        layout.addWidget(self.icon_lbl)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #2D3748; background: transparent; border: none;")
        title_lbl.setAlignment(Qt.AlignLeft)
        layout.addWidget(title_lbl)
        
        desc_lbl = QLabel(description)
        desc_lbl.setStyleSheet("font-size: 10px; color: #718096; background: transparent; border: none;")
        desc_lbl.setAlignment(Qt.AlignLeft)
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)
        
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(15)
        self.shadow.setXOffset(0)
        self.shadow.setYOffset(4)
        self.shadow.setColor(QColor(0, 0, 0, 0))
        self.setGraphicsEffect(self.shadow)

    def enterEvent(self, event):
        self.setStyleSheet("ToolTile { background-color: #FFFFFF; border: 1px solid #3182CE; border-radius: 12px; }")
        self.shadow.setColor(QColor(0, 0, 0, 40))
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet("ToolTile { background-color: #FFFFFF; border: 1px solid #D0D7DE; border-radius: 12px; }")
        self.shadow.setColor(QColor(0, 0, 0, 0))
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.window().go_to_tool(self.index)

class GlobalDropZone(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            GlobalDropZone {
                background-color: white; border: 2px dashed #CBD5E0; border-radius: 20px;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        
        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon('fa5s.cloud-upload-alt', color="#3182CE").pixmap(50, 50))
        icon_lbl.setStyleSheet("background: transparent;")
        layout.addWidget(icon_lbl)
        
        vbox = QVBoxLayout()
        vbox.setAlignment(Qt.AlignCenter)
        lbl = QLabel("Global Drop-Hub")
        lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #2D3748; background: transparent;")
        vbox.addWidget(lbl)
        
        sub = QLabel("Dateien hier ablegen für Sofort-Aktionen & KI-Analyse")
        sub.setStyleSheet("font-size: 13px; color: #718096; background: transparent;")
        vbox.addWidget(sub)
        layout.addLayout(vbox)
        layout.addStretch()
        self.setMinimumHeight(120)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAutoFillBackground(False)

        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(20)
        self.shadow.setColor(QColor(0,0,0,0))
        self.setGraphicsEffect(self.shadow)

    def enterEvent(self, event):
        self.setStyleSheet("GlobalDropZone { background-color: #EDF2F7; border: 2px dashed #3182CE; border-radius: 20px; }")
        self.shadow.setColor(QColor(0,0,0,30))
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet("GlobalDropZone { background-color: white; border: 2px dashed #CBD5E0; border-radius: 20px; }")
        self.shadow.setColor(QColor(0,0,0,0))
        super().leaveEvent(event)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        print("MainWindow initializing...")
        self.setWindowTitle("Omni-Hub v3.9.5")
        self.resize(1150, 850)
        self.setAcceptDrops(True)
        self.tools = []
        
        # Initialize Watchdog Manager
        self.watchdog_manager = WatchdogManager()
        if self.watchdog_manager.config["active"]:
            self.watchdog_manager.start_main()
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.main_stack = QStackedWidget()
        self.main_layout.addWidget(self.main_stack)
        
        # --- Dashboard ---
        self.setup_dashboard()
        # --- Tool View ---
        self.setup_tool_view()
        
        # Register tools
        self.register_all_tools()
        self.populate_tool_lists()
        
        self.main_stack.setCurrentIndex(0)
        print("MainWindow stack index 0 (Dashboard) set.")

    def setup_dashboard(self):
        self.dashboard_widget = QWidget()
        self.dashboard_widget.setStyleSheet("""
            QWidget#Dashboard { background-color: #F8FAFC; }
            QLabel { background-color: transparent; border: none; }
            #LauncherBox, #ToolBox, #QuickActionBox { 
                background-color: #FFFFFF; border: 1px solid #D0D7DE; border-radius: 12px; 
            }
        """)
        self.dashboard_widget.setObjectName("Dashboard")
        dash_layout = QVBoxLayout(self.dashboard_widget)
        dash_layout.setContentsMargins(30, 15, 30, 30)
        dash_layout.setSpacing(6) # Even tighter
        
        # Header
        header = QHBoxLayout()
        
        self.ver_lbl = QLabel("ver. 3.9.5")
        self.ver_lbl.setStyleSheet("""
            background: #EDF2F7; color: #718096; padding: 4px 12px; 
            border-radius: 12px; font-size: 11px; font-weight: bold;
        """)
        header.addWidget(self.ver_lbl)
        
        self.btn_changelog = QPushButton("Changelog")
        self.btn_changelog.setIcon(qta.icon('fa5s.clipboard-list', color="#3182CE"))
        self.btn_changelog.setStyleSheet("""
            QPushButton { background: white; border: 1px solid #E2E8F0; border-radius: 12px; padding: 4px 12px; font-size: 11px; color: #3182CE; }
            QPushButton:hover { background: #F7FAFC; }
        """)
        self.btn_changelog.setCursor(Qt.PointingHandCursor)
        self.btn_changelog.clicked.connect(lambda: os.startfile("changelog.txt") if os.path.exists("changelog.txt") else None)
        header.addWidget(self.btn_changelog)
        
        header.addStretch()
        title = QLabel("Omni-Hub Dashboard")
        title.setStyleSheet("font-size: 26px; font-weight: 800; color: #1A202C; background: transparent;")
        header.addWidget(title)
        header.addStretch()
        
        links = QHBoxLayout()
        btn_web = QPushButton("Webpage")
        btn_web.setIcon(qta.icon('fa5s.globe', color="#4A5568"))
        btn_web.setStyleSheet("border: none; color: #4A5568; font-weight: 600; padding: 5px;")
        btn_web.clicked.connect(lambda: QDesktopServices.openUrl("https://www.google.com/search?q=google.com"))
        btn_git = QPushButton("GitHub")
        btn_git.setIcon(qta.icon('fa5b.github', color="#4A5568"))
        btn_git.setStyleSheet("border: none; color: #4A5568; font-weight: 600; padding: 5px;")
        btn_git.clicked.connect(lambda: QDesktopServices.openUrl("https://github.com"))
        links.addWidget(btn_web)
        links.addWidget(btn_git)
        header.addLayout(links)
        dash_layout.addLayout(header)
        
        # Status Bar (Compact Live-Widgets)
        status_bar = QHBoxLayout()
        status_bar.setContentsMargins(0, 0, 0, 0) # Close gap
        status_bar.setSpacing(10)
        
        self.watchdog_widget = WatchdogWidget(self.watchdog_manager)
        status_bar.addWidget(self.watchdog_widget)
        
        self.health_widget = SystemHealthWidget()
        status_bar.addWidget(self.health_widget)

        self.context_memory_widget = ContextMemoryWidget()
        status_bar.addWidget(self.context_memory_widget)
        
        status_bar.addStretch()
        dash_layout.addLayout(status_bar)
        
        # Mid
        mid_layout = QHBoxLayout()
        mid_layout.setSpacing(20)
        self.drop_hub = GlobalDropZone()
        self.drop_hub.setObjectName("GlobalDrop")
        mid_layout.addWidget(self.drop_hub, 7)
        
        launcher_vbox = QVBoxLayout()
        launcher_header = QHBoxLayout()
        launcher_title = QLabel("App Launcher")
        launcher_title.setStyleSheet("font-weight: bold; color: #4A5568; font-size: 14px; background: transparent;")
        launcher_header.addWidget(launcher_title)
        
        btn_edit_launcher = QPushButton()
        btn_edit_launcher.setIcon(qta.icon('fa5s.edit', color="#718096"))
        btn_edit_launcher.setFixedSize(24, 24)
        btn_edit_launcher.setCursor(Qt.PointingHandCursor)
        btn_edit_launcher.setStyleSheet("border: none; background: transparent;")
        btn_edit_launcher.clicked.connect(self.show_launcher_edit_menu)
        launcher_header.addWidget(btn_edit_launcher)
        launcher_header.addStretch()
        launcher_vbox.addLayout(launcher_header)

        launcher_box = QFrame()
        launcher_box.setObjectName("LauncherBox")
        launcher_box.setMinimumWidth(280)
        launcher_l = QVBoxLayout(launcher_box)
        slots_layout = QHBoxLayout()
        slots_layout.setAlignment(Qt.AlignCenter)
        slots_layout.setContentsMargins(0, 10, 0, 10)
        self.slots = [LauncherSlot(0), LauncherSlot(1), LauncherSlot(2)]
        for s in self.slots: slots_layout.addWidget(s)
        launcher_l.addLayout(slots_layout)
        launcher_vbox.addWidget(launcher_box)
        
        mid_layout.addLayout(launcher_vbox, 3)
        dash_layout.addLayout(mid_layout)
        
        # Bottom
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(25)
        
        left_side = QVBoxLayout()
        main_tools_lbl = QLabel("Main Tools")
        main_tools_lbl.setStyleSheet("font-weight: bold; color: #4A5568; font-size: 15px; background: transparent;")
        left_side.addWidget(main_tools_lbl)
        self.main_tools_grid = QGridLayout()
        self.main_tools_grid.setSpacing(15)
        left_side.addLayout(self.main_tools_grid)
        
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search tools:"))
        self.tool_search = QLineEdit()
        self.tool_search.setPlaceholderText("Filter tools...")
        self.tool_search.setStyleSheet("padding: 8px; border-radius: 8px; border: 1px solid #CBD5E0; background: white;")
        self.tool_search.textChanged.connect(self.filter_tools)
        search_layout.addWidget(self.tool_search)
        left_side.addLayout(search_layout)
        
        self.all_tools_scroll = QScrollArea()
        self.all_tools_scroll.setWidgetResizable(True)
        self.all_tools_scroll.setStyleSheet("border: none; background: transparent;")
        self.tool_list_widget = QWidget()
        self.tool_list_layout = QVBoxLayout(self.tool_list_widget)
        self.tool_list_layout.setAlignment(Qt.AlignTop)
        self.all_tools_scroll.setWidget(self.tool_list_widget)
        left_side.addWidget(self.all_tools_scroll)
        bottom_layout.addLayout(left_side, 7)
        
        right_side = QVBoxLayout()
        qa_lbl = QLabel("Quick Actions")
        qa_lbl.setStyleSheet("font-weight: bold; color: #4A5568; font-size: 15px; background: transparent;")
        right_side.addWidget(qa_lbl)
        qa_box = QFrame()
        qa_box.setObjectName("QuickActionBox")
        qa_vbox = QVBoxLayout(qa_box)
        self.btn_qa_clean = QPushButton("✨ Clear Temp Files")
        self.btn_qa_clean.setStyleSheet("""
            QPushButton { text-align: left; padding: 12px; border: none; font-weight: 600; border-radius: 8px; color: #2D3748; background: transparent;}
            QPushButton:hover { background-color: #F7FAFC; color: #3182CE; }
        """)
        self.btn_qa_clean.clicked.connect(self.quick_action_cleanup)
        qa_vbox.addWidget(self.btn_qa_clean)
        qa_vbox.addStretch()
        right_side.addWidget(qa_box)
        bottom_layout.addLayout(right_side, 3)
        dash_layout.addLayout(bottom_layout)
        self.main_stack.addWidget(self.dashboard_widget)

    def setup_tool_view(self):
        self.tool_view = QWidget()
        self.tool_view.setStyleSheet("background-color: #F0F2F5;")
        tool_view_layout = QVBoxLayout(self.tool_view)
        tool_view_layout.setContentsMargins(20, 15, 20, 20)
        tool_view_layout.setSpacing(15)
        
        tbar = QFrame()
        tbar_layout = QHBoxLayout(tbar)
        self.btn_home = QPushButton("🏠 Home / Dashboard")
        self.btn_home.setStyleSheet("""
            QPushButton {
                background-color: white; border: 1px solid #CBD5E0; border-radius: 8px; 
                padding: 8px 20px; font-size: 13px; color: #2d3748; font-weight: bold;
            }
            QPushButton:hover { background-color: #EDF2F7; border-color: #3182CE; }
        """)
        self.btn_home.clicked.connect(self.go_home)
        tbar_layout.addWidget(self.btn_home)
        tbar_layout.addStretch()
        self.combo_switch = QComboBox()
        self.combo_switch.setMinimumWidth(250)
        self.combo_switch.setStyleSheet("QComboBox { padding: 6px; border-radius: 6px; border: 1px solid #CBD5E0; background: white; }")
        self.combo_switch.currentIndexChanged.connect(self.on_combo_changed)
        tbar_layout.addWidget(self.combo_switch)
        tool_view_layout.addWidget(tbar)
        
        self.tool_stack = QStackedWidget()
        self.tool_stack.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #E2E8F0;")
        tool_view_layout.addWidget(self.tool_stack)
        self.main_stack.addWidget(self.tool_view)

    def register_all_tools(self):
        self.combo_switch.blockSignals(True)
        self.add_tool("Universal Converter", "Wandle Medienformate um.", "fa5s.exchange-alt", UniversalConverterTab())
        self.add_tool("Encryption Hub", "AES-256 Verschlüsselung", "fa5s.lock", EncryptionVaultTab())
        self.add_tool("System Health", "Temp-Daten & Optimierung", "fa5s.medkit", SystemHealthTab())
        self.add_tool("Archive Master", "Zip, Rar & 7z Archive.", "fa5s.file-archive", ArchiveMasterTab())
        self.add_tool("AI Assistant", "Dolphin3 KI Chat", "fa5s.robot", AIAssistantTab())
        self.add_tool("PDF & Web Docs", "PDF Split/Merge", "fa5s.file-pdf", PdfDocsTab())
        self.add_tool("Image Pro", "Bilder & Metadaten", "fa5s.image", ImageProTab())
        self.add_tool("Clipboard Log", "Clipboard Verlauf", "fa5s.clipboard-list", ClipboardHistoryTab())
        self.add_tool("Disk Heatmap", "Speicher Visualisierung", "fa5s.chart-pie", DiskHeatmapTab())
        self.add_tool("Folder Watcher", "Verzeichnisse überwachen", "fa5s.folder-open", FolderWatcherTab(self.watchdog_manager))
        self.combo_switch.blockSignals(False)
        # Connect Dashboard memory widget to the live AI tab
        ai_widget = self.tool_stack.widget(4)
        if hasattr(self, 'context_memory_widget') and ai_widget is not None:
            self.context_memory_widget.bind_ai_tab(ai_widget)

    def populate_tool_lists(self):
        for i in range(min(3, len(self.tools))):
            t = self.tools[i]
            tile = ToolTile(t['title'], t['desc'], t['icon'], i, self)
            self.main_tools_grid.addWidget(tile, 0, i)
        self.refresh_tool_list()

    def refresh_tool_list(self, filter_text=""):
        for i in reversed(range(self.tool_list_layout.count())): 
            w = self.tool_list_layout.itemAt(i).widget()
            if w: w.setParent(None); w.deleteLater()
            
        for i, t in enumerate(self.tools):
            if filter_text.lower() in t['title'].lower() or filter_text.lower() in t['desc'].lower():
                row = QPushButton(f"  {t['title']}")
                row.setIcon(qta.icon(t['icon'], color="#4A5568"))
                row.setIconSize(QSize(20, 20))
                row.setStyleSheet("""
                    QPushButton { 
                        text-align: left; padding: 12px; border: none; background: white; 
                        margin-bottom: 5px; border-radius: 8px; font-weight: 500;
                    }
                    QPushButton:hover { background: #EDF2F7; color: #3182CE; }
                """)
                row.clicked.connect(lambda chk, idx=i: self.go_to_tool(idx))
                self.tool_list_layout.addWidget(row)

    def filter_tools(self, text):
        self.refresh_tool_list(text)

    def quick_action_cleanup(self):
        from logic.system_health import JunkCleanerWorker
        self.qa_worker = JunkCleanerWorker()
        self.qa_worker.progress.connect(print)
        self.qa_worker.finished.connect(lambda c, b: QMessageBox.information(self, "Quick Action", f"Erfolg!\n{c} Dateien entfernt."))
        self.qa_worker.start()

    def go_home(self):
        self.main_stack.setCurrentIndex(0)

    def go_to_tool(self, index):
        print(f"Navigating to tool index: {index}")
        self.combo_switch.blockSignals(True)
        self.combo_switch.setCurrentIndex(index)
        self.combo_switch.blockSignals(False)
        self._switch_to_tool(index)

    def _switch_to_tool(self, index):
        self.tool_stack.setCurrentIndex(index)
        self.main_stack.setCurrentIndex(1)
        print(f"Switched main_stack to index 1, tool_stack to index {index}")

    def add_tool(self, title, desc, icon, widget):
        idx = self.tool_stack.addWidget(widget)
        self.combo_switch.addItem(qta.icon(icon, color="#3182CE"), title)
        self.tools.append({'title': title, 'desc': desc, 'icon': icon, 'widget': widget})
        print(f"Tool registered: {title} at tool_stack index {idx}")

    def on_combo_changed(self, index):
        if self.main_stack.currentIndex() == 1:
            self.tool_stack.setCurrentIndex(index)
        else:
            self.go_to_tool(index)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
        else: event.ignore()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if not urls: return
        file_paths = [u.toLocalFile() for u in urls if os.path.isfile(u.toLocalFile())]
        if not file_paths: return
        
        if self.main_stack.currentIndex() == 1:
            target = self.tool_stack.currentWidget()
            if hasattr(target, 'receive_global_drop'): target.receive_global_drop(file_paths)
            event.acceptProposedAction()
            return
            
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: white; border: 1px solid #B0C4DE; padding: 5px; }")
        act_ai = QAction(qta.icon('fa5s.robot', color="#3182CE"), "KI-Analyse (AI Assistant)", self)
        act_convert = QAction(qta.icon('fa5s.exchange-alt', color="#3182CE"), "Konvertieren (Universal)", self)
        menu.addAction(act_ai)
        menu.addAction(act_convert)
        
        action = menu.exec(QCursor.pos())
        if not action: return
        
        target_idx = 4 if action == act_ai else 0
        self.go_to_tool(target_idx)
        target = self.tool_stack.widget(target_idx)
        if hasattr(target, 'receive_global_drop'): target.receive_global_drop(file_paths)
        event.acceptProposedAction()

    def closeEvent(self, event):
        print("Omni-Hub closing. Cleaning up threads...")
        if hasattr(self, 'watchdog_manager'):
            self.watchdog_manager.stop_main()
        super().closeEvent(event)

    def show_launcher_edit_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background: white; border: 1px solid #D0D7DE; border-radius: 8px; padding: 5px; }")
        for i in range(3):
            act = QAction(f"Slot {i+1} neu belegen...", self)
            act.triggered.connect(lambda chk, idx=i: self.slots[idx].select_app())
            menu.addAction(act)
        menu.exec(QCursor.pos())
