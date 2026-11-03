from ankizin_explorer import logic
from ankizin_explorer.build import build_amboss, build_decks, card_codes
from ankizin_explorer.model import CODE_SUSPENDED_NEW, SUSPENDED_OFFSET, Counts, Snapshot

from .fixtures import DECKS, KLINIK, NEW, SEEN, Builder, sample


class Col:
    """Simuliert suspend/unsuspend auf den Codes eines Snapshots."""

    def __init__(self, builder, show_vorklinik=False):
        self.snap = Snapshot(
            card_codes(builder.cards),
            build_amboss(builder.notes, builder.cards, show_vorklinik),
            build_decks(DECKS, builder.cards, show_vorklinik),
        )

    @property
    def codes(self):
        return self.snap.codes

    def view(self, vid="amboss"):
        return self.snap.view(vid)

    def apply(self, plan):
        codes = {}
        for cid in plan.card_ids:
            stage = self.codes[cid] % SUSPENDED_OFFSET
            codes[cid] = stage if plan.enable else stage + SUSPENDED_OFFSET
        self.snap = self.snap.with_codes(codes)

    def toggle(self, node, vid="amboss"):
        plan = logic.plan_toggle(self.view(vid), node, self.codes)
        self.apply(plan)
        return plan

    def find(self, name, vid="amboss", parent=None):
        hits = [n for n in self.view(vid).nodes if n.name == name and (parent is None or n.parent.name == parent)]
        assert len(hits) == 1, hits
        return hits[0]


def test_states():
    assert logic.node_state(Counts([0, 0, 0, 3, 0, 0])) == logic.STATE_OFF
    assert logic.node_state(Counts([1, 0, 0, 3, 0, 0])) == logic.STATE_PARTIAL
    assert logic.node_state(Counts([1, 2, 3, 0, 0, 0])) == logic.STATE_ON
    assert logic.node_state(Counts()) == logic.STATE_OFF


def test_switched_on_threshold():
    assert logic.is_switched_on(Counts([9, 0, 0, 1, 0, 0]))
    assert not logic.is_switched_on(Counts([8, 0, 0, 2, 0, 0]))
    assert not logic.is_switched_on(Counts())


def test_enable_unsuspends_subtree():
    b, ids = sample()
    col = Col(b)
    pneumo = col.find("Pneumologie")
    plan = col.toggle(pneumo)
    assert plan.enable
    assert sorted(plan.card_ids) == sorted(ids["tb"] + ids["pneumonie"] + ids["lae"] + ids["pneumo_direct"])
    assert plan.new_cards == 4
    assert logic.node_state(col.find("Pneumologie").counts) == logic.STATE_ON
    # Tuberkulose ist auch unter Infektiologie aktiv geworden -> dort teilweise
    assert logic.node_state(col.find("Infektiologie").counts) == logic.STATE_PARTIAL


def test_disable_suspends_everything_including_learned():
    b, ids = sample()
    col = Col(b)
    pneumonie = col.find("Pneumonie (Lungenentzündung)")
    col.toggle(pneumonie)
    plan = col.toggle(pneumonie)
    assert not plan.enable
    assert sorted(plan.card_ids) == sorted(ids["pneumonie"])
    assert col.find("Pneumonie (Lungenentzündung)").counts.active == 0
    # Lernstand bleibt erhalten
    assert col.find("Pneumonie (Lungenentzündung)").counts.mature == 1


def test_on_wins_over_other_switched_on_node():
    b, ids = sample()
    col = Col(b)
    col.toggle(col.find("Infektiologie"))
    col.toggle(col.find("Pneumologie"))
    plan = col.toggle(col.find("Pneumologie"))
    assert not plan.enable
    assert plan.kept == len(ids["tb"])
    assert not set(ids["tb"]) & set(plan.card_ids)
    for cid in ids["tb"]:
        assert col.codes[cid] < SUSPENDED_OFFSET
    assert logic.node_state(col.find("Infektiologie").counts) == logic.STATE_ON


def test_on_wins_ignores_ancestors_and_descendants():
    b, ids = sample()
    col = Col(b)
    col.toggle(col.find("Innere Medizin"))
    # Ausschalten eines Kindes: eingeschalteter Elternknoten schützt nicht
    plan = col.toggle(col.find("Lungenembolie (Lungenarterienembolie, LAE)"))
    assert plan.card_ids == ids["lae"] and plan.kept == 0
    # Ausschalten des Elternknotens: eingeschaltete Kinder schützen nicht
    col.toggle(col.find("Innere Medizin"))
    plan = col.toggle(col.find("Innere Medizin"))
    assert not plan.enable and plan.kept == 0
    assert col.find("Innere Medizin").counts.active == 0


def test_round_trip_restores_state():
    """Fach an, Fach aus: Artikel, die auch woanders hängen, schützen sich nicht selbst."""
    b, ids = sample()
    col = Col(b)
    before = dict(col.codes)
    col.toggle(col.find("Innere Medizin"))
    # Tuberkulose unter Infektiologie/Radiologie ist jetzt rein abgeleitet „an“
    tb_inf = [n for n in col.view().nodes if n.name == "Tuberkulose" and n.parent.name == "Bakterielle Erkrankungen"][0]
    assert logic.node_state(tb_inf.counts) == logic.STATE_ON
    plan = col.toggle(col.find("Innere Medizin"))
    assert plan.kept == 0
    assert col.codes == before


