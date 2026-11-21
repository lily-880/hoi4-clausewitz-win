import sys, struct, re, json, bisect
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
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

def disasm_range(start, end, maxn=120):
    raw=pe.read_rva(start, min(end-start, 0x4000)) or b""
    out=[]
    for i in cs.disasm(raw, start):
        if i.address>=end: break
        out.append(f"0x{i.address:x}  {i.mnemonic} {i.op_str}")
        if len(out)>=maxn: break
    return out

# disassemble define registrars (first 80 ins)
for f in (0x96fb40, 0x96fd50, 0x96ff60, 0x970170):
    fo=func_of(f)
    print("=======", hex(f), "window", fo and (hex(fo[0]), hex(fo[1])))
    print("\n".join(disasm_range(f, (fo[1] if fo else f+0x200), 60)))
    print()

# find add r64, 0x30  encodings: 48/4c 83 c0-c7 / c8-cf  30  (add r, 0x30) and 41/49 83 c0 30
# also 48 83 c4 30 is add rsp, 0x30 — skip rsp
sites=[]
# rex.w add r/m64, imm8: 48 83 /0 ib ; 4c is rex.w + rex.r (doesn't change rm)
# 49 83 /0 ib  rex.w rex.b
for rex,regnames in (
    (b"\x48\x83", ["rax","rcx","rdx","rbx","rsp","rbp","rsi","rdi"]),
    (b"\x49\x83", ["r8","r9","r10","r11","r12","r13","r14","r15"]),
):
    for rm,name in enumerate(regnames):
        if name=="rsp": 
            continue
        pat=rex+bytes([0xc0+rm, 0x30])
        for m in re.finditer(re.escape(pat), text_raw):
            at=text_rva+m.start()
            fo=func_of(at)
            sites.append({"at":hex(at),"reg":name,"func":hex(fo[0]) if fo else None,"end":hex(fo[1]) if fo else None})
print("add r64,0x30 sites", len(sites))
# unique funcs
funcs=sorted({s["func"] for s in sites if s["func"]})
print("unique funcs", len(funcs))
# For each func, see if it also references +0x70 or +0x7c or dword [..+8] like adjacency
interesting=[]
for fhex in funcs:
    f=int(fhex,16)
    fo=func_of(f)
    if not fo: continue
    size=min(fo[1]-fo[0], 0x8000)
    raw=pe.read_rva(f, size) or b""
    # crude: look for 0x70 / 0x7c as disp8 in the function bytes? too many FPs
    # disasm and look
    has70=has7c=has10=has8=has_type_cmp=False
    ins_hit=[]
    for i in cs.disasm(raw, f):
        s=i.op_str
        if "+ 0x70]" in s or "+ 0x70]" in s or "0x70]" in s:
            if i.mnemonic in ("mov","cmp","lea") and "qword" in s or "0x70" in s:
                has70=True
                if "0x70" in s: ins_hit.append(f"0x{i.address:x} {i.mnemonic} {s}")
        if "0x7c]" in s:
            has7c=True
            ins_hit.append(f"0x{i.address:x} {i.mnemonic} {s}")
        if "0x10]" in s and i.mnemonic in ("cmp","movzx","mov","movsx"):
            has10=True
            ins_hit.append(f"0x{i.address:x} {i.mnemonic} {s}")
    if has70 or has7c:
        interesting.append({"func":fhex,"end":hex(fo[1]),"has70":has70,"has7c":has7c,"has10":has10,
                            "add_sites":[s["at"] for s in sites if s["func"]==fhex],
                            "hits":ins_hit[:25]})
print("funcs with add 0x30 and 0x70/0x7c", len(interesting))
for it in interesting:
    print("---", it["func"], "has70", it["has70"], "has7c", it["has7c"], "has10", it["has10"], "adds", it["add_sites"])
    for h in it["hits"][:15]:
        print("   ", h)

Path("research/t181_add30_adj_funcs.json").write_text(json.dumps({"add30":len(sites),"interesting":interesting}, indent=2)+"\n", encoding="utf-8")
