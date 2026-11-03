"""Addon-Konfiguration (config.json)."""

from __future__ import annotations

from typing import Any, Dict

ADDON = __name__.split(".")[0]
KEY_VORKLINIK = "vorklinik_anzeigen"
KEY_SHORTCUT = "tastenkuerzel"
# Ctrl+Shift+E (SPEC-Vorschlag) ist in Anki schon „Exportieren“
DEFAULTS: Dict[str, Any] = {KEY_VORKLINIK: False, KEY_SHORTCUT: "Ctrl+Alt+A"}


def _manager():
    from aqt import mw

    return mw.addonManager if mw is not None else None


def get() -> Dict[str, Any]:
    conf = dict(DEFAULTS)
    mgr = _manager()
    if mgr is not None:
        try:
            conf.update(mgr.getConfig(ADDON) or {})
        except Exception:
            pass
    return conf


def show_vorklinik() -> bool:
    return bool(get().get(KEY_VORKLINIK, False))


def shortcut() -> str:
    value = get().get(KEY_SHORTCUT)
    return value.strip() if isinstance(value, str) else ""


def set_value(key: str, value: Any) -> None:
    mgr = _manager()
    if mgr is None:
        return
    conf = get()
    conf[key] = value
    mgr.writeConfig(ADDON, conf)
