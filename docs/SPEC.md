# AnKIzin Explorer – Spezifikation

Status: Design abgeschlossen (Grilling-Interview, 27 Entscheidungen). Diese Datei ist die
verbindliche Grundlage für die Umsetzung. Abweichungen vorher mit dem Owner klären.

## 1. Zweck

AnKIzin (das große deutschsprachige Medizin-Deck, verteilt über AnkiCollab) wird so
genutzt, wie es gedacht ist: Alle Karten sind ausgesetzt, man aktiviert gezielt die
Themen, die man gerade lernt. Der eingebaute Tag-Explorer von Anki ist dafür zu
unübersichtlich. Der AnKIzin Explorer ist ein **besseres UI auf genau diesen Workflow**,
kein eigenes Ordnungssystem.

Leitfrage des Nutzers: *„Ich suche in Fach X das Thema Y – welche Blöcke gibt es dort,
die ich lernen kann, und wie weit bin ich damit?“* Übersichtlichkeit ist das Hauptziel.

## 2. Datenquellen (AnKIzin-Struktur)

Gemessen an einer echten, aktuellen AnKIzin-Sammlung (~49k Karten):

### 2.1 AMBOSS-Bibliothek-Tags (Standard-Ansicht)

- Klinik: `<ROOT>::#M2_M3_Klinik::#AMBOSS::Bibliothek-Klinik::<Fach>::<…>::<Artikel>`
- Vorklinik: `<ROOT>::#M1_Vorklinik_(work_in_progress)::#AMBOSS::<…>`
- `<ROOT>` ist aktuell `#Ankizin_vAnkiCollab`. **Nicht hart codieren**, sondern per
  Präfix `#Ankizin_v` erkennen (frühere Versionen hießen z. B. `#Ankizin_v5`). Bei
  mehreren Roots den mit den meisten Notizen nehmen.
- Bis zu 8 Ebenen tief, 30 Fächer auf Ebene 1 (Innere_Medizin, Chirurgie, Pharmakologie,
  `(fächerübergreifend)_…` usw.).
- **Ein Artikel hängt oft an mehreren Stellen** (z. B. Tuberkulose unter Infektiologie,
  Innere Medizin und Radiologie). Eine Karte kann also in mehreren Knoten liegen.
- Unterstriche in Tag-Namen für die Anzeige durch Leerzeichen ersetzen.
- Matching über Ankis Suche ist case-insensitiv; Tag-Namen enthalten Klammern, Kommas,
  `&`, `+`, Umlaute – beim Bauen von Suchstrings korrekt escapen bzw. lieber direkt über
  Tag-Listen der Notizen arbeiten.

### 2.2 Deck-Baum (zweite Ansicht)

- `Ankizin::M2_M3_Klinik::<Fach>` – in der Klinik **nur eine Ebene** (29 Fächer).
- `Ankizin::M1_Vorklinik::<Fach>::<…>` – bis zu 3 Ebenen.
- Taugt für grobe „ganzes Fach an/aus“-Schalter.

### 2.3 Auszublenden

Meta-/Projekt-Tags erscheinen nirgends im Baum, u. a.:
`§Projekt_Anki`, `!MARKIERE_DIESE_KARTEN`, `§NEW_CARDS`, `#MEDITRICKS`,
`#UNIVERSITÄTEN`, `!Ankizin_Tutorial_&_Add-Ons`, `M2-100-Tage-Lernplan`,
`M3-Kenntnisprüfung`, `M2-TOP100-Themen`, `#IMPP-Arzneistoffliste`.
Die AMBOSS-Ansicht zeigt ausschließlich die Teilbäume aus 2.1.

## 3. Logik

