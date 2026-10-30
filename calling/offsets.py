"""Offset tables for Windows hoi4.exe.

IMPORTANT: Upstream Clausewitz-MCP offsets were recovered against Linux ELF 1.19.2.
They are NOT valid for Windows PE 1.19.4 unless re-verified.

Load order for WINDOWS_GLOBALS:
  1. built-in stubs (None)
  2. calling/offsets_verified.json  (committed only after manual verification)
  3. calling/offsets_runtime.json   (local live-gs heuristic; gitignored)

Static RTTI/vtable RVAs that are safely proven live under ASLR (COL slot MATCH)
are in PROVEN_STATIC and calling/tables/offsets_windows_1.19.4.json.
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

TARGET = {
    "os": "Windows",
    "exe": "hoi4.exe",
    "game_version": "1.19.4.x",
    "version_name": "Operation Postern",
    "upstream_ref": "https://github.com/smerss/Clausewitz-MCP (Linux 1.19.2 ELF)",
    "exe_sha256_1_19_4": "CF781ED178CD801643B233B7E3FCD1C0EFD19BD01AECD24BF07A35F69F10476F",
}

HYPOTHESIS_STRUCT = {
    "PDXARRAY_DATA": 0x0,
    "PDXARRAY_CAP": 0x8,
    "PDXARRAY_SIZE": 0xC,
    "PDXARRAY_ALLOC": 0x10,
    "PDXARRAY_SZ": 0x18,
    "FIXED": 100000,
    "DAYS_PER_YEAR": 365,
    "GS_COMBATS": 0x268,
    "GS_COUNTRIES": 0x310,
    "GS_MAJORS": 0x328,
    "GS_TAG2INDEX": 0x340,
    "GS_PLAYER_TAG": 0x518,
    "GS_PAUSE_HOURS": 0x908,  # Linux; NOT verified on Windows (garbage)
    "GS_DATE_YEAR": 0x478,  # hypothesis: i32 year (seen 1936)
    "GS_DATE_AUX": 0x47C,  # hypothesis: i32 (seen 31); maybe day-of-year — not full date
}

# Safely static-proven (RTTI + live COL verification). NOT globals / NOT Post.
PROVEN_STATIC = {
    "CGameState_vtable": 0x279F0F0,
    "CGameState_vtable_secondary": 0x279F148,
    "CCurrentGameState_vtable": 0x279F168,
    "CCurrentGameState_vtable_secondary": 0x279F1C0,
    "CInGameIdler_vtable": 0x29E5838,
    "CGameIdler_vtable": 0x27B4158,
    "CCommand_vtable": 0x279F4A0,
    "CArmy_vtable": 0x29D6D68,
    "CArmy_vtable_mi": [0x29D6F48, 0x29D6FB8, 0x29D7000],
    "CUnit_vtable": 0x29CFAC0,
    "CInGameIdler_queue_field_hyp": 0x530,  # idler vt+0x90 loads [this+0x530]
    "CInGameIdler_vt_post_wrapper": 0xE34E90,
    "RTTI_CGameState_name": 0x31E75A0,
    "RTTI_CCurrentGameState_name": 0x31E78B8,
    "RTTI_CCommand_name": 0x31E74B8,
    "CGameState_ctor_lea": 0x1D78AE,
}

WINDOWS_GLOBALS = {
    "G_GAMESTATE": None,
    "G_IDLER": None,
    "G_COUNTRYTAG_DB": None,
    "G_CONSOLE_MANAGER": None,
    "G_DEFAULT_ALLOC": None,
    "FN_CONSOLE_EXECUTE": None,
    "FN_CMD_QUEUE_POST": None,
}

RUNTIME = {
    "image_base": None,
    "image_size": None,
    "pid": None,
}


def _load_json(path: str) -> None:
    if not os.path.isfile(path):
        return
    try:
        data = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return
    for k, v in data.items():
        if k in WINDOWS_GLOBALS and isinstance(v, int):
            WINDOWS_GLOBALS[k] = v


_load_json(os.path.join(HERE, "offsets_verified.json"))
_load_json(os.path.join(HERE, "offsets_runtime.json"))


def require(name: str) -> int:
    v = WINDOWS_GLOBALS.get(name)
    if v is None:
        raise RuntimeError(
            "Offset %s is not recovered for Windows %s yet. "
            "See research/WINDOWS_OFFSETS.md" % (name, TARGET["game_version"])
        )
    return v
