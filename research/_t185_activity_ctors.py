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

def func_of(rva):
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

def clip(start, end, path=None, force_end=None):
    if force_end:
        end=force_end
    raw=pe.read_rva(start, end-start) or b""
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

# For lea sites, get containing function and clip a window around the lea
leas = [0xce8fd9, 0xcecec9, 0xde6d15, 0x13357d0, 0x1338cec, 0x1338dd3, 0x146829d, 0x1468381, 0x14683db, 0x146921f, 0x1469306]
print("===== SArmyUnitActivityData lea sites =====")
for lea in leas:
    fo=func_of(lea)
    print(f"lea {hex(lea)} func {hex(fo[0]) if fo else None}-{hex(fo[1]) if fo else None} size {hex(fo[1]-fo[0]) if fo else None}")

# clip the two CArmy-region functions fully (or 0x400)
for start in (0xce8f00, 0xcece00):
    fo=func_of(start)
    # find func containing nearby lea
    pass

for lea,tag in ((0xce8fd9,"ce8fxx"),(0xcecec9,"cecexx")):
    fo=func_of(lea)
    start=fo[0] if fo else (lea & ~0xF) - 0x80
    end=(fo[1] if fo and fo[1]-fo[0]<0x800 else start+0x400)
    lines=clip(start, end, f"research/_t185_clip_activity_ctor_{tag}.txt")
    print(f"\n======= {hex(start)} ({tag}) n={len(lines)} =====")
    # print from a bit before lea to after, plus any interesting mem
    for ln in lines:
        if any(s in ln for s in ("0x29d7098","TOKEN","[r","lea r","mov qword ptr [","call 0x","combat","0x338","0x340","0x8]","0xc]")) or "29d7098" in ln:
            print(ln)

# also ctor of CSupplyConsumer
print("\n===== CSupplyConsumer lea funcs =====")
for lea in (0xc4e1aa, 0xca4aab):
    fo=func_of(lea)
    print(f"lea {hex(lea)} func {hex(fo[0]) if fo else None}-{hex(fo[1]) if fo else None}")
    start=fo[0] if fo else lea-0x80
    end=(fo[1] if fo and fo[1]-fo[0]<0x600 else start+0x300)
    lines=clip(start, end, f"research/_t185_clip_supplyconsumer_ctor_{hex(lea)}.txt")
    # show first/last and vtable writes
    useful=[ln for ln in lines if "29cfa58" in ln or "TOKEN" in ln or "mov qword ptr [" in ln]
    print("useful", len(useful), "total", len(lines))
    for ln in useful[:30]:
        print(" ", ln)

# CSupplyConsumer writer 0xf4ca30
fo=func_of(0xf4ca30)
start=0xf4ca30
end=(fo[1] if fo and fo[1]-start<0x800 else start+0x500)
# pdata may truncate; force through ret
lines=clip(start, start+0x600, "research/_t185_clip_supplyconsumer_writer_0xf4ca30.txt")
print(f"\n======= CSupplyConsumer writer 0xf4ca30 n={len(lines)} pdata={fo} =====")
toks=[ln for ln in lines if "TOKEN" in ln]
for ln in toks:
    print(ln)
# also layout mem
print("--- mem/call ---")
for ln in lines:
    if "TOKEN" in ln or re.search(r"\[rb[xip] \+", ln) or ln.strip().endswith("ret") or "call 0x" in ln and "254" not in ln:
        print(ln)
