import sys,os,struct,json,re,collections
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from mem import Proc, find_pid
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from gamestate import detect_session, resolve_player_country, _pdx_array, _rtti_name_from_vtable
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}
IMAGE=pe.image_base

def clip(start, end, path=None, extra=0):
    raw=pe.read_rva(start, end-start) or b""
    lines=[]
    for i in cs.disasm(raw, start):
        a=f"0x{i.address:x}  {i.mnemonic} {i.op_str}"
        m=re.search(r"(edx|r8d|r9d|esi|edi|eax|ecx), 0x([0-9a-f]+)", i.op_str)
        if m:
            tok=int(m.group(2),16)
            if tok in id2name:
                a += "  ; TOKEN "+id2name[tok]
        lines.append(a)
        if i.mnemonic=="ret" and i.address>start+8:
            if extra<=0:
                break
            extra -= 1
    if path:
        Path(path).write_text("\n".join(lines)+"\n", encoding="utf-8")
    return lines

for rva,name,sz in ((0x25459e0,"int_or_id_writer_0x25459e0",0x80),(0x19ee810,"19ee810",0x200),(0x19ee660,"19ee660",0x200),(0x74ad90,"74ad90",0x80),(0x22856e0,"22856e0",0x80)):
    lines=clip(rva, rva+sz, f"research/_t185_clip_{name}.txt")
    print(f"\n======= {hex(rva)} {name} n={len(lines)} =====")
    print("\n".join(lines[:40]))

p=Proc(find_pid("hoi4.exe"))
try:
    def cls(a):
        if not a or a<0x10000 or a>0x7fffffffffff: return None
        vt=p.ptr(a)
        if not vt or not (p.base<=vt<p.base+p.image_size): return None
        try:
            n=_rtti_name_from_vtable(pe, vt-p.base)
            return n
        except Exception:
            return None
    session=detect_session(p, pe)
    gs=int(session["signals"]["gs_ptr"],16)
    res=resolve_player_country(p, gs)
    co=int(res["country_ptr"],16)
    ar=_pdx_array(p, co+0x290)
    rows=[]
    classes=collections.Counter()
    for slot in range(ar["size"]):
        ap=p.ptr(ar["data"]+slot*8)
        q340=p.u64(ap+0x340)
        q348=p.u64(ap+0x348)
        q350=p.u64(ap+0x350)
        rows.append({
            "unit_id": p.u32(ap+0x1c),
            "q340": hex(q340),
            "cls340": cls(q340),
            "cls_if_340_is_obj": cls(ap+0x340),
            "q348": hex(q348),
            "cls348": cls(q348),
            "q350": hex(q350),
            "cls350": cls(q350),
            "u32_340": hex(p.u32(ap+0x340)),
            "u32_344": hex(p.u32(ap+0x344)),
        })
        classes[rows[-1]["cls340"]] += 1
        classes["348:"+str(rows[-1]["cls348"])] += 1
    print("\nclass hist", dict(classes))
    print("sample0", json.dumps(rows[0], indent=2))
    print("sample1", json.dumps(rows[1], indent=2))
    Path("research/t185_live_carmy_340.json").write_text(json.dumps(rows, indent=2)+"\n", encoding="utf-8")
finally:
    p.close()
