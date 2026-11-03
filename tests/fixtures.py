"""Kleine, realistische AnKIzin-Sammlung als Roh-Zeilen (generische Tag-Namen)."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from ankizin_explorer.model import QUEUE_SUSPENDED

ROOT = "#Ankizin_vAnkiCollab"
KLINIK = f"{ROOT}::#M2_M3_Klinik::#AMBOSS::Bibliothek-Klinik"
VORKLINIK = f"{ROOT}::#M1_Vorklinik_(work_in_progress)::#AMBOSS::Bibliothek-Vorklinik"

TB_INF = f"{KLINIK}::Infektiologie::Bakterielle_Erkrankungen::Tuberkulose"
TB_PNEUMO = f"{KLINIK}::Innere_Medizin::Pneumologie::Infektiöse_Atemwegserkrankungen::Tuberkulose"
TB_RAD = f"{KLINIK}::Radiologie::Thorax::Tuberkulose"
PNEUMONIE = (
    f"{KLINIK}::Innere_Medizin::Pneumologie::Infektiöse_Atemwegserkrankungen::"
    "Pneumonie_(Lungenentzündung)"
)
LAE = f"{KLINIK}::Innere_Medizin::Pneumologie::Lungengefäßerkrankungen::Lungenembolie_(Lungenarterienembolie,_LAE)"
PBC = (
    f"{KLINIK}::(fächerübergreifend)_Autoimmun-_und_allergische_Erkrankungen::"
    "Primär_biliäre_Cholangitis_(PBC,_Primär_billiäre_Zirrhose,_PBZ)"
)
SALMONELLA = (
    f"{KLINIK}::Infektiologie::Bakterielle_Erkrankungen::Systematik_der_Bakterien::"
    "06-Gramnegative_Stäbchen::02-Salmonella_(Salmonella_enterica)::02-Serovar_Typhi_&_Paratyphi"
)
PNEUMO_DIRECT = f"{KLINIK}::Innere_Medizin::Pneumologie"
VK_FETT = f"{VORKLINIK}::#Fächer::Anatomie::01-Grundlagen_der_Anatomie::Fettgewebe"

META = [
    f"{ROOT}::§Projekt_Anki::Bildquelle",
    f"{ROOT}::!MARKIERE_DIESE_KARTEN::Fehler",
    f"{ROOT}::§NEW_CARDS::2025-01",
    f"{ROOT}::#UNIVERSITÄTEN::Beispiel-Uni::Semester_5",
    f"{ROOT}::#M2_M3_Klinik::#AMBOSS::M2-100-Tage-Lernplan::Lerntag_01",
    f"{ROOT}::#M2_M3_Klinik::#AMBOSS::M2-TOP100-Themen::Pneumonie",
    "#Ankizin_v5::#M2_M3_Klinik::#AMBOSS::Bibliothek-Klinik::Innere_Medizin::Altlast",
]

# Decks
DECKS = [
    (1, "Default"),
    (10, "Ankizin"),
    (11, "Ankizin::!Wie_nutze_ich_das_Deck?"),
    (12, "Ankizin::M2_M3_Klinik"),
    (13, "Ankizin::M2_M3_Klinik::Innere_Medizin"),
    (14, "Ankizin::M2_M3_Klinik::Innere_Medizin::Pneumologie"),
    (15, "Ankizin::M2_M3_Klinik::Infektiologie_und_Hygiene"),
    (16, "Ankizin::M2_M3_Klinik::Radiologie"),
    (17, "Ankizin::M2_M3_Klinik::Allgemein-,Thorax-_und_Gefäßchirurgie"),
    (18, "Ankizin::M1_Vorklinik"),
    (19, "Ankizin::M1_Vorklinik::Anatomie"),
    (20, "Ankizin::M1_Vorklinik::Anatomie::Histologie"),
    (30, "Gefiltert"),
]

NEW, SEEN, MATURE = "new", "seen", "mature"


class Builder:
    def __init__(self) -> None:
        self.notes: List[Tuple[int, str]] = []
        self.cards: List[Tuple[int, int, int, int, int, int, int]] = []
        self._nid = 1000
        self._cid = 5000

    def note(
        self,
        tags: Sequence[str],
        cards: Sequence[Tuple[str, bool]] = ((NEW, True),),
        did: int = 14,
        odid: int = 0,
    ) -> List[int]:
        """Notiz mit Karten [(Stufe, ausgesetzt)]; liefert die Karten-IDs."""
        self._nid += 1
        nid = self._nid
        self.notes.append((nid, " " + " ".join(list(tags) + META[:2]) + " "))
        ids = []
        for stage, suspended in cards:
            self._cid += 1
            ctype, ivl = {NEW: (0, 0), SEEN: (2, 5), MATURE: (2, 40)}[stage]
            queue = QUEUE_SUSPENDED if suspended else (0 if stage == NEW else 2)
            self.cards.append((self._cid, nid, did, odid, queue, ctype, ivl))
            ids.append(self._cid)
        return ids


def sample(show: Optional[Dict[str, object]] = None):
    """Standard-Fixture: Tuberkulose an drei Stellen, Pneumonie, LAE, PBC, Salmonellen."""
    b = Builder()
    ids = {}
    ids["tb"] = b.note([TB_INF, TB_PNEUMO, TB_RAD], [(NEW, True), (SEEN, True)], did=15)
    ids["pneumonie"] = b.note([PNEUMONIE], [(NEW, True), (MATURE, True), (SEEN, True)], did=14)
    ids["lae"] = b.note([LAE], [(NEW, True)], did=14)
    ids["pbc"] = b.note([PBC, META[4]], [(NEW, True)], did=13)
    ids["salmonella"] = b.note([SALMONELLA], [(NEW, True), (NEW, True)], did=15)
    ids["pneumo_direct"] = b.note([PNEUMO_DIRECT], [(NEW, True)], did=14)
    ids["vk"] = b.note([VK_FETT], [(NEW, True)], did=20)
    ids["meta_only"] = b.note(META, [(NEW, True)], did=13)
    ids["altlast"] = b.note([META[6]], [(NEW, True)], did=13)
    return b, ids
