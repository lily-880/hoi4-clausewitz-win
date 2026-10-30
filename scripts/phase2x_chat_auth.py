"""Phase 2x — Chat fields; Move early-drop (vt+0x60/80 false); OEC. RO."""
from __future__ import annotations
import argparse, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "calling"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "research", "re-dumps", "phase2x_report.json"))
    args = ap.parse_args()
    out = {
        "phase": "2x",
        "command_queue": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "early_drop_gate": {
            "site": "0x22c4205..0x22c4240",
            "logic": "if r8b==0 and session+0x725==0: require cmd.vt+0x80 OR vt+0x60 true; else Dropped command",
            "CMoveCommand": "vt+0x60 and vt+0x80 both 0x11d530 (xor al,al;ret) → ALWAYS early-drop unless r8b=1 or session+0x725!=0",
            "implication": "SP Post of Move needs force r8b or +0x725; still DISABLED",
        },
        "CChatCommand": {
            "vt": "0x2a27f28",
            "size": "0x98",
            "factory": "0x13ca430",
            "Execute": "0x13caee0",
            "IsValid": "0x13cd1b0",
            "fields": {
                "+0x28": "SSO string (message text)",
                "+0x48": "vector-like",
                "+0x60": "byte",
                "+0x64": "dword country/player (-1 default)",
                "+0x70": "dword -1",
                "+0x74": "byte 1",
                "+0x78": "SSO string",
            },
        },
        "COrderExecuteCommand": {
            "vt": "0x2a85468",
            "Execute": "0x18d6430",
            "rtti": ".?AVCOrderExecuteCommand@@",
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

        idler = u64(base + ov["G_IDLER"])
        session = u64(u64(idler + 0x530) + 0x380)
        out["live"] = {
            "pid": b.pid,
            "state": u32(session + 0x30),
            "session_0x725": b.read(session + 0x725, 1)[0],
            "session_0x726": b.read(session + 0x726, 1)[0],
            "session_0x3c": b.read(session + 0x3c, 1)[0],
            "exec_flag_0x6cc": b.read(session + 0x6cc, 1)[0],
            "drain": u32(session + 0x60),
            "exec": u32(session + 0x6c8),
        }
        b.close()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
    print("wrote", args.out)
    print("2x: Move early-drop unless r8b/+0x725; Chat fields; posting DISABLED")
    if args.live:
        print("live +0x725=", out["live"]["session_0x725"])


if __name__ == "__main__":
    main()
