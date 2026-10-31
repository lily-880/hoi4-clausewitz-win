#!/usr/bin/env python3
"""Phase 2gn: CArmy+0x200 ↔ Instance+0x70/+0x88 cross (RO).

ONE RO slice. No Post / no ALLOW_POST / no 2fb|2gk execute / never 5x.
Correlate multi-province CArmy+0x200 streams with OrderInstance province maps.
Document link semantics or honest empty. Single snapshot (no endless poll).
"""
from __future__ import annotations

import json
import struct
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import army_subjects
import post_abi
from config import allow_post
from handle import HANDLE_TYPE_ARMY, resolve_handle
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2gn_200_vs_70_cross.json"
SUMMARY = ROOT / "reports" / "phase2gn_summary.json"
DOC = ROOT / "docs" / "PHASE2GN_200_VS_70_CROSS.md"

CA_VT_RVA = 0x29D6D68
TYPE_OG = 0x35
INDEX_LO, INDEX_HI = 1000, 1600
GS_PLAYER_TAG = 0x518
SEED_OIS = (5, 6, 7, 9, 13, 17, 20, 22, 25, 38, 40, 44, 68, 70)
# denser OI scan beyond seed for membership / cross
WIDE_OIS = tuple(range(1, 96))
FOCUS_ARMIES = (1039, 1042)  # 2gm multi hits; also any new +0x200 multi


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


def try_read(b, a, n):
    try:
        return b.read(a, n)
    except Exception:
        return None


def looks_like_province_id(v: int) -> bool:
    return 1 <= v <= 20000


def load_fy():
    path = ROOT / "scripts" / "phase2fy_army_path_vs_70.py"
    src = path.read_text(encoding="utf-8")
    if "if __name__" in src:
        src = src.split("if __name__")[0]
    mod = types.ModuleType("phase2fy_helpers_gn")
    mod.__file__ = str(path)
    exec(compile(src, str(path), "exec"), mod.__dict__)
    return mod


def player_tag(b, base):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    return i32(b, gs + GS_PLAYER_TAG)


def live_meta(b, base, pid, country_tag):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    hours = i32(b, gs + 0x484)
    d = datetime(1936, 1, 1, 0, 0) + timedelta(hours=int(hours))
    pending = stage = drain = exec_c = None
    try:
        sess = u64(b, base + 0x34FFBE8)
        server = u64(b, sess + post_abi.CSession_SERVER)
        pending = u32(b, server + post_abi.CDummyServer_PENDING) if server else None
        stage = u32(b, sess + post_abi.CSession_STAGE_COUNT)
        drain = u32(b, sess + post_abi.CSession_DRAIN_COUNTER)
        exec_c = u32(b, sess + post_abi.CSession_EXEC_COUNTER)
    except Exception:
        pass
    return {
        "pid": pid,
        "hours": hours,
        "ui_date": d.strftime("%Y-%m-%d %H:00"),
        "speed_policy": "pause-or-1x only (never change speed)",
        "country_tag_filter": country_tag,
        "scenario": "ITA@1x CArmy+0x200 ↔ Instance+0x70 cross (no Post)",
        "pending": pending,
        "stage_count": stage,
        "drain": drain,
        "exec": exec_c,
        "allow_post": False,
    }


def read_cpdx_u32(b, base, addr, max_n=64):
    try:
        data = u64(b, addr)
        cap = i32(b, addr + 8)
        size = i32(b, addr + 12)
    except Exception:
        return None
    sentinel = base <= data < base + getattr(b, "image_size", 0x40000000)
    if data < 0x10000 or size <= 0 or size > max_n or sentinel:
        return None
    if size > max(cap, size) + 8:
        return None
    blob = try_read(b, data, size * 4)
    if not blob or len(blob) < size * 4:
        return None
    vals = [struct.unpack_from("<I", blob, i * 4)[0] for i in range(size)]
    return {"size": size, "cap": cap, "data": hex(data), "vals": vals}


def read_army_200(b, base, primary, country_tag):
    """Read CPdxArray at CArmy+0x200; filter tag-singleton FP."""
    arr = read_cpdx_u32(b, base, primary + 0x200, max_n=64)
    if not arr:
        return {"ok": False, "reason": "no_arr"}
    vals = arr["vals"]
    if len(vals) == 1 and country_tag is not None and vals[0] == country_tag:
        return {"ok": False, "reason": "tag_singleton_fp", "vals": vals}
    if not all(looks_like_province_id(v) for v in vals):
        return {"ok": False, "reason": "not_all_province_shaped", "vals": vals[:16]}
    return {
        "ok": True,
        "n": len(vals),
        "multi": len(vals) > 1,
        "province_ids": vals,
        "data": arr["data"],
        "cap": arr["cap"],
    }


