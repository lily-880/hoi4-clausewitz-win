import sys, struct, re, json, bisect, collections
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64, CS_OP_MEM, CS_OP_IMM, CS_OP_REG

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
cs.detail=True
pd=next(s for s in pe.sections if s.name==".pdata")
raw_pd=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
functions=[struct.unpack_from("<III", raw_pd, o)[:2] for o in range(0,len(raw_pd)-11,12)]
starts=[x[0] for x in functions]
text=next(s for s in pe.sections if s.name==".text")
text_rva=text.virtual_address
text_raw=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]

def func_of(rva):
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

def disasm_func(start, end, maxn=200000):
    raw=pe.read_rva(start, min(end-start, maxn)) or b""
    return list(cs.disasm(raw, start))

# 0x2727420
fo=func_of(0x2727420)
print("func 0x2727420", fo and (hex(fo[0]), hex(fo[1])))
if fo:
    for i in disasm_func(fo[0], fo[1]):
        print(f"0x{i.address:x}  {i.mnemonic} {i.op_str}")

# E8 callers of 0x2727420
def e8_callers(dest, limit=40):
    hits=[]
    for m in re.finditer(rb"\xe8", text_raw):
        if m.start()+5>len(text_raw): continue
        at=text_rva+m.start()
        rel=struct.unpack_from("<i", text_raw, m.start()+1)[0]
        if at+5+rel==dest:
            fo=func_of(at)
            hits.append({"at":hex(at),"func":hex(fo[0]) if fo else None})
            if len(hits)>=limit: break
    return hits
print("callers of 0x2727420", e8_callers(0x2727420))

# NMilitary define funcs callers
for dest in (0x96fb40, 0x96fd50, 0x96ff60, 0x970170, 0x5a66a0):
    print(f"callers of {hex(dest)}", e8_callers(dest)[:15], "count scan...")

# type byte patterns in text
# cmp byte ptr [r/m + 0x10], imm 2 or 3
# encodings: 80 /7 ib  with disp8=0x10
# 80 78 10 02  [rax+0x10]
# 80 79 10 02  [rcx+0x10]
# 41 80 7c 24 10 02 etc.
patterns=[]
# raw search for 80 ?? 10 02 and 80 ?? 10 03 and 41 80 ...
cands=[]
for typ in (2,3):
    # 80 7r 10 typ  where 7r is 78-7f (mod=01, /7, rm)
    for rm in range(8):
        pat=bytes([0x80, 0x78+rm, 0x10, typ])
        for m in re.finditer(re.escape(pat), text_raw):
            cands.append((text_rva+m.start(), typ, "80/7+r", pat.hex()))
        # rex.r or rex.b 41/44/45 etc 80 7r 10 typ
        for rex in (0x40,0x41,0x42,0x43,0x44,0x45,0x46,0x47,0x48,0x49,0x4a,0x4b,0x4c,0x4d,0x4e,0x4f):
            pat=bytes([rex, 0x80, 0x78+rm, 0x10, typ])
            for m in re.finditer(re.escape(pat), text_raw):
                cands.append((text_rva+m.start(), typ, "rex 80/7+r", pat.hex()))
    # SIB: 80 7c sib 10 typ  (mod=01, /7, rm=100 SIB, disp8=0x10)
    # 41 80 7c 00 10 02  [r8+rax+0x10] etc - too many SIB combos; search 80 7c ?? 10 02
    pat=rb"[\x40-\x4f]?\x80\x7c.\x10"+bytes([typ])
    for m in re.finditer(pat, text_raw):
        cands.append((text_rva+m.start(), typ, "sib 80/7", text_raw[m.start():m.end()].hex()))

print("cmp +0x10, 2/3 candidates", len(cands))
# unique by address
seen=set(); uniq=[]
for a,typ,k,hx in cands:
    if a in seen: continue
    seen.add(a)
    fo=func_of(a)
    # disasm
    off=a-text_rva
    ins=next(cs.disasm(text_raw[off:off+15], a), None)
    uniq.append({"at":hex(a),"typ":typ,"kind":k,"func":hex(fo[0]) if fo else None,"end":hex(fo[1]) if fo else None,
                 "asm": (ins.mnemonic+" "+ins.op_str) if ins else None})
print("unique", len(uniq))
# filter those whose asm is actually cmp byte ptr [...+0x10], 2/3
real=[u for u in uniq if u["asm"] and "0x10" in u["asm"] and (u["asm"].endswith(", 2") or u["asm"].endswith(", 3") or ", 2" in u["asm"] or ", 3" in u["asm"])]
print("asm-filtered", len(real))
for u in real[:80]:
    print(u)

Path("research/t181_type10_cmps.json").write_text(json.dumps({"count":len(real),"hits":real}, indent=2)+"\n", encoding="utf-8")
