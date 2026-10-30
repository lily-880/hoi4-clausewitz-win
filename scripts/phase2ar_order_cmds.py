"""Phase 2ar — Order* command sizes + serialize field layouts (RO); posting DISABLED."""
from __future__ import annotations
import argparse, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "calling"))

# Sizes from Clone (vt+0x68) mov ecx,imm; serialize RVAs from vt+0xa0
ORDER_CMDS = {
    "COrderExecuteCommand": {
        "vt": 0x2A85468, "type_id": 0x3040, "size": 0x38,
        "clone": 0x18CDBD0, "serialize": 0x18E87C0, "deserialize": 0x18E2100, "Execute": 0x18D6430,
        "fields": [
            {"off": 0x30, "token": 0x3036, "name": "order_index", "kind": "i32"},
            {"off": 0x34, "token": 0x3041, "name": "execute_order", "kind": "bool"},
            {"off": 0x35, "token": 0x2B97, "name": "all", "kind": "bool"},
        ],
    },
    "COrderAssignCommand": {
        "vt": 0x2A84498, "type_id": 0x303E, "size": 0x50,
        "clone": 0x18CD5B0, "serialize": 0x18E80F0, "deserialize": 0x18E1A70, "Execute": 0x18D41B0,
        "fields": [
            {"off": 0x28, "name": "units_data", "kind": "ptr_to_handles"},
            {"off": 0x34, "name": "units_count", "kind": "i32", "token_each": 0x28A3},
            {"off": 0x48, "token": 0x3036, "name": "order_index", "kind": "i32"},
            {"off": 0x4C, "token": 0x3CF3, "name": "assign_to_minimum_order", "kind": "bool"},
        ],
    },
    "COrderUnassignCommand": {
        "vt": 0x2A84550, "type_id": 0x304D, "size": 0x50,
        "clone": 0x18CEBB0, "serialize": 0x18E91B0, "deserialize": 0x18E2EE0, "Execute": 0x18DB050,
        "fields": [
            {"off": 0x28, "name": "units_data", "kind": "ptr_to_handles"},
            {"off": 0x34, "name": "units_count", "kind": "i32", "token_each": 0x28A3},
            {"off": 0x48, "token": 0x3683, "name": "unassign_group", "kind": "bool"},
            {"off": 0x49, "token": 0x3D9E, "name": "unassign_army_group_instances", "kind": "bool"},
        ],
    },
    "COrderDeleteCommand": {
        "vt": 0x2A843E0, "type_id": 0x303F, "size": 0x38,
        "clone": 0x18CDA90, "serialize": 0x18E86E0, "deserialize": 0x18E1FE0, "Execute": 0x18D5FE0,
        "fields": [
            {"off": 0x30, "token": 0x3036, "name": "order_index", "kind": "i32"},
        ],
    },
    "COrderNewFrontCommand": {
        "vt": 0x2A84B10, "type_id": 0x3327, "size": 0x70,
        "clone": 0x18CE0E0, "serialize": 0x18E8AF0, "deserialize": 0x18E25C0, "Execute": 0x18D9000,
        "fields": [
            {"off": 0x38, "name": "units_data", "kind": "ptr_to_handles"},
            {"off": 0x44, "name": "units_count", "kind": "i32", "token_each": 0x28A3},
            {"off": 0x50, "token": 0x174, "name": "path", "kind": "pdxarray"},
            {"off": 0x68, "token": 0x152, "name": "attach", "kind": "i32"},
            {"off": 0x6C, "token": 0x3364, "name": "split_from", "kind": "bool"},
            {"off": 0x6D, "token": 0x36CC, "name": "blitz", "kind": "bool"},
            {"off": 0x6E, "token": 0x38EC, "name": "withdraw", "kind": "bool"},
            {"off": 0x30, "token": 0x3A31, "name": "sub_group", "kind": "gated"},
        ],
    },
    "COrderNewRootCommand": {
        "vt": 0x2A84DF0, "type_id": 0x3328, "size": 0x70,
        "clone": 0x18CE200, "serialize": 0x18E8BF0, "deserialize": 0x18E26D0, "Execute": 0x18D99C0,
        "fields_note": "same family as NewFront (size 0x70); path/units pattern",
    },
    "COrderNewFallbackCommand": {
        "vt": 0x2A84C80, "type_id": 0x33D7, "size": 0x60,
        "clone": 0x18CDFF0, "serialize": 0x18E8A60, "deserialize": 0x18E2500, "Execute": 0x18D8FC0,
    },
    "COrderGroupCommand": {
        "vt": 0x2A83D68, "type_id": 0x2ECF, "size": 0x60,
        "clone": 0x18CDC70, "serialize": 0x18E8830, "deserialize": 0x18E21D0, "Execute": 0x18D64F0,
        "fields_note": "theatre/theater_group/army_group handles at +0x48/+0x50/+0x58",
    },
    "CArmyGroupCommand": {
        "vt": 0x2A83ED8, "type_id": 0x3861, "size": 0x80,
        "clone": 0x18CCCC0, "serialize": 0x18E7A50, "deserialize": 0x18E0E60, "Execute": 0x18D25D0,
    },
    "CSetArmyLeaderCommand": {
        "vt": 0x2A85520, "type_id": 0x3051, "size": 0x40,
        "clone": 0x18CEF00, "serialize": 0x18E9390, "deserialize": 0x18E3210, "Execute": 0x18DB2C0,
        "fields": [
            {"off": 0x28, "token": 0x28B7, "name": "leader", "kind": "handle_gated"},
            {"off": 0x38, "token": 0x282B, "name": "deploy_army_hq", "kind": "bool"},
        ],
    },
}

