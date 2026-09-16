# DSGVO — Vorlagen für Ihre Delegation (Delegatum)

🇫🇷 [Français](README.fr.md) · 🇬🇧 [English](README.en.md) · 🇱🇺 [Lëtzebuergesch](README.lb.md)

> ⚠️ **Vorlage, keine Rechtsberatung.** An Ihre Situation anpassen und von Ihrem Berater, Ihrem Datenschutzbeauftragten (DSB) oder der [CNPD](https://cnpd.public.lu) prüfen lassen. Die vorgeschlagenen Fristen sind **Standardempfehlungen**. Delegatum ist eine experimentelle Anwendung (siehe Hinweis im Haupt-README).

Eine Personaldelegation verarbeitet Beschäftigtendaten ohne Rechtsabteilung — die DSGVO gilt dennoch ab der ersten Verarbeitung. Diese Vorlagen bieten einen konkreten Ausgangspunkt.

## 1. Wer ist Verantwortlicher?

- **Der Herausgeber von Delegatum verarbeitet keine Daten**: kein Online-Dienst — keine Cloud, keine Telemetrie, keine Übermittlung nach außen.
- **Verantwortlicher ist Ihre Organisation** (die Delegation — gegebenenfalls gemeinsam mit dem Arbeitgeber, je nachdem, wer das Tool hostet).
- Läuft das Tool auf der Infrastruktur des Arbeitgebers, kann der technische Administrator auf die gespeicherten Daten zugreifen — **außer auf den Klartext der Sitzungsprotokolle**, der im Browser verschlüsselt wird (der Server sieht ihn nie). Dies in der Risikoanalyse dokumentieren (siehe [Bedrohungsmodell](../../THREAT-MODEL.md)).

## 2. Verzeichnis von Verarbeitungstätigkeiten (Art. 30) — Vorlage

| Zweck | Betroffene | Daten | Rechtsgrundlage (Vorschlag) | Aufbewahrung (empfohlen) |
|---|---|---|---|---|
| Verwaltung der Delegationsmitglieder | Mitglieder, Stellvertreter | Identität, Kontaktdaten, Foto, Rolle, Beschlüsse | Rechtliche Aufgabe der Delegation (Arbeitsgesetzbuch L.412-1 ff.) | Mandat + 5 Jahre |
| Erfassung der Delegationsstunden | Mitglieder | Stunden, Tätigkeiten, CSV-Exporte | Rechtliche Aufgabe (L.415-5) | 5 Jahre |
| Sitzungen und Protokolle | Mitglieder; Geschäftsleitung (geteilte Abschnitte) | Anwesenheit, Tagesordnung, Protokolle | Rechtliche Aufgabe (L.415-6 ff.) | Mandat + 5 Jahre |
| Sicherheits-/Gesundheitsregister | S&G-Delegierter, Servicechefs (Gegenzeichnung) | Feststellungen, Orte, Daten, Folgemaßnahmen (kann Gesundheits-/Vorfallsdaten enthalten) | Rechtliche Aufgabe (L.414-14); ITM-Einsicht | Mandat + 5 Jahre (zu prüfen) |
| Konsultationen des Arbeitgebers | Mitglieder | Stellungnahmen, Austausch, Fristen | Rechtliche Aufgabe (L.414-3) | 5 Jahre |
| Wahlen | Beschäftigte | Kandidaturen; aggregierte Ergebnisse (strukturell anonyme Stimmabgabe — keine Wähler-/Stimmenzuordnung) | Rechtliche Aufgabe (L.413-1 ff.) | Bis Ablauf der Anfechtungen + 5 Jahre |
| Virtuelles Anschlagbrett | Alle Beschäftigten | Mitteilungen der Delegation (nur Lesen für Beschäftigte) | Berechtigtes Interesse (Information der Beschäftigten) | Mandat |
| E-Mail-Benachrichtigungen | Mitglieder, Eingeladene | Adressen, Inhalte (.eml/SMTP) | Rechtliche Aufgabe / berechtigtes Interesse | 12 Monate |
| Sicherheitsprotokoll und Sicherungen | Nutzer | Technische Protokolle, verschlüsselte Sicherungen | Berechtigtes Interesse (Sicherheit) | 30 Tage (Rotation) |

## 3. Aufbewahrungsfristen — praktische Hinweise

- **Grundsatz**: nicht länger als nötig aufbewahren. Daten der Delegation richten sich nach dem **Mandat**, plus Streitigkeiten-Fenster (Empfehlung: + 5 Jahre maximal).
- **Ende des Mandats**: exportieren, was übergeben werden muss, dann **löschen**, was keine Rechtsgrundlage mehr hat.
- **Sicherungen**: kurze Rotation (30 Tage), verschlüsselte Datenträger, außerhalb des Geräts. Eine vergessene Sicherung ist ein potenzieller Datenschutzverstoß.
- **S&G-Register**: gesetzliches Register — Aufbewahrung mit Berater/ITM abstimmen (Standardempfehlung: Mandat + 5 Jahre).

## 4. DSFA (Art. 35) — brauchen Sie eine?

**Kurzscreening** (Antworten dokumentieren — diese Seite kann als Nachweis dienen):

- Verarbeitung **in großem Umfang**? — eine Delegation ist klein;
- **Gesundheitsdaten**? — möglich über das S&G-Register, aber nicht in großem Umfang, nicht zu Behandlungszwecken;
- **systematische Überwachung**? — nein (kein Profiling);
- **schutzbedürftige Personen**, Datenzusammenführung, automatisierte Entscheidungen? — nein.

→ Für eine typische Delegation ist eine DSFA **in der Regel nicht erforderlich**. Falls Ihre Situation mehrere Kriterien kombiniert (oder Sie unsicher sind), nutzen Sie diese vereinfachte Vorlage:

1. **Beschreibung** der Verarbeitung und ihrer Notwendigkeit;
2. **Verhältnismäßigkeit** (Rechtsgrundlage, Datenminimierung, Fristen);
3. **Risiken** für die Betroffenen (unbefugter Zugriff, Offenlegung, Verlust);
4. **Maßnahmen**: Protokollverschlüsselung, Registerintegrität, Zugriffskontrolle, Sicherungen;
5. **Stellungnahme** DSB/Berater, Datum, Überprüfung.

## 5. Was das Tool zum Schutz der Daten tut

- **Protokolle im Browser verschlüsselt** (AES-256-GCM): der Server hält weder Klartext noch Tresor-Passwort. **Wiederherstellungsschlüssel** offline aufbewahren (Safe).
- **S&G-Register**: verkettete Integrität (SHA-256) + **RFC-3161-Siegel**. **Siegel-E-Mails außerhalb des Servers** aufbewahren und das ITM-Dossier regelmäßig exportieren — der Schutz gegen Veränderung hängt von diesen externen Kopien ab.
- **Keine Übermittlung** von Daten an den Herausgeber.
- Betriebsempfehlungen: HTTPS, namentliche Konten, MFA für Administratoren, verschlüsselte Sicherungen, gesperrte Arbeitsplätze.

## 6. Bei einer Datenschutzverletzung (Art. 33-34)

1. **Bewerten und dokumentieren** (Vorfallblatt: Datum, Art, Daten und Betroffene, Folgen, Maßnahmen).
2. **Behörde benachrichtigen** — in Luxemburg die **CNPD** — binnen **72 h** bei Risiko für Betroffene; Betroffene informieren, wenn das Risiko hoch ist.
3. **Typische Ursachen**: unbefugter Zugriff, verlorener Laptop (Desktop-Version), abhandengekommene Sicherung, Fehladressierung von E-Mails.
4. Hinweis: Da **Protokollinhalte verschlüsselt** sind, ist deren Offenlegung nicht automatisch ein hochriskantes Ereignis — der Verlust der Schlüssel jedoch schon.

## Ressourcen

- CNPD — https://cnpd.public.lu · Guichet.lu — DSGVO-Merkblätter
- [THREAT-MODEL.md](../../THREAT-MODEL.md) — dokumentierte technische Grenzen
- [SECURITY.md](../../SECURITY.md) — Sicherheitsprobleme melden
