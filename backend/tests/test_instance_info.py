"""Tests — GET /api/instance (R6a)

Public endpoint, sans auth → retourne profil et domaines.
"""

import pytest


def test_instance_info_no_token(client):
    """GET /api/instance sans jeton → 200, profile='dp', domains contient
    'securite_sante' et 'egalite'."""
    r = client.get("/api/instance")
    assert r.status_code == 200
    data = r.json()
    assert data["profile"] == "dp"
    assert isinstance(data["domains"], list)
    assert "securite_sante" in data["domains"]
    assert "egalite" in data["domains"]


def test_instance_info_with_token(client, org_with_users):
    """GET /api/instance avec jeton → 200 (inchangé, public)."""
    r = client.get("/api/instance", headers={
        "Authorization": f"Bearer {org_with_users['sophie_token']}"
    })
    assert r.status_code == 200
    data = r.json()
    assert data["profile"] == "dp"
