# Threat model — Delegatum

**Status:** living document (v1 — 2026-09-16). Reviews and pull requests welcome.
**Audience:** operators hosting Delegatum, delegations evaluating it, and external reviewers/auditors.

This document states *what the system protects, against whom, and where the limits are*. It is deliberately blunt about the limits: for a tool whose selling point is data sovereignty, an honest threat model is worth more than a marketing claim.

---

## 1. System at a glance

Delegatum ships in two shapes:

- **Self-hosted server** — Docker Compose (FastAPI backend + static frontend + SQLite or PostgreSQL), typically behind Traefik/nginx, optionally behind Cloudflare. Users reach it with a browser; all vault cryptography runs in the browser (WebCrypto).
- **Desktop application** — self-contained Windows/macOS build (pywebview + local backend + local SQLite). No server, no network dependency; data lives in a `data/` folder next to the app.

Both shapes store the same kinds of data:

| Data | Encrypted at rest (by the app)? | Notes |
|---|---|---|
| Minutes (PV) content | **Yes** — client-side AES-256-GCM; DEK wrapped with Argon2id from the vault password | Server/DB never holds plaintext or the vault password |
| Vault recovery envelope | Yes (DEK wrapped under the recovery key) | Recovery key = 26 chars Crockford (~130 bits), one-time display |
| Shared-minute envelopes (`/p/<token>`) | Yes (DEK wrapped under the one-time read code) | Read code = 12 chars, 30-symbol alphabet (~59 bits); 14-day link expiry |
| Safety & health register (Art. L.414-14) | **No** — stored in clear (legal register, must be readable/printable for the ITM) | Integrity is provided by the chained journal + seals, not by secrecy |
| Members, hours, meetings, consultations, notices, emails queue | No | Ordinary personal data of the delegation |
| Election choices | Structurally anonymous — only per-candidate aggregated tallies exist, no per-voter row | By construction, not by policy |

**Integrity of the safety register**: every action (create / countersign / void / seal) is appended to a SHA-256 hash-chained journal (`backend/app/services/register_chain.py`), surfaced live in the UI, and the board can **seal** the register at any time (daily automatic seal included): a seal freezes {event count, chain fingerprint} and gets a **RFC 3161 timestamp** from a public authority (DigiCert/Sectigo) plus an emailed copy to the board. The public `/verify` page re-checks an exported integrity dossier entirely in the browser.

## 2. Trust boundaries

- **The browser is trusted for cryptography.** PVs are encrypted/decrypted in the page. A cross-site scripting bug in the app would defeat vault confidentiality for the unlocked session — which is why the frontend is dependency-light (no embeds, no third-party runtime scripts). **HTTP security headers** ship in `frontend/nginx.conf`: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and a tuned **Content-Security-Policy** (`default-src 'self'`; `connect-src https://api.github.com` for the update banner; `data:`/`blob:` for previews and exports). The CSP was validated against the live app flows (login, register + ITM PDF export, `/verify`, share page, landing) with zero violations — extend the allowlist if you embed the app or add external services.
- **The server and database are NOT trusted with plaintext.** The hosting operator (who may be… the employer) can read every stored byte — except PV plaintext and the vault password, which never leave the browser.
- **The hash chain lives in the same database the app writes.** Anyone with write access to the database can recompute the entire chain. The chain alone is *tamper-evident only against outsiders without DB access*. The real anchor is external: **RFC 3161 seals and their emailed copies** (see §4 and §5).
- **The desktop build** moves the whole boundary onto one machine: the local user account and disk are the perimeter. `data/` (SQLite + `.secret_key` + email queue) is readable by anyone who can read that folder — use disk encryption on shared machines.

## 3. Adversaries

