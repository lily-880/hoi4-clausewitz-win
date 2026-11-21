from __future__ import annotations
import json, re, struct, sys
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
sys.path.insert(0, "calling")
from pe import PE
from mem import Proc, find_pid as mem_find_pid
from gamestate import detect_session, resolve_player_country, _rtti_name_from_vtable, read_campaign_summary

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
pe = PE(EXE)
cs = Cs(CS_ARCH_X86, CS_MODE_64)
cs.detail = False

# --- ORDER_ strings ---
rdata = next(s for s in pe.sections if s.name.startswith(".rdata"))
rblob = pe.data[rdata.raw_ptr:rdata.raw_ptr+rdata.raw_size]
order_strs = []
for m in re.finditer(rb"ORDER_[A-Z0-9_]+", rblob):
    a = m.start()
    while a > 0 and 32 <= rblob[a-1] < 127:
        a -= 1
    b = m.end()
    while b < len(rblob) and 32 <= rblob[b] < 127:
        b += 1
    full = rblob[a:b].decode("latin1")
    order_strs.append({"rva": hex(rdata.virtual_address + a), "s": full[:240]})

# unique ORDER_ tokens
tokens = sorted({re.search(r"ORDER_[A-Z0-9_]+", x["s"]).group() for x in order_strs})
print("ORDER_ tokens:", tokens)

# GetOrderType assert strings
for m in re.finditer(rb"GetOrderType\(\)[^\x00]{0,80}", rblob):
    s = m.group().decode("latin1", "replace")
    print("ASSERT", hex(rdata.virtual_address+m.start()), s)

# jump table 0xfcc818
print("\n======= jump table 0xfcc818 types 2..13 =======")
raw = pe.data[pe.rva_to_off(0xfcc818):pe.rva_to_off(0xfcc818)+12*4]
entries = []
for i in range(12):
    off = struct.unpack_from("<I", raw, i*4)[0]
    typ = i+2
    entries.append((typ, off))
    print(f"  type {typ:2d}  entry=0x{off:x}")

# disasm each unique entry + 40 insns, look for string refs / tokens
def disasm(rva, n=80):
    blob = pe.data[pe.rva_to_off(rva):pe.rva_to_off(rva)+n]
    return list(cs.disasm(blob, rva))

# find lea/rip-relative string refs in each entry function
def rip_strings(rva, nbytes=0x120):
    ins = disasm(rva, nbytes)
    out = []
    for i in ins:
        if i.mnemonic in ("lea", "mov") and "rip" in i.op_str:
            # parse [rip + disp]
            m = re.search(r"rip [\+\-] 0x([0-9a-f]+)", i.op_str)
            if not m:
                continue
            disp = int(m.group(1), 16)
            if "-" in i.op_str.split("rip",1)[1][:3]:
                tgt = i.address + i.size - disp
            else:
                tgt = i.address + i.size + disp
            # try cstring
            try:
                b = pe.data[pe.rva_to_off(tgt):pe.rva_to_off(tgt)+80]
            except Exception:
                continue
            if b"\x00" in b:
                b = b.split(b"\x00",1)[0]
            if b and all(32 <= x < 127 or x in (9,10,13) for x in b) and len(b) >= 3:
                out.append((hex(i.address), i.mnemonic+" "+i.op_str, b.decode("latin1")))
        if i.mnemonic == "ret":
            break
    return out, ins

print("\n======= jump entry strings =======")
for typ, off in entries:
    strs, ins = rip_strings(off, 0x180)
    print(f"\n--- type {typ} @ {hex(off)} ---")
    for s in strs:
        print(" ", s)
    # also print first 12 insns
    for i in ins[:12]:
        print(f"  {hex(i.address)}  {i.mnemonic} {i.op_str}")

# RTTI command names of interest
print("\n======= COrder* / CSet* RTTI (filtered) =======")
data = pe.data
names = []
for m in re.finditer(rb"\.\?AVC[A-Za-z0-9_]+Command@@", data):
    s = m.group().decode("ascii")
    if any(k in s for k in ("Order", "Leader", "Path", "Front", "Assign", "Execute", "Garrison", "Defense", "Offensive", "Army")):
        names.append(s[4:-2])  # strip .?AV and @@
for n in sorted(set(names)):
    print(" ", n)