def cross(a_ids, b_ids):
    sa, sb = set(a_ids or []), set(b_ids or [])
    if not sa or not sb:
        return {
            "n_a": len(sa),
            "n_b": len(sb),
            "overlap": [],
            "frac_a_in_b": None,
            "frac_b_in_a": None,
            "equal": False,
            "equal_as_sets": False,
            "a_subseq_of_b": False,
            "b_subseq_of_a": False,
        }

    def is_subseq(x, y):
        it = iter(y)
        return all(v in it for v in x)

    ov = sorted(sa & sb)
    return {
        "n_a": len(sa),
        "n_b": len(sb),
        "overlap": ov,
        "overlap_n": len(ov),
        "frac_a_in_b": len(ov) / len(sa) if sa else None,
        "frac_b_in_a": len(ov) / len(sb) if sb else None,
        "equal": list(a_ids) == list(b_ids),
        "equal_as_sets": sa == sb,
        "a_subseq_of_b": is_subseq(a_ids, b_ids),
        "b_subseq_of_a": is_subseq(b_ids, a_ids),
    }


def scan_handle_pairs(blob, want_indices: set[int]):
    """Find {type=0x33, index} pairs in blob for wanted army indices."""
    hits = []
    if not blob or len(blob) < 8:
        return hits
    want = set(want_indices)
    for off in range(0, len(blob) - 7, 4):
        typ, ix = struct.unpack_from("<II", blob, off)
        if typ == HANDLE_TYPE_ARMY and ix in want:
            hits.append({"off": hex(off), "type": typ, "index": ix})
    return hits


def scan_u32_ois(blob, ois: set[int]):
    hits = []
    if not blob:
        return hits
    for off in range(0, len(blob) - 3, 4):
        v = struct.unpack_from("<I", blob, off)[0]
        if v in ois:
            hits.append({"off": hex(off), "oi": v})
    return hits


def collect_armies(b, base, country_tag):
    rows = army_subjects.iter_armies_by_index(b, base, INDEX_LO, INDEX_HI, country_tag=country_tag)
    carmy_vt = base + CA_VT_RVA
    out = []
    for r in rows:
        vt = try_u64(b, r["army"])
        if vt != carmy_vt or not r.get("handle_ok") or not r.get("province_id_ok"):
            continue
        a200 = read_army_200(b, base, r["army"], country_tag)
        out.append({
            "index": r["index"],
            "handle": list(r["handle"]),
            "province_id": r["province_id"],
            "army": hex(r["army"]),
            "army_int": r["army"],
            "arr200": a200,
        })
    return out


def collect_instances(fy, b, base, ois):
    rows = []
    for oi in ois:
        try:
            inst = fy.read_inst70(b, base, oi)
        except Exception as e:
            rows.append({"oi": oi, "ok": False, "reason": str(e)})
            continue
        if not inst or not inst.get("vt_ok"):
            rows.append({"oi": oi, "ok": False, "inst": inst})
            continue
        a70 = inst.get("arr70") or {}
        a88 = inst.get("arr88") or {}
        u32s70 = a70.get("u32_stream") or []
        shaped = bool(a70.get("u32_all_province_shaped") and u32s70)
        # province ids from +0x88 CProvince*
        ptr_ids = [x for x in (a88.get("ptr_province_ids_sample") or []) if x is not None]
        # also full stream if available via size
        rows.append({
            "oi": oi,
            "ok": True,
            "inst": inst.get("inst"),
            "inst_int": inst.get("inst_int"),
            "og": inst.get("og"),
            "arr70_n": a70.get("size"),
            "arr70_shaped": shaped,
            "arr70": u32s70[:64] if shaped else u32s70[:16],
            "arr88_size": a88.get("size"),
            "arr88_ptr_kinds": a88.get("ptr_kinds"),
            "arr88_province_ids": ptr_ids[:64],
            "arr_e0_size": (inst.get("arr_e0") or {}).get("size"),
            "arr_100_size": (inst.get("arr_100") or {}).get("size"),
        })
    return rows


