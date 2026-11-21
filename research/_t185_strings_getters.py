import sys,re,json,struct,bisect
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
IMAGE=pe.image_base
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}
pd=next(s for s in pe.sections if s.name==".pdata")
raw_pd=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
functions=[struct.unpack_from("<III", raw_pd, o)[:2] for o in range(0,len(raw_pd)-11,12)]
starts=[x[0] for x in functions]
rdata=next(s for s in pe.sections if s.name==".rdata")
# also .data00 etc
def func_of(rva):
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

# string search across all sections
needles=[
    b"IsInCombat", b"InCombat", b"GetCombat", b"GetLandCombat", b"in_combat",
    b"is_in_combat", b"current_combat", b"pLandCombat", b"pCombat",
    b"in_supply", b"is_in_supply", b"isolated", b"is_isolated",
    b"SArmyUnitActivityData", b"ArmyUnitActivity",
    b"IsInLandCombat", b"GetCurrentCombat", b"HasCombat",
]
print("===== strings =====")
for s in pe.sections:
    blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
    for n in needles:
        for m in re.finditer(re.escape(n), blob):
            rva=s.virtual_address+m.start()
            # context
            start=max(0, m.start()-20)
            ctx=blob[start:m.start()+len(n)+40]
            ctx=bytes(b if 32<=b<127 else 0x2e for b in ctx)
            print(f"  {s.name} {hex(rva)} {n.decode()} ctx={ctx}")

# lea/rip xrefs for interesting strings we'll pick after

def clip(start, nbytes, path=None):
    raw=pe.read_rva(start, nbytes) or b""
    lines=[]
    for i in cs.disasm(raw, start):
        a=f"0x{i.address:x}  {i.mnemonic} {i.op_str}"
        m=re.search(r"(edx|r8d|r9d|esi|edi|eax|ecx), 0x([0-9a-f]+)", i.op_str)
        if m:
            tok=int(m.group(2),16)
            if tok in id2name:
                a += "  ; TOKEN "+id2name[tok]
        lines.append(a)
        if i.mnemonic=="ret" and i.address>start+12:
            break
    if path:
        Path(path).write_text("\n".join(lines)+"\n", encoding="utf-8")
    return lines

# CCombatManager writer 0xc0eae0
lines=clip(0xc0eae0, 0x400, "research/_t185_clip_combatmanager_writer_0xc0eae0.txt")
print("\n======= CCombatManager writer 0xc0eae0 n=%d ====="%len(lines))
for ln in lines:
    if "TOKEN" in ln or "call 0x" in ln or "ret" in ln.split()[-1:]:
        print(ln)

# 0x19ee700
lines=clip(0x19ee700, 0x120, "research/_t185_clip_19ee700.txt")
print("\n======= 0x19ee700 n=%d ====="%len(lines))
print("\n".join(lines))

# short CArmy primary vtable getters (first 40 slots)
raw=pe.read_rva(0x29d6d98, 0x150) or b""
print("\n======= CArmy primary short methods =====")
for i in range(0, 0x150, 8):
    v=struct.unpack_from("<Q", raw, i)[0]
    if not (IMAGE<=v<IMAGE+0x4000000):
        break
    fn=v-IMAGE
    rawf=pe.read_rva(fn, 32) or b""
    ins=list(cs.disasm(rawf, fn))
    text=" ; ".join(f"{x.mnemonic} {x.op_str}" for x in ins[:6])
    if any(x.mnemonic=="ret" for x in ins[:8]) and len(ins)<=8:
        print(f"  vt+{i:#x} {hex(fn)}  {text}")
