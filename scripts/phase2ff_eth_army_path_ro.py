#!/usr/bin/env python3
"""Phase 2ff: ETH live army-subject observe + CArmy path-vector RO polish.

ONE RO slice. No Post / no ALLOW_POST / no 2fb recipe / no tool-gate / never 5x.
Builds Move/Strategic/SupportAttack subject recipes from live ETH CArmy rows.
"""
from __future__ import annotations

import json
import struct
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import army_subjects
import cmd_layout
import post_abi
from config import allow_post
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2ff_eth_army_path_ro.json"
SUMMARY = ROOT / "reports" / "phase2ff_summary.json"
DOC = ROOT / "docs" / "PHASE2FF_ETH_ARMY_PATH_RO.md"
NOTE = ROOT / "docs" / "PHASE2FF_PATH_VECTOR_NOTE.md"

CA_VT_RVA = 0x29D6D68
ETH_TAG = 15  # player_tag in ETH@1x session (2fa)


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


def read_u32_vector(b, begin, end, cap, max_n=64):
    if not begin or not end or end < begin:
        return None
    nbytes = end - begin
    if nbytes % 4 != 0 or nbytes > max_n * 4:
        return None
    if cap and cap < end:
        return None
    blob = try_read(b, begin, nbytes)
    if not blob or len(blob) != nbytes:
        return None
    return list(struct.unpack("<" + "I" * (nbytes // 4), blob))


def live_meta(b, base, pid):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    hours = i32(b, gs + 0x484)
    d = datetime(1936, 1, 1, 0, 0) + timedelta(hours=int(hours))
    return {
        "pid": pid,
        "hours": hours,
        "ui_date": d.strftime("%Y-%m-%d %H:00"),
        "speed_policy": "pause-or-1x only (never change speed)",
        "country_tag_filter": ETH_TAG,
        "scenario": "ETH@1x army-subject+path RO (no Post)",
    }


def deepen_paths(b, base, rows):
    carmy_vt = base + CA_VT_RVA
    deepened = []
    nonempty = 0
    for r in rows:
        obj = r["army"]
        vt = try_u64(b, obj)
        if vt and vt != carmy_vt:
            continue
        blob = try_read(b, obj, 0x800) or b""
        cands = []
        for off in range(0x40, min(len(blob) - 24, 0x780), 8):
            begin, end, cap = struct.unpack_from("<QQQ", blob, off)
            if begin < 0x10000 or end < begin:
                continue
            vals = read_u32_vector(b, begin, end, cap, max_n=32)
            if not vals or not all(looks_like_province_id(v) for v in vals):
                continue
            cands.append({
                "off": hex(off),
                "begin": hex(begin),
                "end": hex(end),
                "cap": hex(cap),
                "n": len(vals),
                "province_ids": vals,
                "matches_current_only": vals == [r["province_id"]],
            })
        actionish = []
        for off in (0x100, 0x120, 0x140, 0x180, 0x200, 0x280, 0x300, 0x380, 0x400, 0x480, 0x500, 0x580):
            if off + 0x40 > len(blob):
                continue
            psz = struct.unpack_from("<I", blob, off + 0x24)[0]
            path_sz = struct.unpack_from("<I", blob, off + 0x3C)[0]
            parr = struct.unpack_from("<Q", blob, off + 0x18)[0]
            path_arr = struct.unpack_from("<Q", blob, off + 0x30)[0]
            if 0 < psz <= 32 and parr > 0x10000:
                vals = read_u32_vector(b, parr, parr + 4 * psz, parr + 4 * psz, max_n=32)
                if vals and all(looks_like_province_id(v) for v in vals):
                    actionish.append({"kind": "province_arr_like", "off": hex(off), "ids": vals})
            if 0 < path_sz <= 32 and path_arr > 0x10000:
                vals = read_u32_vector(b, path_arr, path_arr + 4 * path_sz, path_arr + 4 * path_sz, max_n=32)
                if vals and all(looks_like_province_id(v) for v in vals):
                    actionish.append({"kind": "path_arr_like", "off": hex(off), "ids": vals})
        status = "nonempty_candidate" if (cands or actionish) else "empty_or_absent"
        if cands or actionish:
            nonempty += 1
        deepened.append({
            "index": r["index"],
            "handle": list(r["handle"]),
            "handle_ok": r["handle_ok"],
            "province_id": r["province_id"],
            "province_id_ok": r["province_id_ok"],
            "army": hex(obj),
            "vt_rva": hex(vt - base) if vt else None,
            "vector_cands": cands[:6],
            "actionish_cands": actionish[:6],
            "movement_dest_status": status,
        })
    return {
        "carmy_rows": len(deepened),
        "movement_dest_nonempty_count": nonempty,
        "armies": deepened,
        "note": "Candidates only; empty means do NOT invent destinations. ETH@1x may show midflight paths.",
    }


def recipes_from_subjects(rows, paths):
    """Document-only recipes from live subjects. Never posts."""
    by_ix = {a["index"]: a for a in paths.get("armies", [])}
    out = []
    for r in rows[:12]:
        ix = r["index"]
        path = by_ix.get(ix) or {}
        dest = r["province_id"]
        # Prefer a multi-province candidate dest if present (not inventing — only using observed ids)
        for c in path.get("vector_cands") or []:
            ids = c.get("province_ids") or []
            if len(ids) >= 2:
                dest = ids[-1]
                break
        out.append({
            "index": ix,
            "handle": list(r["handle"]),
            "source_province": r["province_id"],
            "movement_dest_status": path.get("movement_dest_status", "unknown"),
            "move_recipe": army_subjects.move_action_recipe(r),
            "strategic_recipe": army_subjects.strategic_redeploy_recipe(r, dest, clear=1, move_priority=2),
            "support_attack_recipe": army_subjects.support_attack_recipe(r, dest),
            "path_confidence": {
                "move_needs": "province_arr@+0x18 + path_arr@+0x30 game allocs (NOT observed as filled embeds here)",
                "strategic_cheaper": "scalar province @ embed+0x18 from live CArmy handle+dest",
                "support_attack": "handle@+0x28 + target_province@+0x30",
                "live_path_vectors": path.get("movement_dest_status"),
                "posting": "DISABLED",
            },
        })
    return out


def write_docs(rep: dict) -> None:
    live = rep.get("live") or {}
    paths = rep.get("path_deepen") or {}
    NOTE.write_text(
        "\n".join([
            "# Phase 2ff — CArmy path-vector / subject RO note",
            "",
            f"**Live:** pid {live.get('pid')} · {live.get('ui_date')} · hours={live.get('hours')} · ETH tag={ETH_TAG}",
            f"**Path nonempty armies:** {paths.get('movement_dest_nonempty_count')} / {paths.get('carmy_rows')}",
            "",
            "## Path confidence",
            "",
            "| path | needs | status |",
            "|------|-------|--------|",
            "| Ordinary CMove | province_arr + path_arr game allocs | live leaf sample STUBBED; subject handle/province READY |",
            "| StrategicRedeploy | army handle + scalar province | subject READY from live ETH CArmy |",
            "| SupportAttack | handle@+0x28 + target_province@+0x30 | subject READY (recipe only) |",
            "",
            "Empty movement_dest ⇒ do **not** invent destinations. Candidates (if any) are province-id vectors only.",
            "",
            "allow_post **False**. 2fb recipe **not** executed. tool-gate **CLOSED**.",
            "",
        ]),
        encoding="utf-8",
    )
    DOC.write_text(
        "\n".join([
            "# Phase 2ff — ETH army-subject + path-vector RO",
            "",
            f"**Result:** `{rep.get('result')}`  ",
            "**allow_post:** **False** · tool-gate **CLOSED** · never 5x · recipe **NOT executed**",
            "",
            "## Works",
            "",
            "- Live ETH CArmy subject observe (handle/province/tag)",
            "- CArmy path-vector candidate deepen (RO; no invent)",
            "- Move / Strategic / SupportAttack subject recipes from live rows",
            "- Path confidence note (Strategic cheaper than Move vectors)",
            "",
            "## Stubbed",
            "",
            "- in-process ring embed / Post / 2fb recipe exec",
            "- ordinary CMove live leaf sample",
            "- SAFE_POST / ALLOW_POST / tool-gate open",
            "",
            f"## Live",
            "",
            f"```json",
            f"{json.dumps(live, indent=2)}",
            f"```",
            "",
            f"**Next shortest blocker (NON-Post):** {rep.get('next_shortest_blocker')}",
            "",
            "Script: `scripts/phase2ff_eth_army_path_ro.py`",
            "",
        ]),
        encoding="utf-8",
    )


def main() -> int:
    assert allow_post() is False, "allow_post must stay False"
    pid = find_pid()
    live = {"pid": pid}
    rows = []
    paths = {"carmy_rows": 0, "movement_dest_nonempty_count": 0, "armies": [], "note": "no live"}
    recipes = []
    err = None
    if not pid:
        err = "no hoi4 pid"
    else:
        try:
            b = Backend(pid)
            base = int(b.image_base)
            live = live_meta(b, base, pid)
            rows = army_subjects.iter_armies_by_index(b, base, 1000, 1400, country_tag=ETH_TAG)
            # keep CArmy only
            carmy_vt = base + CA_VT_RVA
            carmy_rows = []
            for r in rows:
                vt = try_u64(b, r["army"])
                if vt == carmy_vt and r.get("handle_ok") and r.get("province_id_ok"):
                    carmy_rows.append(r)
            rows = carmy_rows
            paths = deepen_paths(b, base, rows)
            recipes = recipes_from_subjects(rows, paths)
        except Exception as e:
            err = str(e)

    result = "ETH_ARMY_SUBJECT_PATH_RO_DONE" if rows else "ETH_ARMY_SUBJECT_PATH_RO_PARTIAL"
    if err and not rows:
        result = "ETH_ARMY_SUBJECT_PATH_RO_NO_LIVE"

    next_blocker = (
        "NON-Post: ORDERS/front/retreat catalog factory_idx polish OR short ETH@1x stage sight for "
        "SupportAttack/Cancel leaf hex (no Post) — still HARD_DENY allow_post"
    )
    if paths.get("movement_dest_nonempty_count", 0) == 0:
        next_blocker = (
            "NON-Post: path vectors empty this tick — optional short @1x re-observe for nonempty "
            "movement_dest OR ORDERS factory_idx catalog fill; still NO ALLOW_POST"
        )

    rep = {
        "phase": "2ff",
        "ts": datetime.now(timezone.utc).isoformat(),
        "allow_post": False,
        "executed_2fb_recipe": False,
        "tool_gate": "CLOSED",
        "result": result,
        "error": err,
        "live": live,
        "subjects": {
            "country_tag": ETH_TAG,
            "carmy_ok_count": len(rows),
            "sample": [
                {
                    "index": r["index"],
                    "handle": list(r["handle"]),
                    "province_id": r["province_id"],
                    "province_id_ok": r["province_id_ok"],
                    "handle_ok": r["handle_ok"],
                }
                for r in rows[:16]
            ],
        },
        "path_deepen": {
            "carmy_rows": paths.get("carmy_rows"),
            "movement_dest_nonempty_count": paths.get("movement_dest_nonempty_count"),
            "note": paths.get("note"),
            "armies_head": (paths.get("armies") or [])[:8],
        },
        "subject_recipes_head": recipes[:6],
        "path_confidence": {
            "ARMY_MOVE_SUBJECTS": cmd_layout.ARMY_MOVE_SUBJECTS,
            "MOVE_action_fields": cmd_layout.MOVE["action"]["fields"],
            "STRATEGIC_action_fields": cmd_layout.STRATEGIC["action"]["fields"],
            "SUPPORT_ATTACK_fields": cmd_layout.SUPPORT_ATTACK.get("fields"),
            "note": "Strategic scalar province cheaper than Move path vectors for any future human-gated Post",
        },
        "works": [
            "live ETH CArmy subject observe (handle/province)",
            "path-vector candidate deepen (RO)",
            "Move/Strategic/SupportAttack recipes from live subjects",
            "path confidence note",
            "allow_post stays False; recipe not executed",
        ],
        "stubbed": [
            "in-process ring embed",
            "2fb recipe execution",
            "ordinary CMove live leaf",
            "SAFE_POST / ALLOW_POST",
            "self-MOVE",
            "tool-gate open",
            "Post inject",
        ],
        "next_shortest_blocker": next_blocker,
        "parent_sha_base": "b00a383",
    }

    OUT.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2ff",
                "result": result,
                "scenario": live.get("scenario", "ETH@1x"),
                "allow_post": False,
                "tool_gate": "CLOSED",
                "pid": live.get("pid"),
                "ui_date": live.get("ui_date"),
                "hours": live.get("hours"),
                "carmy_ok_count": len(rows),
                "movement_dest_nonempty_count": paths.get("movement_dest_nonempty_count"),
                "works": rep["works"],
                "stubbed": rep["stubbed"],
                "next_shortest_blocker": next_blocker,
                "parent_sha_base": "b00a383",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    write_docs(rep)
    print(json.dumps(json.loads(SUMMARY.read_text(encoding="utf-8")), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
