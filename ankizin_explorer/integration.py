"""Einbindung in Anki: Extras-Menü, Toolbar-Link, Onigiri-Seitenleiste, Hooks (SPEC 6)."""

from __future__ import annotations

import importlib
import sys
import time
from typing import Optional

from aqt import gui_hooks, mw
from aqt.qt import QAction, QKeySequence
from aqt.utils import tooltip

from . import config

COMMAND = "ankizin_explorer_open"
ONIGIRI_ENTRY = "ankizin_explorer.open"
ONIGIRI_ID = "1011095603"
LABEL = "AnKIzin Explorer"

# Einfaches Baum-Symbol; Onigiri nutzt es als Maske (einfarbig)
ICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<path d="M5 3a2 2 0 1 1 0 4 2 2 0 0 1 0-4zm-1 5h2v3h5v2H6v5h5v2H4zm9 1h8v4h-8zm0 7h8v4h-8z'
    'M11 3h10v4H11z"/></svg>'
)

_window = None
_last_open = 0.0
_onigiri_done = False


def open_window() -> None:
    global _window, _last_open
    if mw.col is None:
        tooltip("Bitte zuerst ein Profil öffnen.")
        return
    from .ui.window import ExplorerWindow

    now = time.monotonic()
    if _window is None:
        _window = ExplorerWindow(mw)
    elif now - _last_open > 1.0:
        # Doppelte Aufrufe kurz hintereinander (Onigiri leitet Toolbar-Befehle zusätzlich
        # weiter, ohne `handled` zu prüfen) nur nach vorne holen, nicht neu laden.
        _window.reload("full")
    _last_open = now
    _window.show()
    _window.raise_()
    _window.activateWindow()


def _close_window() -> None:
    global _window
    if _window is not None:
        _window.close()
        _window.deleteLater()
        _window = None


# --- Menü und Toolbar --------------------------------------------------------------


def _shortcut_free(seq: str) -> bool:
    wanted = QKeySequence(seq)
    for action in mw.findChildren(QAction):
        if any(s == wanted for s in action.shortcuts()):
            return False
    return True


def _add_menu() -> None:
    action = QAction(LABEL, mw)
    action.triggered.connect(open_window)
    shortcut = config.shortcut()
    if shortcut and _shortcut_free(shortcut):
        action.setShortcut(QKeySequence(shortcut))
    elif shortcut:
        print(f"[{LABEL}] Tastenkürzel {shortcut} ist schon belegt; Menüeintrag ohne Kürzel.")
    mw.form.menuTools.addAction(action)


def _toolbar_links(links, toolbar) -> None:
    links.append(
        toolbar.create_link(
            COMMAND,
            "AnKIzin",
            open_window,
            tip="AnKIzin Explorer öffnen",
            id="ankizin_explorer",
        )
    )


def _on_js_message(handled, message, _context):
    # Onigiri-Seitenleiste (pycmd). Hat ein anderer Hook (z. B. Onigiris
    # Toolbar-Weiterleitung) den Befehl schon erledigt, nicht doppelt öffnen.
    if message != COMMAND:
        return handled
    if handled[0]:
        return handled
    open_window()
    return (True, None)


# --- Onigiri ------------------------------------------------------------------------


def _onigiri_register_fn():
    """register_sidebar_action aus einem geladenen, aktiven Onigiri – sonst None."""
    for meta in mw.addonManager.all_addon_meta():
        try:
            if not meta.enabled:
                continue
            name = (meta.human_name() or "").casefold()
            if meta.ankiweb_id() != ONIGIRI_ID and meta.dir_name != ONIGIRI_ID and "onigiri" not in name:
                continue
            # Nur ein bereits von Anki geladenes Addon benutzen, nie selbst eines starten
            if meta.dir_name not in sys.modules:
                continue
            mod = importlib.import_module(meta.dir_name)
            fn = getattr(mod, "register_sidebar_action", None)
            if fn is None:
                fn = getattr(importlib.import_module(meta.dir_name + ".api.sidebar"), "register_sidebar_action", None)
            if callable(fn):
                return fn
        except Exception as err:
            print(f"[{LABEL}] Onigiri-Erkennung übersprungen: {err}")
    return None


def _register_onigiri() -> None:
    global _onigiri_done
    if _onigiri_done:
        return
    _onigiri_done = True
    try:
        fn = _onigiri_register_fn()
        if fn is not None:
            fn(entry_id=ONIGIRI_ENTRY, label=LABEL, command=COMMAND, icon_svg=ICON_SVG)
    except Exception as err:
        print(f"[{LABEL}] Onigiri-Eintrag nicht möglich: {err}")


# --- Hooks ----------------------------------------------------------------------


def _on_operation(changes, handler) -> None:
    if _window is not None and _window.isVisible():
        _window.on_collection_changed(changes)


def _on_sync_finished() -> None:
    if _window is not None and _window.isVisible():
        _window.reload("full")


def _on_theme_changed() -> None:
    if _window is not None:
        _window.apply_theme()


def _on_config_updated(_conf) -> None:
    if _window is not None:
        _window.on_config_changed()


def setup() -> None:
    _add_menu()
    gui_hooks.top_toolbar_did_init_links.append(_toolbar_links)
    gui_hooks.webview_did_receive_js_message.append(_on_js_message)
    gui_hooks.profile_did_open.append(_register_onigiri)
    gui_hooks.profile_will_close.append(_close_window)
    gui_hooks.operation_did_execute.append(_on_operation)
    gui_hooks.sync_did_finish.append(_on_sync_finished)
    gui_hooks.theme_did_change.append(_on_theme_changed)
    mw.addonManager.setConfigUpdatedAction(config.ADDON, _on_config_updated)


def window() -> Optional[object]:
    return _window
