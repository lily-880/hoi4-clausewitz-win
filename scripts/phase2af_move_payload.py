"""Phase 2af — Move payload via CUnitMoveAction vt+0xc0; Dummy Post ring feed. RO."""
from __future__ import annotations
import argparse, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "calling"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "research", "re-dumps", "phase2af_report.json"))
    args = ap.parse_args()
    out = {
        "phase": "2af",
        "command_queue": "DISABLED",
        "posting": "DISABLED — not independently proven safe",
        "speed_rule": "pause or 1x only; never 5x",
        "CMoveCommand": {
            "vt": "0x2a2c790",
            "type_id": "0x28a2",
            "size": "0x88",
            "factory": "0x13fb000",
            "action_at": "+0x28",
            "vt_0xa0": "0x1404590 thunk -> action.vt+0xc0",
        },
        "CUnitMoveAction": {
            "vt": "0x2a1f648",
            "ctor": "0x12c1770",
            "serialize_vt_0xc0": "0x12c3920",
            "Execute_vt48": "0x12c2670",
            "IsValid_vt50": "0x12c2ca0",
        },
        "Dummy_Post_feed": {
            "Post": "0x23f5cd0",
            "serialize_helper": "0x22d8ad0",
            "typeid_factory_table": "0x22d8d20",
            "ring": "server+0xa0 after recreate",
            "can_feed_Execute": True,
        },
    }
    if not args.live:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
        print("offline", args.out)
        return

    from process import Backend, find_pid
    from capstone import Cs, CS_ARCH_X86, CS_MODE_64

    ov = json.load(open(os.path.join(ROOT, "calling", "offsets_verified.json"), encoding="utf-8"))
    b = Backend(find_pid("hoi4.exe"))
    base = b.image_base
    md = Cs(CS_ARCH_X86, CS_MODE_64)

    def u64(a): return struct.unpack("<Q", b.read(a, 8))[0]
    def u32(a): return struct.unpack("<I", b.read(a, 4))[0]
    def u8(a): return b.read(a, 1)[0]

    ser = 0x12C3920
    lines = []
    tags = []
    pending = None
    for insn in md.disasm(b.read(base + ser, 0x200), base + ser):
        lines.append(f"{hex(insn.address-base)}: {insn.mnemonic} {insn.op_str}")
        if insn.mnemonic == "mov" and insn.op_str.startswith("edx, 0x"):
            pending = int(insn.op_str.split(",")[1].strip(), 16)
        elif pending is not None and insn.mnemonic in ("lea", "call"):
            tags.append({"tag": hex(pending), "op": f"{insn.mnemonic} {insn.op_str}"})
            pending = None
        if insn.mnemonic == "ret" or len(lines) >= 80:
            break
    out["CUnitMoveAction"]["serialize_disasm"] = lines
    out["CUnitMoveAction"]["serialize_tags"] = tags

    # verify live pointers
    move_a0 = u64(base + 0x2A2C790 + 0xA0) - base
    act_c0 = u64(base + 0x2A1F648 + 0xC0) - base
    out["live_verify"] = {"Move_vt_0xa0": hex(move_a0), "Action_vt_0xc0": hex(act_c0)}

    idler = u64(base + ov["G_IDLER"])
    session = u64(u64(idler + 0x530) + 0x380)
    server = u64(session + 0x40)
    out["live"] = {
        "pid": b.pid,
        "tick": u32(session + 0x84),
        "drain": u32(session + 0x60),
        "exec": u32(session + 0x6C8),
        "seq": u32(server + 0xD0),
        "lists": {"+0x40": hex(u64(server + 0x40)), "+0x58": hex(u64(server + 0x58))},
        "session_0x725": u8(session + 0x725),
        "note": "tick stuck + drain climbing => paused (-start_speed=0); never 5x",
    }
    b.close()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
    print("wrote", args.out)
    print("tags", tags)
    print("verify", out["live_verify"])
    print("live", out["live"])
    print("2af OK; posting DISABLED")


if __name__ == "__main__":
    main()
