# AnKIzin Explorer

Ein Anki-Addon, das das [AnKIzin](https://ankizin.de)-Deck übersichtlich nach Themen
schaltbar macht: AMBOSS-Bibliotheksstruktur als Baum, Lernstand pro Thema, ein Klick zum
Aktivieren oder Aussetzen – statt sich durch den Tag-Explorer zu klicken.

> Status: v1. Design siehe [docs/SPEC.md](docs/SPEC.md), Umsetzungsentscheidungen in
> [docs/DECISIONS.md](docs/DECISIONS.md).

## Funktionen (v1)

- Baum nach AMBOSS-Bibliothek (Standard) oder nach Deck-Struktur
- Live-Suche über alle Themen; Artikel, die an mehreren Stellen hängen, erscheinen überall
- Pro Thema: Ring mit Lernstand (neu / gesehen / gefestigt) und Kartenzahlen
- Übersicht eines Themas mit allen Unterblöcken als Kacheln
- Aktivieren/Aussetzen ganzer Themen, Rückgängig mit Ctrl/Cmd+Z
- „An gewinnt“: Beim Aussetzen bleiben Karten aktiv, die auch in einem anderen aktiven Thema
  liegen
- Sicherheitsabfrage ab 500 Karten mit Schätzung, wie viele Tage die neuen Karten bei deinem
  Tageslimit brauchen
- Hinweis auf neue ausgesetzte Karten in aktiven Themen nach AnKIzin-Updates
- Funktioniert in normalem Anki; mit [Onigiri](https://ankiweb.net/shared/info/1011095603)
  zusätzlich als Eintrag in dessen Seitenleiste

## Benutzung

- **Extras → AnKIzin Explorer** (Kürzel Ctrl+Alt+A, am Mac ⌘⌥A) oder der Link **AnKIzin** in
  der oberen Leiste.
- Checkbox im Baum oder Knopf in der Übersicht: ☐/◐ → aktivieren, ☑ → aussetzen. Ein
  Oberthema schaltet seinen ganzen Teilbaum.
- Aussetzen behält den Lernstand; Deck-Optionen werden nie verändert, das Tageslimit für neue
  Karten regelt weiter Anki.
- Rechtsklick auf ein Thema: „Im Browser zeigen“.
- Einstellung „Vorklinik anzeigen“ direkt im Fenster oder unter *Extras → Add-ons →
  AnKIzin Explorer → Konfiguration*.

### Mit Onigiri

Externe Einträge sind in Onigiri zunächst archiviert. In Onigiris Einstellungen beim
Seitenleisten-Layout den Eintrag **„AnKIzin Explorer“** (mit Baum-Symbol) aktivieren. Onigiri
übernimmt außerdem den Toolbar-Link „AnKIzin“ als eigenen Eintrag – beide öffnen dasselbe
Fenster, einer reicht.

## Entwicklung

- `ankizin_explorer/` ist das Addon-Paket (Datenlogik ohne Qt in `model`, `build`, `logic`,
  `text`, `loader`; Oberfläche in `ui/`; Anki-Einbindung in `integration.py`).
- Tests der Datenlogik (ohne Anki):

  ```bash
  python3 -m pytest tests
  ```

- Zusätzlich gegen Ankis Backend und Qt (offscreen), mit den Paketen einer Anki-Installation
  und passender Python-Version (Anki 26.x: Python 3.13):

  ```bash
  QT_QPA_PLATFORM=offscreen PYTHONPATH=/Applications/Anki.app/Contents/Resources/app_packages python3.13 -m pytest tests
  ```

- Paket bauen (`dist/ankizin_explorer.ankiaddon`):

  ```bash
  python3 scripts/build.py
  ```

## Lizenz

AGPL-3.0, siehe [LICENSE](LICENSE).
