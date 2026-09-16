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

## Dokumentation

- Ausführliche Anleitungen (FR/DE/LB/EN): https://cloudfr.net/docs/delegatum/
- DSGVO: Vorlagen im Lieferumfang — [`docs/gdpr/`](docs/gdpr/README.de.md)
- Sicherheit: [SECURITY.md](SECURITY.md) · Bedrohungsmodell: [THREAT-MODEL.md](THREAT-MODEL.md)

⚠️ Experimentelle Anwendung — dient nur Demonstrationszwecken, stellt keine Rechtsberatung dar und ist nicht garantiert mit der luxemburgischen Gesetzgebung konform. Wenden Sie sich bei arbeitsrechtlichen Fragen an einen qualifizierten Fachmann oder die [Chambre des Salariés (CSL)](https://www.csl.lu).

MIT-Lizenz — Quellcode: github.com/LostInTheBugs/Delegatum
