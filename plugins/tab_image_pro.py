import os
import json
import time
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QFileDialog, QScrollArea, QTextEdit,
    QTabWidget, QGridLayout, QComboBox, QSlider, QLineEdit,
    QCheckBox, QSplitter, QStackedWidget
)
from PySide6.QtCore import Qt, QThread, Signal, QSize, Slot
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QColor, QPalette
import qtawesome as qta
from PIL import Image

from logic.image_pro import ImagePro
from logic.ai_engine import analyze_image

# ── Styles ──────────────────────────────────────────────────────────────────
GLASS_FRAME = """
    QFrame#Glass {
        background-color: rgba(255, 255, 255, 0.7);
        border: 1px solid rgba(226, 232, 240, 0.8);
        border-radius: 20px;
    }
"""

TOOL_TITLE = "font-size: 14px; font-weight: 800; color: #2D3748; background: transparent;"
SUB_TITLE = "font-size: 11px; color: #718096; background: transparent;"

BTN_PRIMARY = """
    QPushButton {
        background-color: #3182CE; color: white; border-radius: 12px;
        padding: 10px 15px; font-weight: 700; font-size: 12px;
    }
    QPushButton:hover { background-color: #2c6fad; }
"""

BTN_GHOST = """
    QPushButton {
        background-color: rgba(255, 255, 255, 0.5); color: #4A5568; 
        border: 1px solid #E2E8F0; border-radius: 10px; padding: 6px 12px;
    }
    QPushButton:hover { background-color: #EDF2F7; border-color: #3182CE; }
"""

# ── Worker Thread ────────────────────────────────────────────────────────────
class ImageWorker(QThread):
    finished = Signal(dict) # result info
    log = Signal(str)

    def __init__(self, action_data):
        super().__init__()
        self.action_data = action_data

    def run(self):
        files = self.action_data.get("files", [])
        action_type = self.action_data.get("action")
        params = self.action_data.get("params", {})
        
        results = []
        for i, f in enumerate(files):
            self.log.emit(f"Verarbeite: {os.path.basename(f)} ({i+1}/{len(files)})...")
            success = False
            msg = ""
            
            if action_type == "strip":
                success, msg = ImagePro.strip_metadata(f)
            elif action_type == "compress":
                success, msg = ImagePro.compress_image(f, quality=params.get("quality", 85))
            elif action_type == "resize":
                # Handle percentage scaling
                try:
                    img_tmp = Image.open(f)
                    w, h = img_tmp.size
                    scale = params.get("width_pct", 100) / 100.0
                    target_w = int(w * scale)
                    success, msg = ImagePro.resize_image(f, width=target_w, quality=params.get("quality", 90))
                except Exception as e:
                    success, msg = False, str(e)
            elif action_type == "convert":
                success, msg = ImagePro.convert_format(f, target_format=params.get("format", "PNG"))
            elif action_type == "palette":
                success, msg = ImagePro.get_color_palette(f)
                if success: msg = f"Farbpalette: {', '.join(msg)}"
            elif action_type == "crop":
                success, msg = ImagePro.smart_focus_crop(f, aspect_ratio=params.get("ratio", "1:1"))
            elif action_type == "remove_bg":
                success, msg = ImagePro.remove_background(f)
            elif action_type == "ai_fix":
                prompt = "Analysiere dieses Bild und gib Tipps zur Verbesserung (Kontrast, Helligkeit, Komposition)."
                msg = analyze_image(f, prompt, backend="gemini_flash")
                success = True
                self.log.emit(f"\n--- AI ANALYSE ---\n{msg}\n------------------\n")
            elif action_type == "ai_desc":
                prompt = "Beschreibe das Bild so exakt wie möglich für einen blinden Nutzer."
                msg = analyze_image(f, prompt, backend="gemini_flash")
                success = True
                self.log.emit(f"\n--- AI BESCHREIBUNG ---\n{msg}\n-----------------------\n")


            if success:
                self.log.emit(f"✓ Erfolg: {msg if isinstance(msg, str) else 'Aktion abgeschlossen'}")
                results.append(msg)
            else:
                self.log.emit(f"✗ Fehler: {msg}")

        self.finished.emit({"success": True, "results": results})

