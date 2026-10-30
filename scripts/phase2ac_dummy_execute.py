"""Phase 2ac — DummyServer Post = log+destroy; Execute feeds server+0x40. RO checklist."""
from __future__ import annotations
import argparse, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "calling"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "research", "re-dumps", "phase2ac_report.json"))
    args = ap.parse_args()
    out = {
        "phase": "2ac",
        "command_queue": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "posting": "DISABLED — not independently proven safe",
        "dummy_server_post": {
            "vt": "0x2bcb040",
            "Post_0x28": "0x23f5cd0",
            "behavior": "stamp seq via +0xd0; push metadata to worker rings; cmd.vt+0(edx=1) DESTROY",
            "feeds_execute": False,
            "rtti": ".?AVCDummyServer@@",
        },
        "execute_loop": {
            "fn": "0x22c4710",
            "pull": "server.vt+0x78() => &server+0x40; walk [head] nodes; IsValid; vt+0x50 Execute",
            "DummyServer_vt_0x78": "0x247620 lea rax,[rcx+0x40]; ret",
            "live_server_plus_0x40": "0 (empty) — explains exec stuck at 13",
        },
        "network_server": {
            "vt": "0x2bcb330",
            "Post_0x28": "0x23fa830",
            "insert": "0x23fa510 — cmd+0x1a!=0 => +0x40 list else +0x58 list",
            "note": "NOT live; SP uses DummyServer",
        },
        "auth_gate": {
            "session_0x3c": "live 1 => SKIP vt+0x90 auth entirely",
            "else": "vt+0x90 must return TRUE or DROP sender not authorized",
        },
        "safe_enable_checklist_ONLY": [
            "DO NOT enable Post on live CDummyServer — destroys cmd, no Execute",
            "Need insert into server+0x40 (or +0x58) matching NetworkServer rules, OR live NetworkServer",
            "Keep session+0x725==1 OR pass vt+0x60/80 OR r8b",
            "Avoid post while session+0x6cc set unless +0x726",
            "Build valid cmd object (Move size 0x88 + CUnitMoveAction@+0x28)",
            "NEVER Post speed cmds (5x ban)",
            "Independently prove Execute runs on posted cmd before enabling queue",
            "Until then: posting DISABLED",
        ],
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
        server = u64(session + 0x40)
        gs = u64(base + ov["G_GAMESTATE"])
        out["live"] = {
            "pid": b.pid,
            "server_vt": hex(u64(server) - base),
            "server_0x40": hex(u64(server + 0x40)),
            "server_0x58": hex(u64(server + 0x58)),
            "server_0xc8": hex(u64(server + 0xc8)),
            "server_0xd0_seq": u32(server + 0xd0),
            "session_0x3c": u8(session + 0x3c),
            "session_0x725": u8(session + 0x725),
            "exec": u32(session + 0x6c8),
            "drain": u32(session + 0x60),
            "tick": u32(session + 0x84),
            "gs_0xb0": u32(gs + 0xb0),
            "gs_0xb4": u32(gs + 0xb4),
        }
        b.close()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
    print("wrote", args.out)
    print("2ac: DummyServer Post destroys; Execute list empty; posting DISABLED")


if __name__ == "__main__":
    main()
