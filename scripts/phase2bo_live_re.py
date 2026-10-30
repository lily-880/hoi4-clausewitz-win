#!/usr/bin/env python3
"""Phase 2bo — RO deepen factory / Strategic+Cancel recipes / IsValid / remaining Orders / tool-gate.

Never posts. Never opens command_queue_tool_gate. Never touches speed/HourlyTick/Pause.
Midflight Move remains stubbed; watcher stays armed separately.
"""
from __future__ import annotations
import json, struct, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

from process import Backend, find_pid  # noqa: E402
from capstone import Cs, CS_ARCH_X86, CS_MODE_64  # noqa: E402
import cmd_layout, post_abi, army_subjects  # noqa: E402
from config import allow_post  # noqa: E402

OUT = ROOT / "reports" / "phase2bo_live_re.json"


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def u8(b, a):
    return b.read(a, 1)[0]


def kind_of(b, base, rva):
    blob = b.read(base + rva, 8)
    if blob[:2] in (b"\x33\xc0", b"\x32\xc0"):
        return "FALSE"
    if blob[:2] == b"\xb0\x01":
        return "TRUE"
    return "FN"


def factory_idx(tid):
    ft = cmd_layout.FACTORY_TABLE
    return tid - ft["index_bias"] if tid >= ft["index_bias_sub_if_ge"] else tid


def factory_fn(b, base, tid):
    ft = cmd_layout.FACTORY_TABLE
    i = factory_idx(tid)
    if i < 0 or i > ft["max_index"]:
        return 0
    return u64(b, base + ft["rva"] + i * 8)


