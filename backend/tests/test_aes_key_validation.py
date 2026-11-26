"""Tests for strict AES key validation in crypto._aes_key().

Sécurité : refuse les clés nulles et les hexadécimaux de mauvaise taille.
"""

import os
from unittest.mock import patch

import pytest

from app.core.crypto import _aes_key


@pytest.fixture(autouse=True)
def clean_env():
    """Supprime SD_SECRET_KEY avant et après chaque test."""
    os.environ.pop("SD_SECRET_KEY", None)
    yield
    os.environ.pop("SD_SECRET_KEY", None)


class TestNullKeyFallback:
    """Vérifie qu'aucune clé nulle n'est utilisée en fallback."""

    def test_absent_env_raises(self):
        """SD_SECRET_KEY absente → RuntimeError, pas de clé nulle."""
        with pytest.raises(RuntimeError, match="SD_SECRET_KEY est absente"):
            _aes_key()

    def test_empty_env_raises(self):
        """SD_SECRET_KEY vide → RuntimeError."""
        os.environ["SD_SECRET_KEY"] = ""
        with pytest.raises(RuntimeError, match="SD_SECRET_KEY est absente"):
            _aes_key()


class TestHexKeyValidation:
    """Vérifie la validation stricte des clés hexadécimales."""

    def test_64_chars_hex_valid(self):
        """Hex de 64 chars (32 bytes) → clé 32 bytes valide."""
        os.environ["SD_SECRET_KEY"] = "0123456789abcdef" * 4
        key = _aes_key()
        assert len(key) == 32
        assert key == bytes.fromhex("0123456789abcdef" * 4)

    def test_65_chars_hex_uses_32_bytes(self):
        """Hex de 65 chars → prend les 64 premiers → 32 bytes."""
        secret = "0123456789abcdef" * 4 + "f"
        os.environ["SD_SECRET_KEY"] = secret
        key = _aes_key()
        assert len(key) == 32
        assert key == bytes.fromhex("0123456789abcdef" * 4)

    def test_32_chars_hex_falls_to_hash(self):
        """Hex de 32 chars (16 bytes) — trop court pour AES, hashé en 32 bytes."""
        os.environ["SD_SECRET_KEY"] = "0123456789abcdef" * 2
        key = _aes_key()
        assert len(key) == 32  # SHA-256 → toujours 32 bytes

    def test_16_chars_hex_falls_to_hash(self):
        """Hex de 16 chars (8 bytes) → hashé en 32 bytes."""
        os.environ["SD_SECRET_KEY"] = "0123456789abcdef"
        key = _aes_key()
        assert len(key) == 32

    def test_short_hex_falls_to_hash(self):
        """Hex très court → hashé en 32 bytes."""
        os.environ["SD_SECRET_KEY"] = "deadbeef"
        key = _aes_key()
        assert len(key) == 32


class TestNonHexKey:
    """Vérifie que les clés non-hex sont hashées correctement."""

    def test_strong_nonhex_produces_32_bytes(self):
        """Clé ASCII longue → SHA-256 → 32 bytes."""
        os.environ["SD_SECRET_KEY"] = "mon_super_secret_key_très_long_et_sécurisé"
        key = _aes_key()
        assert len(key) == 32

    def test_short_nonhex_falls_to_hash(self):
        """Clé non-hex courte → SHA-256 → 32 bytes (suffisant car le
        guard config.py refuse < 32 chars au démarrage)."""
        os.environ["SD_SECRET_KEY"] = "court"
        key = _aes_key()
        assert len(key) == 32

    def test_boundary_32_chars_nonhex_works(self):
        """Clé non-hex de 32 chars exacts → SHA-256 → 32 bytes."""
        os.environ["SD_SECRET_KEY"] = "a" * 32
        key = _aes_key()
        assert len(key) == 32

    def test_deterministic(self):
        """Même clé → même résultat."""
        secret = "ma_clé_secrète_très_forte_et_sécurisée"
        os.environ["SD_SECRET_KEY"] = secret
        key1 = _aes_key()
        key2 = _aes_key()
        assert key1 == key2

    def test_different_keys_different_output(self):
        """Clés différentes → sorties différentes."""
        os.environ["SD_SECRET_KEY"] = "key_one"
        key1 = _aes_key()
        os.environ["SD_SECRET_KEY"] = "key_two"
        key2 = _aes_key()
        assert key1 != key2
