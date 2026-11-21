import sys, struct, json, os, collections
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from mem import Proc, find_pid
from gamestate import detect_session, resolve_player_country, _pdx_array, _rtti_name_from_vtable
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)

def clip(start, nins=80):
    raw=pe.read_rva(start, 0x300) or b""
    out=[]
    for i in cs.disasm(raw, start):
        out.append(f"0x{i.address:x}  {i.mnemonic} {i.op_str}")
        if len(out)>=nins: break
    return out

print("===== path serializer 0x1d2bf0 =====")
print("\n".join(clip(0x1d2bf0, 60)))
print("===== land_combat_id 0x2091bc =====")
print("\n".join(clip(0x209160, 40)))

p=Proc(find_pid("hoi4.exe"))
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

    session=detect_session(p, pe)
    gs=int(session["signals"]["gs_ptr"],16)
    res=resolve_player_country(p, gs)
    co=int(res["country_ptr"],16) if isinstance(res["country_ptr"],str) else res["country_ptr"]
    ar=_pdx_array(p, co+0x290)
    comb=_pdx_array(p, gs+0x268)
    rows=[]
    for slot in range(ar["size"]):
        ap=q(ar["data"]+slot*8)
        uid=struct.unpack("<I", p.read(ap+0x1c,4))[0]
        path_arr=struct.unpack("<QII", p.read(ap+0x1f8, 16)) if False else None
        # try path as pdx at +0x1f8 and +0x200, full_path at +0x210
        def parr(off):
            d,cap,n=struct.unpack("<QII", p.read(ap+off,16))
            return {"off":hex(off),"data":hex(d),"cap":cap,"size":n}
        rec={
            "unit_id":uid,
            "ptr":hex(ap),
            "location_1e0":hex(q(ap+0x1e0) or 0),
            "location_class":cls(q(ap+0x1e0)) if q(ap+0x1e0) else None,
            "loc_id": i32(q(ap+0x1e0)+0xa4) if q(ap+0x1e0) and ptr(q(ap+0x1e0)) else None,
            "prev_1e8":hex(q(ap+0x1e8) or 0), "prev_class":cls(q(ap+0x1e8)) if q(ap+0x1e8) else None,
            "support_attack_1d8":hex(q(ap+0x1d8) or 0),
            "ptr_1f0":hex(q(ap+0x1f0) or 0), "class_1f0":cls(q(ap+0x1f0)) if q(ap+0x1f0) else None,
            "arr_1f8":parr(0x1f8), "arr_200":parr(0x200),
            "full_path_210":parr(0x210), "full_path_size_21c":i32(ap+0x21c),
            "commandlist_2b0":parr(0x2b0), "commandlist_size_2bc":i32(ap+0x2bc),
            "last_combat_gate_1b8":i32(ap+0x1b8),
            "movement_progress_230":i64(ap+0x230),
            "move_priority_238":i32(ap+0x238),
            "retreat_23c":u8(ap+0x23c), "withdraw_23d":u8(ap+0x23d),
            "sr_29f":u8(ap+0x29f),
            "oos_days_488":i32(ap+0x488),
            "execute_order_48c":i32(ap+0x48c),
            "was_paradropped_498":i32(ap+0x498),
            "uc_pause_49c":i32(ap+0x49c),
            "max_supply_5f0": (i64(ap+0x5f0) or 0)/100000,
            "supply_gain_5f8": (i64(ap+0x5f8) or 0)/100000,
            "supply_ratio_600": (i64(ap+0x600) or 0)/100000,
            "qword_610": (i64(ap+0x610) or 0)/100000,
            "raw_5f0":i64(ap+0x5f0), "raw_5f8":i64(ap+0x5f8), "raw_600":i64(ap+0x600), "raw_610":i64(ap+0x610),
        }
        rows.append(rec)
    # summaries
    def uniq(key):
        return collections.Counter(json.dumps(r[key], sort_keys=True) if not isinstance(r[key], (int,float,str,type(None))) else r[key] for r in rows)
    keys=["arr_200","arr_1f8","full_path_210","commandlist_size_2bc","last_combat_gate_1b8","movement_progress_230","move_priority_238","retreat_23c","withdraw_23d","sr_29f","oos_days_488","execute_order_48c","was_paradropped_498","uc_pause_49c","max_supply_5f0","supply_gain_5f8","supply_ratio_600","qword_610","support_attack_1d8","class_1f0","location_class"]
    summary={k:{str(a):c for a,c in uniq(k).items()} for k in keys}
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    out={"pid":p.pid,"read_only":True,"combats_gs_268":comb,"units":rows,"summary":summary}
    Path("research/t182_carmy_order_supply_live.json").write_text(json.dumps(out, indent=2, default=str)+"\n", encoding="utf-8")
    print("wrote live", len(rows), "units")
finally:
    p.close()
