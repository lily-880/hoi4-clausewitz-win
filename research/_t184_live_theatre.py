import sys, struct, json, os
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from mem import Proc, find_pid
from gamestate import detect_session, resolve_player_country, _pdx_array, _rtti_name_from_vtable
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
import re
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"

p=Proc(find_pid("hoi4.exe"))
pe=PE(p.image_path)
cs=Cs(CS_ARCH_X86, CS_MODE_64)
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={item["token"]:item["name"] for item in mp}
try:
    def isptr(x):
        return type(x) is int and 0x10000 < x < 0x7fffffffffff
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
    th=_pdx_array(p, co+0x168)
    theatres=[]
    for j in range(th["size"] if th else 0):
        tp=p.ptr(th["data"]+j*8)
        rec={
            "ptr":hex(tp or 0),"class":cls(tp),
            "handle_type": p.u32(tp+8) if tp else None,
            "id": p.i32(tp+0xc) if tp else None,
            "name": p.msvc_string(tp+0x28) or p.msvc_string(tp+0x30),
            "area": _pdx_array(p, tp+0x18),
            "front": _pdx_array(p, tp+0x50),
            "unit": _pdx_array(p, tp+0x68),
            "orders_group": _pdx_array(p, tp+0x80),
            "field_marshal_group": _pdx_array(p, tp+0x98),
            "theater_group": _pdx_array(p, tp+0xc8),
            "units": [],
        }
        ua=rec["unit"]
        if ua and 0<ua["size"]<=256:
            for k in range(ua["size"]):
                up=p.ptr(ua["data"]+k*8)
                rec["units"].append({
                    "ptr":hex(up or 0),"class":cls(up),
                    "handle_type": p.u32(up+0x18) if up and isptr(up) else None,
                    "unit_id": p.u32(up+0x1c) if up and isptr(up) else None,
                })
        # area province ids via [entry+0x28]+0xa4
        rec["area_province_ids"]=[]
        aa=rec["area"]
        if aa and 0<aa["size"]<=64:
            for k in range(min(aa["size"], 16)):
                ep=p.ptr(aa["data"]+k*8)
                if not ep: continue
                pp=p.ptr(ep+0x28)
                pid=p.i32(pp+0xa4) if pp and isptr(pp) else None
                rec["area_province_ids"].append({"entry":hex(ep),"entry_class":cls(ep),"prov":hex(pp or 0),"id":pid})
        theatres.append(rec)

    combats=_pdx_array(p, gs+0x268)
    out={"pid":p.pid,"read_only":True,"player":res.get("player_index"),"tag":res.get("tag"),
         "theatre_array":th,"theatres":theatres,"gs_combats":combats}
    Path("research/t184_live_theatre.json").write_text(json.dumps(out, indent=2, default=str, ensure_ascii=False)+"\n", encoding="utf-8")
    slim=[{k:t[k] for k in t if k!="area_province_ids" or t[k]} for t in theatres]
    print(json.dumps({"n":len(theatres),"combats":combats,"theatres":[{
        "class":t["class"],"id":t["id"],"type":t["handle_type"],"name":t["name"],
        "area_size": (t["area"] or {}).get("size"),
        "front_size": (t["front"] or {}).get("size"),
        "unit_size": (t["unit"] or {}).get("size"),
        "orders": (t["orders_group"] or {}).get("size"),
        "fm": (t["field_marshal_group"] or {}).get("size"),
        "tg": (t["theater_group"] or {}).get("size"),
        "unit_ids":[u["unit_id"] for u in t["units"]],
        "unit_classes":list({u["class"] for u in t["units"]}),
        "n_area_ids":len(t.get("area_province_ids") or []),
        "area_sample": (t.get("area_province_ids") or [])[:3],
    } for t in theatres]}, indent=2, default=str, ensure_ascii=False))
finally:
    p.close()
