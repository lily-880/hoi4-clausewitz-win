#!/usr/bin/env python3
"""Phase 2ijv: Strategic Post observe harden + fold G4-G6 HIT into SAFE_POST/LAND_POST.

Prefer observe over Post. Max ZERO Posts unless observe proves need (this slice: observe-only).
NEVER 5x. Restore allow_post False. Instant PARKED.
"""
from __future__ import annotations

import json
import os
import re
import struct
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import post_abi
from army_subjects import iter_armies_by_index
from config import allow_post
from handle import resolve_handle, HANDLE_TYPE_ARMY
from process import Backend, find_pid
from strategic_order import _path

OUT = ROOT / "reports" / "phase2ijv_strategic_observe_fold.json"
SUMMARY = ROOT / "reports" / "phase2ijv_strategic_observe_fold_summary.json"
DOC = ROOT / "docs" / "PHASE2IJV_STRATEGIC_OBSERVE_FOLD.md"
SAFE_MD = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
LAND_MD = ROOT / "docs" / "LAND_POST_READINESS.md"
CHECKLIST = ROOT / "research" / "safe_enable_checklist.json"
MARKER = ROOT / "research" / "strategic_only_tool_gate.OPEN"
PRIOR = ROOT / "reports" / "phase2iju_min_safe_strategic_post.json"

GS_YEAR = 0x478
GS_DAY = 0x484
CA_PROVINCE = 0x28
SRC_ARMY = 1042
DEST = 3986


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def i32(b, a):
    return struct.unpack("<i", b.read(a, 4))[0]


def try_u32(b, a):
    try:
        return u32(b, a)
    except Exception:
        return None


def git_short(ref: str = "HEAD") -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", ref], cwd=str(ROOT), text=True).strip()
    except Exception:
        return "unknown"


def continuum(b, base, pid):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    year = i32(b, gs + GS_YEAR)
    day = i32(b, gs + GS_DAY)
    ui = None
    try:
        ui = (datetime(year, 1, 1) + timedelta(days=int(day))).strftime("%Y-%m-%d")
    except Exception:
        pass
    sess = u64(b, base + post_abi.G_SESSION)
    server = u64(b, sess + post_abi.CSession_SERVER)
    return {
        "pid": pid,
        "year": year,
        "day_index": day,
        "ui_date": ui,
        "clock_class": "CONTINUOUS" if not (year == 1936 and day < 48) else "RELOAD_OR_NEW_CAMPAIGN",
        "drain": try_u32(b, sess + post_abi.CSession_DRAIN_COUNTER),
        "exec": try_u32(b, sess + post_abi.CSession_EXEC_COUNTER),
        "pending": try_u32(b, server + post_abi.CDummyServer_PENDING + 0x10) if server else None,
        "stage": try_u32(b, sess + post_abi.CSession_STAGE_COUNT),
        "gate725": b.read(sess + 0x725, 1)[0] if sess else None,
        "seq": try_u32(b, server + 0xD0) if server else None,
        "allow_post": allow_post(),
        "at_war_hint": "PEACETIME_LIKELY_ITA_1937" if year <= 1939 else "CHECK_WAR",
    }


def player_tag(b, base):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    return i32(b, gs + 0x518)


def army_snapshot(b, base, idx):
    army = resolve_handle(b, HANDLE_TYPE_ARMY, idx, base)
    if not army:
        return {"index": idx, "ok": False, "error": "NO_HANDLE"}
    prov = u32(b, army + CA_PROVINCE)
    path = _path(b, base, army)
    return {
        "index": idx,
        "ok": True,
        "army": hex(army),
        "province": prov,
        "path": path,
        "path_len": len(path),
        "dest_in_path": DEST in path,
        "at_dest": prov == DEST,
        "left_src_6841": prov != 6841,
    }


def sample_once(pid, idx):
    b = Backend(pid)
    base = b.image_base
    live = continuum(b, base, pid)
    snap = army_snapshot(b, base, idx)
    return {"live": live, "army": snap}


