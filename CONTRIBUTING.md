# Contributing

Thanks for considering a contribution. Delegatum is a tool for worker
representatives — contributions that improve correctness, privacy and clarity
are the most valuable.

## Ground rules

- **No real personal data** in issues, PRs or tests: these are labour-relations
  records. Use the demo fixtures (`demo` accounts) or invented data.
- **Security issues stay private** — do not open public issues for anything
  exploitable; see [SECURITY.md](SECURITY.md).
- **Scope is frozen pending an external security review** (2026-09): maintenance
  and security fixes are merged quickly; larger features — please open an issue
  first and expect a discussion before code.
- Candidate PRs touching cryptography, authentication or the safety-register
  integrity path must update [THREAT-MODEL.md](THREAT-MODEL.md) if the security
  posture changes.

## Development setup

Backend (Python 3.11+, port 8005):

```bash
cd backend
uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload
```

Frontend (Node 20+):

```bash
cd frontend
npm install
npm run dev        # dev server on :5173, proxies /api
```

Full stack: `docker compose up -d --build` then `bash seed.sh` (demo data).

## Tests — run them before every PR

```bash
# Backend (fast subset while developing, full suite before pushing)
cd backend && .venv/bin/python -m pytest -q

# Frontend
cd frontend && npx vitest run && npm run build
```

Test conventions: backend tests live in `backend/tests/` (pytest fixtures in
`conftest.py`, helpers in `helpers.py`); frontend tests are colocated
(`*.test.ts`). New behaviour needs tests; bug fixes should come with a
regression test.

## Conventions

- **Migrations**: Alembic only, one revision file per change, **idempotent**, and
  verified against both a fresh database and an existing one. Never delete the
  data volume — migrations must preserve data.
- **Versioning**: tags `YYYY.MM.NNN`; the version appears in `VERSION`,
  `backend/app/main.py`, `frontend/package.json`, the footer and README.
  Update [CHANGELOG.md](CHANGELOG.md) in the same commit — release notes are
  generated from it.
- **Commits**: short English messages (`feat:`, `fix:`, `docs:` …), one topic per
  commit; no server names, IPs or credentials in messages or code.
- **Dependencies**: pinned versions; prefer the standard library and
  well-maintained packages; explain in the PR why a new dependency is needed.
- **UI strings**: localized ×5 (fr/en/de/pt/lb) — keep the key parity script
  happy; code comments are French (existing convention), user-facing text is not
  hardcoded.
- **Style**: TypeScript strict, Python type hints on public functions; keep the
  demo (README accounts) working — it is the first thing evaluators try.

## Pull requests

- One topic per PR; CI (backend + frontend + desktop packaging) must be green.
- Describe the user-visible change; screenshots for UI changes.
- Reference the issue if there is one; keep the diff reviewable.
