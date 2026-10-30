"""Phase 2w — CMoveCommand size 0x88 field map; Chat; fix 2t size. RO."""
from __future__ import annotations
import argparse, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "calling"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "research", "re-dumps", "phase2w_report.json"))
    args = ap.parse_args()
    out = {
        "phase": "2w",
        "command_queue": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "correction_vs_2t": "CMoveCommand size is 0x88 (factory 0x13fb000), NOT 0x58",
        "CCommand_base_common": {
            "+0": "vt",
            "+8": "byte flag (0 init)",
            "+0xc": "tick dword (-1 init; stamped by Post from session+0x84)",
            "+0x10": "qword",
            "+0x18": "word checksum-ish (0xffff init; stamped by Post)",
            "+0x1a": "byte execlist flag (NetworkServer +0x40 vs +0x58)",
            "+0x1b": "byte",
            "+0x1c": "seq from sink",
            "+0x20": "seq copy",
        },
        "CMoveCommand": {
            "vt": "0x2a2c790",
            "size": "0x88",
            "factory": "0x13fb000",
            "in_place_ctor": "0x13f6bc0",
            "clone_ctor": "0x13f9350",
            "Execute_thunk": "0x13fc990 -> CUnitMoveAction.vt+0x48 @ 0x12c2670",
            "IsValid_thunk": "0x14002f0 -> CUnitMoveAction.vt+0x50 @ 0x12c2ca0",
            "embedded_at_0x28": "CUnitMoveAction (sub_ctor 0x12c1770)",
        },
        "CUnitMoveAction": {
            "vt": "0x2a1f648",
            "approx_size": "0x60",
            "+0": "vt",
            "+8": "type_id dword 0x3648",
            "+0x10": "handle/id (from global at ctor)",
            "+0x18": "vector-like (province/path?)",
            "+0x30": "vector-like (unit ids? used in Execute)",
            "+0x48": "dword 0",
            "+0x50": "byte/dword flags area",
            "+0x54": "word 0",
            "+0x58": "dword 1",
            "+0x5c": "byte 0",
            "IsValid_needs": "+0x24 count or +0x3c; unit handle @+0x10",
        },
        "CChatCommand": {
            "vt": "0x2a27f28",
            "size": "0x98",
            "Execute": "0x13caee0",
            "IsValid": "0x13cd1b0",
            "note": "possible simpler SP inject candidate later — still DISABLED",
        },
        "CCancelMovement": {
            "vt": "0x2a2c9b8",
            "size": "0x48",
            "Execute": "0x13fbbd0",
            "IsValid": "0x13fed40",
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
            "exec_flag": b.read(session + 0x6cc, 1)[0],
            "drain": u32(session + 0x60),
            "exec": u32(session + 0x6c8),
        }
        b.close()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
    print("wrote", args.out)
    print("2w: CMoveCommand size FIXED 0x88; fields mapped; posting DISABLED")


if __name__ == "__main__":
    main()
