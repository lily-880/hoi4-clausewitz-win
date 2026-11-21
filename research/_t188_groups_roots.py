import sys, json, os, struct, re
from pathlib import Path
sys.path.insert(0, "calling")
from pe import PE
from mem import Proc, find_pid
from gamestate import detect_session, resolve_player_country, _pdx_array, _rtti_name_from_vtable
from country_tags import tag_for_index
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}

# token 0x30ae sites
text=[s for s in pe.sections if s.name==".text"][0]
blob=pe.read_rva(text.virtual_address, text.virtual_size) or b""
base=text.virtual_address
tok=struct.pack("<I", 0x30ae)
print("=== mov edx, orders_group 0x30ae ===")
start=0
while True:
    k=blob.find(tok, start)
    if k<0: break
    if k>=1 and blob[k-1]==0xBA:
        rva=base+k-1
        # print a few lines around by disasm 32 bytes before
        raw=pe.read_rva(rva-24, 48) or b""
        lines=[]
        for i in cs.disasm(raw, rva-24):
            a=f"0x{i.address:x}  {i.mnemonic} {i.op_str}"
            if i.address==rva:
                a += "  ; TOKEN orders_group"
            lines.append(a)
        print(f"--- 0x{rva:x} ---")
        for ln in lines:
            if ln.startswith(f"0x{rva-24:x}") or "TOKEN" in ln or "lea r8" in ln or "lea rdx" in ln or "call " in ln or "mov edx" in ln:
                print(" ", ln)
    start=k+1

# also field_marshal 0x3801, theater_group 0x35d1
for name,t in (("field_marshal_group",0x3801),("theater_group",0x35d1),("order_instance",0x35f7)):
    imm=struct.pack("<I", t)
    sites=[]
    start=0
    while True:
        k=blob.find(imm, start)
        if k<0: break
        if k>=1 and blob[k-1]==0xBA:
            sites.append(base+k-1)
        start=k+1
        if len(sites)>=20: break
    print(f"{name} sites: " + " ".join(hex(s) for s in sites[:15]))

p=Proc(find_pid("hoi4.exe"))
def u64(a):
    b=p.try_read(a,8)
    return struct.unpack("<Q", b)[0] if b and len(b)==8 else None
def cls(ptr):
    if not ptr or ptr<0x10000: return None
    vt=u64(ptr)
    if not vt: return None
    try:
        return _rtti_name_from_vtable(pe, vt-p.base)
    except Exception as e:
        return f"err:{e}"
def parr(obj, off):
    try:
        a=_pdx_array(p, obj+off)
        return {"size": a.get("size"), "capacity": a.get("capacity"), "data": a.get("data")}
    except Exception as e:
        return {"error": str(e)}

try:
    session=detect_session(p, pe)
    gs=int(session["signals"]["gs_ptr"],16)
    countries=_pdx_array(p, gs+0x310)
    cdata=int(countries["data"])
    want={16,44}
    # also majors by scanning tags
    majors=["GER","ITA","ETH","FRA","ENG","SOV","JAP","USA","CHI","RAJ","MAN","SPR","BEL"]
    print("\n=== theatre counts ===")
    rows=[]
    for ci in range(int(countries["size"])):
        cptr=u64(cdata+ci*8)
        if not cptr: continue
        tag=tag_for_index(ci)
        th=parr(cptr, 0x168)
        size=th.get("size") or 0
        if size or tag in majors or ci in want:
            # also try to list first theatre orders_group
            og=None
            if size and th.get("data"):
                tp=u64(int(th["data"]))
                og=parr(tp, 0x80) if tp else None
                tcls=cls(tp)
            else:
                tcls=None
            rows.append({"index":ci,"tag":tag,"theatres":size,"first_th_class":tcls,"first_og":og})
    for r in rows:
        if r["theatres"] or r["tag"] in majors:
            print(r)
    print("countries with theatres", sum(1 for r in rows if r["theatres"]))
    print("sum theatre sizes", sum(r["theatres"] or 0 for r in rows))
finally:
    p.close()