# Live byte checks on key immediates
LIVE_CHECKS = {
    "Assign_size": (0x18CD5BD, bytes.fromhex("b950000000")),
    "Execute_size": (0x18CDBD9, bytes.fromhex("b938000000")),
    "NewFront_size": (0x18CE0ED, bytes.fromhex("b970000000")),
    "Assign_order_idx_tok": (0x18E811E, bytes.fromhex("ba36300000")),
    "Execute_order_idx_tok": (0x18E87ED, bytes.fromhex("ba36300000")),
    "Execute_exec_tok": (0x18E87FF, bytes.fromhex("ba41300000")),
    "NewFront_path_tok": (0x18E8B1D, bytes.fromhex("ba74010000")),
    "Unassign_unit_tok": (0x18E91F4, bytes.fromhex("baa3280000")),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "research", "re-dumps", "phase2ar_report.json"))
    args = ap.parse_args()
    catalog = {}
    for name, info in ORDER_CMDS.items():
        e = {k: (hex(v) if isinstance(v, int) else v) for k, v in info.items() if k != "fields"}
        if "fields" in info:
            e["fields"] = [
                {**f, **({"token_hex": hex(f["token"])} if "token" in f else {}),
                 **({"token_each_hex": hex(f["token_each"])} if "token_each" in f else {}),
                 "off_hex": hex(f["off"])}
                for f in info["fields"]
            ]
        catalog[name] = e
    out = {
        "phase": "2ar",
        "posting": "DISABLED",
        "command_queue": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "order_commands": catalog,
        "safe_enable": "NOT proven — posting DISABLED",
        "notes": [
            "Sizes proven via Clone mov ecx,imm",
            "ba3f000000 near ser start is a writer preamble (token 0x3f), not a named gameplay field",
            "Assign/Unassign unit lists match CancelMovement pattern (ptr+count, token unit each)",
        ],
    }
    if args.live:
        from process import Backend, find_pid
        b = Backend(find_pid("hoi4.exe"))
        base = b.image_base
        verified = {}
        for n, (r, e) in LIVE_CHECKS.items():
            got = b.read(base + r, len(e))
            verified[n] = {"rva": hex(r), "ok": got == e, "got": got.hex()}
        out["live_byte_checks"] = verified
        out["all_checks_ok"] = all(v["ok"] for v in verified.values())
        b.close()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
    print("wrote", args.out)
    for name, info in ORDER_CMDS.items():
        print(f"  {name}: size={hex(info['size'])} ser={hex(info['serialize'])}")
    if args.live:
        print("checks", out["all_checks_ok"])
        for n, v in out["live_byte_checks"].items():
            print(f"  {n}: {'OK' if v['ok'] else 'FAIL'}")


if __name__ == "__main__":
    main()
