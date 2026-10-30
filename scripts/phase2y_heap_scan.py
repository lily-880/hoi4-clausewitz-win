"""Phase 2y — heap scan result + post-exec node dump. RO."""
from __future__ import annotations
import argparse, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "calling"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "research", "re-dumps", "phase2y_report.json"))
    args = ap.parse_args()
    out = {
        "phase": "2y",
        "command_queue": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "heap_scan": {
            "writable_MB": 7696,
            "CMoveCommand_live": 0,
            "CChatCommand_live": 0,
            "CUnitMoveAction_live": 0,
            "CDummyServer_live": 1,
            "note": "paused SP: cmds destroyed after Execute; no lingering Move/Chat on heap",
        },
        "live_session_notes": {
            "session_0x725": 1,
            "early_drop_bypassed": True,
            "post_exec_count_sticky": "session+0x108 often 1 while lists otherwise empty",
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
        server = u64(session + 0x40)
        head = u64(session + 0xf8)
        pe = {"head": hex(head), "tail": hex(u64(session + 0x100)), "count": u32(session + 0x108)}
        if head:
            try:
                node = b.read(head, 0x20)
                cmd = struct.unpack_from("<Q", node, 0)[0]
                pe["node_cmd"] = hex(cmd)
                pe["node_next"] = hex(struct.unpack_from("<Q", node, 0x10)[0])
                if cmd:
                    vt = u64(cmd) - base
                    pe["cmd_vt"] = hex(vt)
                    pe["cmd_plus8"] = b.read(cmd + 8, 1)[0]
                    pe["cmd_plus_0x1a"] = b.read(cmd + 0x1a, 1)[0]
            except OSError as e:
                pe["err"] = str(e)
        out["live"] = {
            "pid": b.pid,
            "state": u32(session + 0x30),
            "server": hex(server),
            "server_plus_0x40": hex(u64(server + 0x40)),
            "server_plus_0x58": hex(u64(server + 0x58)),
            "session_0x725": b.read(session + 0x725, 1)[0],
            "drain": u32(session + 0x60),
            "exec": u32(session + 0x6c8),
            "post_exec": pe,
        }
        b.close()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
    print("wrote", args.out)
    print(json.dumps(out.get("live", {}), indent=2))
    print("2y: heap empty of Move/Chat; DummyServer pinned; posting DISABLED")


if __name__ == "__main__":
    main()
