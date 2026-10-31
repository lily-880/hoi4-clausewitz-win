#!/usr/bin/env python3
"""Phase 2ia: mid-band OG575 dig (Inst70 + OG50 + PATH) (RO).

Home of 2hz reverse hit 2640→oi575 path[3938]. Catalog members, Instant+0x70
(honest empty OK), PATH; cross shared dests with OG481 Inst70. Corrected
INST_VT=0x2A02558. OG+0x50 name STUBBED. One-shot; no Post; never 5x; no speed
write; no midflight; no Assign oi≠0; no Instant-map / hi-band Instant-empty /
463 Inst70 oi1..511 re-poll.
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

OUT = ROOT / "reports" / "phase2ia_midband_og575_dig.json"
SUMMARY = ROOT / "reports" / "phase2ia_summary.json"
DOC = ROOT / "docs" / "PHASE2IA_MIDBAND_OG575_DIG.md"

GS_PLAYER_TAG = 0x518
TYPE_OG = 0x35
FOCUS_OI = 575
REF_OI = 481
EXPECT_IDX = 2640  # from 2hz
EXPECT_PATH = 3938
CA_VT_RVA = 0x29D6D68
CA_MI_OFF = 0xB8
CA_MI_VT = 0x29D6FB8
CA_TAG = 0x1E0
PATH_OFF = 0x60
INST_VT = 0x2A02558
ARMY_LO, ARMY_HI = 1, 3000
SHA_BASE = "8862357"


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
            "ITA mid-band OG575 dig Inst70+OG50+PATH "
            "(INST_VT corrected; no Post; OG50 name STUBBED; no 463 Inst70 re-poll)"
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


def read_cpdx_u32(b, base, arr_addr, max_n=64):
    try:
        data = u64(b, arr_addr)
        size = i32(b, arr_addr + 0xC)
    except Exception:
        return None
    if not data or size <= 0 or size > 4096:
        return None
    if base <= data < base + 0x4000000:
        return {"size": size, "in_image_sentinel": True, "u32s": []}
    n = min(size, max_n)
    blob = try_read(b, data, n * 4)
    if not blob:
        return {"size": size, "in_image_sentinel": False, "u32s": []}
    return {
        "size": size,
        "in_image_sentinel": False,
        "u32s": [struct.unpack_from("<I", blob, j * 4)[0] for j in range(n)],
    }


def build_ptr_index(b, base):
    ptr_to_idx = {}
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
        ptr_to_idx[army] = idx
    return ptr_to_idx


def dig_oi(b, base, tag, oi, ptr_to_idx):
    try:
        hdr = resolve_handle(b, TYPE_OG, oi, base)
    except Exception:
        return {"oi": oi, "ok": False, "error": "resolve_fail"}
    if not hdr:
        return {"oi": oi, "ok": False, "error": "null_hdr"}
    og = hdr + 0x10
    arr98 = read_cpdx_ptrs(b, base, og + 0x98, 2)
    ptrs = (arr98 or {}).get("ptrs") or []
    inst_ok = False
    set70 = set()
    arr70_n = 0
    u32s_head = []
    inst_vt_rva = None
    arr98_size = (arr98 or {}).get("size")
    if ptrs:
        inst = ptrs[0]
        vt = try_u64(b, inst)
        if vt:
            inst_vt_rva = vt - base
        inst_ok = bool(vt and (vt - base) == INST_VT)
        if inst_ok:
            a70 = read_cpdx_u32(b, base, inst + 0x70, 64)
            if a70 and not a70.get("in_image_sentinel"):
                u32s = a70.get("u32s") or []
                if u32s and all(looks_like_province(v) for v in u32s):
                    set70 = set(u32s)
                    arr70_n = len(u32s)
                    u32s_head = u32s[:8]

    arr50 = read_cpdx_ptrs(b, base, og + 0x50, 48)
    members = []
    walk_ok = 0
    expect_in = False
    expect_path_hit = False
    for p in (arr50 or {}).get("ptrs") or []:
        if not p or p < 0x10000:
            continue
        primary = p - CA_MI_OFF
        avt = try_u64(b, primary)
        mi_vt = try_u64(b, p)
        ok = bool(
            avt and (avt - base) == CA_VT_RVA and mi_vt and (mi_vt - base) == CA_MI_VT
        )
        if ok:
            walk_ok += 1
        atag = try_u32(b, primary + CA_TAG) if ok else None
        idx = ptr_to_idx.get(primary)
        if idx == EXPECT_IDX:
            expect_in = True
        path = path60(b, base, primary, tag) if ok else {"n": 0, "province_ids": []}
        pids = path.get("province_ids") or []
        if idx == EXPECT_IDX and EXPECT_PATH in pids:
            expect_path_hit = True
        dest_in_70 = sorted(set(pids) & set70)
        members.append(
            {
                "index": idx,
                "tag": atag,
                "ita": atag == tag if atag is not None else False,
                "walkback_ok": ok,
                "path_ids": pids if ok else [],
                "path_n": path.get("n") if ok else 0,
                "dest_in_70": dest_in_70,
                "triangle": bool(ok and dest_in_70),
            }
        )
    return {
        "oi": oi,
        "ok": True,
        "inst_ok": inst_ok,
        "inst_vt_rva": hex(inst_vt_rva) if inst_vt_rva is not None else None,
        "arr98_size": arr98_size,
        "arr70_n": arr70_n,
        "u32s_head": u32s_head,
        "og50_size": (arr50 or {}).get("size") or 0,
        "walk_ok": walk_ok,
        "expect_idx": EXPECT_IDX,
        "expect_in_og50": expect_in,
        "expect_path_hit": expect_path_hit,
        "members": members,
        "set70": set70,
        "triangle_n": sum(1 for m in members if m.get("triangle")),
        "ita_n": sum(1 for m in members if m.get("ita")),
        "path_mem_n": sum(1 for m in members if (m.get("path_n") or 0) > 0),
    }


def dig_ref70(b, base):
    try:
        hdr = resolve_handle(b, TYPE_OG, REF_OI, base)
    except Exception:
        return set(), {"ok": False}
    if not hdr:
        return set(), {"ok": False}
    og = hdr + 0x10
    arr98 = read_cpdx_ptrs(b, base, og + 0x98, 2)
    ptrs = (arr98 or {}).get("ptrs") or []
    if not ptrs:
        return set(), {"ok": False, "reason": "no_inst_ptrs"}
    inst = ptrs[0]
    vt = try_u64(b, inst)
    if not vt or (vt - base) != INST_VT:
        return set(), {"ok": False, "inst_ok": False, "inst_vt_rva": hex(vt - base) if vt else None}
    a70 = read_cpdx_u32(b, base, inst + 0x70, 64)
    if not a70 or a70.get("in_image_sentinel"):
        return set(), {"ok": True, "inst_ok": True, "arr70_n": 0}
    u32s = a70.get("u32s") or []
    if not u32s or not all(looks_like_province(v) for v in u32s):
        return set(), {"ok": True, "inst_ok": True, "arr70_n": 0}
    return set(u32s), {"ok": True, "inst_ok": True, "arr70_n": len(u32s)}


def patch_docs(meta, result, dig_pub, cross, ref_meta):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    repl = (
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
        f"Assign oi≠0 (2ia `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**."
    )
    for old in (
        "2hz `NONHIBAND_PATH_OG50_REVERSE_HIT`",
        "2ia `MIDBAND_OG575_DIG_HIT`",
        "2ia `MIDBAND_OG575_DIG_PARTIAL`",
        "2ia `MIDBAND_OG575_DIG_EMPTY`",
    ):
        needle = (
            "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0 ({old}); retry GitHub push when reachable. Still **NO ALLOW_POST**."
        )
        if needle in t:
            t = t.replace(needle, repl)
            break
    brief = (
        f"oi{dig_pub.get('oi')} size={dig_pub.get('og50_size')} walk={dig_pub.get('walk_ok')} "
        f"arr70={dig_pub.get('arr70_n')} expect_in={dig_pub.get('expect_in_og50')} "
        f"path_hit={dig_pub.get('expect_path_hit')} tri={dig_pub.get('triangle_n')}"
    )
    t = re.sub(
        r"\| `OG50MI` \| membership \| OG`\+0x50` ≡ CArmy`\+0xB8` — [^\n]*\|\n",
        f"| `OG50MI` | membership | OG`+0x50` ≡ CArmy`+0xB8` — 2ia mid-band "
        f"{brief} (name STUBBED) |\n",
        t,
        count=1,
    )
    row = (
        f"| **2ia** | `{result}` | mid-band OG575 dig Inst70+OG50+PATH (2hz 2640 home) | "
        f"oi≠0 / midflight / Instant-repoll / Post HARD_DENY |\n"
    )
    if "| **2ia** |" in t:
        t = re.sub(r"^\| \*\*2ia\*\* \|.*\n", row, t, count=1, flags=re.M)
    elif "| **2hz** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2hz** |"):
                out.append(row)
        t = "".join(out)
    note = (
        f"**2ia mid-band OG575 dig:** result=`{result}` · {brief} · "
        f"cross70_n={cross.get('shared_n')} shared={cross.get('shared_head')} · "
        f"ref481_arr70={ref_meta.get('arr70_n')} · "
        f"hours={meta.get('hours')} UI={meta.get('ui_date')} · allow_post=False\n"
    )
    if "**2ia mid-band OG575 dig:**" in t:
        t = re.sub(r"^\*\*2ia mid-band OG575 dig:\*\*.*\n", note, t, count=1, flags=re.M)
    elif "**2hz non-hiband path→OG50 reverse:**" in t:
        idx = t.find("**2hz non-hiband path→OG50 reverse:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2hz · non-hiband path→OG50 reverse · 2026-10-31 Asia/Shanghai*",
        "*Phase 2ia · mid-band OG575 dig · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2hz — checklist polish (CLOSED)",
        "## Phase 2gj … 2ia — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2ia | mid-band OG575 dig Inst70+OG50+PATH (2hz 2640 home) | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2ia |" in t2:
        t2 = re.sub(r"^\| 2ia \|.*\n", row2, t2, count=1, flags=re.M)
    elif "| 2hz |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2hz |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2hz — non-hiband path→OG50 reverse. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2ia — mid-band OG575 dig. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")

    DOC.write_text(
        (
            f"# Phase 2ia — mid-band OG575 dig\n\n"
            f"**Result:** `{result}`\n\n"
            f"**Constants:** INST_VT=0x2A02558 · OG+0x50 name STUBBED · expect idx={EXPECT_IDX} path={EXPECT_PATH}\n\n"
            f"**Ref OG{REF_OI} Inst70:** {json.dumps(ref_meta, ensure_ascii=False)}\n\n"
            f"**Dig:** {json.dumps(dig_pub, ensure_ascii=False)}\n\n"
            f"**Cross Inst70 ∩ OG481:** {json.dumps(cross, ensure_ascii=False)}\n\n"
            f"**Live:** pid {meta.get('pid')} · hours={meta.get('hours')} UI={meta.get('ui_date')} · "
            f"drain={meta.get('drain')} · allow_post=False · speed untouched\n\n"
            f"**Semantics:** Mid-band OG575 home of 2hz 2640→575 path[3938]. Instant may be empty "
            f"(honest membership shell). Field name STUBBED. No invent. No Post / 463 Inst70 re-poll.\n\n"
            f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.\n\n"
            f"*Phase 2ia · 2026-10-31 Asia/Shanghai · sha_base {SHA_BASE}*\n"
        ),
        encoding="utf-8",
    )


def main():
    assert allow_post() is False
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2ia",
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

    ptr_to_idx = build_ptr_index(b, base)
    ref70, ref_meta = dig_ref70(b, base)
    dig = dig_oi(b, base, tag, FOCUS_OI, ptr_to_idx)
    dig_pub = {k: v for k, v in dig.items() if k != "set70"}

    s70 = dig.get("set70") or set()
    shared = sorted(s70 & ref70)
    cross = {
        "shared_n": len(shared),
        "shared_head": shared[:16],
        "only_575_n": len(s70 - ref70),
        "only_481_n": len(ref70 - s70),
    }

    dig_ok = bool(dig.get("ok"))
    expect_in = bool(dig.get("expect_in_og50"))
    walk_n = dig.get("walk_ok") or 0
    path_hit = bool(dig.get("expect_path_hit"))
    tri_n = dig.get("triangle_n") or 0
    path_mem = dig.get("path_mem_n") or 0
    inst_ok = bool(dig.get("inst_ok"))

    if dig_ok and expect_in and walk_n >= 1:
        result = "MIDBAND_OG575_DIG_HIT"
    elif dig_ok and (walk_n >= 1 or expect_in or path_hit or inst_ok or tri_n):
        result = "MIDBAND_OG575_DIG_PARTIAL"
    else:
        result = "MIDBAND_OG575_DIG_EMPTY"

    report = {
        "phase": "2ia",
        "result": result,
        "allow_post": False,
        "live": meta,
        "ref481": ref_meta,
        "dig": dig_pub,
        "cross": cross,
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
            "invent OG+0x50 field name",
        ],
        "next_shortest_blocker": (
            "NON-Post: human midflight CMove hex / SAFE Post for ring_embed OR later "
            "plan-dense Assign oi≠0 (2ia mid-band OG575 dig); push when GitHub reachable; "
            "still NO ALLOW_POST"
        ),
        "semantics": (
            "mid-band OG575 Inst70+OG50+PATH; cross∩OG481 Inst70; "
            "field name STUBBED; no Post"
        ),
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    members_path = [
        {
            "index": m.get("index"),
            "path_ids": m.get("path_ids"),
            "dest_in_70": m.get("dest_in_70"),
            "triangle": m.get("triangle"),
        }
        for m in (dig_pub.get("members") or [])
        if (m.get("path_n") or 0) > 0 or m.get("triangle") or m.get("index") == EXPECT_IDX
    ]
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2ia",
                "result": result,
                "allow_post": False,
                "ok": dig_ok,
                "inst_ok": inst_ok,
                "walk_n": walk_n,
                "path_mem_n": path_mem,
                "expect_in": expect_in,
                "expect_path_hit": path_hit,
                "triangle_n": tri_n,
                "cross_shared_n": cross["shared_n"],
                "members_path": members_path,
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
        patch_docs(meta, result, dig_pub, cross, ref_meta)
    except Exception as e:
        report["doc_patch_error"] = str(e)
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "phase": "2ia",
                "result": result,
                "allow_post": False,
                "live": meta,
                "ref481": ref_meta,
                "ok": dig_ok,
                "inst_ok": inst_ok,
                "inst_vt_rva": dig_pub.get("inst_vt_rva"),
                "arr98_size": dig_pub.get("arr98_size"),
                "arr70_n": dig_pub.get("arr70_n"),
                "og50_size": dig_pub.get("og50_size"),
                "walk_n": walk_n,
                "path_mem_n": path_mem,
                "expect_in": expect_in,
                "expect_path_hit": path_hit,
                "triangle_n": tri_n,
                "ita_n": dig_pub.get("ita_n"),
                "cross": cross,
                "members_path": members_path,
                "next_shortest_blocker": report["next_shortest_blocker"],
                "sha_base": SHA_BASE,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