def main():
    pid = find_pid("hoi4.exe")
    b = Backend(pid)
    base = int(b.image_base)
    report = {
        "phase": "2bo",
        "posting": "DISABLED",
        "allow_post": allow_post(),
        "speed_rule": "pause or 1x only; never 5x",
        "pid": pid,
        "base": hex(base),
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }

    sess = u64(b, base + post_abi.G_SESSION)
    report["session"] = {
        "ptr": hex(sess),
        "tick": u32(b, sess + 0x84),
        "flag_725": u8(b, sess + 0x725),
        "flag_6cc": u8(b, sess + 0x6CC),
        "flag_726": u8(b, sess + 0x726),
        "auth_3c": u8(b, sess + 0x3C),
    }

    ft = cmd_layout.FACTORY_TABLE
    table = base + ft["rva"]
    nn = sum(1 for i in range(ft["max_index"] + 1) if u64(b, table + i * 8))
    catalog_ok = []
    catalog_fail = []
    checks = []
    for name, meta in [
        ("MOVE", cmd_layout.MOVE),
        ("STRATEGIC", cmd_layout.STRATEGIC),
        ("CANCEL", cmd_layout.CANCEL),
        ("STARTGAME", cmd_layout.STARTGAME),
        ("CHAT", cmd_layout.CHAT),
    ]:
        checks.append((name, meta))
    for k, v in cmd_layout.ORDERS.items():
        checks.append((k, v))
    for k, v in cmd_layout.NEVER_POST.items():
        checks.append((k, v))
    for k, v in cmd_layout.REMAINING_ARMY_ORDERS.items():
        checks.append((k, v))

    for name, meta in checks:
        tid = meta.get("type_id")
        if tid is None:
            catalog_fail.append({"name": name, "err": "no type_id"})
            continue
        fn = factory_fn(b, base, tid)
        expect = meta.get("factory")
        idx = factory_idx(tid)
        row = {
            "name": name,
            "type_id": hex(tid),
            "idx": idx,
            "fn": hex(fn - base) if fn else None,
            "expect": hex(expect) if expect else None,
            "match": (fn == base + expect) if expect and fn else None,
        }
        if meta.get("vt") and fn:
            row["vt"] = hex(meta["vt"])
            row["vt_readable"] = u64(b, base + meta["vt"]) != 0
        if row["match"] is False or (expect and not fn):
            catalog_fail.append(row)
        else:
            catalog_ok.append(row)

    report["factory"] = {
        "table": hex(ft["rva"]),
        "lookup": hex(ft["lookup"]),
        "bias": hex(ft["index_bias"]),
        "thresh": hex(ft["index_bias_sub_if_ge"]),
        "max_index": ft["max_index"],
        "non_null": nn,
        "catalog_ok": len(catalog_ok),
        "catalog_fail": catalog_fail,
        "ok_names": [r["name"] for r in catalog_ok],
    }

    isv = {}
    pairs = [
        ("CMoveCommand", cmd_layout.MOVE, cmd_layout.ISVALID_PATHS["CMoveCommand"]["rva"]),
        ("CStrategicRedeploymentCommand", cmd_layout.STRATEGIC,
         cmd_layout.ISVALID_PATHS["CStrategicRedeploymentCommand"]["rva"]),
        ("CCancelMovementCommand", cmd_layout.CANCEL,
         cmd_layout.ISVALID_PATHS["CCancelMovementCommand"]["rva"]),
    ]
    for name, meta, rva in pairs:
        live = u64(b, base + meta["vt"] + 0x48) - base
        isv[name] = {
            "catalog_rva": hex(rva),
            "live_vt48": hex(live),
            "match": live == rva,
            "kind": kind_of(b, base, live),
        }
    for k, v in cmd_layout.ORDERS.items():
        live = u64(b, base + v["vt"] + 0x48) - base
        isv[k] = {
            "live_vt48": hex(live),
            "kind": kind_of(b, base, live),
            "execute": hex(u64(b, base + v["vt"] + 0x50) - base),
            "execute_match": (u64(b, base + v["vt"] + 0x50) - base) == v.get("execute", -1),
        }
    pmeta = cmd_layout.NEVER_POST["CPauseGame"]
    plive = u64(b, base + pmeta["vt"] + 0x48) - base
    isv["CPauseGame"] = {
        "live_vt48": hex(plive),
        "kind": kind_of(b, base, plive),
        "catalog": hex(pmeta["isvalid"]),
        "match": plive == pmeta["isvalid"],
        "never_post": True,
    }
    wrap = cmd_layout.ISVALID_PATHS["wrap"]
    isv["wrap"] = {
        "rva": hex(wrap),
        "readable": len(b.read(base + wrap, 16)) == 16,
        "session_auth_3c": report["session"]["auth_3c"],
    }
    report["isvalid"] = isv

    armies = army_subjects.iter_armies_by_index(b, base, 1000, 1200, 15)
    recipes = {"hai_armies": len(armies), "samples": []}
    if armies:
        a0 = armies[0]
        dest = a0["province_id"]
        recipes["samples"].append({
            "army_index": a0["index"],
            "handle": list(a0["handle"]),
            "province_id": a0["province_id"],
            "move": army_subjects.move_action_recipe(a0),
            "strategic": army_subjects.strategic_redeploy_recipe(a0, dest),
            "cancel_one": army_subjects.cancel_movement_recipe([a0]),
            "cancel_all_hai": army_subjects.cancel_movement_recipe(armies),
        })
    recipes["isvalid_notes"] = army_subjects.isvalid_path_notes()
    report["army_recipes"] = recipes

    rem = {}
    for name, meta in cmd_layout.REMAINING_ARMY_ORDERS.items():
        live_isv = u64(b, base + meta["vt"] + 0x48) - base
        live_exec = u64(b, base + meta["vt"] + 0x50) - base
        rem[name] = {
            "type_id": hex(meta["type_id"]),
            "factory": hex(meta["factory"]),
            "vt": hex(meta["vt"]),
            "factory_match": factory_fn(b, base, meta["type_id"]) == base + meta["factory"],
            "isvalid": hex(live_isv),
            "isvalid_kind": kind_of(b, base, live_isv),
            "execute": hex(live_exec),
            "serialize_proof": "stubbed",
        }
    report["remaining_army_orders"] = rem

    report["tool_gate"] = {
        "command_queue_tool_gate": "open_gap_but_DISABLED",
        "status": "CLOSED_NOT_OPENED",
        "allow_post": allow_post(),
        "blocks": [
            {
                "id": "midflight_CMoveCommand",
                "status": "STUBBED",
                "note": "DX11 ignores synthetic input; watcher armed RO; no injection this phase",
            },
            {
                "id": "serialize_recreate_roundtrip",
                "status": "open",
                "note": "factory+lookup deepened; hand-built recreate still unproven",
            },
            {
                "id": "CLAUSEWITZ_ALLOW_POST",
                "status": "hard-deny",
                "note": "config.allow_post always False even if env set",
            },
            {
                "id": "session_725",
                "status": "necessary_not_sufficient",
                "live": report["session"]["flag_725"],
                "note": "725==1 on live SP; still not enough to enable",
            },
            {
                "id": "never_post_expanded",
                "status": "closed",
                "note": "PauseGame+type_ids for all speed/Hourly/Ping; IsValid TRUE on Pause",
            },
        ],
        "action_this_phase": "analysis only — gate NOT opened",
    }

    report["midflight"] = {
        "status": "stubbed",
        "watcher": "phase2bm_midflight_ready armed separately; no wake",
        "input_injection": False,
    }

    report["works"] = [
        "factory table deepen (bias 0x2328 / thresh 0x2710 / max 0x2AF7 / non_null live)",
        "factory->fn match for MOVE/STRATEGIC/CANCEL/ORDERS/NEVER_POST/REMAINING",
        "IsValid wrap + vt+0x48 live for Move/Strategic/Cancel/Orders/Pause",
        "army Strategic+Cancel recipes (HAI)",
        "CPauseGame NEVER_POST type_id 0x29ec IsValid TRUE",
        "NEVER_POST type_ids for Inc/Dec/Set/Hourly/Ping",
        "tool_gate safer analysis; gate stays DISABLED",
        "allow_post False hard-deny",
    ]
    report["stubbed"] = [
        "midflight_CMoveCommand sample (DX11)",
        "REMAINING_ARMY_ORDERS serialize/deserialize/clone full proof",
        "serialize->recreate round-trip into Dummy ring",
        "command_queue_tool_gate enable",
    ]

    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "out": str(OUT),
        "allow_post": report["allow_post"],
        "factory_ok": report["factory"]["catalog_ok"],
        "factory_fail": report["factory"]["catalog_fail"],
        "non_null": nn,
        "hai_armies": recipes["hai_armies"],
        "remaining": len(rem),
        "tool_gate": report["tool_gate"]["status"],
        "flag_725": report["session"]["flag_725"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
