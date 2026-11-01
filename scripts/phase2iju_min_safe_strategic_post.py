#!/usr/bin/env python3
"""Phase 2iju: G4 CLAUSEWITZ_ALLOW_POST + G5 Strategic-only tool-gate + G6 ONE Strategic Post @1x.

User-authorized (t52u). NEVER 5x. Strategic Redeploy only. Restore gates after unless retry needed.
"""
from __future__ import annotations

import json
import os
import struct
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import post_abi
from army_subjects import iter_armies_by_index
from config import allow_post
from process import Backend, find_pid
from strategic_order import strategic_redeploy

OUT = ROOT / "reports" / "phase2iju_min_safe_strategic_post.json"
SUMMARY = ROOT / "reports" / "phase2iju_min_safe_strategic_post_summary.json"
DOC = ROOT / "docs" / "PHASE2IJU_MIN_SAFE_STRATEGIC_POST.md"
MARKER = ROOT / "research" / "strategic_only_tool_gate.OPEN"
CHECKLIST = ROOT / "research" / "safe_enable_checklist.json"

GS_YEAR = 0x478
GS_DAY = 0x484
CA_PROVINCE = 0x28


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
    }


def player_tag(b, base):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    return i32(b, gs + 0x518)


def scan_armies(b, base, tag):
    rows = []
    for lo in range(0, 5000, 500):
        rows.extend(iter_armies_by_index(b, base, lo, lo + 500, country_tag=tag))
    return rows


def army_prov(b, base, idx):
    from handle import resolve_handle, HANDLE_TYPE_ARMY
    army = resolve_handle(b, HANDLE_TYPE_ARMY, idx, base)
    if not army:
        return None
    return {"index": idx, "army": hex(army), "province": u32(b, army + CA_PROVINCE)}


def set_g4_env():
    os.environ["CLAUSEWITZ_ALLOW_POST"] = "1"
    return {"how": "os.environ CLAUSEWITZ_ALLOW_POST=1 in this Python process", "value": os.environ.get("CLAUSEWITZ_ALLOW_POST")}


def open_g5_marker():
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    MARKER.write_text(
        "OPEN Strategic-only tool-gate for Phase 2iju (user t52u).\n"
        "Allows allow_post() True ONLY with CLAUSEWITZ_ALLOW_POST=1.\n"
        "Scope: CStrategicRedeploymentCommand / factory 4753 / FN_CMD_QUEUE_POST once.\n"
        "NEVER_POST: Inc/Dec/SetGameSpeed, HourlyTick, Ping, Pause — still forbidden.\n"
        "Do NOT broaden to Move/Attack/Cancel batch in this gate.\n",
        encoding="utf-8",
    )
    before = None
    after = None
    if CHECKLIST.exists():
        data = json.loads(CHECKLIST.read_text(encoding="utf-8"))
        before = None
        for g in data.get("gaps", []):
            if g.get("id") == "command_queue_tool_gate":
                before = dict(g)
                g["status"] = "OPEN_STRATEGIC_ONLY"
                g["note"] = "2iju G5: Strategic-only tool-gate OPEN (user t52u); other Post families still denied"
                break
        for g in data.get("gaps", []):
            if g.get("id") == "ALLOW_POST_gate":
                g["status"] = "OPEN_WITH_ENV_AND_MARKER"
                g["note"] = "2iju: allow_post True when CLAUSEWITZ_ALLOW_POST=1 and strategic_only_tool_gate.OPEN present"
        data["posting"] = "STRATEGIC_ONLY_GATED"
        data["command_queue"] = "STRATEGIC_ONLY_OPEN"
        CHECKLIST.write_text(json.dumps(data, indent=2), encoding="utf-8")
        after = "OPEN_STRATEGIC_ONLY"
    return {"marker": str(MARKER), "checklist_before": before, "checklist_after": after}


def restore_gates():
    os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
    if MARKER.exists():
        MARKER.unlink()
    if CHECKLIST.exists():
        data = json.loads(CHECKLIST.read_text(encoding="utf-8"))
        for g in data.get("gaps", []):
            if g.get("id") == "command_queue_tool_gate":
                g["status"] = "CLOSED_NOT_OPENED"
                g["note"] = "Re-closed after 2iju G6 one-shot; reopen only with human ALLOW_POST + marker"
            if g.get("id") == "ALLOW_POST_gate":
                g["status"] = "closed"
                g["note"] = "2iju restored: allow_post requires env+marker again"
        data["posting"] = "DISABLED"
        data["command_queue"] = "DISABLED"
        CHECKLIST.write_text(json.dumps(data, indent=2), encoding="utf-8")
    # reload config view
    return {"env_cleared": "CLAUSEWITZ_ALLOW_POST" not in os.environ, "marker_exists": MARKER.exists(), "allow_post": allow_post()}


