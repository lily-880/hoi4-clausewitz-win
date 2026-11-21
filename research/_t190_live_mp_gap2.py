import sys, json, os, struct
from pathlib import Path
sys.path.insert(0, "calling")
from pe import PE
from mem import Proc, find_pid
from gamestate import detect_session, resolve_player_country, _pdx_array
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

def sum_table(tbl):
    # CC6570: data at tbl+8, size at tbl+0x14, stride 8, persons at entry+4
    data=u64(tbl+8)
    n=i32(tbl+0x14)
    if not data or n is None or n<0 or n>32:
        return {"error": True, "n": n, "data": hex(data or 0)}
    entries=[]; total=0
    for i in range(n):
        ci=i32(data+i*8)
        amt=i32(data+i*8+4)
        entries.append({"country":ci,"persons":amt})
        if amt is not None:
            total += amt
    return {"n":n,"sum":total,"entries":entries}

try:
    session=detect_session(p, pe)
    gs=int(session["signals"]["gs_ptr"],16)
    res=resolve_player_country(p, gs)
    eth=int(res["country_ptr"],16)
    th=_pdx_array(p, eth+0x168)
    tp=u64(int(th["data"]))
    ua=_pdx_array(p, tp+0x68)
    n=int(ua["size"])
    data=int(ua["data"])
    units=[]
    for i in range(n):
        ca=u64(data+i*8)
        mp=ca+0x3d0
        cur=sum_table(mp+8)
        need=sum_table(mp+0x28)
        gap=max((need.get("sum") or 0)-(cur.get("sum") or 0), 0) if "sum" in cur and "sum" in need else None
        units.append({"unit_id":i32(ca+0x1c),"backlink_ok":u64(mp+0x48)==ca,"current":cur,"need":need,"gap":gap})
    rec={
        "pid":p.pid,"read_only":True,"layout":"CC6570 data at table+8 size at table+0x14",
        "n_units":len(units),
        "backlink_ok":all(u["backlink_ok"] for u in units),
        "current_total":sum(u["current"].get("sum") or 0 for u in units),
        "need_total":sum(u["need"].get("sum") or 0 for u in units),
        "gap_total":sum(u["gap"] or 0 for u in units),
        "units_with_gap":[u["unit_id"] for u in units if (u["gap"] or 0)>0],
        "sample":units[:3],
    }
    Path("research/t190_live_manpower_gap.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(json.dumps({k:rec[k] for k in rec if k!="sample"}, indent=2))
    print("sample", json.dumps(rec["sample"], indent=2, ensure_ascii=False))
finally:
    p.close()
