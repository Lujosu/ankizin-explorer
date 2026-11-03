# Entscheidungen bei der Umsetzung (v1)

Punkte, die `SPEC.md` offen lässt oder die beim Bauen präzisiert werden mussten.
Jeweils: Entscheidung – Begründung. Abweichungen von der SPEC sind als **Abweichung** markiert.

## Logik

1. **Aussetzen = ganzer Teilbaum; „an gewinnt“ nur noch als Option** (`an_gewinnt`, Standard
   aus). **Abweichung** von SPEC 3 nach dem ersten Test im Alltag.
   *Warum:* Auf einer echten Sammlung mit schon aktiven Themen ließ „Intensivmedizin aus“ 559
   von 5.354 Karten aktiv, weil die Artikel auch unter anderen, aktiven Fächern hängen. Das
   Fach stand danach auf ◐, und der nächste Klick *aktivierte* es wieder – man kam nie auf
   „aus“. Der Owner erwartet: Oberthema aus = alles darunter aus.
   Mit der Option gilt die frühere Regel: Eine Karte bleibt aktiv, wenn sie in einem Knoten M
   liegt, der weder Vorfahr noch Nachfahr ist und bei dem ≥ 90 % der Karten *außerhalb* des
   auszuschaltenden Knotens aktiv sind (sonst würde „Fach an, Fach aus“ den Großteil des
   Fachs aktiv lassen, weil Artikel durch das Einschalten selbst „an“ werden).
2. **Klick auf ☐ oder ◐ aktiviert, Klick auf ☑ setzt aus.** Gilt für Checkbox, Kopf-Knopf und
   Kachel-Knopf (seit 29 eine Checkbox). Der Knopf heißt entsprechend „Aktivieren“ bzw. „Aussetzen“. Bei ◐ gibt es im
   Kopf einen zweiten Knopf „Aussetzen“ und im Rechtsklick-Menü beide Aktionen.
3. **Lernstufen:** neu = `type = 0`; gefestigt = Review-Karte (`type = 2`) mit `ivl ≥ 21`;
   alles andere (Lernen, Wiederlernen, Review < 21 Tage) = gesehen. Aktiv = nicht ausgesetzt
   (`queue ≠ -1`); vergrabene Karten zählen als aktiv.
4. **Nachzügler (SPEC 3.1):** Für jeden eingeschalteten Knoten (≥ 90 % aktiv) zählen die neuen
   ausgesetzten Karten, die direkt an ihm hängen und in keinem seiner Kinder liegen. So wird
   jede Karte auf der tiefsten Ebene gezählt, und Karten in bewusst ausgeschalteten
   Unterthemen eines eingeschalteten Fachs gelten nicht als Nachzügler. „Themen“ im Banner =
   Anzahl solcher Knoten; Karten über Mehrfachzuordnungen hinweg nur einmal. Das Banner
   bezieht sich auf den gerade offenen Tab.
5. **Sicherheitsabfrage:** Die 500er-Schwelle zählt die Karten, die sich tatsächlich ändern
   (beim Aktivieren die bisher ausgesetzten, beim Aussetzen die bisher aktiven abzüglich „an
   gewinnt“). Tage = neue Karten darunter / Limit, aufgerundet. Das Limit kommt aus den
   Deck-Optionen des obersten „Ankizin…“-Decks und wird erst beim Nachfragen gelesen (damit
   Änderungen an den Optionen sofort gelten). Ohne Deck oder bei Limit 0 entfällt die
   Tagesschätzung. Beim Aussetzen nennt der Dialog zusätzlich, wie viele Karten wegen „an
   gewinnt“ aktiv bleiben.
6. **Nachzügler aktivieren** ist ein eigener Undo-Schritt („AnKIzin: „Nachzügler“ aktivieren“)
   und läuft durch dieselbe Abfrage ab 500 Karten.

## Daten

7. **AMBOSS-Ansicht** = nur die Teilbäume `…::#M2_M3_Klinik::#AMBOSS::Bibliothek-Klinik` und
   (optional) `…::#M1_Vorklinik…::#AMBOSS::Bibliothek-Vorklinik`. Lernpläne
   (`M2-100-Tage-Lernplan`, `M1-30-Tage-Lernplan_Turbo` …), `M3-Kenntnisprüfung` und alle
   Meta-Tags fallen damit automatisch weg. Der Vorklinik-Abschnitt wird per Präfix
   `#M1_Vorklinik` erkannt, damit ein späteres Umbenennen von „(work_in_progress)“ nicht stört.
