"""Tests de la garde SD_SECRET_KEY (jetons JWT forgeables si absente)."""

import pytest

from app.core import config
from app.core.config import Settings, assert_secret_key_is_set


@pytest.fixture
def _restore_get_settings(monkeypatch):
    """Restaure get_settings après chaque test (empêche la fuite)."""
    yield


def test_guard_refuses_example_key(_restore_get_settings, monkeypatch):
    monkeypatch.setattr(
        config, "get_settings",
        lambda: Settings(secret_key="change-me-in-production")
    )
    with pytest.raises(RuntimeError, match="SD_SECRET_KEY"):
        assert_secret_key_is_set()


def test_guard_refuses_old_default_key(_restore_get_settings, monkeypatch):
    monkeypatch.setattr(
        config, "get_settings",
        lambda: Settings(
            secret_key="change-me-in-production-use-openssl-rand-hex-32"
        )
    )
    with pytest.raises(RuntimeError, match="SD_SECRET_KEY"):
        assert_secret_key_is_set()


def test_guard_refuses_short_key(_restore_get_settings, monkeypatch):
    monkeypatch.setattr(
        config, "get_settings",
        lambda: Settings(secret_key="short")
    )
    with pytest.raises(RuntimeError, match="SD_SECRET_KEY"):
        assert_secret_key_is_set()


def test_guard_accepts_strong_key(_restore_get_settings, monkeypatch):
    monkeypatch.setattr(
        config, "get_settings",
        lambda: Settings(secret_key="a" * 32)
    )
    assert_secret_key_is_set()  # ne doit pas lever