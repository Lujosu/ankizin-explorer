from ankizin_explorer import text
from ankizin_explorer.build import build_amboss, card_codes
from ankizin_explorer.model import Snapshot

from .fixtures import sample


def view():
    b, _ = sample()
    v = build_amboss(b.notes, b.cards)
    Snapshot(card_codes(b.cards), v, None)
    return v


def test_display_name():
    assert text.display_name("Innere_Medizin") == "Innere Medizin"
    assert text.display_name("#Fächer") == "Fächer"
    assert text.display_name("02-Serovar_Typhi_&_Paratyphi") == "02-Serovar Typhi & Paratyphi"
    assert text.display_name("Allgemein-,Thorax-_und_Gefäßchirurgie") == "Allgemein-,Thorax- und Gefäßchirurgie"
    assert text.display_name("#") == "#"


def test_fmt_int():
    assert text.fmt_int(2340) == "2.340"
    assert text.fmt_int(49123456) == "49.123.456"
    assert text.karten(1) == "1 Karte"
    assert text.karten(1500) == "1.500 Karten"


def test_search_finds_all_locations_with_paths():
    v = view()
    visible, expand, hits = text.filter_keys(v.nodes, "tuberk")
    tb = [n for n in v.nodes if n.name == "Tuberkulose"]
    assert {n.key for n in tb} == hits
    for n in tb:
        for anc in n.path()[:-1]:
            assert anc.key in expand and anc.key in visible
    assert not any(n.name == "Pneumonie (Lungenentzündung)" and n.key in visible for n in v.nodes)


def test_search_case_umlauts_and_multiple_terms():
    v = view()
    _, _, hits = text.filter_keys(v.nodes, "LUNGENENTZÜNDUNG")
    assert len(hits) == 1
    _, _, hits = text.filter_keys(v.nodes, "typhi paratyphi")
    assert len(hits) == 1
    _, _, hits = text.filter_keys(v.nodes, "(pbc,")
    assert len(hits) == 1
    assert text.filter_keys(v.nodes, "   ") is None


def test_search_keeps_subtree_of_hit_collapsed():
    v = view()
    visible, expand, hits = text.filter_keys(v.nodes, "pneumologie")
    pneumo = [n for n in v.nodes if n.name == "Pneumologie"][0]
    assert pneumo.key in hits and pneumo.key not in expand
    for child in pneumo.children:
        assert child.key in visible


def test_sorting():
    v = view()
    names = [n.name for n in text.sorted_children(v.root, text.SORT_ALPHA)]
    assert names == sorted(names, key=str.casefold)
    by_size = text.sorted_children(v.root, text.SORT_SIZE)
    assert [n.counts.total for n in by_size] == sorted((n.counts.total for n in by_size), reverse=True)
    by_progress = text.sorted_children(v.root, text.SORT_PROGRESS)
    ratios = [n.counts.studied / n.counts.total for n in by_progress]
    assert ratios == sorted(ratios, reverse=True)


def test_tooltip_mentions_all_numbers():
    v = view()
    tip = text.counts_tooltip(v.root.counts)
    for word in ("Gesamt", "Neu", "Gesehen", "Gefestigt", "Aktiv", "Ausgesetzt"):
        assert word in tip