def main() -> int:
    # Ensure clean start measurement of allow_post before G4
    os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
    if MARKER.exists():
        MARKER.unlink()

    # Force re-import semantics for allow_post after possible prior env
    import importlib
    import config as cfg
    importlib.reload(cfg)
    global allow_post
    from config import allow_post

    g4_before = allow_post()
    assert g4_before is False

    pid = find_pid()
    if not pid:
        raise SystemExit("HOI4_DEAD")
    b = Backend(pid)
    base = b.image_base
    tag = player_tag(b, base)
    live0 = continuum(b, base, pid)

    # G4
    g4 = set_g4_env()
    importlib.reload(cfg)
    from config import allow_post as allow_post2
    g4_env_only = allow_post2()  # should still be False without marker

    # G5
    g5_before = {"allow_post": g4_env_only, "tool_gate": "CLOSED_NOT_OPENED"}
    g5_open = open_g5_marker()
    importlib.reload(cfg)
    from config import allow_post as allow_post3
    # rebind module-level for strategic_order which imports at call time via assert
    g5_after_allow = allow_post3()
    g5_after = {"allow_post": g5_after_allow, "tool_gate": "OPEN_STRATEGIC_ONLY", "open": g5_open}

    if not g5_after_allow:
        restore_gates()
        raise SystemExit("G5_FAILED_ALLOW_POST_STILL_FALSE")

    # Ensure strategic_order sees refreshed config
    import strategic_order as so
    importlib.reload(so)

    rows = scan_armies(b, base, tag)
    # Prefer historically used 1042 if present else first
    by_idx = {r["index"]: r for r in rows}
    prefer = [1042, 461, 1039, 381]
    src = None
    for ix in prefer:
        if ix in by_idx:
            src = by_idx[ix]
            break
    if src is None and rows:
        src = rows[0]
    if src is None:
        restore_gates()
        raise SystemExit("NO_ARMY")

    dest_pool = []
    seen = set()
    for r in rows:
        pid_ = int(r["province_id"])
        if pid_ == int(src["province_id"]) or pid_ in seen:
            continue
        seen.add(pid_)
        dest_pool.append(pid_)
        if len(dest_pool) >= 12:
            break

    # Dry-run IsValid scan (no Post)
    trials = []
    chosen = None
    for dest in dest_pool:
        # temporarily need allow_post for assert only on live post; dry_run skips assert
        tr = so.strategic_redeploy(int(src["index"]), int(dest), dry_run=True)
        trials.append(tr)
        if tr.get("ok") and tr.get("result") == "DRY_RUN_VALID":
            chosen = tr
            break

    g6 = {
        "src_army": src["index"],
        "src_province": src["province_id"],
        "dest_pool": dest_pool,
        "trials": trials,
        "chosen": chosen,
        "post": None,
        "observe": None,
    }

    live_pre = continuum(b, base, pid)
    src_pre = army_prov(b, base, src["index"])

    if not chosen:
        g6["post"] = {"ok": False, "result": "NO_ISVALID_DEST"}
        restored = restore_gates()
        result_code = "G6_NO_VALID_DEST"
    else:
        dest = int(chosen["province"])
        # G6 ONE Post
        posted = so.strategic_redeploy(int(src["index"]), dest, dry_run=False)
        g6["post"] = posted
        time.sleep(2.0)
        b2 = Backend(pid)
        live_post = continuum(b2, base, pid)
        src_post = army_prov(b2, base, src["index"])
        time.sleep(3.0)
        b3 = Backend(pid)
        live_later = continuum(b3, base, pid)
        src_later = army_prov(b3, base, src["index"])
        g6["observe"] = {
            "pre": live_pre,
            "src_pre": src_pre,
            "immediate": live_post,
            "src_immediate": src_post,
            "later": live_later,
            "src_later": src_later,
            "drain_delta": (live_post.get("drain") or 0) - (live_pre.get("drain") or 0),
            "exec_delta": (live_post.get("exec") or 0) - (live_pre.get("exec") or 0),
            "seq_delta": (live_post.get("seq") or 0) - (live_pre.get("seq") or 0),
            "province_changed": (src_pre or {}).get("province") != (src_later or {}).get("province"),
            "path_before": posted.get("path_before"),
            "path_after": posted.get("path_after"),
        }
        if posted.get("ok") or posted.get("result") in ("PATH_CONTAINS_DEST", "POSTED_DEST_NOT_IN_PATH"):
            # Post path ran; PATH_CONTAINS_DEST is stronger success
            if posted.get("result") == "PATH_CONTAINS_DEST" or g6["observe"]["province_changed"] or g6["observe"]["seq_delta"]:
                result_code = "G6_STRATEGIC_POST_HIT"
            else:
                result_code = "G6_STRATEGIC_POST_ACCEPTED_WEAK"
        else:
            result_code = "G6_STRATEGIC_POST_FAIL"

        # Restore gates after one-shot (safe default)
        restored = restore_gates()

    importlib.reload(cfg)
    from config import allow_post as allow_post_final

    report = {
        "phase": "2iju",
        "result": result_code,
        "authorization": "user t52u / pt52u — CLAUSEWITZ_ALLOW_POST + minimum safe Post verification",
        "speed_policy": "pause-or-1x only; NEVER 5x; no speed write this slice",
        "live0": live0,
        "g4": {
            "before_allow_post": g4_before,
            "set": g4,
            "env_only_allow_post": g4_env_only,
            "note": "Env alone insufficient; marker required (G5)",
        },
        "g5": {
            "before": g5_before,
            "after": g5_after,
        },
        "g6": g6,
        "gates_restored": restored,
        "final_allow_post": allow_post_final(),
        "factory": {"factory_idx": 4753, "factory_rva": "0x13FB580", "type": "CStrategicRedeploymentCommand"},
        "hard_rules": [
            "ONE Strategic Post only",
            "never 5x",
            "no Instant/PATH densify",
            "no invent org/str/theater/adjacency/controller_tag",
            "gates restored after one-shot",
        ],
        "path_c_honesty": {
            "baseline_band": "~60-62%",
            "this_slice_pp": "+8-12pp if G6 HIT (first gated Strategic Post); else 0-2pp gate plumbing only",
            "crossed_70": False,
            "note": "Cross ~70% only if G6 shows PATH_CONTAINS_DEST or clear order effect; honest update below",
        },
        "next_shortest_blocker": "If G6 HIT: harden observe/retry Strategic at war or Move path; if FAIL: fix IsValid dest selection / ring push. Instant still PARKED.",
        "timestamp_asia_shanghai": datetime.now().strftime("%Y-%m-%d %H:%M:%S Asia/Shanghai"),
    }

    # Honest ~70% flag
    crossed = False
    if result_code == "G6_STRATEGIC_POST_HIT":
        crossed = True
        report["path_c_honesty"]["crossed_70"] = True
        report["path_c_honesty"]["estimate_after"] = "~70-72%"
    elif result_code == "G6_STRATEGIC_POST_ACCEPTED_WEAK":
        report["path_c_honesty"]["estimate_after"] = "~65-68%"
        report["path_c_honesty"]["crossed_70"] = False
    else:
        report["path_c_honesty"]["estimate_after"] = "~60-62%"
        report["path_c_honesty"]["crossed_70"] = False

    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2iju",
                "result": result_code,
                "pid": pid,
                "ui_date": (g6.get("observe") or {}).get("later", live0).get("ui_date") if isinstance((g6.get("observe") or {}).get("later", live0), dict) else live0.get("ui_date"),
                "g4_set": True,
                "g5_open": bool(g5_after_allow),
                "g6_result": (g6.get("post") or {}).get("result"),
                "g6_ok": (g6.get("post") or {}).get("ok"),
                "final_allow_post": allow_post_final(),
                "gates_restored": restored.get("env_cleared") and not restored.get("marker_exists"),
                "crossed_70": crossed,
                "src": g6.get("src_army"),
                "dest": (chosen or {}).get("province") if chosen else None,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    DOC.write_text(
        f"""# Phase 2iju — Minimum safe Strategic Post (G4→G5→G6)

**Result:** `{result_code}`  
**Authorization:** user t52u / pt52u  
**Speed:** pause/1x only — NEVER 5x

## G4 — CLAUSEWITZ_ALLOW_POST=1

- Set via `os.environ['CLAUSEWITZ_ALLOW_POST']='1'` in the Post Python process.
- Env alone: allow_post **False** (marker required).

## G5 — Strategic-only tool-gate

- Created `research/strategic_only_tool_gate.OPEN`
- `config.allow_post()` returns True only when env=1 AND marker present
- Checklist `command_queue_tool_gate` → OPEN_STRATEGIC_ONLY for the shot
- Scope: Strategic Redeploy only; NEVER_POST families still forbidden

## G6 — ONE Strategic Redeploy

- Factory idx **4753** / RVA `0x13FB580` via `calling/strategic_order.py`
- Source army: {g6.get('src_army')} province {g6.get('src_province')}
- Chosen: {chosen}
- Post result: {g6.get('post')}
- Observe: {g6.get('observe')}

## Gate restore

After one-shot: env cleared, marker removed, checklist re-closed. final allow_post={allow_post_final()}.

## Path C honesty

estimate_after={report['path_c_honesty'].get('estimate_after')}; crossed_70={report['path_c_honesty']['crossed_70']}

*Phase 2iju — 2026-11-01 Asia/Shanghai*
""",
        encoding="utf-8",
    )

    print(json.dumps({"result": result_code, **json.loads(SUMMARY.read_text(encoding="utf-8"))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
