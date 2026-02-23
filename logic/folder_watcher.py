import os
import shutil
import time
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PySide6.QtCore import QObject, Signal, QThread

CONFIG_PATH = "watchdog_config.json"

DEFAULT_SORTING_MAP = {
    "Images": ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'],
    "Documents": ['.pdf', '.docx', '.doc', '.txt', '.xlsx', '.csv', '.md', '.pptx'],
    "Videos": ['.mp4', '.mkv', '.avi', '.mov', '.wmv'],
    "Audio": ['.mp3', '.wav', '.flac', '.aac', '.m4a'],
    "Archives": ['.zip', '.rar', '.7z', '.tar', '.gz'],
    "Executables": ['.exe', '.msi', '.apk', '.bat', '.sh']
}

class SortingHandler(FileSystemEventHandler):
    def __init__(self, watch_dir, manager):
        self.watch_dir = watch_dir
        self.manager = manager

    def on_created(self, event):
        if not event.is_directory:
            self.manager.process_file(event.src_path, self.watch_dir)

    def on_moved(self, event):
        if not event.is_directory:
            if os.path.dirname(event.dest_path) == self.watch_dir:
                self.manager.process_file(event.dest_path, self.watch_dir)

class WatchdogManager(QObject):
    log_signal = Signal(str)
    status_changed = Signal(bool, str) # active, main_path

    def __init__(self):
        super().__init__()
        self.observers = {} # path -> observer
        self.undo_history = [] # list of (src, dst)
        self.load_config()

    def load_config(self):
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {
                "main_path": os.path.join(os.path.expanduser("~"), "Downloads"),
                "sub_paths": [],
                "active": False,
                "sorting_map": DEFAULT_SORTING_MAP
            }
            self.save_config()

    def save_config(self):
        with open(CONFIG_PATH, 'w') as f:
            json.dump(self.config, f, indent=4)

    def start_main(self):
        path = self.config["main_path"]
        if self.start_observer(path):
            self.config["active"] = True
            self.save_config()
            self.status_changed.emit(True, path)
            return True
        return False

    def stop_main(self):
        path = self.config["main_path"]
        self.stop_observer(path)
        self.config["active"] = False
        self.save_config()
        self.status_changed.emit(False, path)

    def start_observer(self, path):
        if path in self.observers: return True
        if not os.path.exists(path): return False
        
        handler = SortingHandler(path, self)
        observer = Observer()
        observer.schedule(handler, path, recursive=False)
        observer.start()
        self.observers[path] = observer
        self.log_signal.emit(f"Monitoring started: {path}")
        return True

    def stop_observer(self, path):
        if path in self.observers:
            self.observers[path].stop()
            self.observers[path].join()
            del self.observers[path]
            self.log_signal.emit(f"Monitoring stopped: {path}")

    def process_file(self, file_path, watch_dir):
        # Grace period for file locks
        time.sleep(1.0)
        if not os.path.exists(file_path): return

        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()
        if not ext: return

        target_folder = "Other"
        for cat, exts in self.config["sorting_map"].items():
            if ext in exts:
                target_folder = cat
                break

        target_dir = os.path.join(watch_dir, target_folder)
        os.makedirs(target_dir, exist_ok=True)

        dest = os.path.join(target_dir, filename)
        
        # Handle collision
        base, extension = os.path.splitext(filename)
        counter = 1
        while os.path.exists(dest):
            dest = os.path.join(target_dir, f"{base}_{counter}{extension}")
            counter += 1

        try:
            shutil.move(file_path, dest)
            self.undo_history.append((dest, file_path))
            self.log_signal.emit(f"Sorted: {filename} -> {target_folder}/")
        except Exception as e:
            self.log_signal.emit(f"Error: {str(e)}")

    def sort_now(self, path=None):
        target = path if path else self.config["main_path"]
        if not os.path.exists(target): return
        
        count = 0
        for item in os.listdir(target):
            item_path = os.path.join(target, item)
            if os.path.isfile(item_path):
                self.process_file(item_path, target)
                count += 1
        self.log_signal.emit(f"Manual sort finished. {count} files processed.")

    def deep_check(self):
        main = self.config["main_path"]
        self.log_signal.emit("Deep Check started...")
        count = 0
        for cat in self.config["sorting_map"].keys():
            cat_path = os.path.join(main, cat)
            if os.path.exists(cat_path):
                for f in os.listdir(cat_path):
                    f_path = os.path.join(cat_path, f)
                    if os.path.isfile(f_path):
                        ext = os.path.splitext(f)[1].lower()
                        # If ext belongs to another category, move it back to main for re-sorting
                        correct_cat = "Other"
                        for c, exts in self.config["sorting_map"].items():
                            if ext in exts:
                                correct_cat = c
                                break
                        
                        if correct_cat != cat:
                            tmp_path = os.path.join(main, f)
                            shutil.move(f_path, tmp_path)
                            self.process_file(tmp_path, main)
                            count += 1
        self.log_signal.emit(f"Deep Check finished. Corrected {count} items.")

    def undo_last(self):
        if not self.undo_history:
            self.log_signal.emit("Nothing to undo.")
            return
        
        dst, src = self.undo_history.pop()
        try:
            if os.path.exists(dst):
                shutil.move(dst, src)
                self.log_signal.emit(f"Undo: Restored {os.path.basename(src)}")
            else:
                self.log_signal.emit("Undo failed: File missing.")
        except Exception as e:
            self.log_signal.emit(f"Undo error: {e}")

    def scan_external(self, ext_path):
        if not os.path.exists(ext_path): return
        main = self.config["main_path"]
        count = 0
        for item in os.listdir(ext_path):
            ipath = os.path.join(ext_path, item)
            if os.path.isfile(ipath):
                shutil.move(ipath, os.path.join(main, item))
                count += 1
        self.log_signal.emit(f"Imported {count} files from {ext_path}")
        self.sort_now(main)
