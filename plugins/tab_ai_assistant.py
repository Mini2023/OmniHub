"""
Omni-Hub – AI Assistant Tab v4.1 (Hybrid Engine)
==================================================
3-Column Layout:
  LEFT   – Multi-file Drop Zone + Quick Actions
  CENTER – Chat Window + Prompt Input + Template Dropdown
  RIGHT  – Preview / Result Panel + Save/Delete + Context Memory Tracker
"""

from __future__ import annotations
import os
import json

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QListWidget, QListWidgetItem, QComboBox,
    QLineEdit, QSizePolicy, QFrame, QProgressBar,
    QFileDialog, QSplitter, QScrollArea, QAbstractItemView,
    QMessageBox,
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QMimeData
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent, QFont

try:
    import qtawesome as qta
    _HAS_QTA = True
except ImportError:
    _HAS_QTA = False

# ── Style helpers ─────────────────────────────────────────────────────────────

_PANEL_STYLE = """
    QFrame#Panel {{
        background-color: #FFFFFF;
        border: 1px solid #D0D7DE;
        border-radius: 14px;
    }}
    QFrame#Panel:hover {{
        border: 1px solid #5a9fd4;
    }}
"""

_HEADER_LABEL = "font-size:13px; font-weight:700; color:#2D3748; background:transparent; border:none;"
_SMALL_LABEL  = "font-size:11px; color:#718096; background:transparent; border:none;"

_BTN_PRIMARY = """
    QPushButton {
        background-color: #3182CE; color: white; border: none;
        border-radius: 10px; padding: 8px 14px; font-weight: 700; font-size: 12px;
    }
    QPushButton:hover { background-color: #2c6fad; }
    QPushButton:pressed { background-color: #245a8f; }
    QPushButton:disabled { background-color: #ccc; color: #999; }
"""

_BTN_SECONDARY = """
    QPushButton {
        background-color: #EDF2F7; color: #2D3748; border: 1px solid #CBD5E0;
        border-radius: 10px; padding: 8px 14px; font-weight: 600; font-size: 12px;
    }
    QPushButton:hover { background-color: #E2E8F0; border-color: #3182CE; color:#3182CE; }
    QPushButton:pressed { background-color: #CBD5E0; }
    QPushButton:disabled { background-color: #f0f0f0; color:#bbb; }
"""

_BTN_DANGER = """
    QPushButton {
        background-color: #FED7D7; color: #C53030; border: 1px solid #FC8181;
        border-radius: 10px; padding: 8px 14px; font-weight: 600; font-size: 12px;
    }
    QPushButton:hover { background-color: #FEB2B2; border-color: #E53E3E; }
"""

_BTN_SUCCESS = """
    QPushButton {
        background-color: #C6F6D5; color: #276749; border: 1px solid #9AE6B4;
        border-radius: 10px; padding: 8px 14px; font-weight: 600; font-size: 12px;
    }
    QPushButton:hover { background-color: #9AE6B4; border-color: #48BB78; }
"""

# ── QThread Workers ───────────────────────────────────────────────────────────

class AIWorker(QThread):
    """Generic AI worker – runs any callable in a background thread."""
    response_ready = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, func, *args):
        super().__init__()
        self._func = func
        self._args = args

    def run(self):
        try:
            result = self._func(*self._args)
            if result and result.startswith("[") and "Error" in result:
                self.error_occurred.emit(result)
            else:
                self.response_ready.emit(result or "(Leere Antwort)")
        except Exception as e:
            self.error_occurred.emit(f"Thread-Fehler: {e}")


# ── Sub-Widgets ───────────────────────────────────────────────────────────────