1. **External attacker on a public deployment** — credential stuffing, token theft, exploit attempts. Mitigations: HTTPS only, math CAPTCHA on auth endpoints, TOTP MFA (optional per account), bcrypt (cost 12) with an explicit 72-byte cap, JWT `jti` revocation (logout / member removal / admin revoke), rate limiting at the app layer + Traefik/Cloudflare layer.
2. **Hosting administrator / employer** (the sharpest adversary in this context — the employer frequently hosts the delegation's tool). Capabilities and limits:
   - *Can* read everything stored, including the safety register contents and metadata (who countersigned what, when people logged in).
   - *Can* recompute the SHA-256 chain after altering register rows → **but the previously emailed/timestamped seals expose the falsification window** (any seal older than the alteration will not match the recomputed chain).
   - *Can* attempt an **offline attack** on wrapped DEKs: vault password (user-chosen — quality depends on the delegation), recovery key (2^130 — infeasible), read code (30^12 ≈ 2^59 with Argon2id 64 MiB per guess — designed to be out of reach of rented GPU time).
   - *Can* roll back the whole database to an older snapshot (availability/rollback attack). Detection relies on comparing against externally kept seals and backups.
3. **Malicious or compromised member account** — role separation (member / bureau / admin), administrative guards (cannot remove yourself or the last admin), revocation of all tokens on removal, activity visible to the delegation.
4. **Insider mistakes** — backup/restore procedures, migrations that preserve data (never delete the volume), demo auto-reset confined to the demo deployment.
5. **Supply chain / dependencies** — pinned versions; cryptography limited to well-maintained libraries (PyJWT, bcrypt, argon2-cffi, WebCrypto). python-jose was removed in 2026.09.005 (CVEs ≤ 3.3.0 + irregular maintenance).

## 4. What the integrity protection actually covers (read this before trusting the green banner)

The register's integrity story is **two-layered**, and the layers have different strengths:

1. **The chained journal (in-DB)** — makes accidental edits and outside tampering detectable, gives a live, re-playable view of the register. **It does not resist an attacker who writes to the database**, since they can recompute the chain.
2. **The seals (external)** — a seal's RFC 3161 timestamp is issued by a third party and its copy is emailed to the board. A seal pins {event count, fingerprint} at a point in time. **The seals define the falsification window**: content that conflicts with an older seal is detected; content altered *after* the latest seal and *before* the next one is where residual risk lives.

**Therefore, operationally:**

- **Keep every seal email outside the server** (board mailbox, export mailbox, printed copy). A seal kept only on the same disk is not an anchor.
- **Recommended sealing cadence**: the app auto-seals **daily** when new events exist, plus one **manual seal before/after any sensitive period** (e.g., before transmitting the register to the ITM, after an incident, before an audit, at the end of a mandate). Sealing is cheap — use it.
- **Export the ITM dossier regularly** (printable PDF + integrity JSON) and archive it with the seals — the dossier re-verifies on `/verify`, and its verification logic is small, documented and re-implementable by a third party (SHA-256 chain + JSON structure + RFC 3161 via `openssl ts`).
- Honest statement: with no seal ever taken and no copy kept, the banner proves *consistency*, not *immutability*. The app should never be read as offering more than that.

## 5. Known limitations (deliberate, documented)

- **No qualified electronic signature (eIDAS) yet.** RFC 3161 proves *existence at a point in time*, not authorship. Author binding comes from accounts + journal events; a future version may add signing support.
- **Rate limiting is per-process, in-memory** (`backend/app/core/ratelimit.py`): counters reset on restart and are not shared across workers. Current default deployment runs **one** uvicorn worker; if you scale workers, front it with a shared store (e.g., Redis) or rely on the Traefik/Cloudflare limits. Treat the app-level limiter as defense-in-depth, not the primary control.
- **The safety register is not encrypted** (by design — the ITM must be able to consult it, and it is the delegation's own record). Confidentiality relies on deployment security (access control, HTTPS, disk).
- **The `/verify` page needs a browser context**; on an insecure origin the app falls back to a pure-JS SHA-256 implementation (slower). For an offline third-party check without the app, the dossier format is documented in the repository.
- **Email queue files** (`.eml`) contain addresses, links and codes: treat the `emails/` folder (or SMTP credentials) as sensitive.
- **Bus factor 1.** The project is maintained by one person. This is itself a threat (maintenance, trust, continuity). Mitigation: docs (this file, `SECURITY.md`, `CONTRIBUTING.md`), frozen feature scope, and an external review before any institutional adoption.

## 6. Operator checklist (minimum)

- [ ] HTTPS everywhere; `SD_SECRET_KEY` ≥ 32 chars, distinct per deployment.
- [ ] PostgreSQL (or a backed-up SQLite) on a host whose admin you trust *at most* to read metadata.
- [ ] Backups: encrypted, stored **off** the host, tested restores.
- [ ] Seals: automatic daily + manual at key moments; **emailed copies archived outside the server**.
- [ ] Vault & recovery key: strong vault password; recovery key stored offline (paper/safe); never emailed.
- [ ] Updates: follow releases; apply security fixes; check `SECURITY.md` for supported versions.
- [ ] Review login/MFA configuration for admin accounts; MFA enabled where possible.
- [ ] If the app is embedded or extended with external services, extend the **Content-Security-Policy** in `frontend/nginx.conf` accordingly (`default-src 'self'` + the minimal allowlist shipped; re-test the PDF export, the share flow and the logo upload after any change).

## 7. Reporting

Security issues: see [`SECURITY.md`](SECURITY.md). Please do not open a public issue for anything exploitable.
