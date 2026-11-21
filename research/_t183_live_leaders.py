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
            return _rtti_name_from_vtable(p, vt) if ptr(vt) else None
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
    player=res["player_index"]

    # country inline / managers
    managers=[]
    cob=p.read(co, 0x900) or b""
    for off in range(0, min(len(cob)-7, 0x8f8), 8):
        v=struct.unpack_from("<Q", cob, off)[0]
        if off==0: # vtable
            c=cls(co)
            managers.append({"kind":"self","off":"0x0","class":c})
            continue
        c=cls(v) if ptr(v) else None
        if c and any(s in c for s in ("Character","Leader","Theatre","Army","Command","Manager","Group")):
            managers.append({"kind":"ptr","off":hex(off),"ptr":hex(v),"class":c})
        # inline vtable?
        if ptr(v) and pe.image_base <= v < pe.image_base + getattr(pe, "image_size", 0x4000000):
            # might be inline object vtable
            pass

    # GS character manager at +0x6a8
    cm=q(gs+0x6a8)
    cm_class=cls(cm)
    chars_arr=_pdx_array(p, cm+0x10) if ptr(cm) else None

    unit_lids=set()
    ar=_pdx_array(p, co+0x290)
    unit_map=[]
    for slot in range(ar["size"]):
        ap=q(ar["data"]+slot*8)
        uid=u32(ap+0x1c)
        lid=i32(ap+0x564)
        unit_map.append({"unit_id":uid,"leader_id":lid,"army_ptr":hex(ap)})
        if lid is not None and lid>=0:
            unit_lids.add(lid)

    # CCountryCharacters: scan country for nested array of characters or find via managers
    # Also look at known offsets from t163_country_managers if file has offsets
    cc=None
    for m in managers:
        if m.get("class") and "CCountryCharacters" in m["class"]:
            cc=int(m["ptr"],16)

    leaders=[]
    eth_chars=[]
    interesting=("CArmy","CArmyGroup","CTheatre","CTheaterGroup","CArmyLeader","CCharacter","CCountry","COrderGroup","CCommandGroup")

    def scan_leader(lp, char_key=None, char_ptr=None):
        raw=p.read(lp, 0x1100) or b""
        if len(raw)<0x20: return None
        ty,idx=struct.unpack_from("<II", raw, 8)
        rec={
            "ptr":hex(lp),"class":cls(lp),"char_key":char_key,"char_ptr":char_ptr,
            "handle_type":ty,"handle_id":idx,"name20":text(lp+0x20),
            "deployed_1068": raw[0x1068] if len(raw)>0x1068 else None,
            "deploy_army_hq_1058": raw[0x1058] if len(raw)>0x1058 else None,
            "captured_1059": raw[0x1059] if len(raw)>0x1059 else None,
            "attack": struct.unpack_from("<I", raw, 0xf58)[0] if len(raw)>0xf5c else None,
            "location_1060": hex(struct.unpack_from("<Q", raw, 0x1060)[0]) if len(raw)>0x1068 else None,
            "dwords_matching_unit_lids": [],
            "ptrs":[],
        }
        # any dword in object equal to a unit leader_id?
        for off in range(0, len(raw)-3, 4):
            val=struct.unpack_from("<I", raw, off)[0]
            if val in unit_lids:
                rec["dwords_matching_unit_lids"].append({"off":hex(off),"value":val})
        for off in range(0x20, min(len(raw)-7, 0x10f0), 8):
            pv=struct.unpack_from("<Q", raw, off)[0]
            if not ptr(pv): continue
            c=cls(pv)
            if c and any(s in c for s in interesting):
                rec["ptrs"].append({"off":hex(off),"ptr":hex(pv),"class":c})
        # also check if any pointer is one of our CArmy*
        army_ptrs={int(u["army_ptr"],16):u["unit_id"] for u in unit_map}
        rec["ptrs_to_own_units"]=[]
        for off in range(0x20, min(len(raw)-7, 0x10f0), 8):
            pv=struct.unpack_from("<Q", raw, off)[0]
            if pv in army_ptrs:
                rec["ptrs_to_own_units"].append({"off":hex(off),"unit_id":army_ptrs[pv]})
        return rec

    # Iterate character manager; keep ETH army-leader roles only. Foreign roles: count structure only, no names/ids exported.
    foreign_leader_roles=0
    if chars_arr and chars_arr["size"]<=20000:
        for j in range(chars_arr["size"]):
            cp=q(chars_arr["data"]+j*8)
            if not ptr(cp): continue
            key=text(cp+0x28)
            # roles
            roles=_pdx_array(p, cp+0x80)
            army_roles=[]
            if roles and 0<roles["size"]<=16:
                for k in range(roles["size"]):
                    rp=q(roles["data"]+k*8)
                    rc=cls(rp) if rp else None
                    if rc and "CArmyLeader" in rc:
                        army_roles.append(rp)
            # character+0xa8 sometimes points at leader
            a8=q(cp+0xa8)
            if cls(a8) and "CArmyLeader" in (cls(a8) or ""):
                if a8 not in army_roles:
                    army_roles.append(a8)
            is_eth = bool(key and (key.startswith("ETH_") or "selassie" in key.lower() or "kassa" in (key or "").lower()))
            # also characters whose country is player: check a country index field
            owner=i32(cp+0x10) or i32(cp+0x18) or i32(cp+0x1c)
            # We'll classify ETH by key prefix first; also if key is missing try owner later
            if not army_roles:
                continue
            if is_eth:
                for rp in army_roles:
                    rec=scan_leader(rp, key, hex(cp))
                    if rec:
                        rec["char_owner_guess"]=owner
                        leaders.append(rec)
                eth_chars.append({"key":key,"ptr":hex(cp),"n_army_roles":len(army_roles)})
            else:
                foreign_leader_roles += len(army_roles)

    # If few ETH_ keys (dynamic names), also collect leaders whose character country matches player.
    # Scan again for non-ETH-prefixed but owned by player? We may have missed local-named generals.
    # Look at character country token / index. Try common offsets 0x18/0x1c/0x38 as country index.
    # For now print offset histogram of country-like 44 among characters with CArmyLeader if ETH count is low.

    out={
        "pid": p.pid,
        "cm": hex(cm or 0),
        "cm_class": cm_class,
        "chars_arr": chars_arr,
        "managers": managers,
        "cc": hex(cc) if cc else None,
        "eth_chars": eth_chars,
        "n_eth_leaders": len(leaders),
        "foreign_army_leader_roles_count_only": foreign_leader_roles,
        "unit_lids": sorted(unit_lids),
        "leaders": leaders,
        "handle_id_overlap_with_unit_lids": [L["handle_id"] for L in leaders if L.get("handle_id") in unit_lids],
    }
    Path("research/t183_live_leaders.json").write_text(json.dumps(out, indent=2, default=str, ensure_ascii=False)+"\n", encoding="utf-8")
    summary={
        "cm_class": cm_class,
        "chars": chars_arr["size"] if chars_arr else None,
        "managers": managers,
        "n_eth_chars": len(eth_chars),
        "n_eth_leaders": len(leaders),
        "foreign_roles": foreign_leader_roles,
        "unit_lids": sorted(unit_lids),
        "handle_ids": [L.get("handle_id") for L in leaders],
        "names": [L.get("name20") or L.get("char_key") for L in leaders],
        "deployed": dict(collections.Counter(L.get("deployed_1068") for L in leaders)),
        "deploy_hq": dict(collections.Counter(L.get("deploy_army_hq_1058") for L in leaders)),
        "overlap": out["handle_id_overlap_with_unit_lids"],
        "dword_hits": [(L.get("char_key"), L.get("dwords_matching_unit_lids")[:8], L.get("ptrs_to_own_units"), [(x["off"],x["class"]) for x in L.get("ptrs",[])]) for L in leaders],
    }
    print(json.dumps(summary, indent=2, default=str, ensure_ascii=False))
finally:
    p.close()
