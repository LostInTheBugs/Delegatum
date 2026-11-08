# Delegatum — Gestion vun Ärer Personaldelegatioun

🇬🇧 English version: [README.md](README.md) · 🇫🇷 [README.fr.md](README.fr.md) · 🇩🇪 [README.de.md](README.de.md)

Verwaltungsinstrument fir **Personaldelegatiounen** zu Lëtzebuerg (Code du travail, Art. L.412-1 f.) — gebaut, fir datt Är Donnéeën Är Organisatioun ni verloossen.

- 🔐 **Är Donnéeën bleiwen bei Iech**: selbst gehost (Docker) oder **Desktop-App** fir Windows/macOS — keng Cloud, keen Online-Kont, keng Telemetrie.
- 🛡️ **Sécherheets-/Gesondheetsregëster** (Art. L.414-14): Feststellunge mat Géizeechnung vum Servicechef, **verkettegt Integritéitsjournal** (Annulatioun mat Grond amplaz Läschung), **ITM-Dossier** (druckbar PDF + Integritéits-JSON + CSV), **Sigelen mat Zäitstempel (RFC 3161)** an ëffentlech Prüfsäit — geduecht fir d'Aarbechtsinspektioun.
- 🔏 **Sëtzungsprotokoller am Browser verschlësselt** (AES-256-GCM): de Server gesäit ni de Klartext; de Coffre ass duerch Passwuert a Rettungsschlëssel geschützt.
- 👥 Sëtzungen a Protokoller, Delegatiounsstonnen (L.415-5), Konsultatiounen (L.414-3), Statistiken, Wahlen (strukturell anonym Ofstëmmung), Ukënnegungstafel, Joresrapport als PDF.
- 🌍 Interface a 5 Sproochen: **FR / EN / DE / PT / LB**.

## Ausprobéieren, installéieren

