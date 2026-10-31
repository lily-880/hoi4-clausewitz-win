#!/usr/bin/env python3
"""Phase 2ho: widen OG+0x50 ITA membership scan oi 1..511 (RO).

2hn ALL_OUT used oi 1..127. One-shot widen + tag histogram of OG50
walkbacks (proves table still live while ITA absent). Optional PATH200@+0x60
reaffirm on focus armies. No field invent; no midflight; no Assign oi≠0 poll;
no Post; never 5x; no speed write.
"""
from __future__ import annotations

import json
import re
import struct
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import post_abi
from config import allow_post
from handle import HANDLE_TYPE_ARMY, resolve_handle
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2ho_og50_wide_ita_scan.json"
SUMMARY = ROOT / "reports" / "phase2ho_summary.json"
DOC = ROOT / "docs" / "PHASE2HO_OG50_WIDE_ITA_SCAN.md"

GS_PLAYER_TAG = 0x518
TYPE_OG = 0x35
CA_VT_RVA = 0x29D6D68
CA_MI_OFF = 0xB8
CA_MI_VT = 0x29D6FB8
CA_TAG = 0x1E0
PATH_OFF = 0x60
SHA_BASE = "253f467"
ARMY_SCAN = range(1, 2000)
OG_LO, OG_HI = 1, 512  # inclusive-exclusive end → 1..511
FOCUS = (1039, 1042, 1043, 1046, 1049)


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


def looks_like_province(v: int) -> bool:
    return 1 <= v <= 20000


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
        "scenario": "ITA OG+0x50 widen oi1..511 + tag hist (no Post, no midflight, no oi≠0)",
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


def path60(b, base, army, tag):
    blob = try_read(b, army + PATH_OFF, 24)
    if not blob or len(blob) < 24:
        return {"n": 0, "province_ids": []}
    begin, end, _cap = struct.unpack_from("<QQQ", blob, 0)
    vals = []
    if begin >= 0x10000 and end >= begin and (end - begin) // 4 <= 64:
        n = (end - begin) // 4
        raw = try_read(b, begin, n * 4)
        if raw and len(raw) >= n * 4:
            vals = [struct.unpack_from("<I", raw, i * 4)[0] for i in range(n)]
            if not (vals and all(looks_like_province(v) for v in vals)):
                vals = []
    if not vals:
        data, _c, size = struct.unpack_from("<Qii", blob, 0)
        if data >= 0x10000 and 0 < size <= 64 and not (base <= data < base + 0x4000000):
            raw = try_read(b, data, size * 4)
            if raw and len(raw) >= size * 4:
                vals = [struct.unpack_from("<I", raw, i * 4)[0] for i in range(size)]
                if not (vals and all(looks_like_province(v) for v in vals)):
                    vals = []
    if len(vals) == 1 and vals[0] == tag:
        return {"n": 0, "province_ids": [], "tag_fp": True}
    return {"n": len(vals), "province_ids": vals[:12], "tag_fp": False}


def enum_ita(b, base, tag):
    rows = []
    mi_map = {}
    for idx in ARMY_SCAN:
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
        mi = army + CA_MI_OFF
        mi_ok = bool(try_u64(b, mi) and (try_u64(b, mi) - base) == CA_MI_VT)
        p = path60(b, base, army, tag)
        bucket = "multi" if p["n"] > 1 else ("nonempty" if p["n"] == 1 else "empty")
        row = {
            "index": idx,
            "army": hex(army),
            "mi": hex(mi),
            "mi_vt_match": mi_ok,
            "bucket": bucket,
            "path_n": p["n"],
            "path_ids": p["province_ids"],
            "ois_lo": [],
            "ois_hi": [],
        }
        rows.append(row)
        if mi_ok:
            mi_map[mi] = row
    return rows, mi_map


