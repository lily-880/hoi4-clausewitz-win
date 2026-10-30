"""Phase 2ak — CUnitMoveAction field semantics via Execute body; RO."""
from __future__ import annotations
import argparse, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "calling"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "research", "re-dumps", "phase2ak_report.json"))
    args = ap.parse_args()
    out = {
        "phase": "2ak",
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

    def disasm(rva, n=0x300, max_lines=120, stop_ret=True):
        lines = []
        for insn in md.disasm(b.read(base + rva, n), base + rva):
            lines.append(f"{hex(insn.address-base)}: {insn.mnemonic} {insn.op_str}")
            if stop_ret and insn.mnemonic == "ret":
                break
            if len(lines) >= max_lines:
                break
        return lines

    execute = 0x12C2670
    isvalid = 0x12C2CA0
    ctor = 0x12C1770

    out["Execute_disasm"] = disasm(execute, 0x280, max_lines=100, stop_ret=True)
    out["IsValid_disasm"] = disasm(isvalid, 0x120, max_lines=50, stop_ret=True)
    out["Ctor_disasm"] = disasm(ctor, 0x100, max_lines=40, stop_ret=True)

    # Collect field accesses [reg + off] in Execute where this is likely rbx/rsi/rdi/rcx
    field_use = []
    for insn in md.disasm(b.read(base + execute, 0x280), base + execute):
        if "[" in insn.op_str and any(
            f"+ 0x{o:x}" in insn.op_str or f"+ 0x{o:X}" in insn.op_str
            for o in (0x10, 0x18, 0x24, 0x28, 0x30, 0x3C, 0x50, 0x51, 0x52, 0x53, 0x55, 0x58, 0x5C, 8)
        ):
            field_use.append(f"{hex(insn.address-base)}: {insn.mnemonic} {insn.op_str}")
        # also catch +0x10 etc with different formatting
        elif any(x in insn.op_str for x in (
            "+ 0x10]", "+ 0x18]", "+ 0x24]", "+ 0x30]", "+ 0x3c]",
            "+ 0x50]", "+ 0x51]", "+ 0x58]", "+ 0x5c]", "+ 8]",
        )):
            field_use.append(f"{hex(insn.address-base)}: {insn.mnemonic} {insn.op_str}")
        if insn.mnemonic == "ret":
            break
    out["Execute_field_accesses"] = field_use

    # Ctor inits — look for mov [reg+off], imm
    ctor_inits = []
    for insn in md.disasm(b.read(base + ctor, 0x100), base + ctor):
        if insn.mnemonic.startswith("mov") and "[" in insn.op_str:
            ctor_inits.append(f"{hex(insn.address-base)}: {insn.mnemonic} {insn.op_str}")
        if insn.mnemonic == "ret" or len(ctor_inits) >= 30:
            break
    out["Ctor_inits"] = ctor_inits

    # Semantic hypotheses from prior 2w + Execute usage
    out["field_semantics_hypotheses"] = {
        "+0x08": "type token 0x3648 (2w)",
        "+0x10": "CFixedPoint/handle — serialized tag 0x28a3; likely unit or order target handle",
        "+0x18/+0x24": "vector A tag 0x2840 — likely province path / waypoints",
        "+0x30/+0x3c": "vector B tag 0x174 — likely unit ids or sub-orders",
        "+0x50..+0x55": "bool flags (attack/support/strategic/etc) — names TBD",
        "+0x58": "enum/mode default 1; serialized only if !=1 tag 0x37bc",
        "+0x5c": "bool flag tag 0x368f",
        "note": "hypotheses only until mid-flight sample or string xref labels them",
    }

    # Search nearby .rdata for strings xref'd from Execute (rough: scan for lea rip in Execute)
    str_refs = []
    for insn in md.disasm(b.read(base + execute, 0x280), base + execute):
        if insn.mnemonic == "lea" and "rip" in insn.op_str:
            # compute target
            # capstone gives like lea rdx, [rip + 0x1234]
            try:
                disp = insn.op_str.split("rip")[1]
                disp = disp.replace("+", "").replace("]", "").replace("[", "").strip()
                # form: " + 0xNN" or " - 0xNN"
                sign = 1
                if "-" in insn.op_str.split("rip")[1]:
                    sign = -1
                    num = insn.op_str.split("rip")[1].split("-")[1].split("]")[0].strip()
                else:
                    num = insn.op_str.split("rip")[1].split("+")[1].split("]")[0].strip()
                tgt = insn.address + insn.size + sign * int(num, 16)
                raw = b.read(tgt, 64)
                # if printable cstring
                if raw[0] != 0 and all(32 <= c < 127 or c == 0 for c in raw[:40]):
                    s = raw.split(b"\x00", 1)[0].decode("ascii", errors="ignore")
                    if len(s) >= 4:
                        str_refs.append({"at": hex(insn.address - base), "str": s[:80]})
            except Exception:
                pass
        if insn.mnemonic == "ret":
            break
    out["Execute_string_refs"] = str_refs

    idler = u64(base + ov["G_IDLER"])
    session = u64(u64(idler + 0x530) + 0x380)
    out["live"] = {
        "pid": b.pid,
        "tick": u32(session + 0x84),
        "drain": u32(session + 0x60),
        "exec": u32(session + 0x6C8),
        "note": "paused; never 5x",
    }

    b.close()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
    print("wrote", args.out)
    print("field_use", field_use[:20])
    print("ctor_inits", ctor_inits[:15])
    print("strs", str_refs)
    print("live", out["live"])


if __name__ == "__main__":
    main()
