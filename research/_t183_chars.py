import sys, struct, json, os, collections
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from mem import Proc, find_pid
from gamestate import detect_session, resolve_player_country, _pdx_array, _rtti_name_from_vtable
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"

p=Proc(find_pid("hoi4.exe"))
pe=PE(p.image_path)
try:
    def isptr(x):
        return type(x) is int and 0x10000 < x < 0x7fffffffffff
    def cls(a):
        if not isptr(a): return None
        vt=p.ptr(a)
        if not vt or not (p.base <= vt < p.base+p.image_size): return None
        try:
            n=_rtti_name_from_vtable(pe, vt-p.base)
            return n if n and n.startswith((".?AV",".?AU")) and n.endswith("@@") else None
        except Exception:
            return None

    session=detect_session(p, pe)
    gs=int(session["signals"]["gs_ptr"],16)
    res=resolve_player_country(p, gs)
    co=int(res["country_ptr"],16)
    player=res["player_index"]
    cm=p.ptr(gs+0x6a8)
    print("cm", hex(cm), cls(cm))
    arr=_pdx_array(p, cm+0x10)
    print("chars", arr["size"], "first class", cls(p.ptr(arr["data"])))

    # inspect first character layout: strings + roles + owner-like fields
    cp0=p.ptr(arr["data"])
    print("char0", hex(cp0), cls(cp0))
    for off in range(0x10, 0x80, 8):
        s=p.msvc_string(cp0+off)
        if s:
            print(" str", hex(off), s[:80])
    for off in (0x8,0xc,0x10,0x14,0x18,0x1c,0x40,0x44,0x48,0x4c,0x50,0x54):
        print(" i32", hex(off), p.i32(cp0+off))
    for off in range(0x60, 0x100, 8):
        ar2=_pdx_array(p, cp0+off)
        if ar2 and 0<ar2["size"]<=32 and ar2["size"]<=ar2["capacity"]<=64:
            print(" arr", hex(off), ar2["size"], "first", cls(p.ptr(ar2["data"])))
        pv=p.ptr(cp0+off)
        c=cls(pv)
        if c:
            print(" ptr", hex(off), c, hex(pv))

    # scan a slice to find ETH_ names and CArmyLeader roles
    eth=[]
    n_chars_ok=0
    n_army_leader_roles_total=0
    role_classes=collections.Counter()
    name_off_hits=collections.Counter()
    # determine name offset from first 200 chars
    for j in range(min(200, arr["size"])):
        cp=p.ptr(arr["data"]+j*8)
        if cls(cp) and "Character" in (cls(cp) or ""):
            n_chars_ok += 1
        for off in (0x18,0x20,0x28,0x30,0x38):
            s=p.msvc_string(cp+off) if cp else None
            if s and ("_" in s or s.isalpha()) and 2<=len(s)<=80:
                name_off_hits[off]+=1
                if s.startswith("ETH") or "ETH_" in s:
                    eth.append({"idx":j,"off":hex(off),"name":s,"ptr":hex(cp)})
    print("n_chars_ok_first200", n_chars_ok, "name_off_hits", dict(name_off_hits), "eth_in_first200", eth)

    Path("research/t183_char_layout.json").write_text(json.dumps({
        "cm":hex(cm),"arr":arr,"char0":hex(cp0),"char0_class":cls(cp0),
        "name_off_hits":{str(k):v for k,v in name_off_hits.items()},
        "eth_first200":eth
    }, indent=2, default=str)+"\n", encoding="utf-8")
finally:
    p.close()
