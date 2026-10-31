#!/usr/bin/env python3
"""Phase 2ih: post-reload known-OG PATH shells denser (RO).

Catalog OG+0x50 membership + PATH@+0x60 for known oi={481,575,962,976}
after RELOAD_OR_NEW_CAMPAIGN. Instant+0x70 ONLY on populated 481 for dest
cross; NO Instant on 575/962/976 (Instant-empty HARD_DENY). No Assign /
midflight / Post; never 5x; no speed write; OG+0x50 name STUBBED.
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

OUT = ROOT / "reports" / "phase2ih_known_og_path_shells.json"
SUMMARY = ROOT / "reports" / "phase2ih_summary.json"
DOC = ROOT / "docs" / "PHASE2IH_KNOWN_OG_PATH_SHELLS.md"

GS_PLAYER_TAG = 0x518
TYPE_OG = 0x35
KNOWN_OIS = (481, 575, 962, 976)
KIND = {481: "focus", 575: "midband", 962: "hiband", 976: "hiband"}
REF_OI = 481
CA_VT_RVA = 0x29D6D68
CA_MI_OFF = 0xB8
CA_MI_VT = 0x29D6FB8
CA_TAG = 0x1E0
PATH_OFF = 0x60
INST_VT = 0x2A02558
ARMY_LO, ARMY_HI = 1, 3000
# prior sightings across 2ie/2if
PRIOR = {
    481: (),
    575: (2640, 1049, 1043, 1039, 2678),
    962: (),
    976: (),
}
SHA_BASE = "20da2f4"


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
    clock_class = "RELOAD_OR_NEW_CAMPAIGN" if int(hours) < 48 else "CONTINUOUS"
    return {
        "pid": pid,
        "hours": hours,
        "year_at_0x478": year,
        "ui_date": d.strftime("%Y-%m-%d %H:00"),
        "clock_class": clock_class,
        "speed_policy": "pause-or-1x only (never write speed)",
        "country_tag_filter": tag,
        "scenario": (
            "ITA post-reload known-OG PATH shells denser "
            "(481/575/962/976; Instant only on 481; no Post; OG50 name STUBBED)"
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
        return set(), {"ok": False, "reason": "no_inst"}
    inst = ptrs[0]
    vt = try_u64(b, inst)
    if not vt or (vt - base) != INST_VT:
        return set(), {"ok": False, "inst_ok": False}
    a70 = read_cpdx_u32(b, base, inst + 0x70, 64)
    if not a70 or a70.get("in_image_sentinel"):
        return set(), {"ok": True, "inst_ok": True, "arr70_n": 0}
    u32s = a70.get("u32s") or []
    if not u32s or not all(looks_like_province(v) for v in u32s):
        return set(), {"ok": True, "inst_ok": True, "arr70_n": 0}
    return set(u32s), {
        "ok": True,
        "inst_ok": True,
        "arr70_n": len(u32s),
        "u32s_head": u32s[:12],
    }


def dig_shell(b, base, tag, oi, ptr_to_idx, set70):
    """OG+0x50 + PATH. Instant never on oi except via separate ref70 for 481."""
    try:
        hdr = resolve_handle(b, TYPE_OG, oi, base)
    except Exception:
        return {"ok": False, "oi": oi, "error": "resolve_fail"}
    if not hdr:
        return {"ok": False, "oi": oi, "error": "null_hdr"}
    og = hdr + 0x10
    arr50 = read_cpdx_ptrs(b, base, og + 0x50, 48)
    prior = set(PRIOR.get(oi) or ())
    members = []
    walk_ok = 0
    expect_present = []
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
        path = path60(b, base, primary, tag) if ok else {"n": 0, "province_ids": []}
        pids = path.get("province_ids") or []
        dest = sorted(set(pids) & set70) if set70 else []
        if idx in prior:
            expect_present.append(idx)
        members.append(
            {
                "index": idx,
                "tag": atag,
                "ita": atag == tag if atag is not None else False,
                "walkback_ok": ok,
                "path_ids": pids if ok else [],
                "path_n": path.get("n") if ok else 0,
                "dest_in_481_70": dest,
                "triangle_481": bool(ok and dest),
                "path_only_3938": bool(ok and pids == [3938]),
            }
        )
    idxs = [m["index"] for m in members if m.get("index") is not None]
    return {
        "ok": True,
        "oi": oi,
        "kind": KIND.get(oi, "other"),
        "og50_size": (arr50 or {}).get("size") or 0,
        "walk_ok": walk_ok,
        "ita_n": sum(1 for m in members if m.get("ita")),
        "path_mem_n": sum(1 for m in members if (m.get("path_n") or 0) > 0),
        "triangle_481_n": sum(1 for m in members if m.get("triangle_481")),
        "path_only_3938_n": sum(1 for m in members if m.get("path_only_3938")),
        "member_idxs": idxs,
        "expect_present": sorted(set(expect_present)) if prior else [],
        "expect_missing": sorted(prior - set(expect_present)) if prior else [],
        "new_vs_prior": sorted(set(idxs) - prior) if prior else idxs[:],
        "members": members,
        "no_instant_on_shell": oi != REF_OI,
    }


def patch_docs(meta, result, shells_pub, ref_meta):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    repl = (
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
        f"Assign oi≠0 (2ih `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**."
    )
    for old in (
        "2ig `ARR88_RELOAD_PATH_HIT`",
        "2ih `KNOWN_OG_PATH_SHELLS_HIT`",
        "2ih `KNOWN_OG_PATH_SHELLS_PARTIAL`",
        "2ih `KNOWN_OG_PATH_SHELLS_EMPTY`",
    ):
        needle = (
            "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0 ({old}); retry GitHub push when reachable. Still **NO ALLOW_POST**."
        )
        if needle in t:
            t = t.replace(needle, repl)
            break
    brief_parts = []
    for s in shells_pub:
        brief_parts.append(
            f"{s['oi']}:{s.get('og50_size')}/{s.get('path_mem_n')}p"
        )
    brief = (
        f"shells=[{', '.join(brief_parts)}] ref70={ref_meta.get('arr70_n')} "
        f"clock={meta.get('clock_class')}"
    )
    t = re.sub(
        r"\| `OG50MI` \| membership \| OG`\+0x50` ≡ CArmy`\+0xB8` — [^\n]*\|\n",
        f"| `OG50MI` | membership | OG`+0x50` ≡ CArmy`+0xB8` — 2ih known-OG PATH shells "
        f"{brief} (name STUBBED) |\n",
        t,
        count=1,
    )
    row = (
        f"| **2ih** | `{result}` | post-reload known-OG PATH shells denser | "
        f"oi≠0 / midflight / Instant-repoll / Post HARD_DENY |\n"
    )
    if "| **2ih** |" in t:
        t = re.sub(r"^\| \*\*2ih\*\* \|.*\n", row, t, count=1, flags=re.M)
    elif "| **2ig** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2ig** |"):
                out.append(row)
        t = "".join(out)
    note = (
        f"**2ih known-OG PATH shells denser:** result=`{result}` · {brief} · "
        f"hours={meta.get('hours')} UI={meta.get('ui_date')} · allow_post=False\n"
    )
    if "**2ih known-OG PATH shells denser:**" in t:
        t = re.sub(r"^\*\*2ih known-OG PATH shells denser:\*\*.*\n", note, t, count=1, flags=re.M)
    elif "**2ig OG481 arr88 reload×PATH:**" in t:
        idx = t.find("**2ig OG481 arr88 reload×PATH:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2ig · OG481 arr88 reload×PATH · 2026-10-31 Asia/Shanghai*",
        "*Phase 2ih · known-OG PATH shells denser · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2ig — checklist polish (CLOSED)",
        "## Phase 2gj … 2ih — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2ih | post-reload known-OG PATH shells denser | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2ih |" in t2:
        t2 = re.sub(r"^\| 2ih \|.*\n", row2, t2, count=1, flags=re.M)
    elif "| 2ig |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2ig |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2ig — OG481 arr88 reload×PATH. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2ih — known-OG PATH shells denser. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")

    DOC.write_text(
        (
            f"# Phase 2ih — post-reload known-OG PATH shells denser\n\n"
            f"**Result:** `{result}`\n\n"
            f"**Clock:** {meta.get('clock_class')} · hours={meta.get('hours')} · "
            f"year@+0x478={meta.get('year_at_0x478')} · UI={meta.get('ui_date')}\n\n"
            f"**Ref481 Inst70:** {json.dumps(ref_meta, ensure_ascii=False)}\n\n"
            f"**Shells (PATH-only; Instant only via ref481):** "
            f"{json.dumps(shells_pub, ensure_ascii=False)}\n\n"
            f"**Live:** pid {meta.get('pid')} · hours={meta.get('hours')} UI={meta.get('ui_date')} · "
            f"drain={meta.get('drain')} · allow_post=False · speed untouched\n\n"
            f"**Semantics:** known oi 481/575/962/976 membership+PATH denser post-reload. "
            f"No Instant on 575/962/976. Field name STUBBED. No Post.\n\n"
            f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.\n\n"
            f"*Phase 2ih · 2026-10-31 Asia/Shanghai · sha_base {SHA_BASE}*\n"
        ),
        encoding="utf-8",
    )


def main():
    assert allow_post() is False
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2ih",
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
    set70, ref_meta = dig_ref70(b, base)

    shells = []
    for oi in KNOWN_OIS:
        shells.append(dig_shell(b, base, tag, oi, ptr_to_idx, set70))

    shells_pub = []
    ok_n = path_shell_n = 0
    for s in shells:
        pub = {k: v for k, v in s.items() if k != "members"}
        pub["members_head"] = (s.get("members") or [])[:12]
        shells_pub.append(pub)
        if s.get("ok") and (s.get("og50_size") or 0) > 0:
            ok_n += 1
        if (s.get("path_mem_n") or 0) > 0:
            path_shell_n += 1

    if ok_n >= 3 and path_shell_n >= 1:
        result = "KNOWN_OG_PATH_SHELLS_HIT"
    elif ok_n >= 1:
        result = "KNOWN_OG_PATH_SHELLS_PARTIAL"
    else:
        result = "KNOWN_OG_PATH_SHELLS_EMPTY"

    report = {
        "phase": "2ih",
        "result": result,
        "allow_post": False,
        "live": meta,
        "ref481": ref_meta,
        "shells": shells_pub,
        "ok_n": ok_n,
        "path_shell_n": path_shell_n,
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
            "plan-dense Assign oi≠0 (2ih known-OG PATH shells); push when GitHub reachable; "
            "still NO ALLOW_POST"
        ),
        "semantics": (
            "post-reload known oi 481/575/962/976 PATH shells; "
            "Instant only on 481; field name STUBBED; no Post"
        ),
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2ih",
                "result": result,
                "allow_post": False,
                "ok": True,
                "ok_n": ok_n,
                "path_shell_n": path_shell_n,
                "ref481_arr70": ref_meta.get("arr70_n"),
                "shells": [
                    {
                        "oi": s["oi"],
                        "kind": s.get("kind"),
                        "og50_size": s.get("og50_size"),
                        "walk_ok": s.get("walk_ok"),
                        "path_mem_n": s.get("path_mem_n"),
                        "triangle_481_n": s.get("triangle_481_n"),
                        "member_idxs": s.get("member_idxs"),
                        "expect_missing": s.get("expect_missing"),
                        "new_vs_prior": s.get("new_vs_prior"),
                    }
                    for s in shells_pub
                ],
                "live": {
                    "pid": meta.get("pid"),
                    "hours": meta.get("hours"),
                    "ui_date": meta.get("ui_date"),
                    "clock_class": meta.get("clock_class"),
                    "year_at_0x478": meta.get("year_at_0x478"),
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
        patch_docs(meta, result, shells_pub, ref_meta)
    except Exception as e:
        report["doc_patch_error"] = str(e)
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "phase": "2ih",
                "result": result,
                "allow_post": False,
                "live": meta,
                "ref481": ref_meta,
                "ok_n": ok_n,
                "path_shell_n": path_shell_n,
                "shells": [
                    {
                        "oi": s["oi"],
                        "kind": s.get("kind"),
                        "og50_size": s.get("og50_size"),
                        "walk_ok": s.get("walk_ok"),
                        "path_mem_n": s.get("path_mem_n"),
                        "triangle_481_n": s.get("triangle_481_n"),
                        "member_idxs": s.get("member_idxs"),
                        "expect_missing": s.get("expect_missing"),
                        "new_vs_prior": s.get("new_vs_prior"),
                    }
                    for s in shells_pub
                ],
                "next_shortest_blocker": report["next_shortest_blocker"],
                "sha_base": SHA_BASE,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
