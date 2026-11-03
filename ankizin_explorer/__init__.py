"""AnKIzin Explorer – Themen-UI zum Aktivieren/Aussetzen von AnKIzin-Karten.

Nur Einstieg: Die Datenlogik liegt Qt-frei in model/build/logic/text/loader,
die Oberfläche in ui/, die Einbindung in Anki in integration.py.
"""

try:
    from aqt import mw
except ImportError:  # Tests ohne Anki
    mw = None

if mw is not None:
    from . import integration

    integration.setup()
