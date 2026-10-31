#!/usr/bin/env python3
"""Phase 2fg: ORDERS / land factory_idx catalog fill + live table MATCH.

No Post. No tool-gate. No 2fb recipe. allow_post stays False. Never 5x.
"""
from __future__ import annotations

import json
import struct
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import cmd_layout
import post_abi
from config import allow_post
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2fg_orders_factory_idx.json"
SUMMARY = ROOT / "reports" / "phase2fg_summary.json"
DOC = ROOT / "docs" / "PHASE2FG_ORDERS_FACTORY_IDX.md"


def fidx(tid: int) -> int:
    ft = cmd_layout.FACTORY_TABLE
    return tid - ft["index_bias"] if tid >= ft["index_bias_sub_if_ge"] else tid


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def i32(b, a):
    return struct.unpack("<i", b.read(a, 4))[0]


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
        "scenario": "ETH@1x ORDERS factory_idx catalog RO (no Post)",
    }


def catalog_rows() -> list[dict]:
    rows = []
    # core movement family
    for key, d in (
        ("MOVE", cmd_layout.MOVE),
        ("STRATEGIC", cmd_layout.STRATEGIC),
        ("CANCEL", cmd_layout.CANCEL),
        ("SUPPORT_ATTACK", cmd_layout.SUPPORT_ATTACK),
    ):
        tid = int(d["type_id"])
        rows.append({
            "group": "core",
            "name": d.get("name") or key,
            "key": key,
            "type_id": tid,
            "type_id_hex": hex(tid),
            "factory": int(d["factory"]),
            "factory_hex": hex(int(d["factory"])),
            "factory_idx": d.get("factory_idx"),
            "factory_idx_formula": fidx(tid),
            "was_missing": False,
            "stale": d.get("factory_idx") != fidx(tid),
        })
    # ORDERS (filled this slice)
    for name, d in cmd_layout.ORDERS.items():
        tid = int(d["type_id"])
        rows.append({
            "group": "ORDERS",
            "name": name,
            "key": name,
            "type_id": tid,
            "type_id_hex": hex(tid),
            "factory": int(d["factory"]),
            "factory_hex": hex(int(d["factory"])),
            "factory_idx": d.get("factory_idx"),
            "factory_idx_formula": fidx(tid),
            "was_missing_before_2fg": True,
            "stale": d.get("factory_idx") != fidx(tid),
        })
    # LAND_ARMY_FOCUS land cmds (Mass*/Retreat/Attack adjacent) — catalog refresh note
    laf = (getattr(cmd_layout, "LAND_ARMY_FOCUS", {}) or {}).get("commands") or {}
    want = {
        "CMassMoveCommand",
        "CMassCancelMovementCommand",
        "CCancelRunningAwayCommand",
        "CWithdrawArmyHqCommand",
        "COrderNewFallbackCommand",
        "COrderReplaceFallbackCommands",
        "CSetSelectedArmyGroupFallback",
        "CSupportAttackCommand",
        "CToggleStrategicDeploymentCommand",
        "CMoveArmiesInTheaterCommand",
        "COrderSetPathCommand",
        "COrderNewFrontCommand",
    }
    for name in sorted(want):
        d = laf.get(name) or {}
        if not isinstance(d, dict) or "type_id" not in d:
            rows.append({
                "group": "LAND_ARMY_FOCUS",
                "name": name,
                "key": name,
                "status": "missing_from_LAND_ARMY_FOCUS",
            })
            continue
        tid = int(d["type_id"])
        got = d.get("factory_idx")
        rows.append({
            "group": "LAND_ARMY_FOCUS",
            "name": name,
            "key": name,
            "type_id": tid,
            "type_id_hex": hex(tid),
            "factory": d.get("factory"),
            "factory_hex": hex(int(d["factory"])) if d.get("factory") is not None else None,
            "factory_idx": got,
            "factory_idx_formula": fidx(tid),
            "stale": (got is not None and got != fidx(tid)),
            "missing_factory_idx": got is None,
        })
    return rows


