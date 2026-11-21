# research/_t191_factory_slots.py — read-only live factory table + vtable slot check
from __future__ import annotations
import json, struct, sys
from pathlib import Path

sys.path.insert(0, "calling")
from pe import PE
from mem import Proc, find_pid
from gamestate import _rtti_name_from_vtable
import move_order as mo
import cancel_order as co

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
TABLE = 0x35011E0
SLOTS = {
    "MOVE": 1402,
    "CANCEL": 1415,
    "SUPPORT_ATTACK": 3620,
    "STRATEGIC": 4753,
}
# RTTI-proven 1.19.5 primary vtables
VTS_115 = {
    "CArmy": 0x29D6D98,
    "CMoveCommand": 0x2A2CDE0,
    "CUnitMoveAction": 0x2A1FAC8,
    "CCancelMovementCommand": 0x2A2D020,
    "CStrategicRedeploymentCommand": 0x2A2DF20,
    "CUnitStrategicMoveAction": 0x2A1FC68,
    "CSupportAttackCommand": 0x2A2D1A0,
}


def main():
    pid = find_pid("hoi4.exe")
    p = Proc(pid)
    pe = PE(EXE)
    try:
        def q(a):
            return struct.unpack("<Q", p.read(a, 8))[0]

        def u32(a):
            return struct.unpack("<I", p.read(a, 4))[0]

        def cls_from_vt_rva(rva):
            return _rtti_name_from_vtable(pe, rva)

        base = p.base
        slots = {}
        for name, idx in SLOTS.items():
            addr = base + TABLE + idx * 8
            fn = q(addr)
            rva = fn - base if base <= fn < base + p.image_size else None
            head = p.read(fn, 16) if rva is not None else b""
            slots[name] = {
                "idx": idx,
                "slot_addr": hex(addr),
                "fn": hex(fn),
                "rva": hex(rva) if rva is not None else None,
                "head16": head.hex(),
                "head_disasm_hint": None,
            }
            # cheap hint: 64-bit: mov ecx, imm32 = b9 xx xx xx xx
            if head.startswith(b"\xb9"):
                slots[name]["mov_ecx_imm"] = hex(struct.unpack_from("<I", head, 1)[0])

        # Compare old constants
        slots["MOVE"]["old_factory"] = hex(mo.FACTORY_RVA)
        slots["MOVE"]["factory_rva_unchanged"] = slots["MOVE"]["rva"] == hex(mo.FACTORY_RVA)
        slots["CANCEL"]["old_factory"] = hex(co.FACTORY_RVA)
        slots["CANCEL"]["factory_rva_unchanged"] = slots["CANCEL"]["rva"] == hex(co.FACTORY_RVA)

        def vt_slots(rva, n=24):
            va = base + rva
            out = []
            for i in range(n):
                fn = q(va + 8 * i)
                frva = fn - base if base <= fn < base + p.image_size else None
                out.append({"slot": i, "off": hex(i * 8), "rva": hex(frva) if frva is not None else hex(fn)})
            return out

        vtables = {}
        for name, rva in VTS_115.items():
            vtables[name] = {
                "rva": hex(rva),
                "rtti": cls_from_vt_rva(rva),
                "slots": vt_slots(rva, 24),
            }

        # Old action IsValid 0x12C2CA0 — is it still a slot of the new action VT?
        old_isvalid = 0x12C2CA0
        action_slots = vtables["CUnitMoveAction"]["slots"]
        isvalid_hits = [s for s in action_slots if s["rva"] == hex(old_isvalid)]
        cmd_slots = vtables["CMoveCommand"]["slots"]

        out = {
            "pid": pid,
            "base": hex(base),
            "factory_slots": slots,
            "vtables_rtti": {k: v["rtti"] for k, v in vtables.items()},
            "CMoveCommand_slots": cmd_slots,
            "CUnitMoveAction_slots": action_slots,
            "CCancelMovementCommand_slots": vtables["CCancelMovementCommand"]["slots"],
            "old_ACTION_ISVALID_still_on_action_vt": isvalid_hits,
            "old_ACTION_ISVALID": hex(old_isvalid),
            "old_MOVE_EXECUTE": hex(0x13FC990),
            "old_MOVE_EXECUTE_on_cmd_vt": [s for s in cmd_slots if s["rva"] == hex(0x13FC990)],
        }
        Path("research/t191_factory_slots.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({
            "factory_slots": slots,
            "old_ACTION_ISVALID_still_on_action_vt": isvalid_hits,
            "old_MOVE_EXECUTE_on_cmd_vt": out["old_MOVE_EXECUTE_on_cmd_vt"],
            "CMoveCommand_vt_0x48_0x50": [s for s in cmd_slots if s["off"] in ("0x48", "0x50")],
            "CUnitMoveAction_vt_select": [s for s in action_slots if s["off"] in ("0x0", "0x48", "0x50", "0x58", "0xb0", "0xb8")],
            "rtti": out["vtables_rtti"],
        }, indent=2))
    finally:
        p.close()


if __name__ == "__main__":
    main()
