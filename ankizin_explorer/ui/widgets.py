"""Ring, Kacheln und Flow-Layout."""

from __future__ import annotations

import re
from typing import Callable, Dict, List, Optional

from aqt.qt import (
    QEvent,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPainter,
    QPen,
    QPixmap,
    QPoint,
    QPushButton,
    QRect,
    QRectF,
    QSize,
    QSizePolicy,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QVBoxLayout,
    QWidget,
    Qt,
)

from .. import logic
from ..model import Counts
from ..text import counts_tooltip, fmt_int, state_label
from .theme import Palette

ROLE_COUNTS = Qt.ItemDataRole.UserRole + 1


def paint_ring(painter: QPainter, rect: QRectF, counts: Counts, pal: Palette) -> None:
    """Ring mit drei Farben: gefestigt, gesehen, neu (im Uhrzeigersinn ab 12 Uhr)."""
    side = min(rect.width(), rect.height())
    width = max(2.0, side / 5.5)
    inset = width / 2 + 0.5
    r = QRectF(
        rect.x() + (rect.width() - side) / 2 + inset,
        rect.y() + (rect.height() - side) / 2 + inset,
        side - 2 * inset,
        side - 2 * inset,
    )
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(pal.track, width)
    pen.setCapStyle(Qt.PenCapStyle.FlatCap)
    painter.setPen(pen)
    painter.drawEllipse(r)
    total = counts.total
    if total:
        start = 90 * 16
        for value, color in ((counts.mature, pal.mature), (counts.seen, pal.seen), (counts.new, pal.new)):
            if not value:
                continue
            span = -round(360 * 16 * value / total)
            if span == 0:
                span = -16
            pen.setColor(color)
            painter.setPen(pen)
            painter.drawArc(r, start, span)
            start += span
    painter.restore()


_RING_CACHE: Dict[tuple, QPixmap] = {}


def ring_pixmap(counts: Counts, pal: Palette, size: int, dpr: float) -> QPixmap:
    """Kleiner Ring als Pixmap; gleiche Anteile (auf ein Grad gerundet) teilen sich eine."""
    total = counts.total or 1
    shares = tuple(round(360 * v / total) if v else -1 for v in (counts.mature, counts.seen, counts.new))
    key = (size, dpr, pal.dark, shares)
    pix = _RING_CACHE.get(key)
    if pix is not None:
        return pix
    if len(_RING_CACHE) > 4000:  # ~4 KB je Ring; nur zur Sicherheit begrenzt
        _RING_CACHE.clear()
    side = int(round(size * dpr))
    pix = QPixmap(side, side)
    pix.setDevicePixelRatio(dpr)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    paint_ring(p, QRectF(0, 0, size, size), counts, pal)
    p.end()
    _RING_CACHE[key] = pix
    return pix


class RingWidget(QWidget):
    def __init__(self, size: int, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._counts = Counts()
        self._pal = Palette()
        self.setFixedSize(size, size)

    def set_counts(self, counts: Counts, pal: Palette) -> None:
        self._counts = counts
        self._pal = pal
        self.setToolTip(counts_tooltip(counts))
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        paint_ring(p, QRectF(self.rect()), self._counts, self._pal)
        p.end()


class RingDelegate(QStyledItemDelegate):
    """Spalte „Lernstand“ im Baum: kleiner Ring + „gesehen/gesamt“."""

    def __init__(self, parent, palette_fn: Callable[[], Palette]) -> None:
        super().__init__(parent)
        self._palette_fn = palette_fn

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        # Läuft beim Scrollen für jede sichtbare Zeile: nur Hintergrund vom Stil, Ring aus
        # dem Pixmap-Cache, Text direkt.
        widget = option.widget
        style = widget.style() if widget else None
        if style:
            style.drawPrimitive(QStyle.PrimitiveElement.PE_PanelItemViewItem, option, painter, widget)
        data = index.data(ROLE_COUNTS)
        if not data:
            return
        counts = Counts(data)
        pal = self._palette_fn()
        rect = option.rect
        size = min(rect.height() - 4, 16)
        x = rect.x() + 4
        y = rect.y() + (rect.height() - size) // 2
        dpr = widget.devicePixelRatioF() if widget else 1.0
        painter.drawPixmap(x, y, ring_pixmap(counts, pal, size, dpr))
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        painter.setPen(option.palette.highlightedText().color() if selected else pal.fg_subtle)
        text_rect = QRect(x + size + 6, rect.y(), rect.width() - size - 12, rect.height())
        text = f"{fmt_int(counts.studied)}/{fmt_int(counts.total)}"
        text = painter.fontMetrics().elidedText(text, Qt.TextElideMode.ElideLeft, text_rect.width())
        painter.drawText(text_rect, int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), text)

    def sizeHint(self, option, index) -> QSize:  # noqa: N802
        return QSize(ring_column_width(option.fontMetrics), 22)


