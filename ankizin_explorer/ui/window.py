"""Hauptfenster: Baum links, Übersicht mit Kacheln rechts (SPEC 5)."""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from aqt import mw
from aqt.qt import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QKeySequence,
    QLabel,
    QLineEdit,
    QMenu,
    QPoint,
    QPushButton,
    QScrollArea,
    QShortcut,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTabBar,
    QTimer,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    Qt,
)
from aqt.utils import askUser, restoreGeom, restoreSplitter, saveGeom, saveSplitter, tooltip

from .. import config, logic, ops
from ..loader import new_per_day
from ..model import Node, Snapshot, View
from ..text import (
    SORT_ALPHA,
    SORT_LABELS,
    counts_tooltip,
    filter_keys,
    fmt_int,
    karten,
    sorted_children,
)
from .theme import Palette
from .widgets import (
    ROLE_COUNTS,
    CrumbLabel,
    ElidedLabel,
    FlowLayout,
    RingDelegate,
    RingWidget,
    Tile,
    ring_column_width,
    status_text,
    toggle_text,
)

GEOM_KEY = "ankizin_explorer"
ROLE_KEY = Qt.ItemDataRole.UserRole
VIEWS = [("amboss", "AMBOSS-Bibliothek"), ("decks", "Decks")]

Key = Tuple[str, ...]

NO_DATA_TEXT = (
    "<h3>Kein AnKIzin gefunden</h3>"
    "<p>In dieser Sammlung gibt es weder AnKIzin-Tags der AMBOSS-Bibliothek "
    "(<code>#Ankizin_v…::#M2_M3_Klinik::#AMBOSS::Bibliothek-Klinik</code>) "
    "noch ein Deck <code>Ankizin::M2_M3_Klinik</code>.</p>"
    "<p>AnKIzin gibt es kostenlos über AnkiCollab, siehe ankizin.de.</p>"
)


class _ViewState:
    """Auswahl, Aufklappzustand und Scrollposition je Tab."""

    def __init__(self) -> None:
        self.selected: Optional[Key] = None
        self.expanded: Set[Key] = set()
        self.scroll = 0