# ── Components ───────────────────────────────────────────────────────────────
class ImageDropZone(QFrame):
    files_dropped = Signal(list)

    def __init__(self):
        super().__init__()
        self.setObjectName("Glass")
        self.setStyleSheet(GLASS_FRAME)
        self.setAcceptDrops(True)
        self.setMinimumHeight(200)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        self.icon_lbl = QLabel()
        self.icon_lbl.setPixmap(qta.icon('fa5s.images', color="#3182CE").pixmap(64, 64))
        self.icon_lbl.setStyleSheet("background: transparent;")
        layout.addWidget(self.icon_lbl, alignment=Qt.AlignCenter)

        self.text_lbl = QLabel("Bilder hier ablegen")
        self.text_lbl.setStyleSheet(TOOL_TITLE)
        layout.addWidget(self.text_lbl, alignment=Qt.AlignCenter)

        self.sub_lbl = QLabel("JPG, PNG, WEBP")
        self.sub_lbl.setStyleSheet(SUB_TITLE)
        layout.addWidget(self.sub_lbl, alignment=Qt.AlignCenter)

        self.count_lbl = QLabel("0 Dateien ausgewählt")
        self.count_lbl.setStyleSheet("font-size: 10px; color: #A0AEC0; background: transparent;")
        layout.addWidget(self.count_lbl, alignment=Qt.AlignCenter)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.toLocalFile().lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        if paths: self.files_dropped.emit(paths)

