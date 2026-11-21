# Bind COrderNewFrontCommand on 1.19.5 and confirm session + t192 contrasts
from __future__ import annotations
import json, struct, sys
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
sys.path.insert(0, "calling")
from pe import PE
from mem import Proc, find_pid as mem_find_pid
from gamestate import detect_session, resolve_player_country, _rtti_name_from_vtable, read_campaign_summary

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
TABLE = 0x35011E0
EXPECTED_PID = 26976
EXPECTED_GS = 0x26C259D0FF0
EXPECTED_CO = 0x26C4B672530
GROUP = 0x26d2b077020  # may have moved? we'll find via theatre

def is_ptr(x):
    return type(x) is int and 0x100000000 < x < 0x7FFFFFFFFFFF

def pdx(p,a):
    data,cap,size=struct.unpack("<QII", p.read(a,16))
    return data,cap,size

def ptr_array(p,a,bound=4096):
    data,cap,size=pdx(p,a)
    if not 0<=size<=cap<=max(bound,100) or (size and not is_ptr(data)):
        return []
    return [struct.unpack("<Q", p.read(data+8*j,8))[0] for j in range(size)]

def cls(p,pe,a):
    if not is_ptr(a):
        return None
    vt=struct.unpack("<Q", p.read(a,8))[0]
    if not p.base<=vt<p.base+p.image_size:
        return None
    return _rtti_name_from_vtable(pe, vt-p.base)

def unit_path(p,ap):
    data,cap,size=pdx(p, ap+0x200)
    if size<=0 or not is_ptr(data) or size>64:
        return []
    raw=p.read(data,size*4)
    return list(struct.unpack("<"+"I"*size, raw))

def find_fn(pe, rva):
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

def pe_off_to_rva(pe, off):
    for s in pe.sections:
        if s.raw_ptr <= off < s.raw_ptr+s.raw_size:
            return s.virtual_address + (off-s.raw_ptr)
    return None

def find_vt(pe, name):
    needle=("."+"?AV"+name+"@@").encode("ascii")
    data=pe.data
    # find COL then vtable like t192 - simplified: search rdata for string, typedecl-0x10
    rvas=[]
    start=0
    while True:
        i=data.find(needle, start)
        if i<0: break
        rvas.append(pe_off_to_rva(pe,i))
        start=i+1
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
                            vt_rva=s2.virtual_address+m+8  # typical: col ptr then vt
                            # verify pointer-looking
                            if m>=8:
                                # vtable often 8 bytes after COL pointer at object layout?
                                pass
                            # complete object locator is pointed to by vt[-1] = vt_rva-8 holds COL
                            # so if needle2 is at m, vt is m+8
                            vts.append(s2.virtual_address+m+8)
                            k=m+1
                off=j+1
    return sorted(set(vts))

process_pid=mem_find_pid("hoi4.exe")
p=Proc(process_pid)
pe=PE(EXE)
cs=Cs(CS_ARCH_X86, CS_MODE_64)
session=detect_session(p,pe)
gs=int(session["signals"]["gs_ptr"],16)
co=int(resolve_player_country(p,gs)["country_ptr"],16)
idler=int(session["signals"].get("idler_ptr") or "0",16)
summary=read_campaign_summary(p,gs)
ver=summary.get("verified") or {}
date=ver.get("date_full") or ver.get("date") or {}

# find unit 1829 path and theatre groups
def find_unit(uid):
    for ap in ptr_array(p, co+0x290, 4096):
        if struct.unpack("<I", p.read(ap+0x1C,4))[0]==uid:
            return ap
    return 0

u1829=find_unit(1829); u1838=find_unit(1838)
theatres=ptr_array(p, co+0x168, 64)
tp=theatres[0]
ogs=ptr_array(p, tp+0x80, 256)
fms=ptr_array(p, tp+0x98, 256)
tgs=ptr_array(p, tp+0xC8, 256)
og=ogs[0] if ogs else 0

def msvc_string(a):
    blob=p.read(a,32)
    n,cap=struct.unpack_from("<QQ", blob,16)
    if not 0<=n<=1024 or cap<n: return None
    raw=blob[:n] if cap<=15 else p.read(struct.unpack_from("<Q",blob)[0], n)
    return raw.decode("utf-8","replace")