class DropZoneList(QFrame):
    """
    A styled file list that accepts drag-and-drop.
    Emits files_dropped(list[str]) when files are added.
    """
    files_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Panel")
        self.setStyleSheet(_PANEL_STYLE.format())
        self.setAcceptDrops(True)
        self.setMinimumHeight(160)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # Header row
        h = QHBoxLayout()
        icon_lbl = QLabel("📂")
        icon_lbl.setStyleSheet("font-size:18px; background:transparent; border:none;")
        h.addWidget(icon_lbl)
        title = QLabel("Drop Zone (PDF, TXT, DOCX)")
        title.setStyleSheet(_HEADER_LABEL)
        h.addWidget(title)
        h.addStretch()

        btn_add = QPushButton("+ Datei")
        btn_add.setStyleSheet(_BTN_SECONDARY)
        btn_add.setFixedHeight(28)
        btn_add.clicked.connect(self._browse_files)
        h.addWidget(btn_add)

        btn_clr = QPushButton("✕ Alle")
        btn_clr.setStyleSheet(_BTN_DANGER)
        btn_clr.setFixedHeight(28)
        btn_clr.clicked.connect(self.clear_all)
        h.addWidget(btn_clr)
        layout.addLayout(h)

        # Placeholder label
        self._placeholder = QLabel("Dateien hier ablegen oder '+ Datei' klicken\n(PDF · TXT · DOCX · MD)")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setStyleSheet(
            "color:#A0AEC0; font-size:12px; background:transparent; border:none;"
        )

        # List widget
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_widget.setStyleSheet("""
            QListWidget {
                background: #F8FAFF; border: none; border-radius: 8px;
                font-size: 12px; color: #2D3748;
            }
            QListWidget::item { padding: 6px 10px; border-radius: 6px; }
            QListWidget::item:selected { background: #BEE3F8; color: #1A365D; }
            QListWidget::item:hover { background: #EBF8FF; }
        """)

        layout.addWidget(self._placeholder)
        layout.addWidget(self.list_widget)
        self.list_widget.setVisible(False)

    def _refresh_visibility(self):
        has_items = self.list_widget.count() > 0
        self._placeholder.setVisible(not has_items)
        self.list_widget.setVisible(has_items)

    def add_files(self, paths: list[str]):
        for p in paths:
            if self._check(p) and not self._already_added(p):
                item = QListWidgetItem(f"  {os.path.basename(p)}")
                item.setData(Qt.UserRole, p)
                item.setToolTip(p)
                self.list_widget.addItem(item)
        self._refresh_visibility()
        if paths:
            self.files_dropped.emit(self.get_all_paths())

    def _check(self, path: str) -> bool:
        exts = {".pdf", ".txt", ".docx", ".md", ".csv", ".html", ".py", ".json"}
        return os.path.isfile(path) and os.path.splitext(path)[1].lower() in exts

    def _already_added(self, path: str) -> bool:
        for i in range(self.list_widget.count()):
            if self.list_widget.item(i).data(Qt.UserRole) == path:
                return True
        return False

    def clear_all(self):
        self.list_widget.clear()
        self._refresh_visibility()

    def get_selected_paths(self) -> list[str]:
        return [
            item.data(Qt.UserRole)
            for item in self.list_widget.selectedItems()
        ]

    def get_all_paths(self) -> list[str]:
        return [
            self.list_widget.item(i).data(Qt.UserRole)
            for i in range(self.list_widget.count())
        ]

    # ── Drag & Drop ──
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        paths = [u.toLocalFile() for u in event.mimeData().urls()]
        self.add_files(paths)
        event.acceptProposedAction()

    def _browse_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Dateien auswählen", "",
            "Dokumente (*.pdf *.txt *.docx *.md *.csv *.html *.py *.json);;Alle Dateien (*)"
        )
        self.add_files(paths)


