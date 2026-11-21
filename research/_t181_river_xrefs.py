"""t181: xref river_crossing token; find type==2/3 consumers; RTTI."""
import sys, struct, json, re, bisect, collections
from pathlib import Path
sys.path.insert(0, "calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

pe = PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs = Cs(CS_ARCH_X86, CS_MODE_64)
cs.detail = False

# .pdata
pd = next(s for s in pe.sections if s.name == ".pdata")
raw_pd = pe.data[pd.raw_ptr:pd.raw_ptr + pd.raw_size]
functions = [struct.unpack_from("<III", raw_pd, o)[:2] for o in range(0, len(raw_pd) - 11, 12)]
starts = [x[0] for x in functions]

def func_of(rva):
    i = bisect.bisect_right(starts, rva) - 1
    if i < 0:
        return None
    s, e = functions[i]
    if s <= rva < e:
        return s, e
    return None

# collect text section
text = next(s for s in pe.sections if s.name == ".text")
# PE section virtual_address is RVA
text_rva = text.virtual_address
text_raw = pe.data[text.raw_ptr:text.raw_ptr + text.raw_size]
# sometimes virtual_size > raw
print("text rva", hex(text_rva), "raw", hex(len(text_raw)), "vsize", hex(text.virtual_size))

def lea_xrefs(dest, limit=50):
    # RIP-relative LEA: 48 8d 05/0d/15/1d/25/2d/35/3d + rel32
    # also 4c 8d ... for r8-r15
    hits = []
    data = text_raw
    for m in re.finditer(rb"[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]", data):
        at = text_rva + m.start()
        # instruction is 7 bytes: rex 8d modrm rel32
        if m.start() + 7 > len(data):
            continue
        rel = struct.unpack_from("<i", data, m.start() + 3)[0]
        target = at + 7 + rel
        if target == dest:
            fo = func_of(at)
            hits.append({"at": hex(at), "func": hex(fo[0]) if fo else None, "end": hex(fo[1]) if fo else None})
            if len(hits) >= limit:
                break
    return hits

# Also address-in-instruction: 48 8d / 4c 8d already; also mov r64, imm64? rare.
# Also lea with 0x8d without rex for 32-bit? less likely in 64-bit exe for pointers.

needles = {
    "river_crossing": 0x2b494b0,
    "river_crossing_factor": 0x2b6b3c8,
    "river_crossing_factor_against": 0x2b3eb58,
    "RIVER_CROSSING_PENALTY": 0x295bd08,
    "RIVER_CROSSING_PENALTY_LARGE": 0x295be00,
    "RIVER_CROSSING_SPEED_PENALTY": 0x295bf00,
    "RIVER_CROSSING_SPEED_PENALTY_LARGE": 0x295c018,
    "MODIFIER_RIVER_CROSSING_PENALTY_FACTOR": 0x2857490,
}

xmap = {}
for name, dest in needles.items():
    xs = lea_xrefs(dest, limit=80)
    xmap[name] = xs
    print(name, "lea xrefs", len(xs), [(h["at"], h["func"]) for h in xs[:15]])

# RTTI River/Crossing/Adjacency
db = pe.data
rtti = []
for m in re.finditer(rb"\.\?AV[ -~]{0,200}(?:River|Crossing|Adjacen|Strait)[ -~]{0,80}@@", db):
    # map file offset to rva roughly via sections
    off = m.start()
    rva = None
    for s in pe.sections:
        if s.raw_ptr <= off < s.raw_ptr + s.raw_size:
            rva = s.virtual_address + (off - s.raw_ptr)
            break
    rtti.append({"rva": hex(rva) if rva is not None else None, "s": m.group().decode("ascii", "replace")})
print("rtti", len(rtti))
for r in rtti:
    print(" ", r)

# also plain strings we may have missed
extra = []
for pat in [b"has_river", b"is_river", b"river_cross", b"RiverCrossing", b"RIVER_CROSS", b"across_river", b"crossing_river"]:
    for m in re.finditer(pat, db, re.I):
        # take surrounding C-string
        start = m.start()
        # walk back to NUL? just from here
        end = db.find(b"\x00", m.start())
        s = db[m.start():end].decode("latin1", "replace") if end!=-1 else "?"
        if len(s)>80: 
            continue
        off=m.start(); rva=None
        for sec in pe.sections:
            if sec.raw_ptr <= off < sec.raw_ptr + sec.raw_size:
                rva = sec.virtual_address + (off - sec.raw_ptr)
                break
        extra.append({"rva": hex(rva) if rva else None, "s": s})
# unique
seen=set(); uniq=[]
for e in extra:
    k=(e["rva"], e["s"])
    if k not in seen:
        seen.add(k); uniq.append(e)
print("extra strings", len(uniq))
for e in uniq:
    print(" ", e)

Path("research/t181_river_xrefs.json").write_text(json.dumps({"lea_xrefs":xmap,"rtti":rtti,"extra_strings":uniq}, indent=2)+"\n", encoding="utf-8")
print("wrote xrefs")
