# DSGVO — Modeller fir Är Delegatioun (Delegatum)

🇫🇷 [Français](README.fr.md) · 🇬🇧 [English](README.en.md) · 🇩🇪 [Deutsch](README.de.md)

> ⚠️ **Modell, keng juristesch Berodung.** Upasse fir Är Situatioun a vun Ärem Beroder, Ärem Dateschutz-Beaftragten (DSB) oder der [CNPD](https://cnpd.public.lu) verifizéiere loossen. D'Fristen, déi virgeschloe ginn, sinn **Standard-Empfehlungen**. Delegatum ass eng experimentell Applikatioun (kuckt den Hinweis am Haapt-README).

Eng Personaldelegatioun veraarbecht Beschäftegtendonneeëen ouni Juristescher Ofdeelung — d'DSGVO gëllt awer vun der éischter Veraarbechtung un. Dës Modeller bidden en konkreten Ufank.

## 1. Wien ass Verantwortlechen?

- **Den Editeur vun Delegatum veraarbecht keng Donnéeën**: keen Online-Service — keng Cloud, keng Telemetrie, keng Iwwermëttlung no baussen.
- **Verantwortlechen ass Är Organisatioun** (d'Delegatioun — je no Situatioun zesumme mam Patron, jee no wien den Tool hostet).
- Lafen den Tool op der Infrastruktur vum Patron, kann den techneschen Administrateur op déi gespäichert Donnéeën zougräifen — **ausser op den Klartext vun de Protokoller**, dee am Browser verschlësselt gëtt (de Server gesäit en ni). Dat an der Risikoanalys dokumentéieren (kuckt [Bedreungsmodell](../../THREAT-MODEL.md)).

## 2. Verzeechnes vun de Veraarbechtungsaktivitéiten (Art. 30) — Modell

| Zweck | Betraffen | Donnéeën | Rechtsgrondlag (Virschlag) | Opbewahrung (empfohlen) |
|---|---|---|---|---|
| Verwaltung vun de Memberen | Memberen, Stellvertrieder | Identitéit, Kontakter, Foto, Roll, Decisiounen | Juristesch Missioun vun der Delegatioun (Aarbechtsgesetzbuch L.412-1 ff.) | Mandat + 5 Joer |
| Delegatiounsstonnen | Memberen | Stonnen, Aktivitéiten, CSV-Exporten | Juristesch Missioun (L.415-5) | 5 Joer |
| Sëtzungen a Protokoller | Memberen; Direktioun (gedeeelt Sektiounen) | Presenz, Tagesuerdnung, Protokoller | Juristesch Missioun (L.415-6 ff.) | Mandat + 5 Joer |
| Sécherheets-/Gesondheetsregëster | S&G-Delegéierten, Servicechefen (Géigezeechnung) | Feststellunge, Plazen, Daten, Suiten (kann Gesondheets-/Incidentdonnéeën enthalen) | Juristesch Missioun (L.414-14); ITM-Konsultatioun | Mandat + 5 Joer (ze verifizéieren) |
| Konsultatiounen vum Patron | Memberen | Avisen, Austausch, Delaien | Juristesch Missioun (L.414-3) | 5 Joer |
| Wahlen | Beschäftegt | Kandidaturen; aggregéiert Resultater (strukturell anonym Ofstëmmung — keng Zuordnung Wieler/Stëmm) | Juristesch Missioun (L.413-1 ff.) | Bis Enn vun de Kontestatiounen + 5 Joer |
| Virtuell Ukënnegungstafel | All Personal | Kommunikatioun vun der Delegatioun (nëmmen liesen) | Berechtegt Intressi (Informatioun vum Personal) | Mandat |
| E-Mail-Notifikatiounen | Memberen, Invitéen | Adressen, Inhalten (.eml/SMTP) | Juristesch Missioun / berechtegt Intressi | 12 Méint |
| Sécherheetsjournal a Sauvegardë | Benotzer | Technesch Journalen, verschlësselt Sauvegardë | Berechtegt Intressi (Sécherheet) | 30 Deeg (Rotatioun) |

## 3. Opbewahrungsfristen — praktesch Hiwäiser

- **Grondsaz**: net méi laang wéi néideg opbewaaren. D'Donnéeë vun der Delegatioun richte sech no der **Mandatur**, plus eng Frist fir Sträitfäll (Empfehlung: + 5 Joer maximal).
- **Enn vun der Mandatur**: exportéieren wat iwwergi gëtt, duerno **läschen** wat keng Rechtsgrondlag méi huet.
- **Sauvegardë**: kuerz Rotatioun (30 Deeg), verschlësselt Mediä, ausserhalb vum Apparat. Eng vergiessen Sauvegarde ass e potenzielle Verstouss.
- **S&G-Regëster**: gesetzlecht Regëster — Opbewahrung mat Beroder/ITM ofstimmen (Standardempfehlung: Mandatur + 5 Joer).

## 4. DSFA (Art. 35) — braucht Dir eng?

**Kuerz-Screening** (Äntwerten dokumentéieren — dës Säit kann als Noweis dengen):

- Veraarbechtung **an engem grousse Moossstab**? — eng Delegatioun ass kleng;
- **Gesondheetsdonnéeën**? — méiglech iwwer de S&G-Regëster, awer net a grousse Mooss, net fir Behandlung;
- **systematesch Iwwerwaachung**? — nee (kee Profiling);
- **schutzbedürfteg Persounen**, Zesummeféierung vun Donnéeën, automatesch Entscheedungen? — nee.

→ Fir eng typesch Delegatioun ass eng DSFA **in der Regel net néideg**. Wann Är Situatioun méi Krittären kombinéiert (oder Dir onsécher sidd), benotzt dës vereinfacht Virlag:

1. **Beschreiwung** vun der Veraarbechtung an hirer Noutwendegkeet;
2. **Verhältnisméissegkeet** (Rechtsgrondlag, Dateminimiséierung, Fristen);
3. **Risiken** fir d'Betraffen (onbefugten Zougrëff, Divulgatioun, Verloscht);
4. **Mesuren**: Protokollverschlësselung, Integritéit vum Regëster, Zougrëffskontroll, Sauvegardë;
5. **Avis** vum DSB/Beroder, Datum, Iwwerpréiwung.

## 5. Wat den Tool fir de Schutz vun den Donnéeën mécht

- **Protokoller am Browser verschlësselt** (AES-256-GCM): de Server hält weder Klartext nach Tresor-Passwuert. **Rettungsschlëssel** offline opbewaaren (Safe).
- **S&G-Regëster**: verkettegt Integritéit (SHA-256) + **RFC-3161-Sigelen**. **Sigel-E-Maile ausserhalb vum Server** opbewaaren an den ITM-Dossier regelméisseg exportéieren — de Schutz géint Ännerung hänkt vun dësen externe Kopien of.
- **Keng Iwwermëttlung** vun Donnéeën un den Editeur.
- Betribsempfehlungen: HTTPS, nominativ Konten, MFA fir Administratoren, verschlësselt Sauvegardë, gespaart Aarbechtsplazen.

## 6. Bei enger Datenverletzung (Art. 33-34)

1. **Bewerten an dokumentéieren** (Incident-Blatt: Datum, Aart, Donnéeën a Betraffen, Konsequenzen, Mesuren).
2. **Autoritéit informéieren** — zu Lëtzebuerg d'**CNPD** — bannent **72 Stonnen** bei Risiko fir d'Betraffen; d'Betraffen informéieren, wann de Risiko héich ass.
3. **Typesch Ursaachen**: onbefugten Zougrëff, verluerene Laptop (Desktop-Versioun), verluere Sauvegarde, falsch adresséiert E-Maile.
4. Hinweis: well **Protokollinhalter verschlësselt** sinn, ass hir Offenlegung net automatesch e Risiko-Evenement — de Verloscht vun de Schlësselen awer schonn.

## Ressourcen

- CNPD — https://cnpd.public.lu · Guichet.lu — DSGVO-Fichen
- [THREAT-MODEL.md](../../THREAT-MODEL.md) — dokumentéiert technesch Grenzen
- [SECURITY.md](../../SECURITY.md) — Sécherheetsproblemer mellen
