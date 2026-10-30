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


def heap_find_gamestate(p, vtable_rvas, max_region=16 << 20, max_hits=12):
    """Scan writable non-image regions for objects whose vptr matches known GS vtables.
    Works without G_GAMESTATE when a campaign is loaded. Read-only.
    """
    import struct
    runtime = [p.base + r for r in vtable_rvas]
    needles = [struct.pack("<Q", v) for v in runtime]
    hits = []
    for m in p.regions(writable=True, min_size=0x1000):
        start, end = m["start"], m["end"]
        size = end - start
        if size > max_region:
            continue
        if p.base <= start < p.base + p.image_size:
            continue
        data = p.try_read(start, size)
        if not data:
            continue
        for needle, vt in zip(needles, runtime):
            off = 0
            while len(hits) < max_hits:
                i = data.find(needle, off)
                if i < 0:
                    break
                if i % 8 == 0:
                    obj = start + i
                    hits.append({"object": hex(obj), "vptr": hex(vt), "probe": looks_like_gamestate(p, obj)})
                off = i + 8
        if len(hits) >= max_hits:
            break
    return hits


def probe_zero_data_slots(p, slot_rvas, vtable_rvas):
    """Live-check static zero-init .data slots that code writes (pointer globals)."""
    import struct
    vt_set = {p.base + r for r in vtable_rvas}
    out = []
    for rva in slot_rvas:
        slot = p.base + rva
        ptr = p.ptr(slot)
        entry = {"global_rva": hex(rva), "value": hex(ptr) if ptr else None}
        if ptr and ptr > 0x10000:
            obj = p.try_read(ptr, 8)
            if obj:
                vptr = struct.unpack_from("<Q", obj, 0)[0]
                entry["vptr"] = hex(vptr)
                if vptr in vt_set:
                    entry["probe"] = looks_like_gamestate(p, ptr)
                    entry["match"] = True
                    out.append(entry)
                    if entry["probe"].get("ok"):
                        return out  # early exit on strong hit
    return out


def _rtti_name_from_vtable(pe, vt_rva: int):
    """Best-effort .?AV name from COL at vtable-8 (PE image bytes)."""
    import struct
    try:
        col_va = struct.unpack_from("<Q", pe.data, pe.rva_to_off(vt_rva - 8))[0]
        if not col_va:
            return None
        col_rva = col_va - pe.image_base if col_va >= pe.image_base else col_va
        td_rva = struct.unpack_from("<I", pe.data, pe.rva_to_off(col_rva) + 0x0C)[0]
        name = pe.data[pe.rva_to_off(td_rva) + 0x10 :].split(b"\0", 1)[0]
        return name.decode("ascii", "replace")
    except Exception:
        return None


def detect_session(p, pe=None) -> Dict[str, Any]:
    """Classify lobby/frontend vs in-game via G_IDLER (preferred) + GS.

    Phase 2f proved G_GAMESTATE can be live while G_IDLER is still
    CFrontEndIdler (lobby with bookmark/scenario GS). Treat idler type as
    the session gate for Post-path and army spawn — not mere GS presence.
    """
    import offsets as O

    FE = O.PROVEN_STATIC.get("CFrontEndIdler_vtable")
    IG = O.PROVEN_STATIC["CInGameIdler_vtable"]
    APP = O.PROVEN_STATIC.get("CGameApplication_vtable")
    gidler = O.WINDOWS_GLOBALS.get("G_IDLER")
    ggs = O.WINDOWS_GLOBALS.get("G_GAMESTATE")

    out: Dict[str, Any] = {
        "session": "unknown",
        "in_game": False,
        "frontend": False,
        "G_IDLER": hex(gidler) if isinstance(gidler, int) else None,
        "G_GAMESTATE": hex(ggs) if isinstance(ggs, int) else None,
        "idler": None,
        "gamestate_live": False,
        "user_action": None,
        "guidance": None,
        "signals": {},
    }

    idler_ptr = None
    if isinstance(gidler, int):
        try:
            idler_ptr = p.u64(p.base + gidler)
        except OSError:
            idler_ptr = None
    out["signals"]["idler_ptr"] = hex(idler_ptr) if idler_ptr else None

    gs_ptr = None
    if isinstance(ggs, int):
        try:
            gs_ptr = p.u64(p.base + ggs)
        except OSError:
            gs_ptr = None
    out["signals"]["gs_ptr"] = hex(gs_ptr) if gs_ptr else None
    out["gamestate_live"] = bool(gs_ptr and gs_ptr > 0x10000)

    if not idler_ptr:
        out["session"] = "menu_or_unloaded"
        out["guidance"] = (
            "No live idler at G_IDLER. Start HOI4 and load a campaign/save until the "
            "map is visible, then re-run: python clausewitz_win.py status"
        )
        out["user_action"] = "LOAD_CAMPAIGN_MAP"
        return out

    try:
        vt = p.u64(idler_ptr)
        vt_rva = vt - p.base
    except OSError:
        out["session"] = "unreadable_idler"
        out["user_action"] = "LOAD_CAMPAIGN_MAP"
        out["guidance"] = "Idler pointer unreadable; reload into a campaign map."
        return out

    rtti = _rtti_name_from_vtable(pe, vt_rva) if pe is not None else None

    idler_info: Dict[str, Any] = {
        "ptr": hex(idler_ptr),
        "vtable_rva": hex(vt_rva),
        "rtti": rtti,
    }
    try:
        q = p.u64(idler_ptr + O.PROVEN_STATIC["CInGameIdler_queue_field_hyp"])
        idler_info["field_0x530"] = hex(q) if q else None
        if q:
            qvt = p.u64(q)
            qvt_rva = qvt - p.base if p.base <= qvt < p.base + p.image_size else None
            idler_info["field_0x530_vtable_rva"] = hex(qvt_rva) if qvt_rva is not None else None
            if pe is not None and qvt_rva is not None:
                idler_info["field_0x530_rtti"] = _rtti_name_from_vtable(pe, qvt_rva)
            elif APP is not None and qvt_rva == APP:
                idler_info["field_0x530_rtti"] = ".?AVCGameApplication@@"
    except OSError:
        pass
    out["idler"] = idler_info

    if vt_rva == IG or (rtti and "CInGameIdler" in rtti):
        out["session"] = "in_game"
        out["in_game"] = True
        out["signals"]["idler_class"] = "CInGameIdler"
        out["guidance"] = (
            "CInGameIdler live — resolve idler+0x530 queue object READ-ONLY; "
            "hunt FN_CMD_QUEUE_POST; scan CArmy/CArmyGroup. Posting stays DISABLED."
        )
        out["user_action"] = None
        return out

    if FE is not None and (vt_rva == FE or (rtti and "CFrontEndIdler" in rtti)):
        out["session"] = "frontend"
        out["frontend"] = True
        out["signals"]["idler_class"] = "CFrontEndIdler"
        out["user_action"] = "LOAD_CAMPAIGN_MAP"
        out["guidance"] = (
            "G_IDLER is CFrontEndIdler (lobby/frontend). Gamestate may already be "
            "allocated, but armies are not spawned and Post-path +0x530 points at "
            "CGameApplication (setter), not a command queue. "
            "USER ACTION: load a campaign or save until the map UI is visible, then "
            "re-run: python clausewitz_win.py status   or   "
            "python scripts/phase2g_session_postpath.py"
        )
        return out

    out["session"] = "other_idler"
    out["signals"]["idler_class"] = rtti or hex(vt_rva)
    out["user_action"] = "LOAD_CAMPAIGN_MAP"
    out["guidance"] = (
        "Unexpected idler type %s. Load into a campaign map and re-probe."
        % (rtti or hex(vt_rva))
    )
    return out