def test_partially_on_node_does_not_protect():
    b = Builder()
    shared = b.note([f"{KLINIK}::A::X", f"{KLINIK}::B::X"], [(NEW, True)])
    other = b.note([f"{KLINIK}::B::Y"], [(NEW, True)] * 3)
    col = Col(b)
    col.apply(logic.plan_enable(col.find("A"), col.codes))
    # B ist zu 25 % aktiv -> nicht eingeschaltet -> schützt die geteilte Karte nicht
    plan = col.toggle(col.find("A"))
    assert plan.card_ids == shared and plan.kept == 0
    assert other


def test_switched_on_at_90_percent_protects():
    b = Builder()
    shared = b.note([f"{KLINIK}::A::X", f"{KLINIK}::B::X"], [(NEW, True)])
    b.note([f"{KLINIK}::B::Y"], [(NEW, True)] * 9)
    late = b.note([f"{KLINIK}::B::Z"], [(NEW, True)])
    col = Col(b)
    col.apply(logic.plan_enable(col.find("B"), col.codes))
    col.apply(logic.Plan(False, late))
    assert logic.node_state(col.find("B").counts) == logic.STATE_PARTIAL
    plan = col.toggle(col.find("A"))  # A ist an (geteilte Karte aktiv) -> ausschalten
    assert not plan.enable and plan.card_ids == [] and plan.kept == len(shared)


def test_toggle_partial_enables():
    b, ids = sample()
    col = Col(b)
    col.apply(logic.Plan(True, ids["tb"]))
    assert logic.node_state(col.find("Pneumologie").counts) == logic.STATE_PARTIAL
    plan = col.toggle(col.find("Pneumologie"))
    assert plan.enable


def test_stragglers_deepest_only():
    b = Builder()
    old = b.note([f"{KLINIK}::Fach::Thema::Artikel"], [(SEEN, True)] * 19)
    new = b.note([f"{KLINIK}::Fach::Thema::Artikel"], [(NEW, True)])
    off = b.note([f"{KLINIK}::Fach::Anderes_Thema"], [(NEW, True)])
    col = Col(b)
    col.apply(logic.Plan(True, old))
    topics, cards = logic.stragglers(col.view(), col.codes)
    # Artikel ist zu 95 % aktiv; Thema/Fach ebenfalls ≥ 90 %, zählen aber nicht doppelt.
    assert (topics, cards) == (1, new)
    assert off  # Karte im nie eingeschalteten Nachbarthema ist kein Nachzügler


def test_stragglers_ignore_switched_off_child_of_active_parent():
    b = Builder()
    on = b.note([f"{KLINIK}::Fach::A"], [(SEEN, True)] * 30)
    b.note([f"{KLINIK}::Fach::B"], [(NEW, True)] * 2)
    col = Col(b)
    col.apply(logic.Plan(True, on))
    assert logic.is_switched_on(col.find("Fach").counts)
    assert logic.stragglers(col.view(), col.codes) == (0, [])


def test_stragglers_direct_tag_on_parent():
    b = Builder()
    active = b.note([f"{KLINIK}::Fach"], [(SEEN, True)] * 10)
    late = b.note([f"{KLINIK}::Fach"], [(NEW, True)])
    col = Col(b)
    col.apply(logic.Plan(True, active))
    assert logic.stragglers(col.view(), col.codes) == (1, late)


def test_stragglers_multi_location_counted_once():
    b = Builder()
    a = b.note([f"{KLINIK}::A::X"], [(SEEN, True)] * 10)
    c = b.note([f"{KLINIK}::B::X"], [(SEEN, True)] * 10)
    late = b.note([f"{KLINIK}::A::X", f"{KLINIK}::B::X"], [(NEW, True)])
    col = Col(b)
    col.apply(logic.Plan(True, a + c))
    topics, cards = logic.stragglers(col.view(), col.codes)
    assert topics == 2 and cards == late
    assert col.codes[late[0]] == CODE_SUSPENDED_NEW


def test_stragglers_decks_view():
    b = Builder()
    active = b.note(["x"], [(SEEN, True)] * 10, did=14)
    late = b.note(["x"], [(NEW, True)], did=14)
    col = Col(b)
    col.apply(logic.Plan(True, active))
    assert logic.stragglers(col.view("decks"), col.codes) == (1, late)


def test_confirmation_and_estimate():
    assert not logic.needs_confirmation(logic.Plan(True, list(range(499))))
    assert logic.needs_confirmation(logic.Plan(True, list(range(500))))
    assert logic.estimate_days(2340, 20) == 117
    assert logic.estimate_days(2340, 0) is None
    assert logic.estimate_days(2340, None) is None


def test_decks_disable_root_and_enable_fach():
    b, ids = sample()
    col = Col(b)
    im = col.find("Innere Medizin", vid="decks")
    plan = col.toggle(im, vid="decks")
    assert plan.enable and len(plan.card_ids) == im.counts.total
    root = col.view("decks").root
    plan = col.toggle(root, vid="decks")
    assert plan.enable  # Root war nur teilweise an
