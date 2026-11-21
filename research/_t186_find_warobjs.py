import sys,os,re,json,struct,collections,inspect
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from mem import Proc, find_pid
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from gamestate import detect_session, resolve_player_country, _pdx_array, _rtti_name_from_vtable, tag_for_index
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"

print("ETH", tag_for_index(44))
# find ITA by scanning 0..500
tags={}
for i in range(0, 500):
    t=tag_for_index(i)
    if t:
        tags[i]=t
print("n", len(tags), "ITA", [k for k,v in tags.items() if v=="ITA"], "ETH", [k for k,v in tags.items() if v=="ETH"])
print("sample", {k:tags[k] for k in list(tags)[:12]})

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
p=Proc(find_pid("hoi4.exe"))
try:
    def cls(a):
        if not a or a<0x10000 or a>0x7fffffffffff: return None
        try:
            vt=p.ptr(a)
        except Exception:
            return None
        if not vt or not (p.base<=vt<p.base+p.image_size): return None
        try:
            n=_rtti_name_from_vtable(pe, vt-p.base)
            return n
        except Exception:
            return None

    session=detect_session(p, pe)
    gs=int(session["signals"]["gs_ptr"],16)
    res=resolve_player_country(p, gs)
    co=int(res["country_ptr"],16)
    dip=p.ptr(co+0xf88)

    def scan_obj(base, size, label, interesting=("WarRelation","CRelation@@","Guarantee","Truce","Subject","Embargo","MilitaryAccess","NonAggression","LendLease","Attache","Blockade")):
        blob=p.try_read(base, size) or b""
        hits=[]
        for off in range(0, len(blob)-7, 8):
            v=struct.unpack_from("<Q", blob, off)[0]
            name=None
            kind="vt"
            if p.base<=v<p.base+p.image_size:
                name=_rtti_name_from_vtable(pe, v-p.base)
            elif 0x10000<v<0x7fffffffffff:
                name=cls(v)
                kind="ptr"
            if name and any(k in name for k in interesting):
                hits.append((hex(off), kind, hex(v), name))
        print(f"===== {label} n={len(hits)} =====")
        for h in hits[:40]:
            print(" ", h)
        return hits

    scan_obj(dip, 0x800, "ETH CDiplomacyStatus 0x800")
    # CRelationStatus for ITA if we know index
    ita=[k for k,v in tags.items() if v=="ITA"]
    data=p.ptr(dip+8)
    size=p.i32(dip+0x14)
    print("rel array size", size)
    if ita:
        idx=ita[0]
        print("ITA index", idx)
        if 0<=idx<size:
            rs=p.ptr(data+idx*8)
            print("ETH->ITA RelationStatus", hex(rs), cls(rs))
            scan_obj(rs, 0x400, "ETH-ITA CRelationStatus 0x400")

    # scan GS larger
    scan_obj(gs, 0x800, "GS 0x800 wide", interesting=("War","Diplomacy","Relation","Peace","Truce"))
    # countries array to get ITA country ptr? already have countries at gs fields

    # scan CCountry more of ETH for other managers
    scan_obj(co, 0x2000, "CCountry 0x2000", interesting=("War","Diplomacy","Relation","Peace","Truce","Diplo"))
finally:
    p.close()