8. **Root-Tag:** Präfix `#Ankizin_v` (Groß/klein egal); bei mehreren gewinnt der mit den
   meisten Notizen in der Bibliothek. Tags anderer Roots (z. B. Altlasten `#Ankizin_v5`)
   werden ignoriert.
9. **Groß-/Kleinschreibung:** Tags, die sich nur darin unterscheiden, werden zu einem Knoten
   zusammengefasst (wie Ankis eigene Tag-Suche). Angezeigt wird die zuerst gefundene Schreibweise.
10. **Anzeigenamen:** Unterstriche → Leerzeichen, ein führendes `#` entfällt (`#Fächer` →
    „Fächer“). Präfixe wie `02-` bleiben, weil sie die AMBOSS-Reihenfolge tragen.
11. **AMBOSS-Ansicht zählt alle Karten der getaggten Notizen**, egal in welchem Deck sie liegen.
12. **Deck-Ansicht:** oberstes Deck, dessen Name mit „Ankizin“ beginnt und das ein Unterdeck
    `M2_M3_Klinik` bzw. `M1_Vorklinik…` hat (bei mehreren: das mit den meisten Karten). Nur
    diese Abschnitte werden gezeigt; Meta-Decks wie `!Wie_nutze_ich_das_Deck?` und leere Decks
    nicht. Karten in gefilterten Decks zählen zu ihrem Ursprungsdeck (`odid`).
13. **Vorklinik aus:** die Fächer der Klinik stehen direkt oben. **Vorklinik an:** oben die
    Gruppen „Klinik“ und „Vorklinik“. Das gilt für beide Tabs.
14. **Die Wurzel** (keine Auswahl; seit 31 die oberste Baumzeile) zeigt die ganze Bibliothek bzw. alle Decks mit Kacheln für
    die Fächer und einem An/Aus-Knopf für alles (mit Abfrage ab 500).

## Oberfläche

15. **Suche:** alle Wörter müssen als Teilstring im Knotennamen vorkommen (Groß/klein egal).
    Angezeigt werden Treffer, ihre Pfade (aufgeklappt) und die Teilbäume unter Treffern
    (zugeklappt), damit man in einen gefundenen Knoten hineinschauen kann. Esc leert die Suche,
    ein zweites Esc schließt das Fenster; Cmd/Ctrl+F springt ins Suchfeld.
16. **Sortierung „nach Lernstand“** = Anteil gesehen+gefestigt absteigend; „nach Größe“ =
    Kartenzahl absteigend. Gilt für Baum und Kacheln. Sortierung und Tab werden nur für die
    laufende Sitzung gemerkt; Fenstergröße und Teilung über Ankis Profil.
17. **Neu laden:** Nach einem Schaltvorgang (und nach Undo im Hauptfenster) werden nur die
    Kartenzustände neu gelesen – die Bäume bleiben, Auswahl/Aufklappzustand/Scrollposition
    bleiben erhalten. Bei Änderungen an Notizen, Tags oder Decks, nach einem Sync, beim
    erneuten Öffnen des Fensters und über „Neu laden“ wird alles neu geladen. Während Laden
    oder Schalten laufen, sind weitere Schaltvorgänge kurz gesperrt (Tooltip), damit nie mit
    veralteten Zahlen geplant wird.
18. **Undo im Fenster:** Cmd/Ctrl+Z im Explorer-Fenster ruft Ankis normales Undo auf.

## Einbindung

19. **Tastenkürzel `Ctrl+Alt+A`** (Mac: ⌘⌥A) statt des SPEC-Vorschlags `Ctrl+Shift+E` –
    **Abweichung**, weil `Ctrl+Shift+E` in Anki schon „Exportieren“ ist. Über
    `tastenkuerzel` in der Addon-Konfiguration änderbar; ist das Kürzel beim Start schon belegt,
    wird keins gesetzt.
20. **Onigiri:** Das Addon wird über `all_addon_meta()` gefunden (AnkiWeb-ID oder Name) und nur
    benutzt, wenn Anki es bereits geladen hat – es wird nie selbst importiert/gestartet.
    `register_sidebar_action` kommt vom Paket selbst oder aus dessen `api.sidebar`.
    Hinweis: Onigiri übernimmt Toolbar-Links automatisch als eigene Seitenleisten-Einträge
    (`toolbar.<befehl>`). In Onigiris Einstellungen kann der Explorer deshalb zweimal
    auftauchen (beide archiviert, beide öffnen dasselbe Fenster) – im README steht, welchen man
    aktiviert. Ohne Eingriff in Onigiri lässt sich das nicht vermeiden.
