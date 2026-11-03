"""Tests gegen Ankis echtes Backend und Qt (offscreen).

Laufen nur, wenn `anki`/`aqt` importierbar sind, z. B.:
    QT_QPA_PLATFORM=offscreen PYTHONPATH=/Applications/Anki.app/Contents/Resources/app_packages \
        python3.13 -m pytest tests
"""

from __future__ import annotations

import os
import types

import pytest

anki_collection = pytest.importorskip("anki.collection")

from ankizin_explorer import loader, logic  # noqa: E402

from .fixtures import LAE, PBC, PNEUMONIE, SALMONELLA, TB_INF, TB_PNEUMO, TB_RAD, VK_FETT  # noqa: E402


@pytest.fixture
def col(tmp_path):
    col = anki_collection.Collection(str(tmp_path / "test.anki2"))
    basic = col.models.by_name("Basic")

    def add(tags, deck, n=1):
        did = col.decks.id(deck)
        cids = []
        for i in range(n):
            note = col.new_note(basic)
            note["Front"] = f"{deck} {i}"
            note.tags = list(tags)
            col.add_note(note, did)
            cids += note.card_ids()
        return cids

    add([TB_INF, TB_PNEUMO, TB_RAD], "Ankizin::M2_M3_Klinik::Infektiologie_und_Hygiene", 2)
    add([PNEUMONIE], "Ankizin::M2_M3_Klinik::Innere_Medizin::Pneumologie", 3)
    add([LAE], "Ankizin::M2_M3_Klinik::Innere_Medizin::Pneumologie", 2)
    add([PBC], "Ankizin::M2_M3_Klinik::Innere_Medizin", 1)
    add([SALMONELLA], "Ankizin::M2_M3_Klinik::Infektiologie_und_Hygiene", 2)
    add([VK_FETT], "Ankizin::M1_Vorklinik::Anatomie", 1)
    add(["andere::Tags"], "Default", 2)
    col.sched.suspend_cards(list(col.find_cards("deck:Ankizin")))
    yield col
    col.close()


def node(view, name):
    hits = [n for n in view.nodes if n.name == name]
    assert hits, name
    return hits[0]


def test_loader_on_real_collection(col):
    snap = loader.load_snapshot(col)
    amboss = snap.view("amboss")
    decks = snap.view("decks")
    assert amboss.root.counts.total == 10
    assert decks.root.counts.total == 10
    assert len([n for n in amboss.nodes if n.name == "Tuberkulose"]) == 3
    assert snap.root_deck_id == col.decks.id_for_name("Ankizin")
    assert loader.new_per_day(col, snap.root_deck_id) == 20
    snap_vk = loader.load_snapshot(col, show_vorklinik=True)
    assert snap_vk.view("amboss").root.counts.total == 11


def _apply(col, plan, label):
    pos = col.add_custom_undo_entry(label)
    if plan.enable:
        col.sched.unsuspend_cards(plan.card_ids)
    else:
        col.sched.suspend_cards(plan.card_ids)
    return col.merge_undo_entries(pos)


def test_toggle_and_single_undo_step(col):
    snap = loader.load_snapshot(col)
    view = snap.view("amboss")
    plan = logic.plan_toggle(view, node(view, "Pneumologie"), snap.codes)
    assert plan.enable and plan.count == 7
    changes = _apply(col, plan, "AnKIzin: „Pneumologie“ aktivieren")
    assert changes.card
    assert col.undo_status().undo == "AnKIzin: „Pneumologie“ aktivieren"

    snap = snap.with_codes(loader.load_codes(col, snap))
    view = snap.view("amboss")
    assert logic.node_state(node(view, "Pneumologie").counts) == logic.STATE_ON
    assert logic.node_state(node(view, "Infektiologie").counts) == logic.STATE_PARTIAL

    col.undo()
    snap = snap.with_codes(loader.load_codes(col, snap))
    assert snap.view("amboss").root.counts.active == 0


