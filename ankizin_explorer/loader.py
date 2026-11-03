"""Daten einmal per SQL aus der Sammlung laden (SPEC 7).

Braucht nur ein Objekt mit `db.all(sql)` und `decks.all_names_and_ids()` bzw.
`decks.config_dict_for_deck_id()`; läuft im Hintergrund-Thread von QueryOp.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from .build import build_amboss, build_decks, card_codes, merge_cards, pick_root_deck
from .model import Snapshot, card_code

# LIKE ist in SQLite für ASCII ohnehin case-insensitiv; die genaue Prüfung macht build.py.
NOTES_SQL = "select id, tags from notes where tags like '%::#AMBOSS::Bibliothek-%'"
# Alle Karten in einem Rutsch: kleine Zeilen, schneller als ein zweiter Scan über notes
CARDS_SQL = "select id, nid, did, odid, queue, type, ivl from cards"


def load_decks(col) -> List[Tuple[int, str]]:
    return [(int(d.id), d.name) for d in col.decks.all_names_and_ids()]


def ankizin_deck_ids(decks: Sequence[Tuple[int, str]]) -> List[int]:
    """Alle Decks unter einem obersten „Ankizin…“-Deck (Kandidaten für den Deck-Baum)."""
    return [did for did, name in decks if name.split("::")[0].casefold().startswith("ankizin")]


def new_per_day(col, did: int) -> Optional[int]:
    try:
        return int(col.decks.config_dict_for_deck_id(did)["new"]["perDay"])
    except Exception:
        return None


def load_snapshot(col, show_vorklinik: bool = False) -> Snapshot:
    notes = [(int(r[0]), r[1]) for r in col.db.all(NOTES_SQL)]
    decks = load_decks(col)
    deck_ids = set(ankizin_deck_ids(decks))
    nids = {nid for nid, _tags in notes}

    note_cards: List[tuple] = []
    deck_cards: List[tuple] = []
    for r in col.db.all(CARDS_SQL):
        row = tuple(r)
        if row[1] in nids:
            note_cards.append(row)
        if (row[3] or row[2]) in deck_ids:
            deck_cards.append(row)

    amboss = build_amboss(notes, note_cards, show_vorklinik)
    deck_view = build_decks(decks, deck_cards, show_vorklinik)
    codes = card_codes(merge_cards(note_cards, deck_cards))

    root_deck = pick_root_deck(decks, deck_cards)
    return Snapshot(codes, amboss, deck_view, root_deck[0] if root_deck else None)


STATES_SQL = "select id, queue, type, ivl from cards"


def load_codes(col, known: Snapshot) -> dict:
    """Nur Kartenzustände neu lesen (nach einem Schaltvorgang; Bäume bleiben gleich)."""
    codes = known.codes
    fresh = {}
    for cid, queue, ctype, ivl in col.db.all(STATES_SQL):
        if cid in codes:
            fresh[cid] = card_code(queue, ctype, ivl)
    return fresh
