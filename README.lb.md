# Delegatum — Gestion vun Ärer Personaldelegatioun

🇬🇧 English version: [README.md](README.md) · 🇫🇷 [README.fr.md](README.fr.md) · 🇩🇪 [README.de.md](README.de.md)

Verwaltungsinstrument fir **Personaldelegatiounen** zu Lëtzebuerg (Code du travail, Art. L.412-1 f.) — gebaut, fir datt Är Donnéeën Är Organisatioun ni verloossen.

- 🔐 **Är Donnéeën bleiwen bei Iech**: selbst gehost (Docker) oder **Desktop-App** fir Windows/macOS — keng Cloud, keen Online-Kont, keng Telemetrie.
- 🛡️ **Sécherheets-/Gesondheetsregëster** (Art. L.414-14): Feststellunge mat Géigezeechnung vum Servicechef, **verkettegt Integritéitsjournal** (Annulatioun mat Grond amplaz Läschung), **ITM-Dossier** (druckbar PDF + Integritéits-JSON + CSV), **Sigelen mat Zäitstempel (RFC 3161)** an ëffentlech Prüfsäit — geduecht fir d'Aarbechtsinspektioun.
- 🔏 **Sitzungsprotokoller am Browser verschlësselt** (AES-256-GCM): de Server gesäit ni de Klartext; de Coffre ass duerch Passwuert a Rettungsschlëssel geschützt.
- 👥 Sëtzungen a Protokoller, Delegatiounsstonnen (L.415-5), Konsultatiounen (L.414-3), Statistiken, Wahlen (strukturell anonym Ofstëmmung), Ukënnegungstafel, Joresrapport als PDF.
- 🌍 Interface a 5 Sproochen: **FR / EN / DE / PT / LB**.

## Ausprobéieren, installéieren

- 🎮 **Demo**: https://delegatum.cloudfr.net — Testkonten am [README](README.md#demo)
- 🖥️ **Desktop-App**: [lescht Releases](https://github.com/LostInTheBugs/Delegatum/releases) (Windows-/macOS-Zips; Benotzerhandbicher op FR/EN/DE/LB dobäi)
- 🐳 **Selbst gehost**: `docker compose up -d --build`, duerno `bash seed.sh` (Detailer am [README](README.md))

## Dokumentatioun

- Ausféierlech Guide'en (FR/DE/LB/EN): https://cloudfr.net/docs/delegatum/
- DSGVO: Modeller am Gepäck — [`docs/gdpr/`](docs/gdpr/README.lb.md)
- Sécherheet: [SECURITY.md](SECURITY.md) · Bedreungsmodell: [THREAT-MODEL.md](THREAT-MODEL.md)

⚠️ Experimentell Applikatioun — nëmmen als Demonstratioun geduecht, ass keng juristesch Berodung a net garantéiert konform mat der lëtzebuerger Gesetzgebung. Fir Froen zum Aarbechtsrecht konsultéiert en qualifizéierte Professionnel oder d'[Chambre des Salariés (CSL)](https://www.csl.lu).

MIT-Lizenz — Quellcode: github.com/LostInTheBugs/Delegatum
