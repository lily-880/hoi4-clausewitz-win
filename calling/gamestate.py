"""Read-only probes for CGameState once candidate RVAs exist."""
from __future__ import annotations

import struct
from typing import Any, Dict, List, Optional

import offsets as O


def _pdx_array(p, addr: int) -> Optional[dict]:
    """Read CPdxArray header hypotheses."""
    d = p.try_read(addr, 0x18)
    if not d or len(d) < 0x18:
        return None
    data, cap, size = struct.unpack_from("<Qii", d, 0)
    alloc = struct.unpack_from("<Q", d, 0x10)[0]
    return {"data": data, "capacity": cap, "size": size, "alloc": alloc}


def looks_like_gamestate(p, gs_ptr: int) -> Dict[str, Any]:
    """Heuristic checks using upstream field offsets as hypotheses."""
    H = O.HYPOTHESIS_STRUCT
    report = {"ptr": hex(gs_ptr), "ok": False, "checks": {}}
    if not gs_ptr or gs_ptr < 0x10000:
        report["checks"]["nonnull"] = False
        return report
    # countries array at +0x310 (Linux verified; hypothesis on Windows)
    countries = _pdx_array(p, gs_ptr + 0x310)
    report["checks"]["countries_array"] = countries
    if not countries:
        return report
    size = countries["size"]
    cap = countries["capacity"]
    # HOI4 has on the order of a few hundred country slots
    good_size = isinstance(size, int) and 50 <= size <= 2000 and 50 <= cap <= 5000 and size <= cap
    report["checks"]["countries_size_plausible"] = good_size
    # player tag at +0x518
    tag = None
    try:
        tag = p.i32(gs_ptr + 0x518)
    except OSError:
        pass
    report["checks"]["player_tag_raw"] = tag
    report["checks"]["player_tag_plausible"] = tag is not None and 0 <= tag < 2000
    report["ok"] = bool(good_size and report["checks"]["player_tag_plausible"])
    return report


def try_global_rva(p, rva: Optional[int]) -> Dict[str, Any]:
    if rva is None:
        return {"error": "rva is None"}
    slot = p.base + rva
    ptr = p.ptr(slot)
    out = {"rva": hex(rva), "slot": hex(slot), "value": hex(ptr) if ptr else None}
    if ptr:
        out["probe"] = looks_like_gamestate(p, ptr)
    return out


def scan_candidate_globals(p, vtable_rvas: List[int], limit_slots: int = 5000) -> List[dict]:
    """If we know a CGameState vtable RVA, scan .data-like committed regions for
    pointers to heap objects whose first qword equals runtime vtable.

    This is expensive; keep limit modest. Read-only.
    """
    if not vtable_rvas:
        return []
    runtime_vts = [p.base + r for r in vtable_rvas]
    vt_set = set(runtime_vts)
    hits = []
    # Prefer scanning the main module's .data mapping approximation: image range writable
    for m in p.regions(writable=True, min_size=0x1000):
        # skip absurdly large regions
        size = m["end"] - m["start"]
        if size > 64 << 20:
            continue
        # only look inside or near image for global slots
        if not (p.base <= m["start"] < p.base + p.image_size or p.base < m["end"] <= p.base + p.image_size):
            # still allow anonymous heaps? globals are in image .data — skip heap for slot scan
            if m["start"] < p.base or m["start"] >= p.base + p.image_size:
                continue
        data = p.try_read(m["start"], min(size, 8 * limit_slots))
        if not data:
            continue
        for i in range(0, len(data) - 8, 8):
            q = struct.unpack_from("<Q", data, i)[0]
            if q < 0x10000:
                continue
            # candidate: global slot holding pointer to object
            # read object vptr
            obj = p.try_read(q, 8)
            if not obj:
                continue
            vptr = struct.unpack_from("<Q", obj, 0)[0]
            if vptr in vt_set:
                slot_addr = m["start"] + i
                rva = slot_addr - p.base
                probe = looks_like_gamestate(p, q)
                hits.append(
                    {
                        "global_rva": hex(rva),
                        "global_addr": hex(slot_addr),
                        "object": hex(q),
                        "vptr": hex(vptr),
                        "probe": probe,
                    }
                )
                if probe.get("ok") or len(hits) >= 20:
                    if probe.get("ok"):
                        return hits
                    if len(hits) >= 20:
                        return hits
    return hits
