#!/usr/bin/env python3
"""Phase 2ib: PATH200 denser multi-army → OG+0x50 reverse (RO).

Denser than 2hy (focus-prov only) and 2hz (4 targets): scan ITA CArmy
PATH200@+0x60 army1..3000; reverse-map ALL nonempty-path armies into
oi1..1200 OG+0x50 membership. Tag known 481/575/962/976; surface new
mid-band OGs. No Instant (no OG575/hiband Instant-empty / Instant map /
463 Inst70). No Assign / midflight / Post; never 5x; no speed write;
OG+0x50 name STUBBED.
"""
from __future__ import annotations

import json
import re
import struct
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import post_abi
from config import allow_post
from handle import HANDLE_TYPE_ARMY, resolve_handle
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2ib_path200_all_reverse_og50.json"
SUMMARY = ROOT / "reports" / "phase2ib_summary.json"
DOC = ROOT / "docs" / "PHASE2IB_PATH200_ALL_REVERSE_OG50.md"

GS_PLAYER_TAG = 0x518
TYPE_OG = 0x35
CA_VT_RVA = 0x29D6D68
CA_MI_OFF = 0xB8
CA_MI_VT = 0x29D6FB8
CA_TAG = 0x1E0
PATH_OFF = 0x60
KNOWN = {
    481: "focus",
    575: "midband",
    962: "hiband",
    976: "hiband",
}
FOCUS_PROVS = (1176, 3938, 3816, 915)
ARMY_LO, ARMY_HI = 1, 3000
OI_LO, OI_HI = 1, 1200
SHA_BASE = "11f81e3"


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
        "scenario": (
            "ITA PATH200 denser all-nonempty → OG+0x50 reverse oi1..1200 "
            "(no Instant; no Post; OG50 name STUBBED)"
        ),
        "pending": pending,
        "stage_count": stage,
        "drain": drain,
        "exec": exec_c,
        "allow_post": False,
    }


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
        return {"n": 0, "province_ids": []}
    return {"n": len(vals), "province_ids": vals[:12]}


def read_cpdx_ptrs(b, base, arr_addr, max_n=48):
    try:
        data = u64(b, arr_addr)
        size = i32(b, arr_addr + 0xC)
    except Exception:
        return None
    if not data or size <= 0 or size > 4096:
        return None
    if base <= data < base + 0x4000000:
        return {"size": size, "in_image_sentinel": True, "ptrs": []}
    n = min(size, max_n)
    blob = try_read(b, data, n * 8)
    if not blob:
        return {"size": size, "in_image_sentinel": False, "ptrs": []}
    return {
        "size": size,
        "in_image_sentinel": False,
        "ptrs": [struct.unpack_from("<Q", blob, j * 8)[0] for j in range(n)],
    }


def scan_path_armies(b, base, tag):
    focus = set(FOCUS_PROVS)
    ita_ok = empty_n = nonempty_n = multi_n = 0
    path_rows = []
    by_prov = defaultdict(list)
    for idx in range(ARMY_LO, ARMY_HI + 1):
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
        ita_ok += 1
        p = path60(b, base, army, tag)
        n = p.get("n") or 0
        ids = p.get("province_ids") or []
        if n > 1:
            multi_n += 1
        elif n == 1:
            nonempty_n += 1
        else:
            empty_n += 1
            continue
        inter = sorted(set(ids) & focus)
        path_rows.append(
            {
                "index": idx,
                "army": army,
                "path_n": n,
                "path_ids": ids,
                "focus_hit": inter,
            }
        )
        for pid in ids:
            by_prov[pid].append(idx)
    return {
        "ita_ok": ita_ok,
        "empty_n": empty_n,
        "nonempty_n": nonempty_n,
        "multi_n": multi_n,
        "path_rows": path_rows,
        "by_prov_head": {
            str(k): v[:8]
            for k, v in sorted(by_prov.items(), key=lambda kv: -len(kv[1]))[:16]
        },
    }


