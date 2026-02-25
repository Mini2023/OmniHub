import os
import glob
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QFileDialog, QMessageBox, QLineEdit, 
                               QListWidget, QCheckBox, QTextEdit, QFrame)
from PySide6.QtCore import Qt, Signal

from logic.encryption_vault import EncryptWorker, DecryptWorker

class FileDropList(QListWidget):
    dropped = Signal(list)
    def __init__(self, placeholder, ext_filter=None, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.ext_filter = ext_filter
        self.placeholder = placeholder
        self.setStyleSheet("background-color: #F8FAFF; border: 2px dashed #B0C4DE; padding: 10px; font-size: 13pt; border-radius: 8px;")
        self.addItem(self.placeholder)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        files = []
        for u in urls:
            path = u.toLocalFile()
            if os.path.isdir(path):
                # Folder check - notify via console if possible or just skip
                print(f"Warnung: Ordner werden nicht unterstützt: {path}")
                continue
            if os.path.isfile(path):
                if not self.ext_filter or path.lower().endswith(self.ext_filter):
                    files.append(path)
        
        if files:
            if self.count() == 1 and self.item(0).text() == self.placeholder:
                self.takeItem(0)
            self.dropped.emit(files)
            event.accept()
            event.acceptProposedAction()
        else:
            event.ignore()


class EncryptionVaultTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_folder = os.path.join(os.path.expanduser("~"), "Documents", "OmniHub_Vaults")
        os.makedirs(self.main_folder, exist_ok=True)
        
        # Main Theme - Light Modern
        self.setStyleSheet("background-color: #F0F2F5; font-family: 'Segoe UI', sans-serif;")
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(25)
        
        # COLUMN 1: Encryption
        col1 = QVBoxLayout()
        lbl1 = QLabel("🔒 Encryption Hub 2.1")
        lbl1.setStyleSheet("font-size: 20px; font-weight: bold; color: #2D3748; margin-bottom: 10px;")
        col1.addWidget(lbl1)
        
        self.enc_list = FileDropList("Dateien hierher ziehen...")
        self.enc_list.dropped.connect(self.on_enc_drop)
        col1.addWidget(self.enc_list)
        
        algo_group = QLabel("Kaskaden-Algorithmen:")
        algo_group.setStyleSheet("font-weight: bold; color: #4A5568; margin-top: 10px;")
        col1.addWidget(algo_group)
        
        algo_layout = QHBoxLayout()
        self.chk_aes = QCheckBox("AES-256")
        self.chk_aes.setChecked(True)
        self.chk_serpent = QCheckBox("Serpent")
        self.chk_twofish = QCheckBox("Twofish")
        for chk in (self.chk_aes, self.chk_serpent, self.chk_twofish):
            chk.setStyleSheet("color: #2D3748; font-weight: 500;")
            algo_layout.addWidget(chk)
        col1.addLayout(algo_layout)
        
        self.enc_pwd = QLineEdit()
        self.enc_pwd.setEchoMode(QLineEdit.Password)
        self.enc_pwd.setPlaceholderText("Verschlüsselungs-Passwort setzen")
        self.enc_pwd.setStyleSheet("""
            QLineEdit {
                padding: 10px; background-color: white; border: 1px solid #CBD5E0; 
                border-radius: 6px; font-size: 13px; color: #2D3748;
            }
        """)
        col1.addWidget(self.enc_pwd)
        
        # UI Feature: Dynamic Vault Naming
        self.enc_vault_name = QLineEdit()
        self.enc_vault_name.setPlaceholderText("Name des Vaults festlegen (optional)...")
        self.enc_vault_name.setStyleSheet("""
            QLineEdit {
                padding: 10px; background-color: white; border: 1px solid #CBD5E0; 
                border-radius: 6px; font-size: 13px; color: #2D3748;
            }
        """)
        col1.addWidget(self.enc_vault_name)
        
        ebtn_layout = QHBoxLayout()
        self.btn_enc_clear = QPushButton("Clear List")
        self.btn_enc_clear.setStyleSheet("padding: 8px; background-color: #EDF2F7; border-radius: 6px;")
        
        self.btn_encrypt = QPushButton("Encrypt!")
        self.btn_encrypt.setStyleSheet("""
            QPushButton {
                background-color: #3182CE; color: white; font-weight: bold; 
                padding: 10px; border-radius: 6px; font-size: 14px;
            }
            QPushButton:hover { background-color: #2B6CB0; }
        """)
        ebtn_layout.addWidget(self.btn_enc_clear)
        ebtn_layout.addWidget(self.btn_encrypt)
        col1.addLayout(ebtn_layout)
        
        self.enc_output = QLabel("Output Area: Wartet auf Daten...")
        self.enc_output.setWordWrap(True)
        self.enc_output.setStyleSheet("color: #718096; font-size: 11pt; padding: 5px; background: rgba(255,255,255,0.5); border-radius: 4px;")
        col1.addWidget(self.enc_output)
        
        # COLUMN 2: Console & Main Folder
        col2 = QVBoxLayout()
        lbl2 = QLabel("🖥️ System & Feedback")
        lbl2.setStyleSheet("font-size: 18px; font-weight: bold; color: #2D3748;")
        col2.addWidget(lbl2)
        
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setPlaceholderText("Systemprotokoll...")
        self.console.setStyleSheet("""
            QTextEdit {
                background-color: #1A202C; color: #68D391; font-family: 'Consolas', monospace; 
                padding: 12px; border-radius: 10px; font-size: 12px;
            }
        """)
        col2.addWidget(self.console)
        
        self.btn_set_folder = QPushButton(f"Set Main Vault Folder\n{self.main_folder}")
        self.btn_set_folder.setCursor(Qt.PointingHandCursor)
        self.btn_set_folder.setStyleSheet("""
            QPushButton {
                padding: 12px; background-color: #E2E8F0; border: 1px solid #CBD5E0; 
                border-radius: 8px; font-weight: 600; color: #4A5568; margin-bottom: 5px;
            }
            QPushButton:hover { background-color: #CBD5E0; }
        """)
        col2.addWidget(self.btn_set_folder)
        
        self.btn_open_folder = QPushButton("📂 Open Main Folder")
        self.btn_open_folder.setStyleSheet("""
            QPushButton {
                padding: 8px; background-color: transparent; border: 1px solid #CBD5E0; 
                border-radius: 6px; color: #718096; font-size: 11px;
            }
            QPushButton:hover { background-color: #EDF2F7; color: #2D3748; }
        """)
        col2.addWidget(self.btn_open_folder)
        
        # COLUMN 3: Decryption
        col3 = QVBoxLayout()
        lbl3 = QLabel("🔓 Decryption Hub")
        lbl3.setStyleSheet("font-size: 20px; font-weight: bold; color: #2D3748;")
        col3.addWidget(lbl3)
        
        self.dec_list = FileDropList("Vault (.enc) hier ablegen...", ext_filter=".enc")
        self.dec_list.dropped.connect(self.on_dec_drop)
        col3.addWidget(self.dec_list, 1)
        
        self.dec_pwd = QLineEdit()
        self.dec_pwd.setEchoMode(QLineEdit.Password)
        self.dec_pwd.setPlaceholderText("Vault-Passwort eingeben")
        self.dec_pwd.setStyleSheet("""
            QLineEdit {
                padding: 10px; background-color: white; border: 1px solid #CBD5E0; 
                border-radius: 6px; font-size: 13px; color: #2D3748;
            }
        """)
        col3.addWidget(self.dec_pwd)
        
        dbtn_layout = QHBoxLayout()
        self.btn_dec_clear = QPushButton("Clear List")
        self.btn_dec_clear.setStyleSheet("padding: 8px; background-color: #EDF2F7; border-radius: 6px;")
        
        self.btn_decrypt = QPushButton("Decrypt!")
        self.btn_decrypt.setStyleSheet("""
            QPushButton {
                background-color: #38A169; color: white; font-weight: bold; 
                padding: 10px; border-radius: 6px; font-size: 14px;
            }
            QPushButton:hover { background-color: #2F855A; }
        """)
        dbtn_layout.addWidget(self.btn_dec_clear)
        dbtn_layout.addWidget(self.btn_decrypt)
        col3.addLayout(dbtn_layout)
        
        self.dec_output = QLabel("Output Area: Wartet...")
        self.dec_output.setWordWrap(True)
        self.dec_output.setStyleSheet("color: #718096; font-size: 11pt; padding: 5px; background: rgba(255,255,255,0.5); border-radius: 4px;")
        col3.addWidget(self.dec_output)
        
        expl_lbl = QLabel("📁 Detected Vaults in Main Folder:")
        expl_lbl.setStyleSheet("font-weight: bold; color: #4A5568; margin-top: 15px;")
        col3.addWidget(expl_lbl)
        
        self.vault_explorer = QListWidget()
        self.vault_explorer.setStyleSheet("""
            QListWidget {
                background-color: white; border: 1px solid #CBD5E0; 
                border-radius: 8px; font-size: 12pt; color: #2D3748;
            }
        """)
        col3.addWidget(self.vault_explorer, 1)

        # Main Structure Assembly
        main_layout.addLayout(col1, 3)
        
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.VLine)
        sep1.setStyleSheet("color: #CBD5E0;")
        main_layout.addWidget(sep1)
        
        main_layout.addLayout(col2, 4)
        
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.VLine)
        sep2.setStyleSheet("color: #CBD5E0;")
        main_layout.addWidget(sep2)
        
        main_layout.addLayout(col3, 3)

        # Connections
        self.btn_enc_clear.clicked.connect(self.clear_enc)
        self.btn_dec_clear.clicked.connect(self.clear_dec)
        self.btn_encrypt.clicked.connect(self.run_encrypt)
        self.btn_decrypt.clicked.connect(self.run_decrypt)
        self.btn_set_folder.clicked.connect(self.set_main_folder)
        self.btn_open_folder.clicked.connect(self.open_main_folder)
        self.vault_explorer.itemDoubleClicked.connect(self.load_vault_from_explorer)

        self.refresh_vaults()
        self.worker = None

    def log(self, text):
        self.console.append(text)

    def on_enc_drop(self, files):
        for f in files:
            # Check if plural
            items = [self.enc_list.item(i).text() for i in range(self.enc_list.count())]
            if f not in items:
                self.enc_list.addItem(f)

    def on_dec_drop(self, files):
        for f in files:
            items = [self.dec_list.item(i).text() for i in range(self.dec_list.count())]
            if f not in items:
                self.dec_list.addItem(f)

    def clear_enc(self):
        self.enc_list.clear()
        self.enc_list.addItem(self.enc_list.placeholder)
        
    def clear_dec(self):
        self.dec_list.clear()
        self.dec_list.addItem(self.dec_list.placeholder)

    def set_main_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Zentralen Vault-Ordner wählen", self.main_folder)
        if folder:
            self.main_folder = folder
            self.btn_set_folder.setText(f"Set Main Vault Folder\n{self.main_folder}")
            self.log(f"Zentraler Ordner geändert: {self.main_folder}")
            self.refresh_vaults()

    def open_main_folder(self):
        if self.main_folder and os.path.exists(self.main_folder):
            path = os.path.normpath(self.main_folder)
            os.startfile(path)
            self.log(f"Explorer geöffnet: {path}")
        else:
            self.log("❌ Fehler: Hauptordner existiert nicht oder ist nicht gesetzt.")

    def refresh_vaults(self):
        self.vault_explorer.clear()
        pattern = os.path.join(self.main_folder, "*.enc")
        vaults = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
        for v in vaults:
            self.vault_explorer.addItem(os.path.basename(v))
        self.log(f"Vault-Liste aktualisiert ({len(vaults)} gefunden).")

    def load_vault_from_explorer(self, item):
        path = os.path.join(self.main_folder, item.text())
        
        # Clear previous decryption selection
        self.clear_dec()
        if self.dec_list.count() == 1 and self.dec_list.item(0).text() == self.dec_list.placeholder:
            self.dec_list.takeItem(0)
        
        self.dec_list.addItem(path)
        self.log(f"📥 Vault geladen: {item.text()}")
        
        # Visual hint: scroll to pwd input
        self.dec_pwd.setFocus()

    def run_encrypt(self):
        if self.enc_list.count() == 0 or (self.enc_list.count() == 1 and self.enc_list.item(0).text() == self.enc_list.placeholder):
            QMessageBox.warning(self, "Warnung", "Bitte Dateien zum Verschlüsseln hinzufügen.")
            return
            
        pwd = self.enc_pwd.text()
        if not pwd:
            QMessageBox.warning(self, "Warnung", "Passwort erforderlich!")
            return
            
        algos = []
        if self.chk_aes.isChecked(): algos.append("AES-256")
        if self.chk_serpent.isChecked(): algos.append("Serpent")
        if self.chk_twofish.isChecked(): algos.append("Twofish")
        
        if not algos:
            QMessageBox.warning(self, "Warnung", "Bitte mindestens einen Algorithmus wählen.")
            return

        # Smart Naming Logic
        default_name = "SecureVault.enc"
        custom_name = self.enc_vault_name.text().strip()
        if custom_name:
            if not custom_name.lower().endswith(".enc"):
                custom_name += ".enc"
            default_name = custom_name
        else:
            # Fallback to first file name
            first_file = self.enc_list.item(0).text()
            default_name = os.path.splitext(os.path.basename(first_file))[0] + ".enc"

        save_path, _ = QFileDialog.getSaveFileName(self, "Vault speichern", os.path.join(self.main_folder, default_name), "Encrypted (*.enc)")
        if not save_path: return

        files = [self.enc_list.item(i).text() for i in range(self.enc_list.count())]
        
        self.worker = EncryptWorker(files, pwd, algos, save_path)
        self.worker.log.connect(self.log)
        self.worker.finished.connect(self.on_enc_finished)
        self.worker.start()

    def on_enc_finished(self, success, path):
        if success:
            self.enc_output.setText(f"Output: {path}")
            self.clear_enc()
            self.enc_pwd.clear()
            self.refresh_vaults()
            QMessageBox.information(self, "Erfolg", "Verschlüsselung abgeschlossen!")
        else:
            QMessageBox.critical(self, "Fehler", f"Verschlüsselung fehlgeschlagen:\n{path}")

    def run_decrypt(self):
        if self.dec_list.count() == 0 or (self.dec_list.count() == 1 and self.dec_list.item(0).text() == self.dec_list.placeholder):
            QMessageBox.warning(self, "Warnung", "Bitte einen Vault zum Entschlüsseln wählen.")
            return
            
        pwd = self.dec_pwd.text()
        if not pwd:
            QMessageBox.warning(self, "Warnung", "Passwort erforderlich!")
            return

        vault_path = self.dec_list.item(0).text()
        vault_name = os.path.splitext(os.path.basename(vault_path))[0]
        out_dir = os.path.join(self.main_folder, vault_name + "_decrypted")
        os.makedirs(out_dir, exist_ok=True)
        
        self.worker = DecryptWorker(vault_path, pwd, out_dir)
        self.worker.log.connect(self.log)
        self.worker.finished.connect(self.on_dec_finished)
        self.worker.start()

    def on_dec_finished(self, success, path):
        if success:
            norm_path = os.path.normpath(path)
            self.dec_output.setText(f"Entpackt nach: {norm_path}")
            self.clear_dec()
            self.dec_pwd.clear()
            
            # Auto-Open in Explorer
            if os.path.exists(norm_path):
                os.startfile(norm_path)
                self.log(f"🚀 Explorer Auto-Open: {norm_path}")

            QMessageBox.information(self, "Erfolg", f"Vault erfolgreich entschlüsselt!\nOrdner: {norm_path}")
        else:
            QMessageBox.critical(self, "Fehler", "Entschlüsselung fehlgeschlagen. Passwort prüfen.")