session_out={
    "process_pid": process_pid,
    "pid_ok": process_pid==EXPECTED_PID,
    "in_game": session.get("in_game"),
    "gs": hex(gs), "co": hex(co),
    "gs_ok": gs==EXPECTED_GS, "co_ok": co==EXPECTED_CO,
    "date": date,
    "pause": p.read(idler+0x6C1,1)[0] if idler else None,
    "speed": struct.unpack("<i", p.read(gs+0x4BC,4))[0],
    "path_1829": unit_path(p,u1829) if u1829 else None,
    "u1838": hex(u1838) if u1838 else None,
    "theatre": {"ptr":hex(tp),"class":cls(p,pe,tp),"handle":struct.unpack("<II", p.read(tp+8,8)),
                "orders_n":len(ogs),"fm_n":len(fms),"tg_n":len(tgs)},
}
if og:
    leader=struct.unpack("<Q", p.read(og+0x88,8))[0]
    session_out["army1"]={
        "ptr":hex(og),"class":cls(p,pe,og),"handle":struct.unpack("<II", p.read(og+8,8)),
        "name":msvc_string(og+0x160),
        "leader": hex(leader),
        "leader_class": cls(p,pe,leader),
        "leader_handle": struct.unpack("<II", p.read(leader+8,8)) if is_ptr(leader) else None,
        "fm_flag_39": p.read(og+0x39,1)[0],
        "order_instance_n": pdx(p, og+0x98)[2],
        "c0_1838": hex(struct.unpack("<Q", p.read(u1838+0xC0,8))[0]) if u1838 else None,
    }

# factory slot 4095
# live table: each slot 8-byte fn ptr. Confirm index scheme.
# t191: idx = tid-0x2328?  type 0x3327 -> 0x3327-0x2328=0xFFF=4095. Yes idx=4095.
base=p.base
slot=p.u64(base+TABLE+4095*8) if hasattr(p,"u64") else struct.unpack("<Q", p.read(base+TABLE+4095*8,8))[0]
factory_rva=slot-base if base<=slot<base+p.image_size else None
# factory head
head=pe.data[pe.rva_to_off(factory_rva):pe.rva_to_off(factory_rva)+16] if factory_rva else b""
# size from mov ecx, imm
size=None
if head[4:7]==b"\x83\xec\x20" or True:
    # look for b9 xx xx 00 00 (mov ecx, size)
    for i in range(0,16-5):
        if head[i]==0xB9:
            size=struct.unpack_from("<I", head, i+1)[0]
            break

# RTTI vtables
vts=find_vt(pe, "COrderNewFrontCommand")
# For each vt, read vtable slots for IsValid/Execute. Typical CCommand: IsValid often slot, Execute another.
# t192 used vt+some. Let's read first 16 slots and match pdata functions around factory+nearby or +0x70 from old.

# old vt 0x2a84b10, we'll get live vt from rtti
# IsValid/Execute: from bound pattern, read vt slots. Need to know slot index.
# Load how t192 bind did it - typically slot 0 dtor, ... I'll read 16 qwords and list rtti-relative.

def vt_slots(vt_rva, n=16):
    raw=pe.data[pe.rva_to_off(vt_rva):pe.rva_to_off(vt_rva)+n*8]
    out=[]
    for i in range(n):
        q=struct.unpack_from("<Q", raw, i*8)[0]
        rva=q-pe.image_base if pe.image_base<=q<pe.image_base+pe.size_of_image else None
        fn=find_fn(pe,rva) if rva else None
        out.append({"slot":i,"rva":hex(rva) if rva else hex(q), "fn": (hex(fn[0]), hex(fn[1]), fn[1]-fn[0]) if fn else None})
    return out

bind={"factory_idx":4095,"type_id":hex(0x3327),"factory_rva":hex(factory_rva) if factory_rva else None,
      "factory_head": head.hex(),"size":size,"vts":[hex(v) for v in vts],
      "vt_slots": {hex(v): vt_slots(v) for v in vts[:4]}}

# also factory 5433 already known; record army group create call
# write NewFront IsValid/Execute once we know slots. Heuristic: largest non-dtor .text functions.
# For COrderGroupCommand, IsValid and Execute were specific. We'll disassemble later.

Path("research/t193_session_recheck.json").write_text(json.dumps(session_out, indent=2, ensure_ascii=False, default=str)+"\n", encoding="utf-8")
Path("research/t193_bind_newfront.json").write_text(json.dumps(bind, indent=2, ensure_ascii=False, default=str)+"\n", encoding="utf-8")
print(json.dumps({"session":session_out,"bind":{"factory_rva":bind["factory_rva"],"size":size,"vts":bind["vts"],"slots_preview":bind["vt_slots"]}}, indent=2, ensure_ascii=False))
p.close()
