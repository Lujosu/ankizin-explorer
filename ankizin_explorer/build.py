"""Bäume aus Roh-Zeilen bauen (ohne Qt/Anki).

Eingaben sind einfache Tupel, wie sie per SQL aus der Sammlung kommen:
- Notizen: (nid, tags) mit Ankis leerzeichengetrenntem Tag-String
- Karten: (cid, nid, did, odid, queue, type, ivl)
- Decks: (did, name) mit „::“ als Trenner
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .model import Node, View, card_code
from .text import display_name

ROOT_PREFIX = "#ankizin_v"
SEP = "::"

KLINIK = "klinik"
VORKLINIK = "vorklinik"
SECTION_NAMES = {KLINIK: "Klinik", VORKLINIK: "Vorklinik"}

CardRow = Tuple[int, int, int, int, int, int, int]


def card_codes(cards: Iterable[CardRow]) -> Dict[int, int]:
    return {c[0]: card_code(c[4], c[5], c[6]) for c in cards}


# --- AMBOSS-Bibliothek ---------------------------------------------------------


def amboss_section(segments: Sequence[str]) -> Optional[str]:
    """Abschnitt eines AnKIzin-Tags (Segmente inkl. Root) oder None.

    Klinik:    <ROOT>::#M2_M3_Klinik::#AMBOSS::Bibliothek-Klinik::…
    Vorklinik: <ROOT>::#M1_Vorklinik_(work_in_progress)::#AMBOSS::Bibliothek-Vorklinik::…
    """
    if len(segments) < 4 or segments[2].casefold() != "#amboss":
        return None
    s1 = segments[1].casefold()
    lib = segments[3].casefold()
    if s1 == "#m2_m3_klinik" and lib == "bibliothek-klinik":
        return KLINIK
    if s1.startswith("#m1_vorklinik") and lib == "bibliothek-vorklinik":
        return VORKLINIK
    return None


_LIB_MARK = "::#AMBOSS::Bibliothek-"
_LIB_MARK_LOWER = _LIB_MARK.lower()


def _library_tags(tags: str) -> List[str]:
    """Tags mit …::#AMBOSS::Bibliothek-… aus Ankis Tag-String.

    Schneller Weg: die übliche Schreibweise per str.find suchen, ohne den ganzen
    (oft mehrere KB langen) String zu zerlegen. Nur wenn das nichts findet, wird
    Groß/klein-unabhängig gesucht.
    """
    found = []
    i = tags.find(_LIB_MARK)
    while i != -1:
        start = tags.rfind(" ", 0, i) + 1
        end = tags.find(" ", i)
        if end == -1:
            end = len(tags)
        found.append(tags[start:end])
        i = tags.find(_LIB_MARK, end)
    if not found and _LIB_MARK_LOWER in tags.lower():
        found = [t for t in tags.split() if _LIB_MARK_LOWER in t.lower()]
    return found


def _amboss_tags(tags: str):
    """(root_casefold, section, segments) für jeden Bibliotheks-Tag einer Notiz."""
    for tag in _library_tags(tags):
        if not tag[:10].casefold().startswith(ROOT_PREFIX):
            continue
        segs = tag.split(SEP)
        section = amboss_section(segs)
        if section is not None:
            yield segs[0].casefold(), section, segs


def _parse_notes(notes: Iterable[Tuple[int, str]]):
    parsed = []
    for nid, tags in notes:
        found = list(_amboss_tags(tags))
        if found:
            parsed.append((nid, found))
    return parsed


def _pick_root_parsed(parsed) -> Optional[str]:
    per_root: Dict[str, int] = defaultdict(int)
    for _nid, found in parsed:
        for root in {r for r, _s, _g in found}:
            per_root[root] += 1
    if not per_root:
        return None
    return max(per_root.items(), key=lambda kv: (kv[1], kv[0]))[0]


def pick_root(notes: Iterable[Tuple[int, str]]) -> Optional[str]:
    """Root-Tag (casefold) mit den meisten Notizen in der Bibliothek, z. B. #ankizin_vankicollab."""
    return _pick_root_parsed(_parse_notes(notes))


