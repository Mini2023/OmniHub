import os
from pypdf import PdfReader, PdfWriter
import trafilatura
import img2pdf
import fitz
from PySide6.QtCore import QThread, Signal

class PDFManager:
    @staticmethod
    def merge_pdfs(input_paths, output_path):
        writer = PdfWriter()
        try:
            for path in input_paths:
                reader = PdfReader(path)
                for page in reader.pages:
                    writer.add_page(page)
            with open(output_path, "wb") as f:
                writer.write(f)
            return True, "PDFs wurden erfolgreich zusammengeführt."
        except Exception as e:
            return False, f"Fehler beim Zusammenführen: {str(e)}"

    @staticmethod
    def split_pdf(input_path, output_dir):
        try:
            reader = PdfReader(input_path)
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            count = 0
            for i, page in enumerate(reader.pages):
                writer = PdfWriter()
                writer.add_page(page)
                out_path = os.path.join(output_dir, f"{base_name}_seite_{i+1}.pdf")
                with open(out_path, "wb") as f:
                    writer.write(f)
                count += 1
            return True, f"PDF erfolgreich in {count} Einzelseiten aufgeteilt."
        except Exception as e:
            return False, f"Fehler beim Aufteilen: {str(e)}"

    @staticmethod
    def extract_text(input_path):
        try:
            doc = fitz.open(input_path)
            text = ""
            for page in doc:
                text += page.get_text()
            
            output_path = os.path.splitext(input_path)[0] + "_extracted.txt"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text)
            return True, f"Text extrahiert nach: {output_path}"
        except Exception as e:
            return False, f"Fehler bei Textextraktion: {str(e)}"

class ImageToPdfWorker(QThread):
    finished = Signal(bool, str)
    
    def __init__(self, input_paths, output_path):
        super().__init__()
        self.input_paths = input_paths
        self.output_path = output_path
        
    def run(self):
        try:
            with open(self.output_path, "wb") as f:
                f.write(img2pdf.convert(self.input_paths))
            self.finished.emit(True, f"PDF erfolgreich erstellt: {os.path.basename(self.output_path)}")
        except Exception as e:
            self.finished.emit(False, f"Fehler bei Image to PDF: {str(e)}")

class WebExtractorWorker(QThread):
    finished = Signal(str, str) # content, error
    
    def __init__(self, url):
        super().__init__()
        self.url = url
        
    def run(self):
        try:
            downloaded = trafilatura.fetch_url(self.url)
            if downloaded:
                text = trafilatura.extract(downloaded)
                if text:
                    self.finished.emit(text, "")
                    return
            self.finished.emit("", "Fehler: Konnte keinen Text von dieser URL extrahieren.")
        except Exception as e:
            self.finished.emit("", f"Fehler: {str(e)}")
