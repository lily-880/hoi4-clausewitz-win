#!/usr/bin/env python3
"""Phase 2hl: OG50NAME demangle attempt (RO).

Quick PE/RTTI attempt to name OG+0x50 / CArmy+0xB8 MI field/class.
Honest empty OK. Fold 2hk walkback + 2hj matrix stay catalogued.
NO midflight / no oi≠0 poll / no Post / never 5x / no speed write.
"""
from __future__ import annotations

import json
import re
import struct
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import post_abi
from config import allow_post
from gamestate import _rtti_name_from_vtable
from handle import resolve_handle
from msvc_rtti import demangle_simple, scan_type_names
from pe import PE
from process import Backend, find_pid
from stringscan import find_ascii_all

OUT = ROOT / "reports" / "phase2hl_og50name_demangle.json"
SUMMARY = ROOT / "reports" / "phase2hl_summary.json"
DOC = ROOT / "docs" / "PHASE2HL_OG50NAME_DEMANGLE.md"

GS_PLAYER_TAG = 0x518
TYPE_CA = 0x33  # CArmy handle type (fallback scan via tag)
CA_VT_RVA = 0x29D6D68
CA_MI_OFF = 0xB8
CA_TAG = 0x1E0
CA_MI_VT = 0x29D6FB8
MI_VT_CANDS = [0x29D6FB8, 0x29D6F48, 0x29D7000]
SHA_BASE = "7e5ec1e"

# Field-name-ish needles (strict); class-ish needles (loose RTTI substr)
FIELD_NEEDLES = [
    b"m_armies",
    b"m_units",
    b"m_members",
    b"army_members",
    b"order_group_armies",
    b"COrderGroup",
    b"OrderGroupArmies",
    b"MemberInfo",
    b"ArmyMember",
    b"CArmyMember",
]
RTTI_SUBSTRS = [
    "ArmyMember",
    "MemberInfo",
    "OrderGroup",
    "CArmyMI",
    "ArmyInfo",
    "UnitMember",
]


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def i32(b, a):
    return struct.unpack("<i", b.read(a, 4))[0]


def try_u64(b, a):
    try:
        return u64(b, a)
    except Exception:
        return None


def try_u32(b, a):
    try:
        return u32(b, a)
    except Exception:
        return None


def player_tag(b, base):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    return i32(b, gs + GS_PLAYER_TAG)


def live_meta(b, base, pid, tag):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    hours = i32(b, gs + 0x484)
    year = i32(b, gs + 0x478)
    d = datetime(1936, 1, 1, 0, 0) + timedelta(hours=int(hours))
    pending = stage = drain = exec_c = None
    try:
        sess = u64(b, base + post_abi.G_SESSION)
        server = u64(b, sess + post_abi.CSession_SERVER)
        pending = u32(b, server + post_abi.CDummyServer_PENDING + 0x10)
        stage = u32(b, sess + post_abi.CSession_STAGE_COUNT)
        drain = u32(b, sess + post_abi.CSession_DRAIN_COUNTER)
        exec_c = u32(b, sess + post_abi.CSession_EXEC_COUNTER)
    except Exception:
        pass
    return {
        "pid": pid,
        "hours": hours,
        "year_at_0x478": year,
        "ui_date": d.strftime("%Y-%m-%d %H:00"),
        "speed_policy": "pause-or-1x only (never write speed)",
        "country_tag_filter": tag,
        "scenario": "ITA OG50NAME demangle attempt (no Post, no midflight, no oi≠0)",
        "pending": pending,
        "stage_count": stage,
        "drain": drain,
        "exec": exec_c,
        "allow_post": False,
    }


def live_mi_check(b, base, tag):
    """Confirm ITA CArmy+0xB8 carries MI VT 0x29d6fb8.

    resolve_handle(ARMY=51) returns CArmy base: VT@+0x00=0x29d6d68,
    secondary@+0x10=0x29d6f48, MI VT@+0xB8=0x29d6fb8, tag@+0x1E0.
    """
    from handle import HANDLE_TYPE_ARMY

    hits = []
    indices = [1039, 1042, 1043, 1046, 1048, 1049] + list(range(1000, 1060))
    seen = set()
    for idx in indices:
        if idx in seen:
            continue
        seen.add(idx)
        try:
            army = resolve_handle(b, HANDLE_TYPE_ARMY, idx, base)
        except Exception:
            continue
        if not army:
            continue
        vt = try_u64(b, army)
        if not vt or (vt - base) != CA_VT_RVA:
            continue
        atag = try_u32(b, army + CA_TAG)
        if atag != tag:
            continue
        mi_vt = try_u64(b, army + CA_MI_OFF)
        mi_rva = (mi_vt - base) if mi_vt else None
        sec = try_u64(b, army + 0x10)
        hits.append(
            {
                "index": idx,
                "army": hex(army),
                "tag": atag,
                "primary_vt_rva": hex(vt - base),
                "sec_vt_rva": hex(sec - base) if sec else None,
                "mi_vt_rva": hex(mi_rva) if mi_rva is not None else None,
                "mi_vt_match": mi_rva == CA_MI_VT,
            }
        )
        if len(hits) >= 4:
            break
    return hits
    return hits


