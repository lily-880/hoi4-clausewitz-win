"""Phase 2s — exe-list (+0x40) vs drain-list (+0x58); CCommand Execute catalog (READ-ONLY).

Findings:
  - Dummy/Network drain fill ONLY +0x58/+0x60/+0x68 (linked list)
  - +0x40 is a separate channel consumed by FN_EXECUTE_LOOP 0x22c4710 via vt+0x78
  - +0x40 filler still unpinned (not post-during-exec; that path DROPS via session+0x6cc)
  - 174 army-ish CCommand subclasses with real Execute (vt+0x50 != abort)
  - Posting DISABLED. pause/1x only.
"""
from __future__ import annotations
import argparse, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "calling"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument(
        "--out",
        default=os.path.join(ROOT, "research", "re-dumps", "phase2s_report.json"),
    )
    args = ap.parse_args()

    army_path = os.path.join(ROOT, "research", "re-dumps", "phase2s_network_army.json")
    army = []
    if os.path.isfile(army_path):
        army = json.load(open(army_path, encoding="utf-8")).get("army_execute", [])

    out = {
        "phase": "2s",
        "command_queue": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "lists": {
            "+0x58": {
                "role": "drain-pending linked list",
                "fields": {"head": "+0x58", "tail": "+0x60", "count": "+0x68"},
                "filled_by": "CDummyServer/CNetworkServer vt+0x30 drain",
                "getter": "vt+0x40 @ 0x2e9e50 (shared lea this+0x58)",
                "consumed_by": "FN_SESSION_UPDATE 0x22c6410 stage->session+0x48 then Execute vt+0x50",
            },
            "+0x40": {
                "role": "secondary exec channel",
                "getter": "vt+0x78 @ 0x247620 (shared lea this+0x40)",
                "consumed_by": "FN_EXECUTE_LOOP 0x22c4710 (IsValid wrap + Execute vt+0x50 @ 0x22c47dd)",
                "filled_by": "UNPINNED — not Dummy/Network drain/post/clear; not post-during-exec (drops)",
                "sp_paused": "empty (head 0); SP army path uses +0x58 staging",
            },
        },
        "post_during_exec": {
            "flag": "session+0x6cc set around Execute",
            "behavior": "FN_CMD_QUEUE_POST drops with 'Dropped (posted during command execution)' @ 0x22c4371",
            "does_not_fill_plus_0x40": True,
        },
        "CCommand_slots_reminder": {
            "0x48": "IsValid",
            "0x50": "Execute",
            "0x58": "post-Execute",
        },
        "examples": {
            "CChatCommand": {"vt": "0x2a27f28", "Execute": "0x13caee0", "IsValid": "0x13cd1b0"},
            "COrderExecuteCommand": {"vt": "0x2a85468", "Execute": "0x18d6430", "IsValid": "0x18def40"},
            "CMoveCommand": {"Execute": "0x13fc990"},
            "CCancelMovementCommand": {"Execute": "0x13fbbd0"},
            "CMassMoveCommand": {"Execute": "0x13fc310"},
        },
        "army_execute_count": len(army),
        "army_execute_sample": army[:40],
        "posting": "DISABLED",
    }

    if args.live:
        from process import Backend, find_pid

        ov = json.load(
            open(os.path.join(ROOT, "calling", "offsets_verified.json"), encoding="utf-8")
        )
        b = Backend(find_pid("hoi4.exe"))
        base = b.image_base

        def u64(a):
            return struct.unpack("<Q", b.read(a, 8))[0]

        def u32(a):
            return struct.unpack("<I", b.read(a, 4))[0]

        idler = u64(base + ov["G_IDLER"])
        session = u64(u64(idler + 0x530) + 0x380)
        server = u64(session + 0x40)
        out["live"] = {
            "pid": b.pid,
            "state": u32(session + 0x30),
            "drain_ctr": u32(session + 0x60),
            "exec_ctr": u32(session + 0x6c8),
            "executing_flag_0x6cc": u32(session + 0x6cc) & 0xFF,
            "server_plus_0x40": hex(u64(server + 0x40)),
            "server_plus_0x58": hex(u64(server + 0x58)),
            "server_plus_0x68": u32(server + 0x68),
        }
        b.close()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
    print("wrote", args.out)
    print("2s: +0x58=drain path; +0x40 filler UNPINNED; army_exec", len(army), "; posting DISABLED")


if __name__ == "__main__":
    main()
