from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                QPushButton, QTextEdit, QFrame, QScrollArea, QListWidget, 
                                QListWidgetItem, QProgressBar, QDialog, QTableWidget, 
                                QTableWidgetItem, QHeaderView, QGraphicsOpacityEffect)
from PySide6.QtCore import Qt, QTimer, QSize, QRectF, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from logic.system_health import (JunkCleanerWorker, ProcessManagerWorker, 
                                DuplicateFinderWorker, SecurityScannerWorker, 
                                StartupManager, get_system_vitals, SpeedScanWorker)
import psutil
import os

class CircularGauge(QWidget):
    def __init__(self, label, value=0, color="#A2D2FF", size=85, parent=None):
        super().__init__(parent)
        self.label = label
        self.value = value
        self.color = color
        self.setFixedSize(size, size + 25)

    def set_value(self, val):
        self.value = val
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(5, 5, self.width()-10, self.width()-10)
        p.setPen(QPen(QColor("#E2E8F0"), 7))
        p.drawArc(rect, 0 * 16, 360 * 16)
        p.setPen(QPen(QColor(self.color), 7, Qt.SolidLine, Qt.RoundCap))
        span = -(self.value / 100.0) * 360 * 16
        p.drawArc(rect, 90 * 16, span)
        p.setPen(QColor("#2D3748"))
        p.setFont(QFont("Inter", 11, QFont.Bold))
        p.drawText(rect, Qt.AlignCenter, f"{int(self.value)}%")
        lbl_rect = QRectF(0, self.width()-5, self.width(), 25)
        p.setFont(QFont("Inter", 8))
        p.drawText(lbl_rect, Qt.AlignCenter, self.label)

