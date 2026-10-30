"""Phase 2z — CStartGameCommand live post-exec; early-gate contrast. RO."""
from __future__ import annotations
import argparse, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "calling"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "research", "re-dumps", "phase2z_report.json"))
    args = ap.parse_args()
    out = {
        "phase": "2z",
        "command_queue": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "CStartGameCommand": {
            "vt": "0x2a5f448",
            "size": "0x28",
            "factory_leas": ["0x16dc976", "0x16dd106", "0x16dd5cc"],
            "IsValid_0x48": "0x188d90 (mov al,1; ret)",
            "Execute_0x50": "0x16de180",
            "vt_0x60": "0x188d90 TRUE — passes Post early-gate; also gates session post-exec clone",
            "vt_0x80": "0x188d90 TRUE",
            "contrast_Move": "Move stubs both to FALSE (0x11d530)",
            "live_sticky_post_exec": "observed on session+0xf8 while paused",
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
        head = u64(session + 0xf8)
        live = {
            "pid": b.pid,
            "state": u32(session + 0x30),
            "post_exec_count": u32(session + 0x108),
            "drain": u32(session + 0x60),
            "exec": u32(session + 0x6c8),
            "session_0x725": b.read(session + 0x725, 1)[0],
        }
        if head:
            cmd = u64(head)
            live["cmd"] = hex(cmd)
            live["cmd_vt"] = hex(u64(cmd) - base)
            live["tick_0xc"] = u32(cmd + 0xc)
            live["seq_0x1c"] = u32(cmd + 0x1c)
            live["flag_0x1a"] = b.read(cmd + 0x1a, 1)[0]
        out["live"] = live
        b.close()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
    print("wrote", args.out)
    print("2z: CStartGameCommand vt+0x60/80 TRUE; sticky post-exec; posting DISABLED")


if __name__ == "__main__":
    main()