def membership_hunt(b, base, armies, instances):
    """RO: look for army-handle pairs inside Instance/OG blobs; oi u32s inside CArmy."""
    want = {a["index"] for a in armies}
    ois_ok = {r["oi"] for r in instances if r.get("ok")}
    inst_hits = []
    og_hits = []
    army_oi_hits = []

    for r in instances:
        if not r.get("ok"):
            continue
        inst_i = r.get("inst_int")
        og_hex = r.get("og")
        if inst_i:
            blob = try_read(b, inst_i, 0x400) or b""
            hs = scan_handle_pairs(blob, want)
            if hs:
                inst_hits.append({"oi": r["oi"], "inst": r["inst"], "hits": hs[:12]})
        if og_hex:
            try:
                og = int(og_hex, 16)
            except Exception:
                og = None
            if og:
                blob = try_read(b, og, 0x200) or b""
                hs = scan_handle_pairs(blob, want)
                if hs:
                    og_hits.append({"oi": r["oi"], "og": og_hex, "hits": hs[:12]})

    focus = [a for a in armies if a["arr200"].get("multi") or a["index"] in FOCUS_ARMIES]
    for a in focus:
        blob = try_read(b, a["army_int"], 0x800) or b""
        hs = scan_u32_ois(blob, ois_ok)
        # keep sparse unique offs
        uniq = []
        seen = set()
        for h in hs:
            key = (h["oi"], h["off"])
            if key in seen:
                continue
            seen.add(key)
            uniq.append(h)
        if uniq:
            army_oi_hits.append({"army": a["index"], "oi_u32_hits": uniq[:24]})

    return {
        "instance_contains_focus_army_handle": inst_hits,
        "og_contains_focus_army_handle": og_hits,
        "carmy_contains_oi_u32": army_oi_hits,
        "note": "Heuristic blob scans only; hits are candidate links, not demangled fields.",
    }