def pe_demangle_attempt(image_path: str) -> dict:
    out = {
        "image_path": image_path,
        "mi_vt_rtti": [],
        "rtti_substr_hits": [],
        "field_needle_hits": [],
        "error": None,
    }
    if not image_path or not Path(image_path).is_file():
        out["error"] = "no_image_path"
        return out
    try:
        pe = PE(image_path)
    except Exception as e:
        out["error"] = f"pe_open:{e}"
        return out

    for vt_rva in MI_VT_CANDS:
        raw = _rtti_name_from_vtable(pe, vt_rva)
        plain = demangle_simple(raw) if raw else None
        out["mi_vt_rtti"].append(
            {
                "vt_rva": hex(vt_rva),
                "raw": raw,
                "demangled": plain,
                "is_primary_mi": vt_rva == CA_MI_VT,
            }
        )

    for sub in RTTI_SUBSTRS:
        try:
            hits = scan_type_names(pe, sub, limit=12)
        except Exception as e:
            out["rtti_substr_hits"].append({"substr": sub, "error": str(e)})
            continue
        out["rtti_substr_hits"].append(
            {
                "substr": sub,
                "count": len(hits),
                "samples": [
                    {"raw": h["name"], "demangled": demangle_simple(h["name"])}
                    for h in hits[:4]
                ],
            }
        )

    for needle in FIELD_NEEDLES:
        try:
            rvas = find_ascii_all(pe, needle)
            out["field_needle_hits"].append(
                {
                    "needle": needle.decode("ascii", "replace"),
                    "hit_count": len(rvas),
                    "rvas_sample": [hex(r) for r in rvas[:4]],
                }
            )
        except Exception as e:
            out["field_needle_hits"].append(
                {"needle": needle.decode("ascii", "replace"), "error": str(e)}
            )
    return out


def classify(pe_att: dict, live_mi: list) -> str:
    primary = next(
        (x for x in (pe_att.get("mi_vt_rtti") or []) if x.get("is_primary_mi")), None
    )
    dem = (primary or {}).get("demangled") or ""
    class_hit = bool(dem)
    # MI VT 0x29d6fb8 demangling to CArmy = secondary base VT inside CArmy,
    # NOT proof of the OG+0x50 *field* name. Generic PE needles (m_armies etc.)
    # without offset xref are NOT field-name evidence — invent forbidden.
    live_ok = any(h.get("mi_vt_match") for h in live_mi)
    if class_hit and live_ok:
        # Field name remains STUBBED; record class demangle separately.
        return "OG50NAME_CLASS_HIT_FIELD_STUBBED"
    if class_hit:
        return "OG50NAME_CLASS_HIT_LIVE_MISS"
    return "OG50NAME_HONEST_EMPTY"


def patch_docs(meta, result, pe_att, walk_note):
    primary = next(
        (x for x in (pe_att.get("mi_vt_rtti") or []) if x.get("is_primary_mi")), {}
    )
    dem = primary.get("demangled") or "NONE"
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    t = t.replace(
        "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2hk `OG50_MEMBERSHIP_POLISH_HIT`); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2hl `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
    )
    t = re.sub(
        r"\| `OG50NAME` \| [^\n]*\|\n",
        f"| `OG50NAME` | demangled OG`+0x50` / MI field name | {result} "
        f"MI_class={dem} (2hl; field name still STUBBED unless HIT) |\n",
        t,
        count=1,
    )
    # also refresh §6e-style stubbed row if present
    t = re.sub(
        r"\| `OG50NAME` \| Demangled OG\+0x50 / MI field name \| STUBBED \|\n",
        f"| `OG50NAME` | Demangled OG+0x50 / MI field name | {result} MI_class={dem} |\n",
        t,
        count=1,
    )
    row = (
        f"| **2hl** | `{result}` | OG50NAME demangle attempt (MI VT RTTI + PE needles) | "
        f"field name / oi≠0 / midflight / Post HARD_DENY |\n"
    )
    if "| **2hl** |" not in t and "| **2hk** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2hk** |"):
                out.append(row)
        t = "".join(out)
    note = (
        f"**2hl OG50NAME demangle:** result=`{result}` · MI_class={dem} · "
        f"raw={primary.get('raw')} · {walk_note} · hours={meta.get('hours')} "
        f"UI={meta.get('ui_date')} · allow_post=False.\n"
    )
    if "**2hl OG50NAME demangle:**" not in t and "**2hk OG50 membership polish:**" in t:
        idx = t.find("**2hk OG50 membership polish:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2hk · OG50 membership polish + 2hj matrix fold · 2026-10-31 Asia/Shanghai*",
        "*Phase 2hl · OG50NAME demangle attempt · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2hk — checklist polish (CLOSED)",
        "## Phase 2gj … 2hl — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2hl | OG50NAME demangle attempt (MI VT RTTI + PE needles) | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2hl |" not in t2 and "| 2hk |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2hk |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2hk — OG50 membership polish. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2hl — OG50NAME demangle attempt. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")


