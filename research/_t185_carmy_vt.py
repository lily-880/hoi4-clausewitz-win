import sys,os,struct,json
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from mem import Proc, find_pid
from gamestate import detect_session, resolve_player_country, _pdx_array, _rtti_name_from_vtable
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"

p=Proc(find_pid("hoi4.exe"))
pe=PE(p.image_path)
IMAGE=p.base
try:
    def isptr(x):
        return type(x) is int and 0x10000<x<0x7fffffffffff
    def cls(a):
        if not isptr(a): return None
        vt=p.ptr(a)
        if not vt or not (p.base<=vt<p.base+p.image_size): return None
        try:
            n=_rtti_name_from_vtable(pe, vt-p.base)
            return n if n and n.startswith((".?AV",".?AU")) and n.endswith("@@") else None
        except Exception:
            return None

    session=detect_session(p, pe)
    gs=int(session["signals"]["gs_ptr"],16)
    res=resolve_player_country(p, gs)
    co=int(res["country_ptr"],16)
    ar=_pdx_array(p, co+0x290)
    ap=p.ptr(ar["data"])  # first unit
    # dump first 0x80 qwords as vtables if they point into image
    vts=[]
    raw=p.try_read(ap, 0x80) or b""
    for off in range(0, 0x80, 8):
        v=struct.unpack_from("<Q", raw, off)[0]
        in_image = p.base<=v<p.base+p.image_size
        rva=v-p.base if in_image else None
        name=_rtti_name_from_vtable(pe, rva) if rva is not None else None
        if in_image:
            vts.append({"off":hex(off),"rva":hex(rva),"name":name})
    print("CArmy", hex(ap), "class", cls(ap), "uid", p.u32(ap+0x1c))
    print("image vtables in first 0x80:", json.dumps(vts, indent=2))

    # known vtables
    want={0x29d6d98,0x29d6f78,0x29d6fe8,0x29d7030,0x29cfcd8}
    # scan larger region for these exact vtable VAs
    found=[]
    blob=p.try_read(ap, 0x800) or b""
    for off in range(0, len(blob)-7, 8):
        v=struct.unpack_from("<Q", blob, off)[0]
        if p.base<=v<p.base+p.image_size:
            rva=v-p.base
            if rva in want or ( _rtti_name_from_vtable(pe, rva) or "").find("Combat")>=0:
                found.append({"off":hex(off),"rva":hex(rva),"name":_rtti_name_from_vtable(pe, rva)})
    print("interesting vts in 0x800", found)

    # also print 0x19eeaa0 clip we wrote
finally:
    p.close()

print("======= 0x19eeaa0 clip =======")
print(Path("research/_t185_clip_19eeaa0.txt").read_text(encoding="utf-8"))
print("======= 0x1613f40 start (land_combat) =======")
