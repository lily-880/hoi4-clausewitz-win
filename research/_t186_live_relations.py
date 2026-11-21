import sys,os,re,json,struct,collections
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from mem import Proc, find_pid
from gamestate import detect_session, resolve_player_country, _pdx_array, _rtti_name_from_vtable
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"

# hunt existing tag helpers
import gamestate as gsmod
print("gamestate attrs", [n for n in dir(gsmod) if "tag" in n.lower() or "country" in n.lower() or "date" in n.lower()][:40])

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
            return _rtti_name_from_vtable(pe, vt-p.base)
        except Exception:
            return None

    def try_u32(a):
        try:
            return p.u32(a)
        except Exception:
            return None
    def try_i32(a):
        try:
            return p.i32(a)
        except Exception:
            return None
    def try_u64(a):
        try:
            return p.u64(a)
        except Exception:
            return None
    def try_ptr(a):
        try:
            return p.ptr(a)
        except Exception:
            return None

    session=detect_session(p, pe)
    gs=int(session["signals"]["gs_ptr"],16)
    res=resolve_player_country(p, gs)
    co=int(res["country_ptr"],16)
    dip=p.ptr(co+0xf88)
    print("ETH dip", hex(dip), cls(dip), "vt", hex(p.ptr(dip)-p.base) if p.ptr(dip) else None)

    # array at +8 / +0x14
    data=p.ptr(dip+8)
    size=p.i32(dip+0x14)
    cap=p.i32(dip+0x10) if True else None
    print("active_relations data", hex(data), "size", size, "dword+0xc", p.i32(dip+0xc), "cap?", p.i32(dip+0x10))

    # Also peek nearby pdx arrays on dip
    print("dip nearby arrays:")
    for off in range(0, 0x80, 8):
        q=try_u64(dip+off)
        d=try_i32(dip+off+0xc) if off+0xc<0x90 else None
        # size often at +0xc or +0x14 depending on layout
        pass
    # standard pdx array: data+0, alloc+8, size+0xc? But writer uses +8 data and +0x14 size.
    # That's data at +8, size at +0x14 — maybe {vt, data, cap, size} or {something, data, ..., size}

    rels=[]
    class_hist=collections.Counter()
    for i in range(max(size,0)):
        rp=p.ptr(data+i*8)
        name=cls(rp) if rp else None
        class_hist[name]+=1
        rec={"i":i,"ptr":hex(rp) if rp else None,"cls":name}
        if rp and name:
            rec.update({
                "u32_10": try_u32(rp+0x10),
                "u32_14": try_u32(rp+0x14),
                "i32_10": try_i32(rp+0x10),
                "i32_14": try_i32(rp+0x14),
                "cancel_48": p.read(rp+0x48,1)[0] if p.try_read(rp+0x48,1) else None,
                "d20": try_i32(rp+0x20),
                "d24": try_i32(rp+0x24),
                "d28": try_i32(rp+0x28),
                "d2c": try_i32(rp+0x2c),
                "d38": try_i32(rp+0x38),
                "d3c": try_i32(rp+0x3c),
                "d40": try_i32(rp+0x40),
                "d44": try_i32(rp+0x44),
                "q28": hex(try_u64(rp+0x28) or 0),
                "q40": hex(try_u64(rp+0x40) or 0),
            })
            if name and "WarRelation" in name:
                rec.update({
                    "first_was_instigator": p.read(rp+0x158,1)[0] if p.try_read(rp+0x158,1) else None,
                    "hostility_def_15c": try_i32(rp+0x15c),
                    "hostility_inst_160": try_i32(rp+0x160),
                    "threat_150": try_u64(rp+0x150),
                })
        rels.append(rec)

    print("class hist", dict(class_hist))
    # print first 3, all war relations, and index 0
    print("index0", json.dumps(rels[0], default=str))
    wars=[r for r in rels if r.get("cls") and "WarRelation" in (r.get("cls") or "")]
    print("n wars", len(wars))
    print(json.dumps(wars[:10], indent=2))
    print("other classes sample:")
    seen=set()
    for r in rels[1:]:
        n=r.get("cls")
        if n and n not in seen and "War" not in (n or ""):
            seen.add(n)
            print(n, "i", r["i"], "first", r.get("i32_10"), "second", r.get("i32_14"))
            if len(seen)>=8:
                break

    Path("research/t186_live_eth_relations.json").write_text(json.dumps({
        "dip":hex(dip),"size":size,"class_hist":dict(class_hist),"wars":wars,
        "all_brief":[{"i":r["i"],"cls":r.get("cls"),"first":r.get("i32_10"),"second":r.get("i32_14"),"cancel":r.get("cancel_48")} for r in rels],
    }, indent=2)+"\n", encoding="utf-8")
finally:
    p.close()