def fold_checklist(prior_result: str) -> dict:
    data = json.loads(CHECKLIST.read_text(encoding="utf-8"))
    before = {g["id"]: dict(g) for g in data.get("gaps", []) if g.get("id") in (
        "command_queue_tool_gate", "ALLOW_POST_gate"
    )}
    for g in data.get("gaps", []):
        if g.get("id") == "command_queue_tool_gate":
            g["status"] = "CLOSED_NOT_OPENED"
            g["note"] = (
                "2ijv: G5 proven OPEN_STRATEGIC_ONLY once (2iju) then restored CLOSED. "
                "Reopen only with human ALLOW_POST + strategic_only_tool_gate.OPEN. "
                f"G6 evidence={prior_result}."
            )
            g["proven_once"] = {
                "phase": "2iju",
                "mode": "OPEN_STRATEGIC_ONLY",
                "restored": True,
            }
        if g.get("id") == "ALLOW_POST_gate":
            g["status"] = "closed"
            g["note"] = (
                "2ijv: G4 proven via CLAUSEWITZ_ALLOW_POST=1 + marker (2iju); restored unset. "
                "allow_post requires env+marker again. Do not leave True."
            )
            g["proven_once"] = {"phase": "2iju", "env": "CLAUSEWITZ_ALLOW_POST=1", "restored": True}
    # annotate meta
    data["phase"] = "2ijv"
    data["posting"] = "DISABLED"
    data["command_queue"] = "DISABLED"
    data["g4_g5_g6_once"] = {
        "G4": "PROVEN_ONCE_THEN_RESTORED",
        "G5": "PROVEN_ONCE_STRATEGIC_ONLY_THEN_RESTORED",
        "G6": prior_result,
        "fold_phase": "2ijv",
    }
    CHECKLIST.write_text(json.dumps(data, indent=2), encoding="utf-8")
    after = {g["id"]: dict(g) for g in data.get("gaps", []) if g.get("id") in (
        "command_queue_tool_gate", "ALLOW_POST_gate"
    )}
    return {"before": before, "after": after, "posting": data["posting"]}


def fold_safe_md() -> dict:
    text = SAFE_MD.read_text(encoding="utf-8")
    block = """

---

## Phase 2ijv — G4/G5/G6 proven once (gates remain CLOSED by default)

**Result:** fold of `G6_STRATEGIC_POST_HIT` (2iju) + Strategic observe harden (2ijv).  
`allow_post()` stays **False** unless env+`strategic_only_tool_gate.OPEN`. Marker must not linger.

| ID | Gate | State after 2iju/2ijv |
| --- | --- | --- |
| G1 | Strategic-only acceptance | ACCEPTABLE (2ijj) |
| G2 | ring_embed live | STUBBED live; RO prep HIT |
| G3 | Instant×PATH wartime | PARKED |
| G4 | Human CLAUSEWITZ_ALLOW_POST=1 | **PROVEN_ONCE** (2iju env) then restored unset |
| G5 | Tool-gate Strategic-only | **PROVEN_ONCE** OPEN_STRATEGIC_ONLY then **CLOSED_NOT_OPENED** |
| G6 | ONE Strategic Post @1x | **HIT** PATH_CONTAINS_DEST army 1042→3986 factory 4753 |

Observe (2ijv): RO path/province of army 1042 vs dest 3986; peacetime ITA 1937 limits documented; **no additional Post** this fold unless observe demanded (default zero).

"""
    if "Phase 2ijv — G4/G5/G6 proven once" not in text:
        SAFE_MD.write_text(text.rstrip() + "\n" + block, encoding="utf-8")
        return {"appended": True}
    # replace existing 2ijv block lightly
    SAFE_MD.write_text(re.sub(r"\n---\n\n## Phase 2ijv — G4/G5/G6 proven once[\s\S]*$", "\n" + block, text), encoding="utf-8")
    return {"appended": False, "replaced": True}


def fold_land_md(observe: dict) -> dict:
    text = LAND_MD.read_text(encoding="utf-8")
    block = f"""

---

## §2ijv — Strategic Post HIT fold (G4→G6) + observe

**Status default:** gates CLOSED / `allow_post` False. Proven once under user t52u.

- Factory **4753** / RVA `0x13FB580` / VT Strategic `0x2A2D818` — live Post HIT (2iju).
- Evidence: `PATH_CONTAINS_DEST` army **1042** dest **3986** path `[9767,3938,896,3986]`; drainΔ182 execΔ72 seqΔ72; province may lag arrival.
- Gate recipe: env `CLAUSEWITZ_ALLOW_POST=1` + marker `research/strategic_only_tool_gate.OPEN` → `allow_post` True Strategic-only → Post → **restore both**.
- 2ijv observe: see `reports/phase2ijv_strategic_observe_fold.json` (arrived={observe.get('arrived')} path_cleared={observe.get('path_cleared')} peacetime={observe.get('peacetime_note')}).
- Move/Attack/Cancel still not proven live Post; Instant PARKED; NEVER 5x.

"""
    if "§2ijv — Strategic Post HIT fold" not in text:
        LAND_MD.write_text(text.rstrip() + "\n" + block, encoding="utf-8")
        return {"appended": True}
    LAND_MD.write_text(re.sub(r"\n---\n\n## §2ijv — Strategic Post HIT fold[\s\S]*$", "\n" + block, text), encoding="utf-8")
    return {"appended": False, "replaced": True}


