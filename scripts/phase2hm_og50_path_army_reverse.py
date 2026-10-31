#!/usr/bin/env python3
"""Phase 2hm: OG+0x50 ↔ ITA path-army reverse membership (RO).

One-shot: which OrderGroup oi contain MI of path-bearing ITA armies
(1042 multi / 1048 nonempty) vs empty cohort. No field-name invent.
NO midflight / no oi≠0 Assign poll / no Post / never 5x / no speed write.
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
from handle import HANDLE_TYPE_ARMY, resolve_handle
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2hm_og50_path_army_reverse.json"
SUMMARY = ROOT / "reports" / "phase2hm_summary.json"
DOC = ROOT / "docs" / "PHASE2HM_OG50_PATH_ARMY_REVERSE.md"

GS_PLAYER_TAG = 0x518
TYPE_OG = 0x35
CA_VT_RVA = 0x29D6D68
CA_MI_OFF = 0xB8
CA_MI_VT = 0x29D6FB8
CA_TAG = 0x1E0
SHA_BASE = "f336de0"

# From 2hj matrix (catalog); live-resolved again this slice
PATH_MULTI = [1042]
PATH_NONEMPTY = [1048]
PATH_EMPTY = [1039, 1043, 1046, 1049]
FOCUS = PATH_MULTI + PATH_NONEMPTY + PATH_EMPTY


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


def try_read(b, a, n):
    try:
        return b.read(a, n)
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
        "scenario": "ITA OG+0x50↔path-army reverse membership (no Post, no midflight, no oi≠0)",
        "pending": pending,
        "stage_count": stage,
        "drain": drain,
        "exec": exec_c,
        "allow_post": False,
    }


def read_cpdx_ptrs(b, base, arr_addr, max_n=32):
    try:
        data = u64(b, arr_addr)
        size = i32(b, arr_addr + 0xC)
    except Exception:
        return None
    if not data or size <= 0 or size > 4096:
        return None
    if base <= data < base + 0x4000000:
        return {"size": size, "in_image_sentinel": True, "ptrs": []}
    blob = try_read(b, data, min(size, max_n) * 8)
    if not blob:
        return {"size": size, "in_image_sentinel": False, "ptrs": []}
    ptrs = [struct.unpack_from("<Q", blob, j * 8)[0] for j in range(min(size, max_n))]
    return {"size": size, "in_image_sentinel": False, "ptrs": ptrs}


def resolve_armies(b, base, tag, indices):
    rows = []
    mi_to_army = {}
    for idx in indices:
        try:
            army = resolve_handle(b, HANDLE_TYPE_ARMY, idx, base)
        except Exception:
            army = None
        if not army:
            rows.append({"index": idx, "status": "unresolved"})
            continue
        vt = try_u64(b, army)
        if not vt or (vt - base) != CA_VT_RVA:
            rows.append({"index": idx, "status": "vt_miss", "army": hex(army)})
            continue
        atag = try_u32(b, army + CA_TAG)
        if atag != tag:
            rows.append({"index": idx, "status": "tag_miss", "tag": atag, "army": hex(army)})
            continue
        mi = army + CA_MI_OFF
        mi_vt = try_u64(b, mi)
        mi_ok = bool(mi_vt and (mi_vt - base) == CA_MI_VT)
        bucket = (
            "multi" if idx in PATH_MULTI else "nonempty" if idx in PATH_NONEMPTY else "empty"
        )
        row = {
            "index": idx,
            "status": "ok",
            "bucket": bucket,
            "army": hex(army),
            "mi": hex(mi),
            "mi_vt_match": mi_ok,
            "tag": atag,
        }
        rows.append(row)
        if mi_ok:
            mi_to_army[mi] = row
            # also accept primary-eq (rare)
            mi_to_army[army] = {**row, "via": "primary"}
    return rows, mi_to_army


def reverse_og50(b, base, mi_to_army, focus_indices):
    """OG oi → focus army hits via MI@+0xB8 (proxy; no field name)."""
    by_army = {i: [] for i in focus_indices}
    og_hits = []
    elems_scanned = 0
    for oi in range(1, 128):
        try:
            hdr = resolve_handle(b, TYPE_OG, oi, base)
        except Exception:
            continue
        if not hdr:
            continue
        og = hdr + 0x10
        arr50 = read_cpdx_ptrs(b, base, og + 0x50, 24)
        if not arr50 or arr50.get("in_image_sentinel") or not arr50.get("ptrs"):
            continue
        matched = []
        for p in arr50["ptrs"]:
            if not p:
                continue
            elems_scanned += 1
            # canonical: OG+0x50 elem == CArmy+0xB8
            if p in mi_to_army:
                row = mi_to_army[p]
                idx = row["index"]
                if idx in by_army:
                    rec = {"oi": oi, "via": row.get("via", "mi_plus_b8"), "elem": hex(p)}
                    by_army[idx].append(rec)
                    matched.append({"index": idx, "bucket": row.get("bucket"), **rec})
            else:
                # walkback primary = p - 0xB8
                primary = p - CA_MI_OFF
                for maddr, row in list(mi_to_army.items()):
                    if row.get("army") and int(row["army"], 16) == primary:
                        idx = row["index"]
                        if idx in by_army:
                            rec = {"oi": oi, "via": "walkback_primary", "elem": hex(p)}
                            by_army[idx].append(rec)
                            matched.append(
                                {"index": idx, "bucket": row.get("bucket"), **rec}
                            )
                        break
        if matched:
            og_hits.append({"oi": oi, "matches": matched})
    # dedupe oi lists
    for idx in by_army:
        seen = set()
        uniq = []
        for r in by_army[idx]:
            k = r["oi"]
            if k in seen:
                continue
            seen.add(k)
            uniq.append(r)
        by_army[idx] = uniq
    return {
        "by_army": {str(k): v for k, v in by_army.items()},
        "og_hits": og_hits[:40],
        "og_hit_n": len(og_hits),
        "elems_scanned": elems_scanned,
        "note": "Membership proxy OG+0x50[i]==CArmy+0xB8; field name STUBBED (2hl)",
    }


def patch_docs(meta, result, rev, armies):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    # Prefer FIELD_STUBBED (2hl summary) then LIVE_MISS (docs lag)
    for old_r in (
        "OG50NAME_CLASS_HIT_FIELD_STUBBED",
        "OG50NAME_CLASS_HIT_LIVE_MISS",
    ):
        needle = (
            "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0 (2hl `{old_r}`); retry GitHub push when reachable. Still **NO ALLOW_POST**."
        )
        repl = (
            f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0 (2hm `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**."
        )
        if needle in t:
            t = t.replace(needle, repl)
            break
    # brief reverse summary for path armies
    def ois_for(idx):
        return [r["oi"] for r in (rev.get("by_army") or {}).get(str(idx), [])]

    multi_ois = ois_for(1042)
    ne_ois = ois_for(1048)
    t = re.sub(
        r"\| `OG50MI` \| membership \| OG`\+0x50` ≡ CArmy`\+0xB8` — [^\n]*\|\n",
        f"| `OG50MI` | membership | OG`+0x50` ≡ CArmy`+0xB8` — 2hm reverse "
        f"1042→ois{multi_ois} 1048→ois{ne_ois} (field name STUBBED) |\n",
        t,
        count=1,
    )
    row = (
        f"| **2hm** | `{result}` | OG+0x50↔path-army reverse (1042/1048 vs empty) | "
        f"field name / oi≠0 / midflight / Post HARD_DENY |\n"
    )
    t = t.replace(
        "| `OG50NAME` | demangled OG`+0x50` / MI field name | OG50NAME_CLASS_HIT_LIVE_MISS MI_class=CArmy (2hl; field name still STUBBED unless HIT) |",
        "| `OG50NAME` | demangled OG`+0x50` / MI field name | OG50NAME_CLASS_HIT_FIELD_STUBBED MI_class=CArmy (2hl; 2hm reverse maps path armies; field STUBBED) |",
    )
    t = t.replace(
        "| `OG50NAME` | demangled OG`+0x50` / MI field name | OG50NAME_CLASS_HIT_FIELD_STUBBED MI_class=CArmy (2hl; field name still STUBBED unless HIT) |",
        "| `OG50NAME` | demangled OG`+0x50` / MI field name | OG50NAME_CLASS_HIT_FIELD_STUBBED MI_class=CArmy (2hl; 2hm reverse maps path armies; field STUBBED) |",
    )
    if "| **2hm** |" not in t and "| **2hl** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2hl** |"):
                out.append(row)
        t = "".join(out)
    note = (
        f"**2hm OG↔path-army reverse:** result=`{result}` · "
        f"1042→{multi_ois} · 1048→{ne_ois} · og_hits={rev.get('og_hit_n')} · "
        f"hours={meta.get('hours')} UI={meta.get('ui_date')} · allow_post=False.\n"
    )
    if "**2hm OG↔path-army reverse:**" not in t and "**2hl OG50NAME demangle:**" in t:
        idx = t.find("**2hl OG50NAME demangle:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2hl · OG50NAME demangle attempt · 2026-10-31 Asia/Shanghai*",
        "*Phase 2hm · OG↔path-army reverse membership · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2hl — checklist polish (CLOSED)",
        "## Phase 2gj … 2hm — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2hm | OG+0x50↔path-army reverse membership (1042/1048) | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2hm |" not in t2 and "| 2hl |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2hl |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2hl — OG50NAME demangle attempt. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2hm — OG↔path-army reverse. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")


def main():
    assert allow_post() is False
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2hm",
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

    armies, mi_map = resolve_armies(b, base, tag, FOCUS)
    # keep only mi@+0xB8 keys for reverse (drop primary-eq duplicates for scan clarity)
    mi_only = {
        int(r["mi"], 16): r
        for r in armies
        if r.get("status") == "ok" and r.get("mi_vt_match") and r.get("mi")
    }
    rev = reverse_og50(b, base, mi_only, FOCUS)

    path_linked = 0
    for idx in PATH_MULTI + PATH_NONEMPTY:
        if rev["by_army"].get(str(idx)):
            path_linked += 1
    empty_linked = sum(1 for idx in PATH_EMPTY if rev["by_army"].get(str(idx)))
    ok_armies = sum(1 for r in armies if r.get("status") == "ok")

    if path_linked > 0 and rev.get("og_hit_n", 0) > 0:
        result = "OG50_PATH_ARMY_REVERSE_HIT"
    elif ok_armies > 0 and rev.get("og_hit_n", 0) > 0:
        result = "OG50_REVERSE_EMPTY_COHORT_ONLY"
    elif ok_armies > 0:
        result = "OG50_REVERSE_HONEST_EMPTY"
    else:
        result = "OG50_REVERSE_ARMY_UNRESOLVED"

    report = {
        "phase": "2hm",
        "result": result,
        "allow_post": False,
        "live": meta,
        "armies": armies,
        "reverse": rev,
        "path_linked": path_linked,
        "empty_linked": empty_linked,
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
            "invent OG+0x50 field name",
        ],
        "semantics": (
            "Reverse OG+0x50 membership proxy for path vs empty ITA armies; "
            "field name still STUBBED (2hl); no Post"
        ),
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    def ois(idx):
        return [r["oi"] for r in rev["by_army"].get(str(idx), [])]

    summary = {
        "phase": "2hm",
        "result": result,
        "allow_post": False,
        "live": meta,
        "path_linked": path_linked,
        "empty_linked": empty_linked,
        "army_1042_ois": ois(1042),
        "army_1048_ois": ois(1048),
        "empty_ois": {str(i): ois(i) for i in PATH_EMPTY},
        "og_hit_n": rev.get("og_hit_n"),
        "elems_scanned": rev.get("elems_scanned"),
        "next_shortest_blocker": (
            "NON-Post: human midflight CMove hex / SAFE Post for ring_embed OR later "
            "plan-dense Assign oi≠0 (2hm OG↔path reverse); push when GitHub reachable; "
            "still NO ALLOW_POST"
        ),
        "sha_base": SHA_BASE,
        "semantics": "OG↔path-army reverse membership proxy; no field invent; no Post",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    DOC.write_text(
        "\n".join(
            [
                "# Phase 2hm — OG+0x50 ↔ path-army reverse membership",
                "",
                f"**Result:** `{result}`",
                "",
                f"**Path armies:** 1042(multi)→ois{ois(1042)} · 1048(nonempty)→ois{ois(1048)}",
                "",
                f"**Empty cohort ois:** { {i: ois(i) for i in PATH_EMPTY} }",
                "",
                f"**OG hits:** {rev.get('og_hit_n')} · elems_scanned={rev.get('elems_scanned')}",
                "",
                f"**Live:** pid {meta['pid']} · hours={meta['hours']} UI={meta['ui_date']} · "
                f"drain={meta['drain']} · allow_post=False · speed untouched",
                "",
                "**Semantics:** Membership proxy only (OG+0x50[i]==CArmy+0xB8). "
                "OG50NAME field still STUBBED. No invent. No Post / midflight / oi≠0 poll.",
                "",
                "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for "
                "ring_embed OR later Assign oi≠0; retry GitHub push when reachable. "
                "Still **NO ALLOW_POST**.",
                "",
                f"*Phase 2hm · 2026-10-31 Asia/Shanghai · sha_base {SHA_BASE}*",
                "",
            ]
        ),
        encoding="utf-8",
    )

    patch_docs(meta, result, rev, armies)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
