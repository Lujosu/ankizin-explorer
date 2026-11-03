from ankizin_explorer.build import (
    amboss_section,
    build_amboss,
    build_decks,
    card_codes,
    pick_root,
    pick_root_deck,
)
from ankizin_explorer.model import Snapshot

from .fixtures import DECKS, KLINIK, ROOT, Builder, sample


def amboss(show_vorklinik=False):
    b, ids = sample()
    view = build_amboss(b.notes, b.cards, show_vorklinik)
    Snapshot(card_codes(b.cards), view, None)
    return view, ids


def node(view, *names):
    n = view.root
    for name in names:
        matches = [c for c in n.children if c.name == name]
        assert matches, f"{name!r} nicht unter {n.name!r}: {[c.name for c in n.children]}"
        n = matches[0]
    return n


def test_root_detected_by_prefix_and_majority():
    b, _ = sample()
    assert pick_root(b.notes) == ROOT.casefold()


def test_root_not_hardcoded():
    b = Builder()
    b.note(["#Ankizin_v7::#M2_M3_Klinik::#AMBOSS::Bibliothek-Klinik::HNO::Otitis_media"])
    view = build_amboss(b.notes, b.cards)
    assert [c.name for c in view.root.children] == ["HNO"]


def test_sections():
    assert amboss_section(KLINIK.split("::")) == "klinik"
    assert amboss_section(f"{ROOT}::#M2_M3_Klinik::#AMBOSS::M2-100-Tage-Lernplan::x".split("::")) is None
    assert (
        amboss_section(f"{ROOT}::#M1_Vorklinik_(work_in_progress)::#AMBOSS::Bibliothek-Vorklinik".split("::"))
        == "vorklinik"
    )


def test_top_level_faecher_and_hidden_meta():
    view, _ = amboss()
    names = sorted(c.name for c in view.root.children)
    assert names == [
        "(fächerübergreifend) Autoimmun- und allergische Erkrankungen",
        "Infektiologie",
        "Innere Medizin",
        "Radiologie",
    ]
    all_names = {n.name for n in view.nodes}
    for meta in ("Projekt Anki", "MARKIERE DIESE KARTEN", "UNIVERSITÄTEN", "M2-100-Tage-Lernplan", "Altlast"):
        assert meta not in all_names


def test_special_characters_in_names():
    view, _ = amboss()
    pbc = node(
        view,
        "(fächerübergreifend) Autoimmun- und allergische Erkrankungen",
        "Primär biliäre Cholangitis (PBC, Primär billiäre Zirrhose, PBZ)",
    )
    assert pbc.search == [("tag", pbc.search[0][1])]
    assert pbc.search[0][1].endswith("Primär_biliäre_Cholangitis_(PBC,_Primär_billiäre_Zirrhose,_PBZ)")
    sal = node(
        view,
        "Infektiologie",
        "Bakterielle Erkrankungen",
        "Systematik der Bakterien",
        "06-Gramnegative Stäbchen",
        "02-Salmonella (Salmonella enterica)",
        "02-Serovar Typhi & Paratyphi",
    )
    assert len(sal.cards) == 2
    assert sal.depth == 7


def test_article_in_several_places_counts_once_per_node():
    view, ids = amboss()
    tb_nodes = [n for n in view.nodes if n.name == "Tuberkulose"]
    assert len(tb_nodes) == 3
    for n in tb_nodes:
        assert sorted(n.cards) == sorted(ids["tb"])
    # Root zählt jede Karte nur einmal
    assert len(view.root.cards) == len(set(view.root.cards))
    assert view.root.counts.total == sum(
        len(ids[k]) for k in ("tb", "pneumonie", "lae", "pbc", "salmonella", "pneumo_direct")
    )


def test_intermediate_tag_cards_belong_to_node():
    view, ids = amboss()
    pneumo = node(view, "Innere Medizin", "Pneumologie")
    expected = ids["tb"] + ids["pneumonie"] + ids["lae"] + ids["pneumo_direct"]
    assert sorted(pneumo.cards) == sorted(expected)


