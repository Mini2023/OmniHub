import os
import json
import subprocess
from PySide6.QtCore import Qt, QSize, QFileInfo, QTimer, QEasingCurve, QPropertyAnimation, QPoint, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QColor, QCursor, QAction, QDesktopServices, QIcon
from PySide6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
                                QPushButton, QStackedWidget, QLabel, QFrame, 
                                QGridLayout, QComboBox, QProgressBar,
                                QMessageBox, QMenu, QLineEdit, QScrollArea, QListWidget, QListWidgetItem,
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
from ui_components.quick_actions_module import QuickActionsModule
from logic.quick_actions import ZipAllAction


class SystemHealthWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(160, 35)
        self.setCursor(Qt.PointingHandCursor)
        self.base_style = """
            SystemHealthWidget { 
                background-color: rgba(255, 255, 255, 0.8);
                border: 1px solid rgba(255, 255, 255, 1.0);
                border-radius: 15px;
            }
            SystemHealthWidget:hover { border: 1px solid #3182CE; background-color: white; }
        """
        self.setStyleSheet(self.base_style)

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
        self.base_style = """
            WatchdogWidget {
                background-color: rgba(255, 255, 255, 0.8);
                border: 1px solid rgba(255, 255, 255, 1.0);
                border-radius: 15px;
            }
            WatchdogWidget:hover { border: 1px solid #3182CE; background-color: white; }
        """
        self.setStyleSheet(self.base_style)

        
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
        self.base_style = """
            ContextMemoryWidget {
                background-color: rgba(255, 255, 255, 0.8);
                border: 1px solid rgba(255, 255, 255, 1.0);
                border-radius: 15px;
            }
            ContextMemoryWidget:hover { border: 1px solid #3182CE; background-color: white; }
        """
        self.setStyleSheet(self.base_style)

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
        self.setFixedSize(60, 60)

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
            info = QFileInfo(self.app_path)
            icon = QFileIconProvider().icon(info)
            self.setIcon(icon)
            self.setIconSize(QSize(36, 36))

            self.setToolTip(f"Start: {self.app_name}")
            self.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.8);
                    border: 1px solid rgba(255, 255, 255, 1.0);
                    border-radius: 15px;
                }
                QPushButton:hover { background-color: white; border: 1px solid #3182CE; }
            """)
        else:
            self.setText("")
            self.setIcon(qta.icon('fa5s.plus', color="#A0AEC0"))
            self.setIconSize(QSize(20, 20))
            self.setStyleSheet("""
                QPushButton {
                    background-color: rgba(248, 250, 252, 0.5);
                    border: 1px dashed #CBD5E0;
                    border-radius: 15px;
                }
                QPushButton:hover { background-color: rgba(235, 248, 255, 0.8); border: 1px solid #3182CE; }
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
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.base_style = """
            ToolTile {
                background-color: rgba(255, 255, 255, 0.75);
                border: 1px solid rgba(255, 255, 255, 0.9);
                border-radius: 20px;
            }
        """
        self.setStyleSheet(self.base_style)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(6)
        
        self.icon_lbl = QLabel()
        self.icon_lbl.setPixmap(qta.icon(icon_name, color="#3182CE").pixmap(36, 36))
        self.icon_lbl.setAlignment(Qt.AlignLeft)
        self.icon_lbl.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self.icon_lbl)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 800; color: #2D3748; background: transparent;")
        layout.addWidget(title_lbl)
        
        desc_lbl = QLabel(description)
        desc_lbl.setStyleSheet("font-size: 11px; color: #718096; background: transparent;")
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)
        
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(20)
        self.shadow.setOffset(0, 4)
        self.shadow.setColor(QColor(0, 0, 0, 0))
        self.setGraphicsEffect(self.shadow)

        self._anim = QPropertyAnimation(self.shadow, b"blurRadius")
        self._anim.setDuration(200)

    def enterEvent(self, event):
        self.setStyleSheet("ToolTile { background-color: white; border: 1px solid #3182CE; border-radius: 20px; }")
        self._anim.setStartValue(20)
        self._anim.setEndValue(35)
        self._anim.start()
        self.shadow.setColor(QColor(49, 130, 206, 40))
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet(self.base_style)
        self._anim.setStartValue(35)
        self._anim.setEndValue(20)
        self._anim.start()
        self.shadow.setColor(QColor(0, 0, 0, 0))
        super().leaveEvent(event)


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.window().go_to_tool(self.index)


