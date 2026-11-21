import sys, json, os, struct
from pathlib import Path
sys.path.insert(0, "calling")
from pe import PE
from mem import Proc, find_pid
from gamestate import detect_session, resolve_player_country, _pdx_array, _rtti_name_from_vtable
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
def cls(ptr):
    if not ptr or ptr<0x10000: return None
    vt=u64(ptr)
    if not vt: return None
    try:
        return _rtti_name_from_vtable(pe, vt-p.base)
    except Exception:
        return None

def sum_table(tbl):
    data=u64(tbl)
    # try size at +8 and +0xc
    for off,name in ((8,"+8"),(0xc,"+c")):
        n=i32(tbl+off)
        if data and n is not None and 1<=n<=16:
            entries=[]
            total=0
            ok=True
            for i in range(n):
                ci=i32(data+i*8)
                amt=i32(data+i*8+4)
                if ci is None or amt is None or amt<0 or amt>10_000_000 or ci<0 or ci>500:
                    ok=False
                    break
                entries.append({"country":ci,"persons":amt})
                total += amt
            if ok:
                return {"layout":name,"n":n,"sum":total,"entries":entries}
    return {"raw0":hex(u64(tbl) or 0),"i8":i32(tbl+8),"ic":i32(tbl+0xc)}

try:
    session=detect_session(p, pe)
    gs=int(session["signals"]["gs_ptr"],16)
    res=resolve_player_country(p, gs)
    eth=int(res["country_ptr"],16)
    th=_pdx_array(p, eth+0x168)
    tp=u64(int(th["data"]))
    ua=_pdx_array(p, tp+0x68)
    n=min(int(ua.get("size") or 0), 32)
    data=int(ua["data"])
    units=[]
    for i in range(n):
        ca=u64(data+i*8)
        if not ca: continue
        mp=ca+0x3d0  # embedded CArmyManpower
        back=u64(mp+0x48)
        cur=sum_table(mp+8)
        need=sum_table(mp+0x28)
        cur_sum=cur.get("sum")
        need_sum=need.get("sum")
        gap=None
        if isinstance(cur_sum,int) and isinstance(need_sum,int):
            gap=max(need_sum-cur_sum,0)
        units.append({
            "unit_id": i32(ca+0x1c),
            "mp_class": cls(mp),
            "backlink_ok": back==ca,
            "current": cur,
            "need": need,
            "gap": gap,
        })
    rec={
        "pid": p.pid,
        "read_only": True,
        "n_units": len(units),
        "embedded": True,
        "backlink_ok": all(u["backlink_ok"] for u in units),
        "current_total": sum(u["current"].get("sum") or 0 for u in units),
        "need_total": sum(u["need"].get("sum") or 0 for u in units),
        "gap_total": sum(u["gap"] or 0 for u in units),
        "units_with_gap": [u["unit_id"] for u in units if (u["gap"] or 0)>0],
        "all_classes": sorted(set(u["mp_class"] for u in units)),
        "sample": units[:4],
    }
    Path("research/t190_live_manpower_gap.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(json.dumps({k:rec[k] for k in rec if k!="sample"}, indent=2, ensure_ascii=False))
    print("sample", json.dumps(rec["sample"], indent=2, ensure_ascii=False))
finally:
    p.close()