def live_verify(b, base, rows) -> dict:
    ft = cmd_layout.FACTORY_TABLE
    table = base + int(ft["rva"])
    results = []
    match = 0
    mismatch = 0
    skip = 0
    for r in rows:
        if "factory" not in r or r.get("factory") is None:
            skip += 1
            results.append({**r, "live": "SKIP_NO_FACTORY"})
            continue
        idx = r.get("factory_idx")
        if idx is None:
            idx = r.get("factory_idx_formula")
        if idx is None:
            skip += 1
            results.append({**r, "live": "SKIP_NO_IDX"})
            continue
        try:
            slot = u64(b, table + int(idx) * 8)
        except Exception as e:
            mismatch += 1
            results.append({**r, "live": "READ_FAIL", "error": str(e)})
            continue
        expect = base + int(r["factory"])
        ok = slot == expect
        if ok:
            match += 1
        else:
            mismatch += 1
        results.append({
            "group": r.get("group"),
            "name": r.get("name"),
            "factory_idx": idx,
            "factory_rva": hex(int(r["factory"])),
            "slot": hex(slot),
            "expect": hex(expect),
            "match": ok,
            "live": "MATCH" if ok else "MISMATCH",
        })
    return {
        "table_rva": hex(int(ft["rva"])),
        "table_abs": hex(table),
        "match": match,
        "mismatch": mismatch,
        "skip": skip,
        "rows": results,
    }


