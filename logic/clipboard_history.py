import pyperclip
from PySide6.QtCore import QThread, Signal
import time

class ClipboardManager(QThread):
    history_updated = Signal(list)

    def __init__(self, max_clips=20):
        super().__init__()
        self.max_clips = max_clips
        self.history = []
        self._running = True

    def run(self):
        last_clip = ""
        while self._running:
            try:
                current_clip = pyperclip.paste()
                if current_clip and current_clip.strip() != "" and current_clip != last_clip:
                    if current_clip in self.history:
                        self.history.remove(current_clip)
                    self.history.insert(0, current_clip)
                    if len(self.history) > self.max_clips:
                        self.history.pop()
                    self.history_updated.emit(self.history)
                    last_clip = current_clip
            except Exception:
                pass
            time.sleep(1)

    def stop(self):
        self._running = False
        self.wait()

    def clear_history(self):
        self.history.clear()
        self.history_updated.emit(self.history)
        try:
            pyperclip.copy("")
        except:
            pass
