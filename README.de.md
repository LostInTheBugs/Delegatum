# Delegatum — Verwaltung Ihrer Personaldelegation

🇬🇧 English version: [README.md](README.md) · 🇫🇷 [README.fr.md](README.fr.md) · 🇱🇺 [README.lb.md](README.lb.md)

Verwaltungstool für **Personal- bzw. Mitarbeiterdelegationen** in Luxemburg (Arbeitsgesetzbuch, Art. L.412-1 ff.) — gebaut, damit Ihre Daten Ihre Organisation nie verlassen.

- 🔐 **Ihre Daten bleiben bei Ihnen**: selbst gehostet (Docker) oder **Desktop-Anwendung** für Windows/macOS — keine Cloud, kein Online-Konto, keine Telemetrie.
- 🛡️ **Sicherheits-/Gesundheitsregister** (Art. L.414-14): Feststellungen mit Gegenzeichnung des Servicechefs, **verkettetes Integritätsjournal** (Stornierung mit Begründung statt Löschung), **ITM-Dossier** (druckbares PDF + Integritäts-JSON + CSV), **zeitgestempelte Siegel (RFC 3161)** und öffentliche Prüfseite — für die Arbeitsinspektion gedacht.
- 🔏 **Sitzungsprotokolle im Browser verschlüsselt** (AES-256-GCM): der Server sieht nie Klartext; Tresor per Passwort und Wiederherstellungsschlüssel geschützt.
- 👥 Sitzungen und Protokolle, Delegationsstunden (L.415-5), Konsultationen (L.414-3), Statistiken, Wahlen (strukturell anonyme Stimmabgabe), Anschlagbrett, Jahresbericht als PDF.
- 🌍 Oberfläche in fünf Sprachen: **FR / EN / DE / PT / LB**.

## Ausprobieren, installieren

