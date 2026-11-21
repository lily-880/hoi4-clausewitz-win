import sys, json, os, struct
from pathlib import Path
sys.path.insert(0, "calling")
from pe import PE
from mem import Proc, find_pid
from gamestate import detect_session, resolve_player_country, _pdx_array, _rtti_name_from_vtable
from country_tags import tag_for_index
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
p=Proc(find_pid("hoi4.exe"))

def i32(a):
    b=p.try_read(a,4)
    return struct.unpack("<i", b)[0] if b and len(b)==4 else None
def u32(a):
    b=p.try_read(a,4)
    return struct.unpack("<I", b)[0] if b and len(b)==4 else None
def u64(a):
    b=p.try_read(a,8)
    return struct.unpack("<Q", b)[0] if b and len(b)==8 else None
def cls(ptr):
    if not ptr or ptr < 0x10000:
        return None
    vt=u64(ptr)
    if not vt:
        return None
    try:
        return _rtti_name_from_vtable(pe, vt-p.base)
    except Exception as e:
        return f"err:{e}"

def parr(obj, off):
    try:
        a=_pdx_array(p, obj+off)
        return {"data": a.get("data"), "size": a.get("size"), "capacity": a.get("capacity")}
    except Exception as e:
        return {"error": str(e)}

def elems(arr, nmax=64):
    out=[]
    if not arr or arr.get("error") or not arr.get("size") or not arr.get("data"):
        return out
    n=min(int(arr["size"]), nmax)
    base=int(arr["data"])
    for i in range(n):
        ptr=u64(base+i*8)
        out.append(ptr)
    return out

TYPE_HINT={1:"ORDER_MOVE", 3:"ORDER_INVASION", 4:"ORDER_PARADROP_candidate"}

