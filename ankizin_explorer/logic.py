"""Schaltlogik (SPEC 3): Zustände, „an gewinnt“, Nachzügler, Sicherheitsabfrage."""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Set, Tuple

from .model import CODE_SUSPENDED_NEW, STAGE_NEW, Counts, Node, View, is_suspended_code

ON_THRESHOLD = 0.9
CONFIRM_THRESHOLD = 500

STATE_OFF = "off"
STATE_PARTIAL = "partial"
STATE_ON = "on"


def node_state(c: Counts) -> str:
    """☐ aus (0 % aktiv), ◐ teilweise, ☑ an (100 % aktiv)."""
    if c.total == 0 or c.active == 0:
        return STATE_OFF
    if c.active == c.total:
        return STATE_ON
    return STATE_PARTIAL


def is_switched_on(c: Counts) -> bool:
    """Eingeschaltet für „an gewinnt“ und Nachzügler: ≥ 90 % der Karten aktiv."""
    return c.total > 0 and c.active >= ON_THRESHOLD * c.total


def wants_enable(c: Counts) -> bool:
    """Ziel eines Klicks auf Checkbox/Knopf: alles an, außer es ist schon alles an."""
    return node_state(c) != STATE_ON


class Plan:
    """Ergebnis einer Schaltplanung."""

    def __init__(self, enable: bool, card_ids: List[int], new_cards: int = 0, kept: int = 0):
        self.enable = enable
        self.card_ids = card_ids
        self.new_cards = new_cards  # davon neue Karten (nur beim Aktivieren relevant)
        self.kept = kept  # beim Aussetzen: wegen „an gewinnt“ aktiv gelassen

    @property
    def count(self) -> int:
        return len(self.card_ids)

    def __repr__(self) -> str:
        verb = "an" if self.enable else "aus"
        return f"Plan({verb}, {self.count} Karten, neu={self.new_cards}, behalten={self.kept})"


def plan_enable(node: Node, codes: Dict[int, int]) -> Plan:
    ids = []
    new = 0
    for cid in node.cards:
        code = codes[cid]
        if is_suspended_code(code):
            ids.append(cid)
            if code == CODE_SUSPENDED_NEW:
                new += 1
    return Plan(True, ids, new)


def plan_disable(view: View, node: Node, codes: Dict[int, int]) -> Plan:
    """Alle aktiven Karten des Knotens aussetzen – außer sie liegen in einem anderen
    eingeschalteten Knoten der Ansicht („an gewinnt“).

    „Anderer eingeschalteter Knoten“ heißt: weder Vorfahr noch Nachfahr, und ≥ 90 % seiner
    Karten *außerhalb* des auszuschaltenden Knotens sind aktiv. Ein Knoten, dessen Karten
    alle im auszuschaltenden Knoten liegen (z. B. derselbe Artikel unter einem anderen
    Fach), ist nur durch diesen „an“ und schützt deshalb nicht – sonst bliebe nach
    „Fach an, Fach aus“ der Großteil des Fachs aktiv (siehe docs/DECISIONS.md).
    """
    inside = set(node.cards)
    candidates = {cid for cid in inside if not is_suspended_code(codes[cid])}
    protected: Set[int] = set()
    if candidates:
        # Präorder-Lauf; schützt ein unabhängiger Elternknoten, deckt er seinen
        # Teilbaum ab und die Kinder müssen nicht mehr geprüft werden.
        covered: Set[Tuple[str, ...]] = set()
        for other in view.nodes:
            if other.parent is not None and other.parent.key in covered:
                covered.add(other.key)
                continue
            if other is node or other.parent is None:
                continue
            if other.is_ancestor_of(node) or node.is_ancestor_of(other):
                continue
            if not other.counts.active:
                continue
            shared = []
            outside = outside_active = 0
            for cid in other.cards:
                if cid in inside:
                    if cid in candidates:
                        shared.append(cid)
                else:
                    outside += 1
                    if not is_suspended_code(codes[cid]):
                        outside_active += 1
            if not shared or not outside or outside_active < ON_THRESHOLD * outside:
                continue
            covered.add(other.key)
            protected.update(shared)
    ids = [cid for cid in candidates if cid not in protected]
    ids.sort()
    return Plan(False, ids, kept=len(protected))


def plan_toggle(view: View, node: Node, codes: Dict[int, int]) -> Plan:
    if wants_enable(node.counts):
        return plan_enable(node, codes)
    return plan_disable(view, node, codes)


def stragglers(view: View, codes: Dict[int, int]) -> Tuple[int, List[int]]:
    """Neue ausgesetzte Karten in eingeschalteten Themen (SPEC 3.1).

    Jede Karte zählt nur auf der tiefsten Ebene, an der sie hängt: Für jeden
    eingeschalteten Knoten (≥ 90 %) werden die neuen ausgesetzten Karten genommen, die
    in keinem seiner Kinder liegen. Karten in ausgeschalteten Unterthemen eines
    eingeschalteten Fachs bleiben so unberührt. Liefert (Anzahl Themen, Karten-IDs).
    """
    topics = 0
    found: Set[int] = set()
    for node in view.nodes:
        c = node.counts
        if not c.suspended_new or not is_switched_on(c):
            continue
        susp_new = [cid for cid in node.cards if codes[cid] == CODE_SUSPENDED_NEW]
        if node.children:
            in_children: Set[int] = set()
            for ch in node.children:
                in_children.update(ch.cards)
            susp_new = [cid for cid in susp_new if cid not in in_children]
        if susp_new:
            topics += 1
            found.update(susp_new)
    return topics, sorted(found)


def estimate_days(new_cards: int, per_day: Optional[int]) -> Optional[int]:
    if not per_day or per_day <= 0:
        return None
    return math.ceil(new_cards / per_day)


def needs_confirmation(plan: Plan) -> bool:
    return plan.count >= CONFIRM_THRESHOLD


def count_new(card_ids, codes: Dict[int, int]) -> int:
    return sum(1 for cid in card_ids if codes[cid] % 3 == STAGE_NEW)
