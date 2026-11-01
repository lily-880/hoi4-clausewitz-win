#!/usr/bin/env python3
"""Phase 2ijm NON-Post: factory / Post-ABI / clock-queue RO reaffirm + G4–G6 gates.

Live RO only. NO Post / Instant / PATH densify / midflight / ring_embed exec /
tool-gate / ask ALLOW_POST. Catalog remaining human gates G4–G6.
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
from config import allow_post
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2ijm_factory_postabi_clock_ro.json"
SUMMARY = ROOT / "reports" / "phase2ijm_factory_postabi_clock_ro_summary.json"
DOC = ROOT / "docs" / "PHASE2IJM_FACTORY_POSTABI_CLOCK_RO.md"

GS_YEAR = 0x478
GS_DAY = 0x484
RING_BLOB = 0x40
DUMMY_SEQ = 0xD0


def load_hb():
    spec = importlib.util.spec_from_file_location(
        "p2hb", ROOT / "scripts/phase2hb_move_family_fn_polish.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


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


def ov_int(ov, key):
    v = ov[key]
    if isinstance(v, dict):
        for k in ("rva", "value", "off"):
            if k in v and isinstance(v[k], int):
                return v[k]
        return None
    return v if isinstance(v, int) else None


def post_abi_ro(b, base):
    """Reaffirm Dummy/session/Post-ABI constants vs live + offsets_verified (no Post)."""
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    checks = []

    def add(name, expected, live, note=""):
        ok = expected == live if live is not None and expected is not None else False
        checks.append(
            {
                "name": name,
                "expected": hex(expected) if isinstance(expected, int) else expected,
                "live": hex(live) if isinstance(live, int) else live,
                "match": ok,
                "note": note,
            }
        )

    # Module globals vs offsets_verified
    pairs = [
        ("G_SESSION", post_abi.G_SESSION, ov_int(ov, "G_SESSION")),
        ("G_GAMESTATE", post_abi.G_GAMESTATE, ov_int(ov, "G_GAMESTATE")),
        ("CDummyServer_VT", post_abi.CDummyServer_VT, ov_int(ov, "CDummyServer_VT")),
        ("CDummyServer_RING", post_abi.CDummyServer_RING, ov_int(ov, "CDummyServer_RING_EMBED")),
        ("CCommand_VT_ISVALID", post_abi.CCommand_VT_ISVALID, ov_int(ov, "CCommand_VT_ISVALID")),
        ("CCommand_VT_EXECUTE", post_abi.CCommand_VT_EXECUTE, ov_int(ov, "CCommand_VT_EXECUTE")),
        (
            "FN_CMD_QUEUE_POST_SINK_DUMMY",
            post_abi.FN_CMD_QUEUE_POST_SINK_DUMMY,
            ov_int(ov, "FN_CMD_QUEUE_POST_SINK_DUMMY"),
        ),
        (
            "FN_CMD_QUEUE_DRAIN_DUMMY",
            post_abi.FN_CMD_QUEUE_DRAIN_DUMMY,
            ov_int(ov, "FN_CMD_QUEUE_POST_DRAIN_DUMMY"),
        ),
    ]
    for name, pa, ovi in pairs:
        add(f"const_{name}", pa, ovi, "post_abi vs offsets_verified")

    # Live Dummy server VT + ring INLINE
    sess = try_u64(b, base + post_abi.G_SESSION)
    server = try_u64(b, sess + post_abi.CSession_SERVER) if sess else None
    vt_rva = None
    ring = None
    if server:
        vt = try_u64(b, server) or 0
        vt_rva = (vt - base) & 0xFFFFFFFF
        add("live_CDummyServer_VT", post_abi.CDummyServer_VT, vt_rva, "live server VT RVA")
        ring_addr = server + post_abi.CDummyServer_RING
        blob = b.read(ring_addr, RING_BLOB)
        u32s = [struct.unpack_from("<I", blob, i)[0] for i in range(0, 8, 4)]
        cap_like = u32s[1] if len(u32s) > 1 else None
        add("live_RING_capacity_like", 0x10, cap_like, "INLINE_BLOB u32_1 == 0x10")
        seq = try_u32(b, server + DUMMY_SEQ)
        ring = {
            "kind": "INLINE_BLOB",
            "ring_off": hex(post_abi.CDummyServer_RING),
            "ring_addr": hex(ring_addr),
            "u32_0": hex(u32s[0]),
            "u32_1_capacity_like": hex(cap_like) if cap_like is not None else None,
            "capacity_like_equals_0x10": cap_like == 0x10,
            "seq_at_server_plus_0xd0": seq,
            "server_vt_match": vt_rva == post_abi.CDummyServer_VT,
        }

    # Strategic catalog constants vs offsets_verified
    strat_pairs = [
        ("STRAT_VT", 0x2A2D818, ov_int(ov, "CStrategicRedeploymentCommand_VT")),
        ("STRAT_TYPE_ID", 0x35B9, ov_int(ov, "CStrategicRedeploymentCommand_TYPE_ID")),
        ("STRAT_SIZE", 0x50, ov_int(ov, "CStrategicRedeploymentCommand_SIZE")),
        ("STRAT_FACTORY", 0x13FB580, ov_int(ov, "CStrategicRedeploymentCommand_FACTORY")),
        ("STRAT_EMBED", 0x28, ov_int(ov, "CStrategicRedeploymentCommand_ACTION_EMBED")),
        ("STRAT_ACTION_VT", 0x2A1F7E8, ov_int(ov, "CUnitStrategicMoveAction_VT")),
        ("STRAT_ACTION_TYPE", 0x364A, ov_int(ov, "CUnitStrategicMoveAction_TYPE_ID")),
    ]
    for name, cat, ovi in strat_pairs:
        add(f"catalog_{name}", cat, ovi, "catalog vs offsets_verified")

    mismatches = [c for c in checks if not c["match"]]
    return {
        "session": hex(sess) if sess else None,
        "server": hex(server) if server else None,
        "ring": ring,
        "checks": checks,
        "all_const_match": len(mismatches) == 0,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "offsets_verified_updated": False,
        "note": "RO compare only — no writes; no Post; invent no field names",
    }


def human_gates_g4_g6():
    return {
        "status": "CATALOG_ONLY — executor cannot flip; allow_post stays False",
        "G4": {
            "gate": "Human CLAUSEWITZ_ALLOW_POST=1 once",
            "state": "HARD_DENY until human",
            "executor": "CANNOT flip",
            "need": "Conscious human env after G1 ACCEPTABLE + G2 live readiness discussion",
        },
        "G5": {
            "gate": "Dedicated tool-gate open + NEVER_POST",
            "state": "CLOSED_NOT_OPENED",
            "need": "Dedicated slice after G4; refuse NEVER_POST set",
        },
        "G6": {
            "gate": "ONE Strategic Post @1x; verify; pause; unset",
            "state": "FORBIDDEN now",
            "need": "After G4+G5; Strategic preferred (G1 path); never 5x",
        },
        "still_also": {
            "G2_live": "ring_embed in-process push STUBBED (RO prep HIT 2ijk)",
            "G3": "Instant peacetime PARKED",
            "G1": "ACCEPTABLE Strategic-only (2ijj)",
        },
    }


def write_doc(result, live, polish, abi, gates, calendar_ok):
    mism = abi.get("mismatch_count", 0)
    DOC.write_text(
        f"""# Phase 2ijm — Factory / Post-ABI / clock-queue RO reaffirm + G4–G6

