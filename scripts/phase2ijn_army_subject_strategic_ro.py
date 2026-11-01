#!/usr/bin/env python3
"""Phase 2ijn NON-Post: ITA army-subject / Strategic recipe RO + G1–G6 agent matrix.

Live RO only. NO Post / Instant / PATH densify / midflight / ring_embed exec /
tool-gate / ask ALLOW_POST. org/str floats @0x520/0x6ec remain HYPOTHESIS (not invented).
"""
from __future__ import annotations

import importlib.util
import json
import struct
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import post_abi
from army_subjects import (
    cancel_movement_recipe,
    iter_armies_by_index,
    move_action_recipe,
    strategic_redeploy_recipe,
    support_attack_recipe,
)
from config import allow_post
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2ijn_army_subject_strategic_ro.json"
SUMMARY = ROOT / "reports" / "phase2ijn_army_subject_strategic_ro_summary.json"
DOC = ROOT / "docs" / "PHASE2IJN_ARMY_SUBJECT_STRATEGIC_RO.md"

GS_YEAR = 0x478
GS_DAY = 0x484
# Proven CArmy fields only — do NOT invent org/str
CA_HANDLE = 0x18
CA_PROVINCE_ID = 0x28
CA_COUNTRY_TAG = 0x1E0
CA_PROVINCE_PTR = 0x1F0
# Hypothesis offsets — documented as NOT proven
HYP_ORG_STR_A = 0x520
HYP_ORG_LIKE = 0x6EC


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def i32(b, a):
    return struct.unpack("<i", b.read(a, 4))[0]


def f32(b, a):
    return struct.unpack("<f", b.read(a, 4))[0]


def try_u32(b, a):
    try:
        return u32(b, a)
    except Exception:
        return None


def continuum_live(b, base, pid, tag, scenario):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    year = i32(b, gs + GS_YEAR)
    day_index = i32(b, gs + GS_DAY)
    ui = None
    if 1 <= year <= 3000 and 0 <= day_index < 400:
        try:
            ui = (datetime(year, 1, 1) + timedelta(days=int(day_index))).strftime("%Y-%m-%d")
        except Exception:
            ui = None
    pending = stage = drain = exec_c = None
    sess = server = None
    try:
        sess = u64(b, base + post_abi.G_SESSION)
        server = u64(b, sess + post_abi.CSession_SERVER) if sess else None
        if server:
            pending = try_u32(b, server + post_abi.CDummyServer_PENDING + 0x10)
        stage = try_u32(b, sess + post_abi.CSession_STAGE_COUNT) if sess else None
        drain = try_u32(b, sess + post_abi.CSession_DRAIN_COUNTER) if sess else None
        exec_c = try_u32(b, sess + post_abi.CSession_EXEC_COUNTER) if sess else None
    except Exception:
        pass
    clock_class = "CONTINUOUS" if not (year == 1936 and day_index < 48) else "RELOAD_OR_NEW_CAMPAIGN"
    return {
        "pid": pid,
        "year": year,
        "day_index": day_index,
        "ui_date": ui,
        "clock_class": clock_class,
        "clock_source": "GS+0x478 year + GS+0x484 day_index",
        "speed_policy": "pause-or-1x only (never write speed beyond pause/1x)",
        "country_tag_filter": tag,
        "scenario": scenario,
        "session": hex(sess) if sess else None,
        "server": hex(server) if server else None,
        "pending": pending,
        "stage_count": stage,
        "drain": drain,
        "exec": exec_c,
        "allow_post": False,
    }


def player_tag(b, base):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    return i32(b, gs + 0x518)


def scan_ita_armies(b, base, tag: int) -> list[dict]:
    rows: list[dict] = []
    for lo in range(0, 5000, 500):
        rows.extend(iter_armies_by_index(b, base, lo, lo + 500, country_tag=tag))
    return rows


def hyp_float_snapshot(b, army_ptr: int) -> dict:
    """Read hyp floats; status remains HYPOTHESIS — do not invent field names."""
    try:
        a = f32(b, army_ptr + HYP_ORG_STR_A)
        c = f32(b, army_ptr + HYP_ORG_LIKE)
    except Exception as e:
        return {"status": "READ_FAIL", "error": str(e)}
    return {
        "status": "HYPOTHESIS_ONLY",
        "off_0x520_float": a,
        "off_0x6ec_float": c,
        "note": "NOT proven org/str; 2ct REJECTED_AS_CARMY_ORG; do not invent names",
    }


