"""Ring, Kacheln und Flow-Layout."""

from __future__ import annotations

from typing import Callable, List, Optional

from aqt.qt import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPainter,
    QPen,
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
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = ""
        style = opt.widget.style() if opt.widget else None
        if style:
            style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)
        data = index.data(ROLE_COUNTS)
        if not data:
            return
        counts = Counts(data)
        pal = self._palette_fn()
        rect = option.rect
        size = min(rect.height() - 4, 16)
        ring = QRectF(rect.x() + 4, rect.y() + (rect.height() - size) / 2, size, size)
        paint_ring(painter, ring, counts, pal)
        painter.save()
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        painter.setPen(option.palette.highlightedText().color() if selected else pal.fg_subtle)
        text_rect = QRect(int(ring.right()) + 6, rect.y(), rect.width() - size - 12, rect.height())
        painter.drawText(
            text_rect,
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            f"{fmt_int(counts.studied)}/{fmt_int(counts.total)}",
        )
        painter.restore()

    def sizeHint(self, option, index) -> QSize:  # noqa: N802
        return QSize(120, 22)


class FlowLayout(QLayout):
    """Einfaches Fluss-Layout (nach dem Qt-Beispiel) für die Kacheln."""

    def __init__(self, parent: Optional[QWidget] = None, spacing: int = 10) -> None:
        super().__init__(parent)
        self._items: List = []
        self._spacing = spacing

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
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        return size + QSize(m.left() + m.right(), m.top() + m.bottom())

    def _layout(self, rect: QRect, apply: bool) -> int:
        m = self.contentsMargins()
        x0 = rect.x() + m.left()
        x, y = x0, rect.y() + m.top()
        right = rect.right() - m.right()
        line_h = 0
        for item in self._items:
            hint = item.sizeHint()
            if x + hint.width() > right + 1 and line_h > 0:
                x = x0
                y += line_h + self._spacing
                line_h = 0
            if apply:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x += hint.width() + self._spacing
            line_h = max(line_h, hint.height())
        return y + line_h - rect.y() + m.bottom()


def toggle_text(counts: Counts) -> str:
    return "Aktivieren" if logic.wants_enable(counts) else "Aussetzen"


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

    TILE_W = 205

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
        self.setFixedWidth(self.TILE_W)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
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
        top.addWidget(ring, 0, Qt.AlignmentFlag.AlignTop)
        title = QLabel(name + (" ›" if has_children else ""))
        title.setObjectName("azTileTitle")
        title.setWordWrap(True)
        title.setToolTip(name)
        title.setMinimumHeight(38)
        title.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        top.addWidget(title, 1)
        lay.addLayout(top)

        nums = QLabel(f"{fmt_int(counts.studied)}/{fmt_int(counts.total)} gesehen")
        nums.setObjectName("azSubtle")
        nums.setToolTip(counts_tooltip(counts))
        lay.addWidget(nums)

        bottom = QHBoxLayout()
        status = QLabel(status_text(counts))
        status.setObjectName("azSubtle")
        status.setWordWrap(True)
        bottom.addWidget(status, 1)
        btn = QPushButton(toggle_text(counts))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda _=False: on_toggle())
        bottom.addWidget(btn, 0)
        lay.addLayout(bottom)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self._on_open()
            return
        super().mouseReleaseEvent(event)