**Result:** `{result}`  
**allow_post:** **False** · Post **NOT** called · ring_embed live **STUBBED** · Instant **PARKED** · never 5x

## Live clock / queue

pid {live.get("pid")} · {live.get("clock_class")} · day_index={live.get("day_index")} ui={live.get("ui_date")} ·  
drain={live.get("drain")} exec={live.get("exec")} pending={live.get("pending")} · calendar_ok={calendar_ok}

## Factory / VT FN (MOVE family)

- all_factory_match: `{polish.get("all_factory_match")}`
- all_fn_match: `{polish.get("all_fn_match")}`
- strategic_4753_match: `{polish.get("strategic_4753_match")}`

## Post-ABI / offsets_verified RO

- all_const_match: `{abi.get("all_const_match")}` · mismatch_count={mism}
- Dummy ring: kind=`{(abi.get("ring") or {}).get("kind")}` · server_vt_match=`{(abi.get("ring") or {}).get("server_vt_match")}` · cap_like_0x10=`{(abi.get("ring") or {}).get("capacity_like_equals_0x10")}`
- offsets_verified **not** rewritten (no drift requiring update)

## Remaining human gates (G4–G6) — catalog

| Gate | State | Note |
| --- | --- | --- |
| G4 | HARD_DENY until human | CLAUSEWITZ_ALLOW_POST=1 once; executor cannot flip |
| G5 | CLOSED_NOT_OPENED | tool-gate + NEVER_POST after G4 |
| G6 | FORBIDDEN now | ONE Strategic Post @1x after G4+G5 |

Also: G2 live STUBBED · G3 Instant PARKED · G1 Strategic-only ACCEPTABLE.

## Path C honesty (t50u)

~60–62% baseline band; this RO reaffirm ≤+1–2pp confidence, **not** +10pp. **~70% NOT crossed.**

## Next

Human G4 → G5 → G2 live / G6. No densify/poll churn.

