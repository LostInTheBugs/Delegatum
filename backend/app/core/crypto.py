"""Cryptographie légère : chiffrement AES-256-GCM pour les secrets de configuration.

Tous les secrets sensibles (mot de passe SMTP, clés API) sont chiffrés
avant persistance avec une clé dérivée de SD_SECRET_KEY. Le format
stocké est : <nonce hex>(32 chars):<ciphertext hex>

Aucune donnée chiffrée ne contient de secrets en clair dans les logs,
réponses API ou exports.
"""

import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Clé brute : 32 bytes pour AES-256 (SD_SECRET_KEY est un hex string)
def _aes_key() -> bytes:
    secret = os.environ.get("SD_SECRET_KEY", "")
    if not secret:
        return b"\x00" * 32  # fallback — ne jamais arriver en prod
    # Si c'est un hex string, le décoder ; sinon le hasher
    try:
        return bytes.fromhex(secret[:64])
    except ValueError:
        import hashlib
        return hashlib.sha256(secret.encode()).digest()[:32]


def encrypt_secret(plaintext: str) -> str:
    """Chiffre *plaintext* avec AES-256-GCM et retourne le format :
    <nonce hex> (32 chars):<ciphertext+tag hex>.
    """
    key = _aes_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96 bits = norme GCM
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return f"{nonce.hex()}:{ciphertext.hex()}"


def decrypt_secret(encrypted: str) -> str:
    """Déchiffre une chaîne au format <nonce>:<ciphertext> produit par
    :func:`encrypt_secret`. Retourne le texte en clair.
    """
    key = _aes_key()
    aesgcm = AESGCM(key)
    nonce_hex, ciphertext_hex = encrypted.split(":", 1)
    nonce = bytes.fromhex(nonce_hex)
    ciphertext = bytes.fromhex(ciphertext_hex)
    return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")


def is_encrypted(value: str) -> bool:
    """Retourne True si *value* semble être au format chiffré
    (nonce_hex:ciphertext_hex, 24 chars avant le ':' en hex pur).
    """
    if ":" not in value:
        return False
    nonce_hex, _ = value.split(":", 1)
    if len(nonce_hex) != 24:  # 12 bytes * 2 hex chars = 24
        return False
    try:
        bytes.fromhex(nonce_hex)
        return True
    except ValueError:
        return False


def needs_migration(value: str | None) -> bool:
    """Retourne True si une chaîne en base est en clair et nécessite
    d'être re-chiffrée au prochain enregistrement.
    """
    if not value:
        return False
    return not is_encrypted(value)