def test_counts_stages():
    view, _ = amboss()
    pneumonie = node(
        view, "Innere Medizin", "Pneumologie", "Infektiöse Atemwegserkrankungen", "Pneumonie (Lungenentzündung)"
    )
    c = pneumonie.counts
    assert (c.total, c.new, c.seen, c.mature, c.studied, c.active) == (3, 1, 1, 1, 2, 0)


def test_case_variants_merge():
    b = Builder()
    b.note([f"{KLINIK}::Innere_Medizin::Erkrankungen_des_Blutes_und_der_Blutbildenden_Organe::A"])
    b.note([f"{KLINIK}::Innere_Medizin::Erkrankungen_des_Blutes_und_der_blutbildenden_Organe::A"])
    b.note([f"{KLINIK.lower()}::innere_medizin::X"])
    view = build_amboss(b.notes, b.cards)
    im = view.root.children
    assert len(im) == 1
    assert len(im[0].children) == 2
    assert len(im[0].cards) == 3


def test_vorklinik_toggle():
    view, _ = amboss(show_vorklinik=False)
    assert "Anatomie" not in {n.name for n in view.nodes}
    view, ids = amboss(show_vorklinik=True)
    assert [c.name for c in view.root.children] == ["Klinik", "Vorklinik"]
    vk = node(view, "Vorklinik", "Fächer", "Anatomie", "01-Grundlagen der Anatomie", "Fettgewebe")
    assert list(vk.cards) == ids["vk"]
    assert len(view.by_key) == len(view.nodes)


def test_no_ankizin_returns_none():
    b = Builder()
    b.note(["Anatomie::Neuroanatomie", "tolearn"])
    assert build_amboss(b.notes, b.cards) is None
    assert build_decks([(1, "Default")], b.cards) is None


def test_keys_unique_and_preorder():
    view, _ = amboss(show_vorklinik=True)
    seen = set()
    for n in view.nodes:
        assert n.key not in seen
        if n.parent is not None:
            assert n.parent.key in seen
        seen.add(n.key)


# --- Decks --------------------------------------------------------------------


def decks(show_vorklinik=False, extra_cards=()):
    b, ids = sample()
    cards = list(b.cards) + list(extra_cards)
    view = build_decks(DECKS, cards, show_vorklinik)
    Snapshot(card_codes(cards), None, view)
    return view, ids


def test_deck_root_and_sections():
    assert pick_root_deck(DECKS, [])[1] == "Ankizin"
    view, _ = decks()
    names = [c.name for c in view.root.children]
    # leere Decks (Radiologie, Chirurgie) sind ausgeblendet, Meta-Deck ebenso
    assert sorted(names) == ["Infektiologie und Hygiene", "Innere Medizin"]
    im = [c for c in view.root.children if c.name == "Innere Medizin"][0]
    assert [c.name for c in im.children] == ["Pneumologie"]
    assert im.search == [("deck", "Ankizin::M2_M3_Klinik::Innere_Medizin")]
    assert view.root.search == [("deck", "Ankizin::M2_M3_Klinik")]


def test_deck_subtree_counts_and_filtered_decks():
    filtered = (99001, 99, 30, 14, -1, 0, 0)  # in gefiltertem Deck, Ursprung Pneumologie
    view, ids = decks(extra_cards=[filtered])
    im = [c for c in view.root.children if c.name == "Innere Medizin"][0]
    assert 99001 in im.cards
    assert im.counts.total == len(ids["pneumonie"] + ids["lae"] + ids["pneumo_direct"] + ids["pbc"]) + len(
        ids["meta_only"] + ids["altlast"]
    ) + 1


def test_deck_vorklinik_grouping():
    view, ids = decks(show_vorklinik=True)
    assert sorted(c.name for c in view.root.children) == ["Klinik", "Vorklinik"]
    vk = [c for c in view.root.children if c.name == "Vorklinik"][0]
    assert vk.children[0].name == "Anatomie"
    assert list(vk.children[0].children[0].cards) == ids["vk"]
