"""Read-only probes for CGameState once candidate RVAs exist."""
from __future__ import annotations

import struct
from typing import Any, Dict, List, Optional

import offsets as O
from country_tags import tag_for_index


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
    # Cheap layout check only: 0x518 is the old player-index hypothesis and
    # is not the human player on 1.19.4 Windows. 0x520 was the human index
    # in the 2026-11-13 live session. Either being in range is enough here.
    legacy = None
    observed = None
    try:
        legacy = p.i32(gs_ptr + 0x518)
    except OSError:
        pass
    try:
        observed = p.i32(gs_ptr + 0x520)
    except OSError:
        pass
    report["checks"]["player_tag_legacy_0x518"] = legacy
    report["checks"]["player_index_observed_0x520"] = observed
    report["checks"]["player_tag_raw"] = observed if observed is not None else legacy
    plausible = (
        (observed is not None and 0 <= observed < 2000)
        or (legacy is not None and 0 <= legacy < 2000)
    )
    report["checks"]["player_tag_plausible"] = plausible
    report["ok"] = bool(good_size and plausible)
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
    IG_OBS = O.PROVEN_STATIC.get("in_game_idler_vtable_observed") or []
    if isinstance(IG_OBS, int):
        IG_OBS = [IG_OBS]
    IN_GAME_VTS = {IG, *IG_OBS}
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

    if vt_rva in IN_GAME_VTS or (rtti and "CInGameIdler" in rtti):
        out["session"] = "in_game"
        out["in_game"] = True
        if vt_rva == IG or (rtti and "CInGameIdler" in rtti):
            out["signals"]["idler_class"] = "CInGameIdler"
            out["guidance"] = (
                "CInGameIdler live — idler+0x530 is CGameApplication (Post hyp REJECTED). "
                "Hunt real queue elsewhere (CCommand soft-call / session graph). "
                "CO_ARMIES@0x290 CArmy* is division-like on Windows. Posting stays DISABLED."
            )
        else:
            out["signals"]["idler_class"] = "observed_in_game_idler"
            out["guidance"] = (
                "Observed in-game idler vtable %s live (campaign map confirmed; "
                "class name not RTTI-proven). Session gate treats this as in_game. "
                "Posting stays DISABLED."
                % hex(vt_rva)
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
            "USER ACTION: get onto the map (agent: python scripts/launch_into_map.py "
            "--hands-off; same-version -start_save=NAME only). Then re-run: "
            "python clausewitz_win.py status   or   "
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





def _i32_at(p, addr: int) -> Optional[int]:
    blob = p.try_read(addr, 4)
    if not blob or len(blob) < 4:
        return None
    return struct.unpack_from("<i", blob, 0)[0]


def _u64_at(p, addr: int) -> Optional[int]:
    blob = p.try_read(addr, 8)
    if not blob or len(blob) < 8:
        return None
    return struct.unpack_from("<Q", blob, 0)[0]


def resolve_player_country(p, gs_ptr: int, countries: Optional[dict] = None) -> Dict[str, Any]:
    """Resolve the human player's CCountry index.

    GS_PLAYER_TAG@0x518 is the old hypothesis and must not be used alone:
    on HOI4 1.19.4 Windows (live 2026-11-13) it read 15 (Republican Spain)
    while the human player was Ethiopia at index 44.

    Preference:
      1. GS+0x520 when it names a valid country. Live 2026-11-13: this
         followed a console `tag` switch (ETH 44 -> CHI 38) while the
         CCountry+0x538/+0x53C flags stayed on the original country.
      2. The unique country whose observed flags at +0x538 and +0x53C
         are both 1, only if (1) is unavailable. Those flags are not
         the current player after `tag`.
    """
    H = O.HYPOTHESIS_STRUCT
    out: Dict[str, Any] = {
        "ok": False,
        "player_index": None,
        "country_ptr": None,
        "source": None,
        "legacy_gs_0x518": None,
        "observed_gs_0x520": None,
        "human_flag_indices": [],
        "tag": None,
        "reason": None,
    }
    if not gs_ptr or gs_ptr < 0x10000:
        out["reason"] = "bad gs"
        return out
    if countries is None:
        countries = _pdx_array(p, gs_ptr + H["GS_COUNTRIES"])
    out["legacy_gs_0x518"] = _i32_at(p, gs_ptr + H["GS_PLAYER_TAG"])
    out["observed_gs_0x520"] = _i32_at(p, gs_ptr + H.get("GS_PLAYER_INDEX_OBSERVED", 0x520))
    if not countries or not (50 <= countries["size"] <= 2000):
        out["reason"] = "countries implausible"
        return out
    n = countries["size"]
    flag_a = H.get("CO_HUMAN_PLAYER_FLAG_A", 0x538)
    hits: List[int] = []
    partial: List[dict] = []
    for idx in range(n):
        cptr = _u64_at(p, countries["data"] + idx * 8)
        if not cptr:
            continue
        blob = p.try_read(cptr + flag_a, 8)
        if not blob or len(blob) < 8:
            continue
        a, b = struct.unpack_from("<ii", blob, 0)
        if a == 1 and b == 1:
            hits.append(idx)
        elif a == 1 or b == 1:
            partial.append({"index": idx, "flag_a": a, "flag_b": b})
    out["human_flag_indices"] = hits
    if partial:
        out["human_flag_partial"] = partial
    cand_520 = out["observed_gs_0x520"]
    valid_520 = False
    if isinstance(cand_520, int) and 0 <= cand_520 < n:
        valid_520 = bool(_u64_at(p, countries["data"] + cand_520 * 8))

    if len(hits) == 1:
        out["original_human_index"] = hits[0]
    if valid_520:
        out["player_index"] = cand_520
        out["ok"] = True
        if len(hits) == 1 and hits[0] == cand_520:
            out["source"] = "gs_0x520+human_flags"
        else:
            out["source"] = "gs_0x520"
            if len(hits) == 1 and hits[0] != cand_520:
                # Flags still name the country selected at game start;
                # they do not follow console `tag`.
                out["human_flags_unmoved"] = hits[0]
    elif len(hits) == 1:
        out["player_index"] = hits[0]
        out["ok"] = True
        out["source"] = "human_flags"
        out["reason"] = "GS+0x520 not a valid country; fell back to human flags"
    else:
        out["reason"] = "GS+0x520 not a valid country and no unique human-player flag"
        return out

    cptr = _u64_at(p, countries["data"] + out["player_index"] * 8)
    out["country_ptr"] = hex(cptr) if cptr else None
    if not cptr:
        out["ok"] = False
        out["reason"] = "null country"
        return out
    out["tag"] = tag_for_index(out["player_index"])
    return out


def probe_player_armies(p, pe, gs_ptr: int) -> Dict[str, Any]:
    """READ-ONLY: player CCountry + CO_ARMIES (0x290) CArmy* array.

    Promoted after in-game samples (sizes 17 / 50, first_rtti=.?AVCArmy@@).
    On Windows each CArmy carries CSubUnitDefinition@0x138, CProvince@0x1f0,
    CReferencedDivisionTemplate@0x3b8 and has no nested unit array — treat
    armies_count as divisions_count (division-level units) when markers match.
    """
    out: Dict[str, Any] = {
        "ok": False,
        "armies_count": None,
        "divisions_count": None,
        "fleets_count": None,
        "div_templates_count": None,
        "armies_offset": hex(O.HYPOTHESIS_STRUCT.get("CO_ARMIES", 0x290)),
    }
    if not gs_ptr or gs_ptr < 0x10000:
        out["reason"] = "bad gs"
        return out
    countries = _pdx_array(p, gs_ptr + O.HYPOTHESIS_STRUCT["GS_COUNTRIES"])
    resolved = resolve_player_country(p, gs_ptr, countries)
    out["player_resolve"] = resolved
    out["player_tag_legacy_0x518"] = resolved.get("legacy_gs_0x518")
    tag = resolved.get("player_index")
    out["player_tag"] = tag
    out["player_tag_letter"] = resolved.get("tag")
    if not resolved.get("ok") or tag is None:
        out["reason"] = resolved.get("reason") or "player resolve failed"
        return out
    if not countries or not (50 <= countries["size"] <= 2000):
        out["reason"] = "countries implausible"
        return out
    cptr = struct.unpack_from("<Q", p.try_read(countries["data"] + tag * 8, 8) or b"\0"*8, 0)[0]
    out["country_ptr"] = hex(cptr) if cptr else None
    if not cptr:
        out["reason"] = "null country"
        return out
    off = O.HYPOTHESIS_STRUCT.get("CO_ARMIES", 0x290)
    arr = _pdx_array(p, cptr + off)
    out["array"] = arr
    if not arr or not (0 < arr["size"] <= 2000 and arr["size"] <= arr["capacity"] <= 4000):
        out["reason"] = "army array empty/implausible (need map / CInGameIdler)"
        return out
    # confirm first elem RTTI when pe available
    first_rtti = None
    try:
        elem = struct.unpack_from("<Q", p.try_read(arr["data"], 8) or b"\0"*8, 0)[0]
        if elem and pe is not None:
            vt = struct.unpack_from("<Q", p.try_read(elem, 8) or b"\0"*8, 0)[0]
            if vt and p.base <= vt < p.base + getattr(p, "image_size", 0x4000000):
                first_rtti = _rtti_name_from_vtable(pe, vt - p.base)
    except Exception:
        pass
    out["first_rtti"] = first_rtti
    if first_rtti and "CArmy" not in first_rtti:
        out["reason"] = "first elem not CArmy: %s" % first_rtti
        return out
    out["ok"] = True
    out["armies_count"] = arr["size"]
    # Light division-like census (no heap walk): sample up to 32 CArmy*
    div_hits = 0
    sample_n = min(arr["size"], 32)
    ca_sub = O.HYPOTHESIS_STRUCT.get("CA_SUBUNIT_DEF", 0x138)
    ca_prov = O.HYPOTHESIS_STRUCT.get("CA_PROVINCE", 0x1F0)
    ca_tmpl = O.HYPOTHESIS_STRUCT.get("CA_DIV_TEMPLATE", 0x3B8)
    for i in range(sample_n):
        elem = struct.unpack_from("<Q", p.try_read(arr["data"] + i * 8, 8) or b"\0" * 8, 0)[0]
        if not elem:
            continue
        ok_marks = 0
        for off, needle in (
            (ca_sub, "SubUnitDefinition"),
            (ca_prov, "Province"),
            (ca_tmpl, "ReferencedDivisionTemplate"),
        ):
            try:
                child = struct.unpack_from("<Q", p.try_read(elem + off, 8) or b"\0" * 8, 0)[0]
                if not child or pe is None:
                    continue
                cvt = struct.unpack_from("<Q", p.try_read(child, 8) or b"\0" * 8, 0)[0]
                if not cvt or not (p.base <= cvt < p.base + getattr(p, "image_size", 0x4000000)):
                    continue
                nm = _rtti_name_from_vtable(pe, cvt - p.base) or ""
                if needle in nm:
                    ok_marks += 1
            except Exception:
                pass
        if ok_marks >= 3:
            div_hits += 1
    out["division_like_sample"] = {"sampled": sample_n, "with_subunit_province_template": div_hits}
    if sample_n > 0 and div_hits == sample_n:
        out["divisions_count"] = arr["size"]
        out["note"] = (
            "CO_ARMIES@0x290 CArmy* — Windows CArmy is division-level "
            "(SubUnitDef@0x138 + Province@0x1f0 + RefDivTemplate@0x3b8 on all sampled); "
            "divisions_count := armies_count. Nested CUnit arrays empty."
        )
        out["divisions_note"] = out["note"]
    else:
        out["note"] = (
            "CO_ARMIES@0x290 CArmy* verified; division-like markers incomplete "
            "(%d/%d) — divisions_count left null" % (div_hits, sample_n)
        )
        out["divisions_note"] = out["note"]

    # Light: fleets + division templates (no heap walk)
    def _count_typed_array(country: int, off: int, needle: str):
        arr2 = _pdx_array(p, country + off)
        if not arr2 or not (0 < arr2["size"] <= 2000 and arr2["size"] <= arr2["capacity"] <= 4000):
            return None, None
        first_nm = None
        try:
            elem = struct.unpack_from("<Q", p.try_read(arr2["data"], 8) or b"\0" * 8, 0)[0]
            if elem and pe is not None:
                vt = struct.unpack_from("<Q", p.try_read(elem, 8) or b"\0" * 8, 0)[0]
                if vt and p.base <= vt < p.base + getattr(p, "image_size", 0x4000000):
                    first_nm = _rtti_name_from_vtable(pe, vt - p.base)
        except Exception:
            pass
        if first_nm and needle not in first_nm:
            return None, first_nm
        return arr2["size"], first_nm

    fc, fr = _count_typed_array(cptr, O.HYPOTHESIS_STRUCT.get("CO_FLEETS", 0x278), "CFleet")
    tc, tr = _count_typed_array(
        cptr, O.HYPOTHESIS_STRUCT.get("CO_DIV_TEMPLATES", 0x1B8), "ReferencedDivisionTemplate"
    )
    thc, thr = _count_typed_array(cptr, O.HYPOTHESIS_STRUCT.get("CO_THEATRES", 0x168), "CTheatre")
    stc, str_ = _count_typed_array(cptr, O.HYPOTHESIS_STRUCT.get("CO_STATES", 0x460), "CState")
    if fc is not None:
        out["fleets_count"] = fc
        out["fleets_rtti"] = fr
    if tc is not None:
        out["div_templates_count"] = tc
        out["div_templates_rtti"] = tr
    if thc is not None:
        out["theatres_count"] = thc
        out["theatres_rtti"] = thr
    if stc is not None:
        out["states_count"] = stc
        out["states_rtti"] = str_

    # Nested: primary theatre fronts (CTheatre+TH_FRONTS)
    if thc:
        th_arr = _pdx_array(p, cptr + O.HYPOTHESIS_STRUCT.get("CO_THEATRES", 0x168))
        if th_arr and th_arr.get("data") and th_arr["size"] > 0:
            try:
                th_ptr = struct.unpack_from("<Q", p.try_read(th_arr["data"], 8) or b"\0" * 8, 0)[0]
            except Exception:
                th_ptr = 0
            if th_ptr:
                frc, frr = _count_typed_array(
                    th_ptr, O.HYPOTHESIS_STRUCT.get("TH_FRONTS", 0x50), "CFront"
                )
                if frc is not None:
                    out["fronts_count"] = frc
                    out["fronts_rtti"] = frr
                    out["fronts_via"] = "CTheatre+0x50"

    # Country areas / modifiers
    cac, car = _count_typed_array(
        cptr, O.HYPOTHESIS_STRUCT.get("CO_CONTROLLER_AREAS", 0x548), "CControllerArea"
    )
    oac, oar = _count_typed_array(
        cptr, O.HYPOTHESIS_STRUCT.get("CO_OWNER_AREAS", 0x560), "COwnerArea"
    )
    moc, mor = _count_typed_array(
        cptr, O.HYPOTHESIS_STRUCT.get("CO_MODIFIERS", 0x5D0), "CModifier"
    )
    if cac is not None:
        out["controller_areas_count"] = cac
        out["controller_areas_rtti"] = car
    if oac is not None:
        out["owner_areas_count"] = oac
        out["owner_areas_rtti"] = oar
    if moc is not None:
        out["modifiers_count"] = moc
        out["modifiers_rtti"] = mor
    return out


def read_campaign_summary(p, gs_ptr: int) -> Dict[str, Any]:
    """Read-only campaign fields from a live CGameState/CCurrentGameState object.

    Only fields that pass local sanity checks are marked verified=True.
    Date: year@+0x478 plus days-after-1-January @+0x484 (1942 + 229 = 1942-08-18).
    Divisions count filled via probe_player_armies when CArmy markers match.
    """
    out: Dict[str, Any] = {"gs_ptr": hex(gs_ptr), "fields": {}, "verified": {}}
    if not gs_ptr or gs_ptr < 0x10000:
        out["error"] = "bad gs_ptr"
        return out
    blob = p.try_read(gs_ptr, 0x700)
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

    resolved = resolve_player_country(p, gs_ptr, countries)
    out["fields"]["player_resolve"] = resolved
    out["fields"]["player_tag_legacy_0x518"] = resolved.get("legacy_gs_0x518")
    out["fields"]["player_index_observed_0x520"] = resolved.get("observed_gs_0x520")
    if resolved.get("ok") and resolved.get("player_index") is not None:
        tag = resolved["player_index"]
        out["fields"]["player_tag_raw"] = tag
        out["fields"]["player_tag_letter"] = resolved.get("tag")
        out["verified"]["player_tag"] = tag
        out["verified"]["player_tag_letter"] = resolved.get("tag")
        out["verified"]["player_source"] = resolved.get("source")
    else:
        out["fields"]["player_tag_raw"] = None
        out["fields"]["player_resolve_error"] = resolved.get("reason")

    # Date: year@+0x478; days after 1 January of that year @+0x484.
    from clock import ui_date, ui_hour
    year = struct.unpack_from("<i", blob, O.HYPOTHESIS_STRUCT.get("GS_DATE_YEAR", 0x478))[0]
    aux = struct.unpack_from("<i", blob, O.HYPOTHESIS_STRUCT.get("GS_DATE_AUX", 0x47C))[0]
    day_index = struct.unpack_from("<i", blob, O.HYPOTHESIS_STRUCT.get("GS_DATE_HOURS", 0x484))[0]
    hour_like = struct.unpack_from("<i", blob, O.HYPOTHESIS_STRUCT.get("GS_DATE_HOUR_LIKE", 0x480))[0]
    hour_tick = struct.unpack_from("<I", blob, O.HYPOTHESIS_STRUCT.get("GS_DATE_HOUR_TICK", 0x468))[0]
    hour_ui = ui_hour(hour_tick)
    out["fields"]["date_year_hypothesis"] = year
    out["fields"]["date_aux_0x47c"] = aux
    out["fields"]["date_day_index"] = day_index
    out["fields"]["date_hour_like_0x480"] = hour_like
    out["fields"]["date_hour_tick_0x468"] = hour_tick
    out["fields"]["date_ui_hour"] = hour_ui
    out["fields"]["date_full"] = None
    shown = ui_date(year, day_index)
    if 1936 <= year <= 1950:
        out["verified"]["date_year"] = year
    if shown:
        out["fields"]["date_full"] = {
            "year": year,
            "ui": shown,
            "day_index": day_index,
            "ui_hour": hour_ui,
            "hour_tick": hour_tick,
            "source": "G_GAMESTATE+0x478/+0x484 date; ui_hour=(u32(+0x468)%24)+1; +0x480 not hour",
        }
        out["verified"]["date_full"] = out["fields"]["date_full"]
        if hour_ui is not None:
            out["verified"]["date_ui_hour"] = hour_ui
        out["verified"]["date_note"] = "year@+0x478; day@+0x484; ui_hour from +0x468"
    elif 1936 <= year <= 1950:
        out["verified"]["date_note"] = "year@+0x478; day index@+0x484 out of range"

    # Speed setting @+0x4BC (live 2026-11-14). Index is 0-based UI notch;
    # this is not a pause flag, so meta.speed pause|1x stays incomplete.
    speed_off = O.HYPOTHESIS_STRUCT.get("GS_GAME_SPEED_INDEX", 0x4BC)
    if len(blob) >= speed_off + 4:
        speed_index = struct.unpack_from("<i", blob, speed_off)[0]
        out["fields"]["game_speed_index"] = speed_index
        out["fields"]["game_speed_notch"] = speed_index + 1 if 0 <= speed_index <= 4 else None
        out["fields"]["game_speed_note"] = (
            "GS+0x4BC i32, 0-based UI speed setting (notch=index+1); "
            "GS+0x4B8 f32 is 0..1 progress inside the current game hour "
            "(ticks only while unpaused); pause bool address still unknown"
        )
        if 0 <= speed_index <= 4:
            out["verified"]["game_speed_index"] = speed_index
            out["verified"]["game_speed_notch"] = speed_index + 1
        prog_off = O.HYPOTHESIS_STRUCT.get("GS_HOUR_PROGRESS_F32", 0x4B8)
        if len(blob) >= prog_off + 4:
            hour_progress = struct.unpack_from("<f", blob, prog_off)[0]
            out["fields"]["game_hour_progress"] = hour_progress
            if 0.0 <= hour_progress <= 1.0:
                out["verified"]["game_hour_progress"] = hour_progress

    out["fields"]["divisions_count"] = None
    out["fields"]["divisions_note"] = (
        "filled by status when in_game via probe_player_armies — Windows CArmy@CO_ARMIES "
        "is division-level when SubUnitDef+Province+RefDivTemplate markers present; "
        "frontend: array empty."
    )
    out["fields"]["armies_count"] = None
    out["fields"]["armies_note"] = "filled by status when in_game via probe_player_armies"

    # GS-level managers (Phase 2m): CStrategicAirManager@+0x690, CCharacterManager@+0x6a8
    # Counts use size sanity only here (RTTI proven live in phase2m dump; no pe in this fn).
    air_off = O.HYPOTHESIS_STRUCT.get("GS_STRATEGIC_AIR_MANAGER", 0x690)
    char_off = O.HYPOTHESIS_STRUCT.get("GS_CHARACTER_MANAGER", 0x6A8)
    if len(blob) >= char_off + 8:
        air_mgr = struct.unpack_from("<Q", blob, air_off)[0]
        char_mgr = struct.unpack_from("<Q", blob, char_off)[0]
    else:
        mgr_blob = p.try_read(gs_ptr + 0x690, 0x30)
        air_mgr = struct.unpack_from("<Q", mgr_blob, 0)[0] if mgr_blob and len(mgr_blob) >= 8 else 0
        char_mgr = (
            struct.unpack_from("<Q", mgr_blob, 0x6A8 - 0x690)[0]
            if mgr_blob and len(mgr_blob) >= 0x20
            else 0
        )
    out["fields"]["strategic_air_manager"] = hex(air_mgr) if air_mgr else None
    out["fields"]["character_manager"] = hex(char_mgr) if char_mgr else None

    def _world_count(obj: int, off: int, lo: int, hi: int):
        if not obj or obj < 0x10000:
            return None
        arr = _pdx_array(p, obj + off)
        if not arr:
            return None
        if lo <= arr["size"] <= hi and arr["size"] <= arr["capacity"] <= max(hi * 2, hi + 4096):
            return arr["size"]
        return None

    if air_mgr and air_mgr >= 0x10000:
        ac = _world_count(air_mgr, O.HYPOTHESIS_STRUCT.get("SAM_STRATEGIC_AIRS", 0x30), 1, 2000)
        if ac is not None:
            out["verified"]["strategic_airs_count"] = ac
            out["verified"]["strategic_air_manager"] = hex(air_mgr)
        bc = _world_count(air_mgr, O.HYPOTHESIS_STRUCT.get("SAM_AIR_BASES", 0x90), 1, 5000)
        if bc is not None:
            out["verified"]["air_bases_count"] = bc
    if char_mgr and char_mgr >= 0x10000:
        cc = _world_count(char_mgr, O.HYPOTHESIS_STRUCT.get("CM_CHARACTERS", 0x10), 100, 30000)
        if cc is not None:
            out["verified"]["characters_count"] = cc
            out["verified"]["character_manager"] = hex(char_mgr)
        ca = _world_count(char_mgr, O.HYPOTHESIS_STRUCT.get("CM_CHARACTERS_ACTIVE", 0x28), 1, 30000)
        if ca is not None:
            out["verified"]["characters_active_count"] = ca
            out["fields"]["characters_active_note"] = (
                "CM+0x28 CCharacter* subset; role unproven — count only"
            )
    return out


def try_global_summary(p, rva: Optional[int]) -> Dict[str, Any]:
    base = try_global_rva(p, rva)
    if base.get("value"):
        base["campaign"] = read_campaign_summary(p, int(base["value"], 16))
    return base