class ExplorerWindow(QWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("AnKIzin Explorer")
        self.setMinimumSize(760, 480)
        self.pal = Palette()
        self.snapshot: Optional[Snapshot] = None
        self.view_id = "amboss"
        self.sort_mode = SORT_ALPHA
        self.states: Dict[str, _ViewState] = {vid: _ViewState() for vid, _ in VIEWS}
        self.items: Dict[Key, QTreeWidgetItem] = {}
        self._structure: Optional[List[Key]] = None
        self._updating = False
        self._loading = False
        self._op_running = False
        self._pending: Optional[str] = None  # "full" | "codes"
        self._show_vorklinik = config.show_vorklinik()
        self._loaded_vorklinik: Optional[bool] = None

        self._build_ui()
        self.apply_theme()
        try:
            restoreGeom(self, GEOM_KEY, default_size=(1100, 720))
        except TypeError:  # ältere Anki-Versionen ohne default_size
            self.resize(1100, 720)
            restoreGeom(self, GEOM_KEY)
        restoreSplitter(self.splitter, GEOM_KEY)
        self.tree.setFocus()
        self.reload("full")

    # --- Aufbau ----------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 12)
        root.setSpacing(8)

        # Hinweisbanner Nachzügler
        self.banner = QFrame()
        self.banner.setObjectName("azBanner")
        bl = QHBoxLayout(self.banner)
        bl.setContentsMargins(12, 8, 8, 8)
        self.banner_label = QLabel()
        self.banner_label.setWordWrap(True)
        bl.addWidget(self.banner_label, 1)
        self.banner_btn = QPushButton("Nachzügler aktivieren")
        # Kein Startfokus: ein versehentliches Leerzeichen soll nichts schalten
        self.banner_btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.banner_btn.clicked.connect(self._enable_stragglers)
        bl.addWidget(self.banner_btn)
        self.banner.hide()
        root.addWidget(self.banner)

        # Kopfzeile: Tabs, Sortierung, Vorklinik, Neu laden
        top = QHBoxLayout()
        self.tabs = QTabBar()
        self.tabs.setDrawBase(False)
        self.tabs.setExpanding(False)
        for _vid, label in VIEWS:
            self.tabs.addTab(label)
        self.tabs.currentChanged.connect(self._on_tab)
        top.addWidget(self.tabs)
        top.addStretch(1)
        top.addWidget(QLabel("Sortierung:"))
        self.sort_box = QComboBox()
        for mode, label in SORT_LABELS.items():
            self.sort_box.addItem(label, mode)
        self.sort_box.currentIndexChanged.connect(self._on_sort)
        top.addWidget(self.sort_box)
        self.vk_box = QCheckBox("Vorklinik anzeigen")
        self.vk_box.setChecked(self._show_vorklinik)
        self.vk_box.toggled.connect(self._on_vorklinik)
        top.addWidget(self.vk_box)
        self.reload_btn = QPushButton("Neu laden")
        self.reload_btn.setToolTip("Daten neu aus der Sammlung lesen")
        self.reload_btn.clicked.connect(lambda: self.reload("full"))
        top.addWidget(self.reload_btn)
        root.addLayout(top)

        self.pages = QStackedWidget()
        root.addWidget(self.pages, 1)

        # Seite 0: Laden / Meldung
        self.message = QLabel("Lade AnKIzin …")
        self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message.setWordWrap(True)
        self.message.setTextFormat(Qt.TextFormat.RichText)
        self.pages.addWidget(self.message)

        # Seite 1: Master/Detail
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.pages.addWidget(self.splitter)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(6)
        self.search = QLineEdit()
        self.search.setObjectName("azSearch")
        self.search.setPlaceholderText("Thema suchen …")
        self.search.setClearButtonEnabled(True)
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(150)
        self._search_timer.timeout.connect(self._apply_search)
        self.search.textChanged.connect(lambda _t: self._search_timer.start())
        ll.addWidget(self.search)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderHidden(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setItemDelegateForColumn(1, RingDelegate(self.tree, lambda: self.pal))
        header = self.tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(1, ring_column_width(self.tree.fontMetrics()))
        self.tree.setIndentation(16)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._tree_menu)
        self.tree.itemChanged.connect(self._on_item_changed)
        self.tree.currentItemChanged.connect(self._on_current)
        self.tree.itemExpanded.connect(lambda it: self._remember_expand(it, True))
        self.tree.itemCollapsed.connect(lambda it: self._remember_expand(it, False))
        ll.addWidget(self.tree, 1)
        left.setMinimumWidth(280)
        self.splitter.addWidget(left)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(8, 0, 0, 0)
        rl.setSpacing(10)

        self.header = QFrame()
        self.header.setObjectName("azHeader")
        hl = QHBoxLayout(self.header)
        hl.setContentsMargins(16, 12, 16, 12)
        hl.setSpacing(16)
        self.big_ring = RingWidget(76)
        hl.addWidget(self.big_ring, 0, Qt.AlignmentFlag.AlignTop)
        info = QVBoxLayout()
        info.setSpacing(4)
        # Feste Zeilenzahl je Element, damit der Kopf beim Navigieren nicht springt
        self.crumbs = CrumbLabel()
        self.crumbs.setObjectName("azSubtle")
        self.crumbs.linkActivated.connect(self._on_crumb)
        info.addWidget(self.crumbs)
        self.title = ElidedLabel("", lines=2)
        self.title.setObjectName("azTitle")
        info.addWidget(self.title)
        self.summary = QLabel()
        self.summary.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        info.addWidget(self.summary)
        self.status = QLabel()
        self.status.setObjectName("azSubtle")
        self.status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        info.addWidget(self.status)
        hl.addLayout(info, 1)
        btns = QVBoxLayout()
        self.toggle_btn = QPushButton()
        self.toggle_btn.setDefault(False)
        self.toggle_btn.setAutoDefault(False)
        self.toggle_btn.clicked.connect(lambda: self.toggle(self.current_node()))
        btns.addWidget(self.toggle_btn)
        # Bei ◐ heißt der Hauptknopf „Aktivieren“; Aussetzen geht dann über diesen Knopf
        self.off_btn = QPushButton("Aussetzen")
        self.off_btn.setAutoDefault(False)
        self.off_btn.clicked.connect(lambda: self.toggle(self.current_node(), False))
        btns.addWidget(self.off_btn)
        self.browse_btn = QPushButton("Im Browser zeigen")
        self.browse_btn.clicked.connect(lambda: self.show_in_browser(self.current_node()))
        btns.addWidget(self.browse_btn)
        btns.addStretch(1)
        hl.addLayout(btns)
        rl.addWidget(self.header)

        self.tiles_area = QScrollArea()
        self.tiles_area.setObjectName("azTiles")
        self.tiles_area.setWidgetResizable(True)
        self.tiles_area.setFrameShape(QFrame.Shape.NoFrame)
        self._new_tiles_container()
        rl.addWidget(self.tiles_area, 1)
        self.splitter.addWidget(right)
        self.splitter.setStretchFactor(0, 2)
        self.splitter.setStretchFactor(1, 3)
        self.splitter.setSizes([420, 640])
        self.splitter.setChildrenCollapsible(False)
        right.setMinimumWidth(320)

        # Cmd/Ctrl+Z macht wie im Hauptfenster den letzten Schritt rückgängig
        undo_sc = QShortcut(QKeySequence(QKeySequence.StandardKey.Undo), self)
        undo_sc.activated.connect(self._undo)
        find_sc = QShortcut(QKeySequence(QKeySequence.StandardKey.Find), self)
        find_sc.activated.connect(lambda: (self.search.setFocus(), self.search.selectAll()))
        close_sc = QShortcut(QKeySequence("Escape"), self)
        close_sc.activated.connect(self._on_escape)

    def _new_tiles_container(self) -> None:
        inner = QWidget()
        inner.setObjectName("azTilesInner")
        self.tiles_layout = FlowLayout(inner, spacing=10)
        self.tiles_layout.setContentsMargins(0, 0, 0, 0)
        self.tiles_area.setWidget(inner)

    def apply_theme(self) -> None:
        self.pal = Palette()
        # Nicht aufs ganze Fenster setzen: Ein Stylesheet auf einem Vorfahren schickt auch
        # den Baum durch Qts langsamen Stylesheet-Pfad (gemessen ~40 % pro Scroll-Frame).
        sheet = self.pal.stylesheet()
        for widget in (self.banner, self.header, self.search, self.tiles_area):
            widget.setStyleSheet(sheet)
        if self.snapshot is not None:
            self.tree.viewport().update()
            self._show_detail()

    # --- Laden -----------------------------------------------------------------

    def reload(self, kind: str = "full") -> None:
        """Daten im Hintergrund laden; „codes“ liest nur Kartenzustände neu."""
        if mw.col is None:
            return
        if kind == "codes" and (self.snapshot is None or self._loaded_vorklinik != self._show_vorklinik):
            kind = "full"
        if self._loading:
            if self._pending != "full":
                self._pending = kind
            return
        self._loading = True
        self.reload_btn.setEnabled(False)
        if kind == "full":
            show_vk = self._show_vorklinik
            if self.snapshot is None:
                self.message.setText("Lade AnKIzin …")
                self.pages.setCurrentIndex(0)
            ops.load_snapshot(
                self, show_vk, lambda snap: self._on_loaded(snap, show_vk), self._on_load_failed
            )
        else:
            ops.load_codes(
                self, self.snapshot, lambda snap: self._on_loaded(snap, self._loaded_vorklinik), self._on_load_failed
            )

    def _finish_loading(self) -> None:
        self._loading = False
        self.reload_btn.setEnabled(True)
        pending, self._pending = self._pending, None
        if pending:
            self.reload(pending)

    def _on_loaded(self, snap: Snapshot, show_vk: Optional[bool]) -> None:
        self._remember_state()
        self.snapshot = snap
        self._loaded_vorklinik = show_vk
        self._refresh()
        self._finish_loading()

    def _on_load_failed(self, err: Exception) -> None:
        self.message.setText(f"Fehler beim Laden: {err}")
        self.pages.setCurrentIndex(0)
        self._finish_loading()

    def on_collection_changed(self, changes) -> None:
        """Aus gui_hooks.operation_did_execute (auch Undo im Hauptfenster)."""
        if any(getattr(changes, f, False) for f in ("note_text", "tag", "deck", "notetype")):
            self.reload("full")
        elif getattr(changes, "card", False) or getattr(changes, "deck_config", False):
            self.reload("codes")

    # --- Darstellung -----------------------------------------------------------

    def current_view(self) -> Optional[View]:
        return self.snapshot.view(self.view_id) if self.snapshot else None

    def _refresh(self) -> None:
        snap = self.snapshot
        if snap is None:
            return
        if snap.empty:
            self.message.setText(NO_DATA_TEXT)
            self.pages.setCurrentIndex(0)
            self.banner.hide()
            return
        view = self.current_view()
        if view is None:
            other = "AMBOSS-Bibliothek" if self.view_id == "decks" else "Decks"
            what = (
                "kein Deck <code>Ankizin::M2_M3_Klinik</code>"
                if self.view_id == "decks"
                else "keine AnKIzin-Tags der AMBOSS-Bibliothek"
            )
            self.message.setText(
                f"<h3>Hier ist nichts</h3><p>In dieser Sammlung gibt es {what}. "
                f"Probier den Tab „{other}“.</p>"
            )
            self.pages.setCurrentIndex(0)
            self.banner.hide()
            return
        self.pages.setCurrentIndex(1)
        if view.structure() == self._structure:
            self._update_tree_items(view)
        else:
            self._build_tree(view)
        self._apply_search(keep_scroll=True)
        self._show_detail()
        self._update_banner(view)

    def _item_for(self, node: Node, parent_item) -> QTreeWidgetItem:
        item = QTreeWidgetItem(parent_item)
        item.setText(0, node.name)
        item.setData(0, ROLE_KEY, node.key)
        item.setFlags(
            Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsUserCheckable
        )
        self._fill_item(item, node, force=True)
        self.items[node.key] = item
        return item

    def _fill_item(self, item: QTreeWidgetItem, node: Node, force: bool = False) -> None:
        c = node.counts
        state = logic.node_state(c)
        check = {
            logic.STATE_ON: Qt.CheckState.Checked,
            logic.STATE_PARTIAL: Qt.CheckState.PartiallyChecked,
            logic.STATE_OFF: Qt.CheckState.Unchecked,
        }[state]
        # Neue Items haben noch keinen Check-Zustand (keine Box) – dann immer setzen
        if force or item.checkState(0) != check:
            item.setCheckState(0, check)
        item.setData(1, ROLE_COUNTS, list(c.by_code))
        tip = f"{node.name}\n{status_text(c)}\n\n{counts_tooltip(c)}"
        item.setToolTip(0, tip)
        item.setToolTip(1, tip)

    def _build_tree(self, view: View) -> None:
        state = self.states[self.view_id]
        self._updating = True
        self.tree.setUpdatesEnabled(False)
        try:
            self.tree.clear()
            self.items = {}
            stack = [(child, None) for child in reversed(sorted_children(view.root, self.sort_mode))]
            while stack:
                node, parent_item = stack.pop()
                item = self._item_for(node, parent_item if parent_item is not None else self.tree)
                for child in reversed(sorted_children(node, self.sort_mode)):
                    stack.append((child, item))
            for key in state.expanded:
                it = self.items.get(key)
                if it is not None:
                    it.setExpanded(True)
            self._structure = view.structure()
            sel = self.items.get(state.selected) if state.selected else None
            if sel is not None:
                self.tree.setCurrentItem(sel)
            else:
                self.tree.setCurrentItem(None)
        finally:
            self.tree.setUpdatesEnabled(True)
            self._updating = False
        QTimer.singleShot(0, lambda: self.tree.verticalScrollBar().setValue(state.scroll))

    def _update_tree_items(self, view: View) -> None:
        self._updating = True
        try:
            for key, item in self.items.items():
                node = view.by_key.get(key)
                if node is not None:
                    self._fill_item(item, node)
        finally:
            self._updating = False
        self.tree.viewport().update()

    def _remember_state(self) -> None:
        if self._structure is None:
            return
        st = self.states[self.view_id]
        st.scroll = self.tree.verticalScrollBar().value()
        cur = self.tree.currentItem()
        st.selected = cur.data(0, ROLE_KEY) if cur is not None else None

    def _remember_expand(self, item: QTreeWidgetItem, expanded: bool) -> None:
        if self._updating or self.search.text().strip():
            return
        key = item.data(0, ROLE_KEY)
        if expanded:
            self.states[self.view_id].expanded.add(key)
        else:
            self.states[self.view_id].expanded.discard(key)

    def _apply_search(self, keep_scroll: bool = False) -> None:
        view = self.current_view()
        if view is None:
            return
        result = filter_keys(view.nodes, self.search.text())
        self._updating = True
        self.tree.setUpdatesEnabled(False)
        try:
            if result is None:
                expanded = self.states[self.view_id].expanded
                for key, item in self.items.items():
                    item.setHidden(False)
                    want = key in expanded
                    if item.isExpanded() != want:
                        item.setExpanded(want)
            else:
                visible, expand, _hits = result
                for key, item in self.items.items():
                    item.setHidden(key not in visible)
                    want = key in expand
                    if item.isExpanded() != want:
                        item.setExpanded(want)
        finally:
            self.tree.setUpdatesEnabled(True)
            self._updating = False
        if not keep_scroll:
            cur = self.tree.currentItem()
            if cur is not None and not cur.isHidden():
                self.tree.scrollToItem(cur)

    def current_node(self) -> Optional[Node]:
        view = self.current_view()
        if view is None:
            return None
        item = self.tree.currentItem()
        if item is None:
            return view.root
        return view.by_key.get(item.data(0, ROLE_KEY), view.root)

    def _show_detail(self) -> None:
        node = self.current_node()
        view = self.current_view()
        if node is None or view is None:
            return
        c = node.counts
        self.big_ring.set_counts(c, self.pal)
        crumbs = [view.root] + node.path()[:-1]
        if node is view.root:
            self.crumbs.set_parts([])
            self.crumbs.hide()
        else:
            self.crumbs.set_parts([n.name for n in crumbs])
            self.crumbs.show()
        self._crumb_nodes = crumbs
        self.title.setText(node.name)
        self.summary.setText(
            f"<b>{fmt_int(c.studied)}/{fmt_int(c.total)}</b> gesehen · "
            f"{fmt_int(c.new)} neu · {fmt_int(c.seen)} gesehen · {fmt_int(c.mature)} gefestigt"
        )
        self.summary.setToolTip(counts_tooltip(c))
        self.status.setText(f"{status_text(c)} · {fmt_int(c.active)} aktiv, {fmt_int(c.suspended)} ausgesetzt")
        self.toggle_btn.setText(toggle_text(c))
        self.off_btn.setVisible(logic.node_state(c) == logic.STATE_PARTIAL)
        self._fill_tiles(node)

    def _fill_tiles(self, node: Node) -> None:
        scroll = self.tiles_area.verticalScrollBar().value()
        same = getattr(self, "_tiles_for", None) == (self.view_id, node.key)
        self._new_tiles_container()
        children = sorted_children(node, self.sort_mode)
        if not children:
            empty = QLabel("Keine Unterthemen – das ist ein einzelnes Thema.")
            empty.setObjectName("azSubtle")
            empty.setWordWrap(True)
            empty.setProperty("fullRow", True)
            self.tiles_layout.addWidget(empty)
        for child in children:
            tile = Tile(
                child.name,
                child.counts,
                bool(child.children),
                self.pal,
                on_open=lambda k=child.key: self.navigate(k),
                on_toggle=lambda k=child.key: self.toggle(self._node(k)),
                on_menu=lambda pos, k=child.key: self._node_menu(self._node(k), pos),
            )
            self.tiles_layout.addWidget(tile)
        self._tiles_for = (self.view_id, node.key)
        if same:
            QTimer.singleShot(0, lambda: self.tiles_area.verticalScrollBar().setValue(scroll))

    def _update_banner(self, view: View) -> None:
        topics, cards = logic.stragglers(view, self.snapshot.codes)
        self._straggler_cards = cards
        if not cards:
            self.banner.hide()
            return
        themen = "einem deiner aktiven Themen" if topics == 1 else f"{fmt_int(topics)} deiner aktiven Themen"
        neue = "eine neue ausgesetzte Karte" if len(cards) == 1 else f"{fmt_int(len(cards))} neue ausgesetzte Karten"
        self.banner_label.setText(f"In {themen} gibt es {neue} – aktivieren?")
        self.banner.show()

    # --- Navigation ------------------------------------------------------------

    def _node(self, key: Key) -> Optional[Node]:
        view = self.current_view()
        return view.by_key.get(key) if view else None

    def navigate(self, key: Key) -> None:
        item = self.items.get(key)
        if item is None:
            return
        p = item.parent()
        while p is not None:
            p.setExpanded(True)
            p = p.parent()
        if item.isHidden():
            self.search.clear()
            self._apply_search()
        self.tree.setCurrentItem(item)
        self.tree.scrollToItem(item)

    def _on_crumb(self, href: str) -> None:
        try:
            node = self._crumb_nodes[int(href)]
        except (ValueError, IndexError, AttributeError):
            return
        if node.parent is None:
            self.tree.setCurrentItem(None)
            self.tree.clearSelection()
            self._show_detail()
        else:
            self.navigate(node.key)

    def _on_current(self, _cur, _prev) -> None:
        if not self._updating:
            self._show_detail()

    def _on_tab(self, index: int) -> None:
        self._remember_state()
        self.view_id = VIEWS[index][0]
        self._structure = None
        self._refresh()

    def _on_sort(self, _index: int) -> None:
        self._remember_state()
        self.sort_mode = self.sort_box.currentData()
        self._structure = None
        self._refresh()

    def _on_vorklinik(self, checked: bool) -> None:
        self._show_vorklinik = checked
        config.set_value(config.KEY_VORKLINIK, checked)
        self._remember_state()
        self.reload("full")

    def on_config_changed(self) -> None:
        vk = config.show_vorklinik()
        if vk != self.vk_box.isChecked():
            self.vk_box.setChecked(vk)

    def _on_escape(self) -> None:
        if self.search.text():
            self.search.clear()
        else:
            self.close()

    # --- Schalten --------------------------------------------------------------

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._updating or column != 0:
            return
        node = self._node(item.data(0, ROLE_KEY))
        if node is None:
            return
        # Zustand kommt nur aus den Karten: Klick zurücksetzen, dann schalten
        self._updating = True
        try:
            self._fill_item(item, node)
        finally:
            self._updating = False
        self.toggle(node)

    def toggle(self, node: Optional[Node], enable: Optional[bool] = None) -> None:
        """Schalten; ohne `enable` entscheidet der Zustand (☑ → aus, sonst an)."""
        view = self.current_view()
        if node is None or view is None:
            return
        if self._loading or self._op_running:
            tooltip("Einen Moment, die Zahlen werden gerade aktualisiert …", parent=self)
            return
        if enable is None:
            enable = logic.wants_enable(node.counts)
        if enable:
            plan = logic.plan_enable(node, self.snapshot.codes)
        else:
            plan = logic.plan_disable(view, node, self.snapshot.codes, config.on_wins())
        self.run_plan(plan, node.name)

    def run_plan(self, plan: logic.Plan, name: str) -> None:
        if not plan.count:
            if plan.kept:
                tooltip(
                    f"Nichts ausgesetzt: alle {karten(plan.kept)} liegen auch in anderen aktiven Themen.",
                    parent=self,
                )
            else:
                tooltip("Nichts zu ändern.", parent=self)
            return
        if logic.needs_confirmation(plan) and not self._confirm(plan):
            return
        if plan.enable:
            undo_label = f"AnKIzin: „{name}“ aktivieren"
            done = f"{karten(plan.count)} aktiviert."
        else:
            undo_label = f"AnKIzin: „{name}“ aussetzen"
            done = f"{karten(plan.count)} ausgesetzt."
            if plan.kept:
                done += f" {fmt_int(plan.kept)} bleiben aktiv (in anderen aktiven Themen)."
        self._op_running = True

        def finished(ok: bool) -> None:
            self._op_running = False
            if ok:
                tooltip(done, parent=self)

        ops.set_suspended(self, plan.card_ids, not plan.enable, undo_label, on_done=finished)

    def _confirm(self, plan: logic.Plan) -> bool:
        n = fmt_int(plan.count)
        if plan.enable:
            text = f"Du aktivierst {n} Karten"
            if plan.new_cards != plan.count:
                text += f" (davon {fmt_int(plan.new_cards)} neu)"
            per_day = self._new_per_day()
            days = logic.estimate_days(plan.new_cards, per_day)
            if days is not None:
                text += (
                    f". Bei deinem Limit von {fmt_int(per_day)} neuen/Tag sind das ca. "
                    f"{fmt_int(days)} {'Tag' if days == 1 else 'Tage'}. Fortfahren?"
                )
            else:
                text += ". Fortfahren?"
        else:
            text = f"Du setzt {n} Karten aus."
            if plan.kept:
                text += f" {fmt_int(plan.kept)} bleiben aktiv, weil sie in anderen aktiven Themen liegen."
            text += " Fortfahren?"
        return askUser(text, parent=self, title="AnKIzin Explorer")

    def _new_per_day(self) -> Optional[int]:
        did = self.snapshot.root_deck_id if self.snapshot else None
        if did is None or mw.col is None:
            return None
        return new_per_day(mw.col, did)

    def _enable_stragglers(self) -> None:
        cards = getattr(self, "_straggler_cards", [])
        if not cards or self._loading or self._op_running:
            return
        plan = logic.Plan(True, list(cards), new_cards=len(cards))
        self.run_plan(plan, "Nachzügler")

    def _undo(self) -> None:
        try:
            from aqt.operations.collection import undo

            undo(parent=mw)
        except Exception as err:  # pragma: no cover - nur in Anki
            tooltip(str(err), parent=self)

    # --- Menüs / Browser -------------------------------------------------------

    def _tree_menu(self, pos: QPoint) -> None:
        item = self.tree.itemAt(pos)
        node = self._node(item.data(0, ROLE_KEY)) if item is not None else None
        if node is None:
            view = self.current_view()
            node = view.root if view else None
        if node is None:
            return
        self._node_menu(node, self.tree.viewport().mapToGlobal(pos))

    def _node_menu(self, node: Optional[Node], global_pos: QPoint) -> None:
        if node is None:
            return
        menu = QMenu(self)
        state = logic.node_state(node.counts)
        if state != logic.STATE_ON:
            menu.addAction("Aktivieren", lambda: self.toggle(node, True))
        if state != logic.STATE_OFF:
            menu.addAction("Aussetzen", lambda: self.toggle(node, False))
        menu.addAction("Im Browser zeigen", lambda: self.show_in_browser(node))
        if node.parent is not None:
            menu.addAction("Öffnen", lambda: self.navigate(node.key))
        menu.addSeparator()
        menu.addAction("Alles zuklappen", self._collapse_all)
        menu.exec(global_pos)

    def _collapse_all(self) -> None:
        self.states[self.view_id].expanded.clear()
        self.tree.collapseAll()

    def show_in_browser(self, node: Optional[Node]) -> None:
        if node is None or mw.col is None or not node.search:
            return
        from anki.collection import SearchNode

        nodes = [SearchNode(tag=v) if kind == "tag" else SearchNode(deck=v) for kind, v in node.search]
        search = mw.col.build_search_string(*nodes, joiner="OR") if len(nodes) > 1 else mw.col.build_search_string(nodes[0])
        import aqt

        aqt.dialogs.open("Browser", mw, search=(search,))

    # --- Fenster ---------------------------------------------------------------

    def closeEvent(self, event) -> None:  # noqa: N802
        saveGeom(self, GEOM_KEY)
        saveSplitter(self.splitter, GEOM_KEY)
        super().closeEvent(event)