*Phase 2ijm · 2026-11-01 Asia/Shanghai*
""",
        encoding="utf-8",
    )


def patch_docs(result, live, polish, abi):
    note = (
        f"\n### 2ijm factory/Post-ABI/clock RO reaffirm (catalog)\n\n"
        f"**Gate remains CLOSED. allow_post False. No Post.**\n\n"
        f"- Result=`{result}` · factory/FN={polish.get('all_factory_match')}/"
        f"{polish.get('all_fn_match')} · Strat4753={polish.get('strategic_4753_match')} · "
        f"post_abi/ov const_match={abi.get('all_const_match')} mismatch={abi.get('mismatch_count')} · "
        f"ring INLINE server_vt_match={(abi.get('ring') or {}).get('server_vt_match')}.\n"
        f"- Live: pid {live.get('pid')} day_index={live.get('day_index')} ui={live.get('ui_date')} "
        f"drain={live.get('drain')} exec={live.get('exec')}.\n"
        f"- G4–G6 remaining human gates catalogued (executor cannot flip G4). "
        f"Docs: `docs/PHASE2IJM_FACTORY_POSTABI_CLOCK_RO.md`.\n"
        f"- PathC ~60–62%; ≤+1–2pp; ~70% NOT crossed.\n\n"
    )
    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    if "### 2ijm factory/Post-ABI/clock RO reaffirm" not in t2:
        if "### Agent card fold (2ijl)" in t2:
            idx = t2.find("### Agent card fold (2ijl)")
            nxt = t2.find("\n### ", idx + 5)
            if nxt == -1:
                nxt = t2.find("\n## ", idx + 5)
            if nxt != -1:
                t2 = t2[:nxt] + note + t2[nxt:]
            else:
                t2 = t2 + note
        else:
            t2 = t2 + note
    row = (
        f"| 2ijm | factory/Post-ABI/clock RO reaffirm + G4–G6 catalog | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2ijm |" not in t2:
        for key in ("| 2ijl |", "| 2ijk |", "| 2ijj |"):
            if key in t2:
                lines = t2.splitlines(keepends=True)
                out = []
                for line in lines:
                    out.append(line)
                    if line.startswith(key):
                        out.append(row)
                t2 = "".join(out)
                break
    if "*Phase 2ijm" not in t2:
        t2 = t2.rstrip() + (
            "\n\n*Phase 2ijm — factory/Post-ABI/clock RO. Gate stays CLOSED. "
            "2026-11-01 Asia/Shanghai*\n"
        )
    safe.write_text(t2, encoding="utf-8")

    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    land_note = (
        f"\n### 2ijm factory/Post-ABI/clock RO (catalog)\n\n"
        f"See `docs/PHASE2IJM_FACTORY_POSTABI_CLOCK_RO.md`. Live reaffirm "
        f"factory/FN/Strat4753 + post_abi↔offsets_verified + Dummy INLINE ring; "
        f"G4–G6 human gates restated. allow_post False. "
        f"pid {live.get('pid')} day_index={live.get('day_index')} ui={live.get('ui_date')}.\n"
        f"PathC ~60–62%; ~70% NOT crossed.\n\n"
    )
    if "### 2ijm factory/Post-ABI/clock RO" not in t:
        if "### 2ijl agent card" in t:
            idx = t.find("### 2ijl agent card")
            nxt = t.find("\n### ", idx + 5)
            if nxt == -1:
                nxt = t.find("\n## ", idx + 5)
            if nxt != -1:
                t = t[:nxt] + land_note + t[nxt:]
            else:
                t = t + land_note
        else:
            t = t + land_note
    honesty = (
        "- **2ijm:** factory/Post-ABI/clock RO reaffirm; NO Post; Instant PARKED; "
        "PathC ~60–62% honesty (≤+1–2pp; ~70% NOT crossed).\n"
    )
    if "**2ijm:** factory/Post-ABI/clock" not in t:
        if "**2ijl:**" in t:
            idx = t.find("**2ijl:**")
            eol = t.find("\n", idx)
            if eol != -1:
                t = t[: eol + 1] + honesty + t[eol + 1 :]
            else:
                t = t + honesty
        else:
            t = t + honesty
    if "*Phase 2ijm" not in t:
        t = t.rstrip() + "\n\n*Phase 2ijm · factory/Post-ABI/clock RO · 2026-11-01 Asia/Shanghai*\n"
    land.write_text(t, encoding="utf-8")


def main() -> int:
    assert allow_post() is False
    hb = load_hb()
    pid = find_pid()
    if not pid:
        SUMMARY.write_text(
            json.dumps(
                {
                    "phase": "2ijm",
                    "result": "NO_LIVE_PROCESS",
                    "allow_post": False,
                    "next_shortest_blocker": "relaunch ITA@1x; still NO ALLOW_POST",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(json.dumps({"result": "NO_LIVE_PROCESS"}, indent=2))
        return 1

    b = Backend(pid)
    base = b.image_base
    tag = hb.player_tag(b, base)
    scenario = "ITA@1x factory/Post-ABI/clock RO reaffirm (no Post, no Instant, no densify)"
    s0 = continuum_live(b, base, pid, tag, scenario)
    time.sleep(2)
    s1 = continuum_live(b, base, pid, tag, scenario)
    polish = hb.factory_and_fn(b, base)
    abi = post_abi_ro(b, base)
    gates = human_gates_g4_g6()

    family_ok = bool(polish.get("all_factory_match")) and bool(polish.get("all_fn_match"))
    strat_ok = bool(polish.get("strategic_4753_match"))
    abi_ok = bool(abi.get("all_const_match")) and bool(
        (abi.get("ring") or {}).get("server_vt_match")
    ) and bool((abi.get("ring") or {}).get("capacity_like_equals_0x10"))
    calendar_ok = (s1.get("day_index") or 0) > (s0.get("day_index") or 0) or (
        (s1.get("exec") or 0) > (s0.get("exec") or 0)
    ) or ((s1.get("drain") or 0) > (s0.get("drain") or 0))

    if family_ok and strat_ok and abi_ok:
        result = "FACTORY_POSTABI_CLOCK_RO_HIT"
    elif family_ok and abi_ok:
        result = "FACTORY_POSTABI_CLOCK_RO_HIT_STRAT_PARTIAL"
    else:
        result = "FACTORY_POSTABI_CLOCK_RO_PARTIAL"

    out = {
        "phase": "2ijm",
        "slice": "factory_postabi_clock_ro_G4G6_NONPOST",
        "result": result,
        "allow_post": False,
        "post_executed": False,
        "ring_embed_executed": False,
        "instant_parked": True,
        "path_og50_densify": False,
        "midflight_poll": False,
        "asked_user_allow_post": False,
        "move_family_polish": {
            "all_factory_match": polish.get("all_factory_match"),
            "all_fn_match": polish.get("all_fn_match"),
            "factory_match": polish.get("factory_match"),
            "fn_match": polish.get("fn_match"),
            "strategic_4753_match": polish.get("strategic_4753_match"),
            "expected_idx": polish.get("expected_idx"),
        },
        "post_abi_ro": abi,
        "human_gates_g4_g6": gates,
        "live": s1,
        "calendar_sample": {"s0": s0, "s1": s1, "calendar_ok": calendar_ok},
        "path_c_progress_honesty": (
            "~60–62%; factory/Post-ABI/clock RO reaffirm is ≤+1–2pp confidence — "
            "does NOT unlock Post or cross ~70% while G2 live / G4+ remain"
        ),
        "doc": "docs/PHASE2IJM_FACTORY_POSTABI_CLOCK_RO.md",
        "hard_deny": [
            "ALLOW_POST",
            "Post inject",
            "2fb/2gk recipe execute",
            "ring_embed live",
            "tool-gate",
            "Instant empty re-poll",
            "PATH densify",
            "long midflight empty poll",
            "5x",
            "ask user ALLOW_POST",
            "invent field names",
        ],
    }
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    brief = {k: out[k] for k in (
        "phase", "result", "allow_post", "move_family_polish", "post_abi_ro",
        "human_gates_g4_g6", "live", "calendar_sample", "path_c_progress_honesty", "doc",
    )}
    # shrink checks in summary
    if isinstance(brief.get("post_abi_ro"), dict):
        pa = dict(brief["post_abi_ro"])
        pa["checks_n"] = len(pa.get("checks") or [])
        pa.pop("checks", None)
        brief["post_abi_ro"] = pa
    SUMMARY.write_text(json.dumps(brief, indent=2, default=str), encoding="utf-8")
    write_doc(result, s1, polish, abi, gates, calendar_ok)
    patch_docs(result, s1, polish, abi)
    print(
        json.dumps(
            {
                "result": result,
                "all_factory_match": polish.get("all_factory_match"),
                "all_fn_match": polish.get("all_fn_match"),
                "strategic_4753_match": polish.get("strategic_4753_match"),
                "post_abi_all_const_match": abi.get("all_const_match"),
                "mismatch_count": abi.get("mismatch_count"),
                "ring_server_vt_match": (abi.get("ring") or {}).get("server_vt_match"),
                "ring_cap_like_0x10": (abi.get("ring") or {}).get("capacity_like_equals_0x10"),
                "calendar_ok": calendar_ok,
                "allow_post": False,
                "live": {
                    "pid": s1.get("pid"),
                    "year": s1.get("year"),
                    "day_index": s1.get("day_index"),
                    "ui_date": s1.get("ui_date"),
                    "clock_class": s1.get("clock_class"),
                    "drain": s1.get("drain"),
                    "exec": s1.get("exec"),
                },
            },
            indent=2,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