def ring_column_width(fm) -> int:
    """Breite der Lernstand-Spalte: Ring + längste übliche Zahl („18.422/20.064“)."""
    return 4 + 16 + 6 + fm.horizontalAdvance("88.888/88.888") + 8


class FlowLayout(QLayout):
    """Raster für die Kacheln: so viele Spalten wie passen, Kacheln füllen die Breite.

    Widgets mit der Eigenschaft `fullRow` (z. B. ein Hinweistext) nehmen eine ganze Zeile.
    """

    def __init__(self, parent: Optional[QWidget] = None, spacing: int = 10, min_width: int = 200) -> None:
        super().__init__(parent)
        self._items: List = []
        self._spacing = spacing
        self._min_width = min_width

    def addItem(self, item) -> None:  # noqa: N802
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, i):  # noqa: N802
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):  # noqa: N802
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def expandingDirections(self):  # noqa: N802
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:  # noqa: N802
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802
        return self._layout(QRect(0, 0, width, 0), apply=False)

    def setGeometry(self, rect: QRect) -> None:  # noqa: N802
        super().setGeometry(rect)
        self._layout(rect, apply=True)

    def sizeHint(self) -> QSize:  # noqa: N802
        return self.minimumSize()

    def minimumSize(self) -> QSize:  # noqa: N802
        m = self.contentsMargins()
        return QSize(self._min_width + m.left() + m.right(), m.top() + m.bottom())

    def _layout(self, rect: QRect, apply: bool) -> int:
        m = self.contentsMargins()
        x0 = rect.x() + m.left()
        width = max(1, rect.width() - m.left() - m.right())
        sp = self._spacing
        cols = max(1, (width + sp) // (self._min_width + sp))
        col_w = (width - sp * (cols - 1)) // cols
        y = rect.y() + m.top()
        col = 0
        line_h = 0
        for item in self._items:
            widget = item.widget()
            full = bool(widget is not None and widget.property("fullRow"))
            if full or col >= cols:
                if col:
                    y += line_h + sp
                col, line_h = 0, 0
            w = width if full else col_w
            h = item.heightForWidth(w) if item.hasHeightForWidth() else item.sizeHint().height()
            if apply:
                item.setGeometry(QRect(x0 + col * (col_w + sp), y, w, h))
            line_h = max(line_h, h)
            col = cols if full else col + 1
        return y + line_h - rect.y() + m.bottom()


class ElidedLabel(QLabel):
    """Text auf höchstens `lines` Zeilen umbrechen, Rest mit „…“; volle Höhe immer gleich.

    Bricht an Leerzeichen und Bindestrichen, zu lange Einzelwörter notfalls mitten im Wort.
    """

    def __init__(self, text: str, lines: int = 1, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._full = text
        self._lines = lines
        self.setToolTip(text)
        self._fix_height()
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

    def setText(self, text: str) -> None:  # noqa: N802
        self._full = text
        self.setToolTip(text)
        self._relayout()

    def changeEvent(self, event) -> None:  # noqa: N802
        super().changeEvent(event)
        if event.type() in (QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self._fix_height()
            self._relayout()

    def showEvent(self, event) -> None:  # noqa: N802
        self._fix_height()
        self._relayout()
        super().showEvent(event)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._relayout()

    def _fix_height(self) -> None:
        self.setFixedHeight(self.fontMetrics().lineSpacing() * self._lines + 2)

    def _relayout(self) -> None:
        width = self.contentsRect().width()
        if width <= 0:
            return
        super().setText("\n".join(wrap_elide(self._full, self.fontMetrics(), width, self._lines)))


class CrumbLabel(QLabel):
    """Pfad als einzeilige Linkleiste; wird es zu eng, fallen mittlere Teile zu „…“ weg.

    Die Links tragen den Index des Teils (`linkActivated("2")`), der volle Pfad steht im
    Tooltip.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._parts: List[str] = []
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(self.fontMetrics().lineSpacing() + 2)
        sp = self.sizePolicy()
        sp.setRetainSizeWhenHidden(True)
        self.setSizePolicy(sp)

    def set_parts(self, parts: List[str]) -> None:
        self._parts = list(parts)
        self.setToolTip(" › ".join(parts))
        self._relayout()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._relayout()

    def _relayout(self) -> None:
        parts = self._parts
        width = self.contentsRect().width()
        fm = self.fontMetrics()
        shown = list(range(len(parts)))
        # Von der zweiten Stelle an Teile weglassen, bis es passt (erster und letzter bleiben)
        while len(shown) > 2 and width > 0 and fm.horizontalAdvance(self._plain(shown)) > width:
            del shown[1]
        html = []
        prev = None
        for i in shown:
            if prev is not None and i - prev > 1:
                html.append("…")
            html.append(f'<a href="{i}" style="text-decoration:none">{_esc(parts[i])}</a>')
            prev = i
        if len(shown) <= 2 and parts and width > 0 and fm.horizontalAdvance(self._plain(shown)) > width:
            # Auch zwei Teile sind zu lang: den letzten kürzen
            room = width - fm.horizontalAdvance(self._plain(shown[:-1]) + " › ") if len(shown) > 1 else width
            last = fm.elidedText(parts[shown[-1]], Qt.TextElideMode.ElideRight, max(room, 20))
            html[-1] = f'<a href="{shown[-1]}" style="text-decoration:none">{_esc(last)}</a>'
        super().setText(" › ".join(html))

    def _plain(self, shown: List[int]) -> str:
        out = []
        prev = None
        for i in shown:
            if prev is not None and i - prev > 1:
                out.append("…")
            out.append(self._parts[i])
            prev = i
        return " › ".join(out)


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def wrap_elide(text: str, fm, width: int, max_lines: int) -> List[str]:
    tokens = re.findall(r"\S+?(?:-\s*|\s+|$)", text)
    lines: List[str] = []
    cur = ""
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        cand = cur + tok
        if fm.horizontalAdvance(cand.rstrip()) <= width:
            cur = cand
            i += 1
            continue
        if not cur:
            # Wort passt allein nicht in die Zeile: so viele Zeichen wie passen
            n = max(1, len(tok) - 1)
            while n > 1 and fm.horizontalAdvance(tok[:n]) > width:
                n -= 1
            cur, tokens[i] = tok[:n], tok[n:]
        lines.append(cur.rstrip())
        cur = ""
        if len(lines) == max_lines:
            break
    if len(lines) < max_lines and cur:
        lines.append(cur.rstrip())
    elif len(lines) == max_lines and (cur or i < len(tokens)):
        rest = lines[-1] + " " + "".join(tokens[i:])
        lines[-1] = fm.elidedText(rest.strip(), Qt.TextElideMode.ElideRight, width)
    return lines


def toggle_text(counts: Counts) -> str:
    return "Aktivieren" if logic.wants_enable(counts) else "Aussetzen"


def short_status(counts: Counts) -> str:
    """Kurzform für Kacheln: „aktiv“, „ausgesetzt“ oder „69 % aktiv“."""
    state = logic.node_state(counts)
    if state == logic.STATE_PARTIAL:
        return f"{round(100 * counts.active / counts.total)} % aktiv"
    return state_label(state)


def status_text(counts: Counts) -> str:
    state = logic.node_state(counts)
    parts = [state_label(state)]
    if state == logic.STATE_PARTIAL:
        parts[0] += f" ({round(100 * counts.active / counts.total)} %)"
    if counts.suspended_new and logic.is_switched_on(counts):
        parts.append(f"{fmt_int(counts.suspended_new)} neue ausgesetzt")
    return " · ".join(parts)


class Tile(QFrame):
    """Kachel für ein direktes Kind: Name, Ring, Zahlen, Status, An/Aus-Knopf."""

    def __init__(
        self,
        name: str,
        counts: Counts,
        has_children: bool,
        pal: Palette,
        on_open: Callable[[], None],
        on_toggle: Callable[[], None],
        on_menu: Callable[[QPoint], None],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("azTile")
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._on_open = on_open
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(lambda pos: on_menu(self.mapToGlobal(pos)))

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(10)
        ring = RingWidget(38)
        ring.set_counts(counts, pal)
        top.addWidget(ring, 0, Qt.AlignmentFlag.AlignVCenter)
        # Immer zwei Zeilen hoch, damit alle Kacheln einer Reihe gleich aussehen
        title = ElidedLabel(name, lines=2)
        title.setObjectName("azTileTitle")
        top.addWidget(title, 1, Qt.AlignmentFlag.AlignVCenter)
        if has_children:
            arrow = QLabel("›")
            arrow.setObjectName("azSubtle")
            arrow.setToolTip("Hat Unterthemen – klicken zum Öffnen")
            top.addWidget(arrow, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addLayout(top)

        nums = ElidedLabel(f"{fmt_int(counts.studied)}/{fmt_int(counts.total)} gesehen")
        nums.setObjectName("azSubtle")
        nums.setToolTip(counts_tooltip(counts))
        lay.addWidget(nums)

        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        status = ElidedLabel(short_status(counts))
        status.setToolTip(status_text(counts))
        status.setObjectName("azSubtle")
        bottom.addWidget(status, 1, Qt.AlignmentFlag.AlignVCenter)
        btn = QPushButton(toggle_text(counts))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setAutoDefault(False)
        btn.clicked.connect(lambda _=False: on_toggle())
        bottom.addWidget(btn, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addLayout(bottom)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self._on_open()
            return
        super().mouseReleaseEvent(event)