- 🎮 **Demo**: https://delegatum.cloudfr.net — Testkonten im [README](README.md#demo)
- 🖥️ **Desktop-Anwendung**: [letzte Releases](https://github.com/LostInTheBugs/Delegatum/releases) (Windows-/macOS-Zips; Bedienungsanleitungen in FR/EN/DE/LB enthalten)
- 🐳 **Selbst gehostet**: `docker compose up -d --build`, dann `bash seed.sh` (Details im [README](README.md))

## Konfiguration

Kopieren Sie `.env.example` nach `.env` und passen Sie die Variablen an:

| Variable | Beschreibung | Standardwert |
|----------|-------------|-------------|
| `SD_PORT` | Backend-Listenport | `8005` |
| `SD_SECRET_KEY` | JWT-Signierschlüssel — **erforderlich** (die Anwendung verweigert den Start mit einem Beispielwert oder einem Schlüssel kürzer als 32 Zeichen; docker-compose schlägt fehl, wenn nicht gesetzt) | — |
| `SD_DATABASE_URL` | Datenbank-URL (überschreibbar — SQLite-Standard, PostgreSQL unterstützt) | `sqlite:///./data/staff_delegation.db` |
| `SD_INSTANCE_PROFILE` | Instanzprofil — beschränkt verfügbare Module | `dp` (alle Module) |
| `SD_ACCESS_TOKEN_EXPIRE_MINUTES` | JWT-Token-Verfallszeit | `1440` (24 h) |
| `SD_INSTANCE_ADMIN_EMAILS` | Kommagetrennte Liste der als Instanzadministratoren autorisierten E-Mail-Adressen (siehe Updates); leer lassen für Single-Organisation Admin-Fallback | — |
| `SD_UPDATE_NO_BUILD` | `1` auf kleinen Servern, um den Bau von Docker-Images zu verweigern — deployed vorbereitete Images | `0` (Build erlaubt) |
| `SD_UPDATE_LOOP` | `0` zur Deaktivierung der Hintergrund-Check-Schleife (der 🔎-Check in der Admin-Oberfläche funktioniert weiterhin) | `1` (Schleife aktiv) |

Der Port kann über die Umgebungsvariable `SD_PORT` in allen Kontexten (Docker, lokale Entwicklung) überschrieben werden. Alle Konfigurationsdateien referenzieren standardmäßig Port 8005.

## Instanzprofil

`SD_INSTANCE_PROFILE` beschränkt die verfügbaren Module beim Start (die Anwendung verweigert den Start mit einem ungültigen Wert). Gültige Werte:

| Profil | Verfügbare Module |
|--------|-------------------|
| `dp` (Standard) | Alle Module — vollständiges DP-Funktionsumfang |
| `sst` | Dashboard, Domänenaktivitäten (nur Sicherheit/Gesundheit), Stunden, Schulung/ Schutz, Sicherheitsregister (falls `sst`) |
| `egalite` | Dashboard, Domänenaktivitäten (nur Gleichstellung), Stunden, Schulung/ Schutz |
| `sst,egalite` | Dashboard, Domänenaktivitäten (beide), Stunden, Schulung/ Schutz, Sicherheitsregister (falls `sst`) |

Im Delegierten-nur-Profil (`sst`, `egalite` oder `sst,egalite`) sind folgende Module ausgeblendet: Sitzungen/Protokolle/Tresor/Archiv, Wahlen, Konsultationen, Statistiken, Anschlagbrett, Compliance, Kontakt. Die verbleibenden Funktionen sind: Dashboard, Aktivitäten der Profil-domain(en), Stunden, Schulung/Schutz, und Sicherheitsregister (nur wenn `sst`).

## Zugriffsrechte (RBAC)

- **Rolle × Matrix** (Einstellungen → Zugriffsrechte): `Keine / Lesen / Schreiben` pro Org/Rolle/Modul. Der Administrator hat immer `Schreiben`. Knopf « Standardwerte wiederherstellen ».
- **Externe Konten** (bestellter Arbeitnehmer, HR, ITM, Polizei): namhaftes Konto, obligatorisches Ablaufdatum, maximal Leserecht, nie Sitzungen/Protokolle; eingeladen vom Administrator, Präsidenten oder DSS; Ablaufdatum änderbar, sofortige Widerrufung.
- **Delegierten-nur-Instanzen** (`sst`, `egalite`, `sst,egalite`): der Ersteller wird Delegierter + Administrator (kein Präsident); in `egalite,sst` wählt er seine Domäne; die eingeladene Delegation hat standardmässig Leserecht.

## Aktualisierungen

Automatisches Update für delegierte Verwaltung — die Anwendung prüft auf neue Versionen und hinterlegt bei Verfügbarkeit eine Anforderungsdatei; ein systemd-Dienst (Timer + Skript) im Host wendet das Update an, indem er das Release-Tarball zieht, den Code rsynced, Docker-Images neu baut und Alembic-Migrationen ausführt. Der App-Container **berührt niemals** Docker — eine bewusste Sicherheitsgrenze.

### Zugangskontrolle

Nur ein **Instanzadministrator** kann Updates anfragen oder anwenden. Die Instanz-Admin-Zugehörigkeit wird wie folgt bestimmt:

1. **`SD_INSTANCE_ADMIN_EMAILS`** (kommagetrennte Liste) — wenn gesetzt, sind nur die aufgeführten E-Mail-Adressen autorisiert.
2. **Fallback** — wenn `SD_INSTANCE_ADMIN_EMAILS` leer ist, ist jeder Administrator-Benutzer einer **Single-Organisation**-Instanz autorisiert. Multi-Organisation-Instanzen ohne `SD_INSTANCE_ADMIN_EMAILS` sperren den Update-Zugriff (403).

### Konfiguration

Einstellungen werden in der Datenbank gespeichert und sind über den **🔄 Updates**-Link in der Navigationsleiste erreichbar (sichtbar nur für Instanzadministratoren):

- **Check-Kadenz** (nie / 1 h (Standard) / 6 h / 12 h / 24 h / wöchentlich) — die Hintergrund-Schleife prüft GitHub in diesem Intervall.
- **Auto-apply** — standardmäßig aus; wenn an, hinterlegt die Anwendung eine Apply-Anfrage, sobald eine neue Version erkannt wird (niemals während eines laufenden Jobs).
- **🔎 Jetzt prüfen** — einmaliger Check unabhängig von der Kadenz.

### Kleiner-Server-Schutz (`SD_UPDATE_NO_BUILD=1`)

Auf kleinen Hosts, die keine Docker-Images bauen können, setzen Sie `SD_UPDATE_NO_BUILD=1` in `.env` oder als Umgebungsvariable. Der Updater verweigert dann den Bau — der Host muss vorbereitete Images deployen (z. B. über CI) und der Updater überspringt den `--build`-Schritt.

### Automatische Datenbank-Sicherung

Vor jedem Update sichert der Updater jede `.db`-Datei in `DATA_DIR` nach `*.db.pre-<version>`. Die **drei neuesten** Backups pro Datenbank werden behalten; ältere werden bereinigt. Zum Rollback benennen Sie die `.pre-<version>`-Datei zurück zum Originalnamen und starten neu.

### Host-seitige Updater-Installation

Installieren Sie den systemd-Timer auf dem Host, der die Docker-Deployment ausführt:

```sh
sudo cp deploy/delegatum-update.service /etc/systemd/system/
sudo cp deploy/delegatum-update.timer /etc/systemd/system/
# ⚠️ Editieren Sie User und WorkingDirectory vor dem Aktivieren — sie MÜSSEN mit Ihrem Deployment übereinstimmen
# Korrekt: WorkingDirectory=/opt/delegatum  (Repository-Wurzel, wo deploy/ liegt)
# Falsch:  WorkingDirectory=/opt/delegatum/app
sudo systemctl daemon-reload
sudo systemctl enable --now delegatum-update.timer
python3 deploy/apply-update.py --dry-run   # Saniätstest — ändert nichts
```

Der Timer prüft alle 5 Minuten, ob die Anwendung eine Update-Anfrage hinterlegt hat; wenn keine aussteht, tut er nichts. Ohne den Timer funktioniert die 🔎-Schaltfläche im Admin-Panel weiterhin — die Anfrage wartet einfach auf die manuelle Anwendung.

## Dokumentation

- Ausführliche Anleitungen (FR/DE/LB/EN): https://cloudfr.net/docs/delegatum/
- DSGVO: Vorlagen im Lieferumfang — [`docs/gdpr/`](docs/gdpr/README.de.md)
- Sicherheit: [SECURITY.md](SECURITY.md) · Bedrohungsmodell: [THREAT-MODEL.md](THREAT-MODEL.md)

⚠️ Experimentelle Anwendung — dient nur Demonstrationszwecken, stellt keine Rechtsberatung dar und ist nicht garantiert mit der luxemburgischen Gesetzgebung konform. Wenden Sie sich bei arbeitsrechtlichen Fragen an einen qualifizierten Fachmann oder die [Chambre des Salariés (CSL)](https://www.csl.lu).

MIT-Lizenz — Quellcode: github.com/LostInTheBugs/Delegatum
