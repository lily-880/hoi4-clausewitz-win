from __future__ import annotations
import json, struct, sys, bisect
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

sys.path.insert(0, "calling")
from pe import PE

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
pe = PE(EXE)
cs = Cs(CS_ARCH_X86, CS_MODE_64)
pd = next(s for s in pe.sections if s.name == ".pdata")
raw = pe.data[pd.raw_ptr:pd.raw_ptr + pd.raw_size]
functions = []
for i in range(0, len(raw) - 11, 12):
    start, end, _ = struct.unpack_from("<III", raw, i)
    if start and end and end > start:
        functions.append((start, end))
starts = [s for s, e in functions]


def rva_to_off(rva):
    return pe.rva_to_off(rva)


def read_rva(rva, n):
    off = rva_to_off(rva)
    return pe.data[off:off + n] if off is not None else b""


def disasm(start, end):
    blob = read_rva(start, end - start)
    return [{"rva": hex(i.address), "asm": i.mnemonic + " " + i.op_str} for i in cs.disasm(blob, start)]


post = disasm(0x22C4250, 0x22C4780)
# interesting instructions
keys = []
for ins in post:
    a = ins["asm"]
    if any(s in a for s in (
        "0x28", "0x40", "0x725", "0x726", "0x6cc", "0x6c8",
        "call qword", "call 0x", "0x34ffbe8", "0x23f5d40",
    )):
        keys.append(ins)

# also command IsValid 0x1400360
iv_bounds = None
i = bisect.bisect_right(starts, 0x1400360) - 1
if i >= 0 and functions[i][0] <= 0x1400360 < functions[i][1]:
    iv_bounds = functions[i]
iv = disasm(iv_bounds[0], min(iv_bounds[1], iv_bounds[0] + 0x200)) if iv_bounds else []

# action isvalid candidates
for rva in (0x12C2D10, 0x12C2CD0, 0x12C26E0):
    j = bisect.bisect_right(starts, rva) - 1
    if j >= 0 and functions[j][0] <= rva < functions[j][1]:
        print(f"func of {hex(rva)} = {hex(functions[j][0])}-{hex(functions[j][1])} size {functions[j][1]-functions[j][0]}")

Path("research/_t191_clip_fn_post_0x22c4250.txt").write_text(
    "\n".join(f"{x['rva']}  {x['asm']}" for x in post) + "\n", encoding="utf-8"
)
Path("research/_t191_clip_move_isvalid_0x1400360.txt").write_text(
    f"function {hex(iv_bounds[0]) if iv_bounds else None}-{hex(iv_bounds[1]) if iv_bounds else None}\n"
    + "\n".join(f"{x['rva']}  {x['asm']}" for x in iv) + "\n",
    encoding="utf-8",
)
print("POST interesting:")
for x in keys:
    print(f"  {x['rva']}  {x['asm']}")
print("ISVALID head:")
for x in iv[:40]:
    print(f"  {x['rva']}  {x['asm']}")