def main() -> int:
    assert allow_post() is False, "allow_post must stay False"
    pid = find_pid()
    shanghai = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
    err = None
    live = {"pid": pid}
    armies = []
    instances = []
    crosses = []
    membership = {}
    best = None

    if not pid:
        err = "no hoi4 pid"
    else:
        try:
            b = Backend(pid)
            base = int(b.image_base)
            tag = player_tag(b, base)
            live = live_meta(b, base, pid, tag)
            fy = load_fy()
            armies = collect_armies(b, base, tag)
            # Prefer wide OI set for denser cross; seed always included
            instances = collect_instances(fy, b, base, WIDE_OIS)
            membership = membership_hunt(b, base, armies, instances)

            multi = [a for a in armies if a["arr200"].get("ok") and a["arr200"].get("multi")]
            shaped = [r for r in instances if r.get("ok") and r.get("arr70_shaped")]

            for a in multi:
                ids200 = a["arr200"]["province_ids"]
                row = {
                    "army": a["index"],
                    "province_id": a["province_id"],
                    "arr200_n": a["arr200"]["n"],
                    "arr200": ids200,
                    "vs_70": [],
                    "vs_88": [],
                    "best_70": None,
                    "best_88": None,
                }
                best70 = None
                best88 = None
                for r in shaped:
                    xr70 = cross(ids200, r["arr70"])
                    entry70 = {"oi": r["oi"], "arr70_n": r["arr70_n"], **xr70}
                    row["vs_70"].append(entry70)
                    score = (xr70.get("overlap_n") or 0, xr70.get("frac_a_in_b") or 0)
                    if best70 is None or score > best70[0]:
                        best70 = (score, entry70)
                    if r.get("arr88_province_ids"):
                        xr88 = cross(ids200, r["arr88_province_ids"])
                        entry88 = {"oi": r["oi"], "arr88_n": len(r["arr88_province_ids"]), **xr88}
                        row["vs_88"].append(entry88)
                        score88 = (xr88.get("overlap_n") or 0, xr88.get("frac_a_in_b") or 0)
                        if best88 is None or score88 > best88[0]:
                            best88 = (score88, entry88)
                # keep only top overlaps in compact form
                row["vs_70"] = sorted(row["vs_70"], key=lambda x: -(x.get("overlap_n") or 0))[:8]
                row["vs_88"] = sorted(row["vs_88"], key=lambda x: -(x.get("overlap_n") or 0))[:8]
                row["best_70"] = best70[1] if best70 else None
                row["best_88"] = best88[1] if best88 else None
                crosses.append(row)
                if best is None:
                    best = row
                else:
                    bn = (best.get("best_70") or {}).get("overlap_n") or 0
                    cn = (row.get("best_70") or {}).get("overlap_n") or 0
                    if cn > bn:
                        best = row

            live = live_meta(b, base, pid, tag)
        except Exception as e:
            err = str(e)

    multi_n = sum(1 for a in armies if a.get("arr200", {}).get("multi"))
    shaped_n = sum(1 for r in instances if r.get("ok") and r.get("arr70_shaped"))
    any_overlap = any((c.get("best_70") or {}).get("overlap_n", 0) > 0 for c in crosses)
    any_equal = any((c.get("best_70") or {}).get("equal") or (c.get("best_70") or {}).get("equal_as_sets") for c in crosses)
    any_subseq = any(
        (c.get("best_70") or {}).get("a_subseq_of_b") or (c.get("best_70") or {}).get("b_subseq_of_a")
        for c in crosses
    )
    mem_inst = len(membership.get("instance_contains_focus_army_handle") or [])
    mem_og = len(membership.get("og_contains_focus_army_handle") or [])

    if err and not armies:
        result = "CROSS_200_VS_70_NO_LIVE"
    elif any_equal:
        result = "CROSS_200_VS_70_EQUAL_HIT"
    elif any_subseq and any_overlap:
        result = "CROSS_200_VS_70_SUBSEQ_HIT"
    elif any_overlap:
        result = "CROSS_200_VS_70_PARTIAL_OVERLAP"
    elif multi_n and shaped_n:
        result = "CROSS_200_VS_70_NO_OVERLAP"
    elif multi_n:
        result = "CROSS_200_PRESENT_INSTANCE70_THIN"
    else:
        result = "CROSS_200_VS_70_HONEST_EMPTY"

    next_blocker = (
        "NON-Post: gate CLOSED; human midflight CMove hex OR human SAFE Post for Strategic "
        "ring_embed; retry GitHub push when auth reachable — still NO ALLOW_POST"
    )
    if result == "CROSS_200_VS_70_NO_OVERLAP":
        next_blocker = (
            "NON-Post: CArmy+0x200 ⊀ Instance+0x70 this window (RO ceiling on link) — "
            "optional membership via Assign stage sight OR named movement_dest hunt; "
            "human midflight CMove / SAFE Post for ring_embed; push when GitHub reachable; still NO ALLOW_POST"
        )
    elif any_overlap:
        next_blocker = (
            "NON-Post: deepen +0x200↔+0x70 overlap semantics (membership/Assign link) OR "
            "human midflight CMove hex / SAFE Post for ring_embed; push when reachable — still NO ALLOW_POST"
        )

    rep = {
        "phase": "2gn",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "captured_at_shanghai": shanghai,
        "allow_post": False,
        "executed_2fb_recipe": False,
        "executed_2gk_recipe": False,
        "tool_gate": "CLOSED",
        "result": result,
        "error": err,
        "live": live,
        "counts": {
            "carmy_rows": len(armies),
            "arr200_multi": multi_n,
            "instance_ok": sum(1 for r in instances if r.get("ok")),
            "instance_70_shaped": shaped_n,
            "cross_rows": len(crosses),
            "any_overlap_70": any_overlap,
            "any_equal_70": any_equal,
            "membership_inst_hits": mem_inst,
            "membership_og_hits": mem_og,
        },
        "armies_200_multi": [
            {
                "index": a["index"],
                "province_id": a["province_id"],
                "n": a["arr200"]["n"],
                "province_ids": a["arr200"]["province_ids"],
            }
            for a in armies
            if a.get("arr200", {}).get("multi")
        ],
        "instances_70_shaped": [
            {
                "oi": r["oi"],
                "arr70_n": r["arr70_n"],
                "arr70": r["arr70"][:24],
                "arr88_province_ids": (r.get("arr88_province_ids") or [])[:24],
            }
            for r in instances
            if r.get("ok") and r.get("arr70_shaped")
        ],
        "crosses": crosses,
        "best_cross": best,
        "membership": membership,
        "works": [
            "CArmy+0x200 multi re-read (tag-FP filtered)",
            "Instance+0x70/+0x88 province streams on wide OI seed",
            "cross metrics equal/set/subseq/overlap",
            "heuristic membership blob scans (Instance/OG/CArmy)",
        ],
        "stubbed": [
            "named demangled movement_dest",
            "proven army↔OI membership field",
            "in-process ring_embed",
            "2fb/2gk execute",
            "ALLOW_POST",
            "tool-gate",
            "CMove midflight hex",
            "Post inject",
        ],
        "next_shortest_blocker": next_blocker,
        "sha_base": "2c3f022",
    }
    OUT.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2gn",
                "result": result,
                "allow_post": False,
                "live": live,
                "arr200_multi": multi_n,
                "instance_70_shaped": shaped_n,
                "any_overlap_70": any_overlap,
                "best_overlap_n": (best or {}).get("best_70", {}) and (best.get("best_70") or {}).get("overlap_n"),
                "best_army": (best or {}).get("army"),
                "best_oi": ((best or {}).get("best_70") or {}).get("oi"),
                "membership_inst_hits": mem_inst,
                "membership_og_hits": mem_og,
                "next_shortest_blocker": next_blocker,
                "sha_base": "2c3f022",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    # doc
    b70 = (best or {}).get("best_70") or {}
    lines = [
        "# Phase 2gn — CArmy+0x200 ↔ Instance+0x70/+0x88 cross (RO)",
        "",
        f"**Result:** `{result}`  ",
        f"**Live:** pid {live.get('pid')} · {live.get('ui_date')} · hours={live.get('hours')} · tag={live.get('country_tag_filter')}  ",
        f"**+0x200 multi armies:** {multi_n} · **Instance+0x70 shaped:** {shaped_n} · **any overlap:** {any_overlap}  ",
        f"**Best +0x70 cross:** army {best.get('army') if best else None} ↔ oi {b70.get('oi')} · overlap_n={b70.get('overlap_n')} · frac_a_in_b={b70.get('frac_a_in_b')}  ",
        f"**Membership heuristic:** Instance hits={mem_inst} · OG hits={mem_og}  ",
        "",
        "**allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb/2gk **NOT executed**",
        "",
        "## Method",
        "",
        "1. Re-read ITA CArmy `+0x200` CPdxArray<u32> (filter country-tag singletons).",
        "2. Resolve wide OI set → `COrderInstance` via OG+0x98; read `+0x70` u32 / `+0x88` CProvince* ids.",
        "3. Cross each multi `+0x200` vs each shaped `+0x70` / `+0x88` (equal / set / subseq / overlap).",
        "4. Heuristic membership: scan Instance/OG blobs for `{0x33, army_ix}`; scan CArmy for oi u32s.",
        "",
        "## Semantics (this window)",
        "",
    ]
    if any_equal:
        lines.append("- **HIT:** at least one `+0x200` equals an Instance`+0x70` stream (set or exact).")
    elif any_subseq and any_overlap:
        lines.append("- **PARTIAL:** subsequence/overlap between `+0x200` and some `+0x70` — not identity.")
    elif any_overlap:
        lines.append("- **PARTIAL overlap only** — not equal/subseq identity; do **not** name `+0x200` as Instance path.")
    elif multi_n and shaped_n:
        lines.append(
            "- **NO OVERLAP** between any multi `CArmy+0x200` and any shaped Instance`+0x70` "
            "(extends 2fy `inst70_no_overlap` specifically for the 2gm `+0x200` candidate)."
        )
        lines.append("- `+0x200` remains a **province-id candidate array**, not proven order/front path (`+0x70`).")
    else:
        lines.append("- Thin sample — honest empty / incomplete.")
    lines += [
        "",
        "## Works",
        "",
        "- CArmy+0x200 multi re-read + Instance+0x70/+0x88 cross metrics",
        "- Heuristic army↔OI membership blob scans",
        "",
        "## Stubbed / HARD_DENY",
        "",
        "- named demangled `movement_dest` / proven membership field",
        "- ring_embed · Post · ALLOW_POST · tool-gate · 2fb/2gk execute · CMove midflight hex",
        "",
        f"**Next shortest blocker (NON-Post):** {next_blocker}",
        "",
        "Script: `scripts/phase2gn_200_vs_70_cross.py`",
        "",
        f"*Phase 2gn · {shanghai} Asia/Shanghai*",
        "",
    ]
    DOC.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({
        "result": result,
        "live": live,
        "multi": multi_n,
        "shaped70": shaped_n,
        "any_overlap": any_overlap,
        "best": {"army": (best or {}).get("army"), "oi": b70.get("oi"), "overlap_n": b70.get("overlap_n")},
        "mem_inst": mem_inst,
        "mem_og": mem_og,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
