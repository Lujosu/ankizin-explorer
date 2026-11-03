"""Farben passend zum Anki-Theme (hell/dunkel), ruhig und an Onigiri angelehnt."""

from __future__ import annotations

from aqt.qt import QColor


def night_mode() -> bool:
    try:
        from aqt.theme import theme_manager

        return bool(theme_manager.night_mode)
    except Exception:
        return False


def _anki_color(name: str, fallback: str) -> QColor:
    try:
        from aqt import colors
        from aqt.theme import theme_manager

        return theme_manager.qcolor(getattr(colors, name))
    except Exception:
        return QColor(fallback)


class Palette:
    def __init__(self) -> None:
        dark = night_mode()
        self.dark = dark
        # Ring: neu / gesehen / gefestigt + Spur
        self.new = QColor("#5f6b7a" if dark else "#b3bdca")
        self.seen = QColor("#d9a441" if dark else "#efb44a")
        self.mature = QColor("#4fa67d" if dark else "#4caf84")
        self.track = QColor("#383d45" if dark else "#e7e9ed")
        self.canvas = _anki_color("CANVAS", "#2c2c2c" if dark else "#f5f5f5")
        self.elevated = _anki_color("CANVAS_ELEVATED", "#363636" if dark else "#ffffff")
        self.border = _anki_color("BORDER_SUBTLE", "#444444" if dark else "#e0e0e0")
        self.fg = _anki_color("FG", "#eeeeee" if dark else "#202020")
        self.fg_subtle = _anki_color("FG_SUBTLE", "#aaaaaa" if dark else "#6b6b6b")
        self.accent = _anki_color("BUTTON_PRIMARY_BG", "#4f8fd6" if dark else "#3a7bd5")
        self.banner_bg = QColor("#3b3424" if dark else "#fff6e0")
        self.banner_border = QColor("#6b5a2e" if dark else "#f0d590")

    def css(self, color: QColor) -> str:
        return color.name()

    def stylesheet(self) -> str:
        c = self.css
        return f"""
QFrame#azTile {{
    background: {c(self.elevated)};
    border: 1px solid {c(self.border)};
    border-radius: 12px;
}}
QFrame#azTile:hover {{
    border: 1px solid {c(self.accent)};
}}
QFrame#azHeader {{
    background: {c(self.elevated)};
    border: 1px solid {c(self.border)};
    border-radius: 14px;
}}
QFrame#azBanner {{
    background: {c(self.banner_bg)};
    border: 1px solid {c(self.banner_border)};
    border-radius: 10px;
}}
QLabel#azSubtle {{
    color: {c(self.fg_subtle)};
}}
QLabel#azTitle {{
    font-size: 17px;
    font-weight: 600;
}}
QLabel#azTileTitle {{
    font-weight: 600;
}}
QLineEdit#azSearch {{
    border: 1px solid {c(self.border)};
    border-radius: 8px;
    padding: 4px 8px;
}}
QScrollArea#azTiles, QWidget#azTilesInner {{
    background: transparent;
    border: none;
}}
"""
