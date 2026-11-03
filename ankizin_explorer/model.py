"""Datenmodell ohne Qt- und Anki-Abhängigkeit.

Eine Karte wird auf einen kleinen Code reduziert (Lernstufe + ausgesetzt), ein Knoten
kennt die IDs aller Karten seines Teilbaums. Zählungen werden aus beidem berechnet.
"""

from __future__ import annotations

from array import array
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

# Lernstufen (SPEC 4)
STAGE_NEW = 0
STAGE_SEEN = 1
STAGE_MATURE = 2

MATURE_IVL = 21
QUEUE_SUSPENDED = -1
TYPE_NEW = 0
TYPE_REVIEW = 2

# Code = Stufe + 3, wenn ausgesetzt -> 0..5
SUSPENDED_OFFSET = 3
CODE_SUSPENDED_NEW = STAGE_NEW + SUSPENDED_OFFSET


def card_code(queue: int, ctype: int, ivl: int) -> int:
    if ctype == TYPE_NEW:
        stage = STAGE_NEW
    elif ctype == TYPE_REVIEW and ivl >= MATURE_IVL:
        stage = STAGE_MATURE
    else:
        stage = STAGE_SEEN
    return stage + (SUSPENDED_OFFSET if queue == QUEUE_SUSPENDED else 0)


def is_suspended_code(code: int) -> bool:
    return code >= SUSPENDED_OFFSET


class Counts:
    """Kartenzahlen eines Knotens."""

    __slots__ = ("by_code",)

    def __init__(self, by_code: Optional[Sequence[int]] = None) -> None:
        self.by_code = list(by_code) if by_code is not None else [0] * 6

    @classmethod
    def of(cls, cards: Iterable[int], codes: Dict[int, int]) -> "Counts":
        c = [0, 0, 0, 0, 0, 0]
        for cid in cards:
            c[codes[cid]] += 1
        return cls(c)

    @property
    def total(self) -> int:
        return sum(self.by_code)

    @property
    def active(self) -> int:
        c = self.by_code
        return c[0] + c[1] + c[2]

    @property
    def suspended(self) -> int:
        c = self.by_code
        return c[3] + c[4] + c[5]

    @property
    def new(self) -> int:
        return self.by_code[0] + self.by_code[3]

    @property
    def seen(self) -> int:
        """Gesehen im engeren Sinn: gelernt, Intervall < 21 Tage."""
        return self.by_code[1] + self.by_code[4]

    @property
    def mature(self) -> int:
        return self.by_code[2] + self.by_code[5]

    @property
    def studied(self) -> int:
        """„gesehen“ in der Anzeige „gesehen/gesamt“ = gesehen + gefestigt."""
        return self.seen + self.mature

    @property
    def suspended_new(self) -> int:
        return self.by_code[CODE_SUSPENDED_NEW]

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Counts) and other.by_code == self.by_code

    def __repr__(self) -> str:
        return f"Counts({self.by_code})"


# Browser-Suche eines Knotens: Liste von ("tag" | "deck", Name); mehrere = ODER
SearchSpec = List[Tuple[str, str]]


class Node:
    __slots__ = ("key", "name", "parent", "children", "cards", "search", "counts")

    def __init__(
        self,
        key: Tuple[str, ...],
        name: str,
        parent: Optional["Node"],
        search: Optional[SearchSpec] = None,
    ) -> None:
        self.key = key
        self.name = name
        self.parent = parent
        self.children: List[Node] = []
        self.cards = array("q")
        self.search: SearchSpec = search or []
        self.counts = Counts()
        if parent is not None:
            parent.children.append(self)

    @property
    def depth(self) -> int:
        return len(self.key)

    def path(self) -> List["Node"]:
        """Vorfahren ohne Wurzel, von oben nach unten, inklusive self."""
        out = []
        n: Optional[Node] = self
        while n is not None and n.parent is not None:
            out.append(n)
            n = n.parent
        out.reverse()
        return out

    def is_ancestor_of(self, other: "Node") -> bool:
        """True, wenn self echter Vorfahr von other ist."""
        k = self.key
        return len(k) < len(other.key) and other.key[: len(k)] == k

    def __repr__(self) -> str:
        return f"Node({'::'.join(self.key) or '<root>'}, {len(self.cards)} Karten)"


class View:
    """Ein Baum (AMBOSS-Bibliothek oder Decks)."""

    def __init__(self, view_id: str, root: Node) -> None:
        self.view_id = view_id
        self.root = root
        self.nodes: List[Node] = []  # Präorder, inkl. Wurzel
        self.by_key: Dict[Tuple[str, ...], Node] = {}
        self.reindex()

    def reindex(self) -> None:
        self.nodes = []
        stack = [self.root]
        while stack:
            n = stack.pop()
            self.nodes.append(n)
            stack.extend(reversed(n.children))
        self.by_key = {n.key: n for n in self.nodes}

    def recount(self, codes: Dict[int, int]) -> None:
        for n in self.nodes:
            n.counts = Counts.of(n.cards, codes)

    def structure(self) -> List[Tuple[str, ...]]:
        return [n.key for n in self.nodes]


class Snapshot:
    """Alles, was das Fenster anzeigt; wird im Hintergrund geladen."""

    def __init__(
        self,
        codes: Dict[int, int],
        amboss: Optional[View],
        decks: Optional[View],
        root_deck_id: Optional[int] = None,
    ) -> None:
        self.codes = codes
        self.views: Dict[str, Optional[View]] = {"amboss": amboss, "decks": decks}
        # AnKIzin-Hauptdeck: dessen Deck-Optionen liefern das Limit neuer Karten/Tag
        self.root_deck_id = root_deck_id
        for v in self.views.values():
            if v is not None:
                v.recount(codes)

    def with_codes(self, codes: Dict[int, int]) -> "Snapshot":
        """Gleiche Bäume, neue Kartenzustände. Fehlt eine Karte (gelöscht), bleibt ihr alter Code."""
        merged = dict(self.codes)
        merged.update(codes)
        return Snapshot(merged, self.views["amboss"], self.views["decks"], self.root_deck_id)

    def view(self, view_id: str) -> Optional[View]:
        return self.views.get(view_id)

    @property
    def empty(self) -> bool:
        return all(v is None for v in self.views.values())
