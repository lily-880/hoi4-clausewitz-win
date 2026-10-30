"""Phase 2v — Post drop gates + delivery; CCancelMovement. RO / posting DISABLED."""
from __future__ import annotations
import argparse, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "calling"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "research", "re-dumps", "phase2v_report.json"))
    args = ap.parse_args()
    out = {
        "phase": "2v",
        "command_queue": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "FN_CMD_QUEUE_POST": {
            "rva": "0x22c41e0",
            "args": "rcx=CSession*, rdx=CCommand*, r8b=force_skip_early?",
            "success_delivery": "server = session+0x40; call server.vt+0x28(cmd) @ 0x22c46a0 → Dummy sink 0x23f5cd0",
            "return": "al=1 success / al=0 dropped",
            "drop_gates": [
                {
                    "when": "r8b==0 and session+0x725==0 and (cmd.vt+0x80 or cmd.vt+0x60)",
                    "log": "Dropped command:",
                    "site": "0x22c4240",
                },
                {
                    "when": "session+0x3c==0 and session+0x6cc!=0 and session+0x726==0 and !cmd.vt+0x80",
                    "log": "Dropped (posted during command execution):",
                    "site": "0x22c434a",
                    "note": "Post-during-Execute DROPS",
                },
                {
                    "when": "session+0x3c==0 and cmd.vt+0x90(auth) fails",
                    "log": "Dropped (sender not authorized):",
                    "site": "0x22c443f",
                },
            ],
            "stamps_before_delivery": {
                "cmd+0xc": "session+0x84 (tick?)",
                "cmd+0x18": "min(session+0x60, 0x7fff) as word",
            },
        },
        "CCancelMovement": {
            "vt": "0x2a2c9b8",
            "size": "0x48",
            "IsValid_0x48": "0x13fed40",
            "Execute_0x50": "0x13fbbd0",
            "ctors_lea_vt": ["0x13f6001", "0x13f626d", "0x13f8e1d", "0x13fad16"],
            "factory_alloc": "0x13face6 mov ecx,0x48 near lea 0x13fad16",
        },
        "safe_enable_checklist_NOT_DONE": [
            "Prove SP Dummy sink → drain → staging → Execute for injected cmd (RO observe only so far)",
            "Build valid CMoveCommand/CUnitMoveAction heap object with correct fields",
            "Ensure session+0x6cc==0 at Post time",
            "Pass cmd.vt+0x90 auth / vt+0x80 / vt+0x60 gates",
            "Independent crash-free proof in paused SP — STILL OPEN",
        ],
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

        idler = u64(base + ov["G_IDLER"])
        session = u64(u64(idler + 0x530) + 0x380)
        server = u64(session + 0x40)
        svt = u64(server) - base
        out["live"] = {
            "pid": b.pid,
            "state": u32(session + 0x30),
            "exec_flag_0x6cc": b.read(session + 0x6cc, 1)[0],
            "session_0x725": b.read(session + 0x725, 1)[0],
            "session_0x726": b.read(session + 0x726, 1)[0],
            "session_0x3c": b.read(session + 0x3c, 1)[0],
            "server_vt": hex(svt),
            "server_vt_plus_0x28": hex(u64(base + svt + 0x28) - base),
            "drain": u32(session + 0x60),
            "exec": u32(session + 0x6c8),
        }
        b.close()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
    print("wrote", args.out)
    print("2v: Post→server.vt+0x28; drop strings pinned; CancelMovement; posting DISABLED")


if __name__ == "__main__":
    main()
