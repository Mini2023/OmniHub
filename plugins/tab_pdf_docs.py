import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QListWidget, QMessageBox)
from PySide6.QtCore import Qt

from logic.pdf_docs import PDFManager, ImageToPdfWorker

class PdfDocsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        layout = QVBoxLayout(self)
        
        lbl = QLabel("PDF Toolkit & Document Processor")
        lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #5c8cbc;")
        layout.addWidget(lbl)
        
        # Local Drop Zone text
        self.drop_lbl = QLabel("Drop Zone: PDFs und Bilder hier ablegen")
        self.drop_lbl.setAlignment(Qt.AlignCenter)
        self.drop_lbl.setStyleSheet("""
            QLabel {
                background-color: #F8FAFF;
                border: 2px dashed #B0C4DE;
                border-radius: 12px;
                padding: 20px;
                font-size: 14px;
                color: #5c8cbc;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.drop_lbl)
        
        self.file_list = QListWidget()
        self.file_list.setStyleSheet("background-color: #F8FAFF; border: 1px solid #B0C4DE; font-size: 13pt; color: #333;")
        layout.addWidget(self.file_list)
        
        btn_layout = QHBoxLayout()
        self.btn_merge = QPushButton("PDFs zusammenfügen")
        self.btn_split = QPushButton("PDF splitten")
        self.btn_img2pdf = QPushButton("Bilder zu PDF")
        self.btn_extract = QPushButton("Text extrahieren")
        self.btn_clear = QPushButton("Liste leeren")
        
        for btn in (self.btn_merge, self.btn_split, self.btn_img2pdf, self.btn_extract, self.btn_clear):
            btn.setStyleSheet("""
                QPushButton { background-color: white; border: 1px solid #B0C4DE; border-radius: 6px; padding: 6px; color: #333;}
                QPushButton:hover { background-color: #e6f2ff; }
            """)
            btn_layout.addWidget(btn)
        
        layout.addLayout(btn_layout)
        
        self.btn_merge.clicked.connect(self.action_merge)
        self.btn_split.clicked.connect(self.action_split)
        self.btn_img2pdf.clicked.connect(self.action_img2pdf)
        self.btn_extract.clicked.connect(self.action_extract)
        self.btn_clear.clicked.connect(self.file_list.clear)

        self.worker = None

    def receive_local_drop(self, files):
        for f in files:
            items = [self.file_list.item(i).text() for i in range(self.file_list.count())]
            if f not in items:
                self.file_list.addItem(f)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            files = [u.toLocalFile() for u in urls if os.path.isfile(u.toLocalFile())]
            self.receive_local_drop(files)
            event.acceptProposedAction()
        else:
            event.ignore()

    def get_selected_or_all(self):
        selected = [i.text() for i in self.file_list.selectedItems()]
        if not selected:
            selected = [self.file_list.item(i).text() for i in range(self.file_list.count())]
        return selected

    def action_merge(self):
        files = [f for f in self.get_selected_or_all() if f.lower().endswith('.pdf')]
        if len(files) < 2:
            QMessageBox.warning(self, "Warnung", "Bitte mind. 2 PDFs in die Liste ziehen!")
            return
        out = os.path.join(os.path.dirname(files[0]), "Merged_Result.pdf")
        success, msg = PDFManager.merge_pdfs(files, out)
        if success:
            QMessageBox.information(self, "Erfolg", msg)
        else:
            QMessageBox.critical(self, "Fehler", msg)

    def action_split(self):
        files = [f for f in self.get_selected_or_all() if f.lower().endswith('.pdf')]
        if not files: return
        for f in files:
            success, msg = PDFManager.split_pdf(f, os.path.dirname(f))
            if not success:
                QMessageBox.critical(self, "Fehler", msg)
        QMessageBox.information(self, "Erledigt", "Splitten der gewählten PDFs abgeschlossen.")

    def action_img2pdf(self):
        files = [f for f in self.get_selected_or_all() if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if not files:
            QMessageBox.warning(self, "Warnung", "Keine gültigen Bilder (PNG/JPG) gefunden!")
            return
        out = os.path.join(os.path.dirname(files[0]), "Images_Converted.pdf")
        self.worker = ImageToPdfWorker(files, out)
        self.worker.finished.connect(self.on_worker_done)
        self.worker.start()

    def action_extract(self):
        files = [f for f in self.get_selected_or_all() if f.lower().endswith('.pdf')]
        if not files: return
        for f in files:
            success, msg = PDFManager.extract_text(f)
            if not success:
                QMessageBox.critical(self, "Fehler", msg)
        QMessageBox.information(self, "Erledigt", "Textextraktion abgeschlossen.")

    def on_worker_done(self, success, msg):
        if success:
            QMessageBox.information(self, "Erfolg", msg)
        else:
            QMessageBox.critical(self, "Fehler", msg)
