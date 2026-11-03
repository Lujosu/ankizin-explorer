"""Schaltvorgänge und Laden über Ankis Operations-API (Undo, Hintergrund-Thread)."""

from __future__ import annotations

from typing import Callable, List, Optional

from aqt.operations import CollectionOp, QueryOp
from aqt.qt import QWidget, sip

from . import loader
from .model import Snapshot


def set_suspended(
    parent: QWidget,
    card_ids: List[int],
    suspend: bool,
    undo_label: str,
    on_done: Optional[Callable[[bool], None]] = None,
) -> None:
    """Ein Schaltvorgang = ein Undo-Schritt mit eigenem Namen. on_done(erfolgreich)."""
    ids = list(card_ids)

    def op(col):
        pos = col.add_custom_undo_entry(undo_label)
        if suspend:
            col.sched.suspend_cards(ids)
        else:
            col.sched.unsuspend_cards(ids)
        return col.merge_undo_entries(pos)

    def failed(err: Exception) -> None:
        from aqt import mw
        from aqt.utils import showWarning

        if on_done is not None:
            on_done(False)
        # Ist das Fenster inzwischen geschlossen, die Meldung am Hauptfenster zeigen
        owner = mw if sip.isdeleted(parent) else parent
        showWarning(f"AnKIzin Explorer: Schalten fehlgeschlagen.\n\n{err}", parent=owner)

    cop = CollectionOp(parent=parent, op=op).failure(failed)
    if on_done is not None:
        cop = cop.success(lambda _changes: on_done(True))
    cop.run_in_background()


def load_snapshot(
    parent: QWidget,
    show_vorklinik: bool,
    on_success: Callable[[Snapshot], None],
    on_failure: Callable[[Exception], None],
) -> None:
    QueryOp(
        parent=parent,
        op=lambda col: loader.load_snapshot(col, show_vorklinik),
        success=on_success,
    ).failure(on_failure).run_in_background()


def load_codes(
    parent: QWidget,
    known: Snapshot,
    on_success: Callable[[Snapshot], None],
    on_failure: Callable[[Exception], None],
) -> None:
    QueryOp(
        parent=parent,
        op=lambda col: known.with_codes(loader.load_codes(col, known)),
        success=on_success,
    ).failure(on_failure).run_in_background()