21. **Toolbar-Link** heißt kurz „AnKIzin“, der Menüeintrag „AnKIzin Explorer“.
    Zusätzlich ein Knopf „AnKIzin Explorer öffnen“ unter der Deckliste
    (`deck_browser_will_render_content`); Onigiri zeigt ihn als externes Widget. Abschaltbar
    über `knopf_startseite`.
22. **manifest.json:** `min_point_version` 250200 (Anki 25.02), kein `max_point_version`,
    `homepage` leer (trägt der Owner beim Upload ein).

## Oberfläche und Performance (nach dem ersten Test)

23. **Stylesheet nur auf Kopf, Banner, Suche und Kacheln**, nicht aufs ganze Fenster. Ein
    Stylesheet auf einem Vorfahren schickt auch den Baum durch Qts Stylesheet-Pfad; das
    kostete gemessen ~40 % pro Scroll-Frame.
24. **Ringe im Baum aus einem Pixmap-Cache** (Anteile auf ein Grad gerundet), Zeilenhintergrund
    nur über `PE_PanelItemViewItem`. Zusammen mit 23: Scroll-Frame im Baum ~8 ms → ~4 ms
    (offscreen gemessen, 4.100 Knoten).
25. **Kacheln als Raster:** Spaltenzahl aus der Breite (min. 200 px), Kacheln füllen die Zeile.
    Titel immer zwei Zeilen hoch (Umbruch an Leerzeichen/Bindestrich, zu lange Wörter
    notfalls im Wort, Rest „…“, voller Name im Tooltip), Status einzeilig in Kurzform
    („69 % aktiv“). „›“ für Unterthemen als eigenes Element.
26. **Kopf mit fester Höhe:** Pfad einzeilig, mittlere Teile fallen bei Platzmangel zu „…“
    weg (voller Pfad im Tooltip); Titel höchstens zwei Zeilen.
27. **Baum:** linker Bereich mindestens 280 px, Splitter nicht zuklappbar, Lernstand-Spalte
    aus der Schriftbreite berechnet, Zahl wird notfalls gekürzt. Startfokus auf dem Baum,
    der Banner-Knopf („Nachzügler aktivieren“) bekommt nur per Tab den Fokus.
28. **Begriffe:** Gesamtfortschritt heißt „gelernt“ (= gesehen + gefestigt), „gesehen“ nur noch
    für die Stufe < 21 Tage. Kopf: „54 von 148 gelernt“, darunter eine Legende in den
    Ringfarben („● 94 neu ● 29 gesehen ● 25 gefestigt“); reicht die Breite nicht, entfallen
    die Wörter, Zahlen und Punkte bleiben. Kacheln „29 von 56 gelernt“, Baum weiter „54/148“.
29. **Kacheln mit Tri-State-Checkbox** statt „Aktivieren/Aussetzen“-Knopf, links in der
    Titelzeile; Ring, Zahlen und Status darunter (so bleibt dem Titel die Breite). Gleiche
    Logik wie im Baum: Zustand nur aus den Karten, ein Klick ändert die Anzeige nicht selbst,
    sondern schaltet (☐/◐ → an, ☑ → aus). Geschaltet wird erst nach dem Mausereignis, weil
    der Neuaufbau die Kachel samt Checkbox ersetzt. Klick auf die Checkbox navigiert nicht.
30. **„…“-Menü** rechts neben der Sortierung mit „Vorklinik anzeigen“ und „Neu laden“
    (Ctrl+R, Mac ⌘R). Das Kürzel ist ein `QShortcut` im Fenster; im Menü wird es nur
    angezeigt (sonst wäre es doppelt belegt). Während des Ladens ist beides gesperrt.
31. **Wurzel als oberste Baumzeile** („AMBOSS-Bibliothek“ bzw. „Decks“) mit Checkbox und
    Ring, immer aufgeklappt (auch nach Neuaufbau, Sortier-/Tabwechsel, „Alles zuklappen“
    und bei der Suche). Beim Öffnen ist sie gewählt; der Pfad-Link auf die Wurzel wählt sie.
    Ihre Checkbox schaltet alles (Abfrage ab 500). Kostet eine Einrückungsstufe.
32. **Statuszeile im Kopf kurz:** „102 von 148 Karten aktiv“, bei eingeschaltetem Knoten mit
    Nachzüglern „ · 12 neue ausgesetzt“. Die ausführliche Form („teilweise aktiv (69 %) ·
    102 aktiv, 46 ausgesetzt · …“) steht im Tooltip und in den Baum-Tooltips.
