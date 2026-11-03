# AnKIzin Explorer

Anki-Addon: übersichtliches Themen-UI zum Aktivieren/Aussetzen von AnKIzin-Karten.

- **Spezifikation:** `docs/SPEC.md` ist verbindlich. Vor jeder Designabweichung den Owner fragen.
- **Lokale Fakten** (Profilnamen, Pfade, installierte Addons): `CLAUDE.local.md` (nicht im Repo).

## Aufbau

- `ankizin_explorer/` – das Addon-Paket (das, was in `addons21/` landet).
  `__init__.py` nur Einstieg/Hooks; Datenlogik ohne Qt-Abhängigkeit in eigenen Modulen,
  damit sie mit einfachen Fixtures testbar ist.
- `tests/` – pytest; Logik (Baum bauen, Zustände, „an gewinnt“, Nachzügler) ohne
  laufendes Anki testen.
- `scripts/build.py` – erzeugt `dist/ankizin_explorer.ankiaddon`.

## Entwickeln

- Das Paket ist per Symlink als `addons21/ankizin_explorer` eingehängt; Anki neu starten
  lädt den Code.
- Manuelle Tests im Anki-Profil **„Test“**, nie im Hauptprofil. Ins Hauptprofil erst,
  wenn der Owner zustimmt – Schaltvorgänge verändern dort echte Lerndaten.
- Nie direkt per sqlite in eine Sammlung schreiben, solange Anki läuft. Lesend nur auf
  einer Kopie.
- Andere Addons (insb. Onigiri) nicht verändern; nur deren öffentliche APIs nutzen.

## Datenschutz (öffentliches Repo)

Keine personenbezogenen Daten committen: keine echten Namen, E-Mails, Uni, absolute Pfade
mit Benutzernamen, Screenshots privater Decks. Commits laufen mit der GitHub-noreply-Adresse
(in der Repo-Git-Config gesetzt). Vor jedem Push `git grep` auf persönliche Begriffe aus
`CLAUDE.local.md`.