class SlideOutMenu(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SlideOut")
        self.setStyleSheet("""
            QFrame#SlideOut {
                background-color: rgba(255, 255, 255, 0.9);
                border-left: 1px solid #3182CE;
                border-radius: 0px 20px 20px 0px;
            }
        """)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 15, 10, 15)
        self.layout.setSpacing(10)

        title = QLabel("Hub Actions")
        title.setStyleSheet("font-weight: 800; color: #3182CE; font-size: 10px; text-transform: uppercase;")
        self.layout.addWidget(title)

        self.btn_zip = self.create_btn("📦 Alle zippen", "fa5s.file-archive")
        self.btn_pdf = self.create_btn("📄 In PDF (AI)", "fa5s.file-pdf")
        self.btn_ai = self.create_btn("🤖 An AI senden", "fa5s.robot")
        self.btn_image = self.create_btn("🖼 In Image Pro", "fa5s.image")

    def create_btn(self, text, icon):
        btn = QPushButton(text)
        btn.setIcon(qta.icon(icon, color="#4A5568"))
        btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none; color: #4A5568; 
                text-align: left; padding: 5px; font-size: 11px; font-weight: 600;
            }
            QPushButton:hover { background: rgba(49, 130, 206, 0.1); color: #3182CE; border-radius: 5px; }
        """)
        btn.setCursor(Qt.PointingHandCursor)
        self.layout.addWidget(btn)
        return btn

class GlobalDropZone(QFrame):
    files_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.files = []
        self.base_style = """
            GlobalDropZone {
                background-color: rgba(255, 255, 255, 0.7);
                border: 2px dashed rgba(49, 130, 206, 0.3);
                border-radius: 20px;
            }
        """
        self.setStyleSheet(self.base_style)
        
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Content Area
        self.content = QWidget()
        content_l = QVBoxLayout(self.content)
        content_l.setContentsMargins(20, 10, 20, 10)
        content_l.setSpacing(5)

        header = QHBoxLayout()
        header.setSpacing(10)
        self.icon_lbl = QLabel()
        self.icon_lbl.setPixmap(qta.icon('fa5s.cloud-upload-alt', color="#3182CE").pixmap(32, 32))
        self.icon_lbl.setStyleSheet("background: transparent;")
        header.addWidget(self.icon_lbl)
        
        vbox = QVBoxLayout()
        vbox.setSpacing(0)
        lbl = QLabel("Global Drop-Hub")
        lbl.setStyleSheet("font-size: 15px; font-weight: 800; color: #2D3748; background: transparent;")
        vbox.addWidget(lbl)
        self.sub_lbl = QLabel("Persistenter Kontext")
        self.sub_lbl.setStyleSheet("font-size: 10px; color: #A0AEC0; background: transparent;")
        vbox.addWidget(self.sub_lbl)
        header.addLayout(vbox)

        header.addStretch()

        self.btn_clear = QPushButton()
        self.btn_clear.setIcon(qta.icon('fa5s.times', color="#CBD5E0"))
        self.btn_clear.setFixedSize(24, 24)
        self.btn_clear.setStyleSheet("border: none; background: transparent;")
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.clicked.connect(self.clear_hub)
        self.btn_clear.setVisible(False)
        header.addWidget(self.btn_clear)
        content_l.addLayout(header)

        # List of files
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background: transparent; border: none; font-size: 11px; color: #4A5568;
            }
            QListWidget::item { padding: 4px; border-bottom: 1px solid rgba(226, 232, 240, 0.5); }
        """)
        self.list_widget.verticalScrollBar().setFixedWidth(4)
        content_l.addWidget(self.list_widget)
        self.main_layout.addWidget(self.content, 1)

        # Slide-out Logic
        self.menu = SlideOutMenu(self)
        self.menu.setFixedWidth(130)
        self.menu.move(self.width(), 0)
        self.menu_visible = False
        
        self.handle = QPushButton(self)
        self.handle.setFixedSize(20, 40)
        self.handle.setIcon(qta.icon('fa5s.chevron-left', color="#3182CE"))
        self.handle.setStyleSheet("""
            QPushButton { 
                background: white; border: 1px solid #E2E8F0; 
                border-radius: 10px 0px 0px 10px; border-right: none;
            }
        """)
        self.handle.setCursor(Qt.PointingHandCursor)
        self.handle.clicked.connect(self.toggle_menu)
        self.handle.setVisible(False)

        self.setMinimumHeight(130)
        self.setFixedHeight(160)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(20)
        self.shadow.setColor(QColor(0,0,0,0))
        self.setGraphicsEffect(self.shadow)
        
        self._anim = QPropertyAnimation(self.shadow, b"blurRadius")
        self._anim.setDuration(300)

        # Menu Animation
        self.menu_anim = QPropertyAnimation(self.menu, b"pos")
        self.menu_anim.setDuration(300)
        self.menu_anim.setEasingCurve(QEasingCurve.OutQuint)

    def resizeEvent(self, event):
        if not self.menu_visible:
            self.menu.move(self.width(), 0)
        else:
            self.menu.move(self.width() - 130, 0)
        self.menu.setFixedHeight(self.height())
        self.handle.move(self.width() - (20 if not self.menu_visible else 150), self.height()//2 - 20)
        super().resizeEvent(event)

    def toggle_menu(self):
        self.menu_visible = not self.menu_visible
        start = self.menu.pos()
        end_x = self.width() - 130 if self.menu_visible else self.width()
        self.menu_anim.setStartValue(start)
        self.menu_anim.setEndValue(QPoint(end_x, 0))
        self.menu_anim.start()
        
        icon = 'fa5s.chevron-right' if self.menu_visible else 'fa5s.chevron-left'
        self.handle.setIcon(qta.icon(icon, color="#3182CE"))
        
        # Handle Move
        handle_x = self.width() - (150 if self.menu_visible else 20)
        self.handle.move(handle_x, self.height()//2 - 20)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [u.toLocalFile() for u in event.mimeData().urls()]
        self.add_files(paths)
        event.acceptProposedAction()
        # Visual feedback
        self.setStyleSheet(self.base_style + "border-color: #48BB78; background-color: rgba(240, 255, 244, 0.8);")
        QTimer.singleShot(500, lambda: self.setStyleSheet(self.base_style))

    def add_files(self, paths):
        from PySide6.QtWidgets import QListWidgetItem
        for p in paths:
            if p not in self.files:
                self.files.append(p)
                item = QListWidgetItem(f"📄 {os.path.basename(p)}")
                item.setToolTip(p)
                self.list_widget.addItem(item)
        
        count = len(self.files)
        has_files = count > 0
        self.handle.setVisible(has_files)
        self.btn_clear.setVisible(has_files)
        self.sub_lbl.setText(f"Geladene Dateien: {count}")
        self.files_changed.emit(count)

    def clear_hub(self):
        self.files = []
        self.list_widget.clear()
        self.handle.setVisible(False)
        self.btn_clear.setVisible(False)
        self.sub_lbl.setText("Persistenter Kontext")
        if self.menu_visible: self.toggle_menu()
        self.files_changed.emit(0)


    def enterEvent(self, event):
        self.setStyleSheet("""
            GlobalDropZone {
                background-color: rgba(235, 248, 255, 0.85);
                border: 2px dashed #3182CE;
                border-radius: 20px;
            }
        """)
        self._anim.setStartValue(20)
        self._anim.setEndValue(35)
        self._anim.start()
        self.shadow.setColor(QColor(49, 130, 206, 30))
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet(self.base_style)
        self._anim.setStartValue(35)
        self._anim.setEndValue(20)
        self._anim.start()
        self.shadow.setColor(QColor(0,0,0,0))
        super().leaveEvent(event)



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        print("MainWindow initializing...")
        self.setWindowTitle("Omni-Hub v4.5.1")
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
                background-color: rgba(255, 255, 255, 0.7); 
                border: 1px solid rgba(255, 255, 255, 0.9); 
                border-radius: 20px; 
            }
        """)
        self.dashboard_widget.setObjectName("Dashboard")
        dash_layout = QVBoxLayout(self.dashboard_widget)
        dash_layout.setContentsMargins(40, 30, 40, 40)
        dash_layout.setSpacing(25)
        
        # --- Header (Top Bar) ---
        header = QHBoxLayout()
        header.setSpacing(15)


        
        # Left: Version & Changelog
        header_left = QHBoxLayout()
        header_left.setSpacing(10)
        
        # Consistent Style for Header Items (Explicit Selectors to avoid parsing errors)
        header_item_base = """
            background: rgba(255,255,255,0.8); border: 1px solid #E2E8F0; 
            border-radius: 12px; padding: 6px 12px; font-size: 11px; color: #4A5568; font-weight: 700;
        """
        
        self.ver_lbl = QLabel("ver. 4.5.1")
        self.ver_lbl.setStyleSheet(f"QLabel {{ {header_item_base} color: #A0AEC0; }}")
        header_left.addWidget(self.ver_lbl)
        
        self.btn_changelog = QPushButton("Changelog")
        self.btn_changelog.setCursor(Qt.PointingHandCursor)
        self.btn_changelog.setStyleSheet(f"QPushButton {{ {header_item_base} }} QPushButton:hover {{ background: #EDF2F7; }}")
        self.btn_changelog.clicked.connect(lambda: os.startfile("changelog.txt") if os.path.exists("changelog.txt") else None)
        header_left.addWidget(self.btn_changelog)
        header.addLayout(header_left)
        
        header.addStretch()
        
        # Center: Title
        title = QLabel("Omni-Hub Dashboard")
        title.setStyleSheet("font-size: 28px; font-weight: 900; color: #1A202C; letter-spacing: -0.5px; background: transparent;")
        header.addWidget(title)
        
        header.addStretch()
        
        # Right: Web & GitHub
        header_right = QHBoxLayout()
        header_right.setSpacing(10)
        
        btn_style_blue = f"QPushButton {{ {header_item_base} color: #3182CE; }} QPushButton:hover {{ background: #EBF8FF; border-color: #BEE3F8; }}"
        
        btn_web = QPushButton("Webpage")
        btn_web.setIcon(qta.icon('fa5s.globe', color="#3182CE"))
        btn_web.setStyleSheet(btn_style_blue)
        btn_web.setCursor(Qt.PointingHandCursor)
        btn_web.clicked.connect(lambda: QDesktopServices.openUrl("https://www.google.com/search?q=google.com"))
        
        btn_git = QPushButton("GitHub")
        btn_git.setIcon(qta.icon('fa5b.github', color="#2D3748"))
        btn_git.setStyleSheet(btn_style_blue)
        btn_git.setCursor(Qt.PointingHandCursor)
        btn_git.clicked.connect(lambda: QDesktopServices.openUrl("https://github.com/Mini2023/OmniHub"))


        
        header_right.addWidget(btn_web)
        header_right.addWidget(btn_git)
        header.addLayout(header_right)

        
        dash_layout.addLayout(header)
        
        # Separator Line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("border: none; background: #E2E8F0; height: 1px;")
        dash_layout.addWidget(line)
        
        # --- Live Widgets ---
        status_bar = QHBoxLayout()
        status_bar.setContentsMargins(0, 0, 0, 0)
        status_bar.setSpacing(15)
        
        self.watchdog_widget = WatchdogWidget(self.watchdog_manager)
        status_bar.addWidget(self.watchdog_widget)
        
        self.health_widget = SystemHealthWidget()
        status_bar.addWidget(self.health_widget)

        self.context_memory_widget = ContextMemoryWidget()
        status_bar.addWidget(self.context_memory_widget)
        
        status_bar.addStretch()
        dash_layout.addLayout(status_bar)
        
        # --- Main Content Area (2 Columns) ---
        main_content_hbox = QHBoxLayout()
        main_content_hbox.setSpacing(25)
        
        # LEFT COLUMN: Top Row (Drop/Launcher) + Bottom Section (Tools)
        left_column = QVBoxLayout()
        left_column.setSpacing(25)
        
        # 1. Top Row: Global Drop-Hub & App Launcher
        top_row = QHBoxLayout()
        top_row.setSpacing(20)
        
        # Global Drop-Hub (persistent)
        self.drop_hub = GlobalDropZone()
        self.drop_hub.setMinimumWidth(380)
        top_row.addWidget(self.drop_hub, 4)
        
        # Connect Hub signals
        self.drop_hub.files_changed.connect(lambda c: self.context_memory_widget.update_health(c)) # Re-using for status
        
        # Connect SlideOut Menu Actions
        self.drop_hub.menu.btn_zip.clicked.connect(lambda: self.qa_module.run_action(ZipAllAction))
        self.drop_hub.menu.btn_ai.clicked.connect(lambda: self.send_hub_to_tool(4))   # AI Assistant
        self.drop_hub.menu.btn_image.clicked.connect(lambda: self.send_hub_to_tool(6)) # Image Pro
        self.drop_hub.menu.btn_pdf.clicked.connect(lambda: self.send_hub_to_tool(5))   # PDF Docs



        
        # App Launcher (compressed)
        launcher_vbox = QVBoxLayout()
        launcher_vbox.setSpacing(8)
        launcher_header = QHBoxLayout()
        l_title = QLabel("Launcher")
        l_title.setStyleSheet("font-weight: 800; color: #4A5568; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;")
        launcher_header.addWidget(l_title)
        launcher_header.addStretch()
        
        btn_edit_l = QPushButton()
        btn_edit_l.setIcon(qta.icon('fa5s.cog', color="#A0AEC0"))
        btn_edit_l.setFixedSize(22, 22)
        btn_edit_l.setCursor(Qt.PointingHandCursor)
        btn_edit_l.setStyleSheet("border: none; background: transparent;")
        btn_edit_l.clicked.connect(self.show_launcher_edit_menu)
        launcher_header.addWidget(btn_edit_l)
        launcher_vbox.addLayout(launcher_header)

        launcher_box = QFrame()
        launcher_box.setObjectName("LauncherBox")
        launcher_box.setMaximumHeight(120)
        launcher_l = QVBoxLayout(launcher_box)
        launcher_l.setContentsMargins(10, 10, 10, 10)
        slots_l = QHBoxLayout()
        slots_l.setSpacing(12)
        self.slots = [LauncherSlot(0), LauncherSlot(1), LauncherSlot(2)]
        for s in self.slots: slots_l.addWidget(s)
        launcher_l.addLayout(slots_l)
        launcher_vbox.addWidget(launcher_box)
        top_row.addLayout(launcher_vbox, 3)
        
        left_column.addLayout(top_row)
        
        # 2. Bottom Section: Favorite Tools & Search/List
        tools_vbox = QVBoxLayout()
        tools_vbox.setSpacing(15)
        
        mt_header = QHBoxLayout()
        main_tools_lbl = QLabel("Fav Tools")
        main_tools_lbl.setStyleSheet("font-weight: 800; color: #4A5568; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;")
        mt_header.addWidget(main_tools_lbl)
        mt_header.addStretch()
        
        self.btn_edit_favs = QPushButton()
        self.btn_edit_favs.setIcon(qta.icon('fa5s.star', color="#A0AEC0"))
        self.btn_edit_favs.setFixedSize(22, 22)
        self.btn_edit_favs.setCursor(Qt.PointingHandCursor)
        self.btn_edit_favs.setStyleSheet("border: none; background: transparent;")
        self.btn_edit_favs.clicked.connect(self.show_favorites_menu)
        mt_header.addWidget(self.btn_edit_favs)
        tools_vbox.addLayout(mt_header)
        
        self.main_tools_grid = QGridLayout()
        self.main_tools_grid.setSpacing(15)
        self.main_tools_grid.setContentsMargins(15, 12, 15, 12)
        
        main_tools_box = QFrame()
        main_tools_box.setObjectName("ToolBox")
        main_tools_box.setLayout(self.main_tools_grid)
        tools_vbox.addWidget(main_tools_box)
        
        search_vbox = QVBoxLayout()
        search_vbox.setSpacing(10)
        search_vbox.setContentsMargins(0, 0, 0, 0)
        
        self.tool_search = QLineEdit()
        self.tool_search.setPlaceholderText("🔍 Tools...")
        self.tool_search.setStyleSheet("""
            QLineEdit { 
                padding: 10px 15px; border-radius: 12px; border: 1px solid #E2E8F0; 
                background: rgba(255,255,255,0.8); font-size: 13px; color: #2D3748;
            }
            QLineEdit:focus { border: 1px solid #3182CE; background: white; }
        """)
        self.tool_search.textChanged.connect(self.filter_tools)
        search_vbox.addWidget(self.tool_search)
        
        self.all_tools_scroll = QScrollArea()
        self.all_tools_scroll.setWidgetResizable(True)
        self.all_tools_scroll.setStyleSheet("border: none; background: transparent;")
        self.tool_list_widget = QWidget()
        self.tool_list_layout = QVBoxLayout(self.tool_list_widget)
        self.tool_list_layout.setAlignment(Qt.AlignTop)
        self.tool_list_layout.setContentsMargins(0, 0, 0, 0)
        self.tool_list_layout.setSpacing(8)
        self.all_tools_scroll.setWidget(self.tool_list_widget)
        search_vbox.addWidget(self.all_tools_scroll)
        tools_vbox.addLayout(search_vbox)
        
        left_column.addLayout(tools_vbox)
        main_content_hbox.addLayout(left_column, 7)
        
        # RIGHT COLUMN: Quick Actions Sidebar
        qa_vbox = QVBoxLayout()
        qa_vbox.setSpacing(10)
        
        qa_header = QHBoxLayout()
        qa_title = QLabel("Actions")
        qa_title.setStyleSheet("font-weight: 800; color: #4A5568; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;")
        qa_header.addWidget(qa_title)
        qa_header.addStretch()
        
        btn_style_qa = "border: none; background: transparent;"
        self.btn_add_qa = QPushButton()
        self.btn_add_qa.setIcon(qta.icon('fa5s.plus', color="#3182CE"))
        self.btn_add_qa.setFixedSize(22, 22)
        self.btn_add_qa.setStyleSheet(btn_style_qa)
        self.btn_add_qa.setCursor(Qt.PointingHandCursor)
        
        self.btn_rem_qa = QPushButton()
        self.btn_rem_qa.setIcon(qta.icon('fa5s.minus', color="#E53E3E"))
        self.btn_rem_qa.setFixedSize(22, 22)
        self.btn_rem_qa.setStyleSheet(btn_style_qa)
        self.btn_rem_qa.setCursor(Qt.PointingHandCursor)
        
        qa_header.addWidget(self.btn_add_qa)
        qa_header.addWidget(self.btn_rem_qa)
        qa_vbox.addLayout(qa_header)
        
        self.qa_module = QuickActionsModule()
        self.qa_module.setObjectName("QuickActionBox")
        self.qa_module.set_drop_hub(self.drop_hub) # Link to Global Context

        # Full-height style with more distinct separation
        self.qa_module.setStyleSheet("""
            #QuickActionBox {
                background-color: rgba(255, 255, 255, 0.45);
                border-left: 2px solid rgba(49, 130, 206, 0.2);
                border-radius: 20px;
            }
        """)
        self.btn_add_qa.clicked.connect(lambda: self.qa_module.open_library(len(self.qa_module.active_action_names)))
        self.btn_rem_qa.clicked.connect(self.qa_module.remove_last_action)
        qa_vbox.addWidget(self.qa_module, 1) # ADD STRETCH
        
        main_content_hbox.addLayout(qa_vbox, 2)

        dash_layout.addLayout(main_content_hbox)
        
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
        # Load favorites from config or default to first 4
        favs = [0, 1, 2, 4] # Defaults
        fav_config = "tool_favorites.json"
        if os.path.exists(fav_config):
            try:
                with open(fav_config, 'r') as f:
                    favs = json.load(f)
            except: pass
        
        # Clear existing favorites grid
        for i in reversed(range(self.main_tools_grid.count())):
            self.main_tools_grid.itemAt(i).widget().setParent(None)

        for i, tool_idx in enumerate(favs[:4]):
            if tool_idx < len(self.tools):
                t = self.tools[tool_idx]
                tile = ToolTile(t['title'], t['desc'], t['icon'], tool_idx, self)
                self.main_tools_grid.addWidget(tile, 0, i)
        self.refresh_tool_list()

    def show_favorites_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background: white; border: 1px solid #E2E8F0; border-radius: 12px; padding: 5px; }")
        
        fav_config = "tool_favorites.json"
        
        for i, t in enumerate(self.tools):
            act = QAction(f"★ {t['title']}", self)
            act.triggered.connect(lambda chk, idx=i: self.toggle_favorite(idx))
            menu.addAction(act)
        menu.exec(QCursor.pos())

    def toggle_favorite(self, idx):
        fav_config = "tool_favorites.json"
        favs = [0, 1, 2, 4]
        if os.path.exists(fav_config):
            try:
                with open(fav_config, 'r') as f:
                    favs = json.load(f)
            except: pass
        
        if idx in favs:
            favs.remove(idx)
        else:
            if len(favs) >= 4:
                favs.pop(0)
            favs.append(idx)
        
        with open(fav_config, 'w') as f:
            json.dump(favs, f)
        
        self.populate_tool_lists()


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
        self.main_stack.setCurrentIndex(1)
        self.tool_stack.setCurrentIndex(index)

    def send_hub_to_tool(self, index):
        if not self.drop_hub.files:
            QMessageBox.information(self, "Omni-Hub Hub", "Der Hub ist leer. Bitte Dateien hinzufügen.")
            return
        self.go_to_tool(index)
        target = self.tool_stack.widget(index)
        if hasattr(target, 'receive_global_drop'):
            target.receive_global_drop(self.drop_hub.files)

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