def test_browser_search_strings_escape(col):
    from anki.collection import SearchNode

    snap = loader.load_snapshot(col)
    view = snap.view("amboss")
    for name, expected in (("Primär biliäre Cholangitis (PBC, Primär billiäre Zirrhose, PBZ)", 1),
                           ("02-Serovar Typhi & Paratyphi", 2), ("Tuberkulose", 2)):
        n = node(view, name)
        kind, value = n.search[0]
        search = col.build_search_string(SearchNode(tag=value))
        assert len(col.find_cards(search)) == expected, search
    deck_node = node(snap.view("decks"), "Innere Medizin")
    search = col.build_search_string(SearchNode(deck=deck_node.search[0][1]))
    assert len(col.find_cards(search)) == deck_node.counts.total


# --- Fenster (offscreen) -------------------------------------------------------------


@pytest.fixture
def window(col, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    qt = pytest.importorskip("aqt.qt")
    app = qt.QApplication.instance() or qt.QApplication([])

    from ankizin_explorer import ops
    from ankizin_explorer.ui import window as win

    fake_mw = types.SimpleNamespace(col=col)
    monkeypatch.setattr(win, "mw", fake_mw)
    for name in ("restoreGeom", "saveGeom", "restoreSplitter", "saveSplitter"):
        monkeypatch.setattr(win, name, lambda *a, **k: None)
    tips = []
    monkeypatch.setattr(win, "tooltip", lambda msg, **k: tips.append(msg))
    asked = []
    monkeypatch.setattr(win, "askUser", lambda text, **k: asked.append(text) or True)
    monkeypatch.setattr(win.config, "show_vorklinik", lambda: False)
    monkeypatch.setattr(win.config, "set_value", lambda *a: None)

    holder = {}

    def load_snapshot(parent, show_vk, on_success, on_failure):
        on_success(loader.load_snapshot(col, show_vk))

    def load_codes(parent, known, on_success, on_failure):
        on_success(known.with_codes(loader.load_codes(col, known)))

    def set_suspended(parent, card_ids, suspend, undo_label, on_done=None):
        pos = col.add_custom_undo_entry(undo_label)
        (col.sched.suspend_cards if suspend else col.sched.unsuspend_cards)(card_ids)
        changes = col.merge_undo_entries(pos)
        holder["w"].on_collection_changed(changes)
        if on_done:
            on_done(True)

    monkeypatch.setattr(ops, "load_snapshot", load_snapshot)
    monkeypatch.setattr(ops, "load_codes", load_codes)
    monkeypatch.setattr(ops, "set_suspended", set_suspended)

    w = win.ExplorerWindow(None)
    holder["w"] = w
    w.show()
    app.processEvents()
    w._tips = tips
    w._asked = asked
    yield w
    w.close()
    w.deleteLater()
    app.processEvents()


def _tops(w):
    """Namen der Fächer = Kinder der Wurzelzeile."""
    assert w.tree.topLevelItemCount() == 1
    root = w.tree.topLevelItem(0)
    return [root.child(i).text(0) for i in range(root.childCount())]


def test_window_tree_detail_search(window):
    w = window
    assert w.pages.currentIndex() == 1
    tops = _tops(w)
    assert tops == sorted(tops, key=str.casefold)
    assert "Innere Medizin" in tops
    # Beim Öffnen ist die Wurzel gewählt: Übersicht mit Kacheln aller Fächer
    assert w.title.text() == "AMBOSS-Bibliothek"
    assert w.tiles_layout.count() == len(tops)
    assert "gelernt" in w.summary.text() and "gesehen" not in w.summary.text()
    assert w.pal.mature.name() in w.legend.text()
    w.resize(1100, 720)
    qt = pytest.importorskip("aqt.qt")
    qt.QApplication.processEvents()
    assert "neu" in w.legend.text() and "gefestigt" in w.legend.text()
    # zu schmal für die Wörter: nur Punkte und Zahlen
    w.legend.resize(60, w.legend.height())
    assert "gefestigt" not in w.legend.text() and w.pal.mature.name() in w.legend.text()
    assert w.status.text() == "0 von 10 Karten aktiv"

    w.search.setText("tuberk")
    w._apply_search()
    visible = [k for k, it in w.items.items() if not it.isHidden()]
    assert sum(1 for k in visible if k and k[-1] == "tuberkulose") == 3

    key = next(k for k in w.items if k and k[-1] == "pneumologie")
    w.navigate(key)
    assert w.title.text() == "Pneumologie"
    assert "Innere Medizin" in w.crumbs.toolTip()
    assert w.tiles_layout.count() == 2  # Infektiöse Atemwegserkrankungen, Lungengefäßerkrankungen


def test_window_toggle_keeps_selection_and_updates(window):
    w = window
    key = next(k for k in w.items if k and k[-1] == "pneumologie")
    w.navigate(key)
    w.items[key].setExpanded(True)
    w.toggle(w.current_node())
    assert w.current_node().key == key
    assert w.items[key].isExpanded()
    assert w.items[key].checkState(0).name == "Checked"
    assert w.toggle_btn.text() == "Aussetzen"
    assert any("aktiviert" in t for t in w._tips)
    # Infektiologie enthält Tuberkulose -> teilweise
    inf = next(k for k in w.items if k == ("klinik", "infektiologie"))
    assert w.items[inf].checkState(0).name == "PartiallyChecked"

    # Checkbox-Klick im Baum schaltet wieder aus
    w.items[key].setCheckState(0, w.items[key].checkState(0).__class__.Unchecked)
    assert w.items[key].checkState(0).name == "Unchecked"
    assert w.snapshot.view("amboss").root.counts.active == 0


def test_window_confirmation_and_banner(window, col):
    w = window
    w.toggle(w.current_node())  # Wurzel: nur 10 Karten -> keine Abfrage
    assert not w._asked
    # neue ausgesetzte Karte in aktivem Thema -> Banner
    basic = col.models.by_name("Basic")
    note = col.new_note(basic)
    note["Front"] = "neu"
    note.tags = [PNEUMONIE]
    col.add_note(note, col.decks.id("Ankizin::M2_M3_Klinik::Innere_Medizin::Pneumologie"))
    # weitere aktive Karten, damit das Thema ≥ 90 % aktiv bleibt
    for i in range(9):
        extra = col.new_note(basic)
        extra["Front"] = f"aktiv {i}"
        extra.tags = [PNEUMONIE]
        col.add_note(extra, col.decks.id("Ankizin::M2_M3_Klinik::Innere_Medizin::Pneumologie"))
    col.sched.suspend_cards(note.card_ids())
    w.reload("full")
    assert not w.banner.isHidden()
    assert "1 neue ausgesetzte Karte" in w.banner_label.text() or "eine neue ausgesetzte Karte" in w.banner_label.text()
    w._enable_stragglers()
    assert w.banner.isHidden()


def test_window_decks_tab_and_empty_collection(window, tmp_path, monkeypatch):
    w = window
    w.tabs.setCurrentIndex(1)
    assert w.tree.topLevelItem(0).text(0) == "Decks"
    assert _tops(w) == ["Infektiologie und Hygiene", "Innere Medizin"]
    assert w.tree.currentItem() is w.tree.topLevelItem(0)
    w.tabs.setCurrentIndex(0)

    empty = anki_collection.Collection(str(tmp_path / "empty.anki2"))
    try:
        from ankizin_explorer import ops

        monkeypatch.setattr(
            ops, "load_snapshot", lambda p, vk, ok, fail: ok(loader.load_snapshot(empty, vk))
        )
        w.reload("full")
        assert w.pages.currentIndex() == 0
        assert "Kein AnKIzin gefunden" in w.message.text()
    finally:
        empty.close()


# --- Einbindung (Menü, Toolbar, Onigiri) ----------------------------------------------


def test_integration_setup(monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    qt = pytest.importorskip("aqt.qt")
    app = qt.QApplication.instance() or qt.QApplication([])
    import sys

    from ankizin_explorer import integration

    main = qt.QMainWindow()
    menu = main.menuBar().addMenu("Extras")
    export = qt.QAction("Exportieren", main)
    export.setShortcut(qt.QKeySequence("Ctrl+Shift+E"))
    main.addAction(export)

    registered = {}
    onigiri = types.ModuleType("1011095603")
    onigiri.register_sidebar_action = lambda **kw: registered.update(kw)
    monkeypatch.setitem(sys.modules, "1011095603", onigiri)
    meta = types.SimpleNamespace(
        enabled=True, dir_name="1011095603", human_name=lambda: "Onigiri", ankiweb_id=lambda: "1011095603"
    )
    manager = types.SimpleNamespace(
        all_addon_meta=lambda: [meta],
        getConfig=lambda name: {"tastenkuerzel": "Ctrl+Alt+A", "vorklinik_anzeigen": False},
        setConfigUpdatedAction=lambda name, fn: None,
    )

    # Stand-in für aqt.mw: ein echtes QMainWindow mit den benutzten Attributen
    main.col = None
    main.addonManager = manager
    main.form = types.SimpleNamespace(menuTools=menu)
    fake = main
    monkeypatch.setattr(integration, "mw", fake)
    import aqt

    monkeypatch.setattr(aqt, "mw", fake)
    opened = []
    monkeypatch.setattr(integration, "open_window", lambda: opened.append(1))

    integration.setup()
    actions = [a for a in menu.actions() if a.text() == "AnKIzin Explorer"]
    assert len(actions) == 1
    assert actions[0].shortcut().toString() == qt.QKeySequence("Ctrl+Alt+A").toString()
    assert not integration._shortcut_free("Ctrl+Shift+E")

    links = []
    toolbar = types.SimpleNamespace(create_link=lambda cmd, label, func, tip=None, id=None: f"{cmd}|{label}")
    integration._toolbar_links(links, toolbar)
    assert links == ["ankizin_explorer_open|AnKIzin"]

    assert integration._on_js_message((False, None), "something_else", None) == (False, None)
    assert integration._on_js_message((False, None), integration.COMMAND, None) == (True, None)
    assert integration._on_js_message((True, None), integration.COMMAND, None) == (True, None)
    assert opened == [1]

    monkeypatch.setattr(integration, "_onigiri_done", False)
    integration._register_onigiri()
    assert registered["entry_id"] == "ankizin_explorer.open"
    assert registered["command"] == integration.COMMAND
    assert registered["icon_svg"].startswith("<svg")

    # Onigiri installiert, aber nicht geladen -> nicht importieren
    monkeypatch.delitem(sys.modules, "1011095603")
    monkeypatch.setattr(integration, "_onigiri_done", False)
    registered.clear()
    integration._register_onigiri()
    assert registered == {}
    main.deleteLater()
    app.processEvents()


def test_wrap_elide_keeps_spaces_and_breaks_long_words():
    qt = pytest.importorskip("aqt.qt")
    app = qt.QApplication.instance() or qt.QApplication([])  # noqa: F841 - muss leben
    from ankizin_explorer.ui.widgets import wrap_elide

    fm = qt.QFontMetrics(qt.QFont())
    assert wrap_elide("Kurz", fm, 140, 2) == ["Kurz"]
    lines = wrap_elide("Kinder- und Jugendpsychiatrie", fm, fm.horizontalAdvance("Jugendpsychiatrie") + 2, 2)
    assert lines == ["Kinder- und", "Jugendpsychiatrie"]
    long_word = "Nebenniereninsuffizienzausdruck" * 3
    lines = wrap_elide(long_word, fm, 100, 2)
    assert len(lines) == 2 and lines[1].endswith("…")
    assert all(fm.horizontalAdvance(line) <= 100 for line in lines)


def test_disable_partial_parent_from_header(window):
    """◐-Oberthema über „Aussetzen“ im Kopf: der ganze Teilbaum geht aus, auch geteilte Karten."""
    w = window
    key = next(k for k in w.items if k and k[-1] == "pneumologie")
    w.navigate(key)
    w.toggle(w.current_node())  # an; Tuberkulose ist dadurch auch unter Infektiologie aktiv
    inf = next(k for k in w.items if k and k[-1] == "infektiologie")
    w.navigate(inf)
    assert w.current_node().counts.active and w.off_btn.isVisibleTo(w)
    w.toggle(w.current_node(), False)
    assert w.current_node().counts.active == 0
    assert all(w._node(k).counts.active == 0 for k in w.items if k[: len(inf)] == inf)
    assert not w.off_btn.isVisibleTo(w) and w.toggle_btn.text() == "Aktivieren"


def _tile(w, name):
    from ankizin_explorer.ui.widgets import Tile

    for i in range(w.tiles_layout.count()):
        tile = w.tiles_layout.itemAt(i).widget()
        if isinstance(tile, Tile) and tile.findChild(type(w.title)).toolTip() == name:
            return tile
    raise KeyError(name)


def test_tile_checkbox_toggles_without_navigating(window):
    qt = pytest.importorskip("aqt.qt")
    qtest = pytest.importorskip("PyQt6.QtTest")
    w = window
    w.resize(1100, 720)
    qt.QApplication.processEvents()
    tile = _tile(w, "Innere Medizin")
    assert tile.check.checkState() == qt.Qt.CheckState.Unchecked
    assert tile.check.toolTip() == "Aktivieren"
    qtest.QTest.mouseClick(tile.check, qt.Qt.MouseButton.LeftButton)
    qt.QApplication.processEvents()
    # geschaltet, aber nicht hineinnavigiert
    assert w.current_node().key == ()
    assert w.title.text() == "AMBOSS-Bibliothek"
    inner = next(w._node(k) for k in w.items if k and k[-1] == "innere_medizin")
    assert logic.node_state(inner.counts) == logic.STATE_ON
    tile = _tile(w, "Innere Medizin")
    assert tile.check.checkState() == qt.Qt.CheckState.Checked
    assert tile.check.toolTip() == "Aussetzen"

    # Der Klick selbst ändert den angezeigten Zustand nie, erst die neuen Kartenzahlen
    tile.check.click()
    assert tile.check.checkState() == qt.Qt.CheckState.Checked
    qt.QApplication.processEvents()
    assert logic.node_state(inner.counts) == logic.STATE_OFF
    assert _tile(w, "Innere Medizin").check.checkState() == qt.Qt.CheckState.Unchecked

    # Klick auf den Rest der Kachel navigiert hinein
    tile = _tile(w, "Innere Medizin")
    qtest.QTest.mouseClick(tile, qt.Qt.MouseButton.LeftButton, pos=qt.QPoint(tile.width() // 2, tile.height() - 8))
    qt.QApplication.processEvents()
    assert w.title.text() == "Innere Medizin"


def test_root_row(window):
    qt = pytest.importorskip("aqt.qt")
    w = window
    root = w.tree.topLevelItem(0)
    assert root.text(0) == "AMBOSS-Bibliothek" and root.data(0, qt.Qt.ItemDataRole.UserRole) == ()
    assert root.isExpanded() and w.tree.currentItem() is root
    assert w.current_node() is w.current_view().root

    # Breadcrumb auf die Wurzel wählt die Wurzelzeile
    key = next(k for k in w.items if k and k[-1] == "pneumologie")
    w.navigate(key)
    w._on_crumb("0")
    assert w.tree.currentItem() is root and w.title.text() == "AMBOSS-Bibliothek"

    # Suche: Wurzel bleibt sichtbar und aufgeklappt, auch ohne Treffer
    w.search.setText("gibtesnicht")
    w._apply_search()
    assert not root.isHidden() and root.isExpanded()
    w.search.setText("")
    w._apply_search()
    assert root.isExpanded()

    # Zuklappen, Sortier- und Tabwechsel: Wurzel wieder offen, Auswahl bleibt
    w.navigate(key)
    w._collapse_all()
    assert w.tree.topLevelItem(0).isExpanded()
    w.sort_box.setCurrentIndex(1)
    assert w.tree.topLevelItem(0).isExpanded() and w.current_node().key == key
    w.tabs.setCurrentIndex(1)
    assert w.tree.topLevelItem(0).isExpanded()
    w.tabs.setCurrentIndex(0)
    assert w.current_node().key == key
    w.navigate(())
    w.reload("full")
    assert w.tree.currentItem() is w.tree.topLevelItem(0)

    # Checkbox der Wurzel schaltet alles
    root = w.tree.topLevelItem(0)
    root.setCheckState(0, qt.Qt.CheckState.Checked)
    assert w.current_view().root.counts.active == w.current_view().root.counts.total
    assert w.tree.topLevelItem(0).checkState(0) == qt.Qt.CheckState.Checked


def test_root_checkbox_asks_from_500(window, monkeypatch):
    qt = pytest.importorskip("aqt.qt")
    w = window
    monkeypatch.setattr(logic, "CONFIRM_THRESHOLD", 5)
    from ankizin_explorer.ui import window as win

    monkeypatch.setattr(win, "askUser", lambda text, **k: w._asked.append(text) or False)
    w.tree.topLevelItem(0).setCheckState(0, qt.Qt.CheckState.Checked)
    assert w._asked and w.current_view().root.counts.active == 0
    # abgelehnt: Checkbox zeigt wieder den Kartenzustand
    assert w.tree.topLevelItem(0).checkState(0) == qt.Qt.CheckState.Unchecked


def test_more_menu_and_reload_shortcut(window, col, monkeypatch):
    qt = pytest.importorskip("aqt.qt")
    w = window
    assert w.more_btn.popupMode() == qt.QToolButton.ToolButtonPopupMode.InstantPopup
    labels = [a.text() for a in w.more_btn.menu().actions() if not a.isSeparator()]
    assert labels == ["Vorklinik anzeigen", "Neu laden"]
    assert w.vk_action.isCheckable() and not w.vk_action.isChecked()
    assert w.reload_action.shortcut() == qt.QKeySequence("Ctrl+R")
    assert w.reload_sc.key() == qt.QKeySequence("Ctrl+R")

    # Vorklinik über das Menü lädt neu (mit Gruppen „Klinik“/„Vorklinik“)
    w.vk_action.setChecked(True)
    assert _tops(w) == ["Klinik", "Vorklinik"]
    from ankizin_explorer.ui import window as win

    monkeypatch.setattr(win.config, "show_vorklinik", lambda: False)
    w.on_config_changed()
    assert not w.vk_action.isChecked()

    # Neu laden ist gesperrt, solange geladen wird
    from ankizin_explorer import ops

    pending = []
    monkeypatch.setattr(ops, "load_snapshot", lambda p, vk, ok, fail: pending.append((ok, vk)))
    w.reload_sc.activated.emit()
    assert len(pending) == 1
    assert not w.reload_action.isEnabled() and not w.reload_sc.isEnabled()
    ok, vk = pending.pop()
    ok(loader.load_snapshot(col, vk))
    assert w.reload_action.isEnabled() and w.reload_sc.isEnabled()
    w.reload_action.trigger()
    assert len(pending) == 1


def test_status_texts():
    from ankizin_explorer.model import Counts
    from ankizin_explorer.ui.widgets import status_detail, status_text

    # 92 aktiv, 8 ausgesetzt, davon 5 neu -> eingeschaltet (≥ 90 %) mit Nachzüglern
    c = Counts([80, 6, 6, 5, 2, 1])
    assert status_text(c) == "92 von 100 Karten aktiv · 5 neue ausgesetzt"
    assert status_detail(c) == "teilweise aktiv (92 %) · 92 aktiv, 8 ausgesetzt · 5 neue ausgesetzt"
    c = Counts([10, 0, 0, 30, 0, 0])
    assert status_text(c) == "10 von 40 Karten aktiv"
    assert status_text(Counts([1, 0, 0, 0, 0, 0])) == "1 von 1 Karte aktiv"


def test_legend_follows_theme(window, monkeypatch):
    from ankizin_explorer.ui import theme

    w = window
    light = w.pal.new.name()
    monkeypatch.setattr(theme, "night_mode", lambda: True)
    w.apply_theme()
    assert w.pal.dark and w.pal.new.name() != light
    assert w.pal.new.name() in w.legend.text() and light not in w.legend.text()
