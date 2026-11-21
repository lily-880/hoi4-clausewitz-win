# patch player-country resolve into offsets.py + gamestate.py
from pathlib import Path

# --- offsets.py ---
off = Path("calling/offsets.py")
text = off.read_text(encoding="utf-8")
old = '''    "GS_TAG2INDEX": 0x340,
    "GS_PLAYER_TAG": 0x518,
    "GS_STRATEGIC_AIR_MANAGER": 0x690,  # CStrategicAirManager* (live RTTI)
'''
new = '''    "GS_TAG2INDEX": 0x340,
    # GS_PLAYER_TAG@0x518 is the old player-index hypothesis. On HOI4 1.19.4
    # Windows (live 2026-11-13, pid 36620) it read 15 (Republican Spain's
    # 17-division OOB) while the human player was Ethiopia at index 44.
    # Do not treat this field as the current player.
    "GS_PLAYER_TAG": 0x518,
    # Observed live 2026-11-13 on the same process: i32 country index at
    # GS+0x520 equaled the human player (44). Class field name not proven.
    "GS_PLAYER_INDEX_OBSERVED": 0x520,
    "GS_STRATEGIC_AIR_MANAGER": 0x690,  # CStrategicAirManager* (live RTTI)
'''
if old not in text:
    raise SystemExit("offsets.py anchor not found")
text = text.replace(old, new, 1)

old2 = '''    "CO_OWNER_AREAS": 0x560,  # CPdxArray<COwnerArea*> (live HAI=9)
    "CO_MODIFIERS": 0x5D0,  # CPdxArray<CModifier*> (live HAI=36)
'''
new2 = '''    "CO_OWNER_AREAS": 0x560,  # CPdxArray<COwnerArea*> (live HAI=9)
    "CO_MODIFIERS": 0x5D0,  # CPdxArray<CModifier*> (live HAI=36)
    # Observed live 2026-11-13: i32 at +0x538 and +0x53C were 1 only for
    # the human-controlled country (index 44) among 440 CCountry objects.
    # Class field names not RTTI-proven; treat as human-player flags only.
    "CO_HUMAN_PLAYER_FLAG_A": 0x538,
    "CO_HUMAN_PLAYER_FLAG_B": 0x53C,
'''
if old2 not in text:
    raise SystemExit("offsets.py CCountry anchor not found")
text = text.replace(old2, new2, 1)
off.write_text(text, encoding="utf-8")
print("patched offsets.py")

# --- gamestate.py ---
gs = Path("calling/gamestate.py")
gtext = gs.read_text(encoding="utf-8")

old3 = '''    # player tag at +0x518
    tag = None
    try:
        tag = p.i32(gs_ptr + 0x518)
    except OSError:
        pass
    report["checks"]["player_tag_raw"] = tag
    report["checks"]["player_tag_plausible"] = tag is not None and 0 <= tag < 2000
    report["ok"] = bool(good_size and report["checks"]["player_tag_plausible"])
'''
new3 = '''    # Cheap layout check only: 0x518 is the old player-index hypothesis and
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
'''
if old3 not in gtext:
    raise SystemExit("looks_like_gamestate anchor not found")
gtext = gtext.replace(old3, new3, 1)

resolver = '''
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
      1. The unique country whose observed flags at CCountry+0x538 and
         +0x53C are both 1 (exactly one such country in that session).
      2. GS+0x520 when it names a valid country, if (1) is unavailable.
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
        idx = hits[0]
        out["player_index"] = idx
        out["ok"] = True
        if valid_520 and cand_520 == idx:
            out["source"] = "human_flags+gs_0x520"
        else:
            out["source"] = "human_flags"
            if valid_520 and cand_520 != idx:
                out["disagreement_gs_0x520"] = cand_520
    elif valid_520:
        out["player_index"] = cand_520
        out["ok"] = True
        out["source"] = "gs_0x520"
        out["reason"] = "human flags not unique; used observed GS+0x520"
    else:
        out["reason"] = "no unique human-player flag and GS+0x520 not a valid country"
        return out

    cptr = _u64_at(p, countries["data"] + out["player_index"] * 8)
    out["country_ptr"] = hex(cptr) if cptr else None
    if not cptr:
        out["ok"] = False
        out["reason"] = "null country"
    return out


'''

