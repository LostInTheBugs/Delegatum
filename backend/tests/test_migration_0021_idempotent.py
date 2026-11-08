"""Idempotent upgrade of migration 0021 (RBAC).

Simulates the real failure scenario:
1. Fresh DB → alembic upgrade to 0020 (last migration before 0021)
2. Simulate startup: Base.metadata.create_all() creates role_permissions + all tables
3. alembic upgrade head → must succeed (0021 is idempotent)
4. alembic current → head
5. Re-run upgrade head again → must still succeed
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Ensure the backend directory is on sys.path so `from app.database import Base` works.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest


def test_migration_0021_idempotent():
    """Upgrade 0021 after create_all must not raise duplicate-column/table."""
    # ── Create fresh DB ──────────────────────────────────────────────────
    fd, path = tempfile.mkstemp(suffix=".db", prefix="sd_migration_0021_")
    os.close(fd)

    parent = Path(__file__).resolve().parent.parent  # backend/
    try:
        db_url = f"sqlite:///{path}"
        env = os.environ.copy()
        env["SD_DATABASE_URL"] = db_url

        # Step 1: upgrade to 0020 (migration before 0021)
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "20260801_0020_self_update_config"],
            cwd=str(parent), env=env, capture_output=True, text=True,
        )
        assert result.returncode == 0, f"upgrade 0020 failed: {result.stderr}"

        # Step 2: simulate startup — create_all creates all tables including role_permissions
        import sqlalchemy as sa
        from app.core.database import Base
        engine = sa.create_engine(db_url)
        Base.metadata.create_all(engine)

        # Step 3: upgrade head (0021) — must not crash on duplicate column/table
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=str(parent), env=env, capture_output=True, text=True,
        )
        assert result.returncode == 0, f"upgrade head failed: {result.stderr}"

        # Step 4: check current revision is head
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "current"],
            cwd=str(parent), env=env, capture_output=True, text=True,
        )
        assert result.returncode == 0, f"current failed: {result.stderr}"
        assert "20261108_0021_rbac (head)" in result.stdout, f"expected head in: {result.stdout}"

        # Step 5: re-run upgrade head — idempotency must hold
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=str(parent), env=env, capture_output=True, text=True,
        )
        assert result.returncode == 0, f"second upgrade head failed: {result.stderr}"

    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
