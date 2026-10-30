"""MSVC RTTI TypeDescriptor scanner for PE32+ (Windows hoi4.exe).

MSVC encodes class names as `.?AVClassName@@` (or `.?AU` for structs) inside
TypeDescriptor objects in .rdata / .data.

TypeDescriptor (x64, approximate):
  +0x00  void*  pVFTable   (type_info vftable)
  +0x08  void*  spare
  +0x10  char   name[]     // ".?AVCGameState@@"
"""
from __future__ import annotations

import struct
from typing import Dict, List, Optional

from pe import PE
from stringscan import data_pointer_slots, find_ascii_all, rip_lea_xrefs


def scan_type_names(pe: PE, substr: str = "CGameState", limit: int = 200) -> List[dict]:
    """Find TypeDescriptor-like name strings containing substr."""
    # Search raw for .?AV / .?AU prefixes then filter
    out = []
    for prefix in (b".?AV", b".?AU"):
        for rva in find_ascii_all(pe, prefix):
            raw = pe.read_rva(rva, 256)
            if not raw:
                continue
            end = raw.find(b"\0")
            name = raw[: end if end >= 0 else len(raw)].decode("ascii", "replace")
            if substr and substr not in name:
                continue
            # TypeDescriptor base is typically name_rva - 0x10
            td_rva = rva - 0x10
            out.append({"name": name, "name_rva": rva, "td_rva": td_rva})
            if len(out) >= limit:
                return out
    return out


def demangle_simple(name: str) -> str:
    """`.?AVCGameState@@` -> `CGameState` (best-effort)."""
    if name.startswith(".?AV") or name.startswith(".?AU"):
        core = name[4:]
        if core.endswith("@@"):
            core = core[:-2]
        return core
    return name


def find_col_and_vtable(pe: PE, td_rva: int) -> dict:
    """Given TypeDescriptor RVA, find CompleteObjectLocator slots that point at it,
    and from COL infer vtable (COL is typically at vtable[-1] for single inheritance).

    COL (x64):
      +0x00 DWORD signature (1 for 64-bit)
      +0x04 DWORD offset
      +0x08 DWORD cdOffset
      +0x0C DWORD typeDescriptorRva   (RVA, not VA)
      +0x10 DWORD classDescriptorRva
      +0x14 DWORD objectBaseRva
    """
    # Search .rdata for DWORD == td_rva at COL+0x0C
    hits_col = []
    for s in pe.sections:
        if s.name not in (".rdata", ".data"):
            continue
        blob = pe.data[s.raw_ptr : s.raw_ptr + s.raw_size]
        needle = struct.pack("<I", td_rva)
        start = 0
        while True:
            i = blob.find(needle, start)
            if i < 0:
                break
            # candidate COL base = this field - 0x0C
            if i >= 0x0C and (i - 0x0C) % 4 == 0:
                col_off = i - 0x0C
                sig = struct.unpack_from("<I", blob, col_off)[0]
                if sig in (0, 1):
                    col_rva = s.virtual_address + col_off
                    hits_col.append(col_rva)
            start = i + 1
    vt_candidates = []
    for col_rva in hits_col[:20]:
        # Look for pointer-sized slots equal to ImageBase+col_rva (vtable meta pointer)
        slots = data_pointer_slots(pe, col_rva, max_hits=8)
        for slot in slots:
            # For MSVC, the vtable usually starts at slot+8 (after COL pointer)
            vt_candidates.append({"col_rva": col_rva, "col_ptr_slot": slot, "vtable_rva": slot + 8})
    return {"cols": hits_col[:20], "vtables": vt_candidates[:20]}


def catalog(pe: PE, names: Optional[List[str]] = None) -> Dict[str, dict]:
    names = names or [
        "CGameState",
        "CInGameIdler",
        "CCommandQueue",
        "CLandCombat",
        "CCountry",
        "CArmy",
        "CDivision",
        "CConsoleCmdManager",
    ]
    out = {}
    for n in names:
        tds = scan_type_names(pe, n, limit=20)
        entry = {"type_descriptors": tds, "vtables": []}
        for td in tds[:5]:
            info = find_col_and_vtable(pe, td["td_rva"])
            entry["vtables"].extend(info["vtables"])
            entry.setdefault("cols", []).extend(info["cols"])
        # also LEA xrefs to the name string (debug/assert paths)
        xrefs = []
        for td in tds[:3]:
            xrefs.extend(rip_lea_xrefs(pe, td["name_rva"], max_hits=16))
        entry["name_xrefs"] = xrefs[:32]
        out[n] = entry
    return out


def exact_type(pe: PE, class_name: str) -> Optional[dict]:
    """Recover COL/vtables for exact `.?AV{class_name}@@` (or .?AU)."""
    from stringscan import find_ascii_all
    for prefix in (".?AV", ".?AU"):
        needle = (prefix + class_name + "@@").encode("ascii")
        rvas = find_ascii_all(pe, needle)
        if not rvas:
            continue
        name_rva = rvas[0]
        td_rva = name_rva - 0x10
        info = find_col_and_vtable(pe, td_rva)
        return {
            "name": prefix + class_name + "@@",
            "name_rva": name_rva,
            "td_rva": td_rva,
            "cols": info["cols"],
            "vtables": info["vtables"],
        }
    return None
