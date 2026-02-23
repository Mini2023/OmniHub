import os
from PySide6.QtCore import QThread, Signal

class DiskScannerWorker(QThread):
    progress = Signal(str)
    finished = Signal(dict, int) # stats dict, total bytes

    def __init__(self, path):
        super().__init__()
        self.path = path
        
        self.categories = {
            "Images": { "exts": ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'], "color": "#FF9999", "bytes": 0 },
            "Documents": { "exts": ['.pdf', '.docx', '.doc', '.txt', '.xlsx', '.csv', '.md', '.pptx'], "color": "#99CCFF", "bytes": 0 },
            "Videos": { "exts": ['.mp4', '.mkv', '.avi', '.mov', '.wmv'], "color": "#FFCC99", "bytes": 0 },
            "Audio": { "exts": ['.mp3', '.wav', '.flac', '.aac', '.m4a'], "color": "#CC99FF", "bytes": 0 },
            "Archives": { "exts": ['.zip', '.rar', '.7z', '.tar', '.gz'], "color": "#FFFF99", "bytes": 0 },
            "Executables/Dev": { "exts": ['.exe', '.msi', '.apk', '.py', '.js', '.html', '.css'], "color": "#99FF99", "bytes": 0 },
            "Other": { "exts": [], "color": "#E0E0E0", "bytes": 0 }
        }

    def run(self):
        total_bytes = 0
        file_count = 0
        try:
            for root, dirs, files in os.walk(self.path):
                # Speed hack: Do not dive recursively into deep system folders if they select root
                if "Windows" in root or "Program Files" in root or "AppData" in root:
                    continue
                for file in files:
                    filepath = os.path.join(root, file)
                    try:
                        size = os.path.getsize(filepath)
                        total_bytes += size
                        file_count += 1
                        
                        ext = os.path.splitext(file)[1].lower()
                        categorized = False
                        for cat, data in self.categories.items():
                            if cat != "Other" and ext in data["exts"]:
                                data["bytes"] += size
                                categorized = True
                                break
                        if not categorized:
                            self.categories["Other"]["bytes"] += size
                            
                        if file_count % 1000 == 0:
                            self.progress.emit(f"Scanned {file_count} files...")
                    except Exception:
                        pass
        except Exception as e:
            self.progress.emit(f"Scan Error occurred: {e}")
            
        self.finished.emit(self.categories, total_bytes)
