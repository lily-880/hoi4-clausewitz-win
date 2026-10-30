"""Phase 2ab — Post early-gate order; +0x725 writers; Chat auth; speed note. RO."""
from __future__ import annotations
import argparse, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "calling"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "research", "re-dumps", "phase2ab_report.json"))
    args = ap.parse_args()
    out = {
        "phase": "2ab",
        "command_queue": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "post_early_gate_order": {
            "fn": "FN_CMD_QUEUE_POST @ 0x22c41e0",
            "bypass_to_stamp_path_if_any": [
                "r8b != 0 (caller force)",
                "session+0x725 != 0",
                "cmd.vt+0x80 returns TRUE",
                "cmd.vt+0x60 returns TRUE",
            ],
            "else": "DROP 'Dropped command:'",
            "note": "ALL four must fail for early drop; live +0x725=1 => Move/Chat pass early",
        },
        "post_after_bypass": [
            "stamp cmd+0xc = session+0x84 (tick)",
            "stamp cmd+0x18 = min(session+0x60, 0x7fff)",
            "if session+0x6cc!=0 and session+0x726==0: DROP during-exec",
            "auth path may DROP 'sender not authorized'",
            "success: server.vt+0x28(cmd)",
        ],
        "session_0x725": {
            "meaning": "early-gate bypass flag",
            "writers": "set to 1 after Idler.vt+0x88 -> App.vt+0x88 returns session",
            "sites": ["0x1ee3d3", "0x1ee728", "0xa5bd0b", "0xf70ef0", "0x14c2007"],
        },
        "session_0x726": "paired with +0x6cc for post-during-exec drop",
        "Chat_vt_0x90": {
            "rva": "0x13cc9a0",
            "shape": "multi-path serialize/auth; path @0x13ccc20 returns al=1",
            "fields_touched": ["cmd+0x60", "cmd+0x64", "cmd+0x88"],
        },
        "posting": "DISABLED",
    }
    if args.live:
        from process import Backend, find_pid

        ov = json.load(open(os.path.join(ROOT, "calling", "offsets_verified.json"), encoding="utf-8"))
        b = Backend(find_pid("hoi4.exe"))
        base = b.image_base

        def u64(a):
            return struct.unpack("<Q", b.read(a, 8))[0]

        def u32(a):
            return struct.unpack("<I", b.read(a, 4))[0]

        def u8(a):
            return b.read(a, 1)[0]

        idler = u64(base + ov["G_IDLER"])
        session = u64(u64(idler + 0x530) + 0x380)
        gs = u64(base + ov["G_GAMESTATE"])
        out["live"] = {
            "pid": b.pid,
            "state": u32(session + 0x30),
            "drain": u32(session + 0x60),
            "tick_0x84": u32(session + 0x84),
            "exec": u32(session + 0x6c8),
            "exec_flag_0x6cc": u8(session + 0x6cc),
            "bypass_0x725": u8(session + 0x725),
            "flag_0x726": u8(session + 0x726),
            "post_exec_count": u32(session + 0x108),
            "gs_plus_0xb0": u32(gs + 0xb0),
            "gs_plus_0xb4": u32(gs + 0xb4),
            "speed_note": "gs+0xb0/0xb4 observed; treat as candidate speed; never force 5x",
        }
        b.close()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
    print("wrote", args.out)
    print("2ab Post gate order pinned; posting DISABLED")


if __name__ == "__main__":
    main()
