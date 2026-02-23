import os
from PySide6.QtCore import QThread, Signal
from PIL import Image
from moviepy import VideoFileClip
from markitdown import MarkItDown

class ConversionWorker(QThread):
    progress = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, files, target_ext, output_folder, custom_name=None):
        super().__init__()
        self.files = files
        self.target_ext = target_ext.lower().strip('.')
        self.output_folder = output_folder
        self.custom_name = custom_name
        self.md = MarkItDown()

    def run(self):
        success_count = 0
        total = len(self.files)
        
        for i, file_path in enumerate(self.files):
            try:
                if not os.path.exists(file_path):
                    self.progress.emit(f"File not found: {file_path}")
                    continue

                filename = os.path.basename(file_path)
                base_name, old_ext = os.path.splitext(filename)
                
                # Determine new name
                if self.custom_name and total == 1:
                    new_filename = f"{self.custom_name}.{self.target_ext}"
                else:
                    new_filename = f"{base_name}.{self.target_ext}"
                
                target_path = os.path.join(self.output_folder, new_filename)
                
                self.progress.emit(f"[{i+1}/{total}] Processing: {filename}...")

                # Conversion Logic
                if self.target_ext in ['png', 'jpg', 'jpeg', 'webp', 'bmp', 'tiff', 'ico']:
                    self._convert_image(file_path, target_path)
                elif self.target_ext in ['mp4', 'mkv', 'mov', 'avi', 'gif']:
                    self._convert_video(file_path, target_path)
                elif self.target_ext in ['mp3', 'wav', 'ogg']:
                    self._convert_audio(file_path, target_path)
                elif self.target_ext in ['md', 'txt', 'pdf']:
                    self._convert_doc(file_path, target_path)
                else:
                    self.progress.emit(f"Unsupported target format: {self.target_ext}")
                    continue

                success_count += 1
                self.progress.emit(f"Done: {new_filename}")
            except Exception as e:
                self.progress.emit(f"Error converting {file_path}: {str(e)}")

        self.finished.emit(True, f"Successfully converted {success_count} of {total} files.")

    def _convert_image(self, src, dst):
        with Image.open(src) as img:
            if img.mode in ("RGBA", "P") and self.target_ext in ['jpg', 'jpeg']:
                img = img.convert("RGB")
            img.save(dst)

    def _convert_video(self, src, dst):
        clip = VideoFileClip(src)
        if dst.lower().endswith('.gif'):
            clip.write_gif(dst, fps=10, logger=None)
        else:
            clip.write_videofile(dst, codec="libx264", audio_codec="aac", logger=None)
        clip.close()

    def _convert_audio(self, src, dst):
        clip = VideoFileClip(src)
        clip.audio.write_audiofile(dst, logger=None)
        clip.close()

    def _convert_doc(self, src, dst):
        result = self.md.convert(src)
        if dst.lower().endswith('.md'):
            with open(dst, "w", encoding="utf-8") as f:
                f.write(result.text_content)
        elif dst.lower().endswith('.txt'):
             with open(dst, "w", encoding="utf-8") as f:
                f.write(result.text_content)
        elif dst.lower().endswith('.pdf'):
            # Basic PDF creation via PIL for images or simple text for docs
            # For real docs to PDF, we'd need more complex libs, but let's try a simple approach
            from reportlab.pdfgen import canvas
            c = canvas.Canvas(dst)
            text = result.text_content
            textobject = c.beginText(40, 750)
            for line in text.splitlines():
                textobject.textLine(line[:100]) # simple wrap
            c.drawText(textobject)
            c.save()

def get_supported_targets(file_path):
    ext = os.path.splitext(file_path)[1].lower().strip('.')
    img_exts = ['jpg', 'jpeg', 'png', 'webp', 'bmp', 'gif', 'tiff', 'ico']
    vid_exts = ['mp4', 'mkv', 'mov', 'avi', 'flv', 'wmv']
    doc_exts = ['doc', 'docx', 'pdf', 'txt', 'md', 'xlsx', 'pptx']
    
    if ext in img_exts:
        return ['PNG', 'JPG', 'WEBP', 'BMP', 'ICO', 'TIFF']
    elif ext in vid_exts:
        return ['MP4', 'MKV', 'MOV', 'AVI', 'GIF', 'MP3 (Audio)']
    elif ext in doc_exts:
        return ['PDF', 'MD', 'TXT']
    return ['PNG', 'MP4', 'PDF', 'MP3']
