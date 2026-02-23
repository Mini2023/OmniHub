import os
import hashlib
import winreg
import psutil
import socket
import shutil
from PySide6.QtCore import QThread, Signal

class JunkCleanerWorker(QThread):
    progress = Signal(str)
    item_found = Signal(dict)
    finished = Signal(int, int)

    def __init__(self, mode="scan"):
        super().__init__()
        self.mode = mode

    def run(self):
        paths = [
            os.environ.get('TEMP'), 
            r'C:\Windows\Temp',
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp'),
            os.path.join(os.environ.get('SystemRoot', 'C:\Windows'), 'Prefetch')
        ]
        items_count = 0
        total_size = 0
        
        for path in paths:
            if not path or not os.path.exists(path): continue
            self.progress.emit(f"Checking: {path}")
            try:
                for entry in os.scandir(path):
                    try:
                        info = entry.stat()
                        total_size += info.st_size
                        items_count += 1
                        
                        if self.mode == "clean":
                            if entry.is_file():
                                os.remove(entry.path)
                            elif entry.is_dir():
                                shutil.rmtree(entry.path)
                        else:
                            self.item_found.emit({
                                'name': entry.name,
                                'path': entry.path,
                                'size': info.st_size,
                                'type': 'Junk'
                            })
                            
                    except:
                        continue
            except:
                continue

        self.progress.emit(f"Junk analysis done. {items_count} items analyzed.")
        self.finished.emit(items_count, total_size)

class ProcessManagerWorker(QThread):
    finished = Signal(list)

    def run(self):
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
            try:
                pinfo = proc.info
                mem = pinfo['memory_info'].rss / (1024 * 1024)
                processes.append({
                    'pid': pinfo['pid'],
                    'name': pinfo['name'],
                    'mem': mem,
                    'cpu': pinfo['cpu_percent']
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        processes.sort(key=lambda x: x['mem'], reverse=True)
        self.finished.emit(processes[:50])

class SpeedScanWorker(QThread):
    finished = Signal(list)

    def run(self):
        hogs = []
        whitelist = ["explorer.exe", "svchost.exe", "system idle process", "omnihub.exe", "python.exe", "taskmgr.exe"]
        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                pinfo = proc.info
                name = pinfo['name'].lower()
                mem = pinfo['memory_info'].rss / (1024 * 1024)
                
                # If > 500MB and not in whitelist
                if mem > 500 and name not in whitelist:
                    hogs.append({
                        'pid': pinfo['pid'],
                        'name': pinfo['name'],
                        'mem': mem
                    })
            except:
                continue
        self.finished.emit(hogs)

class DuplicateFinderWorker(QThread):
    progress = Signal(str)
    item_found = Signal(dict)
    finished = Signal(list)

    def __init__(self, directory):
        super().__init__()
        self.directory = directory

    def run(self):
        hashes = {}
        duplicates = []
        count = 0
        try:
            for root, dirs, files in os.walk(self.directory):
                if any(x in root for x in ["Windows", "Program Files", "AppData", ".git"]): continue
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        fsize = os.path.getsize(fp)
                        if fsize > 100 * 1024 * 1024: continue
                        
                        md5 = hashlib.md5()
                        with open(fp, 'rb') as file:
                            chunk = file.read(8192)
                            if not chunk: continue
                            md5.update(chunk)
                        file_hash = md5.hexdigest()
                        
                        if file_hash in hashes:
                            duplicates.append(fp)
                            self.item_found.emit({
                                'name': f,
                                'path': fp,
                                'size': fsize,
                                'type': 'Duplicate'
                            })
                        else:
                            hashes[file_hash] = fp
                            
                        count += 1
                        if count % 100 == 0:
                            self.progress.emit(f"Analyzed: {count} files...")
                    except:
                        continue
        except Exception as e:
            self.progress.emit(f"Error: {e}")
            
        self.progress.emit(f"Scan complete. {len(duplicates)} duplicates found.")
        self.finished.emit(duplicates)

class SecurityScannerWorker(QThread):
    progress = Signal(str)
    item_found = Signal(dict)
    finished = Signal(int)

    def run(self):
        issues = 0
        self.progress.emit("Checking open ports...")
        common_ports = [21, 23, 445, 3389]
        for port in common_ports:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.1)
            if s.connect_ex(('127.0.0.1', port)) == 0:
                self.item_found.emit({'name': f'Unsecure Port {port}', 'path': 'Network', 'size': 0, 'type': 'Security'})
                issues += 1
            s.close()
            
        self.progress.emit("Checking UAC settings...")
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System", 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(key, "EnableLUA")
            if val == 0:
                self.item_found.emit({'name': 'UAC is Disabled', 'path': 'Registry', 'size': 0, 'type': 'Security'})
                issues += 1
            winreg.CloseKey(key)
        except:
            pass

        self.progress.emit("Security scan finished.")
        self.finished.emit(issues)

class StartupManager:
    RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
    BACKUP_KEY = r"Software\OmniHub\RunDisabled"

    @staticmethod
    def get_startup_entries():
        entries = []
        locations = [
            (winreg.HKEY_CURRENT_USER, StartupManager.RUN_KEY, True),
            (winreg.HKEY_CURRENT_USER, StartupManager.BACKUP_KEY, False),
            (winreg.HKEY_LOCAL_MACHINE, StartupManager.RUN_KEY, True)
        ]
        
        for hkey, subkey, is_enabled in locations:
            try:
                key = winreg.OpenKey(hkey, subkey, 0, winreg.KEY_READ)
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        score = 0
                        v_lower = value.lower()
                        if any(x in v_lower for x in ["update", "steam", "discord", "electron", "chrome", "java"]): score += 2
                        if any(x in v_lower for x in ["tray", "helper", "agent"]): score += 1
                        impact = "Low"; 
                        if score >= 3: impact = "High"
                        elif score >= 1: impact = "Medium"
                        entries.append({'name': name, 'path': value, 'impact': impact, 'enabled': is_enabled, 'hkey': hkey, 'subkey': subkey})
                        i += 1
                    except OSError: break
                winreg.CloseKey(key)
            except: continue
        return entries

    @staticmethod
    def toggle_entry(entry):
        try:
            hkey = entry['hkey']
            old_subkey = StartupManager.RUN_KEY if entry['enabled'] else StartupManager.BACKUP_KEY
            new_subkey = StartupManager.BACKUP_KEY if entry['enabled'] else StartupManager.RUN_KEY
            old_k = winreg.OpenKey(hkey, old_subkey, 0, winreg.KEY_ALL_ACCESS)
            val, v_type = winreg.QueryValueEx(old_k, entry['name'])
            winreg.DeleteValue(old_k, entry['name'])
            winreg.CloseKey(old_k)
            try: new_k = winreg.CreateKeyEx(hkey, new_subkey, 0, winreg.KEY_ALL_ACCESS)
            except: new_k = winreg.OpenKey(hkey, new_subkey, 0, winreg.KEY_ALL_ACCESS)
            winreg.SetValueEx(new_k, entry['name'], 0, v_type, val)
            winreg.CloseKey(new_k)
            return True
        except: return False

def get_system_vitals():
    try:
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('C:').percent
        return cpu, ram, disk
    except: return 0, 0, 0