def main() -> int:
    assert allow_post() is False, "allow_post must stay False"
    # Ensure env cannot sneak Post
    import os

    os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
    assert allow_post() is False

    pid = find_pid()
    if not pid:
        raise SystemExit("HOI4_DEAD — relaunch needed")
    b = Backend(pid)
    base = b.image_base
    tag = player_tag(b, base)
    scenario = "ITA@1x army-subject + Strategic recipe RO (no Post)"

    s0 = continuum_live(b, base, pid, tag, scenario)
    time.sleep(1.5)
    s1 = continuum_live(b, base, pid, tag, scenario)
    calendar_ok = (
        s1["clock_class"] == "CONTINUOUS"
        and (s1["drain"] or 0) >= (s0["drain"] or 0)
        and (s1["exec"] or 0) >= (s0["exec"] or 0)
    )

    rows = scan_ita_armies(b, base, tag)
    handle_ok_n = sum(1 for r in rows if r.get("handle_ok"))
    prov_ok_n = sum(1 for r in rows if r.get("province_id_ok"))
    all_subject_ok = len(rows) > 0 and handle_ok_n == len(rows) and prov_ok_n == len(rows)

    # Sample up to 8 armies for recipes + hyp floats
    sample = rows[:8]
    sample_out = []
    recipes = []
    for r in sample:
        army = r["army"]
        # cross-check province ptr @ proven CA_PROVINCE 0x1F0
        try:
            pref_direct = u64(b, army + CA_PROVINCE_PTR)
        except Exception:
            pref_direct = None
        hyp = hyp_float_snapshot(b, army)
        row = {
            "index": r["index"],
            "handle": list(r["handle"]),
            "army": hex(army),
            "province_id": r["province_id"],
            "province": hex(r["province"]) if r["province"] else None,
            "province_ptr_0x1f0": hex(pref_direct) if pref_direct else None,
            "province_ptr_match_resolve": (pref_direct == r["province"]) if pref_direct and r["province"] else False,
            "country_tag": r["country_tag"],
            "handle_ok": r["handle_ok"],
            "province_id_ok": r["province_id_ok"],
            "org_str_hyp": hyp,
        }
        sample_out.append(row)
        # Strategic dest = same province (redeploy-no-op shape) — docs only
        dest = int(r["province_id"])
        recipes.append(
            {
                "army_index": r["index"],
                "strategic": strategic_redeploy_recipe(r, dest),
                "move_action": move_action_recipe(r),
                "support_attack": support_attack_recipe(r, dest),
            }
        )

    cancel_rec = cancel_movement_recipe(sample) if sample else None

    gates = {
        "G1": {
            "state": "ACCEPTABLE",
            "via": "Strategic-only (2ijj)",
            "note": "CMove midflight hex still STUBBED; Strategic path accepted",
        },
        "G2": {
            "state": "RO_PREP_HIT_LIVE_STUBBED",
            "via": "2ijk INLINE_BLOB + SAFE needs",
            "note": "live ring_embed execute STUBBED",
        },
        "G3": {"state": "PARKED", "via": "peacetime Instant", "note": "no Instant empty re-poll"},
        "G4": {
            "state": "HARD_DENY_UNTIL_HUMAN",
            "via": "CLAUSEWITZ_ALLOW_POST=1 once",
            "note": "executor cannot flip",
        },
        "G5": {"state": "CLOSED_NOT_OPENED", "via": "tool-gate + NEVER_POST after G4"},
        "G6": {
            "state": "FORBIDDEN_NOW",
            "via": "ONE Strategic Post @1x after G4+G5",
            "note": "this slice did NOT Post",
        },
    }

    proven_fields = {
        "CA_HANDLE": hex(CA_HANDLE),
        "CA_PROVINCE_ID": hex(CA_PROVINCE_ID),
        "CA_COUNTRY_TAG": hex(CA_COUNTRY_TAG),
        "CA_PROVINCE_PTR": hex(CA_PROVINCE_PTR),
        "HANDLE_TYPE_ARMY": 0x33,
        "status": "PROVEN_LIVE",
    }
    hyp_fields = {
        "CArmy+0x520": "HYPOTHESIS float (not proven org/str)",
        "CArmy+0x6ec": "HYPOTHESIS float (not proven org)",
        "status": "NOT_INVENTED",
    }

    result_code = (
        "ARMY_SUBJECT_STRATEGIC_RO_HIT"
        if all_subject_ok and calendar_ok and allow_post() is False
        else "ARMY_SUBJECT_STRATEGIC_RO_PARTIAL"
    )

    report = {
        "phase": "2ijn",
        "result": result_code,
        "allow_post": False,
        "posting": "DISABLED",
        "hard_rules": [
            "no Instant empty / Inst70/ARR88/tri70 poll",
            "no PATH/OG50-only densify",
            "no long midflight empty poll",
            "no Post inject / 2fb/2gk / tool-gate / ring_embed live",
            "no ask ALLOW_POST / no invent field names",
            "org/str @0x520/0x6ec remain HYPOTHESIS",
        ],
        "live_s0": s0,
        "live_s1": s1,
        "calendar_ok": calendar_ok,
        "drain_delta": (s1["drain"] or 0) - (s0["drain"] or 0),
        "exec_delta": (s1["exec"] or 0) - (s0["exec"] or 0),
        "army_subject": {
            "country_tag_filter": tag,
            "scan_range": "0..5000 step 500",
            "count": len(rows),
            "handle_ok_count": handle_ok_n,
            "province_id_ok_count": prov_ok_n,
            "all_subject_ok": all_subject_ok,
            "indices": [r["index"] for r in rows],
            "unique_province_ids": sorted({r["province_id"] for r in rows}),
            "sample": sample_out,
        },
        "proven_carmy_fields": proven_fields,
        "hypothesis_not_invented": hyp_fields,
        "strategic_recipes_sample": recipes,
        "cancel_recipe_sample": cancel_rec,
        "gates_g1_g6": gates,
        "path_c_honesty": {
            "baseline_band": "~60-62%",
            "this_slice_pp": "<=+1-2pp perception confidence (army subject RO)",
            "crossed_70": False,
            "note": "~70% NOT crossed while G2 live / G4+ block Post",
        },
        "next_shortest_blocker": "Human G4 CLAUSEWITZ_ALLOW_POST=1 (executor cannot flip) → G5 tool-gate → G2 live ring_embed / G6 one Strategic Post @1x",
        "timestamp_asia_shanghai": datetime.now().strftime("%Y-%m-%d %H:%M:%S Asia/Shanghai"),
    }

    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2ijn",
                "result": result_code,
                "allow_post": False,
                "pid": pid,
                "ui_date": s1["ui_date"],
                "day_index": s1["day_index"],
                "clock_class": s1["clock_class"],
                "drain": s1["drain"],
                "exec": s1["exec"],
                "army_count": len(rows),
                "all_subject_ok": all_subject_ok,
                "calendar_ok": calendar_ok,
                "crossed_70": False,
                "next": report["next_shortest_blocker"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    md = "\n".join(
        [
            "# Phase 2ijn — ITA army-subject + Strategic recipe RO",
            "",
            f"**Result:** `{result_code}`  ",
            "**allow_post:** **False** · Post **NOT** called · ring_embed live **STUBBED** · Instant **PARKED** · never 5x",
            "",
            "## Live clock / queue",
            "",
            f"pid {pid} · {s1['clock_class']} · day_index={s1['day_index']} ui={s1['ui_date']} ·  ",
            f"drain={s1['drain']} exec={s1['exec']} pending={s1['pending']} · calendar_ok={calendar_ok}",
            "",
            "## Army subject RO (proven fields only)",
            "",
            f"- country_tag_filter={tag} (player GS+0x518)",
            f"- armies_found={len(rows)} · handle_ok={handle_ok_n} · province_id_ok={prov_ok_n} · all_subject_ok={all_subject_ok}",
            f"- Proven: `CA_HANDLE@+0x18` · `CA_PROVINCE_ID@+0x28` · `CA_COUNTRY_TAG@+0x1E0` · `CA_PROVINCE_PTR@+0x1F0`",
            f"- Unique provinces: {len(report['army_subject']['unique_province_ids'])}",
            "- Strategic / Move / SupportAttack / Cancel **recipes** built from live rows — `posting: DISABLED`",
            "",
            "## Hypothesis — NOT invented",
            "",
            "- `CArmy+0x520` / `+0x6ec` floats remain **HYPOTHESIS_ONLY** (2ct REJECTED_AS_CARMY_ORG)",
            "- Do **not** feed agent as org/str until proven",
            "",
            "## G1–G6 agent matrix (catalog)",
            "",
            "| Gate | State | Note |",
            "| --- | --- | --- |",
            "| G1 | ACCEPTABLE Strategic-only | 2ijj; CMove hex still STUBBED |",
            "| G2 | RO prep HIT · live STUBBED | 2ijk INLINE_BLOB |",
            "| G3 | PARKED peacetime Instant | no empty re-poll |",
            "| G4 | HARD_DENY until human | CLAUSEWITZ_ALLOW_POST=1; executor cannot flip |",
            "| G5 | CLOSED_NOT_OPENED | tool-gate after G4 |",
            "| G6 | FORBIDDEN now | ONE Strategic Post @1x after G4+G5 |",
            "",
            "## Path C honesty (t50u)",
            "",
            "~60–62% baseline band; this army-subject RO ≤+1–2pp confidence, **not** +10pp. **~70% NOT crossed.**",
            "",
            "## Next",
            "",
            "Human G4 → G5 → G2 live / G6. Instant PARKED. No densify/poll churn.",
            "",
            "*Phase 2ijn · 2026-11-01 Asia/Shanghai*",
            "",
        ]
    )
    DOC.write_text(md, encoding="utf-8")

    print(json.dumps({"result": result_code, "armies": len(rows), "all_ok": all_subject_ok, "calendar_ok": calendar_ok, "allow_post": allow_post(), "ui": s1["ui_date"], "day": s1["day_index"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
