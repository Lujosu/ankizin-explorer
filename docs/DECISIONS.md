# Entscheidungen bei der Umsetzung (v1)

Punkte, die `SPEC.md` offen lässt oder die beim Bauen präzisiert werden mussten.
Jeweils: Entscheidung – Begründung. Abweichungen von der SPEC sind als **Abweichung** markiert.

## Logik

1. **„An gewinnt“: Ein anderer Knoten schützt nur, wenn er auch außerhalb des
   auszuschaltenden Knotens eingeschaltet ist.** (Präzisierung von SPEC 3, bitte bestätigen)
   Beim Ausschalten von Knoten N bleibt eine Karte aktiv, wenn sie in einem Knoten M liegt,
   der weder Vorfahr noch Nachfahr von N ist und bei dem ≥ 90 % der Karten *außerhalb von N*
   aktiv sind.
   *Warum:* Wörtlich genommen („M ist ≥ 90 % aktiv“) wird jeder Artikel, der zusätzlich unter
   einem anderen Fach hängt, durch das Einschalten von N selbst „an“ – und schützt dann beim
   Ausschalten von N seine Karten. Gemessen an einer echten AnKIzin-Sammlung: „Innere Medizin
   an, dann aus“ hätte 18.422 von 20.064 Karten aktiv gelassen (Pharmakologie 2.438 von
   3.162, Neurologie 3.877 von 4.962). Mit der Präzisierung stellt An/Aus den alten Zustand
   wieder her, und ein wirklich separat eingeschaltetes Thema (z. B. Infektiologie) behält
   seine gemeinsamen Karten mit Innere Medizin weiterhin. Ein Knoten, dessen Karten alle in N
   liegen, schützt nie.
2. **Klick auf ☐ oder ◐ aktiviert, Klick auf ☑ setzt aus.** Gilt für Checkbox, Kopf-Knopf und
   Kachel-Knopf. Der Knopf heißt entsprechend „Aktivieren“ bzw. „Aussetzen“.
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
14. **Die Wurzel** (keine Auswahl) zeigt die ganze Bibliothek bzw. alle Decks mit Kacheln für
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
22. **manifest.json:** `min_point_version` 250200 (Anki 25.02), kein `max_point_version`,
    `homepage` leer (trägt der Owner beim Upload ein).
