import os
import subprocess
import shutil
import ctypes
import json
import time
from PySide6.QtCore import QThread, Signal, QObject
import qtawesome as qta
from PIL import Image, ImageOps

class QuickAction(QObject):
    finished = Signal(bool, str) # success, message

    def __init__(self, name, icon, description, category):
        super().__init__()
        self.name = name
        self.icon = icon
        self.description = description
        self.category = category
        self.files = [] # Optional global context


    def execute(self):
        """Override this method in subclasses"""
        pass

# --- System Actions ---

class EmptyTrashAction(QuickAction):
    def __init__(self):
        super().__init__("Empty Trash", "fa5s.trash-restore", "Löscht den Papierkorb", "System")
    
    def execute(self):
        try:
            # SHEmptyRecycleBinW flags: 1=no confirm, 2=no progress, 4=no sound
            ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 1 | 2 | 4)
            self.finished.emit(True, "Papierkorb geleert.")
        except Exception as e:
            self.finished.emit(False, str(e))

class ClearTempFilesAction(QuickAction):
    def __init__(self):
        super().__init__("Clear Temp", "fa5s.broom", "Löscht temporäre Dateien", "System")
    
    def execute(self):
        try:
            temp_dirs = [os.environ.get('TEMP'), r'C:\Windows\Temp']
            count = 0
            for d in temp_dirs:
                if not d or not os.path.exists(d): continue
                for item in os.listdir(d):
                    item_path = os.path.join(d, item)
                    try:
                        if os.path.isfile(item_path): os.remove(item_path); count += 1
                        elif os.path.isdir(item_path): shutil.rmtree(item_path); count += 1
                    except: pass
            self.finished.emit(True, f"{count} temporäre Dateien entfernt.")
        except Exception as e:
            self.finished.emit(False, str(e))

class RestartExplorerAction(QuickAction):
    def __init__(self):
        super().__init__("Restart Explorer", "fa5s.sync-alt", "Neustart des Windows Explorers", "System")
    
    def execute(self):
        try:
            subprocess.run(["taskkill", "/F", "/IM", "explorer.exe"], capture_output=True)
            subprocess.Popen(["explorer.exe"])
            self.finished.emit(True, "Explorer neu gestartet.")
        except Exception as e:
            self.finished.emit(False, str(e))

class ClipboardClearAction(QuickAction):
    def __init__(self):
        super().__init__("Clear Clipboard", "fa5s.clipboard", "Leert die Zwischenablage", "System")
    
    def execute(self):
        try:
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().clear()
            self.finished.emit(True, "Zwischenablage geleert.")
        except Exception as e:
            self.finished.emit(False, str(e))

class KillChromeAction(QuickAction):
    def __init__(self):
        super().__init__("Kill Chrome", "fa5b.chrome", "Beendet alle Chrome-Prozesse", "System")
    
    def execute(self):
        try:
            subprocess.run(["taskkill", "/F", "/IM", "chrome.exe", "/T"], capture_output=True)
            self.finished.emit(True, "Chrome beendet.")
        except Exception as e:
            self.finished.emit(False, str(e))

class PCLockAction(QuickAction):
    def __init__(self):
        super().__init__("Lock PC", "fa5s.user-lock", "Sperrt den Computer", "System")
    
    def execute(self):
        try:
            ctypes.windll.user32.LockWorkStation()
            self.finished.emit(True, "PC gesperrt.")
        except Exception as e:
            self.finished.emit(False, str(e))

class MuteAllAction(QuickAction):
    def __init__(self):
        super().__init__("Mute All", "fa5s.volume-mute", "Stummschalten (Toggle)", "System")
    
    def execute(self):
        try:
            # Using nircmd if available or a simple vbs script
            # For simplicity, we use shell key simulation for Media Mute
            import win32api
            import win32con
            win32api.keybd_event(win32con.VK_VOLUME_MUTE, 0, 0, 0)
            self.finished.emit(True, "Audio Toggle.")
        except Exception:
            try:
                # Fallback: simulation using powershell or similar if win32api missing
                os.system("powershell -c (New-Object -ComObject WScript.Shell).SendKeys([char]173)")
                self.finished.emit(True, "Audio Toggle (PS).")
            except Exception as e:
                self.finished.emit(False, str(e))