class ChatBubbleArea(QTextEdit):
    """Read-only HTML chat bubble display."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setStyleSheet("""
            QTextEdit {
                background-color: #F8FAFF;
                border: none;
                border-radius: 10px;
                padding: 8px;
                font-size: 13px;
                color: #2D3748;
            }
        """)

    def append_bubble(self, text: str, role: str = "ai", file_name: str = ""):
        """role: 'user' | 'ai' | 'system'"""
        text_escaped = text.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")

        if role == "user":
            html = f"""
            <div style="text-align:right;margin:8px 4px;">
              <span style="background:#A2D2FF;color:#1A365D;padding:9px 14px;
                border-radius:16px 16px 4px 16px;font-size:13px;display:inline-block;
                max-width:75%;">
                {text_escaped}
              </span>
              {f'<br><span style="font-size:10px;color:#718096;">📄 {file_name}</span>' if file_name else ''}
            </div>"""
        elif role == "system":
            html = f"""
            <div style="text-align:center;margin:6px 4px;">
              <span style="background:#EDF2F7;color:#4A5568;padding:5px 12px;
                border-radius:20px;font-size:11px;display:inline-block;">
                ⚙ {text_escaped}
              </span>
            </div>"""
        else:  # ai
            html = f"""
            <div style="text-align:left;margin:8px 4px;">
              <span style="background:#FFFFFF;color:#2D3748;padding:9px 14px;
                border:1px solid #E2E8F0;border-radius:4px 16px 16px 16px;
                font-size:13px;display:inline-block;max-width:85%;">
                {text_escaped}
              </span>
            </div>"""

        self.append(html)
        # Scroll to bottom
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())


class PreviewPanel(QFrame):
    """Right-side panel: shows AI results and provides save/delete buttons."""
    save_requested   = Signal(str)  # content to save
    delete_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Panel")
        self.setStyleSheet(_PANEL_STYLE)
        self._content = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Title
        row = QHBoxLayout()
        icon = QLabel("📋")
        icon.setStyleSheet("font-size:16px; background:transparent; border:none;")
        row.addWidget(icon)
        lbl = QLabel("Ergebnis-Vorschau")
        lbl.setStyleSheet(_HEADER_LABEL)
        row.addWidget(lbl)
        row.addStretch()
        layout.addLayout(row)

        # Text area
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(False)
        self.text_area.setPlaceholderText(
            "KI-Antworten, Zusammenfassungen und Vergleiche\nerscheinen hier zur Vorschau."
        )
        self.text_area.setStyleSheet("""
            QTextEdit {
                background: #FAFBFD; border: 1px solid #E2E8F0;
                border-radius: 10px; padding: 8px; font-size: 12px; color: #2D3748;
            }
            QTextEdit:focus { border: 1px solid #3182CE; }
        """)
        layout.addWidget(self.text_area)

        # Buttons
        btn_row = QVBoxLayout()
        btn_row.setSpacing(6)

        self.btn_save_src = QPushButton("💾  Speichern (Quelle)")
        self.btn_save_src.setStyleSheet(_BTN_SUCCESS)
        self.btn_save_src.clicked.connect(lambda: self.save_requested.emit(self.text_area.toPlainText()))
        btn_row.addWidget(self.btn_save_src)

        self.btn_save_as = QPushButton("📁  Speichern unter …")
        self.btn_save_as.setStyleSheet(_BTN_SECONDARY)
        self.btn_save_as.clicked.connect(self._save_as)
        btn_row.addWidget(self.btn_save_as)

        self.btn_delete = QPushButton("🗑  Vorschau löschen")
        self.btn_delete.setStyleSheet(_BTN_DANGER)
        self.btn_delete.clicked.connect(self._delete)
        btn_row.addWidget(self.btn_delete)

        layout.addLayout(btn_row)

        # ── Context Memory Tracker ────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #E2E8F0; background: #E2E8F0; border: none; max-height:1px;")
        layout.addWidget(sep)

        mem_hdr = QHBoxLayout()
        mem_icon = QLabel("🧠")
        mem_icon.setStyleSheet("font-size:14px; background:transparent; border:none;")
        mem_hdr.addWidget(mem_icon)
        mem_lbl = QLabel("Context Memory")
        mem_lbl.setStyleSheet(_HEADER_LABEL)
        mem_hdr.addWidget(mem_lbl)
        mem_hdr.addStretch()
        self.mem_pct_lbl = QLabel("0 %")
        self.mem_pct_lbl.setStyleSheet("font-size:12px;font-weight:700;color:#3182CE;background:transparent;border:none;")
        mem_hdr.addWidget(self.mem_pct_lbl)
        layout.addLayout(mem_hdr)

        self.mem_bar = QProgressBar()
        self.mem_bar.setRange(0, 100)
        self.mem_bar.setValue(0)
        self.mem_bar.setTextVisible(False)
        self.mem_bar.setFixedHeight(8)
        self.mem_bar.setStyleSheet("""
            QProgressBar {
                background: #E2E8F0; border-radius: 4px; border: none;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #4299E1, stop:0.7 #3182CE, stop:1 #E53E3E);
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.mem_bar)

        self.mem_status_lbl = QLabel("Kein Gespräch aktiv")
        self.mem_status_lbl.setStyleSheet(_SMALL_LABEL)
        layout.addWidget(self.mem_status_lbl)

    # ── Public helpers ────────────────────────────────────────────────────

    def set_content(self, text: str):
        self._content = text
        self.text_area.setPlainText(text)

    def update_memory(self, ratio: float, history_len: int):
        pct = int(ratio * 100)
        self.mem_bar.setValue(pct)
        self.mem_pct_lbl.setText(f"{pct} %")
        if ratio < 0.5:
            color = "#48BB78"
            status = f"✅ {history_len} Nachrichten – Speicher OK"
        elif ratio < 0.75:
            color = "#ED8936"
            status = f"⚠ {history_len} Nachrichten – halb voll"
        else:
            color = "#E53E3E"
            status = f"🔴 {history_len} Nachrichten – fast voll!"
        self.mem_pct_lbl.setStyleSheet(
            f"font-size:12px;font-weight:700;color:{color};background:transparent;border:none;"
        )
        self.mem_status_lbl.setText(status)

    # ── Private ───────────────────────────────────────────────────────────

    def _save_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Ergebnis speichern", "",
            "Textdatei (*.txt);;Markdown (*.md);;Alle Dateien (*)"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self.text_area.toPlainText())
                QMessageBox.information(self, "Gespeichert", f"Datei gespeichert:\n{path}")
            except Exception as e:
                QMessageBox.warning(self, "Fehler", str(e))

    def _delete(self):
        self.text_area.clear()
        self._content = ""
        self.delete_requested.emit()