def reverse_og50(b, base, path_rows):
    """Map army ptr → list of oi that list it in OG+0x50. No Instant."""
    want = {}
    for r in path_rows:
        want[r["army"]] = r["index"]
        want[r["army"] + CA_MI_OFF] = r["index"]  # also match MI ptr form
    army_to_ois = defaultdict(list)
    oi_with_arr50 = 0
    oi_scanned = 0
    for oi in range(OI_LO, OI_HI + 1):
        try:
            hdr = resolve_handle(b, TYPE_OG, oi, base)
        except Exception:
            continue
        oi_scanned += 1
        if not hdr:
            continue
        og = hdr + 0x10
        arr50 = read_cpdx_ptrs(b, base, og + 0x50, 48)
        if not arr50 or arr50.get("in_image_sentinel"):
            continue
        ptrs = arr50.get("ptrs") or []
        if not ptrs:
            continue
        oi_with_arr50 += 1
        for p in ptrs:
            if not p or p < 0x10000:
                continue
            idx = want.get(p) or want.get(p - CA_MI_OFF)
            if idx is None:
                # walkback primary if MI
                mi_vt = try_u64(b, p)
                if mi_vt and (mi_vt - base) == CA_MI_VT:
                    primary = p - CA_MI_OFF
                    idx = want.get(primary)
            if idx is None:
                continue
            if oi not in army_to_ois[idx]:
                army_to_ois[idx].append(oi)
    return dict(army_to_ois), {"oi_scanned": oi_scanned, "oi_with_arr50": oi_with_arr50}


def classify_ois(ois):
    tags = []
    for oi in ois:
        tags.append({"oi": oi, "kind": KNOWN.get(oi, "other")})
    return tags


def patch_docs(meta, result, scan_pub, reverse_meta, hits_pub, new_ois):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    repl = (
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
        f"Assign oi≠0 (2ib `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**."
    )
    for old in (
        "2ia `MIDBAND_OG575_DIG_HIT`",
        "2ib `PATH200_ALL_REVERSE_HIT`",
        "2ib `PATH200_ALL_REVERSE_PARTIAL`",
        "2ib `PATH200_ALL_REVERSE_EMPTY`",
    ):
        needle = (
            "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0 ({old}); retry GitHub push when reachable. Still **NO ALLOW_POST**."
        )
        if needle in t:
            t = t.replace(needle, repl)
            break
    brief = (
        f"path_armies={scan_pub.get('path_army_n')} hit={len(hits_pub)} "
        f"new_ois={new_ois[:12]} oi_scanned={reverse_meta.get('oi_scanned')} "
        f"oi_with_arr50={reverse_meta.get('oi_with_arr50')}"
    )
    t = re.sub(
        r"\| `OG50MI` \| membership \| OG`\+0x50` ≡ CArmy`\+0xB8` — [^\n]*\|\n",
        f"| `OG50MI` | membership | OG`+0x50` ≡ CArmy`+0xB8` — 2ib PATH200 denser "
        f"{brief} (name STUBBED) |\n",
        t,
        count=1,
    )
    row = (
        f"| **2ib** | `{result}` | PATH200 denser all-nonempty → OG50 reverse | "
        f"oi≠0 / midflight / Instant-repoll / Post HARD_DENY |\n"
    )
    if "| **2ib** |" in t:
        t = re.sub(r"^\| \*\*2ib\*\* \|.*\n", row, t, count=1, flags=re.M)
    elif "| **2ia** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2ia** |"):
                out.append(row)
        t = "".join(out)
    note = (
        f"**2ib PATH200 denser→OG50 reverse:** result=`{result}` · {brief} · "
        f"hours={meta.get('hours')} UI={meta.get('ui_date')} · allow_post=False\n"
    )
    if "**2ib PATH200 denser→OG50 reverse:**" in t:
        t = re.sub(r"^\*\*2ib PATH200 denser→OG50 reverse:\*\*.*\n", note, t, count=1, flags=re.M)
    elif "**2ia mid-band OG575 dig:**" in t:
        idx = t.find("**2ia mid-band OG575 dig:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2ia · mid-band OG575 dig · 2026-10-31 Asia/Shanghai*",
        "*Phase 2ib · PATH200 denser all→OG50 reverse · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2ia — checklist polish (CLOSED)",
        "## Phase 2gj … 2ib — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2ib | PATH200 denser all-nonempty → OG50 reverse | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2ib |" in t2:
        t2 = re.sub(r"^\| 2ib \|.*\n", row2, t2, count=1, flags=re.M)
    elif "| 2ia |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2ia |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2ia — mid-band OG575 dig. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2ib — PATH200 denser all→OG50 reverse. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")

    DOC.write_text(
        (
            f"# Phase 2ib — PATH200 denser all → OG50 reverse\n\n"
            f"**Result:** `{result}`\n\n"
            f"**Scan:** {json.dumps(scan_pub, ensure_ascii=False)}\n\n"
            f"**Reverse:** {json.dumps(reverse_meta, ensure_ascii=False)}\n\n"
            f"**Hits (path army → ois):** {json.dumps(hits_pub, ensure_ascii=False)}\n\n"
            f"**New OIs (not in known 481/575/962/976):** {new_ois}\n\n"
            f"**Live:** pid {meta.get('pid')} · hours={meta.get('hours')} UI={meta.get('ui_date')} · "
            f"drain={meta.get('drain')} · allow_post=False · speed untouched\n\n"
            f"**Semantics:** Denser PATH200 multi-army + OG+0x50 reverse for all nonempty-path "
            f"ITA armies. No Instant. Field name STUBBED. No Post.\n\n"
            f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.\n\n"
            f"*Phase 2ib · 2026-10-31 Asia/Shanghai · sha_base {SHA_BASE}*\n"
        ),
        encoding="utf-8",
    )


