"""Phase 2ag — typeid factory table 0x28a2 + full CUnitMoveAction serialize fields. RO."""
from __future__ import annotations
import argparse, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "calling"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "research", "re-dumps", "phase2ag_report.json"))
    args = ap.parse_args()
    out = {
        "phase": "2ag",
        "command_queue": "DISABLED",
        "posting": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
    }
    if not args.live:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
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

    # FN_TYPEID_FACTORY_LOOKUP 0x22d8d20:
    # lea eax,[rcx-0x2328]; cmp ecx,0x2710; cmovge ecx,eax
    # movsxd rax,ecx; cmp rax,0x2af7; ja miss
    # lea rcx,[rip+0x1228490]; mov rax,[rcx+rax*8]
    lookup = 0x22D8D20
    # find RIP-relative table base from lea at 0x22d8d49
    # lea rcx, [rip + 0x1228490] at 0x22d8d49 — next insn after lea is 0x22d8d50
    # table = 0x22d8d50 + 0x1228490
    table_rva = 0x22D8D50 + 0x1228490
    out["typeid_factory_table_rva"] = hex(table_rva)
    out["lookup_fn"] = hex(lookup)
    out["index_bias"] = {"sub_if_ge_0x2710": 0x2328, "max_index": 0x2AF7}

    def typeid_to_index(tid):
        ecx = tid
        if ecx >= 0x2710:
            ecx = tid - 0x2328
        return ecx

    typeids = {
        "CMoveCommand": 0x28A2,
        "CCancelMovementCommand": 0x28AF,
        "CChatCommand": 0x184,
        "CStartGameCommand": 0x359E,
        "COrderExecuteCommand": None,  # resolve later if known
    }
    factories = {}
    for name, tid in typeids.items():
        if tid is None:
            continue
        idx = typeid_to_index(tid)
        if idx < 0 or idx > 0x2AF7:
            factories[name] = {"tid": hex(tid), "idx": idx, "fn": None, "oob": True}
            continue
        fn = u64(base + table_rva + idx * 8)
        factories[name] = {
            "tid": hex(tid),
            "idx": idx,
            "fn": hex(fn - base) if fn and base <= fn < base + 0x4000000 else (hex(fn) if fn else None),
        }
    out["factories"] = factories

    # Disasm Move factory from table (should be 0x13fb000)
    move_fn = factories["CMoveCommand"].get("fn")
    if move_fn:
        mf = int(move_fn, 16)
        lines = []
        for insn in md.disasm(b.read(base + mf, 0x80), base + mf):
            lines.append(f"{hex(insn.address-base)}: {insn.mnemonic} {insn.op_str}")
            if insn.mnemonic == "ret" or len(lines) >= 25:
                break
        out["Move_factory_disasm"] = lines

    # Full CUnitMoveAction serialize field map
    ser = 0x12C3920
    ser_lines = []
    field_map = []
    # Walk with more context: track lea [rbx+off] after tags
    pending_tag = None
    for insn in md.disasm(b.read(base + ser, 0x280), base + ser):
        ser_lines.append(f"{hex(insn.address-base)}: {insn.mnemonic} {insn.op_str}")
        if insn.mnemonic == "mov" and "edx, 0x" in insn.op_str:
            pending_tag = int(insn.op_str.split("edx,")[1].strip(), 16)
        elif pending_tag is not None:
            if insn.mnemonic == "lea" and "rbx" in insn.op_str:
                # lea rdx/r8, [rbx + off]
                field_map.append({"tag": hex(pending_tag), "access": insn.op_str, "kind": "lea_field"})
                pending_tag = None
            elif insn.mnemonic == "movzx" and "rbx" in insn.op_str:
                field_map.append({"tag": hex(pending_tag), "access": insn.op_str, "kind": "byte"})
                pending_tag = None
            elif insn.mnemonic == "mov" and "rbx" in insn.op_str and "edx" not in insn.op_str:
                field_map.append({"tag": hex(pending_tag), "access": insn.op_str, "kind": "mov"})
                # don't clear yet — might be setup
            elif insn.mnemonic == "call":
                field_map.append({"tag": hex(pending_tag), "call": insn.op_str, "kind": "call_only"})
                pending_tag = None
        if insn.mnemonic == "ret" or len(ser_lines) >= 100:
            break
    out["CUnitMoveAction_serialize_disasm"] = ser_lines
    out["CUnitMoveAction_field_map"] = field_map

    # Also map shared header fields from Write 0x22d9390
    out["CCommand_header_fields"] = {
        "+0xc": "dword (copied to ser buf)",
        "+0x18": "word (player/slot from server+related)",
        "+0x1a": "byte (route: nonzero => execlist +0x40 else drain +0x58)",
        "+0x1c": "dword seq (from lock xadd server+0xd0)",
        "+0x20": "dword seq copy",
        "tag_header": "0x1f3",
        "tag_payload": "0x41",
    }

    # Safe-enable blockers checklist (still DISABLED)
    out["safe_enable_blockers"] = [
        "No mid-flight live Move captured to verify round-trip serialize",
        "server+0x40 execlist filler for DummyServer path still only via recreate ring->drain->stage",
        "Posting from tooling never called — independent safety proof incomplete",
        "Action field semantic names (province/unit handles) not fully labeled",
        "NEVER Post speed cmds; pause/1x only",
    ]

    idler = u64(base + ov["G_IDLER"])
    session = u64(u64(idler + 0x530) + 0x380)
    server = u64(session + 0x40)
    out["live"] = {
        "pid": b.pid,
        "tick": u32(session + 0x84),
        "drain": u32(session + 0x60),
        "exec": u32(session + 0x6C8),
        "seq": u32(server + 0xD0),
        "lists_empty": u64(server + 0x40) == 0 and u64(server + 0x58) == 0,
        "session_0x725": u8(session + 0x725),
    }

    # Resolve Cancel factory too — quick size check
    for name in ("CCancelMovementCommand", "CChatCommand", "CStartGameCommand"):
        fn_s = factories.get(name, {}).get("fn")
        if not fn_s:
            continue
        fn = int(fn_s, 16)
        # look for mov ecx, size before alloc
        for insn in md.disasm(b.read(base + fn, 0x40), base + fn):
            if insn.mnemonic == "mov" and insn.op_str.startswith("ecx, 0x"):
                factories[name]["size_imm"] = insn.op_str.split(",")[1].strip()
                break

    b.close()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
    print("wrote", args.out)
    print("table", out["typeid_factory_table_rva"])
    print("factories", json.dumps(factories, indent=2))
    print("fields", json.dumps(field_map, indent=2))
    print("live", out["live"])


if __name__ == "__main__":
    main()
