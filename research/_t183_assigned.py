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
    arr=_pdx_array(p, cm+0x10)

    # own units
    armies=_pdx_array(p, co+0x290)
    units=[]
    army_by_ptr={}
    lids=set()
    for slot in range(armies["size"]):
        ap=p.ptr(armies["data"]+slot*8)
        uid=p.u32(ap+0x1c)
        lid=p.i32(ap+0x564)
        units.append({"unit_id":uid,"leader_id":lid,"ptr":hex(ap)})
        army_by_ptr[ap]=uid
        if lid>=0: lids.add(lid)

    interesting=("CArmy","CArmyGroup","CTheatre","CTheaterGroup","CArmyLeader","CCharacter","CCountry","COrderGroup","CCommandGroup","CFront")
    chars=[]
    leaders=[]
    role_a8_classes=collections.Counter()
    for j in range(arr["size"]):
        cp=p.ptr(arr["data"]+j*8)
        if not cp: continue
        if p.i32(cp+0x68)!=player: continue
        name=p.msvc_string(cp+0x28)
        a8=p.ptr(cp+0xa8)
        ac=cls(a8)
        role_a8_classes[ac or "null"] += 1
        rec={"char":hex(cp),"name":name,"a8":hex(a8 or 0),"a8_class":ac}
        chars.append(rec)
        if ac and "CArmyLeader" in ac:
            raw=p.try_read(a8, 0x1100) or b""
            ty,idx=struct.unpack_from("<II", raw, 8) if len(raw)>=16 else (None,None)
            L={
                "name":name,"char":hex(cp),"ptr":hex(a8),"class":ac,
                "handle_type":ty,"handle_id":idx,
                "name20":p.msvc_string(a8+0x20),
                "deployed_1068": raw[0x1068] if len(raw)>0x1068 else None,
                "deploy_army_hq_1058": raw[0x1058] if len(raw)>0x1058 else None,
                "captured_1059": raw[0x1059] if len(raw)>0x1059 else None,
                "pending_1050_present": None,
                "dwords_eq_unit_lids":[],
                "dwords_eq_handle":[],
                "ptrs":[],
                "ptrs_to_own_units":[],
            }
            if len(raw)>0x1058:
                # pending object check: just first qword
                L["pending_1050"]=hex(struct.unpack_from("<Q", raw, 0x1050)[0])
            for off in range(0, len(raw)-3, 4):
                val=struct.unpack_from("<I", raw, off)[0]
                if val in lids:
                    L["dwords_eq_unit_lids"].append({"off":hex(off),"value":val})
                if idx is not None and val==idx and off not in (8,):
                    # skip handle itself at +8? handle id is at +0xc (second u32 of +8)
                    pass
            # handle_id is at +0xc
            # also search handle_id occurrences besides +0xc
            if idx is not None:
                for off in range(0, len(raw)-3, 4):
                    if off==0xc: continue
                    if struct.unpack_from("<I", raw, off)[0]==idx:
                        L["dwords_eq_handle"].append(hex(off))
            for off in range(0x8, min(len(raw)-7, 0x10f8), 8):
                pv=struct.unpack_from("<Q", raw, off)[0]
                if pv in army_by_ptr:
                    L["ptrs_to_own_units"].append({"off":hex(off),"unit_id":army_by_ptr[pv]})
                if isptr(pv):
                    c=cls(pv)
                    if c and any(s in c for s in interesting):
                        L["ptrs"].append({"off":hex(off),"ptr":hex(pv),"class":c})
            # does handle_id match any unit leader_id?
            L["assigned_unit_ids"]=[u["unit_id"] for u in units if u["leader_id"]==idx]
            leaders.append(L)

    print("player chars", len(chars), "a8 classes", dict(role_a8_classes), "army leaders", len(leaders))
    print("unit lids", sorted(lids))
    print("leader handle_ids", [L["handle_id"] for L in leaders])
    print("deployed", dict(collections.Counter(L["deployed_1068"] for L in leaders)))
    print("deploy_hq", dict(collections.Counter(L["deploy_army_hq_1058"] for L in leaders)))
    slim=[{k:L[k] for k in ("name","handle_id","deployed_1068","deploy_army_hq_1058","assigned_unit_ids","ptrs_to_own_units","ptrs","dwords_eq_unit_lids","dwords_eq_handle")} for L in leaders]
    print(json.dumps(slim, ensure_ascii=False, indent=2))
    Path("research/t183_live_assigned_to.json").write_text(json.dumps({
        "pid":p.pid,"player":player,"n_player_chars":len(chars),
        "a8_classes":dict(role_a8_classes),
        "units_with_leaders":[u for u in units if u["leader_id"]>=0],
        "leaders":leaders
    }, indent=2, default=str, ensure_ascii=False)+"\n", encoding="utf-8")
finally:
    p.close()
