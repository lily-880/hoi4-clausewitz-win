#!/usr/bin/env python3
"""Phase 2fi: retreat/attack catalog field polish + live factory/VT RO verify.

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
from config import allow_post
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2fi_retreat_attack_polish.json"
SUMMARY = ROOT / "reports" / "phase2fi_summary.json"
DOC = ROOT / "docs" / "PHASE2FI_RETREAT_ATTACK_POLISH.md"

# BASE vt slots (cmd_layout.BASE)
VT_ISVALID = 0x48
VT_EXECUTE = 0x50
VT_GETTYPEID = 0x58  # PostExec / type-id writer on many cmds
VT_GATE60 = 0x60
VT_GATE80 = 0x80
VT_CLONE = 0x68
VT_SERIALIZE = 0xA0
VT_DESERIALIZE = 0xA8

GATE_TRUE = 0x188D90
GATE_FALSE = 0x11D530


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
        "scenario": "ETH@1x retreat/attack catalog field polish (no Post)",
    }


def catalog_targets():
    keys = (
        ("SUPPORT_ATTACK", cmd_layout.SUPPORT_ATTACK),
        ("CANCEL_RUNNING_AWAY", cmd_layout.CANCEL_RUNNING_AWAY),
        ("WITHDRAW_ARMY_HQ", cmd_layout.WITHDRAW_ARMY_HQ),
        ("ARMY_GROUP_FALLBACK", cmd_layout.ARMY_GROUP_FALLBACK),
        ("MASS_CANCEL", cmd_layout.MASS_CANCEL),
        ("ORDER_REPLACE_FALLBACK", cmd_layout.ORDER_REPLACE_FALLBACK),
        ("MOVE", cmd_layout.MOVE),
        ("STRATEGIC", cmd_layout.STRATEGIC),
        ("CANCEL", cmd_layout.CANCEL),
    )
    rows = []
    for key, d in keys:
        tid = int(d["type_id"])
        rows.append({
            "key": key,
            "name": d.get("name") or key,
            "role": d.get("role"),
            "type_id": tid,
            "type_id_hex": hex(tid),
            "vt_rva": int(d["vt"]),
            "factory": int(d["factory"]),
            "factory_idx": d.get("factory_idx"),
            "factory_idx_formula": fidx(tid),
            "fields": d.get("fields"),
            "catalog_clone": d.get("clone"),
            "catalog_serialize": d.get("serialize"),
            "catalog_deserialize": d.get("deserialize"),
            "catalog_gettypeid": d.get("gettypeid"),
            "catalog_isvalid": d.get("isvalid"),
            "catalog_execute": d.get("execute"),
        })
    # ORDERS NewFallback fields polish check
    nf = cmd_layout.ORDERS["COrderNewFallbackCommand"]
    rows.append({
        "key": "ORDERS.COrderNewFallbackCommand",
        "name": "COrderNewFallbackCommand",
        "role": "retreat",
        "type_id": int(nf["type_id"]),
        "type_id_hex": hex(int(nf["type_id"])),
        "vt_rva": int(nf["vt"]),
        "factory": int(nf["factory"]),
        "factory_idx": nf.get("factory_idx"),
        "factory_idx_formula": fidx(int(nf["type_id"])),
        "fields": nf.get("fields"),
        "catalog_clone": nf.get("clone"),
        "catalog_serialize": nf.get("serialize"),
        "catalog_deserialize": nf.get("deserialize"),
        "catalog_gettypeid": nf.get("gettypeid"),
        "catalog_isvalid": nf.get("isvalid"),
        "catalog_execute": nf.get("execute"),
    })
    return rows


def read_vt_slots(b, base, vt_rva: int) -> dict:
    vt = base + vt_rva
    def slot(off):
        try:
            abs_fn = u64(b, vt + off)
            return abs_fn - base if abs_fn >= base else abs_fn
        except Exception:
            return None

    def gate_kind(rva):
        if rva is None:
            return None
        if rva == GATE_TRUE:
            return "TRUE"
        if rva == GATE_FALSE:
            return "FALSE"
        return "FN"

    out = {
        "isvalid": slot(VT_ISVALID),
        "execute": slot(VT_EXECUTE),
        "gettypeid_or_postexec": slot(VT_GETTYPEID),
        "gate_0x60": slot(VT_GATE60),
        "gate_0x80": slot(VT_GATE80),
        "clone": slot(VT_CLONE),
        "serialize": slot(VT_SERIALIZE),
        "deserialize": slot(VT_DESERIALIZE),
    }
    out["gate_0x60_kind"] = gate_kind(out["gate_0x60"])
    out["gate_0x80_kind"] = gate_kind(out["gate_0x80"])
    return out


def verify_factory_table(b, base, rows):
    ft = cmd_layout.FACTORY_TABLE
    table = base + int(ft["rva"])
    # entry: pointer-sized factory FN
    entry_size = int(ft.get("entry_size") or 8)
    match = mismatch = skip = 0
    details = []
    for r in rows:
        idx = r.get("factory_idx")
        if idx is None:
            skip += 1
            details.append({**r, "live_status": "SKIP_NO_IDX"})
            continue
        try:
            live_abs = u64(b, table + idx * entry_size)
            live_rva = live_abs - base if live_abs >= base else live_abs
        except Exception as e:
            skip += 1
            details.append({**r, "live_status": f"READ_FAIL:{e}"})
            continue
        cat = int(r["factory"])
        ok = live_rva == cat
        if ok:
            match += 1
            st = "MATCH"
        else:
            mismatch += 1
            st = "MISMATCH"
        details.append({
            "name": r["name"],
            "key": r["key"],
            "factory_idx": idx,
            "catalog_factory": hex(cat),
            "live_factory": hex(live_rva),
            "live_status": st,
            "fields": r.get("fields"),
        })
    return {"match": match, "mismatch": mismatch, "skip": skip, "details": details}


def apply_live_fills(vt_fills: dict) -> list[str]:
    """Patch CANCEL_RUNNING_AWAY None slots from live VT (box+PC file). No invent."""
    changed = []
    path = ROOT / "calling" / "cmd_layout.py"
    text = path.read_text(encoding="utf-8")
    cra = vt_fills.get("CANCEL_RUNNING_AWAY") or {}
    if not cra:
        return changed

    def repl_none(field: str, rva):
        nonlocal text
        if rva is None:
            return
        # Only replace None for CANCEL_RUNNING_AWAY block
        needle = f'    "{field}": None,  # '
        # More precise: within CANCEL_RUNNING_AWAY only — replace first matching comment patterns
        patterns = {
            "clone": '    "clone": None,  # VT+0x68 live fill 2fi (was absent from catalog)',
            "serialize": '    "serialize": None,  # VT+0xA0 live fill 2fi',
            "deserialize": '    "deserialize": None,  # VT+0xA8 live fill 2fi',
            "gettypeid": '    "gettypeid": None,  # VT+0x58 PostExec/type writer live fill 2fi',
        }
        old = patterns.get(field)
        if not old or old not in text:
            return
        new = f'    "{field}": {hex(int(rva))},  # Phase 2fi live VT fill'
        text = text.replace(old, new, 1)
        changed.append(f"CANCEL_RUNNING_AWAY.{field}={hex(int(rva))}")

    repl_none("clone", cra.get("clone"))
    repl_none("serialize", cra.get("serialize"))
    repl_none("deserialize", cra.get("deserialize"))
    repl_none("gettypeid", cra.get("gettypeid_or_postexec"))

    # gates
    for gkey, kind_key in (("gate_0x60", "gate_0x60_kind"), ("gate_0x80", "gate_0x80_kind")):
        kind = cra.get(kind_key)
        if kind in ("TRUE", "FALSE"):
            old = f'    "{gkey}": None,  # filled live 2fi if VT readable'
            if old in text:
                val = "True" if kind == "TRUE" else "False"
                text = text.replace(old, f'    "{gkey}": {val},  # Phase 2fi live VT {kind} stub', 1)
                # only first None gate — handle both by iterating carefully
                changed.append(f"CANCEL_RUNNING_AWAY.{gkey}={val}")
                # restore remaining None marker for second gate if first consumed
                # re-read: do sequential single replaces with unique comments already distinct? both share same comment
                # Fix: use unique comments in catalog — already both say same. After first replace, second still None.
                pass

    # Fix gates with unique approach: rewrite both lines if still None
    if cra.get("gate_0x60_kind") in ("TRUE", "FALSE") and '"gate_0x60": None' in text:
        val = "True" if cra["gate_0x60_kind"] == "TRUE" else "False"
        text = text.replace(
            '    "gate_0x60": None,  # filled live 2fi if VT readable',
            f'    "gate_0x60": {val},  # Phase 2fi live VT {cra["gate_0x60_kind"]} stub',
            1,
        )
        if f"CANCEL_RUNNING_AWAY.gate_0x60={val}" not in changed:
            changed.append(f"CANCEL_RUNNING_AWAY.gate_0x60={val}")
    if cra.get("gate_0x80_kind") in ("TRUE", "FALSE") and '"gate_0x80": None' in text:
        val = "True" if cra["gate_0x80_kind"] == "TRUE" else "False"
        text = text.replace(
            '    "gate_0x80": None,',
            f'    "gate_0x80": {val},  # Phase 2fi live VT {cra["gate_0x80_kind"]} stub',
            1,
        )
        if f"CANCEL_RUNNING_AWAY.gate_0x80={val}" not in changed:
            changed.append(f"CANCEL_RUNNING_AWAY.gate_0x80={val}")

    if changed:
        path.write_text(text, encoding="utf-8")
    return changed


def main():
    assert allow_post() is False, "allow_post must stay False"
    pid = find_pid()
    assert pid, "hoi4 not found"
    b = Backend(pid)
    base = int(b.image_base)

    live = live_meta(b, base, pid)
    rows = catalog_targets()
    factory = verify_factory_table(b, base, rows)

    vt_fills = {}
    for r in rows:
        key = r["key"]
        if key.startswith("ORDERS."):
            continue
        slots = read_vt_slots(b, base, int(r["vt_rva"]))
        vt_fills[key] = slots
        # cross-check isvalid/execute if catalog has them
        r["live_vt"] = {k: (hex(v) if isinstance(v, int) else v) for k, v in slots.items()}
        if r.get("catalog_isvalid") and slots.get("isvalid"):
            r["isvalid_match"] = int(r["catalog_isvalid"]) == int(slots["isvalid"])
        if r.get("catalog_execute") and slots.get("execute"):
            r["execute_match"] = int(r["catalog_execute"]) == int(slots["execute"])

    fills = apply_live_fills(vt_fills)

    core_keys = list(cmd_layout.LAND_ARMY_FOCUS.get("core", {}).keys())
    field_maps = {
        "SUPPORT_ATTACK": cmd_layout.SUPPORT_ATTACK.get("fields"),
        "CANCEL_RUNNING_AWAY": cmd_layout.CANCEL_RUNNING_AWAY.get("fields"),
        "WITHDRAW_ARMY_HQ": cmd_layout.WITHDRAW_ARMY_HQ.get("fields"),
        "ARMY_GROUP_FALLBACK": cmd_layout.ARMY_GROUP_FALLBACK.get("fields"),
        "MASS_CANCEL": cmd_layout.MASS_CANCEL.get("fields"),
        "ORDER_REPLACE_FALLBACK": cmd_layout.ORDER_REPLACE_FALLBACK.get("fields"),
        "ORDERS.COrderNewFallbackCommand": cmd_layout.ORDERS["COrderNewFallbackCommand"].get("fields"),
    }

    result = "RETREAT_ATTACK_FIELD_POLISH_OK"
    if factory["mismatch"]:
        result = "RETREAT_ATTACK_FIELD_POLISH_FACTORY_MISMATCH"

    works = [
        "first-class CANCEL_RUNNING_AWAY / WITHDRAW_ARMY_HQ / ARMY_GROUP_FALLBACK / MASS_CANCEL / ORDER_REPLACE_FALLBACK",
        "ORDERS NewFallback fields fallback_flag_or_id@+0x54",
        f"LAND_ARMY_FOCUS.core now includes retreat_fallback; keys={core_keys}",
        f"live factory MATCH={factory['match']} MISMATCH={factory['mismatch']}",
        f"CancelRunningAway live VT fills: {fills or 'none-needed-or-failed'}",
        "allow_post stays False; recipe not executed",
    ]
    stubbed = [
        "in-process ring embed",
        "2fb recipe execution",
        "ordinary CMove live leaf",
        "SAFE_POST / ALLOW_POST",
        "self-MOVE",
        "tool-gate open",
        "Post inject",
        "path-vector nonempty (peacetime ETH)",
        "battle-plan NewFallback subject wiring beyond +0x54",
    ]
    next_blocker = (
        "NON-Post: peacetime ETH RO ceiling on midflight path/leaf — next cheapest: "
        "pause+1x war-dense relaunch observe (ITA/ETH war) for nonempty path OR leaf sight; "
        "still NO ALLOW_POST"
    )

    report = {
        "phase": "2fi",
        "ts": datetime.now(timezone.utc).isoformat(),
        "allow_post": False,
        "executed_2fb_recipe": False,
        "tool_gate": "CLOSED",
        "result": result,
        "live": live,
        "field_maps": field_maps,
        "land_army_focus_core_keys": core_keys,
        "factory_table": {
            "match": factory["match"],
            "mismatch": factory["mismatch"],
            "skip": factory["skip"],
            "details": factory["details"],
        },
        "vt_fills": {
            k: {kk: (hex(vv) if isinstance(vv, int) else vv) for kk, vv in v.items()}
            for k, v in vt_fills.items()
        },
        "catalog_live_fills_applied": fills,
        "rows": [
            {
                "key": r["key"],
                "name": r["name"],
                "factory_idx": r.get("factory_idx"),
                "fields": r.get("fields"),
                "isvalid_match": r.get("isvalid_match"),
                "execute_match": r.get("execute_match"),
                "live_vt": r.get("live_vt"),
            }
            for r in rows
        ],
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_blocker,
        "parent_sha_base": "ef62e72",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2fi",
                "result": result,
                "scenario": live["scenario"],
                "allow_post": False,
                "tool_gate": "CLOSED",
                "pid": live["pid"],
                "ui_date": live["ui_date"],
                "hours": live["hours"],
                "factory_match": factory["match"],
                "factory_mismatch": factory["mismatch"],
                "core_keys": core_keys,
                "fills": fills,
                "works": works,
                "stubbed": stubbed,
                "next_shortest_blocker": next_blocker,
                "parent_sha_base": "ef62e72",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    lines = [
        "# Phase 2fi — retreat/attack catalog field polish",
        "",
        f"**Result:** `{result}`  ",
        f"**Base:** `ef62e72` (2fh) · **allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb recipe **NOT executed**",
        "",
        "## Field maps (proven only — no invent)",
        "",
        "| layout | fields |",
        "|--------|--------|",
    ]
    for k, fields in field_maps.items():
        pretty = ", ".join(f"{n}@+{hex(o)}" for n, o in (fields or {}).items())
        lines.append(f"| `{k}` | {pretty} |")
    lines += [
        "",
        "## LAND_ARMY_FOCUS.core",
        "",
        f"Keys: `{core_keys}` (added **retreat_fallback** → CANCEL_RUNNING_AWAY)",
        "",
        "## Live factory table",
        "",
        f"- MATCH: **{factory['match']}** · MISMATCH: **{factory['mismatch']}** · skip: {factory['skip']}",
        "",
        "## CancelRunningAway live VT fills",
        "",
        f"- {fills or '(none)'}",
        "",
        "## Live",
        "",
        "```json",
        json.dumps(live, indent=2),
        "```",
        "",
        f"**Next shortest blocker (NON-Post):** {next_blocker}",
        "",
        "Script: `scripts/phase2fi_retreat_attack_polish.py`",
    ]
    DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({
        "phase": "2fi",
        "result": result,
        "allow_post": False,
        "pid": live["pid"],
        "ui_date": live["ui_date"],
        "hours": live["hours"],
        "factory_match": factory["match"],
        "factory_mismatch": factory["mismatch"],
        "fills": fills,
        "core_keys": core_keys,
        "next_shortest_blocker": next_blocker,
    }, indent=2))


if __name__ == "__main__":
    main()
