import sys, struct, json, os, collections, re
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from mem import Proc, find_pid
from gamestate import detect_session, resolve_player_country, _pdx_array, _rtti_name_from_vtable
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
p=Proc(find_pid("hoi4.exe"))
OFF=0x10
try:
    def ptr(x):
        return type(x) is int and 0x10000 < x < 0x7fffffffffff
    def q(a):
        b=p.read(a,8)
        return struct.unpack("<Q",b)[0] if b and len(b)==8 else None
    def i32(a):
        b=p.read(a,4)
        return struct.unpack("<i",b)[0] if b and len(b)==4 else None
    def u8(a):
        b=p.read(a,1)
        return b[0] if b and len(b)==1 else None
    def cls(a):
        if not ptr(a): return None
        try:
            vt=q(a)
            return _rtti_name_from_vtable(p, vt) if ptr(vt) else None
        except Exception:
            return None
    def parr(addr):
        raw=p.read(addr,16)
        if not raw or len(raw)<16: return None
        d,cap,n=struct.unpack("<QII", raw)
        return {"data":hex(d),"cap":cap,"size":n,"data_i":d}

    session=detect_session(p, pe)
    gs=int(session["signals"]["gs_ptr"],16)
    res=resolve_player_country(p, gs)
    co=int(res["country_ptr"],16) if isinstance(res["country_ptr"],str) else res["country_ptr"]
    player=res["player_index"]

    # hour tick / speed if known slots from prior
    # G_IDLER etc already in session
    tick = i32(gs+0x1c) or i32(gs+0x18)  # guess; also try campaign if any
    # common prior: hour tick mentioned; search previous session files
    out={"pid":p.pid,"read_only":True,"player_index":player,"country":hex(co),"gs":hex(gs),
         "in_game":True,"tag":res.get("tag")}

    # --- units ---
    ar=_pdx_array(p, co+0x290)
    units=[]
    leader_on_units=[]
    formation_ptr_hist=collections.Counter()
    interesting_cls=("CArmy","CArmyGroup","CTheatre","CTheaterGroup","CArmyLeader","COrderGroup","CCommandGroup","CFront","CArmyTheatre","CUnitGroup","COrdersGroup")
    for slot in range(ar["size"]):
        ap=q(ar["data"]+slot*8)
        if not ptr(ap): continue
        uid=struct.unpack("<I", p.read(ap+0x1c,4))[0]
        lid=i32(ap+0x564)
        leader_flag=u8(ap+0x630)
        rec={"unit_id":uid,"leader_id":lid,"leader_flag_630":leader_flag,"ptrs":[]}
        # scan qwords 0x20..0x700 for interesting classes (skip vtable)
        blob=p.read(ap, 0x800) or b""
        for off in range(0x20, min(len(blob)-7, 0x7f8), 8):
            pv=struct.unpack_from("<Q", blob, off)[0]
            if not ptr(pv): continue
            c=cls(pv)
            if c and any(s in c for s in interesting_cls):
                rec["ptrs"].append({"off":hex(off),"ptr":hex(pv),"class":c})
                formation_ptr_hist[f"{hex(off)}:{c}"]=formation_ptr_hist.get(f"{hex(off)}:{c}",0)+1
        units.append(rec)
        if lid is not None and lid>=0:
            leader_on_units.append({"unit_id":uid,"leader_id":lid})

    # --- ETH theatres / groups (player only) ---
    th=_pdx_array(p, co+0x168)
    theatres=[]
    group_counts={"orders_group":0,"field_marshal_group":0,"theater_group":0}
    if th:
        for j in range(th["size"]):
            tp=q(th["data"]+j*8)
            trec={"ptr":hex(tp or 0),"class":cls(tp) if tp else None,"groups":{}}
            if not tp: 
                theatres.append(trec); continue
            for label,off in (("orders_group",0x80),("field_marshal_group",0x98),("theater_group",0xc8)):
                gr=_pdx_array(p, tp+off)
                trec["groups"][label]=gr
                if gr:
                    group_counts[label]+=gr["size"]
                    # sample first 3 group objects: class + some ids + child arrays
                    samples=[]
                    for k in range(min(gr["size"], 3)):
                        gp=q(gr["data"]+k*8)
                        g={"ptr":hex(gp or 0),"class":cls(gp) if gp else None}
                        if gp and ptr(gp):
                            # scan first 0x200 for arrays and ids
                            raw=p.read(gp, 0x200) or b""
                            g["i32_8"]=struct.unpack_from("<i", raw, 8)[0] if len(raw)>=12 else None
                            g["i32_1c"]=struct.unpack_from("<i", raw, 0x1c)[0] if len(raw)>=0x20 else None
                            # pdx arrays in first 0x180
                            arrs=[]
                            for off2 in range(0x20, 0x180, 8):
                                if off2+16>len(raw): break
                                d,cap,n=struct.unpack_from("<QII", raw, off2)
                                if ptr(d) and 0<=n<=256 and n<=cap<=1024:
                                    first=cls(q(d)) if n else None
                                    arrs.append({"off":hex(off2),"size":n,"cap":cap,"first_class":first})
                            g["arrays"]=arrs
                        samples.append(g)
                    trec["groups"][label]["samples"]=samples
            theatres.append(trec)

    # --- leaders: find country leader array ---
    # t163 used character/leader lists; try common country offsets and also follow unit leader_id
    # We need the CArmyLeader* for each leader_id. Search country for CArmyLeader arrays.
    leader_arrays=[]
    co_blob=p.read(co, 0x900) or b""
    for off in range(0x20, min(len(co_blob)-15, 0x8f0), 8):
        d,cap,n=struct.unpack_from("<QII", co_blob, off)
        if not (ptr(d) and 0<n<=256 and n<=cap<=1024): continue
        c0=cls(q(d))
        if c0 and "Leader" in c0:
            leader_arrays.append({"off":hex(off),"data":hex(d),"cap":cap,"size":n,"first_class":c0})

    leaders=[]
    # prefer arrays classified CArmyLeader
    chosen=None
    for a in leader_arrays:
        if a["first_class"] and "CArmyLeader" in a["first_class"]:
            chosen=a; break
    if not chosen and leader_arrays:
        chosen=leader_arrays[0]

    def scan_leader(lp):
        raw=p.read(lp, 0x1100) or b""
        hid=struct.unpack_from("<I", raw, 0x8)[0] if len(raw)>=0xc else None
        lid=struct.unpack_from("<i", raw, 0x1c)[0] if len(raw)>=0x20 else None
        # name often at +0x20 pdx string? t163 used name20
        deployed=raw[0x1068] if len(raw)>0x1068 else None
        deploy_hq=raw[0x1058] if len(raw)>0x1058 else None
        captured=raw[0x1059] if len(raw)>0x1059 else None
        rec={"ptr":hex(lp),"class":cls(lp),"handle_id":hid,"maybe_id":lid,
             "deployed_1068":deployed,"deploy_army_hq_1058":deploy_hq,"captured_1059":captured,
             "ptrs":[]}
        for off in range(0x20, min(len(raw)-7, 0x10f0), 8):
            pv=struct.unpack_from("<Q", raw, off)[0]
            if not ptr(pv): continue
            c=cls(pv)
            if c and any(s in c for s in interesting_cls + ("CCharacter","CCountry")):
                rec["ptrs"].append({"off":hex(off),"ptr":hex(pv),"class":c})
        return rec

    if chosen:
        data=int(chosen["data"],16)
        for k in range(chosen["size"]):
            lp=q(data+k*8)
            if ptr(lp):
                leaders.append(scan_leader(lp))

    # also resolve leaders referenced by units if not in list
    unit_leader_ptrs=[]
    # leader_id is handle id? t163 handle type 4713 id 312. observation uses +0x564 as leader_id and it was verified.
    # Match maybe_id or handle_id
    ids_from_units=set(x["leader_id"] for x in leader_on_units)
    ids_from_leaders=set()
    for L in leaders:
        for cand in (L.get("handle_id"), L.get("maybe_id")):
            if cand is not None:
                ids_from_leaders.add(cand)

    out.update({
        "unit_count": len(units),
        "units_with_leader": leader_on_units,
        "units_leader_flag_hist": dict(collections.Counter(u["leader_flag_630"] for u in units)),
        "units_leader_id_hist": dict(collections.Counter((">=0" if (u["leader_id"] or 0)>=0 else str(u["leader_id"])) for u in units)),
        "unit_formation_ptr_hist": dict(formation_ptr_hist),
        "theatre_array": th,
        "eth_theatres": theatres,
        "group_counts": group_counts,
        "country_leader_arrays": leader_arrays,
        "chosen_leader_array": chosen,
        "leaders": leaders,
        "leader_ids_from_units": sorted(ids_from_units),
        "leader_ids_from_leader_objects": sorted(x for x in ids_from_leaders if x is not None),
        "gs_combats": _pdx_array(p, gs+0x268),
    })
    # compact unit ptrs for file (all units, player only)
    out["units"]=[{k:u[k] for k in u} for u in units]
    Path("research/t183_live_formation_leaders.json").write_text(json.dumps(out, indent=2, default=str, ensure_ascii=False)+"\n", encoding="utf-8")
    summary={
        "pid":p.pid,
        "units":len(units),
        "with_leader":len(leader_on_units),
        "leader_ids":leader_on_units,
        "flag_hist":out["units_leader_flag_hist"],
        "lid_hist":out["units_leader_id_hist"],
        "formation_ptrs":out["unit_formation_ptr_hist"],
        "theatres":len(theatres),
        "group_counts":group_counts,
        "leader_arrays":leader_arrays,
        "n_leaders":len(leaders),
        "deployed_hist":dict(collections.Counter(L.get("deployed_1068") for L in leaders)),
        "leader_ptr_classes":dict(collections.Counter(f"{pt['off']}:{pt['class']}" for L in leaders for pt in L.get("ptrs",[]))),
        "gs_combats":out["gs_combats"],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
finally:
    p.close()
