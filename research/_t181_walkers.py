import sys, struct, re, json, bisect, collections
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

# Reuse interesting list, tighten with capstone on the function itself
d=json.loads(Path("research/t181_add30_adj_funcs.json").read_text(encoding="utf-8"))

def is_stack(s):
    return "rsp" in s or "rbp" in s

good=[]
for it in d["interesting"]:
    f=int(it["func"],16)
    fo=func_of(f)
    if not fo: continue
    size=min(fo[1]-fo[0], 0x10000)
    raw=pe.read_rva(f, size) or b""
    data_ins=[]; size_ins=[]; type_ins=[]; imm23=[]; add30=[]
    for i in cs.disasm(raw, f):
        s=i.op_str
        line=f"0x{i.address:x} {i.mnemonic} {s}"
        if i.mnemonic=="add" and s.endswith(", 0x30") and "rsp" not in s and "rbp" not in s:
            add30.append(line)
        if not is_stack(s):
            if i.mnemonic in ("mov","lea") and "qword ptr [" in s and "+ 0x70]" in s:
                data_ins.append(line)
            if i.mnemonic in ("mov","cmp","movsxd") and "dword ptr [" in s and "+ 0x7c]" in s:
                size_ins.append(line)
            # type byte from record: +0x10, byte/movzx/cmp
            if "+ 0x10]" in s and i.mnemonic in ("cmp","movzx","movsx","mov"):
                if "byte ptr" in s or i.mnemonic in ("movzx","movsx"):
                    type_ins.append(line)
        # cmp with 2 or 3 on al/eax after possible type load
        if i.mnemonic=="cmp" and (s.endswith(", 2") or s.endswith(", 3") or s.endswith(", 2") or ", 0x2" in s or ", 0x3" in s):
            if "byte" in s or s.startswith("al") or s.startswith("eax") or s.startswith("r") or "dil" in s or "sil" in s or "b," in s:
                imm23.append(line)
    if data_ins and size_ins and add30:
        rec={"func":it["func"],"end":it["end"],"add30":add30[:8],"data":data_ins[:8],"size":size_ins[:8],
             "type_byte":type_ins[:20],"cmp_2_3":imm23[:20]}
        good.append(rec)

print("adjacency-like funcs", len(good))
# print those with type byte or cmp 2/3
for rec in good:
    if rec["type_byte"] or rec["cmp_2_3"]:
        print("====", rec["func"], "end", rec["end"])
        print("  type:", rec["type_byte"])
        print("  cmp23:", rec["cmp_2_3"][:12])
        print("  data:", rec["data"][:4])
        print("  add30:", rec["add30"][:4])

print("ALL funcs", [g["func"] for g in good])
Path("research/t181_adj_walkers.json").write_text(json.dumps({"count":len(good),"funcs":good}, indent=2)+"\n", encoding="utf-8")
