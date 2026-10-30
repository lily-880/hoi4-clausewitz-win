"""Offset tables for Windows hoi4.exe.

IMPORTANT: Upstream Clausewitz-MCP offsets were recovered against Linux ELF 1.19.2.
They are NOT valid for Windows PE 1.19.4. Values below marked status=stub or
status=unverified must not be used for writes or command injection.

Struct *field* offsets recovered from serializers may be similar across platforms
when the C++ layout matches, but global RVAs and function addresses almost always differ.
"""
from __future__ import annotations

TARGET = {
    "os": "Windows",
    "exe": "hoi4.exe",
    "game_version": "1.19.4.0",
    "version_name": "Operation Postern",
    "upstream_ref": "https://github.com/smerss/Clausewitz-MCP (Linux 1.19.2 ELF)",
}

# ---------------------------------------------------------------------------
# Struct field offsets that are *often* layout-stable (still verify before use)
# Copied from upstream as HYPOTHESES only — status unverified on Windows.
# ---------------------------------------------------------------------------
HYPOTHESIS_STRUCT = {
    # CPdxArray
    "PDXARRAY_DATA": 0x0,
    "PDXARRAY_CAP": 0x8,
    "PDXARRAY_SIZE": 0xC,
    "PDXARRAY_ALLOC": 0x10,
    "PDXARRAY_SZ": 0x18,
    # Fixed point scale
    "FIXED": 100000,
    "DAYS_PER_YEAR": 365,
}

# Global RVAs / function RVAs: MUST be regenerated for Windows PE.
# Left at None intentionally so callers fail closed.
WINDOWS_GLOBALS = {
    "G_GAMESTATE": None,       # CGameState*
    "G_IDLER": None,           # CInGameIdler*
    "G_COUNTRYTAG_DB": None,
    "G_CONSOLE_MANAGER": None,
    "G_DEFAULT_ALLOC": None,
    "FN_CONSOLE_EXECUTE": None,
    "FN_CMD_QUEUE_POST": None,  # CCommandQueue::Post — Phase 2
}

# Proven at runtime by doctor/status (filled dynamically, not committed guesses)
RUNTIME = {
    "image_base": None,
    "image_size": None,
    "pid": None,
}


def require(name: str) -> int:
    v = WINDOWS_GLOBALS.get(name)
    if v is None:
        raise RuntimeError(
            "Offset %s is not recovered for Windows %s yet. "
            "See research/WINDOWS_OFFSETS.md" % (name, TARGET["game_version"])
        )
    return v
