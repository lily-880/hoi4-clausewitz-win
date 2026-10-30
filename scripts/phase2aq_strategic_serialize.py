"""Phase 2aq — CStrategicRedeploymentCommand + CUnitStrategicMoveAction serialize (RO); posting DISABLED."""
from __future__ import annotations
import argparse, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "calling"))

# CStrategicRedeploymentCommand
CMD_VT = 0x2A2D818
CMD_TYPE_ID = 0x35B9
CMD_SIZE = 0x50
CMD_FACTORY = 0x13FB580
CMD_CLONE = 0x13F9C10
CMD_ACTION_EMBED = 0x28
# Shared with CMoveCommand for Execute / serialize thunks (dispatch into embedded action)
CMD_EXECUTE_THUNK = 0x13FC990  # -> action.vt+0x48
CMD_SERIALIZE_THUNK = 0x1404590  # add rcx,0x28; jmp [rax+0xc0]
CMD_DESERIALIZE_THUNK = 0x1403570

# CUnitStrategicMoveAction (RTTI .?AVCUnitStrategicMoveAction@@)
ACTION_VT = 0x2A1F7E8
ACTION_TYPE_ID = 0x364A  # token unit_strategic_move_action
ACTION_SIZE = 0x28
ACTION_CTOR = 0x12C1A40
ACTION_SERIALIZE = 0x12C3AA0
ACTION_DESERIALIZE = 0x12C3740
ACTION_APPLY = 0x12C2C20  # vt+0x48

ACTION_FIELDS = [
    {"off": 0x10, "token": 0x289D, "name": "army", "kind": "handle", "writer": 0x2285670,
     "note": "army handle (NOT unit 0x28A3 like CUnitMoveAction)"},
    {"off": 0x18, "token": 0x2840, "name": "province", "kind": "i32", "writer": 0x25458A0,
     "note": "single province id (NOT pdxarray like Move)"},
    {"off": 0x1C, "token": 0x29F1, "name": "clear", "kind": "bool", "writer": 0x2546110, "ctor_default": 1},
    {"off": 0x20, "token": 0x37BC, "name": "move_priority", "kind": "enum_i32", "enum_fn": 0x19D7560,
     "writer": 0x25455A0, "default_skip": 1, "ctor_default": 1},
]

LIVE_CHECKS = {
    "army_tok": (0x12C3AB3, bytes.fromhex("ba9d280000")),
    "lea_handle": (0x12C3ABD, bytes.fromhex("488d5310")),
    "prov_load": (0x12C3AC9, bytes.fromhex("448b4318")),
    "prov_tok": (0x12C3ACD, bytes.fromhex("ba40280000")),
    "clear_ld": (0x12C3ADA, bytes.fromhex("440fb6431c")),
    "clear_tok": (0x12C3ADF, bytes.fromhex("baf1290000")),
    "prio_ld": (0x12C3AEC, bytes.fromhex("8b5320")),
    "prio_cmp1": (0x12C3AEF, bytes.fromhex("83fa01")),
    "prio_tok": (0x12C3AFE, bytes.fromhex("babc370000")),
    "factory_size": (0x13FB586, bytes.fromhex("b950000000")),  # mov ecx, 0x50
    "action_standalone_size": (0x12C2538, bytes.fromhex("b928000000")),  # mov ecx, 0x28
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "research", "re-dumps", "phase2aq_report.json"))
    args = ap.parse_args()
    layout = []
    for f in ACTION_FIELDS:
        e = dict(f)
        e["cmd_off"] = CMD_ACTION_EMBED + f["off"]
        e["token_hex"] = hex(f["token"])
        e["off_hex"] = hex(f["off"])
        layout.append(e)
    out = {
        "phase": "2aq",
        "posting": "DISABLED",
        "command_queue": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "CStrategicRedeploymentCommand": {
            "vt": hex(CMD_VT),
            "type_id": hex(CMD_TYPE_ID),
            "size": hex(CMD_SIZE),
            "factory": hex(CMD_FACTORY),
            "clone": hex(CMD_CLONE),
            "action_embed": hex(CMD_ACTION_EMBED),
            "Execute_thunk": hex(CMD_EXECUTE_THUNK),
            "serialize_thunk": hex(CMD_SERIALIZE_THUNK),
            "deserialize_thunk": hex(CMD_DESERIALIZE_THUNK),
            "note": "Execute/serialize thunks shared with CMoveCommand; dispatch into embedded action",
        },
        "CUnitStrategicMoveAction": {
            "rtti": ".?AVCUnitStrategicMoveAction@@",
            "vt": hex(ACTION_VT),
            "type_id": hex(ACTION_TYPE_ID),
            "type_token_name": "unit_strategic_move_action",
            "size": hex(ACTION_SIZE),
            "ctor": hex(ACTION_CTOR),
            "serialize": hex(ACTION_SERIALIZE),
            "deserialize": hex(ACTION_DESERIALIZE),
            "Apply_vt48": hex(ACTION_APPLY),
            "fields": layout,
            "contrast_vs_CUnitMoveAction": {
                "handle_token": "army 0x289d vs unit 0x28a3",
                "province": "single i32 vs pdxarray+path",
                "size": "0x28 vs ~0x60",
                "no_path_vector": True,
                "no_safe_avoid_sticky_bools": True,
            },
        },
        "safe_enable": "NOT proven — posting DISABLED",
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
        # token names
        def u64(a):
            return struct.unpack("<Q", b.read(a, 8))[0]
        def token_name(tok):
            arr = u64(base + 0x368F5A0)
            e = arr + tok * 32
            size = u64(e + 16)
            cap = u64(e + 24)
            if cap > 15 or size > 15:
                return b.read(u64(e), min(int(size), 80)).split(b"\x00")[0].decode("latin1", "replace")
            return b.read(e, int(size)).decode("latin1", "replace")
        out["token_names"] = {hex(f["token"]): token_name(f["token"]) for f in ACTION_FIELDS}
        out["token_names"][hex(ACTION_TYPE_ID)] = token_name(ACTION_TYPE_ID)
        b.close()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
    print("wrote", args.out)
    print("CStrategicRedeploymentCommand size", hex(CMD_SIZE), "embeds CUnitStrategicMoveAction@+0x28")
    for e in layout:
        print(f"  action+{e['off_hex']} cmd+{hex(e['cmd_off'])} {e['name']} ({e['kind']}) token {e['token_hex']}")
    if args.live:
        print("checks", out["all_checks_ok"])
        for n, v in out["live_byte_checks"].items():
            print(f"  {n}: {'OK' if v['ok'] else 'FAIL'}")


if __name__ == "__main__":
    main()