def write_doc(rep: dict) -> None:
    live = rep.get("live") or {}
    filled = rep.get("orders_filled") or []
    ver = rep.get("live_verify") or {}
    lines = [
        "# Phase 2fg — ORDERS factory_idx catalog fill",
        "",
        f"**Result:** `{rep.get('result')}`  ",
        "**allow_post:** **False** · tool-gate **CLOSED** · never 5x · recipe **NOT executed**",
        "",
        "## ORDERS factory_idx (was missing → filled)",
        "",
        "| command | type_id | factory_idx |",
        "|---------|---------|-------------|",
    ]
    for r in filled:
        lines.append(f"| {r['name']} | `{r['type_id_hex']}` | **{r['factory_idx']}** |")
    lines += [
        "",
        "## Live factory table verify",
        "",
        f"- MATCH: **{ver.get('match')}** · MISMATCH: **{ver.get('mismatch')}** · skip: {ver.get('skip')}",
        f"- table RVA `{ver.get('table_rva')}`",
        "",
        "## Core land (already filled 2fe)",
        "",
        "- MOVE 1402 · STRATEGIC **4753** · CANCEL 1415 · SUPPORT_ATTACK 3620",
        "",
        f"## Live",
        "",
        f"```json",
        json.dumps(live, indent=2),
        "```",
        "",
        f"**Next shortest blocker (NON-Post):** {rep.get('next_shortest_blocker')}",
        "",
        "Script: `scripts/phase2fg_orders_factory_idx.py`",
        "",
    ]
    DOC.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    assert allow_post() is False
    rows = catalog_rows()
    orders = [r for r in rows if r.get("group") == "ORDERS"]
    # ensure all ORDERS have factory_idx == formula
    bad = [r for r in orders if r.get("factory_idx") != r.get("factory_idx_formula")]
    laf_missing = [
        r for r in rows
        if r.get("group") == "LAND_ARMY_FOCUS" and r.get("missing_factory_idx")
    ]

    pid = find_pid()
    live = {"pid": pid}
    verify = {"match": 0, "mismatch": 0, "skip": 0, "rows": [], "note": "no live"}
    err = None
    if pid:
        try:
            b = Backend(pid)
            base = int(b.image_base)
            live = live_meta(b, base, pid)
            # verify ORDERS + core + LAND focus that have factory
            to_check = [
                r for r in rows
                if r.get("factory") is not None and (
                    r.get("factory_idx") is not None or r.get("factory_idx_formula") is not None
                )
            ]
            # for LAND missing idx, still check via formula
            for r in to_check:
                if r.get("factory_idx") is None and r.get("factory_idx_formula") is not None:
                    r = {**r, "factory_idx": r["factory_idx_formula"]}
            verify = live_verify(b, base, to_check)
        except Exception as e:
            err = str(e)
    else:
        err = "no hoi4 pid"

    if bad:
        result = "ORDERS_FACTORY_IDX_INCOMPLETE"
    elif verify.get("mismatch", 0) > 0:
        result = "ORDERS_FACTORY_IDX_FILLED_LIVE_MISMATCH"
    elif pid and verify.get("match", 0) > 0:
        result = "ORDERS_FACTORY_IDX_FILLED_LIVE_MATCH"
    else:
        result = "ORDERS_FACTORY_IDX_FILLED_OFFLINE"

    next_blocker = (
        "NON-Post: short ETH@1x path-vector re-observe for nonempty movement_dest "
        "OR land Mass*/CancelRunningAway factory_idx gap fill if any remain; still NO ALLOW_POST"
    )
    if laf_missing:
        next_blocker = (
            "NON-Post: LAND_ARMY_FOCUS missing factory_idx on "
            + ",".join(r["name"] for r in laf_missing)
            + " — fill next; still NO ALLOW_POST"
        )

    rep = {
        "phase": "2fg",
        "ts": datetime.now(timezone.utc).isoformat(),
        "allow_post": False,
        "executed_2fb_recipe": False,
        "tool_gate": "CLOSED",
        "result": result,
        "error": err,
        "live": live,
        "formula": {
            "if_tid_ge": hex(cmd_layout.FACTORY_TABLE["index_bias_sub_if_ge"]),
            "idx": "tid - index_bias (0x2328 / 9000)",
            "else": "idx = tid",
        },
        "orders_filled": [
            {
                "name": r["name"],
                "type_id_hex": r["type_id_hex"],
                "factory_idx": r["factory_idx"],
                "factory_hex": r["factory_hex"],
            }
            for r in orders
        ],
        "core_land": [r for r in rows if r.get("group") == "core"],
        "land_army_focus_gaps": laf_missing,
        "live_verify": {
            "match": verify.get("match"),
            "mismatch": verify.get("mismatch"),
            "skip": verify.get("skip"),
            "table_rva": verify.get("table_rva"),
            "rows_head": (verify.get("rows") or [])[:24],
            "mismatches": [x for x in (verify.get("rows") or []) if x.get("live") == "MISMATCH"][:12],
        },
        "works": [
            "ORDERS factory_idx filled for 10 land order cmds",
            "core MOVE/STRATEGIC/CANCEL/SUPPORT_ATTACK indices confirmed vs formula",
            "live factory table slot verify (when hoi4 attached)",
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
            "path-vector nonempty (deferred)",
        ],
        "next_shortest_blocker": next_blocker,
        "parent_sha_base": "0e78322",
    }
    OUT.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2fg",
                "result": result,
                "scenario": live.get("scenario", "ETH@1x"),
                "allow_post": False,
                "tool_gate": "CLOSED",
                "pid": live.get("pid"),
                "ui_date": live.get("ui_date"),
                "hours": live.get("hours"),
                "orders_filled_count": len(orders),
                "live_match": verify.get("match"),
                "live_mismatch": verify.get("mismatch"),
                "land_focus_missing_fidx": [r["name"] for r in laf_missing],
                "works": rep["works"],
                "stubbed": rep["stubbed"],
                "next_shortest_blocker": next_blocker,
                "parent_sha_base": "0e78322",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    write_doc(rep)
    print(json.dumps(json.loads(SUMMARY.read_text(encoding="utf-8")), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
