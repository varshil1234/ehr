# utils/encryption.py
import base64
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

BLOCK_SIZE = 16
NONCE_SIZE = 12   # recommended for GCM

class AESCipher:
    def __init__(self, key: bytes):
        if not isinstance(key, (bytes, bytearray)):
            raise TypeError("Key must be bytes")
        # key must be 16/24/32 bytes for AES
        self.key = key

    def encrypt(self, raw: str) -> str:
        raw_bytes = str(raw).encode("utf-8")
        cipher = AES.new(self.key, AES.MODE_GCM, nonce=get_random_bytes(NONCE_SIZE))
        ciphertext, tag = cipher.encrypt_and_digest(raw_bytes)
        # store as: nonce + tag + ciphertext
        return base64.b64encode(cipher.nonce + tag + ciphertext).decode("utf-8")

    def decrypt(self, enc: str) -> str:
        try:
            enc_bytes = base64.b64decode(enc)
            nonce = enc_bytes[:NONCE_SIZE]
            tag = enc_bytes[NONCE_SIZE:NONCE_SIZE+16]
            ciphertext = enc_bytes[NONCE_SIZE+16:]
            cipher = AES.new(self.key, AES.MODE_GCM, nonce=nonce)
            data = cipher.decrypt_and_verify(ciphertext, tag)
            return data.decode("utf-8")
        except Exception as e:
            # bubble up so caller can handle
            raise

def is_base64(s: str) -> bool:
    try:
        # Must be a multiple of 4 in length and roundtrip successfully
        if not isinstance(s, str) or len(s.strip()) == 0 or len(s) % 4 != 0:
            return False
        return base64.b64encode(base64.b64decode(s)).decode() == s
    except Exception:
        return False