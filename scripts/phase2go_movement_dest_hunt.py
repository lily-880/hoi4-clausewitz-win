#!/usr/bin/env python3
"""Phase 2go: named movement_dest hunt on CArmy (RO).

ONE RO slice. No Post / no ALLOW_POST / no 2fb|2gk execute / never 5x.
String/RTTI needles + live scalar dest consistency vs CArmy+0x200[-1] / +0x2B4.
Document hits or honest empty. Single snapshot (no endless poll).
"""
from __future__ import annotations

import json
import struct
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import army_subjects
import post_abi
from config import allow_post
from pe import PE
from process import Backend, find_pid
from stringscan import find_ascii_all

OUT = ROOT / "reports" / "phase2go_movement_dest_hunt.json"
SUMMARY = ROOT / "reports" / "phase2go_summary.json"
DOC = ROOT / "docs" / "PHASE2GO_MOVEMENT_DEST_HUNT.md"

CA_VT_RVA = 0x29D6D68
CA_PROVINCE_ID = 0x28
CA_LAST_PATH_CAND = 0x2B4  # WINDOWS_OFFSETS soft — not demangled
CA_PATH200 = 0x200
INDEX_LO, INDEX_HI = 1000, 1600
GS_PLAYER_TAG = 0x518

# Needles: exact / substring-ish ASCII likely to appear if a named symbol/log exists
NEEDLES = [
    b"movement_dest",
    b"MovementDest",
    b"movement_destination",
    b"move_destination",
    b"MoveDestination",
    b"dest_province",
    b"destination_province",
    b"path_destination",
    b"m_movement_dest",
    b"m_destination",
    b"nDestination",
    b"nDestProvince",
    b"target_province",  # may hit many; classify separately
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


def try_read(b, a, n):
    try:
        return b.read(a, n)
    except Exception:
        return None


def looks_like_province_id(v: int) -> bool:
    return 1 <= v <= 20000


def player_tag(b, base):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    return i32(b, gs + GS_PLAYER_TAG)


def live_meta(b, base, pid, country_tag, image_path):
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
        "scenario": "ITA@1x named movement_dest hunt (no Post)",
        "image_path": image_path,
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
    blob = try_read(b, data, size * 4)
    if not blob or len(blob) < size * 4:
        return None
    vals = [struct.unpack_from("<I", blob, i * 4)[0] for i in range(size)]
    return vals


def string_hunt(image_path: str) -> dict:
    out = {"image_path": image_path, "needles": [], "error": None}
    try:
        pe = PE(image_path)
    except Exception as e:
        out["error"] = str(e)
        return out
    for needle in NEEDLES:
        try:
            rvas = find_ascii_all(pe, needle)
        except Exception as e:
            out["needles"].append({"needle": needle.decode("ascii", "replace"), "error": str(e)})
            continue
        # cap
        out["needles"].append({
            "needle": needle.decode("ascii", "replace"),
            "hit_count": len(rvas),
            "rvas_sample": [hex(r) for r in rvas[:8]],
            "strict_movement_dest_family": needle.lower() in (
                b"movement_dest", b"movementdest", b"movement_destination",
                b"move_destination", b"movedestination", b"m_movement_dest",
            ) or needle.startswith(b"movement_dest") or needle.startswith(b"MovementDest"),
        })
    # summary: any strict family hit?
    strict = [n for n in out["needles"] if n.get("strict_movement_dest_family") and n.get("hit_count", 0) > 0]
    loose = [n for n in out["needles"] if not n.get("strict_movement_dest_family") and n.get("hit_count", 0) > 0]
    out["strict_family_hits"] = len(strict)
    out["loose_family_hits"] = len(loose)
    out["named_symbol_found"] = len(strict) > 0
    return out


def collect_armies(b, base, country_tag):
    rows = army_subjects.iter_armies_by_index(b, base, INDEX_LO, INDEX_HI, country_tag=country_tag)
    carmy_vt = base + CA_VT_RVA
    out = []
    for r in rows:
        primary = r["army"]
        vt = try_u64(b, primary)
        if vt != carmy_vt or not r.get("handle_ok") or not r.get("province_id_ok"):
            continue
        cur = r["province_id"]
        path = read_cpdx_u32(b, base, primary + CA_PATH200, max_n=64)
        # filter tag singleton
        if path and len(path) == 1 and path[0] == country_tag:
            path = None
        if path and not all(looks_like_province_id(v) for v in path):
            path = None
        last200 = path[-1] if path and len(path) >= 1 else None
        soft_2b4 = try_u32(b, primary + CA_LAST_PATH_CAND)
        if soft_2b4 is not None and not looks_like_province_id(soft_2b4):
            soft_2b4 = None
        # scalar scan: u32 province-shaped != current; score if == last200
        blob = try_read(b, primary, 0x800) or b""
        scalar_hits = []
        for off in range(0x20, min(len(blob) - 3, 0x7FC), 4):
            # skip inside +0x200 CPdxArray header region vaguely
            v = struct.unpack_from("<I", blob, off)[0]
            if not looks_like_province_id(v):
                continue
            if v == cur:
                continue
            if country_tag is not None and v == country_tag:
                continue
            kind = "other_scalar"
            if last200 is not None and v == last200:
                kind = "eq_path200_last"
            if soft_2b4 is not None and v == soft_2b4 and off != CA_LAST_PATH_CAND:
                kind = "eq_2b4" if kind == "other_scalar" else kind + "+eq_2b4"
            if kind != "other_scalar":
                scalar_hits.append({"off": hex(off), "val": v, "kind": kind})
        out.append({
            "index": r["index"],
            "province_id": cur,
            "army": hex(primary),
            "path200_n": len(path) if path else 0,
            "path200_last": last200,
            "path200_sample": (path or [])[:12],
            "soft_2b4": soft_2b4,
            "soft_2b4_eq_path_last": (soft_2b4 is not None and last200 is not None and soft_2b4 == last200),
            "soft_2b4_eq_current": soft_2b4 == cur if soft_2b4 is not None else None,
            "dest_like_scalars": scalar_hits[:24],
        })
    return out


def rank_dest_offsets(armies):
    """Offsets that repeatedly equal path200[-1] across multi-path armies."""
    multi = [a for a in armies if a["path200_n"] > 1 and a["path200_last"] is not None]
    ctr = Counter()
    examples = defaultdict(list)
    for a in multi:
        for h in a["dest_like_scalars"]:
            if "eq_path200_last" in h["kind"]:
                ctr[h["off"]] += 1
                if len(examples[h["off"]]) < 3:
                    examples[h["off"]].append({"army": a["index"], "val": h["val"]})
    ranked = [
        {"off": off, "armies_agree": n, "multi_pool": len(multi), "examples": examples[off]}
        for off, n in ctr.most_common(12)
    ]
    # +0x2B4 agreement rate
    soft_agree = sum(1 for a in multi if a.get("soft_2b4_eq_path_last"))
    return {
        "multi_path_armies": len(multi),
        "soft_2b4_eq_path_last_count": soft_agree,
        "soft_2b4_eq_path_last_frac": (soft_agree / len(multi)) if multi else None,
        "scalar_offs_eq_path_last_ranked": ranked,
        "best_scalar_off": ranked[0]["off"] if ranked else None,
        "note": "Agreement ≠ demangled name; candidate dest scalar only.",
    }


def main() -> int:
    assert allow_post() is False, "allow_post must stay False"
    pid = find_pid()
    shanghai = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
    err = None
    live = {"pid": pid}
    strings = {}
    armies = []
    ranking = {}

    if not pid:
        err = "no hoi4 pid"
    else:
        try:
            b = Backend(pid)
            base = int(b.image_base)
            tag = player_tag(b, base)
            image_path = getattr(b, "image_path", "") or ""
            live = live_meta(b, base, pid, tag, image_path)
            strings = string_hunt(image_path) if image_path else {"error": "no image_path"}
            armies = collect_armies(b, base, tag)
            ranking = rank_dest_offsets(armies)
            live = live_meta(b, base, pid, tag, image_path)
        except Exception as e:
            err = str(e)

    multi_n = sum(1 for a in armies if a.get("path200_n", 0) > 1)
    named = bool((strings or {}).get("named_symbol_found"))
    soft_frac = (ranking or {}).get("soft_2b4_eq_path_last_frac")
    best_off = (ranking or {}).get("best_scalar_off")
    best_agree = 0
    if ranking.get("scalar_offs_eq_path_last_ranked"):
        best_agree = ranking["scalar_offs_eq_path_last_ranked"][0]["armies_agree"]

    if err and not armies:
        result = "MOVEMENT_DEST_HUNT_NO_LIVE"
    elif named:
        result = "MOVEMENT_DEST_NAMED_STRING_HIT"
    elif soft_frac is not None and soft_frac >= 0.8 and multi_n >= 2:
        result = "MOVEMENT_DEST_SOFT_2B4_AGREES_PATH_LAST"
    elif best_off and best_agree >= 2:
        result = "MOVEMENT_DEST_SCALAR_CANDIDATE_HIT"
    elif multi_n == 0:
        result = "MOVEMENT_DEST_HUNT_NO_MULTI_PATH"
    else:
        result = "MOVEMENT_DEST_NAMED_HONEST_EMPTY"

    next_blocker = (
        "NON-Post: gate CLOSED; human midflight CMove hex OR human SAFE Post for Strategic "
        "ring_embed; retry GitHub push when auth reachable — still NO ALLOW_POST"
    )
    if result in ("MOVEMENT_DEST_NAMED_HONEST_EMPTY", "MOVEMENT_DEST_HUNT_NO_MULTI_PATH"):
        next_blocker = (
            "NON-Post: named movement_dest still NOT_DEMANGLED (string empty; no stable demangled field) — "
            "optional Assign-stage membership sight; else human midflight CMove / SAFE Post for ring_embed; "
            "push when GitHub reachable; still NO ALLOW_POST"
        )
    elif result.startswith("MOVEMENT_DEST_SOFT") or result.startswith("MOVEMENT_DEST_SCALAR"):
        next_blocker = (
            f"NON-Post: deepen candidate dest scalar {best_off or '+0x2B4'} (still unnamed) OR "
            "Assign-stage membership / human CMove hex / SAFE Post for ring_embed; "
            "push when reachable — still NO ALLOW_POST"
        )

    rep = {
        "phase": "2go",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "captured_at_shanghai": shanghai,
        "allow_post": False,
        "executed_2fb_recipe": False,
        "executed_2gk_recipe": False,
        "tool_gate": "CLOSED",
        "result": result,
        "error": err,
        "live": live,
        "string_hunt": strings,
        "counts": {
            "carmy_rows": len(armies),
            "path200_multi": multi_n,
            "named_symbol_found": named,
            "soft_2b4_eq_path_last_frac": soft_frac,
            "best_scalar_off": best_off,
            "best_scalar_agree": best_agree,
        },
        "ranking": ranking,
        "armies_sample": [
            {k: a[k] for k in a if k != "dest_like_scalars"}
            | {"dest_like_scalars": a.get("dest_like_scalars", [])[:8]}
            for a in armies
            if a.get("path200_n", 0) > 0
        ][:16],
        "works": [
            "PE ASCII needle hunt for movement_dest family",
            "live CArmy+0x200 last vs +0x2B4 soft + scalar offset agreement",
            "honest empty if no demangled name",
        ],
        "stubbed": [
            "demangled named movement_dest field",
            "proven army↔OI membership",
            "in-process ring_embed",
            "2fb/2gk execute",
            "ALLOW_POST",
            "tool-gate",
            "CMove midflight hex",
            "Post inject",
        ],
        "next_shortest_blocker": next_blocker,
        "sha_base": "35fa0dc",
    }
    OUT.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2go",
                "result": result,
                "allow_post": False,
                "live": live,
                "named_symbol_found": named,
                "path200_multi": multi_n,
                "soft_2b4_eq_path_last_frac": soft_frac,
                "best_scalar_off": best_off,
                "best_scalar_agree": best_agree,
                "next_shortest_blocker": next_blocker,
                "sha_base": "35fa0dc",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    strict_hits = [
        n for n in (strings.get("needles") or [])
        if n.get("strict_movement_dest_family") and n.get("hit_count", 0) > 0
    ]
    lines = [
        "# Phase 2go — named movement_dest hunt (RO)",
        "",
        f"**Result:** `{result}`  ",
        f"**Live:** pid {live.get('pid')} · {live.get('ui_date')} · hours={live.get('hours')} · tag={live.get('country_tag_filter')}  ",
        f"**PE strings (strict movement_dest family):** {len(strict_hits)} needles with hits · named_symbol_found={named}  ",
        f"**+0x200 multi armies:** {multi_n} · **+0x2B4==path[-1] frac:** {soft_frac} · **best scalar:** {best_off} (agree {best_agree})  ",
        "",
        "**allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb/2gk **NOT executed**",
        "",
        "## Method",
        "",
        "1. ASCII needle hunt in `hoi4.exe` for `movement_dest` / `MoveDestination` / related.",
        "2. Live ITA CArmy: read `+0x200` path (tag-FP filtered), soft `+0x2B4`, scalar u32 scan for values == path[-1].",
        "3. Rank offsets by multi-army agreement — **agreement ≠ demangled name**.",
        "",
        "## Findings",
        "",
    ]
    if named:
        lines.append("- Strict family **string HIT** — still need field-offset proof before naming a member.")
    else:
        lines.append("- Strict `movement_dest` family strings: **HONEST EMPTY** (no demangled symbol evidence in PE ASCII).")
    if soft_frac is not None:
        lines.append(f"- Soft catalog `CArmy+0x2B4` == `+0x200[-1]`: **{soft_frac}** of multi-path armies (candidate dest scalar only).")
    if best_off:
        lines.append(f"- Best agreeing scalar off: `{best_off}` on {best_agree} multi-path armies (unnamed).")
    else:
        lines.append("- No scalar offset repeatedly echoed `+0x200[-1]` beyond noise this window.")
    lines += [
        "",
        "## Works",
        "",
        "- PE needle hunt + live dest-scalar consistency vs `+0x200`/`+0x2B4`",
        "",
        "## Stubbed / HARD_DENY",
        "",
        "- demangled named `movement_dest` member",
        "- ring_embed · Post · ALLOW_POST · tool-gate · 2fb/2gk · CMove midflight hex",
        "",
        f"**Next shortest blocker (NON-Post):** {next_blocker}",
        "",
        "Script: `scripts/phase2go_movement_dest_hunt.py`",
        "",
        f"*Phase 2go · {shanghai} Asia/Shanghai*",
        "",
    ]
    DOC.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({
        "result": result,
        "live": live,
        "named": named,
        "multi": multi_n,
        "soft_frac": soft_frac,
        "best_off": best_off,
        "best_agree": best_agree,
        "strict_string_hits": len(strict_hits),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
