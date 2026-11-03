"""Anzeige-Texte, Zahlformat, Suche und Sortierung (ohne Qt)."""

from __future__ import annotations

import re
from typing import Callable, List, Sequence

from .model import Counts, Node

_SPACES = re.compile(r"\s+")


def display_name(segment: str) -> str:
    """Tag-/Deck-Segment für die Anzeige: Unterstriche -> Leerzeichen, führendes # weg."""
    name = _SPACES.sub(" ", segment.replace("_", " ")).strip()
    stripped = name.lstrip("#").strip()
    return stripped or name


def fmt_int(n: int) -> str:
    """Deutsche Tausenderpunkte: 2340 -> „2.340“."""
    return f"{n:,}".replace(",", ".")


def karten(n: int) -> str:
    return f"{fmt_int(n)} Karte" if n == 1 else f"{fmt_int(n)} Karten"


def search_terms(query: str) -> List[str]:
    return [t for t in query.casefold().split() if t]


def name_matches(name: str, terms: Sequence[str]) -> bool:
    """Alle Suchbegriffe müssen im Namen vorkommen (Teilstring, Groß/klein egal)."""
    if not terms:
        return True
    folded = name.casefold()
    return all(t in folded for t in terms)


def filter_keys(nodes: Sequence[Node], query: str):
    """Sichtbare und aufzuklappende Knoten für eine Suche.

    Liefert (sichtbar, aufklappen, treffer) als Mengen von Schlüsseln, oder None ohne
    Suche. Sichtbar sind Treffer, deren Pfade und die Teilbäume unter Treffern
    (zugeklappt), damit man in einen gefundenen Knoten hineinschauen kann. Die Wurzel
    (oberste Baumzeile) ist immer sichtbar und aufgeklappt.
    """
    terms = search_terms(query)
    if not terms:
        return None
    hits = set()
    expand = set()
    under_hit = set()
    # nodes ist Präorder: Eltern kommen vor ihren Kindern
    for n in nodes:
        if n.parent is None:
            expand.add(n.key)
            continue
        if n.parent.key in hits or n.parent.key in under_hit:
            under_hit.add(n.key)
        if name_matches(n.name, terms):
            hits.add(n.key)
            p = n.parent
            while p.parent is not None and p.key not in expand:
                expand.add(p.key)
                p = p.parent
    return hits | expand | under_hit, expand, hits


SORT_ALPHA = "alpha"
SORT_SIZE = "size"
SORT_PROGRESS = "progress"
SORT_LABELS = {
    SORT_ALPHA: "Alphabetisch",
    SORT_SIZE: "Nach Größe",
    SORT_PROGRESS: "Nach Lernstand",
}


def _progress(c: Counts) -> float:
    return c.studied / c.total if c.total else 0.0


def sort_key(mode: str) -> Callable[[Node], tuple]:
    if mode == SORT_SIZE:
        return lambda n: (-n.counts.total, n.name.casefold())
    if mode == SORT_PROGRESS:
        return lambda n: (-_progress(n.counts), -n.counts.total, n.name.casefold())
    return lambda n: (n.name.casefold(), n.name)


def sorted_children(node: Node, mode: str) -> List[Node]:
    return sorted(node.children, key=sort_key(mode))


def state_label(state: str) -> str:
    return {"on": "aktiv", "partial": "teilweise aktiv", "off": "ausgesetzt"}[state]


def learned_text(c: Counts) -> str:
    """Gesamtfortschritt: „54 von 148 gelernt“ (gelernt = gesehen + gefestigt)."""
    return f"{fmt_int(c.studied)} von {fmt_int(c.total)} gelernt"


def active_text(c: Counts) -> str:
    """Kurzer Schaltzustand: „102 von 148 Karten aktiv“."""
    return f"{fmt_int(c.active)} von {karten(c.total)} aktiv"


def counts_tooltip(c: Counts) -> str:
    return "\n".join(
        [
            f"Gelernt: {fmt_int(c.studied)} von {karten(c.total)} (gesehen + gefestigt)",
            f"Neu: {fmt_int(c.new)}",
            f"Gesehen (< 21 Tage): {fmt_int(c.seen)}",
            f"Gefestigt (≥ 21 Tage): {fmt_int(c.mature)}",
            f"Aktiv: {fmt_int(c.active)} · Ausgesetzt: {fmt_int(c.suspended)}",
        ]
        + ([f"Davon neu und ausgesetzt: {fmt_int(c.suspended_new)}"] if c.suspended_new else [])
    )