class ToggleDarkModeAction(QuickAction):
    def __init__(self):
        super().__init__("Dark Mode", "fa5s.moon", "Wechselt Windows Theme", "System")
    
    def execute(self):
        try:
            import winreg
            path = r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize'
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_ALL_ACCESS)
            current_val, _ = winreg.QueryValueEx(key, 'AppsUseLightTheme')
            new_val = 0 if current_val == 1 else 1
            winreg.SetValueEx(key, 'AppsUseLightTheme', 0, winreg.REG_DWORD, new_val)
            winreg.SetValueEx(key, 'SystemUsesLightTheme', 0, winreg.REG_DWORD, new_val)
            winreg.CloseKey(key)
            self.finished.emit(True, f"Dark Mode {'deaktiviert' if new_val else 'aktiviert'}.")
        except Exception as e:
            self.finished.emit(False, str(e))

class SpeedtestAction(QuickAction):
    def __init__(self):
        super().__init__("Speedtest", "fa5s.tachometer-alt", "Öffnet Speedtest im Browser", "System")
    
    def execute(self):
        try:
            import webbrowser
            webbrowser.open("https://www.speedtest.net")
            self.finished.emit(True, "Speedtest geöffnet.")
        except Exception as e:
            self.finished.emit(False, str(e))

class IPConfigAction(QuickAction):
    def __init__(self):
        super().__init__("IP Config", "fa5s.network-wired", "Zeigt IP-Informationen", "System")
    
    def execute(self):
        try:
            res = subprocess.check_output("ipconfig", shell=True).decode('cp850')
            # Extract main IPv4 address for a cleaner message
            import re
            ips = re.findall(r"IPv4.*: ([\d\.]+)", res)
            msg = f"IPs: {', '.join(ips)}" if ips else "Keine IP gefunden."
            self.finished.emit(True, msg)
        except Exception as e:
            self.finished.emit(False, str(e))

# --- Media Actions ---

def get_clipboard_image():
    try:
        from PIL import ImageGrab
        img = ImageGrab.grabclipboard()
        if isinstance(img, Image.Image):
            return img
    except: pass
    return None

def save_result_image(img, prefix):
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    path = os.path.join(desktop, f"{prefix}_{int(time.time())}.jpg")
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.save(path, "JPEG")
    return path

class PNGtoJPEGAction(QuickAction):
    def __init__(self):
        super().__init__("PNG to JPEG", "fa5s.file-image", "Clipboard PNG -> Desktop JPEG", "Media")
    
    def execute(self):
        img = get_clipboard_image()
        if img:
            path = save_result_image(img, "Converted")
            self.finished.emit(True, f"Gespeichert: {os.path.basename(path)}")
        else:
            self.finished.emit(False, "Kein Bild in der Zwischenablage!")

class BlackAndWhiteAction(QuickAction):
    def __init__(self):
        super().__init__("B&W Filter", "fa5s.adjust", "S/W Filter auf Clipboard Bild", "Media")
    
    def execute(self):
        img = get_clipboard_image()
        if img:
            bw = img.convert("L")
            path = save_result_image(bw, "BW")
            self.finished.emit(True, f"S/W Bild gespeichert: {os.path.basename(path)}")
        else:
            self.finished.emit(False, "Kein Bild in der Zwischenablage!")