anchor = 'def probe_player_armies(p, pe, gs_ptr: int) -> Dict[str, Any]:'
if anchor not in gtext:
    raise SystemExit("probe_player_armies anchor not found")
if "def resolve_player_country(" in gtext:
    raise SystemExit("resolve_player_country already present")
gtext = gtext.replace(anchor, resolver + anchor, 1)

old4 = '''    countries = _pdx_array(p, gs_ptr + O.HYPOTHESIS_STRUCT["GS_COUNTRIES"])
    tag_blob = p.try_read(gs_ptr + O.HYPOTHESIS_STRUCT["GS_PLAYER_TAG"], 4)
    if not tag_blob:
        out["reason"] = "no tag"
        return out
    tag = struct.unpack_from("<i", tag_blob, 0)[0]
    out["player_tag"] = tag
    if not countries or not (50 <= countries["size"] <= 2000):
        out["reason"] = "countries implausible"
        return out
    if not (0 <= tag < countries["size"]):
        out["reason"] = "bad tag"
        return out
    cptr = struct.unpack_from("<Q", p.try_read(countries["data"] + tag * 8, 8) or b"\\0"*8, 0)[0]
    out["country_ptr"] = hex(cptr) if cptr else None
    if not cptr:
        out["reason"] = "null country"
        return out
'''
new4 = '''    countries = _pdx_array(p, gs_ptr + O.HYPOTHESIS_STRUCT["GS_COUNTRIES"])
    resolved = resolve_player_country(p, gs_ptr, countries)
    out["player_resolve"] = resolved
    out["player_tag_legacy_0x518"] = resolved.get("legacy_gs_0x518")
    tag = resolved.get("player_index")
    out["player_tag"] = tag
    if not resolved.get("ok") or tag is None:
        out["reason"] = resolved.get("reason") or "player resolve failed"
        return out
    if not countries or not (50 <= countries["size"] <= 2000):
        out["reason"] = "countries implausible"
        return out
    cptr = struct.unpack_from("<Q", p.try_read(countries["data"] + tag * 8, 8) or b"\\0"*8, 0)[0]
    out["country_ptr"] = hex(cptr) if cptr else None
    if not cptr:
        out["reason"] = "null country"
        return out
'''
if old4 not in gtext:
    raise SystemExit("probe_player_armies tag-read anchor not found")
gtext = gtext.replace(old4, new4, 1)

old5 = '''    tag = struct.unpack_from("<i", blob, O.HYPOTHESIS_STRUCT["GS_PLAYER_TAG"])[0]
    out["fields"]["player_tag_raw"] = tag
    if 0 <= tag < 2000:
        out["verified"]["player_tag"] = tag
'''
new5 = '''    resolved = resolve_player_country(p, gs_ptr, countries)
    out["fields"]["player_resolve"] = resolved
    out["fields"]["player_tag_legacy_0x518"] = resolved.get("legacy_gs_0x518")
    out["fields"]["player_index_observed_0x520"] = resolved.get("observed_gs_0x520")
    if resolved.get("ok") and resolved.get("player_index") is not None:
        tag = resolved["player_index"]
        out["fields"]["player_tag_raw"] = tag
        out["verified"]["player_tag"] = tag
        out["verified"]["player_source"] = resolved.get("source")
    else:
        out["fields"]["player_tag_raw"] = None
        out["fields"]["player_resolve_error"] = resolved.get("reason")
'''
if old5 not in gtext:
    raise SystemExit("read_campaign_summary tag-read anchor not found")
gtext = gtext.replace(old5, new5, 1)

gs.write_text(gtext, encoding="utf-8")
print("patched gamestate.py")
print("syntax check...")
import py_compile
py_compile.compile("calling/offsets.py", doraise=True)
py_compile.compile("calling/gamestate.py", doraise=True)
print("ok")
