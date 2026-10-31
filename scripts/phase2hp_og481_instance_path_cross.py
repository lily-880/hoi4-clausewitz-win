#!/usr/bin/env python3
"""Phase 2hp: oi=481 OG+0x50 × Instance+0x70/+0x88 × PATH200 cross (RO).

Deepen 2ho hi-band HIT: members of oi=481 vs COrderInstance province maps
and PATH200@+0x60. Contrast out-of-OG path focus 1039/1042. One-shot.
No field invent; no midflight; no Assign oi≠0 poll; no Post; never 5x;
no speed write.
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

OUT = ROOT / "reports" / "phase2hp_og481_instance_path_cross.json"
SUMMARY = ROOT / "reports" / "phase2hp_summary.json"
DOC = ROOT / "docs" / "PHASE2HP_OG481_INSTANCE_PATH_CROSS.md"

GS_PLAYER_TAG = 0x518
TYPE_OG = 0x35
CA_VT_RVA = 0x29D6D68
CA_MI_OFF = 0xB8
CA_MI_VT = 0x29D6FB8
CA_TAG = 0x1E0
PATH_OFF = 0x60
INST_VT = 0x2A84A38
CP_VT = 0x29D3C68
CP_PROVINCE_ID = 0x18
FOCUS_OI = 481
OUT_OF_OG_PATH = (1039, 1042)
IN_OG_HINT = (382, 410, 445, 455, 461, 463)
SHA_BASE = "2c387a6"


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
        "scenario": f"ITA oi={FOCUS_OI} OG50×Inst70/88×PATH200 (no Post, no midflight, no oi≠0)",
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
    n = min(size, max_n)
    blob = try_read(b, data, n * 8)
    if not blob:
        return {"size": size, "in_image_sentinel": False, "ptrs": []}
    ptrs = [struct.unpack_from("<Q", blob, j * 8)[0] for j in range(n)]
    return {"size": size, "in_image_sentinel": False, "ptrs": ptrs, "data": hex(data)}


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
    u32s = [struct.unpack_from("<I", blob, j * 4)[0] for j in range(n)]
    return {"size": size, "in_image_sentinel": False, "u32s": u32s, "data": hex(data)}


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


def resolve_army_row(b, base, tag, idx):
    try:
        army = resolve_handle(b, HANDLE_TYPE_ARMY, idx, base)
    except Exception:
        army = None
    if not army:
        return {"index": idx, "status": "unresolved"}
    vt = try_u64(b, army)
    if not vt or (vt - base) != CA_VT_RVA:
        return {"index": idx, "status": "vt_miss", "army": hex(army)}
    atag = try_u32(b, army + CA_TAG)
    mi = army + CA_MI_OFF
    mi_vt = try_u64(b, mi)
    mi_ok = bool(mi_vt and (mi_vt - base) == CA_MI_VT)
    p = path60(b, base, army, tag)
    bucket = "multi" if p["n"] > 1 else ("nonempty" if p["n"] == 1 else "empty")
    return {
        "index": idx,
        "status": "ok",
        "army": hex(army),
        "army_i": army,
        "mi": hex(mi),
        "mi_i": mi,
        "mi_vt_match": mi_ok,
        "tag": atag,
        "tag_match": atag == tag,
        "bucket": bucket,
        "path_n": p["n"],
        "path_ids": p["province_ids"],
    }


def dig_oi481(b, base, tag):
    try:
        hdr = resolve_handle(b, TYPE_OG, FOCUS_OI, base)
    except Exception:
        hdr = None
    if not hdr:
        return {"ok": False, "reason": "og_unresolved"}
    og = hdr + 0x10
    og_vt = try_u64(b, og)
    arr50 = read_cpdx_ptrs(b, base, og + 0x50, 24)
    arr98 = read_cpdx_ptrs(b, base, og + 0x98, 8)
    inst = None
    inst_vt_ok = False
    if arr98 and arr98.get("ptrs"):
        inst = arr98["ptrs"][0]
        ivt = try_u64(b, inst)
        inst_vt_ok = bool(ivt and (ivt - base) == INST_VT)

    members = []
    mi_set = {}
    if arr50 and not arr50.get("in_image_sentinel"):
        for p in arr50.get("ptrs") or []:
            if not p:
                continue
            primary = p - CA_MI_OFF
            vt = try_u64(b, primary)
            ok = bool(vt and (vt - base) == CA_VT_RVA)
            atag = try_u32(b, primary + CA_TAG) if ok else None
            path = path60(b, base, primary, tag) if ok else {"n": 0, "province_ids": []}
            bucket = (
                "multi"
                if path.get("n", 0) > 1
                else ("nonempty" if path.get("n", 0) == 1 else "empty")
            )
            rec = {
                "mi": hex(p),
                "primary": hex(primary) if ok else None,
                "walkback_ok": ok,
                "tag": atag,
                "ita": atag == tag,
                "bucket": bucket if ok else None,
                "path_ids": path.get("province_ids") if ok else [],
                "path_n": path.get("n") if ok else 0,
            }
            members.append(rec)
            if ok:
                mi_set[p] = rec

    arr70 = arr88_ids = None
    arr70_shaped = False
    arr88_kinds = {}
    if inst and inst_vt_ok:
        a70 = read_cpdx_u32(b, base, inst + 0x70, 64)
        if a70 and not a70.get("in_image_sentinel"):
            u32s = a70.get("u32s") or []
            arr70_shaped = bool(u32s) and all(looks_like_province(v) for v in u32s)
            arr70 = {
                "size": a70.get("size"),
                "shaped": arr70_shaped,
                "u32s": u32s[:32],
            }
        a88 = read_cpdx_ptrs(b, base, inst + 0x88, 32)
        if a88 and not a88.get("in_image_sentinel"):
            ids = []
            kinds = {"CProvince": 0, "CArmy": 0, "COrderInstance": 0, "other": 0, "nullish": 0}
            for p in a88.get("ptrs") or []:
                if not p or p < 0x10000:
                    kinds["nullish"] += 1
                    continue
                vr = try_u64(b, p)
                if not vr:
                    kinds["other"] += 1
                    continue
                rva = vr - base
                if rva == CP_VT:
                    kinds["CProvince"] += 1
                    pid = try_u32(b, p + CP_PROVINCE_ID)
                    if pid is not None:
                        ids.append(pid)
                elif rva == CA_VT_RVA:
                    kinds["CArmy"] += 1
                elif rva == INST_VT:
                    kinds["COrderInstance"] += 1
                else:
                    kinds["other"] += 1
            arr88_ids = ids[:32]
            arr88_kinds = kinds

    # cross member path ids vs inst maps
    path_union = set()
    for m in members:
        if m.get("ita") and m.get("path_ids"):
            path_union.update(m["path_ids"])
    set70 = set((arr70 or {}).get("u32s") or []) if arr70_shaped else set()
    set88 = set(arr88_ids or [])
    cross70 = sorted(path_union & set70)
    cross88 = sorted(path_union & set88)

    return {
        "ok": True,
        "oi": FOCUS_OI,
        "hdr": hex(hdr),
        "og": hex(og),
        "og_vt_rva": hex(og_vt - base) if og_vt else None,
        "arr50_size": (arr50 or {}).get("size"),
        "member_n": len(members),
        "ita_members": sum(1 for m in members if m.get("ita")),
        "members": members,
        "inst": hex(inst) if inst else None,
        "inst_vt_ok": inst_vt_ok,
        "arr70": arr70,
        "arr88_province_ids": arr88_ids,
        "arr88_kinds": arr88_kinds,
        "path_union_ita": sorted(path_union),
        "cross70": cross70,
        "cross88": cross88,
        "cross70_n": len(cross70),
        "cross88_n": len(cross88),
    }


def patch_docs(meta, result, dig, contrast):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    repl = (
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
        f"Assign oi≠0 (2hp `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**."
    )
    for old_r in (
        "2ho `OG50_WIDE_ITA_HIT_HI`",
        "2hp `OG481_PATH_INST_CROSS_HIT`",
        "2hp `OG481_PATH_INST_CROSS_PARTIAL`",
        "2hp `OG481_MEMBERS_PATH_ONLY`",
        "2hp `OG481_GONE`",
    ):
        needle = (
            "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later "
            f"Assign oi≠0 ({old_r}); retry GitHub push when reachable. Still **NO ALLOW_POST**."
        )
        if needle in t:
            t = t.replace(needle, repl)
            break
    c70 = dig.get("cross70_n", 0) if dig.get("ok") else 0
    c88 = dig.get("cross88_n", 0) if dig.get("ok") else 0
    t = re.sub(
        r"\| `OG50MI` \| membership \| OG`\+0x50` ≡ CArmy`\+0xB8` — [^\n]*\|\n",
        f"| `OG50MI` | membership | OG`+0x50` ≡ CArmy`+0xB8` — 2hp oi=481 "
        f"ita={dig.get('ita_members')} cross70={c70} cross88={c88} |\n",
        t,
        count=1,
    )
    # INST7088 row if present
    t = re.sub(
        r"\| `INST7088` \| order/front maps \| Instance`\+0x70`/`\+0x88`[^\n]*\|\n",
        f"| `INST7088` | order/front maps | Instance`+0x70`/`+0x88` — 2hp oi=481 "
        f"cross70={c70} cross88={c88} (⊀ named dest) |\n",
        t,
        count=1,
    )
    row = (
        f"| **2hp** | `{result}` | oi=481 OG50×Inst70/88×PATH200 cross | "
        f"field name / oi≠0 / midflight / Post HARD_DENY |\n"
    )
    if "| **2hp** |" in t:
        t = re.sub(r"\| \*\*2hp\*\* \|[^\n]*\n", row, t, count=1)
    elif "| **2ho** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2ho** |"):
                out.append(row)
        t = "".join(out)
    note = (
        f"**2hp oi=481 Inst×PATH cross:** result=`{result}` · ita_members={dig.get('ita_members')} · "
        f"cross70={c70} cross88={c88} · path_union={dig.get('path_union_ita')} · "
        f"out_og_path={[(c.get('index'), c.get('path_ids')) for c in contrast if c.get('status')=='ok']} · "
        f"hours={meta.get('hours')} UI={meta.get('ui_date')} · allow_post=False.\n"
    )
    if "**2hp oi=481 Inst×PATH cross:**" in t:
        t = re.sub(r"\*\*2hp oi=481 Inst×PATH cross:\*\*[^\n]*\n", note, t, count=1)
    elif "**2ho OG50 wide ITA scan:**" in t:
        idx = t.find("**2ho OG50 wide ITA scan:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2ho · OG+0x50 widen oi1..511 · 2026-10-31 Asia/Shanghai*",
        "*Phase 2hp · oi=481 OG50×Inst×PATH cross · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2ho — checklist polish (CLOSED)",
        "## Phase 2gj … 2hp — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2hp | oi=481 OG50×Inst70/88×PATH200 cross | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2hp |" in t2:
        t2 = re.sub(r"\| 2hp \|[^\n]*\n", row2, t2, count=1)
    elif "| 2ho |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2ho |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2ho — OG50 wide ITA scan. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2hp — oi=481 Inst×PATH cross. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")


def main():
    assert allow_post() is False
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2hp",
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

    dig = dig_oi481(b, base, tag)
    contrast = [resolve_army_row(b, base, tag, i) for i in OUT_OF_OG_PATH]
    # also reaffirm hinted in-OG indices still resolve
    hinted = [resolve_army_row(b, base, tag, i) for i in IN_OG_HINT]

    if not dig.get("ok"):
        result = "OG481_GONE"
    elif dig.get("cross70_n", 0) > 0 or dig.get("cross88_n", 0) > 0:
        result = "OG481_PATH_INST_CROSS_HIT"
    elif dig.get("ita_members", 0) > 0 and dig.get("inst_vt_ok") and (
        dig.get("arr70") or dig.get("arr88_province_ids") is not None
    ):
        # members + inst readable but path ⊀ maps (honest empty cross like 2gn)
        if any(m.get("path_n", 0) > 0 for m in dig.get("members") or []):
            result = "OG481_PATH_INST_CROSS_EMPTY"
        else:
            result = "OG481_MEMBERS_NO_PATH"
    elif dig.get("ita_members", 0) > 0:
        result = "OG481_MEMBERS_PATH_ONLY"
    else:
        result = "OG481_NO_ITA_MEMBERS"

    report = {
        "phase": "2hp",
        "result": result,
        "allow_post": False,
        "live": meta,
        "dig": dig,
        "contrast_out_of_og": contrast,
        "hinted_in_og": [
            {
                "index": h.get("index"),
                "status": h.get("status"),
                "bucket": h.get("bucket"),
                "path_ids": h.get("path_ids"),
                "tag_match": h.get("tag_match"),
            }
            for h in hinted
        ],
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
            "oi=481 OG+0x50 members × Inst+0x70/+0x88 × PATH200@+0x60; "
            "field name STUBBED; no Post"
        ),
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    summary = {
        "phase": "2hp",
        "result": result,
        "allow_post": False,
        "live": meta,
        "oi": FOCUS_OI,
        "ita_members": dig.get("ita_members"),
        "member_n": dig.get("member_n"),
        "inst_vt_ok": dig.get("inst_vt_ok"),
        "arr70_n": (dig.get("arr70") or {}).get("size") if dig.get("arr70") else None,
        "arr70_shaped": (dig.get("arr70") or {}).get("shaped") if dig.get("arr70") else None,
        "arr88_n": len(dig.get("arr88_province_ids") or []) if dig.get("ok") else None,
        "arr88_kinds": dig.get("arr88_kinds"),
        "path_union_ita": dig.get("path_union_ita"),
        "cross70": dig.get("cross70"),
        "cross88": dig.get("cross88"),
        "cross70_n": dig.get("cross70_n"),
        "cross88_n": dig.get("cross88_n"),
        "ita_member_paths": [
            {"path_ids": m.get("path_ids"), "bucket": m.get("bucket"), "primary": m.get("primary")}
            for m in (dig.get("members") or [])
            if m.get("ita")
        ],
        "contrast_out_of_og": [
            {"index": c.get("index"), "bucket": c.get("bucket"), "path_ids": c.get("path_ids"), "status": c.get("status")}
            for c in contrast
        ],
        "next_shortest_blocker": (
            "NON-Post: human midflight CMove hex / SAFE Post for ring_embed OR later "
            "plan-dense Assign oi≠0 (2hp oi=481 Inst×PATH); push when GitHub reachable; "
            "still NO ALLOW_POST"
        ),
        "sha_base": SHA_BASE,
        "semantics": "oi=481 deep cross; no field invent; no Post",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    DOC.write_text(
        "\n".join(
            [
                "# Phase 2hp — oi=481 OG50 × Inst+0x70/+0x88 × PATH200",
                "",
                f"**Result:** `{result}`",
                "",
                f"**OG oi={FOCUS_OI}:** ita_members={dig.get('ita_members')} / "
                f"member_n={dig.get('member_n')} · inst_vt_ok={dig.get('inst_vt_ok')}",
                "",
                f"**Cross:** path∩arr70={dig.get('cross70')} (n={dig.get('cross70_n')}) · "
                f"path∩arr88={dig.get('cross88')} (n={dig.get('cross88_n')})",
                "",
                f"**ITA path_union:** {dig.get('path_union_ita')}",
                "",
                f"**arr70:** {dig.get('arr70')}",
                "",
                f"**arr88 kinds:** {dig.get('arr88_kinds')} · ids={dig.get('arr88_province_ids')}",
                "",
                f"**Out-of-OG path contrast 1039/1042:** {summary['contrast_out_of_og']}",
                "",
                f"**Live:** pid {meta['pid']} · hours={meta['hours']} UI={meta['ui_date']} · "
                f"drain={meta['drain']} · allow_post=False · speed untouched",
                "",
                "**Semantics:** Membership proxy + Instance province maps × PATH200@+0x60. "
                "Field name still STUBBED. No invent. No Post / midflight / oi≠0 poll.",
                "",
                "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for "
                "ring_embed OR later Assign oi≠0; retry GitHub push when reachable. "
                "Still **NO ALLOW_POST**.",
                "",
                f"*Phase 2hp · 2026-10-31 Asia/Shanghai · sha_base {SHA_BASE}*",
                "",
            ]
        ),
        encoding="utf-8",
    )

    patch_docs(meta, result, dig, contrast)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
