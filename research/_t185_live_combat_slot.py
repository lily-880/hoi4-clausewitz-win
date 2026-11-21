import sys,os,struct,json,collections
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from mem import Proc, find_pid
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from gamestate import detect_session, resolve_player_country, _pdx_array
import re
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"

# clip 0x1613f40
pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}
cs=Cs(CS_ARCH_X86, CS_MODE_64)
raw=pe.read_rva(0x1613f40, 0x200) or b""
lines=[]
for i in cs.disasm(raw, 0x1613f40):
    a=f"0x{i.address:x}  {i.mnemonic} {i.op_str}"
    m=re.search(r"(edx|r8d|r9d|esi|edi|eax|ecx), 0x([0-9a-f]+)", i.op_str)
    if m:
        tok=int(m.group(2),16)
        if tok in id2name:
            a += "  ; TOKEN "+id2name[tok]
    lines.append(a)
    if i.mnemonic=="ret" and i.address>0x1613f40+16:
        break
Path("research/_t185_clip_land_combat_0x1613f40.txt").write_text("\n".join(lines)+"\n", encoding="utf-8")
print("======= 0x1613f40 =====")
print("\n".join(lines))

p=Proc(find_pid("hoi4.exe"))
try:
    session=detect_session(p, pe)
    gs=int(session["signals"]["gs_ptr"],16)
    res=resolve_player_country(p, gs)
    co=int(res["country_ptr"],16)
    ar=_pdx_array(p, co+0x290)
    rows=[]
    for slot in range(ar["size"]):
        ap=p.ptr(ar["data"]+slot*8)
        vt=p.ptr(ap+0x338)
        rows.append({
            "unit_id": p.u32(ap+0x1c),
            "vt_338_rva": hex((vt-p.base) if vt and p.base<=vt<p.base+p.image_size else 0),
            "combat_340": p.i32(ap+0x340),
            "training_344": p.i32(ap+0x344),
            "q_348": p.u64(ap+0x348),
            "dwords_348_360": {hex(off): p.i32(ap+off) for off in range(0x348, 0x368, 4)},
        })
    print(json.dumps({
        "n": len(rows),
        "vt_hist": dict(collections.Counter(r["vt_338_rva"] for r in rows)),
        "combat_hist": dict(collections.Counter(r["combat_340"] for r in rows)),
        "training_hist": dict(collections.Counter(r["training_344"] for r in rows)),
        "sample0": rows[0],
    }, indent=2))
    Path("research/t185_live_carmy_combat_slot.json").write_text(json.dumps({
        "pid": p.pid, "read_only": True, "gs_combats": _pdx_array(p, gs+0x268),
        "units": rows
    }, indent=2)+"\n", encoding="utf-8")
finally:
    p.close()