# ── Main Tab ──────────────────────────────────────────────────────────────────

class AIAssistantTab(QWidget):
    """AI Assistant v4.1 – 3-column hybrid engine interface."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._worker: AIWorker | None = None
        self._conversation_history: list[dict] = []
        self._active_files: list[str] = []

        self._build_ui()

    # ── UI Construction ───────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(10)

        root.addWidget(self._make_header())

        # 3-column splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(10)
        splitter.setStyleSheet("QSplitter::handle { background: transparent; }")

        splitter.addWidget(self._make_left_panel())
        splitter.addWidget(self._make_center_panel())
        splitter.addWidget(self._make_right_panel())
        splitter.setSizes([280, 520, 300])

        root.addWidget(splitter)

    # ── Header ────────────────────────────────────────────────────────────

    def _make_header(self) -> QFrame:
        frame = QFrame()
        frame.setMaximumHeight(50)   # Patch v3.9.6: cap header height
        frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #EBF8FF, stop:1 #F0FFF4);
                border: 1px solid #BEE3F8; border-radius: 12px;
            }
            QLabel { background: transparent; border: none; }
        """)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(14, 4, 14, 4)

        # Icon – scales with title
        icon = QLabel("🤖")
        icon.setStyleSheet("font-size:20px; background:transparent; border:none;")
        layout.addWidget(icon)

        # Title – bumped to 16pt per Patch v3.9.6
        title = QLabel("AI Assistant  <span style='font-size:10px;color:#718096;font-weight:400'>v4.1.1 – Hybrid Engine</span>")
        title.setTextFormat(Qt.RichText)
        title.setStyleSheet("font-size:16pt;font-weight:800;color:#1A365D;background:transparent;border:none;")
        layout.addWidget(title)
        layout.addStretch()

        # Backend selector label
        be_lbl = QLabel("Engine:")
        be_lbl.setStyleSheet("font-size:11px;font-weight:600;color:#4A5568;background:transparent;border:none;")
        layout.addWidget(be_lbl)

        self.combo_backend = QComboBox()
        self.combo_backend.addItems([
            "🦙  Lokal – Ollama (Dolphin)",
            "✨  Gemini 3 Pro  (Cloud)",
            "⚡  Gemini 3 Flash (Cloud)",
        ])
        self.combo_backend.setStyleSheet("""
            QComboBox {
                padding: 4px 10px; border-radius: 10px; border: 1px solid #BEE3F8;
                background: white; font-size: 11px; font-weight: 600; color: #2D3748;
                min-width: 200px;
            }
            QComboBox:hover { border: 1px solid #3182CE; }
            QComboBox::drop-down { border: none; }
        """)
        self.combo_backend.currentIndexChanged.connect(self._on_backend_changed)
        layout.addWidget(self.combo_backend)

        # Status dot
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("font-size:12px;color:#48BB78;background:transparent;border:none;")
        self.status_dot.setToolTip("Backend-Status: Bereit")
        layout.addWidget(self.status_dot)

        # Clear history button
        btn_clear = QPushButton("🗑  Chat leeren")
        btn_clear.setStyleSheet(_BTN_SECONDARY)
        btn_clear.setFixedHeight(26)
        btn_clear.clicked.connect(self._clear_chat)
        layout.addWidget(btn_clear)

        return frame

    # ── Left Panel ────────────────────────────────────────────────────────

    def _make_left_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 5, 0)
        layout.setSpacing(10)

        # Drop Zone
        self.drop_zone = DropZoneList()
        self.drop_zone.files_dropped.connect(self._on_files_added)
        layout.addWidget(self.drop_zone)

        # Quick Actions Panel
        qa_frame = QFrame()
        qa_frame.setObjectName("Panel")
        qa_frame.setStyleSheet(_PANEL_STYLE)
        qa_layout = QVBoxLayout(qa_frame)
        qa_layout.setContentsMargins(12, 10, 12, 12)
        qa_layout.setSpacing(8)

        qa_title = QLabel("⚡ Quick Actions")
        qa_title.setStyleSheet(_HEADER_LABEL)
        qa_layout.addWidget(qa_title)

        actions = [
            ("📝  Zusammenfassen",   self._qa_summarize, "#3182CE"),
            ("💡  Erklären",         self._qa_explain,   "#805AD5"),
            ("✏️  Umschreiben",      self._qa_rewrite,   "#D69E2E"),
            ("⚖️  Multi-File Compare", self._qa_compare, "#DD6B20"),
        ]
        for label, slot, color in actions:
            btn = QPushButton(label)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: white; color: {color};
                    border: 1px solid {color}55; border-radius: 10px;
                    padding: 9px 12px; font-weight: 700; font-size: 12px;
                    text-align: left;
                }}
                QPushButton:hover {{ background-color: {color}11; border-color: {color}; }}
                QPushButton:pressed {{ background-color: {color}22; }}
            """)
            btn.clicked.connect(slot)
            qa_layout.addWidget(btn)

        layout.addWidget(qa_frame)
        layout.addStretch()
        return w

    # ── Center Panel ──────────────────────────────────────────────────────

    def _make_center_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(8)

        # Chat area frame
        chat_frame = QFrame()
        chat_frame.setObjectName("Panel")
        chat_frame.setStyleSheet(_PANEL_STYLE)
        chat_fl = QVBoxLayout(chat_frame)
        chat_fl.setContentsMargins(10, 10, 10, 10)
        chat_fl.setSpacing(6)

        ch_hdr = QHBoxLayout()
        ch_icon = QLabel("💬")
        ch_icon.setStyleSheet("font-size:16px; background:transparent; border:none;")
        ch_hdr.addWidget(ch_icon)
        ch_title = QLabel("Chat-Verlauf")
        ch_title.setStyleSheet(_HEADER_LABEL)
        ch_hdr.addWidget(ch_title)
        ch_hdr.addStretch()
        chat_fl.addLayout(ch_hdr)

        self.chat_area = ChatBubbleArea()
        chat_fl.addWidget(self.chat_area)

        # Progress bar (spinner)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # indeterminate
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background: #E2E8F0; border: none; border-radius: 2px; }
            QProgressBar::chunk { background: #3182CE; border-radius: 2px; }
        """)
        self.progress_bar.setVisible(False)
        chat_fl.addWidget(self.progress_bar)

        # stretch=4 → chat area gets ~80% of available vertical space
        layout.addWidget(chat_frame, 4)

        # Active file chip
        self.chip_frame = QFrame()
        self.chip_frame.setStyleSheet("""
            QFrame {
                background-color: #EBF8FF; border: 1px solid #BEE3F8;
                border-radius: 20px; padding: 2px;
            }
            QLabel { background: transparent; border: none; color: #2B6CB0; font-size: 11px; font-weight: 600; }
        """)
        chip_hl = QHBoxLayout(self.chip_frame)
        chip_hl.setContentsMargins(10, 3, 6, 3)
        chip_hl.setSpacing(6)
        self.chip_label = QLabel("📎 Kontext: —")
        chip_hl.addWidget(self.chip_label)
        chip_hl.addStretch()
        btn_chip_clr = QPushButton("✕")
        btn_chip_clr.setFixedSize(20, 20)
        btn_chip_clr.setStyleSheet(
            "QPushButton{border:none;background:transparent;color:#E53E3E;font-weight:700;}"
            "QPushButton:hover{color:#C53030;}"
        )
        btn_chip_clr.clicked.connect(self._clear_file_context)
        chip_hl.addWidget(btn_chip_clr)
        self.chip_frame.setVisible(False)
        layout.addWidget(self.chip_frame)

        # Input row
        input_frame = QFrame()
        input_frame.setObjectName("Panel")
        input_frame.setStyleSheet(_PANEL_STYLE)
        input_fl = QVBoxLayout(input_frame)
        input_fl.setContentsMargins(10, 8, 10, 10)
        input_fl.setSpacing(8)

        # Template dropdown
        tpl_row = QHBoxLayout()
        tpl_lbl = QLabel("🎭 Rolle:")
        tpl_lbl.setStyleSheet(_SMALL_LABEL)
        tpl_row.addWidget(tpl_lbl)

        self.combo_template = QComboBox()
        self.combo_template.addItems([
            "Generalist (Standard)",
            "🎓 Experte & Berater",
            "📚 Lehrer – Einfach erklären",
            "📊 Analyst – Strukturiert",
            "✍️  Texter – Kreativ umschreiben",
        ])
        self.combo_template.setStyleSheet("""
            QComboBox {
                padding: 5px 10px; border-radius: 8px; border: 1px solid #E2E8F0;
                background: white; font-size: 12px; color: #4A5568;
            }
            QComboBox:hover { border-color: #3182CE; }
            QComboBox::drop-down { border: none; }
        """)
        tpl_row.addWidget(self.combo_template)
        tpl_row.addStretch()
        input_fl.addLayout(tpl_row)

        # Text input + send
        send_row = QHBoxLayout()
        send_row.setSpacing(8)

        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText(
            "Stell eine Frage, oder drücke Quick Action für Dateioperationen …"
        )
        self.prompt_input.setStyleSheet("""
            QLineEdit {
                background: #F8FAFF; border: 1px solid #CBD5E0;
                border-radius: 10px; padding: 10px 14px; font-size: 13px; color: #2D3748;
            }
            QLineEdit:focus { border: 1.5px solid #3182CE; background: white; }
        """)
        self.prompt_input.returnPressed.connect(self._send_chat)
        send_row.addWidget(self.prompt_input)

        self.btn_send = QPushButton("Senden ➤")
        self.btn_send.setStyleSheet(_BTN_PRIMARY)
        self.btn_send.setFixedHeight(42)
        self.btn_send.clicked.connect(self._send_chat)
        send_row.addWidget(self.btn_send)

        input_fl.addLayout(send_row)
        layout.addWidget(input_frame)

        return w

    # ── Right Panel ───────────────────────────────────────────────────────

    def _make_right_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(5, 0, 0, 0)
        layout.setSpacing(0)

        self.preview_panel = PreviewPanel()
        self.preview_panel.save_requested.connect(self._save_to_source)
        self.preview_panel.delete_requested.connect(lambda: None)
        layout.addWidget(self.preview_panel)

        return w

    # ── Backend helpers ───────────────────────────────────────────────────

    @property
    def _backend(self) -> str:
        """Map dropdown index → backend string for ai_engine."""
        return ["ollama", "gemini_pro", "gemini_flash"][self.combo_backend.currentIndex()]

    def _on_backend_changed(self, idx: int):
        names = ["Ollama (Lokal)", "Gemini 3 Pro", "Gemini 3 Flash"]
        name  = names[idx]
        self.chat_area.append_bubble(f"Backend gewechselt → {name}", role="system")

    def _get_system_prompt_for_template(self) -> str:
        templates = {
            0: "Du bist ein hilfreicher, allgemeiner KI-Assistent.",
            1: (
                "Du bist ein hochspezialisierter Experte und Berater. "
                "Gib professionelle, detaillierte Antworten mit konkreten Empfehlungen."
            ),
            2: (
                "Du bist ein geduldiger Lehrer. Erkläre alles so einfach wie möglich, "
                "nutze Analogien und Beispiele."
            ),
            3: (
                "Du bist ein präziser Analyst. Strukturiere deine Antworten immer mit "
                "Überschriften, Bullet-Points und klaren Schlussfolgerungen."
            ),
            4: (
                "Du bist ein kreativer Texter. Schreibe lebendig, ansprechend und "
                "mit überzeugender Sprache."
            ),
        }
        return templates.get(self.combo_template.currentIndex(), templates[0])

    # ── File context ──────────────────────────────────────────────────────

    def _on_files_added(self, paths: list[str]):
        self._active_files = paths
        if paths:
            names = ", ".join(os.path.basename(p) for p in paths[:3])
            extra = f" +{len(paths)-3}" if len(paths) > 3 else ""
            self.chip_label.setText(f"📎 Kontext: {names}{extra}")
            self.chip_frame.setVisible(True)

    def _clear_file_context(self):
        """Remove all file context and hide the context chip."""
        self._active_files = []
        self.active_context_file = None   # Patch v3.9.6: explicit None
        self.chip_frame.setVisible(False)
        self.drop_zone.list_widget.clearSelection()

    # ── Chat sending ──────────────────────────────────────────────────────

    def _send_chat(self):
        text = self.prompt_input.text().strip()
        if not text:
            return

        self.prompt_input.clear()
        self.btn_send.setEnabled(False)
        self.status_dot.setStyleSheet("font-size:14px;color:#ED8936;background:transparent;border:none;")

        # Build context from selected files
        selected = self.drop_zone.get_selected_paths()
        context_files = selected if selected else self._active_files

        file_name = ""
        if context_files:
            file_name = ", ".join(os.path.basename(p) for p in context_files[:3])

        self.chat_area.append_bubble(text, role="user", file_name=file_name)

        # Build prompt
        if context_files:
            from logic.ai_engine import _read_file_text as _read
            ctx_parts = []
            for fp in context_files[:3]:
                txt = _read(fp, max_chars=2500)
                ctx_parts.append(f"[{os.path.basename(fp)}]\n{txt}")
            file_ctx = "\n\n".join(ctx_parts)
            prompt = f"Datei-Kontext:\n{file_ctx}\n\nFrage:\n{text}"
        else:
            prompt = text

        # Update conversation history
        self._conversation_history.append({"role": "user", "content": prompt})

        # Apply template system prompt
        import logic.ai_engine as eng
        eng.SYSTEM_PROMPT = self._get_system_prompt_for_template()

        self.progress_bar.setVisible(True)
        self._worker = AIWorker(
            eng.chat_ai, prompt, self._backend, list(self._conversation_history[:-1])
        )
        self._worker.response_ready.connect(self._on_ai_response)
        self._worker.error_occurred.connect(self._on_ai_error)
        self._worker.finished.connect(self._on_worker_done)
        self._worker.start()

    def _on_ai_response(self, text: str):
        self.chat_area.append_bubble(text, role="ai")
        self.preview_panel.set_content(text)
        self._conversation_history.append({"role": "assistant", "content": text})
        self._update_memory()

    def _on_ai_error(self, err: str):
        self.chat_area.append_bubble(f"⚠ Fehler: {err}", role="system")

    def _on_worker_done(self):
        self.progress_bar.setVisible(False)
        self.btn_send.setEnabled(True)
        self.status_dot.setStyleSheet("font-size:14px;color:#48BB78;background:transparent;border:none;")

    # ── Quick Actions ─────────────────────────────────────────────────────

    def _run_file_action(self, func_name: str):
        """Generic dispatcher for file-level quick actions."""
        import logic.ai_engine as eng

        selected = self.drop_zone.get_selected_paths()
        all_paths = self.drop_zone.get_all_paths()
        targets = selected if selected else all_paths

        if not targets:
            self.chat_area.append_bubble(
                "⚠ Bitte zuerst eine Datei in die Drop Zone laden.", role="system"
            )
            return

        self.btn_send.setEnabled(False)
        self.status_dot.setStyleSheet("font-size:14px;color:#ED8936;background:transparent;border:none;")

        label_map = {
            "summarize": "Zusammenfassung",
            "explain":   "Erklärung",
            "rewrite":   "Überarbeitung",
        }

        fp = targets[0]
        name = os.path.basename(fp)
        self.chat_area.append_bubble(
            f"{label_map.get(func_name, func_name)} von: {name}", role="user"
        )
        self.progress_bar.setVisible(True)

        if func_name == "summarize":
            fn = lambda: eng.summarize_file(fp, self._backend)
        elif func_name == "explain":
            fn = lambda: eng.explain_file(fp, self._backend)
        elif func_name == "rewrite":
            fn = lambda: eng.rewrite_file(fp, self._backend)
        else:
            return

        self._worker = AIWorker(fn)
        self._worker.response_ready.connect(self._on_ai_response)
        self._worker.error_occurred.connect(self._on_ai_error)
        self._worker.finished.connect(self._on_worker_done)
        self._worker.start()

    def _qa_summarize(self):
        self._run_file_action("summarize")

    def _qa_explain(self):
        self._run_file_action("explain")

    def _qa_rewrite(self):
        self._run_file_action("rewrite")

    def _qa_compare(self):
        import logic.ai_engine as eng

        all_paths = self.drop_zone.get_all_paths()
        if len(all_paths) < 2:
            self.chat_area.append_bubble(
                "⚠ Multi-File Compare benötigt mindestens 2 Dateien in der Drop Zone.",
                role="system"
            )
            return

        names = " & ".join(os.path.basename(p) for p in all_paths[:4])
        self.chat_area.append_bubble(f"Vergleiche: {names}", role="user")
        self.progress_bar.setVisible(True)
        self.btn_send.setEnabled(False)
        self.status_dot.setStyleSheet("font-size:14px;color:#ED8936;background:transparent;border:none;")

        self._worker = AIWorker(eng.compare_files, all_paths[:4], self._backend)
        self._worker.response_ready.connect(self._on_ai_response)
        self._worker.error_occurred.connect(self._on_ai_error)
        self._worker.finished.connect(self._on_worker_done)
        self._worker.start()

    # ── Memory tracker ────────────────────────────────────────────────────

    def _update_memory(self):
        from logic.ai_engine import get_context_fill_ratio
        ratio = get_context_fill_ratio(self._conversation_history)
        self.preview_panel.update_memory(ratio, len(self._conversation_history))

    # ── Misc ──────────────────────────────────────────────────────────────

    def _clear_chat(self):
        self._conversation_history.clear()
        self.chat_area.clear()
        self.preview_panel.update_memory(0.0, 0)
        self.chat_area.append_bubble("💬 Chat geleert – neues Gespräch gestartet.", role="system")

    def _save_to_source(self, content: str):
        selected = self.drop_zone.get_selected_paths()
        if not selected:
            QMessageBox.information(
                self, "Kein Ziel",
                "Bitte eine Datei in der Drop Zone auswählen um sie zu überschreiben.\n"
                "Oder nutze 'Speichern unter...' für eine neue Datei."
            )
            return
        fp = selected[0]
        try:
            with open(fp, "w", encoding="utf-8") as f:
                f.write(content)
            self.chat_area.append_bubble(f"✅ Gespeichert → {os.path.basename(fp)}", role="system")
        except Exception as e:
            QMessageBox.warning(self, "Fehler", str(e))

    # ── Drag & Drop (global / MainWindow forwarding) ──────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        paths = [u.toLocalFile() for u in event.mimeData().urls()]
        self.drop_zone.add_files(paths)
        event.acceptProposedAction()

    def receive_global_drop(self, files: list[str]):
        """Called by MainWindow when files are dropped on the Dashboard."""
        self.drop_zone.add_files(files)