| Thema | Entscheidung |
|---|---|
| Was heißt „an“ | Karten des Themas werden **unsuspended**. Keine gefilterten Decks. |
| Was heißt „aus“ | **Alle** Karten des Themas werden suspended, auch bereits gelernte. Scheduling-Daten bleiben erhalten. |
| Überlappung | Beim Ausschalten wird der **ganze Teilbaum** ausgesetzt, auch Karten, die zusätzlich in anderen Themen hängen (geändert nach dem ersten Test, siehe DECISIONS 1). „An gewinnt“ ist als Option `an_gewinnt` erhalten. |
| Zustand | **Kein eigenes Gedächtnis.** Zustand eines Knotens ergibt sich nur aus den Karten: ☐ aus (0 % aktiv), ◐ teilweise, ☑ an (100 % aktiv). |
| Eingeschaltet für „An gewinnt“ | Ein Knoten gilt als eingeschaltet, wenn ≥ 90 % seiner Karten aktiv sind (gleiche Schwelle wie 3.1). |
| Oberthemen | Checkbox auf einem Oberknoten schaltet den ganzen Teilbaum. |
| Sicherheitsabfrage | Ab **500 Karten** pro Schaltvorgang: Dialog „Du aktivierst 2.340 Karten. Bei deinem Limit von X neuen/Tag sind das ca. Y Tage. Fortfahren?“ (X aus den Deck-Optionen des AnKIzin-Hauptdecks, Y = neue Karten / X). Beim Aussetzen analog ohne Tagesschätzung. |
| Deck-Optionen | Werden **nie** verändert. Das Tageslimit regelt weiter Anki. |
| Undo | Jeder Schaltvorgang ist ein eigener Undo-Schritt (Cmd/Ctrl+Z im Hauptfenster), über `CollectionOp` + `col.add_custom_undo_entry` / `merge_undo_entries`. |

### 3.1 Neue Karten nach AnKIzin-Updates

AnkiCollab importiert neue Karten ausgesetzt (`suspend_new_cards = true`). Dadurch fällt
ein vorher eingeschaltetes Thema auf „teilweise“. Das Addon erkennt das ohne Gedächtnis:

- Knoten mit ≥ 90 % aktiven Karten, die zusätzlich **ausgesetzte neue** Karten
  (queue = suspended, type = new) enthalten, gelten als „aktiv mit Nachzüglern“.
- Oben im Fenster erscheint ein Hinweisbanner: „In 6 deiner aktiven Themen gibt es 48
  neue ausgesetzte Karten – aktivieren?“ mit Button. Nur Blattknoten bzw. den jeweils
  tiefsten betroffenen Knoten zählen, damit nichts doppelt gezählt wird.
- Optional (Ausbau): Hinweis zusätzlich als Tooltip beim Profilstart, wenn das Banner
  Nachzügler finden würde.

## 4. Lernstand

Pro Knoten, gezählt in **Karten** (nicht Notizen):

- **neu** – noch nie gelernt (type = new)
- **gesehen** – mindestens einmal gelernt, Intervall < 21 Tage
- **gefestigt** – Intervall ≥ 21 Tage

Darstellung: kleiner **Ring mit 3 Farben** pro Zeile/Kachel, daneben „gesehen/gesamt“
(gesehen hier = gesehen + gefestigt). Hover-Tooltip mit allen Zahlen inkl. aktiv/ausgesetzt.

## 5. Oberfläche

- **Natives Qt-Fenster** (kein Webview) – muss bei tausenden Knoten flüssig sein.
  Hell/Dunkel nach Anki-Theme, optisch an Onigiri angelehnt (runde Ecken, ruhige Farben),
  funktioniert aber ohne Onigiri gleich gut.
- **Tabs:** „AMBOSS-Bibliothek“ (Standard) · „Decks“.
- **Layout Master/Detail:**
  - **Links:** Baum mit Live-Suchfeld oben, Tri-State-Checkboxen, Ring, Zahlen. Alle
    Ebenen bis zum Artikel, anfangs zugeklappt. Suche filtert den Baum auf Treffer + deren
    Pfade und klappt sie auf; Treffer an mehreren Stellen erscheinen alle.
  - **Rechts:** Übersicht des gewählten Knotens: Kopf mit Pfad, großem Ring, Summen und
    An/Aus-Knopf für den ganzen Knoten; darunter **Kacheln für alle direkten Kinder**
    (Name, Ring, Zahlen, Status, An/Aus-Knopf). Klick auf eine Kachel navigiert hinein.
- **Sortierung** (Baum und Kacheln): alphabetisch (Standard), nach Größe, nach Lernstand.
- **Kontextmenü / Button:** „Im Browser zeigen“ öffnet den Kartenbrowser mit der Suche
  für diesen Knoten.
