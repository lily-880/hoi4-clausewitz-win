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

    # known ETH character
    eth0=int(json.loads(Path("research/t183_eth_characters.json").read_text(encoding="utf-8"))["eth"][5]["ptr"],16)
    # wait, index 5 in the filtered list was 海尔·塞拉西 - confirm
    eth_list=json.loads(Path("research/t183_eth_characters.json").read_text(encoding="utf-8"))["eth"]
    eth0=int(next(x["ptr"] for x in eth_list if x["name"]=="海尔·塞拉西"),16)
    other=p.ptr(arr["data"])  # Kirill
    print("eth0", hex(eth0), p.msvc_string(eth0+0x28), "other", p.msvc_string(other+0x28))

    raw_e=p.try_read(eth0, 0x140) or b""
    raw_o=p.try_read(other, 0x140) or b""
    diffs=[]
    for off in range(0, min(len(raw_e),len(raw_o))-3, 4):
        a=struct.unpack_from("<i", raw_e, off)[0]
        b=struct.unpack_from("<i", raw_o, off)[0]
        if a!=b:
            diffs.append((hex(off), a, b))
    print("i32 diffs vs char0 (first 20)", diffs[:20])

    # pointers equal to CCountry?
    def scan_eq(cp, target, label):
        raw=p.try_read(cp, 0x160) or b""
        hits=[]
        for off in range(0, len(raw)-7, 8):
            if struct.unpack_from("<Q", raw, off)[0]==target:
                hits.append(hex(off))
        print(label, "ptr hits to country", hits)

    scan_eq(eth0, co, "eth0")
    scan_eq(other, co, "other")

    # maybe country index packed in a handle. Search i32==44 on eth0
    print("eth0 i32==44", [hex(off) for off in range(0,len(raw_e)-3,4) if struct.unpack_from("<i", raw_e, off)[0]==player])
    print("eth0 u32 interesting", [(hex(off), struct.unpack_from("<I", raw_e, off)[0]) for off in range(0,0x80,4) if struct.unpack_from("<I", raw_e, off)[0] not in (0,1)])

    # Count how many characters point to our CCountry
    n_ptr_country=0
    with_leader=[]
    for j in range(arr["size"]):
        cp=p.ptr(arr["data"]+j*8)
        raw=p.try_read(cp, 0x160) or b""
        ok=False
        for off in range(0, len(raw)-7, 8):
            if struct.unpack_from("<Q", raw, off)[0]==co:
                ok=True; break
        if not ok:
            continue
        n_ptr_country += 1
        name=p.msvc_string(cp+0x28)
        army=p.ptr(cp+0xa8)
        ac=cls(army)
        if ac and "CArmyLeader" in ac:
            with_leader.append({"name":name,"char":hex(cp),"leader":hex(army)})
    print("chars pointing at player country", n_ptr_country, "with CArmyLeader@+0xa8", len(with_leader))
    print(json.dumps(with_leader, ensure_ascii=False, indent=2))
    Path("research/t183_player_leaders_index.json").write_text(json.dumps({"n_chars":n_ptr_country,"leaders":with_leader}, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
finally:
    p.close()
