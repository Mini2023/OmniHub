"""
Omni-Hub – AI Assistant Tab v4.1.2 (Patch: Chat Evolution & UI Re-Balancing)
==============================================================================
Changes in 4.1.2:
  - WhatsApp-style chat: user RIGHT / AI LEFT, no centred text, dynamic bubble width
  - Quick Actions as 2-column grid tiles (saves vertical space)
  - Beispiel-Prompts dropdown next to the Rolle selector
  - Intelligent preview filter: only file/Quick-Action results reach preview panel
  - Ultra-compact header (maximumHeight=42)
  - Splitter widths: 220 | 580 | 300  (chat gets more room)
"""

from __future__ import annotations
import os
import json

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QListWidget, QListWidgetItem, QComboBox,
    QLineEdit, QSizePolicy, QFrame, QProgressBar,
    QFileDialog, QSplitter, QScrollArea, QAbstractItemView,
    QMessageBox, QGridLayout,
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QMimeData
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent, QFont

try:
    import qtawesome as qta
    _HAS_QTA = True
except ImportError:
    _HAS_QTA = False

# ── Style constants ───────────────────────────────────────────────────────────

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

_HEADER_LABEL = "font-size:12px; font-weight:700; color:#2D3748; background:transparent; border:none;"
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
        border-radius: 10px; padding: 6px 12px; font-weight: 600; font-size: 11px;
    }
    QPushButton:hover { background-color: #E2E8F0; border-color: #3182CE; color:#3182CE; }
    QPushButton:pressed { background-color: #CBD5E0; }
    QPushButton:disabled { background-color: #f0f0f0; color:#bbb; }
"""

_BTN_DANGER = """
    QPushButton {
        background-color: #FED7D7; color: #C53030; border: 1px solid #FC8181;
        border-radius: 10px; padding: 7px 12px; font-weight: 600; font-size: 11px;
    }
    QPushButton:hover { background-color: #FEB2B2; border-color: #E53E3E; }
"""

_BTN_SUCCESS = """
    QPushButton {
        background-color: #C6F6D5; color: #276749; border: 1px solid #9AE6B4;
        border-radius: 10px; padding: 7px 12px; font-weight: 600; font-size: 11px;
    }
    QPushButton:hover { background-color: #9AE6B4; border-color: #48BB78; }
"""

# ── Beispiel-Prompts ──────────────────────────────────────────────────────────

EXAMPLE_PROMPTS = [
    "── Beispiel-Prompts ──",
    "Fasse dieses Dokument zusammen",
    "Finde Widersprüche in diesen Dateien",
    "Erstelle eine Tabelle aus den Daten",
    "Was sind die wichtigsten Kernaussagen?",
    "Erkläre das einfach für einen Laien",
    "Übersetze diesen Text ins Englische",
    "Liste alle Zahlen und Fakten auf",
    "Schreibe eine professionelle E-Mail dazu",
]

# ── QThread Worker ────────────────────────────────────────────────────────────

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


# ── DropZoneList ──────────────────────────────────────────────────────────────

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
        self.setMinimumHeight(130)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(5)

        # Header row
        h = QHBoxLayout()
        icon_lbl = QLabel("📂")
        icon_lbl.setStyleSheet("font-size:15px; background:transparent; border:none;")
        h.addWidget(icon_lbl)
        title = QLabel("Drop Zone")
        title.setStyleSheet(_HEADER_LABEL)
        h.addWidget(title)
        h.addStretch()

        btn_add = QPushButton("+ Datei")
        btn_add.setStyleSheet(_BTN_SECONDARY)
        btn_add.setFixedHeight(24)
        btn_add.clicked.connect(self._browse_files)
        h.addWidget(btn_add)

        btn_clr = QPushButton("✕")
        btn_clr.setStyleSheet(_BTN_DANGER)
        btn_clr.setFixedHeight(24)
        btn_clr.setFixedWidth(30)
        btn_clr.clicked.connect(self.clear_all)
        h.addWidget(btn_clr)
        layout.addLayout(h)

        # Placeholder
        self._placeholder = QLabel("PDF · TXT · DOCX\nHier ablegen")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setStyleSheet(
            "color:#A0AEC0; font-size:11px; background:transparent; border:none;"
        )

        # List widget
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_widget.setStyleSheet("""
            QListWidget {
                background: #F8FAFF; border: none; border-radius: 8px;
                font-size: 11px; color: #2D3748;
            }
            QListWidget::item { padding: 5px 8px; border-radius: 5px; }
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
        return [item.data(Qt.UserRole) for item in self.list_widget.selectedItems()]

    def get_all_paths(self) -> list[str]:
        return [self.list_widget.item(i).data(Qt.UserRole) for i in range(self.list_widget.count())]

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


# ── Chat Bubble Area (WhatsApp-Style) ─────────────────────────────────────────

class ChatBubbleArea(QTextEdit):
    """
    Read-only HTML chat display with strict WhatsApp-style alignment:
      - User messages: RIGHT-aligned blue bubble
      - AI messages:   LEFT-aligned white bubble with border
      - System notes:  centred pill
    Each bubble uses an outer full-width div + an inner inline-block span
    so the bubble width is dynamic (text-dependent) while alignment is strict.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setStyleSheet("""
            QTextEdit {
                background-color: #F0F4F8;
                border: none;
                border-radius: 12px;
                padding: 6px;
                font-size: 13px;
                color: #2D3748;
            }
        """)

    def append_bubble(self, text: str, role: str = "ai", file_name: str = ""):
        """
        role: 'user' | 'ai' | 'system'
        The outer div is full-width; text-align pushes the inner span.
        The inner span is inline-block so it only takes as much width as needed.
        """
        # Escape HTML but keep meaningful newlines
        safe = (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", "<br>"))

        file_badge = ""
        if file_name:
            file_badge = (
                f'<div style="text-align:inherit;margin-top:3px;">'
                f'<span style="font-size:10px;color:#718096;">📄 {file_name}</span>'
                f'</div>'
            )

        if role == "user":
            html = f"""
<div style="width:100%;text-align:right;margin:6px 0;">
<span style="
  display:inline-block;
  background:#3182CE;
  color:#FFFFFF;
  padding:9px 14px;
  border-radius:18px 18px 4px 18px;
  font-size:13px;
  max-width:78%;
  word-wrap:break-word;
  text-align:left;
">{safe}</span>
{file_badge}
</div>"""

        elif role == "system":
            html = f"""
<div style="width:100%;text-align:center;margin:5px 0;">
<span style="
  display:inline-block;
  background:#EDF2F7;
  color:#4A5568;
  padding:4px 14px;
  border-radius:20px;
  font-size:10px;
">⚙ {safe}</span>
</div>"""

        else:  # ai
            html = f"""
<div style="width:100%;text-align:left;margin:6px 0;">
<span style="
  display:inline-block;
  background:#FFFFFF;
  color:#2D3748;
  padding:9px 14px;
  border:1px solid #E2E8F0;
  border-radius:4px 18px 18px 18px;
  font-size:13px;
  max-width:82%;
  word-wrap:break-word;
  text-align:left;
">{safe}</span>
{file_badge}
</div>"""

        self.append(html)
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())


# ── Preview Panel (right column) ─────────────────────────────────────────────

class PreviewPanel(QFrame):
    """Right-side panel: shows AI file/action results and context memory bar."""
    save_requested   = Signal(str)
    delete_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Panel")
        self.setStyleSheet(_PANEL_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Title
        row = QHBoxLayout()
        icon = QLabel("📋")
        icon.setStyleSheet("font-size:15px; background:transparent; border:none;")
        row.addWidget(icon)
        lbl = QLabel("Ergebnis-Vorschau")
        lbl.setStyleSheet(_HEADER_LABEL)
        row.addWidget(lbl)
        row.addStretch()
        layout.addLayout(row)

        # Sub-label
        self._sub = QLabel("Erscheint nur bei Datei-Anfragen")
        self._sub.setStyleSheet(_SMALL_LABEL)
        layout.addWidget(self._sub)

        # Text area
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(False)
        self.text_area.setPlaceholderText(
            "Quick-Action oder Datei-Anfrage\nErgebnis erscheint hier."
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
        btn_row.setSpacing(5)

        self.btn_save_src = QPushButton("💾  Speichern (Quelle)")
        self.btn_save_src.setStyleSheet(_BTN_SUCCESS)
        self.btn_save_src.clicked.connect(
            lambda: self.save_requested.emit(self.text_area.toPlainText())
        )
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

        # Context Memory Tracker
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background:#E2E8F0; border:none; max-height:1px;")
        layout.addWidget(sep)

        mem_hdr = QHBoxLayout()
        mem_icon = QLabel("🧠")
        mem_icon.setStyleSheet("font-size:13px; background:transparent; border:none;")
        mem_hdr.addWidget(mem_icon)
        mem_lbl = QLabel("Context Memory")
        mem_lbl.setStyleSheet(_HEADER_LABEL)
        mem_hdr.addWidget(mem_lbl)
        mem_hdr.addStretch()
        self.mem_pct_lbl = QLabel("0 %")
        self.mem_pct_lbl.setStyleSheet(
            "font-size:11px;font-weight:700;color:#3182CE;background:transparent;border:none;"
        )
        mem_hdr.addWidget(self.mem_pct_lbl)
        layout.addLayout(mem_hdr)

        self.mem_bar = QProgressBar()
        self.mem_bar.setRange(0, 100)
        self.mem_bar.setValue(0)
        self.mem_bar.setTextVisible(False)
        self.mem_bar.setFixedHeight(7)
        self.mem_bar.setStyleSheet("""
            QProgressBar {
                background: #E2E8F0; border-radius: 3px; border: none;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #4299E1, stop:0.7 #3182CE, stop:1 #E53E3E);
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.mem_bar)

        self.mem_status_lbl = QLabel("Kein Gespräch aktiv")
        self.mem_status_lbl.setStyleSheet(_SMALL_LABEL)
        layout.addWidget(self.mem_status_lbl)

    # ── Public helpers ────────────────────────────────────────────────────

    def set_content(self, text: str):
        self.text_area.setPlainText(text)

    def update_memory(self, ratio: float, history_len: int):
        pct = int(ratio * 100)
        self.mem_bar.setValue(pct)
        self.mem_pct_lbl.setText(f"{pct} %")
        if ratio < 0.5:
            colour = "#48BB78"; status = f"✅ {history_len} Nachrichten – OK"
        elif ratio < 0.75:
            colour = "#ED8936"; status = f"⚠ {history_len} Nachrichten – halb voll"
        else:
            colour = "#E53E3E"; status = f"🔴 {history_len} Nachrichten – fast voll!"
        self.mem_pct_lbl.setStyleSheet(
            f"font-size:11px;font-weight:700;color:{colour};background:transparent;border:none;"
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
        self.delete_requested.emit()


# ── Main Tab ──────────────────────────────────────────────────────────────────

class AIAssistantTab(QWidget):
    """AI Assistant v4.1.2 – WhatsApp-style chat, grid Quick Actions, smart preview."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._worker: AIWorker | None = None
        self._conversation_history: list[dict] = []
        self._active_files: list[str] = []
        self.active_context_file = None
        # Flag: True when the AI response should also update the preview panel
        self._preview_this_response: bool = False

        self._build_ui()

    # ── UI Construction ───────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 6, 10, 8)
        root.setSpacing(6)

        root.addWidget(self._make_header())

        # 3-column splitter – wider centre column
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(8)
        splitter.setStyleSheet("QSplitter::handle { background: transparent; }")

        splitter.addWidget(self._make_left_panel())
        splitter.addWidget(self._make_center_panel())
        splitter.addWidget(self._make_right_panel())
        splitter.setSizes([220, 580, 300])   # centre gets lion's share

        root.addWidget(splitter)

    # ── Header (ultra-compact) ────────────────────────────────────────────

    def _make_header(self) -> QFrame:
        frame = QFrame()
        frame.setMaximumHeight(42)   # v4.1.2: absolute minimum height
        frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #EBF8FF, stop:1 #F0FFF4);
                border: 1px solid #BEE3F8; border-radius: 10px;
            }
            QLabel { background: transparent; border: none; }
        """)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 3, 12, 3)
        layout.setSpacing(8)

        icon = QLabel("🤖")
        icon.setStyleSheet("font-size:16px; background:transparent; border:none;")
        layout.addWidget(icon)

        title = QLabel("AI Assistant <span style='font-size:9px;color:#718096;font-weight:400'>v4.1.2</span>")
        title.setTextFormat(Qt.RichText)
        title.setStyleSheet("font-size:13pt;font-weight:800;color:#1A365D;background:transparent;border:none;")
        layout.addWidget(title)
        layout.addStretch()

        be_lbl = QLabel("Engine:")
        be_lbl.setStyleSheet("font-size:10px;font-weight:600;color:#4A5568;background:transparent;border:none;")
        layout.addWidget(be_lbl)

        self.combo_backend = QComboBox()
        self.combo_backend.addItems([
            "🦙  Ollama (Lokal)",
            "✨  Gemini 3 Pro",
            "⚡  Gemini 3 Flash",
        ])
        self.combo_backend.setStyleSheet("""
            QComboBox {
                padding: 3px 8px; border-radius: 8px; border: 1px solid #BEE3F8;
                background: white; font-size: 10px; font-weight: 600; color: #2D3748;
                min-width: 150px;
            }
            QComboBox:hover { border: 1px solid #3182CE; }
            QComboBox::drop-down { border: none; }
        """)
        self.combo_backend.currentIndexChanged.connect(self._on_backend_changed)
        layout.addWidget(self.combo_backend)

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("font-size:11px;color:#48BB78;background:transparent;border:none;")
        layout.addWidget(self.status_dot)

        btn_clear = QPushButton("🗑 Leeren")
        btn_clear.setStyleSheet(_BTN_SECONDARY)
        btn_clear.setFixedHeight(24)
        btn_clear.clicked.connect(self._clear_chat)
        layout.addWidget(btn_clear)

        return frame

    # ── Left Panel: Drop Zone + 2-Column Quick Action Grid ────────────────

    def _make_left_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(8)

        # Drop Zone
        self.drop_zone = DropZoneList()
        self.drop_zone.files_dropped.connect(self._on_files_added)
        layout.addWidget(self.drop_zone)

        # Quick Actions – 2-column grid (saves vertical space)
        qa_frame = QFrame()
        qa_frame.setObjectName("Panel")
        qa_frame.setStyleSheet(_PANEL_STYLE)
        qa_layout = QVBoxLayout(qa_frame)
        qa_layout.setContentsMargins(10, 8, 10, 10)
        qa_layout.setSpacing(6)

        qa_title = QLabel("⚡ Quick Actions")
        qa_title.setStyleSheet(_HEADER_LABEL)
        qa_layout.addWidget(qa_title)

        grid = QGridLayout()
        grid.setSpacing(6)

        actions = [
            ("📝 Zusammenfassen", self._qa_summarize, "#3182CE"),
            ("💡 Erklären",       self._qa_explain,   "#805AD5"),
            ("✏️ Umschreiben",    self._qa_rewrite,   "#D69E2E"),
            ("⚖️ Vergleichen",    self._qa_compare,   "#DD6B20"),
        ]
        for idx, (label, slot, color) in enumerate(actions):
            btn = QPushButton(label)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: white; color: {color};
                    border: 1px solid {color}55; border-radius: 10px;
                    padding: 10px 6px; font-weight: 700; font-size: 11px;
                    text-align: center;
                }}
                QPushButton:hover {{ background-color: {color}15; border-color: {color}; }}
                QPushButton:pressed {{ background-color: {color}30; }}
            """)
            btn.clicked.connect(slot)
            row_idx, col_idx = divmod(idx, 2)
            grid.addWidget(btn, row_idx, col_idx)

        qa_layout.addLayout(grid)
        layout.addWidget(qa_frame)
        layout.addStretch()
        return w

    # ── Center Panel: WhatsApp Chat + Input bar ───────────────────────────

    def _make_center_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(6)

        # Chat area
        chat_frame = QFrame()
        chat_frame.setObjectName("Panel")
        chat_frame.setStyleSheet(_PANEL_STYLE)
        chat_fl = QVBoxLayout(chat_frame)
        chat_fl.setContentsMargins(8, 8, 8, 8)
        chat_fl.setSpacing(4)

        ch_hdr = QHBoxLayout()
        ch_icon = QLabel("💬")
        ch_icon.setStyleSheet("font-size:14px; background:transparent; border:none;")
        ch_hdr.addWidget(ch_icon)
        ch_title = QLabel("Chat-Verlauf")
        ch_title.setStyleSheet(_HEADER_LABEL)
        ch_hdr.addWidget(ch_title)
        ch_hdr.addStretch()
        chat_fl.addLayout(ch_hdr)

        self.chat_area = ChatBubbleArea()
        chat_fl.addWidget(self.chat_area)

        # Indeterminate progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background: #E2E8F0; border: none; border-radius: 1px; }
            QProgressBar::chunk { background: #3182CE; border-radius: 1px; }
        """)
        self.progress_bar.setVisible(False)
        chat_fl.addWidget(self.progress_bar)

        # stretch=5 → chat takes ~80% of column height
        layout.addWidget(chat_frame, 5)

        # Active file chip (context indicator)
        self.chip_frame = QFrame()
        self.chip_frame.setStyleSheet("""
            QFrame {
                background-color: #EBF8FF; border: 1px solid #BEE3F8;
                border-radius: 16px; padding: 1px;
            }
            QLabel { background: transparent; border: none; color: #2B6CB0; font-size: 11px; font-weight: 600; }
        """)
        chip_hl = QHBoxLayout(self.chip_frame)
        chip_hl.setContentsMargins(10, 2, 6, 2)
        chip_hl.setSpacing(5)
        self.chip_label = QLabel("📎 Kontext: —")
        chip_hl.addWidget(self.chip_label)
        chip_hl.addStretch()
        btn_chip_clr = QPushButton("✕")
        btn_chip_clr.setFixedSize(18, 18)
        btn_chip_clr.setStyleSheet(
            "QPushButton{border:none;background:transparent;color:#E53E3E;font-weight:700;font-size:11px;}"
            "QPushButton:hover{color:#C53030;}"
        )
        btn_chip_clr.clicked.connect(self._clear_file_context)
        chip_hl.addWidget(btn_chip_clr)
        self.chip_frame.setVisible(False)
        layout.addWidget(self.chip_frame)

        # ── Input panel ───────────────────────────────────────────────────
        input_frame = QFrame()
        input_frame.setObjectName("Panel")
        input_frame.setStyleSheet(_PANEL_STYLE)
        input_fl = QVBoxLayout(input_frame)
        input_fl.setContentsMargins(10, 7, 10, 8)
        input_fl.setSpacing(6)

        # Row 1: Rolle + Beispiel-Prompts
        tpl_row = QHBoxLayout()
        tpl_row.setSpacing(6)

        tpl_lbl = QLabel("🎭")
        tpl_lbl.setStyleSheet(_SMALL_LABEL)
        tpl_row.addWidget(tpl_lbl)

        self.combo_template = QComboBox()
        self.combo_template.addItems([
            "Generalist",
            "🎓 Experte & Berater",
            "📚 Lehrer",
            "📊 Analyst",
            "✍️  Texter",
        ])
        self.combo_template.setStyleSheet("""
            QComboBox {
                padding: 4px 8px; border-radius: 8px; border: 1px solid #E2E8F0;
                background: white; font-size: 11px; color: #4A5568;
            }
            QComboBox:hover { border-color: #3182CE; }
            QComboBox::drop-down { border: none; }
        """)
        tpl_row.addWidget(self.combo_template)

        # Beispiel-Prompts dropdown
        ex_lbl = QLabel("💡")
        ex_lbl.setStyleSheet(_SMALL_LABEL)
        tpl_row.addWidget(ex_lbl)

        self.combo_examples = QComboBox()
        self.combo_examples.addItems(EXAMPLE_PROMPTS)
        self.combo_examples.setStyleSheet("""
            QComboBox {
                padding: 4px 8px; border-radius: 8px; border: 1px solid #E2E8F0;
                background: white; font-size: 11px; color: #4A5568;
                min-width: 160px;
            }
            QComboBox:hover { border-color: #805AD5; }
            QComboBox::drop-down { border: none; }
        """)
        self.combo_examples.currentIndexChanged.connect(self._on_example_selected)
        tpl_row.addWidget(self.combo_examples)
        tpl_row.addStretch()
        input_fl.addLayout(tpl_row)

        # Row 2: text input + send button
        send_row = QHBoxLayout()
        send_row.setSpacing(7)

        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText(
            "Frag etwas, oder wähle Quick Action / Beispiel-Prompt …"
        )
        self.prompt_input.setStyleSheet("""
            QLineEdit {
                background: #F8FAFF; border: 1px solid #CBD5E0;
                border-radius: 10px; padding: 9px 13px; font-size: 13px; color: #2D3748;
            }
            QLineEdit:focus { border: 1.5px solid #3182CE; background: white; }
        """)
        self.prompt_input.returnPressed.connect(self._send_chat)
        send_row.addWidget(self.prompt_input)

        self.btn_send = QPushButton("Senden ➤")
        self.btn_send.setStyleSheet(_BTN_PRIMARY)
        self.btn_send.setFixedHeight(40)
        self.btn_send.clicked.connect(self._send_chat)
        send_row.addWidget(self.btn_send)

        input_fl.addLayout(send_row)
        layout.addWidget(input_frame)

        return w

    # ── Right Panel ───────────────────────────────────────────────────────

    def _make_right_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(4, 0, 0, 0)
        layout.setSpacing(0)

        self.preview_panel = PreviewPanel()
        self.preview_panel.save_requested.connect(self._save_to_source)
        layout.addWidget(self.preview_panel)

        return w

    # ── Backend helpers ───────────────────────────────────────────────────

    @property
    def _backend(self) -> str:
        return ["ollama", "gemini_pro", "gemini_flash"][self.combo_backend.currentIndex()]

    def _on_backend_changed(self, idx: int):
        names = ["Ollama (Lokal)", "Gemini 3 Pro", "Gemini 3 Flash"]
        self.chat_area.append_bubble(f"Backend → {names[idx]}", role="system")

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

    # ── Beispiel-Prompts ──────────────────────────────────────────────────

    def _on_example_selected(self, idx: int):
        if idx == 0:
            return  # header entry, ignore
        prompt = EXAMPLE_PROMPTS[idx]
        self.prompt_input.setText(prompt)
        self.prompt_input.setFocus()
        # Reset back to header so re-selecting same prompt works
        self.combo_examples.blockSignals(True)
        self.combo_examples.setCurrentIndex(0)
        self.combo_examples.blockSignals(False)

    # ── File context ──────────────────────────────────────────────────────

    def _on_files_added(self, paths: list[str]):
        self._active_files = paths
        if paths:
            names = ", ".join(os.path.basename(p) for p in paths[:3])
            extra = f" +{len(paths)-3}" if len(paths) > 3 else ""
            self.chip_label.setText(f"📎 {names}{extra}")
            self.chip_frame.setVisible(True)

    def _clear_file_context(self):
        self._active_files = []
        self.active_context_file = None
        self.chip_frame.setVisible(False)
        self.drop_zone.list_widget.clearSelection()

    # ── Chat sending ──────────────────────────────────────────────────────

    def _send_chat(self):
        text = self.prompt_input.text().strip()
        if not text:
            return

        self.prompt_input.clear()
        self.btn_send.setEnabled(False)
        self.status_dot.setStyleSheet(
            "font-size:11px;color:#ED8936;background:transparent;border:none;"
        )

        # Check for file context
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
            # File-based chat → also update preview
            self._preview_this_response = True
        else:
            prompt = text
            # Plain chat → do NOT update preview
            self._preview_this_response = False

        self._conversation_history.append({"role": "user", "content": prompt})

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
        # Intelligent preview filter: only file/action responses go to preview
        if self._preview_this_response:
            self.preview_panel.set_content(text)
        self._conversation_history.append({"role": "assistant", "content": text})
        self._update_memory()

    def _on_ai_error(self, err: str):
        self.chat_area.append_bubble(f"⚠ Fehler: {err}", role="system")

    def _on_worker_done(self):
        self.progress_bar.setVisible(False)
        self.btn_send.setEnabled(True)
        self.status_dot.setStyleSheet(
            "font-size:11px;color:#48BB78;background:transparent;border:none;"
        )

    # ── Quick Actions (all set _preview_this_response = True) ────────────

    def _run_file_action(self, func_name: str):
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
        self.status_dot.setStyleSheet(
            "font-size:11px;color:#ED8936;background:transparent;border:none;"
        )

        label_map = {
            "summarize": "📝 Zusammenfassung",
            "explain":   "💡 Erklärung",
            "rewrite":   "✏️ Überarbeitung",
        }

        fp = targets[0]
        name = os.path.basename(fp)
        self.chat_area.append_bubble(f"{label_map.get(func_name, func_name)} von: {name}", role="user")
        self.progress_bar.setVisible(True)
        # Quick Actions always update the preview panel
        self._preview_this_response = True

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

    def _qa_summarize(self): self._run_file_action("summarize")
    def _qa_explain(self):   self._run_file_action("explain")
    def _qa_rewrite(self):   self._run_file_action("rewrite")

    def _qa_compare(self):
        import logic.ai_engine as eng

        all_paths = self.drop_zone.get_all_paths()
        if len(all_paths) < 2:
            self.chat_area.append_bubble(
                "⚠ Vergleich braucht ≥ 2 Dateien in der Drop Zone.", role="system"
            )
            return

        names = " & ".join(os.path.basename(p) for p in all_paths[:4])
        self.chat_area.append_bubble(f"⚖️ Vergleiche: {names}", role="user")
        self.progress_bar.setVisible(True)
        self.btn_send.setEnabled(False)
        self.status_dot.setStyleSheet(
            "font-size:11px;color:#ED8936;background:transparent;border:none;"
        )
        self._preview_this_response = True

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
        self.chat_area.append_bubble("💬 Neues Gespräch gestartet.", role="system")

    def _save_to_source(self, content: str):
        selected = self.drop_zone.get_selected_paths()
        if not selected:
            QMessageBox.information(
                self, "Kein Ziel",
                "Bitte eine Datei in der Drop Zone auswählen.\n"
                "Oder 'Speichern unter...' für eine neue Datei."
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
