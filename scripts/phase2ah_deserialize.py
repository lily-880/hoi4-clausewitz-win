"""Phase 2ah — CUnitMoveAction deserialize (read) + Cancel serialize; round-trip RO checklist."""
from __future__ import annotations
import argparse, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "calling"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "research", "re-dumps", "phase2ah_report.json"))
    args = ap.parse_args()
    out = {
        "phase": "2ah",
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

    def disasm(rva, n=0x200, max_lines=90, stop_ret=True):
        lines = []
        for insn in md.disasm(b.read(base + rva, n), base + rva):
            lines.append(f"{hex(insn.address-base)}: {insn.mnemonic} {insn.op_str}")
            if stop_ret and insn.mnemonic == "ret":
                break
            if len(lines) >= max_lines:
                break
        return lines

    action_vt = 0x2A1F648
    # Find read/deserialize slot — often near write. Check vt+0xb8 (seen 0x12c3340), +0xb0, +0xc8
    slots = {}
    for off in range(0, 0xE0, 8):
        fn = u64(base + action_vt + off)
        if fn and base <= fn < base + 0x4000000:
            slots[hex(off)] = hex(fn - base)
    out["CUnitMoveAction_vt_slots"] = slots

    # Heuristic: deserialize often mirrors serialize; check +0xb8 and neighbors for tag reads
    read_cands = {}
    for off_hex, fn_hex in slots.items():
        fn = int(fn_hex, 16)
        raw = b.read(base + fn, 0x80)
        # look for imm tags used in serialize: 0x28a3, 0x2840, 0x174
        blob = raw
        hits = []
        for tag in (0x28A3, 0x2840, 0x174, 0x29F1, 0x2C84):
            pat = struct.pack("<I", tag)
            if pat in blob:
                hits.append(hex(tag))
        if hits:
            read_cands[off_hex] = {"fn": fn_hex, "tags": hits}
    out["deserialize_slot_cands"] = read_cands

    # Prefer slot that isn't +0xc0 (write) and has 0x28a3
    deser_fn = None
    deser_slot = None
    for off_hex, info in read_cands.items():
        if off_hex == "0xc0":
            continue
        if "0x28a3" in info["tags"]:
            deser_fn = int(info["fn"], 16)
            deser_slot = off_hex
            break
    if deser_fn is None and read_cands:
        # take first non-c0
        for off_hex, info in read_cands.items():
            if off_hex != "0xc0":
                deser_fn = int(info["fn"], 16)
                deser_slot = off_hex
                break

    out["deserialize_slot"] = deser_slot
    out["deserialize_fn"] = hex(deser_fn) if deser_fn else None
    if deser_fn:
        out["deserialize_disasm"] = disasm(deser_fn, 0x280, max_lines=100, stop_ret=True)

    # Move cmd Read shared calls payload read — follow vt after Write's pattern
    # CCommand Read 0x22d90f0 — find call to vt slot for payload
    read_shared = 0x22D90F0
    out["CCommand_READ_SHARED_disasm"] = disasm(read_shared, 0x100, max_lines=50, stop_ret=False)
    payload_read_slot = None
    for insn in md.disasm(b.read(base + read_shared, 0x100), base + read_shared):
        # call qword ptr [rax + off]
        if insn.mnemonic == "call" and "qword ptr [rax +" in insn.op_str:
            # extract off
            s = insn.op_str
            try:
                off = int(s.split("+")[1].split("]")[0].strip(), 16)
                payload_read_slot = off
            except Exception:
                pass
    out["payload_read_vt_slot_from_shared"] = hex(payload_read_slot) if payload_read_slot is not None else None

    # Cancel command serialize path
    cancel_vt = 0x2A2C9B8
    cancel_a0 = u64(base + cancel_vt + 0xA0)
    out["Cancel_vt_0xa0"] = hex(cancel_a0 - base) if cancel_a0 and base <= cancel_a0 < base + 0x4000000 else None
    if out["Cancel_vt_0xa0"]:
        out["Cancel_vt_0xa0_disasm"] = disasm(int(out["Cancel_vt_0xa0"], 16), 0x100, max_lines=40)

    # Chat vt+0xa0
    chat_vt = 0x2A27F28
    chat_a0 = u64(base + chat_vt + 0xA0)
    out["Chat_vt_0xa0"] = hex(chat_a0 - base) if chat_a0 and base <= chat_a0 < base + 0x4000000 else None
    if out["Chat_vt_0xa0"]:
        out["Chat_vt_0xa0_disasm"] = disasm(int(out["Chat_vt_0xa0"], 16), 0xC0, max_lines=35)

    # Round-trip RO checklist (no writes)
    out["roundtrip_checklist_RO"] = {
        "1_header_write": "cmd.vt+0x10 @ 0x22d9390 tags 0x1f3 then 0x41 then vt+0xa0",
        "2_move_thunk": "Move vt+0xa0 @ 0x1404590 -> action.vt+0xc0 @ 0x12c3920",
        "3_Dummy_Post": "0x23f5cd0 stamps seq; builds stream; 0x22d8ad0 recreate",
        "4_factory": "0x22d8d20 -> table 0x35011e0 -> 0x13fb000 Move",
        "5_header_read": "cmd.vt+0x20 @ 0x22d90f0 then payload read vt slot",
        "6_ring": "push recreated at server+0xa0",
        "7_drain": "vt+0x30 -> pending +0x58 -> stage -> Execute",
        "posting": "DISABLED until independent proof",
    }

    idler = u64(base + ov["G_IDLER"])
    session = u64(u64(idler + 0x530) + 0x380)
    server = u64(session + 0x40)
    out["live"] = {
        "pid": b.pid,
        "tick": u32(session + 0x84),
        "drain": u32(session + 0x60),
        "exec": u32(session + 0x6C8),
        "seq": u32(server + 0xD0),
        "session_0x725": u8(session + 0x725),
        "lists_empty": u64(server + 0x40) == 0 and u64(server + 0x58) == 0,
    }

    b.close()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
    print("wrote", args.out)
    print("deser_slot", deser_slot, "fn", out.get("deserialize_fn"))
    print("payload_read_slot", out.get("payload_read_vt_slot_from_shared"))
    print("cands", read_cands)
    print("Cancel_a0", out.get("Cancel_vt_0xa0"), "Chat_a0", out.get("Chat_vt_0xa0"))
    print("live", out["live"])


if __name__ == "__main__":
    main()
