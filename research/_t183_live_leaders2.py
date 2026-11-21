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
    def parr(addr):
        return _pdx_array(p, addr)

    session=detect_session(p, pe)
    gs=int(session["signals"]["gs_ptr"],16)
    res=resolve_player_country(p, gs)
    co=int(res["country_ptr"],16)
    print("country", cls(co), hex(co), "gs", cls(gs))

    # managers on country
    managers=[]
    cob=p.try_read(co, 0xA00) or b""
    for off in range(8, min(len(cob)-7, 0x9f8), 8):
        v=struct.unpack_from("<Q", cob, off)[0]
        c=cls(v) if isptr(v) else None
        if c:
            managers.append({"off":hex(off),"ptr":hex(v),"class":c})
    print("country ptr classes", json.dumps(managers, ensure_ascii=False)[:3000])

    ar=parr(co+0x290)
    units=[]
    officers=[]
    for slot in range(ar["size"]):
        ap=p.ptr(ar["data"]+slot*8)
        uid=p.u32(ap+0x1c)
        lid=p.i32(ap+0x564)
        op=p.ptr(ap+0x568)
        rec={"unit_id":uid,"leader_id":lid,"leader_ptr":hex(op or 0),"leader_class":cls(op),"army_ptr":hex(ap)}
        units.append(rec)
        if lid>=0 or (op and isptr(op)):
            officers.append(rec)

    print("officers", json.dumps(officers, ensure_ascii=False, indent=2))

    interesting=("CArmy","CArmyGroup","CTheatre","CTheaterGroup","CArmyLeader","CCharacter","CCountry","COrderGroup","CCommandGroup","CFront")

    def scan_leader(lp, via=None):
        raw=p.try_read(lp, 0x1100) or b""
        ty,idx=struct.unpack_from("<II", raw, 8) if len(raw)>=16 else (None,None)
        rec={
            "ptr":hex(lp),"class":cls(lp),"via":via,
            "handle_type":ty,"handle_id":idx,
            "name20": p.msvc_string(lp+0x20),
            "deployed_1068": raw[0x1068] if len(raw)>0x1068 else None,
            "deploy_army_hq_1058": raw[0x1058] if len(raw)>0x1058 else None,
            "captured_1059": raw[0x1059] if len(raw)>0x1059 else None,
            "attack": struct.unpack_from("<I", raw, 0xf58)[0] if len(raw)>0xf5c else None,
            "dwords_eq_leader_id": [],
            "ptrs": [],
            "ptrs_to_own_units": [],
        }
        unit_lids={u["leader_id"] for u in units if u["leader_id"]>=0}
        army_ptrs={int(u["army_ptr"],16):u["unit_id"] for u in units}
        for off in range(0, len(raw)-3, 4):
            val=struct.unpack_from("<I", raw, off)[0]
            if val in unit_lids:
                rec["dwords_eq_leader_id"].append({"off":hex(off),"value":val})
        for off in range(0x8, min(len(raw)-7, 0x10f0), 8):
            pv=struct.unpack_from("<Q", raw, off)[0]
            if pv in army_ptrs:
                rec["ptrs_to_own_units"].append({"off":hex(off),"unit_id":army_ptrs[pv]})
            if not isptr(pv): continue
            c=cls(pv)
            if c and any(s in c for s in interesting):
                rec["ptrs"].append({"off":hex(off),"ptr":hex(pv),"class":c})
        return rec

    leader_scans=[scan_leader(int(o["leader_ptr"],16), {"unit_id":o["unit_id"],"leader_id":o["leader_id"]}) for o in officers if int(o["leader_ptr"],16)]
    print("assigned leader scans", json.dumps(leader_scans, indent=2, ensure_ascii=False, default=str))

    # find CCountryCharacters and all ETH leaders
    cc=next((int(m["ptr"],16) for m in managers if "CCountryCharacters" in m["class"]), None)
    print("CCountryCharacters", hex(cc) if cc else None, cls(cc) if cc else None)

    all_eth_leaders=[]
    if cc:
        # dump arrays on cc
        arrs=[]
        blob=p.try_read(cc, 0x200) or b""
        for off in range(0, len(blob)-15, 8):
            d,cap,n=struct.unpack_from("<QII", blob, off)
            if isptr(d) and 0<n<=400 and n<=cap<=2000:
                first=p.ptr(d)
                arrs.append({"off":hex(off),"size":n,"cap":cap,"first_class":cls(first)})
        print("cc arrays", arrs)
        # t163 used cc+0x70
        for off in (0x70, 0x10, 0x20, 0x30, 0x40, 0x50, 0x60, 0x80, 0x90):
            ar2=parr(cc+off)
            if not ar2 or not (0<ar2["size"]<=400): continue
            print("trying cc"+hex(off), "size", ar2["size"], "first", cls(p.ptr(ar2["data"])))
            if "Leader" in (cls(p.ptr(ar2["data"])) or "") or "Character" in (cls(p.ptr(ar2["data"])) or ""):
                for k in range(ar2["size"]):
                    lp=p.ptr(ar2["data"]+k*8)
                    c=cls(lp)
                    if c and "CArmyLeader" in c:
                        all_eth_leaders.append(scan_leader(lp, {"array":hex(off),"idx":k}))
                    elif c and "Character" in c:
                        # follow +0xa8 and roles +0x80
                        a8=p.ptr(lp+0xa8)
                        if cls(a8) and "CArmyLeader" in (cls(a8) or ""):
                            all_eth_leaders.append(scan_leader(a8, {"char":p.msvc_string(lp+0x28),"idx":k}))

    print("n_eth_leaders", len(all_eth_leaders))
    if all_eth_leaders:
        print(json.dumps({
            "n":len(all_eth_leaders),
            "deployed":dict(collections.Counter(x["deployed_1068"] for x in all_eth_leaders)),
            "names":[(x["name20"], x["handle_id"], x["deployed_1068"], x["ptrs_to_own_units"], [(pp["off"],pp["class"]) for pp in x["ptrs"]]) for x in all_eth_leaders],
        }, indent=2, ensure_ascii=False))

    out={
        "pid":p.pid,"country_class":cls(co),"managers":managers,
        "units":units,"officers":officers,
        "assigned_leader_scans":leader_scans,
        "eth_leaders":all_eth_leaders,
        "cc":hex(cc) if cc else None,
    }
    Path("research/t183_live_leaders.json").write_text(json.dumps(out, indent=2, default=str, ensure_ascii=False)+"\n", encoding="utf-8")
finally:
    p.close()
