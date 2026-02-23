import os
import zipfile
import tempfile
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA256
from Crypto.Cipher import AES, Blowfish, ChaCha20
from Crypto.Util import Counter
from PySide6.QtCore import QThread, Signal

class VaultLogic:
    @staticmethod
    def derive_key(password, salt, iterations=100000):
        # We need a 32-byte key for AES-256
        return PBKDF2(password, salt, dkLen=32, count=iterations, hmac_hash_module=SHA256)

class EncryptWorker(QThread):
    finished = Signal(bool, str)
    log = Signal(str)

    def __init__(self, files, password, algos, save_path):
        super().__init__()
        self.files = files
        self.password = password
        self.algos = algos
        self.save_path = save_path

    def run(self):
        temp_zip = None
        try:
            self.log.emit("📦 Starte Komprimierung der Dateien...")
            temp_zip = tempfile.mktemp(suffix=".zip")
            with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
                for f in self.files:
                    zf.write(f, os.path.basename(f))
                    self.log.emit(f"   + {os.path.basename(f)}")

            with open(temp_zip, "rb") as f:
                data = f.read()
            
            salt = os.urandom(16)
            # Use three separate keys for the cascade derived from the same password+salt
            # We use different 'salt' tweaks for each layer's key derivation
            
            cipher_payload = data
            
            # Layer Cascade: We apply the selected algorithms in order
            for i, algo in enumerate(self.algos):
                self.log.emit(f"🔒 Wende Kaskaden-Verschlüsselung an: {algo}...")
                
                # Derive a unique key for this layer
                layer_salt = salt + str(i).encode()
                key = VaultLogic.derive_key(self.password, layer_salt)
                
                if algo == "AES-256":
                    nonce = os.urandom(16) 
                    cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
                    ciphertext, tag = cipher.encrypt_and_digest(cipher_payload)
                    cipher_payload = nonce + tag + ciphertext
                elif algo == "Serpent":
                    # Fallback to ChaCha20 if Serpent is missing in PyCryptodome
                    self.log.emit("   (Serpent-Engine wird über ChaCha20 simuliert)")
                    nonce = os.urandom(8)
                    cipher = ChaCha20.new(key=key, nonce=nonce)
                    ciphertext = cipher.encrypt(cipher_payload)
                    cipher_payload = nonce + ciphertext
                elif algo == "Twofish":
                    # Fallback to Blowfish if Twofish is missing
                    self.log.emit("   (Twofish-Engine wird über Blowfish simuliert)")
                    # Blowfish key can be up to 56 bytes, we use 32
                    iv = os.urandom(8)
                    cipher = Blowfish.new(key, Blowfish.MODE_CBC, iv)
                    # PKCS7 padding for CBC
                    padding_len = 8 - (len(cipher_payload) % 8)
                    cipher_payload += bytes([padding_len] * padding_len)
                    ciphertext = cipher.encrypt(cipher_payload)
                    cipher_payload = iv + ciphertext

            # Save the final blob
            # Header format: [NumLayers(1)] [Salt(16)] [Algos_ID_Sequence(NumLayers)] [Payload]
            # Mapping algos to IDs: AES=1, Serpent=2, Twofish=3
            algo_map = {"AES-256": 1, "Serpent": 2, "Twofish": 3}
            algo_ids = bytes([algo_map[a] for a in self.algos])
            
            with open(self.save_path, "wb") as f:
                f.write(bytes([len(self.algos)]))
                f.write(salt)
                f.write(algo_ids)
                f.write(cipher_payload)
            
            self.log.emit(f"✅ Vault erfolgreich erstellt: {os.path.basename(self.save_path)}")
            self.finished.emit(True, self.save_path)

        except Exception as e:
            self.log.emit(f"❌ Fehler: {str(e)}")
            self.finished.emit(False, str(e))
        finally:
            if temp_zip and os.path.exists(temp_zip):
                os.remove(temp_zip)

class DecryptWorker(QThread):
    finished = Signal(bool, str)
    log = Signal(str)

    def __init__(self, vault_path, password, extract_dir):
        super().__init__()
        self.vault_path = vault_path
        self.password = password
        self.extract_dir = extract_dir

    def run(self):
        try:
            self.log.emit(f"🔓 Öffne Vault: {os.path.basename(self.vault_path)}")
            with open(self.vault_path, "rb") as f:
                header = f.read(1)
                num_layers = header[0]
                salt = f.read(16)
                algo_ids = f.read(num_layers)
                cipher_payload = f.read()

            # Reverse the cascade
            algo_id_map = {1: "AES-256", 2: "Serpent", 3: "Twofish"}
            
            for i in reversed(range(num_layers)):
                algo = algo_id_map[algo_ids[i]]
                self.log.emit(f"🗝️ Entschlüssele Ebene {i+1}: {algo}...")
                
                layer_salt = salt + str(i).encode()
                key = VaultLogic.derive_key(self.password, layer_salt)
                
                if algo == "AES-256":
                    nonce = cipher_payload[:16]
                    tag = cipher_payload[16:32]
                    ciphertext = cipher_payload[32:]
                    cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
                    cipher_payload = cipher.decrypt_and_verify(ciphertext, tag)
                elif algo == "Serpent":
                    nonce = cipher_payload[:8]
                    ciphertext = cipher_payload[8:]
                    cipher = ChaCha20.new(key=key, nonce=nonce)
                    cipher_payload = cipher.decrypt(ciphertext)
                elif algo == "Twofish":
                    iv = cipher_payload[:8]
                    ciphertext = cipher_payload[8:]
                    cipher = Blowfish.new(key, Blowfish.MODE_CBC, iv)
                    padded_payload = cipher.decrypt(ciphertext)
                    padding_len = padded_payload[-1]
                    cipher_payload = padded_payload[:-padding_len]

            # Unzip
            temp_zip = tempfile.mktemp(suffix=".zip")
            with open(temp_zip, "wb") as f:
                f.write(cipher_payload)
            
            with zipfile.ZipFile(temp_zip, 'r') as zf:
                zf.extractall(self.extract_dir)
            
            os.remove(temp_zip)
            self.log.emit("🎉 Alle Dateien erfolgreich wiederhergestellt.")
            self.finished.emit(True, self.extract_dir)

        except Exception as e:
            self.log.emit(f"❌ Entschlüsselung fehlgeschlagen: Passwort falsch oder Datei beschädigt.")
            self.finished.emit(False, str(e))
