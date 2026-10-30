"""Phase 2ae — type ids + Move vt+0xa0 payload serialize; durable. RO."""
from __future__ import annotations
import argparse, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "calling"))

TYPE_IDS = {
    "CMoveCommand": 0x28A2,
    "CCancelMovementCommand": 0x28AF,
    "CChatCommand": 0x184,
    "CStartGameCommand": 0x359E,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "research", "re-dumps", "phase2ae_report.json"))
    args = ap.parse_args()
    out = {
        "phase": "2ae",
        "command_queue": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "posting": "DISABLED",
        "type_ids_vt_0x58": {k: hex(v) for k, v in TYPE_IDS.items()},
        "serialize_slots": {
            "vt_0x10_write": "0x22d9390 shared — writes +0xc/+0x18/+0x1a/+0x1c/+0x20 then vt+0xa0 payload",
            "vt_0x20_read": "0x22d90f0 shared — tags 0x1f3 header, 0x41 payload",
            "vt_0x58_typeid": "per-class imm",
        },
        "midflight_poll": "20x empty ring/lists; exec stuck 13; no UI activity",
    }
    if args.live:
        from process import Backend, find_pid
        from capstone import Cs, CS_ARCH_X86, CS_MODE_64

        b = Backend(find_pid("hoi4.exe"))
        base = b.image_base
        md = Cs(CS_ARCH_X86, CS_MODE_64)

        def u64(a):
            return struct.unpack("<Q", b.read(a, 8))[0]

        move_vt = 0x2A2C790
        a0 = u64(base + move_vt + 0xA0) - base
        lines = []
        for insn in md.disasm(b.read(base + a0, 0xA0), base + a0):
            lines.append(f"{hex(insn.address-base)}: {insn.mnemonic} {insn.op_str}")
            if insn.address - base >= a0 + 0x90:
                break
        out["Move_vt_0xa0"] = hex(a0)
        out["Move_vt_0xa0_disasm"] = lines
        # verify type ids live
        live_ids = {}
        for name, vt in [
            ("CMoveCommand", 0x2A2C790),
            ("CCancelMovementCommand", 0x2A2C9B8),
            ("CChatCommand", 0x2A27F28),
            ("CStartGameCommand", 0x2A5F448),
        ]:
            fn = u64(base + vt + 0x58) - base
            # read imm from mov dword [rdx], imm32 — usually at fn+0
            raw = b.read(base + fn, 8)
            if raw[0] == 0xC7 and raw[1] == 0x02:
                live_ids[name] = hex(struct.unpack_from("<I", raw, 2)[0])
            else:
                live_ids[name] = f"fn={hex(fn)}"
        out["live_type_ids"] = live_ids
        b.close()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
    print("wrote", args.out)
    print("2ae type ids + serialize slots; posting DISABLED")


if __name__ == "__main__":
    main()