try:
    session=detect_session(p, pe)
    gs=int(session["signals"]["gs_ptr"],16)
    res=resolve_player_country(p, gs)
    countries=_pdx_array(p, gs+0x310)
    eth=int(res["country_ptr"],16)
    rec={
        "pid": p.pid,
        "in_game": True,
        "gs": hex(gs),
        "player_index": res["player_index"],
        "tag": res["tag"],
        "country_ptr": hex(eth),
        "pause_flag_6c1": p.read(int(session["signals"]["idler_ptr"],16)+0x6c1,1)[0],
        "read_only": True,
        "eth_theatre": None,
        "eth_fronts": [],
        "eth_order_instances": [],
        "world_orders_groups": 0,
        "world_order_instances": 0,
        "world_instances_by_type": {},
        "countries_with_order_instances": [],
        "countries_with_orders_groups": [],
        "front_classes": {},
    }
    n_countries=int(countries["size"])
    cdata=int(countries["data"])
    # walk all countries theatres
    for ci in range(n_countries):
        cptr=u64(cdata+ci*8)
        if not cptr:
            continue
        if cls(cptr) not in (".?AVCCountry@@",) and ci not in (0,16,44) and not cptr:
            continue
        th=parr(cptr, 0x168)
        tptrs=elems(th, 32)
        country_groups=0
        country_instances=0
        inst_types=[]
        for tp in tptrs:
            if not tp:
                continue
            tname=cls(tp)
            fronts=parr(tp, 0x50)
            for fp in elems(fronts, 32):
                fn=cls(fp) or "?"
                rec["front_classes"][fn]=rec["front_classes"].get(fn,0)+1
                if ci==44:
                    rec["eth_fronts"].append({
                        "ptr": hex(fp),
                        "class": fn,
                        "dword_30": u32(fp+0x30) if fp else None,
                        "id_plus_c": u32(fp+0xc) if fp else None,
                        "type_plus_8": u32(fp+0x8) if fp else None,
                    })
            for label, off in (("orders_group",0x80),("field_marshal_group",0x98),("theater_group",0xc8)):
                arr=parr(tp, off)
                size=arr.get("size") or 0
                if size:
                    country_groups += size
                    rec["world_orders_groups"] += size
                    for gp in elems(arr, 64):
                        gname=cls(gp)
                        # order_instance on COrdersGroup +0x98 / +0xa4; CArmyGroup may inherit; CTheaterGroup uses +0x48 for child groups not instances
                        inst=parr(gp, 0x98)
                        inst_ptrs=elems(inst, 64)
                        # if this is CTheaterGroup, +0x98 might be something else; check class
                        if gname and "CTheaterGroup" in gname:
                            inst_ptrs=[]
                            child=parr(gp, 0x48)
                            rec.setdefault("theater_groups", []).append({"country":ci,"tag":tag_for_index(ci),"ptr":hex(gp),"children":child.get("size")})
                            continue
                        for ip in inst_ptrs:
                            iname=cls(ip)
                            typ=u32(ip+0x30) if ip else None
                            iid=u32(ip+0x244) if ip else None
                            path=parr(ip, 0x70) if ip else {}
                            states=parr(ip, 0xe0) if ip else {}
                            country_instances += 1
                            rec["world_order_instances"] += 1
                            rec["world_instances_by_type"][str(typ)] = rec["world_instances_by_type"].get(str(typ),0)+1
                            inst_types.append(typ)
                            item={
                                "ptr": hex(ip) if ip else None,
                                "class": iname,
                                "type": typ,
                                "type_hint": TYPE_HINT.get(typ),
                                "instance_id": iid,
                                "path_size": path.get("size"),
                                "states_size": states.get("size"),
                                "country": ci,
                                "tag": tag_for_index(ci),
                                "group": hex(gp),
                                "group_class": gname,
                            }
                            if ci==44:
                                rec["eth_order_instances"].append(item)
                            else:
                                rec.setdefault("foreign_instance_samples", []).append(item)
            if ci==44:
                rec["eth_theatre"]={
                    "ptr": hex(tp),
                    "class": tname,
                    "id": u32(tp+0xc),
                    "handle_type": u32(tp+0x8),
                    "front": fronts,
                    "unit": parr(tp, 0x68),
                    "orders_group": parr(tp, 0x80),
                    "field_marshal_group": parr(tp, 0x98),
                    "theater_group": parr(tp, 0xc8),
                }
        if country_groups:
            rec["countries_with_orders_groups"].append({"index":ci,"tag":tag_for_index(ci),"groups":country_groups,"instances":country_instances,"types":inst_types})
        if country_instances:
            rec["countries_with_order_instances"].append({"index":ci,"tag":tag_for_index(ci),"instances":country_instances,"types":inst_types})

    # cap foreign samples
    if len(rec.get("foreign_instance_samples",[]))>12:
        rec["foreign_instance_samples_truncated"]=len(rec["foreign_instance_samples"])
        rec["foreign_instance_samples"]=rec["foreign_instance_samples"][:12]

    Path("research/t188_live_plans.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False, default=str)+"\n", encoding="utf-8")
    print(json.dumps({
        "eth_fronts": rec["eth_fronts"],
        "eth_theatre_groups": {k: rec["eth_theatre"][k] for k in ("front","unit","orders_group","field_marshal_group","theater_group","id","class")} if rec["eth_theatre"] else None,
        "eth_order_instances": rec["eth_order_instances"],
        "world_orders_groups": rec["world_orders_groups"],
        "world_order_instances": rec["world_order_instances"],
        "world_instances_by_type": rec["world_instances_by_type"],
        "countries_with_orders_groups": rec["countries_with_orders_groups"][:20],
        "n_countries_with_groups": len(rec["countries_with_orders_groups"]),
        "n_countries_with_instances": len(rec["countries_with_order_instances"]),
        "front_classes": rec["front_classes"],
        "foreign_samples": rec.get("foreign_instance_samples",[])[:6],
    }, indent=2, ensure_ascii=False, default=str))
finally:
    p.close()
