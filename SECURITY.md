# Security policy

## Supported versions

Only the **latest release** (the most recent tag on `main`) receives security fixes.
There are no LTS branches. See [releases](https://github.com/LostInTheBugs/Delegatum/releases)
and [CHANGELOG.md](CHANGELOG.md).

## Reporting a vulnerability

**Preferred:** use GitHub's private vulnerability reporting —
*Security → Report a vulnerability* on this repository. It keeps the report,
the discussion and the fix private until a coordinated disclosure.

If you cannot use that feature, open a minimal issue **without exploit details**
asking for a private contact channel.

Please include:

- affected version / commit, and deployment shape (self-hosted server or desktop build);
- a reproduction (steps, payloads, screenshots) and your assessment of impact;
- which assets are at risk (minutes plaintext, safety register, accounts, availability).

**What to expect:** acknowledgement within **7 days**; for confirmed issues, a
remediation plan within **30 days**, a fix aligned with the next release where
feasible, and credit in the release notes (unless you prefer otherwise). This is
a no-budget project — there is no bug bounty, but reports are taken seriously and
thanked loudly.

## Scope

**In scope:** the code in this repository (backend, frontend, desktop packaging,
default deployment configuration), including its cryptographic claims:

- vault confidentiality (client-side AES-256-GCM, Argon2id-wrapped DEK);
- register integrity (SHA-256 journal, RFC 3161 seals, `/verify` page);
- authentication & authorization (JWT, MFA, roles, revocation);
- ballot anonymity (structural, aggregated tallies only).

**Out of scope:** misconfigured self-hosted deployments beyond the defaults we
ship; findings that require physical access to an unlocked device; social
engineering; resource exhaustion within documented rate-limit expectations.

**Please read [THREAT-MODEL.md](THREAT-MODEL.md) first.** It documents *known,
accepted limitations* (e.g. the in-database chain is recomputable by anyone with
write access — the external seals are the anchor; the app-level rate limiter is
in-memory by design). Reports that restate these limits will be answered with a
reference to that document — but if you find a way to *exploit* one of them
end-to-end (e.g. alter the register without a seal mismatch, or crack a wrapped
DEK within the documented parameters), that is exactly what we want to hear.

**Testing etiquette:** test against **your own deployment** (a local
`docker compose up` takes two minutes) — not against the shared public demo.
No automated scanning against the demo, please.

## Disclosure

We follow coordinated disclosure: fix first, release, then publish details
(release notes will credit the reporter). We will not pursue legal action for
good-faith research conducted under this policy on your own deployments.
