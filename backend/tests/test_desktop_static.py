"""App de bureau — service statique du front compilé (SD_STATIC_DIR / mount_spa).

Le montage n'est utilisé que par le launcher desktop ; ces tests couvrent le
repli SPA (index.html pour les routes client) et la non-régression API
(un /api/* inconnu doit rester un 404 JSON, jamais l'index HTML).
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.spa import mount_spa


def _build_static(tmp_path):
    (tmp_path / "index.html").write_text(
        "<!doctype html><title>Delegatum</title>", encoding="utf-8"
    )
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path / "favicon.ico").write_bytes(b"\x00\x00\x01\x00")
    return tmp_path


def _client(tmp_path) -> TestClient:
    app = FastAPI()

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    assert mount_spa(app, str(tmp_path)) is True
    return TestClient(app)


def test_serves_index_and_assets(tmp_path):
    c = _client(_build_static(tmp_path))
    r = c.get("/")
    assert r.status_code == 200 and "Delegatum" in r.text
    assert r.headers["content-type"].startswith("text/html")
    r = c.get("/assets/app.js")
    assert r.status_code == 200 and "console.log" in r.text
    assert c.get("/favicon.ico").status_code == 200


def test_spa_fallback_for_client_routes(tmp_path):
    c = _client(_build_static(tmp_path))
    for route in ("/dashboard", "/login", "/elections/42"):
        r = c.get(route)
        assert r.status_code == 200, route
        assert "Delegatum" in r.text, route


def test_api_routes_not_shadowed(tmp_path):
    c = _client(_build_static(tmp_path))
    assert c.get("/api/health").json() == {"status": "ok"}
    r = c.get("/api/unknown")
    assert r.status_code == 404
    assert "text/html" not in r.headers.get("content-type", "")
    assert r.json() == {"detail": "Not Found"}


def test_disabled_without_directory(tmp_path):
    app = FastAPI()
    assert mount_spa(app, "") is False
    assert mount_spa(app, None) is False
    assert mount_spa(app, str(tmp_path / "does-not-exist")) is False
    # non monté → la racine reste un 404 FastAPI standard
    c = TestClient(app)
    assert c.get("/").status_code == 404