def read_campaign_summary(p, gs_ptr: int) -> Dict[str, Any]:
    """Read-only campaign fields from a live CGameState/CCurrentGameState object.

    Only fields that pass local sanity checks are marked verified=True.
    Date year at +0x478 is a hypothesis (seen as 1936 on start); month/day layout TBD.
    Divisions count is NOT exposed until country-struct offsets are proven.
    """
    out: Dict[str, Any] = {"gs_ptr": hex(gs_ptr), "fields": {}, "verified": {}}
    if not gs_ptr or gs_ptr < 0x10000:
        out["error"] = "bad gs_ptr"
        return out
    blob = p.try_read(gs_ptr, 0x600)
    if not blob or len(blob) < 0x520:
        out["error"] = "short read"
        return out
    vptr = struct.unpack_from("<Q", blob, 0)[0]
    out["vptr"] = hex(vptr)

    countries = _pdx_array(p, gs_ptr + O.HYPOTHESIS_STRUCT["GS_COUNTRIES"])
    out["fields"]["countries"] = countries
    if countries and 50 <= countries["size"] <= 2000 and countries["size"] <= countries["capacity"] <= 5000:
        out["verified"]["countries_count"] = countries["size"]

    majors = _pdx_array(p, gs_ptr + O.HYPOTHESIS_STRUCT["GS_MAJORS"])
    out["fields"]["majors"] = majors
    if majors and 1 <= majors["size"] <= 20 and majors["size"] <= majors["capacity"] <= 64:
        out["verified"]["majors_count"] = majors["size"]

    tag = struct.unpack_from("<i", blob, O.HYPOTHESIS_STRUCT["GS_PLAYER_TAG"])[0]
    out["fields"]["player_tag_raw"] = tag
    if 0 <= tag < 2000:
        out["verified"]["player_tag"] = tag

    # Date hypothesis: i32 year at +0x478 (observed 1936); +0x47c aux (seen 31) maybe DOY — not full Y-M-D
    year = struct.unpack_from("<i", blob, O.HYPOTHESIS_STRUCT.get("GS_DATE_YEAR", 0x478))[0]
    aux = struct.unpack_from("<i", blob, O.HYPOTHESIS_STRUCT.get("GS_DATE_AUX", 0x47C))[0]
    out["fields"]["date_year_hypothesis"] = year
    out["fields"]["date_aux_0x47c"] = aux
    out["fields"]["date_aux_note"] = "hypothesis only (possible day-of-year); full date not proven"
    if 1936 <= year <= 1950:
        out["verified"]["date_year"] = year
        out["verified"]["date_note"] = "year@+0x478; full Y-M-D not confirmed (aux@+0x47c unproven)"
    # expose aux in fields always; never mark verified without independent UI/day proof
    out["fields"]["date_full"] = None

    out["fields"]["divisions_count"] = None
    out["fields"]["divisions_note"] = (
        "stubbed — need G_IDLER=CInGameIdler (map). Frontend: 0 CArmy/CArmyGroup/CUnit "
        "heap hits (~6.5GB). CO_ARMIES@0x290 empty. Phase 2g"
    )
    return out


def try_global_summary(p, rva: Optional[int]) -> Dict[str, Any]:
    base = try_global_rva(p, rva)
    if base.get("value"):
        base["campaign"] = read_campaign_summary(p, int(base["value"], 16))
    return base
