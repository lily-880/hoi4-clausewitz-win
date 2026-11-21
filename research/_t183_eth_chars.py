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
    print("player", player, "chars", arr["size"])

    # role array of char0
    cp0=p.ptr(arr["data"])
    roles=_pdx_array(p, cp0+0x80)
    print("roles80", roles)
    if roles:
        for k in range(min(roles["size"], 8)):
            rp=p.ptr(roles["data"]+8*k)
            print(" role", k, hex(rp or 0), cls(rp), "raw8", (p.try_read(roles["data"]+8*k,8) or b"").hex())

    keys=("ETH","Selassie","Haile","Abebe","Nasibu","Mulugeta","Desta","Ayalew","塞拉西","海尔","阿拉盖")
    eth=[]
    owner_hist=collections.Counter()
    owner44=0
    army_leaders_player=[]
    foreign_army_leader_roles=0

    # guess country index offsets by seeing if any i32 == 44 frequently
    country_off_counts=collections.Counter()

    for j in range(arr["size"]):
        cp=p.ptr(arr["data"]+j*8)
        if not cp: continue
        name=p.msvc_string(cp+0x28) or ""
        key=p.msvc_string(cp+0x38) or p.msvc_string(cp+0x20) or ""
        # country-like i32s
        for off in (0x8,0xc,0x18,0x1c,0x40,0x44,0x70,0x74,0x78,0x7c,0x98,0x9c,0xa0,0xa4):
            try:
                v=p.i32(cp+off)
            except Exception:
                continue
            if v==player:
                country_off_counts[off]+=1
        is_eth = any(k.lower() in (name+" "+key).lower() for k in ("eth_","selassie","haile","abebe","nasibu","mulugeta","desta","ayalew","abba","kassa","kebbede","demissie","zelleka","sileshi")) or name.startswith("ETH") or key.startswith("ETH") or "塞拉西" in name
        roles=_pdx_array(p, cp+0x80)
        army=None
        if roles and 0<roles["size"]<=16:
            for k in range(roles["size"]):
                # might be pointer array
                rp=p.ptr(roles["data"]+8*k)
                c=cls(rp)
                if c and "Leader" in c:
                    if "CArmyLeader" in c:
                        army=rp
        a8=p.ptr(cp+0xa8)
        if cls(a8) and "CArmyLeader" in (cls(a8) or ""):
            army=a8
        if is_eth:
            eth.append({"idx":j,"ptr":hex(cp),"name":name,"key":key,"army":hex(army) if army else None,"army_class":cls(army) if army else None})
        if army:
            # decide player-owned later
            pass

    print("country_off_counts", dict(country_off_counts))
    print("eth", len(eth))
    print(json.dumps(eth, ensure_ascii=False, indent=2)[:4000])
    Path("research/t183_eth_characters.json").write_text(json.dumps({"player":player,"country_off_counts":{str(k):v for k,v in country_off_counts.items()},"eth":eth}, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
finally:
    p.close()
