from __future__ import annotations
import json, struct, sys
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
sys.path.insert(0, "calling")
from pe import PE
from mem import Proc, find_pid as mem_find_pid

EXE=r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
TABLE=0x35011E0
pe=PE(EXE)
cs=Cs(CS_ARCH_X86, CS_MODE_64)
p=Proc(mem_find_pid("hoi4.exe"))
base=p.base

def find_fn(rva):
    pdata=next(s for s in pe.sections if s.name.startswith(".pdata"))
    raw=pe.data[pdata.raw_ptr:pdata.raw_ptr+pdata.raw_size]
    n=len(raw)//12
    lo,hi=0,n-1
    while lo<=hi:
        mid=(lo+hi)//2
        b,e,u=struct.unpack_from("<III", raw, mid*12)
        if rva<b: hi=mid-1
        elif rva>=e: lo=mid+1
        else: return b,e
    return None

def pe_off_to_rva(off):
    for s in pe.sections:
        if s.raw_ptr<=off<s.raw_ptr+s.raw_size:
            return s.virtual_address+(off-s.raw_ptr)
    return None

def find_vt(name):
    needle=("."+"?AV"+name+"@@").encode("ascii")
    data=pe.data
    rvas=[]; start=0
    while True:
        i=data.find(needle, start)
        if i<0: break
        rvas.append(pe_off_to_rva(i)); start=i+1
    vts=[]
    rdata=[s for s in pe.sections if s.name.startswith(".rdata") or s.name.startswith(".data")]
    for str_rva in rvas:
        if str_rva is None: continue
        typedecl=str_rva-0x10
        target=struct.pack("<I", typedecl)
        for s in rdata:
            chunk=data[s.raw_ptr:s.raw_ptr+s.raw_size]
            off=0
            while True:
                j=chunk.find(target, off)
                if j<0: break
                if j>=0x0C:
                    col_rva=s.virtual_address+(j-0x0C)
                    va=pe.image_base+col_rva
                    needle2=struct.pack("<Q", va)
                    for s2 in rdata:
                        chunk2=data[s2.raw_ptr:s2.raw_ptr+s2.raw_size]
                        k=0
                        while True:
                            m=chunk2.find(needle2,k)
                            if m<0: break
                            vts.append(s2.virtual_address+m+8)
                            k=m+1
                off=j+1
    return sorted(set(vts))

def slots(vt,n=16):
    raw=pe.data[pe.rva_to_off(vt):pe.rva_to_off(vt)+n*8]
    out=[]
    for i in range(n):
        q=struct.unpack_from("<Q", raw, i*8)[0]
        rva=q-pe.image_base if pe.image_base<=q<pe.image_base+pe.size_of_image else None
        fn=find_fn(rva) if rva else None
        out.append({"slot":i,"rva":hex(rva) if rva else hex(q),
                    "fn": (hex(fn[0]),hex(fn[1]),fn[1]-fn[0]) if fn else None})
    return out

def factory(idx):
    slot=struct.unpack("<Q", p.read(base+TABLE+idx*8,8))[0]
    rva=slot-base
    head=pe.data[pe.rva_to_off(rva):pe.rva_to_off(rva)+16]
    size=None
    for i in range(0,12):
        if head[i]==0xB9:
            size=struct.unpack_from("<I", head, i+1)[0]; break
    return rva, head.hex(), size

out={}
for name, idx in (("COrderNewRootCommand",4096),):
    rva,head,size=factory(idx)
    vts=find_vt(name)
    out[name]={"idx":idx,"factory":hex(rva),"head":head,"size":size,"vts":[hex(v) for v in vts],
               "slots":{hex(v):slots(v) for v in vts[:2]}}
    print(json.dumps(out[name], indent=2))

# also find AddNewCompletePlan type/idx via RTTI + factory table scan later if needed
vts2=find_vt("COrderAddNewCompletePlanCommand")
print("AddNewComplete vts", [hex(v) for v in vts2[:6]])

Path("research/t193_bind_newroot.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")

# disasm IsValid/Execute once we have slots 9/10
if out["COrderNewRootCommand"]["vts"]:
    sl=out["COrderNewRootCommand"]["slots"][out["COrderNewRootCommand"]["vts"][0]]
    isv=int(sl[9]["rva"],16); exe=int(sl[10]["rva"],16)
    def dump(rva, n, title):
        lines=[]
        blob=pe.data[pe.rva_to_off(rva):pe.rva_to_off(rva)+n]
        for i in cs.disasm(blob, rva):
            lines.append(f"{hex(i.address)}  {i.mnemonic} {i.op_str}")
            if title.startswith("isvalid") and i.mnemonic=="ret" and int(hex(i.address),16)>rva+0x20:
                break
        Path(f"research/_t193_clip_{title}.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")
        print(f"\n======= {title} {hex(rva)} =====")
        for l in lines[:80] if not title.startswith("isvalid") else lines:
            print(l)
        return lines
    dump(isv, 0x200, f"COrderNewRootCommand_isvalid_{hex(isv)}")
    dump(exe, 0x200, f"COrderNewRootCommand_execute_{hex(exe)}")

p.close()
