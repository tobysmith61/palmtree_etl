# accounts/local_kms.py
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os, base64
from django.conf import settings

def generate_encrypted_dek():
    dek = os.urandom(32)

    MASTER_KEY = base64.urlsafe_b64decode(settings.LOCAL_MASTER_KEY)
    aes = AESGCM(MASTER_KEY)
    nonce = os.urandom(12)

    encrypted_dek = nonce + aes.encrypt(nonce, dek, None)
    return dek, encrypted_dek

def decrypt_dek(encrypted_dek: bytes) -> bytes:
    nonce = encrypted_dek[:12]
    ciphertext = encrypted_dek[12:]
    
    MASTER_KEY = base64.urlsafe_b64decode(settings.LOCAL_MASTER_KEY)
    aes = AESGCM(MASTER_KEY)
    return aes.decrypt(nonce, ciphertext, None)
