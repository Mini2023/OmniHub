from PySide6.QtCore import Qt, QSize, Signal, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QColor, QCursor
from PySide6.QtWidgets import (QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, 
                                QLabel, QPushButton, QFrame, QDialog, QScrollArea,
                                QMessageBox, QGraphicsDropShadowEffect)

import qtawesome as qta
from logic.quick_actions import QuickActionRegistry, ActionWorker, load_active_actions, save_active_actions

class QuickActionTile(QFrame):
    clicked = Signal(object) # emits the action class

    def __init__(self, name, icon, action_class, parent=None):
        super().__init__(parent)
        self.name = name
        self.icon = icon
        self.action_class = action_class
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Style
        self.base_style = """
            QuickActionTile {
                background-color: rgba(255, 255, 255, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.8);
                border-radius: 15px;
            }
            QuickActionTile:hover {
                background-color: rgba(235, 248, 255, 0.9);
                border: 1px solid #3182CE;
            }
        """
        self.setStyleSheet(self.base_style)

        # Animation Setup
        self._anim = QPropertyAnimation(self, b"maximumSize")
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.OutQuad)

        # Flexible Height for Sidebar Harmony
        self.setMinimumHeight(60)

        layout = QVBoxLayout(self)

        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        self.icon_lbl = QLabel()
        self.icon_lbl.setPixmap(qta.icon(icon, color="#3182CE").pixmap(24, 24))
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        self.icon_lbl.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self.icon_lbl)


        self.name_lbl = QLabel(name)
        self.name_lbl.setStyleSheet("font-size: 9px; font-weight: 700; color: #4A5568; background: transparent; border: none;")
        self.name_lbl.setAlignment(Qt.AlignCenter)
        self.name_lbl.setWordWrap(True)
        layout.addWidget(self.name_lbl)

        # Shadow
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(15)
        self.shadow.setColor(QColor(0, 0, 0, 15))
        self.shadow.setOffset(0, 2)
        self.setGraphicsEffect(self.shadow)

        # Animation Setup for dezenten Scale-Effekt
        self._anim = QPropertyAnimation(self.shadow, b"blurRadius")
        self._anim.setDuration(200)

    def enterEvent(self, event):
        self.setStyleSheet("""
            QuickActionTile {
                background-color: rgba(235, 248, 255, 0.95);
                border: 1px solid #3182CE;
                border-radius: 15px;
            }
        """)
        self._anim.setStartValue(15)
        self._anim.setEndValue(25)
        self._anim.start()
        self.shadow.setColor(QColor(49, 130, 206, 50))
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet(self.base_style)
        self._anim.setStartValue(25)
        self._anim.setEndValue(15)
        self._anim.start()
        self.shadow.setColor(QColor(0, 0, 0, 15))
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.action_class)
        super().mousePressEvent(event)


class LibraryItem(QFrame):
    selected = Signal(str)

    def __init__(self, name, icon, desc, parent=None):
        super().__init__(parent)
        self.name = name
        self.setFixedHeight(60)
        self.setCursor(Qt.PointingHandCursor)
        
        self.setStyleSheet("""
            LibraryItem {
                background-color: rgba(247, 250, 252, 0.82);
                border: 1px solid #E2E8F0;
                border-radius: 12px;
                padding: 10px;
            }
            LibraryItem:hover {
                background-color: #EDF2F7;
                border: 1px solid #3182CE;
            }
        """)

        layout = QHBoxLayout(self)
        
        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon(icon, color="#3182CE").pixmap(24, 24))
        layout.addWidget(icon_lbl)
        
        vbox = QVBoxLayout()
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("font-weight: bold; color: #2D3748; background: transparent;")
        vbox.addWidget(name_lbl)
        
        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet("font-size: 10px; color: #718096; background: transparent;")
        vbox.addWidget(desc_lbl)
        layout.addLayout(vbox)
        layout.addStretch()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.selected.emit(self.name)