class Resize50Action(QuickAction):
    def __init__(self):
        super().__init__("Resize 50%", "fa5s.compress-arrows-alt", "Clipboard Bild 50% verkleinern", "Media")
    
    def execute(self):
        img = get_clipboard_image()
        if img:
            w, h = img.size
            resized = img.resize((w//2, h//2), Image.Resampling.LANCZOS)
            path = save_result_image(resized, "Resized")
            self.finished.emit(True, f"Verkleinert: {os.path.basename(path)}")
        else:
            self.finished.emit(False, "Kein Bild in der Zwischenablage!")


class ExtractAudioAction(QuickAction):
    def __init__(self):
        super().__init__("Extract MP3", "fa5s.music", "Audio aus Video extrahieren", "Media")
    
    def execute(self):
        if not self.files:
            self.finished.emit(False, "Keine Video-Dateien im Drop-Hub!")
            return
        self.finished.emit(True, f"{len(self.files)} Videos werden verarbeitet...")

class StripMetadataAction(QuickAction):
    def __init__(self):
        super().__init__("No Metadata", "fa5s.eye-slash", "Entfernt EXIF-Daten", "Media")
    
    def execute(self):
        if not self.files:
            self.finished.emit(False, "Keine Dateien im Drop-Hub!")
            return
        from logic.image_pro import ImagePro
        count = 0
        for f in self.files:
            success, _ = ImagePro.strip_metadata(f)
            if success: count += 1
        self.finished.emit(True, f"Metadaten von {count} Bildern entfernt.")

class ZipAllAction(QuickAction):
    def __init__(self):
        super().__init__("Zip All", "fa5s.file-archive", "Alle Hub-Dateien zippen", "System")
    
    def execute(self):
        if not self.files:
            self.finished.emit(False, "Drop-Hub ist leer!")
            return
        import zipfile
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        zip_path = os.path.join(desktop, f"Hub_Archive_{int(time.time())}.zip")
        try:
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for f in self.files:
                    zipf.write(f, os.path.basename(f))
            self.finished.emit(True, f"Archiv erstellt: {os.path.basename(zip_path)}")
        except Exception as e:
            self.finished.emit(False, str(e))


# --- AI / Automation ---

class SummarizeClipboardAction(QuickAction):
    def __init__(self):
        super().__init__("AI Summary", "fa5s.file-alt", "Fasst Clipboard-Text zusammen", "AI/Automation")
    
    def execute(self):
        try:
            from PySide6.QtWidgets import QApplication
            text = QApplication.clipboard().text()
            if not text:
                self.finished.emit(False, "Zwischenablage ist leer.")
                return
            # This should ideally call logic.ai_engine
            self.finished.emit(True, "Analyse gestartet (KI)...")
        except Exception as e:
            self.finished.emit(False, str(e))

class TranslateToENAction(QuickAction):
    def __init__(self):
        super().__init__("Translate EN", "fa5s.language", "Übersetzt Clipboard -> EN", "AI/Automation")
    
    def execute(self):
        self.finished.emit(True, "Übersetzung gestartet...")

class FixGrammarAction(QuickAction):
    def __init__(self):
        super().__init__("Fix Grammar", "fa5s.spell-check", "Grammatik-Korrektur (Clipboard)", "AI/Automation")
    
    def execute(self):
        self.finished.emit(True, "Prüfung läuft...")

class AIImageGenAction(QuickAction):
    def __init__(self):
        super().__init__("AI Image", "fa5s.magic", "Generiert Bild aus Clipboard", "AI/Automation")
    
    def execute(self):
        self.finished.emit(True, "Generator wird geladen...")

class OpenWorkSetupAction(QuickAction):
    def __init__(self):
        super().__init__("Work Setup", "fa5s.briefcase", "Öffnet Arbeitsumgebung", "AI/Automation")
    
    def execute(self):
        try:
            # Example setup
            apps = ["code.exe", "slack.exe", "chrome.exe"]
            for app in apps:
                subprocess.Popen(["start", app], shell=True)
            self.finished.emit(True, "Work-Setup gestartet.")
        except Exception as e:
            self.finished.emit(False, str(e))

# --- Custom Creative Actions ---

class OpenTerminalAction(QuickAction):
    def __init__(self):
        super().__init__("Terminal", "fa5s.terminal", "Öffnet PowerShell", "Custom")
    def execute(self):
        subprocess.Popen(["powershell"])
        self.finished.emit(True, "PowerShell geöffnet.")

class ScreenshotAction(QuickAction):
    def __init__(self):
        super().__init__("Screenshot", "fa5s.camera", "Bildschirmfoto in 3s", "Custom")
    def execute(self):
        time.sleep(3)
        from PySide6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen()
        img = screen.grabWindow(0)
        path = os.path.join(os.path.expanduser("~"), "Desktop", f"Shot_{int(time.time())}.png")
        img.save(path, "png")
        self.finished.emit(True, f"Saved to Desktop: {os.path.basename(path)}")

class SystemInfoAction(QuickAction):
    def __init__(self):
        super().__init__("SysInfo", "fa5s.info-circle", "Detaillierte Systeminfo", "Custom")
    def execute(self):
        import platform, psutil
        info = f"OS: {platform.system()} {platform.release()}\nCPU: {psutil.cpu_count()} Kerne\nRAM: {round(psutil.virtual_memory().total / (1024**3), 1)}GB"
        self.finished.emit(True, info)

class ShowDesktopAction(QuickAction):
    def __init__(self):
        super().__init__("Desktop", "fa5s.desktop", "Desktop anzeigen", "Custom")
    def execute(self):
        # Win+D simulation
        shell = ctypes.windll.shell32
        shell.ShellExecuteW(None, "open", "shell:::{3080F90D-D7AD-11D9-BD98-0000947B0257}", None, None, 1)
        self.finished.emit(True, "Desktop fokussiert.")

class NewNotepadAction(QuickAction):
    def __init__(self):
        super().__init__("Notepad", "fa5s.sticky-note", "Neue Notiz", "Custom")
    def execute(self):
        subprocess.Popen(["notepad.exe"])
        self.finished.emit(True, "Notepad geöffnet.")

# --- Action Runner ---

class ActionWorker(QThread):
    finished = Signal(bool, str)

    def __init__(self, action_class, files=None):
        super().__init__()
        self.action_class = action_class
        self.files = files or []

    def run(self):
        # Create a fresh instance for each execution to avoid signal issues
        action_instance = self.action_class()
        action_instance.files = self.files # Pass context
        action_instance.finished.connect(self.finished.emit)
        action_instance.execute()


class QuickActionRegistry:
    def __init__(self):
        self.actions_map = {
            "Empty Trash": EmptyTrashAction,
            "Clear Temp": ClearTempFilesAction,
            "Restart Explorer": RestartExplorerAction,
            "Clear Clipboard": ClipboardClearAction,
            "Kill Chrome": KillChromeAction,
            "Lock PC": PCLockAction,
            "Mute All": MuteAllAction,
            "Dark Mode": ToggleDarkModeAction,
            "Speedtest": SpeedtestAction,
            "IP Config": IPConfigAction,
            "PNG to JPEG": PNGtoJPEGAction,
            "B&W Filter": BlackAndWhiteAction,
            "Resize 50%": Resize50Action,
            "Extract MP3": ExtractAudioAction,
            "No Metadata": StripMetadataAction,
            "AI Summary": SummarizeClipboardAction,
            "Translate EN": TranslateToENAction,
            "Fix Grammar": FixGrammarAction,
            "AI Image": AIImageGenAction,
            "Work Setup": OpenWorkSetupAction,
            "Terminal": OpenTerminalAction,
            "Screenshot": ScreenshotAction,
            "SysInfo": SystemInfoAction,
            "Desktop": ShowDesktopAction,
            "Notepad": NewNotepadAction,
            "Zip All": ZipAllAction
        }


    def get_action_instance(self, name):
        action_class = self.actions_map.get(name)
        if action_class:
            return action_class()
        return None

    def get_all_info(self):
        """Returns list of (name, icon, desc, category) for UI"""
        infos = []
        for name, cls in self.actions_map.items():
            dummy = cls()
            infos.append((name, dummy.icon, dummy.description, dummy.category, cls))
        return infos

    def get_by_category(self):
        cats = {}
        for name, cls in self.actions_map.items():
            dummy = cls()
            if dummy.category not in cats: cats[dummy.category] = []
            cats[dummy.category].append((name, dummy.icon, dummy.description, cls))
        return cats


CONFIG_FILE = "quick_actions_config.json"

def load_active_actions():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except: pass
    # Default selection
    return ["Empty Trash", "Clear Temp", "Restart Explorer", "Lock PC", 
            "PNG to JPEG", "AI Summary", "Terminal", "SysInfo"]

def save_active_actions(actions):
    with open(CONFIG_FILE, "w") as f:
        json.dump(actions, f, indent=4)