class SpeedScanDialog(QDialog):
    def __init__(self, hogs, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Optimization Suggestions")
        self.resize(550, 400)
        self.setStyleSheet("background-color: #F8FAFC; font-family: 'Inter';")
        layout = QVBoxLayout(self)
        
        lbl = QLabel("The following non-system apps are consuming significant resources:")
        lbl.setStyleSheet("font-weight: bold; color: #4A5568;")
        layout.addWidget(lbl)
        
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["App Name", "RAM Usage", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("background: white; border-radius: 8px;")
        layout.addWidget(self.table)
        
        for p in hogs:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(p['name']))
            self.table.setItem(row, 1, QTableWidgetItem(f"{p['mem']:.0f} MB"))
            
            btn = QPushButton("Optimize")
            btn.setStyleSheet("background: #A2D2FF; color: white; border-radius: 4px; padding: 4px; font-weight: bold;")
            btn.clicked.connect(lambda chk, pid=p['pid']: self.kill_and_refresh(pid))
            self.table.setCellWidget(row, 2, btn)
            
        if not hogs:
            layout.addWidget(QLabel("No RAM-Hogs detected. Your system looks great!"))

    def kill_and_refresh(self, pid):
        try:
            p = psutil.Process(pid)
            p.terminate()
        except: pass
        self.accept()

class SystemHealthTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #F8FAFC; font-family: 'Inter';")
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 15, 20, 20)
        
        # 1. HEADER
        header_frame = QFrame()
        header_frame.setStyleSheet("background: white; border-radius: 20px; border: 1px solid #E2E8F0;")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 10, 15, 10)
        header_layout.setSpacing(10)
        
        self.score_gauge = CircularGauge("Health", 100, color="#48BB78", size=110)
        header_layout.addWidget(self.score_gauge)
        
        # Quick Status Panel (Alert Area)
        self.alert_panel = QFrame()
        self.alert_panel.setStyleSheet("background: #F7FAFC; border-radius: 12px; border: 1px solid #EDF2F7;")
        alert_layout = QVBoxLayout(self.alert_panel)
        alert_layout.setContentsMargins(15, 8, 15, 8)
        self.alert_lbl = QLabel("✅ System optimized")
        self.alert_lbl.setStyleSheet("color: #4A5568; font-size: 11px; font-weight: 600;")
        self.alert_lbl.setWordWrap(True)
        alert_layout.addWidget(self.alert_lbl)
        
        self.alert_opacity = QGraphicsOpacityEffect(self.alert_panel)
        self.alert_panel.setGraphicsEffect(self.alert_opacity)
        
        header_layout.addWidget(self.alert_panel, 1)
        
        # Mini Gauges
        self.cpu_gauge = CircularGauge("CPU", 0, color="#A2D2FF", size=75)
        self.ram_gauge = CircularGauge("RAM", 0, color="#A2D2FF", size=75)
        self.disk_gauge = CircularGauge("Disk", 0, color="#A2D2FF", size=75)
        
        header_layout.addWidget(self.cpu_gauge)
        header_layout.addWidget(self.ram_gauge)
        header_layout.addWidget(self.disk_gauge)
        
        self.main_layout.addWidget(header_frame)
        
        # 2. MIDDLE
        mid_layout = QHBoxLayout()
        mid_layout.setSpacing(15)
        
        # LEFT: Modules
        left_pane = QFrame()
        left_pane.setFixedWidth(210)
        left_pane.setStyleSheet("background: white; border-radius: 15px; border: 1px solid #E2E8F0;")
        left_vbox = QVBoxLayout(left_pane)
        left_vbox.setContentsMargins(10, 12, 10, 12)
        
        mods = [
            ("⚡ Speed Scan", self.start_speed_scan),
            ("🧹 Junk Cleaner", self.start_junk_scan),
            ("🚀 Process Manager", self.open_proc_manager),
            ("⚙️ Startup Apps", self.open_startup_manager),
            ("👯 Duplicate Scanner", self.start_dup_scan),
            ("🛡️ Security Scan", self.start_security_scan),
            ("🌪️ Full Deep Scan", self.start_full_scan)
        ]
        
        for name, func in mods:
            btn = QPushButton(name)
            btn.setStyleSheet("""
                QPushButton { text-align: left; padding: 12px; border: none; border-radius: 10px; font-weight: 600; color: #4A5568;}
                QPushButton:hover { background-color: #EDF2F7; color: #3182CE; }
            """)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(func)
            left_vbox.addWidget(btn)
        left_vbox.addStretch()
        mid_layout.addWidget(left_pane)
        
        # MIDDLE: Status Console
        self.status_console = QTextEdit()
        self.status_console.setReadOnly(True)
        self.status_console.setFixedWidth(220)
        self.status_console.setStyleSheet("""
            background: #2D3748; color: #CBD5E0; border-radius: 15px; border: 2px solid #1A202C; 
            font-family: 'Consolas', monospace; font-size: 10px; padding: 10px;
        """)
        mid_layout.addWidget(self.status_console)
        
        # RIGHT: Detailed Output
        right_frame = QFrame()
        right_frame.setStyleSheet("background: white; border-radius: 15px; border: 1px solid #E2E8F0;")
        right_vbox = QVBoxLayout(right_frame)
        right_vbox.addWidget(QLabel("<b>Diagnosis & Optimization results</b>"))
        
        self.output_list = QListWidget()
        self.output_list.setStyleSheet("border: none; background: transparent;")
        right_vbox.addWidget(self.output_list)
        
        self.action_btn = QPushButton("Resolve Selected Items")
        self.action_btn.setStyleSheet("background: #F56565; color: white; padding: 12px; border-radius: 10px; font-weight: bold;")
        self.action_btn.clicked.connect(self.perform_cleanup)
        right_vbox.addWidget(self.action_btn)
        
        mid_layout.addWidget(right_frame, 1)
        self.main_layout.addLayout(mid_layout)
        
        self.vitals_timer = QTimer()
        self.vitals_timer.timeout.connect(self.update_vitals)
        self.vitals_timer.start(2000)
        
        self.alerts = []
        self.worker = None

    def log(self, msg):
        self.status_console.append(f"> {msg}")
        self.status_console.ensureCursorVisible()

    def update_vitals(self):
        c, r, d = get_system_vitals()
        self.cpu_gauge.set_value(c)
        self.ram_gauge.set_value(r)
        self.disk_gauge.set_value(d)
        
        # Intelligent Score
        startups = [e for e in StartupManager.get_startup_entries() if e['enabled'] and e['impact'] == "High"]
        score = 100 - (c*0.1 + r*0.15 + len(startups)*4)
        self.score_gauge.set_value(max(10, min(100, score)))
        
        # Update Alerts based on internal data
        new_alerts = []
        if len(startups) > 0: new_alerts.append(f"⚠️ {len(startups)} High-Impact Startups")
        if r > 85: new_alerts.append("⚠️ RAM usage critical")
        
        if not new_alerts and not self.alerts:
            self.update_header_alert("✅ System optimized")
        elif new_alerts != self.alerts:
            self.alerts = new_alerts
            self.update_header_alert("\n".join(self.alerts))

    def update_header_alert(self, text):
        if self.alert_lbl.text() == text: return
        
        self.anim = QPropertyAnimation(self.alert_opacity, b"opacity")
        self.anim.setDuration(300)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.setEasingCurve(QEasingCurve.InOutQuad)
        
        def swap():
            self.alert_lbl.setText(text)
            a2 = QPropertyAnimation(self.alert_opacity, b"opacity")
            a2.setDuration(400)
            a2.setStartValue(0.0)
            a2.setEndValue(1.0)
            a2.start()
            
        self.anim.finished.connect(swap)
        self.anim.start()

    def start_speed_scan(self):
        self.log("Running Speed Scan (RAM Intelligence)...")
        self.worker = SpeedScanWorker()
        self.worker.finished.connect(self.show_speed_results)
        self.worker.start()

    def show_speed_results(self, hogs):
        dlg = SpeedScanDialog(hogs, self)
        dlg.exec()
        self.log(f"Speed scan done. Found {len(hogs)} hogs.")

    def start_junk_scan(self):
        self.log("Deep scan for system junk...")
        self.output_list.clear()
        self.worker = JunkCleanerWorker(mode="scan")
        self.worker.progress.connect(self.log)
        self.worker.item_found.connect(self.add_output_item)
        self.worker.finished.connect(lambda c, s: self.alerts.append(f"⚠️ {s/(1024*1024):.1f} MB Junk found") if s > 0 else None)
        self.worker.start()

    def start_dup_scan(self):
        self.log("Scanning Downloads for duplicates...")
        self.output_list.clear()
        path = os.path.join(os.path.expanduser("~"), "Downloads")
        self.worker = DuplicateFinderWorker(path)
        self.worker.progress.connect(self.log)
        self.worker.item_found.connect(self.add_output_item)
        self.worker.start()

    def start_security_scan(self):
        self.log("Security analysis...")
        self.output_list.clear()
        self.worker = SecurityScannerWorker()
        self.worker.progress.connect(self.log)
        self.worker.item_found.connect(self.add_output_item)
        self.worker.start()

    def start_full_scan(self):
        self.start_junk_scan()

    def add_output_item(self, info):
        size = info['size'] / (1024*1024)
        item = QListWidgetItem(f"[{info['type']}] {info['name']} ({size:.1f} MB)")
        item.setData(Qt.UserRole, info['path'])
        self.output_list.addItem(item)

    def perform_cleanup(self):
        import shutil
        self.log("Resolving items...")
        for i in range(self.output_list.count()):
            item = self.output_list.item(i)
            path = item.data(Qt.UserRole)
            try:
                if os.path.isfile(path): os.remove(path)
                elif os.path.isdir(path): shutil.rmtree(path)
            except: pass
        self.output_list.clear()
        self.log("Optimization complete.")

    def open_proc_manager(self):
        from PySide6.QtWidgets import QDialog, QTableWidget, QTableWidgetItem, QHeaderView
        from logic.system_health import ProcessManagerWorker
        
        class ProcDlg(QDialog):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setWindowTitle("Global Process View")
                self.resize(600, 500)
                l = QVBoxLayout(self)
                self.t = QTableWidget(0, 3)
                self.t.setHorizontalHeaderLabels(["PID", "Name", "Memory"])
                self.t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
                l.addWidget(self.t)
                self.w = ProcessManagerWorker()
                self.w.finished.connect(self.fill)
                self.w.start()
            def fill(self, data):
                for p in data:
                    r = self.t.rowCount(); self.t.insertRow(r)
                    self.t.setItem(r, 0, QTableWidgetItem(str(p['pid'])))
                    self.t.setItem(r, 1, QTableWidgetItem(p['name']))
                    self.t.setItem(r, 2, QTableWidgetItem(f"{p['mem']:.1f} MB"))
        
        ProcDlg(self).exec()

    def open_startup_manager(self):
        from logic.system_health import StartupManager
        class StartupDlg(QDialog):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setWindowTitle("Startup Control")
                self.resize(600, 450)
                l = QVBoxLayout(self)
                self.t = QTableWidget(0, 3)
                self.t.setHorizontalHeaderLabels(["App", "Impact", "Action"])
                self.t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
                l.addWidget(self.t)
                self.refresh()
            def refresh(self):
                self.t.setRowCount(0)
                entries = StartupManager.get_startup_entries()
                for e in entries:
                    r = self.t.rowCount(); self.t.insertRow(r)
                    self.t.setItem(r, 0, QTableWidgetItem(e['name']))
                    impact = QTableWidgetItem(e['impact'])
                    impact.setForeground(QColor("#C53030") if e['impact'] == "High" else QColor("#2D3748"))
                    self.t.setItem(r, 1, impact)
                    b = QPushButton("Disable" if e['enabled'] else "Enable")
                    b.clicked.connect(lambda ch, item=e: self.toggle(item))
                    self.t.setCellWidget(r, 2, b)
            def toggle(self, entry):
                StartupManager.toggle_entry(entry)
                self.refresh()
        StartupDlg(self).exec()