class QuickActionLibraryWindow(QDialog):
    action_selected = Signal(str) 

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quick Action Bibliothek")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(500, 600)
        self.setModal(True)
        
        # Outer container for shadowing and rounded corners on frameless
        self.container = QFrame(self)
        self.container.setObjectName("LibContainer")
        self.container.setStyleSheet("""
            #LibContainer {
                background-color: white;
                border: 1px solid #E2E8F0;
                border-radius: 20px;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.container)
        
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(25, 25, 25, 25)
        
        header_row = QHBoxLayout()
        header = QLabel("Quick Action Bibliothek")
        header.setStyleSheet("font-size: 20px; font-weight: 800; color: #1A202C; background: transparent;")
        header_row.addWidget(header)
        header_row.addStretch()
        
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(30, 30)
        btn_close.setStyleSheet("background: #FED7D7; color: #C53030; border-radius: 15px; font-weight: bold; border: none;")
        btn_close.clicked.connect(self.reject)
        header_row.addWidget(btn_close)
        layout.addLayout(header_row)
        
        sub = QLabel("Wähle eine Aktion für deinen Dashboard-Slot.")
        sub.setStyleSheet("font-size: 13px; color: #718096; margin-bottom: 20px; background: transparent;")
        layout.addWidget(sub)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        container_layout = QVBoxLayout(scroll_content)
        container_layout.setSpacing(10)
        
        registry = QuickActionRegistry()
        cats = registry.get_by_category()
        
        for category, actions in cats.items():
            cat_lbl = QLabel(category.upper())
            cat_lbl.setStyleSheet("font-weight: 800; color: #A0AEC0; font-size: 10px; margin-top: 15px; letter-spacing: 1.5px; background: transparent;")
            container_layout.addWidget(cat_lbl)
            
            for name, icon, desc, cls in actions:
                item = LibraryItem(name, icon, desc)
                item.selected.connect(self.on_item_selected)
                container_layout.addWidget(item)
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(0, 5)
        self.container.setGraphicsEffect(shadow)

    def on_item_selected(self, name):
        self.action_selected.emit(name)
        self.accept()

class QuickActionsModule(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.registry = QuickActionRegistry()
        self.active_action_names = load_active_actions()
        self.workers = []
        self.drop_hub = None
        self.init_ui()

    def set_drop_hub(self, hub):
        self.drop_hub = hub


    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(10)

        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background: transparent;")
        self.grid_layout = None
        
        self.update_quick_actions_grid()
        self.main_layout.addWidget(self.grid_container)


    def update_quick_actions_grid(self):
        # 1. Update-Vermeidung
        if hasattr(self, '_last_actions') and self._last_actions == self.active_action_names:
            return
        self._last_actions = list(self.active_action_names)

        # 2. Sicherer Layout-Reset
        if self.grid_container.layout() is not None:
            old_layout = self.grid_container.layout()
            while old_layout.count():
                item = old_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.setParent(None)
                    widget.deleteLater()
            
            # Lösche altes Layout-Objekt komplett (reparenting)
            QWidget().setLayout(old_layout)

        # 3. Grid-Initialisierung (Frisches QGridLayout)
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(8)

        # 4. Neue Widgets hinzufügen (2-Column Grid)
        for i in range(8):
            if i < len(self.active_action_names):
                name = self.active_action_names[i]
                action_class = self.registry.actions_map.get(name)
                if action_class:
                    dummy = action_class()
                    tile = QuickActionTile(name, dummy.icon, action_class)
                    tile.clicked.connect(self.run_action)
                else:
                    tile = self.create_empty_tile(i)
            else:
                tile = self.create_empty_tile(i)
            
            row, col = divmod(i, 2)
            self.grid_layout.addWidget(tile, row, col)
            
            # Stretch-Faktoren explizit setzen
            self.grid_layout.setColumnStretch(col, 1)
            self.grid_layout.setRowStretch(row, 1)

        # 5. UI-Refresh & Geometrie-Fix
        self.grid_container.update()
        self.grid_container.adjustSize()
        self.update()



    def create_empty_tile(self, index):
        tile = QFrame()
        tile.setStyleSheet("""
            QFrame {
                background-color: rgba(248, 250, 252, 0.4);
                border: 1px dashed #CBD5E0;
                border-radius: 15px;
            }
            QFrame:hover { background-color: rgba(237, 242, 247, 0.6); border: 1px solid #3182CE; }
        """)
        tile.setCursor(Qt.PointingHandCursor)
        l = QVBoxLayout(tile)
        lbl = QLabel("+")
        lbl.setStyleSheet("font-size: 20px; color: #A0AEC0; font-weight: bold; background: transparent;")
        lbl.setAlignment(Qt.AlignCenter)
        l.addWidget(lbl)
        tile.mousePressEvent = lambda e, idx=index: self.open_library(idx)
        
        # Consistent height for 8 tiles in a sidebar
        tile.setMinimumHeight(60)
        return tile



    def open_library(self, index):
        lib = QuickActionLibraryWindow(self)
        lib.action_selected.connect(lambda name: self.update_action(index, name))
        lib.exec()

    def update_action(self, index, name):
        if index < len(self.active_action_names):
            self.active_action_names[index] = name
        else:
            self.active_action_names.append(name)
        
        save_active_actions(self.active_action_names)
        self.update_quick_actions_grid()


    def remove_last_action(self):
        if self.active_action_names:
            self.active_action_names.pop()
            save_active_actions(self.active_action_names)
            self.update_quick_actions_grid()


    def run_action(self, action_class):
        files = []
        if self.drop_hub:
            files = self.drop_hub.files
            if files:
                # Visual Feedback: Glow the Hub
                self.drop_hub.setStyleSheet(self.drop_hub.base_style + "border-color: #3182CE; background-color: rgba(235, 248, 255, 0.95);")
                QTimer.singleShot(400, lambda: self.drop_hub.setStyleSheet(self.drop_hub.base_style))
        
        worker = ActionWorker(action_class, files=files)
        worker.finished.connect(self.on_action_finished)
        self.workers.append(worker)
        worker.start()


    def on_action_finished(self, success, message):
        from PySide6.QtWidgets import QMessageBox
        if success:
            QMessageBox.information(self, "Omni-Hub Action", f"Erfolg: {message}")
        else:
            QMessageBox.critical(self, "Omni-Hub Fehler", f"Fehler: {message}")
        
        # Cleanup workers
        self.workers = [w for w in self.workers if not w.isFinished()]