def main():
    assert allow_post() is False
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2hl",
            "result": "NO_LIVE_PROCESS",
            "allow_post": False,
            "next_shortest_blocker": "NON-Post: restore live; still NO ALLOW_POST",
        }
        SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 1

    b = Backend()
    base = b.image_base
    tag = player_tag(b, base)
    meta = live_meta(b, base, pid, tag)
    image_path = getattr(b, "image_path", "") or ""
    pe_att = pe_demangle_attempt(image_path)
    live_mi = live_mi_check(b, base, tag)
    result = classify(pe_att, live_mi)

    primary = next(
        (x for x in (pe_att.get("mi_vt_rtti") or []) if x.get("is_primary_mi")), {}
    )
    walk_note = f"live_mi_match={any(h.get('mi_vt_match') for h in live_mi)}"

    report = {
        "phase": "2hl",
        "result": result,
        "allow_post": False,
        "live": meta,
        "pe_demangle": pe_att,
        "live_mi": live_mi,
        "primary_mi_class": primary.get("demangled"),
        "primary_mi_raw": primary.get("raw"),
        "sha_base": SHA_BASE,
        "hard_deny": [
            "ALLOW_POST",
            "CLAUSEWITZ_ALLOW_POST",
            "Post inject",
            "2fb/2gk recipe execute",
            "tool-gate",
            "5x",
            "speed write",
            "ask right-click",
            "long midflight empty poll",
            "Assign oi≠0 long poll",
            "invent field name without PE/RTTI evidence",
        ],
        "semantics": (
            "OG50NAME demangle attempt: MI VT RTTI class vs OG+0x50 field name; "
            "class≠field; invent forbidden; no Post"
        ),
        "catalog_fold": {
            "2hk_walkback": "387/387 ita=21",
            "2hj_matrix": "multi=1042 nonempty=1048 empty=1039/1043/1046/1049 @+0x60",
        },
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    field_hits = [
        n["needle"]
        for n in (pe_att.get("field_needle_hits") or [])
        if n.get("hit_count", 0) > 0
    ]
    summary = {
        "phase": "2hl",
        "result": result,
        "allow_post": False,
        "live": meta,
        "mi_class": primary.get("demangled"),
        "mi_raw": primary.get("raw"),
        "live_mi_n": len(live_mi),
        "live_mi_match": any(h.get("mi_vt_match") for h in live_mi),
        "field_needle_hits": field_hits,
        "pe_error": pe_att.get("error"),
        "next_shortest_blocker": (
            "NON-Post: human midflight CMove hex / SAFE Post for ring_embed OR later "
            "plan-dense Assign oi≠0 (2hl OG50NAME); push when GitHub reachable; "
            "still NO ALLOW_POST"
        ),
        "sha_base": SHA_BASE,
        "semantics": "OG50NAME demangle attempt; class≠field; no invent; no Post",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    DOC.write_text(
        "\n".join(
            [
                "# Phase 2hl — OG50NAME demangle attempt",
                "",
                f"**Result:** `{result}`",
                "",
                f"**MI VT `0x29d6fb8` RTTI:** raw={primary.get('raw')} · "
                f"demangled={primary.get('demangled')}",
                "",
                f"**Live MI check:** {live_mi}",
                "",
                f"**Field needles with hits:** {field_hits or 'NONE'}",
                "",
                f"**PE error:** {pe_att.get('error')}",
                "",
                f"**Live:** pid {meta['pid']} · hours={meta['hours']} UI={meta['ui_date']} · "
                f"drain={meta['drain']} · allow_post=False · speed untouched",
                "",
                "**Semantics:** Class demangle of MI VT ≠ demangled OG+0x50 *field* name. "
                "Inventing a field name without PE/RTTI evidence is HARD_DENY. No Post.",
                "",
                "**Catalog fold:** 2hk walkback 387/387 ita=21; 2hj matrix "
                "1042/1048 @+0x60.",
                "",
                "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for "
                "ring_embed OR later Assign oi≠0; retry GitHub push when reachable. "
                "Still **NO ALLOW_POST**.",
                "",
                f"*Phase 2hl · 2026-10-31 Asia/Shanghai · sha_base {SHA_BASE}*",
                "",
            ]
        ),
        encoding="utf-8",
    )

    patch_docs(meta, result, pe_att, walk_note)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