- 🎮 **Demo**: https://delegatum.cloudfr.net — Testkonten am [README](README.md#demo)
- 🖥️ **Desktop-App**: [lescht Releases](https://github.com/LostInTheBugs/Delegatum/releases) (Windows-/macOS-Zips; Benotzerhandbicher op FR/EN/DE/LB dobäi)
- 🐳 **Selbst gehost**: `docker compose up -d --build`, duerno `bash seed.sh` (Detailer am [README](README.md))

## Konfiguratioun

Kopéiert `.env.example` op `.env` an passt d'Variabelen un:

| Variable | Beschreiwung | Standardwärt |
|----------|-------------|-------------|
| `SD_PORT` | Backend-Listenport | `8005` |
| `SD_SECRET_KEY` | JWT-Signéierschlëssel — **erfuerderlech** (d'App verweigert den Start mat engem Beispillwärt oder engem Schlëssel méi wéi 32 Zeechen; docker-compose feel, wann net gesat) | — |
| `SD_DATABASE_URL` | Datebank-URL (iwwerschreifbar — SQLite Standard, PostgreSQL ënnerstëtzt) | `sqlite:///./data/staff_delegation.db` |
| `SD_INSTANCE_PROFILE` | Instanzprofil — beschränkt disponibel Module | `dp` (all Module) |
| `SD_ACCESS_TOKEN_EXPIRE_MINUTES` | JWT-Token-Verfallszäit | `1440` (24 h) |
| `SD_INSTANCE_ADMIN_EMAILS` | Komma-getrennt Lëscht vun E-Mail-Adressen, déi als Instanzadministratoren autoriséiert sinn (kuckt Updates); eidel loosse fir Single-Organisation Admin-Fallback | — |
| `SD_UPDATE_NO_BUILD` | `1` op klenge Serveren, fir de Bau vu Docker-Images ze verweigeren — deployed virbereetete Images | `0` (Build erlaabt) |
| `SD_UPDATE_LOOP` | `0` fir den Hannergrond-Check-Lëss ze deaktivéieren (den 🔎-Check am Admin-Panel funktionnéiert weider) | `1` (Lëss aktiv) |

De Port kann iwwer d'Ëmgebungsvariabel `SD_PORT` an alle Kontexter (Docker, lokal Entwécklung) iwwerschriwwe ginn. All Konfiguratiounsdateien referenzéieren Standardméisseg Port 8005.

## Instanzprofil

`SD_INSTANCE_PROFILE` beschränkt disponibel Module beim Start (d'App verweigeret den Start mat engem ongültegen Wäert). Gëlteg Wäerter:

| Profil | Disponibel Module |
|--------|-------------------|
| `dp` (Standard) | All Module — komplette DP-Funktionsumfang |
| `sst` | Dashboard, Domän-Aktivitéiten (nëmmen Sécherheet/Gesondheet), Stonnen, Formatioun/Schutz, Sécherheetsregister (wann `sst`) |
| `egalite` | Dashboard, Domän-Aktivitéiten (nëmmen Gläichstellung), Stonnen, Formatioun/Schutz |
| `sst,egalite` | Dashboard, Domän-Aktivitéiten (bäid), Stonnen, Formatioun/Schutz, Sécherheetsregister (wann `sst`) |

Am Nëmme-Delegéierte-Profil (`sst`, `egalite` oder `sst,egalite`) si folgend Module verstoppt: Sëtzungen/Protokoller/Coffre/Archiv, Wahlen, Konsultatiounen, Statistiken, Ukënnegungstafel, Compliance, Kontakt. Déi bleiwen Funktiounen si: Dashboard, Aktivitéite vun der/en Profil-domän(en), Stonnen, Formatioun/Schutz, an Sécherheetsregister (nëmmen wann `sst`).

## Aktualiséierongen

Automateschen Update fir delegéiert Verwaltung — d'App prüft op nei Versiounen an ënnerleet wann disponibel eng Ufrodatei; en systemd-Déngscht (Timer + Skript) um Host wend den Update un, andeems en de Release-Tarball zitt, de Code rsynced, Docker-Images nei baut an Alembic-Migratiounen ausféiert. De App-Container **riiert ni** Docker un — eng bewosst Sécherheetsgrenz.

### Zougankskontroll

Nur en **Instanzadministrator** kann Updates ufroen oder uwenden. D'Instanz-Admin-Zougehéieregkeet gëtt wéi follegt bestëmmt:

1. **`SD_INSTANCE_ADMIN_EMAILS`** (komma-getrennt Lëscht) — wann gesat, si nëmmen déi opgelëscht E-Mail-Adressen autoriséiert.
2. **Fallback** — wann `SD_INSTANCE_ADMIN_EMAILS` eidel ass, ass jiddwer Administrator-Benutzer vun enger **Single-Organisation**-Instanz autoriséiert. Multi-Organisation-Instanze ouni `SD_INSTANCE_ADMIN_EMAILS` sperren den Update-Zougang (403).

### Konfiguratioun

Astellungen ginn an der Datebank gespäichert an si iwwer de **🔄 Updates**-Link an der Navigatiounsläsch erreechbar (nëmmen fir Instanzadministratoren siichtbar):

- **Check-Kadenz** (ni / 1 h (Standard) / 6 h / 12 h / 24 h / wochentlech) — den Hannergrond-Lëss prüft GitHub an dësem Intervall.
- **Auto-apply** — standardméisseg aus; wann un, ënnerleet d'App eng Apply-Ufro soulaang eng nei Versioun erkannt gëtt (ni wärend engem lafende Job).
- **🔎 Elo prüfen** — eenmolge Check onofhängeg vun der Kadenz.

### Klenge-Server-Schutz (`SD_UPDATE_NO_BUILD=1`)

Op klenge Hosten, déi keng Docker-Images baue kënnen, setzt `SD_UPDATE_NO_BUILD=1` an `.env` oder als Ëmgebungsvariabel. Den Updater verweigeret da de Bau — de Host muss virbereetete Images deployen (z. B. iwwer CI) an den Updater iwwerspréngt den `--build`-Schrëtt.

### Automatesch Datebanksécherung

Viru jidwer Update sichert den Updater all `.db`-Datei an `DATA_DIR` no `*.db.pre-<version>`. Déi **dräi neist** Backups pro Datebank ginn behalen; méi al ginn bereinigt. Zum Rollback benannt Dir d'.pre-<version>-Datei zeréck op de Originalnumm an start nei.

### Host-seitegen Updater-Installatioun

Installéiert den systemd-Timer op dem Host, deen de Docker-Deployment ausféiert:

```sh
sudo cp deploy/delegatum-update.service /etc/systemd/system/
sudo cp deploy/delegatum-update.timer /etc/systemd/system/
# ⚠️ Editéiert User a WorkingDirectory virum Aktivéieren — se MÜSSEN mat Ärem Deployment iwwereneestëmmen
# Korrekt: WorkingDirectory=/opt/delegatum  (Repository-Wuerzel, wou deploy/ läit)
# Falsch:  WorkingDirectory=/opt/delegatum/app
sudo systemctl daemon-reload
sudo systemctl enable --now delegatum-update.timer
python3 deploy/apply-update.py --dry-run   # Saniétstest — ännert näischt
```

Den Timer prüft all 5 Minutten, ob d'App eng Update-Ufro ënnerleet huet; wann keen aussteet, mécht en näischt. Ouni den Timer funktionnéiert d'Schaltfläch 🔎 am Admin-Panel weider — d'Ufro waart einfach op d'manuell Uwendung.

## Dokumentatioun

- Ausféierlech Guide'en (FR/DE/LB/EN): https://cloudfr.net/docs/delegatum/
- DSGVO: Modeller am Gepäck — [`docs/gdpr/`](docs/gdpr/README.lb.md)
- Sécherheet: [SECURITY.md](SECURITY.md) · Bedreungsmodell: [THREAT-MODEL.md](THREAT-MODEL.md)

⚠️ Experimentell Applikatioun — nëmmen als Demonstratioun geduecht, ass keng juristesch Berodung a net garantéiert konform mat der lëtzebuerger Gesetzgebung. Fir Froen zum Aarbechtsrecht konsultéiert en qualifizéierte Professionnel oder d'[Chambre des Salariés (CSL)](https://www.csl.lu).

MIT-Lizenz — Quellcode: github.com/LostInTheBugs/Delegatum