# ── Main Tab ─────────────────────────────────────────────────────────────────
class ImageProTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_files = []
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20)

        # ── LEFT: File Management & Console ──
        left_panel = QVBoxLayout()
        left_panel.setSpacing(15)

        self.drop_zone = ImageDropZone()
        self.drop_zone.files_dropped.connect(self.add_files)
        left_panel.addWidget(self.drop_zone, 2)

        btn_row = QHBoxLayout()
        self.btn_add = QPushButton(" + Hinzufügen")
        self.btn_add.setStyleSheet(BTN_GHOST)
        self.btn_add.clicked.connect(self.browse_files)
        
        self.btn_clear = QPushButton(" ✕ Liste leeren")
        self.btn_clear.setStyleSheet(BTN_GHOST)
        self.btn_clear.clicked.connect(self.clear_list)
        
        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_clear)
        left_panel.addLayout(btn_row)

        console_box = QFrame()
        console_box.setObjectName("Glass")
        console_box.setStyleSheet(GLASS_FRAME)
        console_layout = QVBoxLayout(console_box)
        c_lbl = QLabel("Systemkonsole")
        c_lbl.setStyleSheet(SUB_TITLE + "font-weight: bold;")
        console_layout.addWidget(c_lbl)
        
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("background: transparent; border: none; font-family: Consolas; font-size: 11px; color: #4A5568;")
        console_layout.addWidget(self.console)
        left_panel.addWidget(console_box, 1)

        main_layout.addLayout(left_panel, 2)

        # ── CENTER: Action Center ──
        center_panel = QVBoxLayout()
        center_panel.setSpacing(15)

        action_box = QFrame()
        action_box.setObjectName("Glass")
        action_box.setStyleSheet(GLASS_FRAME)
        action_l = QVBoxLayout(action_box)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: none; background: transparent; }
            QTabBar::tab { 
                background: rgba(255,255,255,0.4); padding: 10px 20px; 
                border-radius: 8px; margin-right: 5px; color: #718096; font-weight: 700;
            }
            QTabBar::tab:selected { background: white; color: #3182CE; }
        """)

        # Tab 1: Classic
        classic_w = QWidget()
        classic_l = QVBoxLayout(classic_w)
        classic_l.setSpacing(12)
        
        self.cb_strip = QCheckBox("Metadaten entfernen (Strip)")
        self.cb_strip.setStyleSheet(SUB_TITLE + "font-size: 13px;")
        classic_l.addWidget(self.cb_strip)

        fmt_row = QHBoxLayout()
        fmt_row.addWidget(QLabel("Format Konverter:"))
        self.combo_format = QComboBox()
        self.combo_format.addItems(["Original", "PNG", "JPEG", "WEBP"])
        fmt_row.addWidget(self.combo_format)
        classic_l.addLayout(fmt_row)

        classic_l.addWidget(QLabel("Smart Resizer (Skalierung %):"))
        self.resize_slider = QSlider(Qt.Horizontal)
        self.resize_slider.setRange(10, 200)
        self.resize_slider.setValue(100)
        classic_l.addWidget(self.resize_slider)
        self.resize_val = QLabel("100%")
        self.resize_val.setAlignment(Qt.AlignCenter)
        self.resize_slider.valueChanged.connect(lambda v: self.resize_val.setText(f"{v}%"))
        classic_l.addWidget(self.resize_val)

        # Tab 2: AI Enhancer
        ai_w = QWidget()
        ai_l = QVBoxLayout(ai_w)
        ai_l.setSpacing(15)
        self.btn_ai_fix = QPushButton("✨ KI Auto-Fix (Gemini)")
        self.btn_ai_fix.setStyleSheet(BTN_PRIMARY)
        self.btn_ai_fix.clicked.connect(lambda: self.run_action("ai_fix"))
        
        self.btn_ai_desc = QPushButton("🔍 AI Image Describer")
        self.btn_ai_desc.setStyleSheet(BTN_PRIMARY.replace("#3182CE", "#805AD5"))
        self.btn_ai_desc.clicked.connect(lambda: self.run_action("ai_desc"))
        
        ai_l.addWidget(self.btn_ai_fix)
        ai_l.addWidget(self.btn_ai_desc)
        ai_l.addStretch()

        # Tab 3: Smart Tools
        smart_w = QWidget()
        smart_l = QVBoxLayout(smart_w)
        smart_l.setSpacing(15)
        
        self.btn_rembg = QPushButton("✂️ Background entfernen (rembg)")
        self.btn_rembg.setStyleSheet(BTN_PRIMARY.replace("#3182CE", "#E53E3E"))
        self.btn_rembg.clicked.connect(lambda: self.run_action("remove_bg"))
        smart_l.addWidget(self.btn_rembg)

        self.btn_palette = QPushButton("🎨 Farbpalette extrahieren")
        self.btn_palette.setStyleSheet(BTN_GHOST)
        self.btn_palette.clicked.connect(lambda: self.run_action("palette"))
        smart_l.addWidget(self.btn_palette)
        
        smart_l.addWidget(QLabel("Smart Focus Crop:"))
        self.combo_crop = QComboBox()
        self.combo_crop.addItems(["1:1 (Quadrat)", "16:9 (Kino)", "4:3 (Classic)"])
        smart_l.addWidget(self.combo_crop)
        self.btn_crop = QPushButton("🎯 Focus Crop anwenden")
        self.btn_crop.setStyleSheet(BTN_GHOST)
        self.btn_crop.clicked.connect(lambda: self.run_action("crop"))
        smart_l.addWidget(self.btn_crop)
        smart_l.addStretch()

        self.tabs.addTab(classic_w, "Classic")
        self.tabs.addTab(ai_w, "AI Enhancer")
        self.tabs.addTab(smart_w, "Smart Tools")
        
        action_l.addWidget(self.tabs)
        center_panel.addWidget(action_box)
        main_layout.addLayout(center_panel, 3)

        # ── RIGHT: Output & Control ──
        right_panel = QVBoxLayout()
        right_panel.setSpacing(15)

        preview_box = QFrame()
        preview_box.setObjectName("Glass")
        preview_box.setStyleSheet(GLASS_FRAME)
        preview_layout = QVBoxLayout(preview_box)
        self.preview_lbl = QLabel("Vorschau")
        self.preview_lbl.setAlignment(Qt.AlignCenter)
        self.preview_lbl.setStyleSheet("color: #CBD5E0; border: 2px dashed rgba(226, 232, 240, 0.5); border-radius: 10px;")
        self.preview_lbl.setMinimumSize(250, 250)
        preview_layout.addWidget(self.preview_lbl)
        right_panel.addWidget(preview_box)

        control_box = QVBoxLayout()
        self.btn_start = QPushButton("🚀 Aktion starten")
        self.btn_start.setFixedHeight(50)
        self.btn_start.setStyleSheet(BTN_PRIMARY)
        self.btn_start.clicked.connect(self.start_process)
        
        self.btn_folder = QPushButton("📂 Ausgabeordner öffnen")
        self.btn_folder.setStyleSheet(BTN_GHOST)
        self.btn_folder.clicked.connect(self.open_output_folder)
        
        control_box.addWidget(self.btn_start)
        control_box.addWidget(self.btn_folder)
        right_panel.addLayout(control_box)
        right_panel.addStretch()

        main_layout.addLayout(right_panel, 2)

    # ── Slots ──────────────────────────────────────────────────────────────────
    def log(self, text):
        ts = time.strftime("[%H:%M:%S]")
        self.console.append(f"{ts} {text}")
        # Scroll to bottom
        self.console.verticalScrollBar().setValue(self.console.verticalScrollBar().maximum())

    def add_files(self, paths):
        for p in paths:
            if p not in self.selected_files:
                self.selected_files.append(p)
        self.update_count()
        if self.selected_files:
            self.show_preview(self.selected_files[-1])
        self.log(f"{len(paths)} Dateien hinzugefügt.")

    def browse_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Bilder wählen", "", "Bilder (*.png *.jpg *.jpeg *.webp)")
        if paths: self.add_files(paths)

    def clear_list(self):
        self.selected_files = []
        self.update_count()
        self.preview_lbl.clear()
        self.preview_lbl.setText("Vorschau")
        self.log("Liste geleert.")

    def update_count(self):
        self.drop_zone.count_lbl.setText(f"{len(self.selected_files)} Dateien ausgewählt")

    def show_preview(self, path):
        pix = QPixmap(path)
        if not pix.isNull():
            scaled = pix.scaled(self.preview_lbl.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview_lbl.setPixmap(scaled)

    def run_action(self, action_type):
        """Unified runner for single-click actions (AI, Smart)"""
        if not self.selected_files:
            self.log("⚠ Keine Dateien ausgewählt!")
            return
        
        params = {}
        if action_type == "crop":
            params["ratio"] = self.combo_crop.currentText().split(" ")[0]
        
        self.execute_worker(action_type, params)

    def start_process(self):
        """Logic for Tab 0 (Classic)"""
        if self.tabs.currentIndex() != 0:
            self.log("Nutze die Buttons in den Tabs für AI/Smart Tools.")
            return
            
        if not self.selected_files:
            self.log("⚠ Keine Dateien ausgewählt!")
            return

        # Determine action from classic settings
        # This is simplified: we do multiple if checked?
        # For now, let's prioritize Convert > Resize > Compress
        if self.combo_format.currentText() != "Original":
            self.execute_worker("convert", {"format": self.combo_format.currentText()})
        elif self.cb_strip.isChecked():
            self.execute_worker("strip", {})
        else:
            scale = self.resize_slider.value()
            if scale != 100:
                self.execute_worker("resize", {"quality": 95, "width_pct": scale})
            else:
                self.execute_worker("compress", {"quality": 85})

    def execute_worker(self, action, params):
        self.log(f"Starte Aktion: {action}...")
        self.btn_start.setEnabled(False)
        self.worker = ImageWorker({"files": self.selected_files, "action": action, "params": params})
        self.worker.log.connect(self.log)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()

    def on_worker_finished(self, result):
        self.btn_start.setEnabled(True)
        self.log("Aktion abgeschlossen.")
        if result.get("results") and os.path.exists(result["results"][-1]):
             # If it's a list, it might be text for AI
             if isinstance(result["results"][-1], str) and os.path.isfile(result["results"][-1]):
                self.show_preview(result["results"][-1])

    def open_output_folder(self):
        if self.selected_files:
            os.startfile(os.path.dirname(self.selected_files[0]))
        else:
            os.startfile(os.getcwd())

    def receive_global_drop(self, files: list[str]):
        """Called by MainWindow with files from the Drop-Hub."""
        valid = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        if valid:
            self.add_files(valid)