def wide_og_scan(b, base, mi_map, player):
    """Walk OG oi OG_LO..OG_HI-1; ITA reverse + tag hist of walkback-ok members."""
    tag_hist = Counter()
    walk_ok = walk_fail = 0
    og_with_members = 0
    og_resolved = 0
    ita_lo = 0
    ita_hi = 0
    elems = 0
    ita_og_hits = []
    ita_walk_orphans = []  # tag==player but MI not in scanned handle map
    primary_set = {int(r["army"], 16) for r in mi_map.values()}

    for oi in range(OG_LO, OG_HI):
        try:
            hdr = resolve_handle(b, TYPE_OG, oi, base)
        except Exception:
            continue
        if not hdr:
            continue
        og_resolved += 1
        og = hdr + 0x10
        arr50 = read_cpdx_ptrs(b, base, og + 0x50, 24)
        if not arr50 or arr50.get("in_image_sentinel") or not arr50.get("ptrs"):
            continue
        band = "lo" if oi < 128 else "hi"
        matched_ita = []
        any_elem = False
        for p in arr50["ptrs"]:
            if not p:
                continue
            any_elem = True
            elems += 1
            if p in mi_map:
                row = mi_map[p]
                key = "ois_lo" if band == "lo" else "ois_hi"
                if oi not in row[key]:
                    row[key].append(oi)
                matched_ita.append(row["index"])
                if band == "lo":
                    ita_lo += 1
                else:
                    ita_hi += 1
            # walkback tag histogram (any nation)
            primary = p - CA_MI_OFF
            vt = try_u64(b, primary)
            if vt and (vt - base) == CA_VT_RVA:
                walk_ok += 1
                atag = try_u32(b, primary + CA_TAG)
                if atag is not None:
                    tag_hist[atag] += 1
                if atag == player and primary not in primary_set:
                    if len(ita_walk_orphans) < 8:
                        ita_walk_orphans.append({
                            "oi": oi,
                            "band": band,
                            "primary": hex(primary),
                            "mi": hex(p),
                        })
            else:
                walk_fail += 1
        if any_elem:
            og_with_members += 1
        if matched_ita:
            ita_og_hits.append({"oi": oi, "band": band, "indices": matched_ita})

    top_tags = [{"tag": t, "n": n} for t, n in tag_hist.most_common(12)]
    return {
        "og_range": [OG_LO, OG_HI - 1],
        "og_resolved": og_resolved,
        "og_with_members": og_with_members,
        "elems_scanned": elems,
        "walkback_ok": walk_ok,
        "walkback_fail": walk_fail,
        "ita_member_hits_lo": ita_lo,
        "ita_member_hits_hi": ita_hi,
        "ita_og_hits": ita_og_hits[:24],
        "tag_hist_top": top_tags,
        "player_tag_in_hist": tag_hist.get(player, 0),
        "ita_walk_orphans": ita_walk_orphans,
        "note": "Widen vs 2hn oi1..127; tag hist = walkback CArmy+0xB8→primary tag@+0x1E0",
    }


def patch_docs(meta, result, wide, rows, counts):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    repl = (
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
        f"Assign oi≠0 (2ho `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**."
    )
    for old_r in (
        "2hn `OG50_PATH_CROSSTAB_ALL_OUT`",
        "2ho `OG50_WIDE_ITA_ABSENT`",
        "2ho `OG50_WIDE_ITA_TAG_HIST_FOCUS_ABSENT`",
        "2ho `OG50_WIDE_ITA_HIT_HI`",
        "2ho `OG50_WIDE_ITA_HIT_LO`",
    ):
        needle = (
            "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0 ({old_r}); retry GitHub push when reachable. Still **NO ALLOW_POST**."
        )
        if needle in t:
            t = t.replace(needle, repl)
            break
    t = re.sub(
        r"\| `OG50MI` \| membership \| OG`\+0x50` ≡ CArmy`\+0xB8` — [^\n]*\|\n",
        f"| `OG50MI` | membership | OG`+0x50` ≡ CArmy`+0xB8` — 2ho wide oi1..511 "
        f"ita_lo={wide['ita_member_hits_lo']} ita_hi={wide['ita_member_hits_hi']} "
        f"walk={wide['walkback_ok']}/{wide['walkback_ok']+wide['walkback_fail']} |\n",
        t,
        count=1,
    )
    row = (
        f"| **2ho** | `{result}` | OG+0x50 widen oi1..511 ITA + tag hist | "
        f"field name / oi≠0 / midflight / Post HARD_DENY |\n"
    )
    if "| **2ho** |" in t:
        t = re.sub(r"\| \*\*2ho\*\* \|[^\n]*\n", row, t, count=1)
    elif "| **2hn** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2hn** |"):
                out.append(row)
        t = "".join(out)
    note = (
        f"**2ho OG50 wide ITA scan:** result=`{result}` · ita={counts.get('ita')} · "
        f"ita_lo={wide['ita_member_hits_lo']} ita_hi={wide['ita_member_hits_hi']} · "
        f"walk={wide['walkback_ok']}/{wide['walkback_ok']+wide['walkback_fail']} · "
        f"og_members={wide['og_with_members']} · player_tag_in_hist={wide['player_tag_in_hist']} · "
        f"hours={meta.get('hours')} UI={meta.get('ui_date')} · allow_post=False.\n"
    )
    if "**2ho OG50 wide ITA scan:**" in t:
        t = re.sub(r"\*\*2ho OG50 wide ITA scan:\*\*[^\n]*\n", note, t, count=1)
    elif "**2hn OG×PATH crosstab:**" in t:
        idx = t.find("**2hn OG×PATH crosstab:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2hn · OG+0x50 × PATH200 crosstab · 2026-10-31 Asia/Shanghai*",
        "*Phase 2ho · OG+0x50 widen oi1..511 · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2hn — checklist polish (CLOSED)",
        "## Phase 2gj … 2ho — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2ho | OG+0x50 widen oi1..511 ITA + tag hist | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2ho |" in t2:
        t2 = re.sub(r"\| 2ho \|[^\n]*\n", row2, t2, count=1)
    elif "| 2hn |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2hn |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2hn — OG×PATH crosstab. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2ho — OG50 wide ITA scan. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")


