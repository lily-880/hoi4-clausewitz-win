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
# writer rbx = CArmy+0x10 (secondary interface)
OFF=0x10
try:
    def ptr(x): return type(x) is int and 0x10000<x<0x7fffffffffff
    def q(a):
        b=p.read(a,8)
        return struct.unpack("<Q",b)[0] if b and len(b)==8 else None
    def i32(a):
        b=p.read(a,4)
        return struct.unpack("<i",b)[0] if b and len(b)==4 else None
    def i64(a):
        b=p.read(a,8)
        return struct.unpack("<q",b)[0] if b and len(b)==8 else None
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
    def parr(ap, woff):
        d,cap,n=struct.unpack("<QII", p.read(ap+OFF+woff,16))
        return {"writer_off":hex(woff),"ca_off":hex(OFF+woff),"data":hex(d),"cap":cap,"size":n}

    session=detect_session(p, pe)
    gs=int(session["signals"]["gs_ptr"],16)
    res=resolve_player_country(p, gs)
    co=int(res["country_ptr"],16) if isinstance(res["country_ptr"],str) else res["country_ptr"]
    ar=_pdx_array(p, co+0x290)
    rows=[]
    for slot in range(ar["size"]):
        ap=q(ar["data"]+slot*8)
        w=ap+OFF
        uid=struct.unpack("<I", p.read(ap+0x1c,4))[0]
        loc=q(w+0x1e0)
        rec={
            "unit_id":uid,
            "location": {"ptr":hex(loc or 0),"class":cls(loc) if loc else None,"id": i32(loc+0xa4) if loc and ptr(loc) else None},
            "prev": {"ptr":hex(q(w+0x1e8) or 0),"class":cls(q(w+0x1e8)) if q(w+0x1e8) else None},
            "support_attack": {"ptr":hex(q(w+0x1d8) or 0),"class":cls(q(w+0x1d8)) if q(w+0x1d8) else None},
            "path": parr(ap, 0x1f0),
            "full_path": parr(ap, 0x210),
            "commandlist": parr(ap, 0x2b0),
            "last_combat_gate_1b8": i32(w+0x1b8),
            "movement_progress_raw": i64(w+0x230),
            "move_priority": i32(w+0x238),
            "retreat": u8(w+0x23c),
            "withdraw": u8(w+0x23d),
            "strategic_redeployment": u8(w+0x29f),
            "oos_days": i32(w+0x488),
            "execute_order": i32(w+0x48c),
            "was_paradropped": i32(w+0x498),
            "uc_pause": i32(w+0x49c),
            "max_supply": (i64(w+0x5f0) or 0)/100000,
            "supply_gain": (i64(w+0x5f8) or 0)/100000,
            "supply_ratio": (i64(w+0x600) or 0)/100000,
            "raw_5f0": i64(w+0x5f0),
            "raw_5f8": i64(w+0x5f8),
            "raw_600": i64(w+0x600),
        }
        rows.append(rec)
    def uniq(key):
        vals=[]
        for r in rows:
            v=r[key]
            vals.append(json.dumps(v, sort_keys=True) if isinstance(v, dict) else v)
        return {str(a):c for a,c in collections.Counter(vals).items()}
    keys=["path","full_path","commandlist","last_combat_gate_1b8","movement_progress_raw","move_priority","retreat","withdraw","strategic_redeployment","oos_days","execute_order","was_paradropped","uc_pause","max_supply","supply_gain","supply_ratio","location","support_attack","prev"]
    summary={k:uniq(k) for k in keys}
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    # sample first location vs known province
    print("sample0", json.dumps(rows[0], default=str))
    Path("research/t182_carmy_order_supply_live.json").write_text(json.dumps({
        "pid": p.pid, "read_only": True, "writer_base": "CArmy+0x10",
        "combats_gs_268": _pdx_array(p, gs+0x268),
        "summary": summary, "units": rows
    }, indent=2, default=str)+"\n", encoding="utf-8")
finally:
    p.close()
