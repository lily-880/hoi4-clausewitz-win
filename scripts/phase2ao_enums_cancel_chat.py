"""Phase 2ao — move_priority enum + Cancel/Chat serialize fields (RO); posting DISABLED."""
from __future__ import annotations
import argparse, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "calling"))

MOVE_PRIORITY = {
    0: {"token": 0x37BD, "name": "front_order"},
    1: {"token": 0x77, "name": "normal", "serialize_default_skip": True},
    2: {"token": 0x37BE, "name": "player_order"},
    3: {"token": 0x4C91, "name": "ai_player_order"},
}

CANCEL_FIELDS = [
    {"off": 0x28, "name": "units_data", "kind": "ptr_to_handles"},
    {"off": 0x34, "name": "units_count", "kind": "i32", "token_each": 0x28A3},
    {"off": 0x40, "name": "sticky", "kind": "bool", "token": 0x368F},
]

CHAT_FIELDS = [
    {"off": 0x28, "name": "message", "kind": "std_string", "token": 0xDD},
    {"off": 0x38, "name": "message_len_gate", "kind": "size_t"},
    {"off": 0x64, "name": "user", "kind": "i32", "token": 0xE2},
    {"off": 0x68, "name": "channel", "kind": "i32", "token": 0xD6},
    {"off": 0x6C, "name": "color", "kind": "i32", "token": 0x56},
    {"off": 0x74, "name": "datetime", "kind": "bool", "token": 0xD9},
    {"off": 0x70, "name": "receiver", "kind": "i32", "token": 0xC6},
    {"off": 0x78, "name": "sender", "kind": "stringish", "token": 0x240},
    {"off": 0x60, "name": "chat_localize_on_receipt", "kind": "bool", "token": 0x302E},
    {"off": 0x54, "name": "key_value_pairs_gate", "kind": "i32", "token": 0x2E2},
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument(
        "--out",
        default=os.path.join(ROOT, "research", "re-dumps", "phase2ao_report.json"),
    )
    args = ap.parse_args()
    out = {
        "phase": "2ao",
        "posting": "DISABLED",
        "command_queue": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "FN_MOVE_PRIORITY_ENUM": hex(0x19D7560),
        "move_priority": {str(k): v for k, v in MOVE_PRIORITY.items()},
        "CCancelMovement_SERIALIZE": hex(0x1404130),
        "cancel_fields": CANCEL_FIELDS,
        "CChatCommand_SERIALIZE": hex(0x13D7FA0),
        "chat_fields": CHAT_FIELDS,
        "safe_enable": "NOT proven",
    }
    if args.live:
        from process import Backend, find_pid

        b = Backend(find_pid("hoi4.exe"))
        base = b.image_base

        def u64(a):
            return struct.unpack("<Q", b.read(a, 8))[0]

        def token_name(tok):
            arr = u64(base + 0x368F5A0)
            e = arr + tok * 32
            size = u64(e + 16)
            cap = u64(e + 24)
            if cap > 15 or size > 15:
                return b.read(u64(e), min(int(size), 80)).split(b"\x00")[0].decode(
                    "latin1"
                )
            return b.read(e, int(size)).decode("latin1")

        # Verify enum token immediates in binary
        sites = {
            0: (0x19D75D7, 0x37BD),
            1: (0x19D7604, 0x77),
            2: (0x19D75F5, 0x37BE),
            3: (0x19D75E6, 0x4C91),
        }
        verified = {}
        for val, (rva, expect_tok) in sites.items():
            raw = b.read(base + rva, 6)
            # C7 03 imm or C7 01 imm
            if raw[0] == 0xC7 and raw[1] in (0x03, 0x01):
                imm = struct.unpack("<I", raw[2:6])[0]
            else:
                imm = None
            name = token_name(expect_tok)
            verified[str(val)] = {
                "rva": hex(rva),
                "token": hex(expect_tok),
                "imm_ok": imm == expect_tok,
                "name": name,
                "name_ok": name == MOVE_PRIORITY[val]["name"],
            }
        out["enum_live_checks"] = verified
        out["enum_ok"] = all(v["imm_ok"] and v["name_ok"] for v in verified.values())

        # Cancel sticky/unit tokens present
        raw = b.read(base + 0x1404155, 5)
        out["cancel_unit_token_ok"] = raw[0] == 0xBA and struct.unpack("<I", raw[1:5])[
            0
        ] == 0x28A3
        raw = b.read(base + 0x1404185, 5)
        out["cancel_sticky_token_ok"] = raw[0] == 0xBA and struct.unpack(
            "<I", raw[1:5]
        )[0] == 0x368F
        b.close()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
    print("wrote", args.out)
    for k, v in MOVE_PRIORITY.items():
        print(f"  move_priority {k} = {v['name']} token {hex(v['token'])}")
    if args.live:
        print("enum_ok", out["enum_ok"], out["enum_live_checks"])
        print("cancel tokens", out["cancel_unit_token_ok"], out["cancel_sticky_token_ok"])


if __name__ == "__main__":
    main()