def main():
    assert allow_post() is False
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2ho",
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

    rows, mi_map = enum_ita(b, base, tag)
    wide = wide_og_scan(b, base, mi_map, tag)

    counts = {
        "ita": len(rows),
        "multi": sum(1 for r in rows if r["bucket"] == "multi"),
        "nonempty": sum(1 for r in rows if r["bucket"] == "nonempty"),
        "empty": sum(1 for r in rows if r["bucket"] == "empty"),
        "in_og_any": sum(1 for r in rows if r["ois_lo"] or r["ois_hi"]),
    }
    focus_path = [
        {
            "index": r["index"],
            "bucket": r["bucket"],
            "path_ids": r["path_ids"],
            "ois_lo": r["ois_lo"],
            "ois_hi": r["ois_hi"],
        }
        for r in rows
        if r["index"] in FOCUS or r["bucket"] != "empty"
    ]

    if wide["ita_member_hits_hi"] > 0:
        result = "OG50_WIDE_ITA_HIT_HI"
    elif wide["ita_member_hits_lo"] > 0:
        result = "OG50_WIDE_ITA_HIT_LO"
    elif wide["player_tag_in_hist"] > 0 and counts["in_og_any"] == 0:
        # ITA tag present in OG50 walkbacks, but scanned handle MIs not among elems
        result = "OG50_WIDE_ITA_TAG_HIST_FOCUS_ABSENT"
    elif wide["walkback_ok"] > 0 and counts["ita"] > 0:
        result = "OG50_WIDE_ITA_ABSENT"
    elif wide["walkback_ok"] > 0:
        result = "OG50_WIDE_NO_ITA_ARMIES"
    else:
        result = "OG50_WIDE_HONEST_EMPTY"

    report = {
        "phase": "2ho",
        "result": result,
        "allow_post": False,
        "live": meta,
        "counts": counts,
        "wide": wide,
        "armies": [
            {
                "index": r["index"],
                "bucket": r["bucket"],
                "path_n": r["path_n"],
                "path_ids": r["path_ids"],
                "ois_lo": r["ois_lo"],
                "ois_hi": r["ois_hi"],
                "mi_vt_match": r["mi_vt_match"],
            }
            for r in rows
        ],
        "focus_path": focus_path,
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
            "Widen OG+0x50 oi1..511 for ITA; tag hist proves non-ITA occupancy; "
            "field name STUBBED; no Post"
        ),
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    summary = {
        "phase": "2ho",
        "result": result,
        "allow_post": False,
        "live": meta,
        "counts": counts,
        "ita_lo": wide["ita_member_hits_lo"],
        "ita_hi": wide["ita_member_hits_hi"],
        "walkback": f"{wide['walkback_ok']}/{wide['walkback_ok']+wide['walkback_fail']}",
        "og_with_members": wide["og_with_members"],
        "player_tag_in_hist": wide["player_tag_in_hist"],
        "tag_hist_top": wide["tag_hist_top"][:8],
        "focus_path": focus_path,
        "ita_og_hits": wide["ita_og_hits"],
        "ita_walk_orphans": wide.get("ita_walk_orphans"),
        "next_shortest_blocker": (
            "NON-Post: human midflight CMove hex / SAFE Post for ring_embed OR later "
            "plan-dense Assign oi≠0 (2ho OG50 wide); push when GitHub reachable; "
            "still NO ALLOW_POST"
        ),
        "sha_base": SHA_BASE,
        "semantics": "OG50 widen oi1..511; ITA absent or hi-band hit; no field invent; no Post",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    DOC.write_text(
        "\n".join(
            [
                "# Phase 2ho — OG+0x50 widen oi1..511 ITA scan",
                "",
                f"**Result:** `{result}`",
                "",
                f"**ITA hits:** lo(1..127)={wide['ita_member_hits_lo']} · "
                f"hi(128..511)={wide['ita_member_hits_hi']}",
                "",
                f"**Walkback:** {wide['walkback_ok']}/{wide['walkback_ok']+wide['walkback_fail']} · "
                f"og_with_members={wide['og_with_members']} · "
                f"player_tag_in_hist={wide['player_tag_in_hist']}",
                "",
                f"**Tag hist top:** {wide['tag_hist_top'][:8]}",
                "",
                f"**Focus/path:** {focus_path}",
                "",
                f"**Live:** pid {meta['pid']} · hours={meta['hours']} UI={meta['ui_date']} · "
                f"drain={meta['drain']} · allow_post=False · speed untouched",
                "",
                "**Semantics:** Widen vs 2hn oi1..127. Membership proxy only. "
                "Field name still STUBBED. No invent. No Post / midflight / oi≠0 poll.",
                "",
                "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for "
                "ring_embed OR later Assign oi≠0; retry GitHub push when reachable. "
                "Still **NO ALLOW_POST**.",
                "",
                f"*Phase 2ho · 2026-10-31 Asia/Shanghai · sha_base {SHA_BASE}*",
                "",
            ]
        ),
        encoding="utf-8",
    )

    patch_docs(meta, result, wide, rows, counts)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
