from __future__ import annotations
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
import sys
sys.path.insert(0, "calling")
from pe import PE

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
pe = PE(EXE)
cs = Cs(CS_ARCH_X86, CS_MODE_64)

def read_rva(rva, n):
    off = pe.rva_to_off(rva)
    return pe.data[off:off+n]

def dump(rva, n, title, filt=None):
    lines = []
    for i in cs.disasm(read_rva(rva, n), rva):
        line = f"{hex(i.address)}  {i.mnemonic} {i.op_str}"
        if filt is None or any(s in line.lower() for s in filt):
            lines.append(line)
    Path(f"research/_t192_clip_{title}.txt").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(f"\n======= {title} {hex(rva)}+{hex(n)} hits {len(lines)} =====")
    for line in lines[:200]:
        print(line)
    return lines

# search both writer candidates for displacements 0x1048/1068/1058 and token-like immediates
filt = ["0x1048", "0x1068", "0x1058", "0x1040", "0x41c7", "0x385b"]
for rva, n, title in (
    (0xC7E8C0, 0x400, "CArmyLeader_writer_0xc7e8c0"),
    (0xC7E930, 0x400, "CArmyLeader_writer_0xc7e930"),
    (0xC4D030, 0x400, "COrdersGroup_writer_0xc4d030"),
    (0xC4D0A0, 0x400, "COrdersGroup_writer_0xc4d0a0"),
):
    # first, print any interesting hits, but also write full clip
    full = []
    for i in cs.disasm(read_rva(rva, n), rva):
        full.append(f"{hex(i.address)}  {i.mnemonic} {i.op_str}")
    Path(f"research/_t192_clip_{title}.txt").write_text("\n".join(full)+"\n", encoding="utf-8")
    hits = [ln for ln in full if any(s in ln.lower() for s in ["0x1048","0x1068","0x1058","0x1040","0x41c7","0x50]", "0x5c", "0x160", "0x88", "0x18]"])]
    print(f"\n======= {title} hits =====")
    for ln in hits:
        print(ln)
    print(f"  (full {len(full)} ins, first: {full[0] if full else 'empty'})")
