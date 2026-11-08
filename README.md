# Delegatum — Staff Delegation Application

<img src="frontend/public/delegatum-lockup.png" alt="Delegatum — Data Sovereignty" width="210">

> ⚠️ **Experimental application** — This software is provided for demonstration purposes only. It does not constitute legal advice and is not guaranteed to comply with current Luxembourg legislation. Any use is at the user's own risk. Consult a qualified professional or the [Chambre des Salariés (CSL)](https://www.csl.lu) for any question related to labour law.

Management tool for **staff delegations** in Luxembourg, inspired by the Labour Code (Art. L.412-1, L.414-2, L.414-3, L.415-5, L.416-1). *Formerly known as StaffDPapp.*

🌍 Français : [README.fr.md](README.fr.md) · Deutsch : [README.de.md](README.de.md) · Lëtzebuergesch : [README.lb.md](README.lb.md)

Current version: **2026.11.002-c1** — [See GitHub releases](https://github.com/LostInTheBugs/Delegatum/releases)

## Features

- 🏛️ **Delegation creation**: name, company, headcount → automatic computation of the number of members/deputies
- 👥 **Organisation chart**: board (president, vice-president, secretary) + members + deputies + special designations
- 📅 **Meetings**: calendar, invitations, agenda items, management invitation (J+5 minimum), stats 6 meetings/year including 3 with management, **one-click agenda templates** with the mandatory/recommended legal points (ordinary, with management, health & safety L.414-14, equality L.414-15 — each point flagged 🔴/⚪ and carrying its article reference)
- ⏱️ **My hours**: mandate hours tracking with legal weekly credit (Art. L.415-5), **CSV export** (own hours or whole delegation for the board)
- 🔐 **Authentication**: JWT, math CAPTCHA, TOTP MFA, multi-language (FR/EN/DE/PT/**LB 🇱🇺**)
- 📝 **Minutes (PV)**: sectioned minutes (internal / shared-with-management), draft & validated statuses, direction preview, **archive library with search**
- 🔐 **Vault (coffre)**: client-side AES-256-GCM encryption, Argon2id-wrapped DEK, auto-lock on inactivity — plaintext never leaves the browser, **recovery key** (one-time display, unlocks + resets password without data loss)
- 👁️ **Direction preview + PDF**: management-only projection of shared sections, decrypted in-browser, PDF export
- 📧 **Notifications**: convocations, validated-minutes alerts, member invitations, meeting reminders — configured by the delegation admin, no external infrastructure required:
  - **`.eml` files** (no SMTP access needed — download individually or as a batch)
  - **SMTP** (authenticated or not, STARTTLS/SSL, retry, test email)
  - **Standalone CLI** (`email_sender.py`, Python stdlib) — export JSON, run on any machine with SMTP access
- 🔑 **Secure sharing with management**: link `/p/<token>` + one-time reading code — the server never sees plaintext (DEK wrapped under the code, decrypted in the recipient's browser), 14-day expiry, revocation, PDF export
- 🚀 **Update banner**: notifies when a new version is released on GitHub (the app's only external link)
- 🖥️ **Dashboard vitrine**: overview widgets — annual meetings vs. legal minimum, pending consultations with overdue badge, hours this month, workforce by sex, delegation members
- 📋 **Consultations (Art. L.414-3)**: opinion/consultation tracking with the employer — 13 legal domains, 2-month decision deadline for internal rules, motivated answer required, direction emails + overdue reminders
- 📊 **Semiannual statistics (Art. L.414-3)**: workforce by sex, per semester (S1/S2), ratio visualization, history managed by the board, **PDF report export**
- 📄 **Annual activity report**: one A4 PDF per year — workforce by sex, delegation hours (L.415-5), meetings (L.415-6), consultations (L.414-3), **designated delegates** (sécurité/santé L.414-14, égalité L.414-15) with declared hours, legal credits **and logged activities**
- 🛡️ **Delegate activities**: designated delegates log their control tours, enquiries, trainings, actions and awareness sessions (L.414-14 / L.414-15) — visible to the whole delegation, counted in the annual report
- 🛡️ **Safety & health register (Art. L.414-14)**: the designated delegate records findings (date, place, description, countersignature by the department head — confirmed by the board); entries are **never deleted, only voided with a reason**; actions are chained in a **tamper-evident SHA-256 journal** (live integrity banner, register re-playable from the journal); **one-click ITM dossier** (printable PDF + integrity JSON + CSV export), **RFC 3161 timestamped seals** emailed to the board, and a **public `/verify` page** — anyone (inspectorate included) can re-check an export in the browser, no account needed
- 👥 **Mass invitations**: paste an employee list (`email;first;last`, one per line) → one invitation code per person, per-line results (created / duplicate / invalid), codes shown once with copy button — mass-invited users get plain employee accounts
- 🗑️ **Member lifecycle**: remove former members in one click (Mon organisation) — account deactivated, login blocked, history preserved; guards prevent removing yourself or the last administrator
- 📌 **Virtual notice board (Art. L.414-16)**: the delegation and the designated safety/health & equality delegates post communications visible to **all staff including plain employees** (read-only for them) — electronic display is explicitly legal
- ⚖️ **Compliance cockpit**: live status of 10 legal obligations (meetings L.415-6, plenary L.415-7, workforce stats L.414-3, consultations, validated PVs L.416-5, designations L.414-14/15, bureau names L.416-1, renewal window L.413-2, eco-financial reports L.414-5, notice board) with event logging and history
- 🗳️ **Elections (L.413-1 to L.413-6)**: full cycle — announcement poster PDF, candidacies with automatic eligibility check (L.413-4), **structurally anonymous ballot** (identity is stored in `election_ballots` with no choice; choices exist only as **aggregated per-candidate tallies** — no per-voter row exists, so nothing can be correlated, even with full database read access), d'Hondt proportional tally (≥100 employees) or relative majority, titulaires + suppléants, constitutive meeting reminder
- 🧩 **Optional feature modules**: the administrator enables/disables whole modules (elections, my hours, notice board, compliance cockpit, consultations, workforce stats, delegate activities, legal pages, contact page) in My organisation — disabled modules disappear from navigation, direct URLs redirect, and the backend refuses every route (403)
- 🏷️ **Company logo**: upload your organisation's logo (PNG/JPG/SVG, ≤ 512 KB) — displayed in the header of every page and on the login screen (type the organisation identifier shown in My organisation)
- 📇 **Contact page**: the delegation's contact details (email, phone, office hours — editable by the administrator) plus the bureau, visible to all staff
- 👤 **My profile**: photo, language, password change, MFA
- 🖥️ **Desktop application (Windows / macOS)**: self-contained builds (no server, no installer) — unzip `Delegatum-Windows.zip` (double-click `Delegatum.exe`) or `Delegatum-macOS.zip` (double-click `Delegatum.app`; first launch: right-click → Open); data stays in a `data/` folder next to the app (macOS fallback: `~/Library/Application Support/Delegatum`); exports use a native "Save as" dialog; user guides in FR/EN/DE/LB (attached to each release)

## Demo

**Test accounts** (Demo organisation, 120 employees, 5 members + 5 deputies):

| Email | Name | Status | Role |
|-------|------|--------|------|
| `sophie@demo.lu` | Sophie Muller | Member | President |
| `marc@demo.lu` | Marc Weber | Member | Vice-president |
| `laura@demo.lu` | Laura Schmit | Member | Secretary |
| `tom@demo.lu` | Tom Wagner | Member | Member |
| `emma@demo.lu` | Emma Kirsch | Member | Member |
| `paul@demo.lu` | Paul Hoffmann | Deputy | Member |
| `anna@demo.lu` | Anna Klein | Deputy | Member |
| `david@demo.lu` | David Fischer | Deputy | Member |
| `clara@demo.lu` | Clara Becker | Deputy | Member |
| `lucas@demo.lu` | Lucas Thill | Deputy | Member |

All passwords: `demo123456`

**Vault (coffre) password**: `test123456` — the vault must be unlocked in the browser to read/write encrypted minutes (WebCrypto requires HTTPS or localhost; it does not work over plain HTTP).

**Vault recovery key (démo)**: `0511-3A9D-243E-5749` — unlocks the vault and allows setting a new password if the vault password is forgotten (see "Mot de passe oublié ? → Utiliser ma clé de récupération" on the unlock screen).

**🔄 Demo auto-reset**: the demo resets itself every morning (cron, 06:30 UTC) — all account passwords return to `demo123456`, TOTP is disabled, and the vault password returns to `test123456` (encrypted minutes are preserved). Sample data (meetings, consultations, delegate activities, statistics, notices, election) is seeded via `backend/scripts/seed_demo_data.py`.

- 🎮 **Demo**: https://delegatum.cloudfr.net

## Installation and deployment

### Prerequisites

- Docker and Docker Compose
- Node.js 20+ (for frontend development)
- Python 3.11+ (for backend development)

### Local development

```bash
# Backend (port 8005 by default)
cd backend
pip install -r requirements.txt
SD_PORT=8005 python -m uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload

# Frontend (port 5173)
cd frontend
npm install
npm run dev
```

### Docker Compose

```bash
# Build and launch
docker compose up -d --build

# Seed (after volume deletion)
bash seed.sh
```

## Configuration

Copy `.env.example` to `.env` and adjust the variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `SD_PORT` | Backend listen port | `8005` |
| `SD_SECRET_KEY` | JWT signing key — **required** (the app refuses to start with an example value or a key shorter than 32 chars; docker-compose fails fast if unset) | — |
| `SD_DATABASE_URL` | Database URL (overridable — SQLite default, PostgreSQL supported) | `sqlite:///./data/staff_delegation.db` |
| `SD_INSTANCE_PROFILE` | Instance profile — restricts available modules (see below) | `dp` (all modules) |
| `SD_ACCESS_TOKEN_EXPIRE_MINUTES` | JWT token expiration | `1440` (24h) |
| `SD_INSTANCE_ADMIN_EMAILS` | Comma-separated list of email addresses authorised as instance administrators (see Updates below); leave empty for single-org admin fallback | — |
| `SD_UPDATE_NO_BUILD` | `1` on small servers to refuse building images on the host — deploy images built elsewhere | `0` (build allowed) |
| `SD_UPDATE_LOOP` | `0` to disable the background update-check loop (the admin panel's 🔎 Check still works) | `1` (loop active) |

The port can be overridden via the `SD_PORT` environment variable in all contexts (Docker, local development). All configuration files reference port 8005 by default.

## Instance profile

`SD_INSTANCE_PROFILE` restricts which modules are available at startup (the backend refuses to start with an invalid value). Valid values:

| Profile | Available modules |
|---------|-------------------|
| `dp` (default) | All modules — full staff delegation feature set |
| `sst` | Dashboard, domain activities (sécurité/santé only), hours, training/protection, safety & health register (if `sst`) |
| `egalite` | Dashboard, domain activities (égalité only), hours, training/protection |
| `sst,egalite` | Dashboard, domain activities (both), hours, training/protection, safety & health register (if `sst`) |

In a delegate-only profile (`sst`, `egalite`, or `sst,egalite`), the following modules are hidden: meetings, minutes (PV), vault, archive, elections, consultations, statistics, display, compliance, contact. The remaining features are: dashboard, activities of the profile domain(s), hours, training/protection, and safety & health register (only when `sst`).

## Security

- 🔒 **Passwords**: bcrypt directly (no unmaintained passlib), passwords over 72 bytes rejected explicitly (no silent bcrypt truncation), Argon2id for invitation codes.
- 🔑 **JWT signing key guard**: startup is refused when `SD_SECRET_KEY` is missing, shorter than 32 characters, or equal to a known example value — a deployment forgetting its `.env` cannot silently run with forgeable tokens.

## Access rights (RBAC)

- **Role × module matrix** (Settings → Access rights): `None / Read / Write` per org/role/module. The administrator always has `Write`. Button to restore defaults.
- **External accounts** (designated employee, HR, ITM, police): named accounts, mandatory expiration date, maximum read access, never meetings/minutes; invited by the administrator, president or DSS. Expiration can be changed; revocation is immediate.
- **Delegate-only instances** (`sst`, `egalite`, `sst,egalite`): the creator becomes delegate + administrator (no president); in `egalite,sst` the delegate chooses their domain; invited delegates have read-only access by default.

## Data protection (GDPR)

Ready-to-adapt templates ship with the repository — processing register (Art. 30), retention guidance and a DPIA (Art. 35) screening/canvas: [Français](docs/gdpr/README.fr.md) · [English](docs/gdpr/README.en.md) · [Deutsch](docs/gdpr/README.de.md) · [Lëtzebuergesch](docs/gdpr/README.lb.md).

## Main dependencies

- **Frontend**: React 18, TypeScript, Vite, React Router 6
- **Backend**: Python 3.11, FastAPI, SQLAlchemy, PyJWT, pyotp
- **Database**: SQLite (development), PostgreSQL (production recommended)
- **Reverse proxy**: Traefik + Let's Encrypt (HTTPS)

## Updates

Self-update for delegated administration — the app checks for new versions and, if one is available, deposits a request file; a host-side systemd service (timer + script) applies the update by pulling the release tarball, rsyncing the code, rebuilding Docker images, and running Alembic migrations. The app container **never** touches Docker — a deliberate security boundary.

### Access control

Only an **instance administrator** can request or apply updates. Instance admin is determined by:

1. **`SD_INSTANCE_ADMIN_EMAILS`** (comma-separated list) — if set, only listed emails are authorised.
2. **Fallback** — if `SD_INSTANCE_ADMIN_EMAILS` is empty, any admin user of a **single-organisation** instance is authorised. Multi-org instances without `SD_INSTANCE_ADMIN_EMAILS` block update access (403).

### Configuration

Settings are stored in the database, accessible from the **🔄 Mises à jour / Updates** link in the navigation bar (visible only to instance administrators):

- **Check cadence** (never / 1 h (default) / 6 h / 12 h / 24 h / weekly) — the background loop queries GitHub at this interval.
- **Auto-apply** — off by default; when on, the app deposits an apply request as soon as a new version is detected (never during a running job).
- **🔎 Check now** — one-shot check regardless of cadence.

### Small-server guard (`SD_UPDATE_NO_BUILD=1`)

On small hosts that cannot build Docker images, set `SD_UPDATE_NO_BUILD=1` in `.env` or as an environment variable. The updater then refuses to build — the host must deploy pre-built images (e.g. via CI) and the updater will skip the `--build` step.

### Automatic database backup

Before every update, the updater backs up every `.db` file in `DATA_DIR` to `*.db.pre-<version>`. The **three most recent** backups per database are kept; older ones are purged. To roll back, rename the `.pre-<version>` file back to the original name and restart.

### Host-side updater installation

Install the systemd timer on the host that runs the Docker deployment:

```sh
sudo cp deploy/delegatum-update.service /etc/systemd/system/
sudo cp deploy/delegatum-update.timer /etc/systemd/system/
# ⚠️ Edit User and WorkingDirectory before enabling — they MUST match your deployment
# Correct: WorkingDirectory=/opt/delegatum  (repository root where deploy/ sits)
# Wrong:   WorkingDirectory=/opt/delegatum/app
sudo systemctl daemon-reload
sudo systemctl enable --now delegatum-update.timer
python3 deploy/apply-update.py --dry-run   # sanity check — changes nothing
```

The timer checks every 5 minutes whether the app has deposited an update request; if none is pending it does nothing. Without the timer, the 🔎 Check button in the admin panel still works — the request simply waits for manual application.

## Upgrade

> **⚠️ Updating to the next version logs out all users.** Previously issued JWT tokens are invalidated: everyone will need to log in again. See [CHANGELOG.md](CHANGELOG.md) for details.

**Procedure:**

1. Backup the database: `docker compose exec backend cp /app/data/staff_delegation.db /app/data/backup-$(date +%F).db`
2. Pull the new version: `git pull`
3. Rebuild: `docker compose up -d --build`
4. Apply migrations: `docker compose exec backend alembic upgrade head`

Alembic migrations preserve existing data — **do not delete the volume**.
If the email normalization migration stops, two accounts differ only by case: the error message lists the duplicates to resolve before retrying.

## Tech stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, TypeScript, Vite |
| Backend | Python 3.11, FastAPI, SQLAlchemy |
| Database | SQLite (development), PostgreSQL (production recommended) |
| Reverse proxy | Traefik + Let's Encrypt (HTTPS) |
| Deployment | Docker Compose |

## Development cost (LLM)

This project is built through AI-assisted sessions — token usage and cost ledger: [TOKENS.md](TOKENS.md).

## Legal references

- Art. L.412-1: Number of delegates according to headcount
- Art. L.414-2/3: Special designations (health/safety, equality)
- Art. L.415-5: Weekly hours credit
- Art. L.416-1: Board (president, vice-president, secretary)

More info: [CSL - Means available to the delegation](https://www.csl.lu/en/your-rights/employees/social-dialogue/staff-delegation/means-available-to-the-delegation/)
