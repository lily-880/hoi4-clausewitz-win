import sys, struct, json, os, collections
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from mem import Proc, find_pid
from gamestate import detect_session, resolve_player_country, _pdx_array, _rtti_name_from_vtable
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
p=Proc(find_pid("hoi4.exe"))
IMAGE=pe.image_base
try:
    def ptr(x):
        return type(x) is int and 0x10000 < x < 0x7fffffffffff
    def q(a):
        b=p.read(a,8)
        return struct.unpack("<Q",b)[0] if b and len(b)==8 else None
    def i32(a):
        b=p.read(a,4)
        return struct.unpack("<i",b)[0] if b and len(b)==4 else None
    def u32(a):
        b=p.read(a,4)
        return struct.unpack("<I",b)[0] if b and len(b)==4 else None
    def cls(a):
        if not ptr(a): return None
        try:
            vt=q(a)
            if not ptr(vt) or vt < IMAGE: return None
            return _rtti_name_from_vtable(pe, vt-IMAGE)
        except Exception:
            return None
    def text(a):
        b=p.read(a,32)
        if not b or len(b)!=32: return None
        n,c=struct.unpack_from("<QQ",b,16)
        if n>512 or c<n: return None
        raw=b[:n] if c<=15 else p.read(struct.unpack_from("<Q",b)[0], n)
        if raw is None or len(raw)!=n: return None
        try:
            s=raw.decode("utf-8")
            return s if all(ch.isprintable() for ch in s) else None
        except Exception:
            return None

    session=detect_session(p, pe)
    gs=int(session["signals"]["gs_ptr"],16)
    res=resolve_player_country(p, gs)
    co=int(res["country_ptr"],16)

    print("country class", cls(co), "gs class", cls(gs))
    cm=q(gs+0x6a8)
    print("cm", hex(cm or 0), cls(cm))
    chars_arr=_pdx_array(p, cm+0x10) if ptr(cm) else None
    print("chars_arr", chars_arr)
    # sample first 5 characters: class, name-like strings at several offsets
    samples=[]
    if chars_arr:
        for j in range(min(5, chars_arr["size"])):
            cp=q(chars_arr["data"]+j*8)
            rec={"ptr":hex(cp or 0),"class":cls(cp),"names":{}}
            for off in (0x10,0x18,0x20,0x28,0x30,0x38,0x40,0x48,0x50):
                rec["names"][hex(off)]=text(cp+off)
            rec["roles80"]=_pdx_array(p, cp+0x80)
            if rec["roles80"] and rec["roles80"]["size"]<=16 and rec["roles80"]["size"]>0:
                rec["role0"]=cls(q(rec["roles80"]["data"]))
            rec["a8"]=hex(q(cp+0xa8) or 0)
            rec["a8cls"]=cls(q(cp+0xa8))
            samples.append(rec)
    print(json.dumps(samples, indent=2, ensure_ascii=False))

    # also scan country pointers now that RTTI works
    managers=[]
    cob=p.read(co, 0x900) or b""
    for off in range(0x8, min(len(cob)-7, 0x8f8), 8):
        v=struct.unpack_from("<Q", cob, off)[0]
        c=cls(v) if ptr(v) else None
        if c and any(s in c for s in ("Character","Leader","Theatre","Army","Command","Manager","Group")):
            managers.append({"off":hex(off),"ptr":hex(v),"class":c})
    print("managers", json.dumps(managers, ensure_ascii=False))
finally:
    p.close()