def build_amboss(
    notes: Sequence[Tuple[int, str]],
    cards: Sequence[CardRow],
    show_vorklinik: bool = False,
) -> Optional[View]:
    parsed = _parse_notes(notes)
    root_tag = _pick_root_parsed(parsed)
    if root_tag is None:
        return None
    sections = [KLINIK, VORKLINIK] if show_vorklinik else [KLINIK]
    grouped = show_vorklinik

    cards_by_nid: Dict[int, List[int]] = defaultdict(list)
    for c in cards:
        cards_by_nid[c[1]].append(c[0])

    root = Node((), "AMBOSS-Bibliothek", None)
    # Trie: Knoten -> {Segment casefold -> Kind}; Abschnittsanfänge je Abschnitt
    kids: Dict[Node, Dict[str, Node]] = {root: {}}
    section_nodes: Dict[str, Node] = {}
    section_tags: Dict[str, str] = {}
    folded: Dict[str, str] = {}

    for nid, found in parsed:
        hit = set()
        in_view = False
        for root_cf, section, segs in found:
            if root_cf != root_tag or section not in sections:
                continue
            in_view = True
            node = section_nodes.get(section)
            if node is None:
                section_tag = SEP.join(segs[:4])
                section_tags[section] = section_tag
                if grouped:
                    node = Node((section,), SECTION_NAMES[section], root, [("tag", section_tag)])
                    kids[node] = {}
                else:
                    node = root
                section_nodes[section] = node
            if node is not root:
                hit.add(node)
            for i in range(4, len(segs)):
                seg = segs[i]
                if not seg:
                    break
                cf = folded.get(seg)
                if cf is None:
                    cf = folded[seg] = seg.casefold()
                children = kids[node]
                child = children.get(cf)
                if child is None:
                    key = (node.key or (section,)) + (cf,)
                    child = Node(key, display_name(seg), node, [("tag", SEP.join(segs[: i + 1]))])
                    children[cf] = child
                    kids[child] = {}
                node = child
                hit.add(node)
        if not in_view:
            continue
        cids = cards_by_nid.get(nid, ())
        root.cards.extend(cids)
        for node in hit:
            node.cards.extend(cids)

    if not root.cards:
        return None
    root.search = [("tag", section_tags[s]) for s in sections if s in section_tags]
    return View("amboss", root)


# --- Deck-Baum -----------------------------------------------------------------


def _deck_section(segment: str) -> Optional[str]:
    s = segment.casefold()
    if s == "m2_m3_klinik":
        return KLINIK
    if s.startswith("m1_vorklinik"):
        return VORKLINIK
    return None


def pick_root_deck(
    decks: Sequence[Tuple[int, str]], cards: Sequence[CardRow]
) -> Optional[Tuple[int, str]]:
    """Oberstes Deck „Ankizin…“ mit Klinik-/Vorklinik-Unterdeck und den meisten Karten."""
    tops = {}
    for did, name in decks:
        segs = name.split(SEP)
        if len(segs) == 1 and name.casefold().startswith("ankizin"):
            tops[name.casefold()] = (did, name)
    with_sections = set()
    for _did, name in decks:
        segs = name.split(SEP)
        if len(segs) >= 2 and segs[0].casefold() in tops and _deck_section(segs[1]):
            with_sections.add(segs[0].casefold())
    if not with_sections:
        return None
    did_top = {}
    for did, name in decks:
        top = name.split(SEP)[0].casefold()
        if top in with_sections:
            did_top[did] = top
    per_top: Dict[str, int] = defaultdict(int)
    for c in cards:
        top = did_top.get(c[3] or c[2])
        if top:
            per_top[top] += 1
    best = max(with_sections, key=lambda t: (per_top.get(t, 0), t))
    return tops[best]


def build_decks(
    decks: Sequence[Tuple[int, str]],
    cards: Sequence[CardRow],
    show_vorklinik: bool = False,
) -> Optional[View]:
    picked = pick_root_deck(decks, cards)
    if picked is None:
        return None
    _root_did, root_name = picked
    root_cf = root_name.casefold()
    sections = [KLINIK, VORKLINIK] if show_vorklinik else [KLINIK]
    grouped = show_vorklinik

    root = Node((), "Decks", None)
    nodes: Dict[Tuple[str, ...], Node] = {}
    did_key: Dict[int, Tuple[str, ...]] = {}
    section_decks: Dict[str, str] = {}

    # Kürzere Namen zuerst, damit Eltern vor Kindern angelegt werden
    for did, name in sorted(decks, key=lambda d: d[1].count(SEP)):
        segs = name.split(SEP)
        if len(segs) < 2 or segs[0].casefold() != root_cf:
            continue
        section = _deck_section(segs[1])
        if section not in sections:
            continue
        key: Tuple[str, ...] = (section,)
        if len(segs) == 2:
            section_decks.setdefault(section, name)
            if grouped:
                nodes[key] = Node(key, SECTION_NAMES[section], root, [("deck", name)])
            else:
                nodes[key] = root
            did_key[did] = key
            continue
        key = key + tuple(s.casefold() for s in segs[2:])
        parent = nodes.get(key[:-1])
        if parent is None:
            continue
        nodes[key] = Node(key, display_name(segs[-1]), parent, [("deck", name)])
        did_key[did] = key

    for c in cards:
        key = did_key.get(c[3] or c[2])
        if key is None:
            continue
        cid = c[0]
        root.cards.append(cid)
        while key:
            node = nodes[key]
            if node is not root:
                node.cards.append(cid)
            key = key[:-1]

    if not root.cards:
        return None
    _prune_empty(root)
    root.search = [("deck", section_decks[s]) for s in sections if s in section_decks]
    return View("decks", root)


def _prune_empty(node: Node) -> None:
    node.children = [c for c in node.children if len(c.cards)]
    for c in node.children:
        _prune_empty(c)


def merge_cards(*card_lists: Iterable[CardRow]) -> List[CardRow]:
    seen = set()
    out = []
    for cl in card_lists:
        for c in cl:
            if c[0] not in seen:
                seen.add(c[0])
                out.append(c)
    return out

