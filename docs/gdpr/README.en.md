# GDPR — Templates for your delegation (Delegatum)

🇫🇷 [Français](README.fr.md) · 🇩🇪 [Deutsch](README.de.md) · 🇱🇺 [Lëtzebuergesch](README.lb.md)

> ⚠️ **Template, not legal advice.** Adapt it to your situation and have it validated by your counsel, your Data Protection Officer (DPO) or the [CNPD](https://cnpd.public.lu). Suggested durations are **default recommendations**. Delegatum is provided as an experimental tool (see the main README disclaimer).

A staff delegation processes employee data without a legal department — yet the GDPR applies from the very first processing operation. These templates are a concrete starting point.

## 1. Who is the data controller?

- **The Delegatum editor processes no data**: the tool is not an online service — no cloud, no telemetry, nothing sent outside.
- **The controller is your organisation** (the delegation — together with the employer where applicable, depending on who hosts the tool).
- If the tool runs on the employer's infrastructure, the technical administrator can access stored data — **except the plaintext of minutes**, which is encrypted in the browser (the server never sees it). Document this in your risk analysis (see the [threat model](../../THREAT-MODEL.md)).

## 2. Record of processing activities (Art. 30) — template

| Purpose | Data subjects | Data | Legal basis (suggested) | Retention (recommended) |
|---|---|---|---|---|
| Delegation member management | Members, deputies | Identity, contact details, photo, role, deliberations | Legal mission of the delegation (Labour Code L.412-1 ff.) | Mandate + 5 years |
| Delegation hours tracking | Members | Hours, activities, CSV exports | Legal mission (L.415-5) | 5 years |
| Meetings and minutes | Members; management (shared sections) | Attendance, agenda, minutes | Legal mission (L.415-6 ff.) | Mandate + 5 years |
| Safety & health register | Safety delegate, department heads (countersignature) | Findings, places, dates, follow-ups (may contain health/incident data) | Legal mission (L.414-14); ITM consultation | Mandate + 5 years (validate) |
| Employer consultations | Members | Opinions, exchanges, deadlines | Legal mission (L.414-3) | 5 years |
| Elections | Employees | Candidacies; aggregated results (structurally anonymous vote — no voter/choice link exists) | Legal mission (L.413-1 ff.) | Until challenges expire + 5 years |
| Virtual notice board | All staff | Delegation communications (read-only for staff) | Legitimate interest (staff information) | Mandate |
| Email notifications | Members, invitees | Addresses, contents (.eml/SMTP) | Legal mission / legitimate interest | 12 months |
| Security log and backups | Users | Technical logs, encrypted backups | Legitimate interest (security) | 30 days (rotation) |

## 3. Retention — practical guidance

- **Principle**: keep no longer than necessary. Delegation data naturally aligns with the **mandate**, plus a dispute window (recommendation: + 5 years maximum).
- **End of mandate**: export what must be handed over, then **purge** what has no remaining legal basis — data with neither use nor obligation must go.
- **Backups**: short rotation (30 days), encrypted media, stored off-site. A forgotten backup is a potential breach.
- **S&S register**: a legal register — validate its retention with your counsel/the ITM (default recommendation: mandate + 5 years).

## 4. DPIA (Art. 35) — do you need one?

**Quick screening** (document your answers — this page can be the record):

- **large-scale** processing? — a delegation is small-scale;
- **health data**? — possible via the S&S register, but not large-scale, not for care purposes;
- **systematic monitoring** of people? — no (no profiling);
- **vulnerable people**, data matching, automated decisions? — no.

→ For a typical delegation, a DPIA is **generally not required**. If your situation combines several criteria (or you are unsure), use this simplified canvas:

1. **Description** of the processing and its necessity (purposes, data, flows, people);
2. **Proportionality** (legal basis, minimisation, durations);
3. **Risks** to the people (unauthorised access, disclosure, loss);
4. **Measures**: minutes encryption, register integrity, access control, backups;
5. **Opinion** of the DPO/counsel, date, review.

## 5. What the tool does to protect data

- **Minutes are encrypted in the browser** (AES-256-GCM): the server never holds plaintext or the vault password. Keep the **recovery key** offline (safe/strongbox).
- **S&S register**: chained integrity (SHA-256) + **RFC 3161 seals**. Keep the **seal emails off the server** (board mailbox) and export the ITM dossier regularly — protection against tampering depends on those external copies.
- **No transfer** of data to the tool's editor.
- Operational recommendations: HTTPS, named accounts, MFA for administrators, encrypted backups, locked workstations.

## 6. In case of a data breach (Art. 33-34)

1. **Assess and document** (incident sheet: date, nature, data and people affected, consequences, measures taken).
2. **Notify the authority** — in Luxembourg, the **CNPD** — within **72 h** if a risk exists for people; inform the people concerned if the risk is high.
3. **Typical causes**: unauthorised access, lost laptop (desktop build), stray backup, email sent to the wrong recipient.
4. Note: since **minutes content is encrypted**, its exposure is not automatically a high-risk breach — but losing the keys is.

## Resources

- CNPD — https://cnpd.public.lu · Guichet.lu — GDPR fact sheets
- [THREAT-MODEL.md](../../THREAT-MODEL.md) — documented technical limits of the tool
- [SECURITY.md](../../SECURITY.md) — reporting a security issue
