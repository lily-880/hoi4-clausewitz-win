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

def u64(a):
    b=p.try_read(a,8)
    return struct.unpack("<Q", b)[0] if b and len(b)==8 else None
def i32(a):
    b=p.try_read(a,4)
    return struct.unpack("<i", b)[0] if b and len(b)==4 else None
def u16(a):
    b=p.try_read(a,2)
    return struct.unpack("<H", b)[0] if b and len(b)==2 else None
def i16(a):
    b=p.try_read(a,2)
    return struct.unpack("<h", b)[0] if b and len(b)==2 else None
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
        return {"data": a.get("data"), "size": a.get("size"), "capacity": a.get("capacity")}
    except Exception as e:
        return {"error": str(e)}

def overlay_len(bp, off):
    # used as r.array(bp+0x10) / bp+0x28 in input_loaded_fields — CPdxArray
    a=parr(bp, off)
    if a.get("error"):
        return None
    return a.get("size")

def scan_status(st_ptr, origin):
    out={"origin":origin,"ptr":hex(st_ptr) if st_ptr else None,"class":cls(st_ptr) if st_ptr else None,
         "buildings":0,"damaged":[],"overlays":[],"ok_undamaged":0}
    if not st_ptr or out["class"] not in (".?AVCBuildingStatus@@",):
        return out
    buildings=parr(st_ptr, 0x38)
    n=buildings.get("size") or 0
    data=buildings.get("data")
    if not data or n<=0:
        return out
    n=min(int(n), 128)
    for i in range(n):
        bp=u64(int(data)+i*8)
        if not bp: continue
        name=cls(bp)
        if name and "CBuilding" not in name:
            continue
        out["buildings"] += 1
        level=i16(bp+0x40)
        healthy=i16(bp+0x42)
        o1=overlay_len(bp, 0x10)
        o2=overlay_len(bp, 0x28)
        rec={"bp":hex(bp),"level":level,"healthy":healthy,"overlay_10":o1,"overlay_28":o2,"origin":origin}
        if level is None or healthy is None:
            continue
        if healthy<level:
            if len(out["damaged"])<8:
                out["damaged"].append(rec)
            else:
                out.setdefault("damaged_extra",0)
                out["damaged_extra"]=out["damaged_extra"]+1
        if (o1 or 0)>0 or (o2 or 0)>0:
            if len(out["overlays"])<8:
                out["overlays"].append(rec)
            else:
                out.setdefault("overlay_extra",0)
                out["overlay_extra"]=out["overlay_extra"]+1
        if healthy==level and not o1 and not o2:
            out["ok_undamaged"] += 1
    return out