def main():
    assert allow_post() is False
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2ib",
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

    scan = scan_path_armies(b, base, tag)
    path_rows = scan["path_rows"]
    army_to_ois, reverse_meta = reverse_og50(b, base, path_rows)

    hits = []
    new_oi_set = set()
    known_hit_n = 0
    for r in path_rows:
        ois = sorted(army_to_ois.get(r["index"]) or [])
        kinds = classify_ois(ois)
        for k in kinds:
            if k["kind"] == "other":
                new_oi_set.add(k["oi"])
            else:
                known_hit_n += 1
        hits.append(
            {
                "index": r["index"],
                "path_ids": r["path_ids"],
                "focus_hit": r["focus_hit"],
                "ois": ois,
                "kinds": kinds,
            }
        )

    hit_n = sum(1 for h in hits if h["ois"])
    path_army_n = len(path_rows)
    new_ois = sorted(new_oi_set)
    scan_pub = {
        "ita_ok": scan["ita_ok"],
        "empty_n": scan["empty_n"],
        "nonempty_n": scan["nonempty_n"],
        "multi_n": scan["multi_n"],
        "path_army_n": path_army_n,
        "by_prov_head": scan["by_prov_head"],
    }
    hits_pub = hits  # all path armies (usually small)

    if path_army_n >= 1 and hit_n >= 1:
        result = "PATH200_ALL_REVERSE_HIT"
    elif path_army_n >= 1:
        result = "PATH200_ALL_REVERSE_PARTIAL"
    else:
        result = "PATH200_ALL_REVERSE_EMPTY"

    report = {
        "phase": "2ib",
        "result": result,
        "allow_post": False,
        "live": meta,
        "scan": scan_pub,
        "reverse": reverse_meta,
        "hits": hits_pub,
        "new_ois": new_ois,
        "hit_n": hit_n,
        "known_kind_sightings": known_hit_n,
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
            "Instant map re-poll",
            "hi-band Instant-empty re-poll",
            "463 Inst70 oi1..511 re-poll",
            "OG575 Instant-empty re-poll",
            "invent OG+0x50 field name",
        ],
        "next_shortest_blocker": (
            "NON-Post: human midflight CMove hex / SAFE Post for ring_embed OR later "
            "plan-dense Assign oi≠0 (2ib PATH200 denser→OG50); push when GitHub reachable; "
            "still NO ALLOW_POST"
        ),
        "semantics": (
            "PATH200 denser all-nonempty ITA → OG+0x50 reverse oi1..1200; "
            "no Instant; field name STUBBED; no Post"
        ),
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2ib",
                "result": result,
                "allow_post": False,
                "path_army_n": path_army_n,
                "hit_n": hit_n,
                "new_ois": new_ois,
                "hits_head": hits_pub[:24],
                "reverse": reverse_meta,
                "scan": {
                    "ita_ok": scan_pub["ita_ok"],
                    "nonempty_n": scan_pub["nonempty_n"],
                    "multi_n": scan_pub["multi_n"],
                },
                "live": {
                    "pid": meta.get("pid"),
                    "hours": meta.get("hours"),
                    "ui_date": meta.get("ui_date"),
                    "drain": meta.get("drain"),
                    "exec": meta.get("exec"),
                    "allow_post": False,
                },
                "sha_base": SHA_BASE,
                "next_shortest_blocker": report["next_shortest_blocker"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    try:
        patch_docs(meta, result, scan_pub, reverse_meta, hits_pub[:32], new_ois)
    except Exception as e:
        report["doc_patch_error"] = str(e)
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "phase": "2ib",
                "result": result,
                "allow_post": False,
                "live": meta,
                "scan": scan_pub,
                "reverse": reverse_meta,
                "hit_n": hit_n,
                "path_army_n": path_army_n,
                "new_ois": new_ois,
                "hits_head": hits_pub[:24],
                "next_shortest_blocker": report["next_shortest_blocker"],
                "sha_base": SHA_BASE,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