- **Einstellungen:** „Vorklinik anzeigen“ (Standard: aus). Weitere nur wenn nötig.
- Nach jedem Schaltvorgang Zahlen neu berechnen, Auswahl und Aufklappzustand behalten.
- Daten im Hintergrund laden (`QueryOp`), Fenster nicht blockieren.

## 6. Einbindung und Kompatibilität

- **Vanilla Anki ist gleichwertig, nicht Fallback.** Immer vorhanden:
  - Menüeintrag unter **Extras → AnKIzin Explorer** mit Tastenkürzel (Vorschlag:
    `Ctrl+Shift+E`, vorher auf Konflikte prüfen).
  - Link in der oberen Toolbar (`gui_hooks.top_toolbar_did_init_links`).
  - Knopf unter der Deckliste (`gui_hooks.deck_browser_will_render_content`), abschaltbar
    über `knopf_startseite`.
- **Zusätzlich, wenn Onigiri installiert ist:** Eintrag in der Onigiri-Seitenleiste über
  dessen öffentliche API:
  ```python
  onigiri.register_sidebar_action(
      entry_id="ankizin_explorer.open",
      label="AnKIzin Explorer",
      command="ankizin_explorer_open",
      icon_svg="<svg …>",
  )
  ```
  - Das Onigiri-Paket liegt unter seiner AnkiWeb-ID als Ordnername. Nicht per
    `import Onigiri` laden, sondern über `mw.addonManager.all_addon_meta()` den Ordner
    finden und mit `importlib.import_module(<ordner>)` importieren; alles in try/except.
  - `command` kommt per `pycmd()`; in `gui_hooks.webview_did_receive_js_message`
    behandeln.
  - Externe Einträge sind in Onigiri standardmäßig „archiviert“ und müssen in dessen
    Einstellungen aktiviert werden – im README erwähnen.
  - Registrierung erst nach `profile_did_open` / `main_window_did_init`, wenn alle
    Addons geladen sind.
- **Keine Abhängigkeiten auf andere Addons**, keine Monkeypatches fremder Addons, kein
  Ändern von Onigiri-, AnkiCollab- oder AnKIzin-Notetype-Dateien.
- Nur öffentliche Anki-APIs (`aqt`, `anki`), Python ≥ 3.9, PyQt6.
- Zielversionen: Anki **25.02+** bis aktuell (getestet auf 26.9.x). `manifest.json` /
  AnkiWeb-Metadaten entsprechend setzen.
- Wenn kein AnKIzin-Deck/Tag gefunden wird: freundliche Meldung statt leerem Fenster.

## 7. Performance

- Eine Sammlung hat ~50k AnKIzin-Karten und ~100k AMBOSS-Tag-Zuordnungen.
- Daten einmal per SQL über `mw.col.db` laden (Notiz-ID → Tags, Karten → queue/type/ivl/did),
  Baum in Python aggregieren. Nicht pro Knoten eine `find_cards`-Suche.
- Schalten über `mw.col.sched.suspend_cards` / `unsuspend_cards` mit den gesammelten
  Karten-IDs.
- Ziel: Fenster öffnet in < 2 s, Schalten eines Fachs in < 2 s.

## 8. Später (nicht Teil von v1)

- „Nur dieses Thema jetzt lernen“ → gefiltertes Deck aus dem Knoten erzeugen.
- Bento-Widget für die Onigiri-Startseite (aktive Themen + Fortschritt).
- Weitere Ansichten (z. B. AMBOSS-Lernpläne) – nur wenn gewünscht.

## 9. Veröffentlichung

- Öffentliches GitHub-Repo, gemeinfrei (The Unlicense) auf Wunsch des Owners.
- Build-Skript erzeugt `dist/ankizin_explorer.ankiaddon` (Zip des Pakets ohne
  `__pycache__`, ohne `meta.json`).
- Upload auf AnkiWeb macht der Owner manuell.
- **Keine personenbezogenen Daten** im Repo: keine Namen, E-Mails, Uni, lokale Pfade mit
  Benutzernamen, Screenshots mit privaten Decks.