try:
    session=detect_session(p, pe)
    gs=int(session["signals"]["gs_ptr"],16)
    res=resolve_player_country(p, gs)
    countries=_pdx_array(p, gs+0x310)
    cdata=int(countries["data"])
    summary={
        "pid": p.pid,
        "read_only": True,
        "states_scanned": 0,
        "state_status_ok": 0,
        "state_buildings": 0,
        "state_damaged": 0,
        "state_overlays": 0,
        "state_undamaged": 0,
        "provinces_from_states": 0,
        "prov_status_ok": 0,
        "prov_buildings": 0,
        "prov_damaged": 0,
        "prov_overlays": 0,
        "prov_undamaged": 0,
        "damaged_samples": [],
        "overlay_samples": [],
        "eth_state_infra": [],
        "state_province_offset": None,
    }
    # discover CState province array from one ETH state
    eth=int(res["country_ptr"],16)
    states=parr(eth, 0x460)
    first_state=None
    if states.get("size") and states.get("data"):
        first_state=u64(int(states["data"]))
    # probe likely pdx array offsets on CState for CProvince*
    discovered=None
    if first_state and cls(first_state)==".?AVCState@@":
        probes=[]
        for off in range(0x0, 0x200, 8):
            a=parr(first_state, off)
            sz=a.get("size") or 0
            dat=a.get("data")
            if 1<=sz<=200 and dat:
                ep=u64(int(dat))
                cn=cls(ep)
                if cn and "CProvince" in cn:
                    probes.append({"off":hex(off),"size":sz,"first":cn, "first_id": i32(ep+0xa4)})
        summary["province_array_probes"]=probes
        if probes:
            discovered=int(probes[0]["off"],16)
            summary["state_province_offset"]=hex(discovered)

    for ci in range(int(countries["size"])):
        cptr=u64(cdata+ci*8)
        if not cptr: continue
        if cls(cptr) not in (".?AVCCountry@@",):
            continue
        starr=parr(cptr, 0x460)
        nst=starr.get("size") or 0
        sdata=starr.get("data")
        if not sdata or nst<=0:
            continue
        nst=min(int(nst), 400)
        for si in range(nst):
            sp=u64(int(sdata)+si*8)
            if not sp: continue
            if cls(sp)!=".?AVCState@@":
                continue
            summary["states_scanned"] += 1
            stid=i32(sp+0x58)
            rec=scan_status(sp+0x120, f"state:{tag_for_index(ci)}:{stid}")
            if rec["class"]==".?AVCBuildingStatus@@":
                summary["state_status_ok"] += 1
            summary["state_buildings"] += rec["buildings"]
            summary["state_damaged"] += len(rec["damaged"]) + rec.get("damaged_extra",0)
            summary["state_overlays"] += len(rec["overlays"]) + rec.get("overlay_extra",0)
            summary["state_undamaged"] += rec["ok_undamaged"]
            if ci==44 and rec["buildings"]:
                summary["eth_state_infra"].append({"state_id":stid, "buildings":rec["buildings"], "undamaged":rec["ok_undamaged"], "damaged":rec["damaged"], "overlays":rec["overlays"]})
            for s in rec["damaged"]:
                if len(summary["damaged_samples"])<12:
                    s=dict(s); s["tag"]=tag_for_index(ci); s["state_id"]=stid
                    summary["damaged_samples"].append(s)
            for s in rec["overlays"]:
                if len(summary["overlay_samples"])<12:
                    s=dict(s); s["tag"]=tag_for_index(ci); s["state_id"]=stid
                    summary["overlay_samples"].append(s)
            if discovered is not None:
                par=parr(sp, discovered)
                psz=par.get("size") or 0
                pdata=par.get("data")
                if pdata and psz>0:
                    psz=min(int(psz), 400)
                    summary["provinces_from_states"] += psz
                    for pi in range(psz):
                        pp=u64(int(pdata)+pi*8)
                        if not pp: continue
                        # CProvince+0x190 is CBuildingStatus object (embedded?), t169 uses province+0x190 as status root
                        prec=scan_status(pp+0x190, f"prov:{tag_for_index(ci)}:{i32(pp+0xa4)}")
                        if prec["class"]==".?AVCBuildingStatus@@":
                            summary["prov_status_ok"] += 1
                        summary["prov_buildings"] += prec["buildings"]
                        summary["prov_damaged"] += len(prec["damaged"]) + prec.get("damaged_extra",0)
                        summary["prov_overlays"] += len(prec["overlays"]) + prec.get("overlay_extra",0)
                        summary["prov_undamaged"] += prec["ok_undamaged"]
                        for s in prec["damaged"]:
                            if len(summary["damaged_samples"])<12:
                                s=dict(s); s["tag"]=tag_for_index(ci); s["province_id"]=i32(pp+0xa4)
                                summary["damaged_samples"].append(s)
                        for s in prec["overlays"]:
                            if len(summary["overlay_samples"])<12:
                                s=dict(s); s["tag"]=tag_for_index(ci); s["province_id"]=i32(pp+0xa4)
                                summary["overlay_samples"].append(s)

    Path("research/t189_live_buildings.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str)+"\n", encoding="utf-8")
    # compact print
    keys=["states_scanned","state_status_ok","state_buildings","state_damaged","state_overlays","state_undamaged",
          "state_province_offset","provinces_from_states","prov_status_ok","prov_buildings","prov_damaged","prov_overlays","prov_undamaged",
          "damaged_samples","overlay_samples","eth_state_infra","province_array_probes"]
    print(json.dumps({k:summary.get(k) for k in keys}, indent=2, ensure_ascii=False, default=str))
finally:
    p.close()