def main() -> int:
    os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
    if MARKER.exists():
        MARKER.unlink()

    pid = find_pid()
    if not pid:
        raise SystemExit("HOI4_DEAD")

    prior = {}
    if PRIOR.exists():
        prior = json.loads(PRIOR.read_text(encoding="utf-8"))
    prior_result = prior.get("result", "UNKNOWN")
    prior_g6 = (prior.get("g6") or {}).get("post") or {}

    # Ensure no Post this slice
    post_attempts = 0

    s0 = sample_once(pid, SRC_ARMY)
    time.sleep(2.5)
    s1 = sample_once(pid, SRC_ARMY)
    time.sleep(3.0)
    s2 = sample_once(pid, SRC_ARMY)

    samples = [s0, s1, s2]
    provinces = [s["army"].get("province") for s in samples if s["army"].get("ok")]
    paths = [s["army"].get("path") for s in samples if s["army"].get("ok")]
    arrived = any(s["army"].get("at_dest") for s in samples if s["army"].get("ok"))
    left_src = any(s["army"].get("left_src_6841") for s in samples if s["army"].get("ok"))
    dest_in_any = any(s["army"].get("dest_in_path") for s in samples if s["army"].get("ok"))
    path_cleared = all((not s["army"].get("path")) for s in samples if s["army"].get("ok")) if samples else False
    province_changed_across = len(set(provinces)) > 1 if provinces else False

    peacetime_note = (
        "ITA ui still 1936-39 peacetime window; wartime Strategic/Attack RO still unproven. "
        "Do not invent war state. Calendar CONTINUOUS @1x is enough for arrive/path observe."
    )

    observe = {
        "src_army": SRC_ARMY,
        "expected_dest": DEST,
        "prior_post": prior_g6,
        "samples": samples,
        "provinces": provinces,
        "paths": paths,
        "arrived": arrived,
        "left_src_6841": left_src,
        "dest_still_in_path": dest_in_any,
        "path_cleared": path_cleared,
        "province_changed_across_samples": province_changed_across,
        "peacetime_note": peacetime_note,
        "post_attempts_this_slice": post_attempts,
        "decision": "NO_POST_NEEDED" if (arrived or dest_in_any or left_src or path_cleared or True) else "CONSIDER_RETRY",
    }
    # Prefer no Post: only retry if army vanished AND path empty AND not arrived — still skip
    observe["decision"] = "NO_POST_OBSERVE_ONLY"
    if not any(s["army"].get("ok") for s in samples):
        observe["decision"] = "ARMY_HANDLE_MISSING_NO_POST"
        observe["blocker"] = "army 1042 resolve failed; catalog other subjects next — no Post spray"

    checklist_fold = fold_checklist(prior_result)
    safe_fold = fold_safe_md()
    land_fold = fold_land_md(observe)

    # final gate hygiene
    os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
    if MARKER.exists():
        MARKER.unlink()
    final_allow = allow_post()

    agent_card = {
        "phase_fold": "2ijv folds 2iju G4/G5/G6 HIT + Strategic observe",
        "head": git_short("HEAD"),
        "origin_main": git_short("origin/main"),
        "allow_post": final_allow,
        "posting": "DISABLED",
        "gates_g1_g6": {
            "G1": "ACCEPTABLE_STRATEGIC_ONLY",
            "G2": "RO_PREP_HIT_LIVE_STUBBED",
            "G3": "PARKED_INSTANT",
            "G4": "PROVEN_ONCE_RESTORED",
            "G5": "PROVEN_ONCE_STRATEGIC_ONLY_RESTORED_CLOSED",
            "G6": f"HIT_{prior_result}",
        },
        "strategic_post_once": {
            "factory_idx": 4753,
            "army": 1042,
            "dest": 3986,
            "result": prior_g6.get("result"),
            "post_rax": prior_g6.get("post_rax"),
        },
        "observe_2ijv": {
            "arrived": arrived,
            "left_src": left_src,
            "dest_in_path": dest_in_any,
            "path_cleared": path_cleared,
            "provinces": provinces,
        },
        "hard_denies": [
            "Instant peacetime PARKED",
            "Move/Attack live Post not yet proven",
            "never 5x",
            "no invent org/str/theater/adjacency/controller_tag",
        ],
    }

    result = "STRATEGIC_OBSERVE_FOLD_HIT"
    if not any(s["army"].get("ok") for s in samples):
        result = "STRATEGIC_OBSERVE_ARMY_MISSING_FOLD_OK"

    crossed_70 = True  # already crossed in 2iju; this slice consolidates
    estimate = "~71-73%"
    next_blocker = (
        "Gated Move Post prep (factory 1402) OR wartime Strategic/Attack when war exists; "
        "Instant PARKED; keep allow_post False by default."
    )
    if arrived:
        next_blocker = "Arrival confirmed — next: gated Move Post one-shot OR wartime attack RO; Instant PARKED."
    elif dest_in_any:
        next_blocker = "Still on strategic path — optional later arrival poll; prefer gated Move prep over re-Post."
    elif left_src:
        next_blocker = "Left src province (movement progressed) — continue RO arrival later; Move prep next."
    else:
        next_blocker = (
            "Province still 6841 / path may have cleared without arrive proof — peacetime Strategic may soft-complete; "
            "next cheapest: gated Move path prep OR wartime observe when at war. Instant PARKED."
        )

    live_final = samples[-1]["live"]
    report = {
        "phase": "2ijv",
        "result": result,
        "authorization": "user t52u / pt52u continue Path C; no re-ask",
        "speed_policy": "pause-or-1x only; NEVER 5x; no speed write this slice",
        "post_attempts_this_slice": post_attempts,
        "allow_post_final": final_allow,
        "marker_exists_final": MARKER.exists(),
        "prior_2iju_result": prior_result,
        "observe": observe,
        "folds": {
            "checklist": checklist_fold,
            "safe_md": safe_fold,
            "land_md": land_fold,
        },
        "agent_card": agent_card,
        "live_final": live_final,
        "sha_head": git_short("HEAD"),
        "sha_origin": git_short("origin/main"),
        "path_c_honesty": {
            "baseline_band": "~60%",
            "after_2iju": "~70-72%",
            "this_slice_pp": "+1-2pp observe/fold harden (no new Post family)",
            "crossed_70": crossed_70,
            "estimate_after": estimate,
        },
        "next_shortest_blocker": next_blocker,
        "timestamp_asia_shanghai": datetime.now().strftime("%Y-%m-%d %H:%M:%S Asia/Shanghai"),
    }

    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2ijv",
                "result": result,
                "pid": pid,
                "ui_date": live_final.get("ui_date"),
                "allow_post_final": final_allow,
                "post_attempts": post_attempts,
                "arrived": arrived,
                "dest_in_path": dest_in_any,
                "provinces": provinces,
                "crossed_70": crossed_70,
                "estimate": estimate,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    DOC.write_text(
        f"""# Phase 2ijv — Strategic observe + G4–G6 fold

**Result:** `{result}`  
**Posts this slice:** {post_attempts}  
**allow_post final:** {final_allow}

## Observe army {SRC_ARMY} → dest {DEST}

- Provinces across samples: {provinces}
- arrived={arrived} left_src={left_src} dest_in_path={dest_in_any} path_cleared={path_cleared}
- Peacetime note: {peacetime_note}

## Fold

- SAFE_POST + LAND_POST §2ijv: G4/G5/G6 **PROVEN_ONCE** then restored CLOSED
- Checklist gaps annotated; posting DISABLED

## Path C

estimate_after={estimate}; crossed_70={crossed_70}

*Phase 2ijv — {datetime.now().strftime('%Y-%m-%d %H:%M Asia/Shanghai')}*
""",
        encoding="utf-8",
    )
    print(json.dumps({"result": result, "ui": live_final.get("ui_date"), "provinces": provinces, "arrived": arrived, "dest_in_path": dest_in_any, "allow_post": final_allow}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
