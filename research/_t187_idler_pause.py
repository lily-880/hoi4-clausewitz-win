import sys,os,re,json,struct
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from mem import Proc, find_pid
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from gamestate import detect_session, _rtti_name_from_vtable
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
IMAGE=pe.image_base
cs=Cs(CS_ARCH_X86, CS_MODE_64)
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}

def clip(start, nbytes, path=None):
    raw=pe.read_rva(start, nbytes) or b""
    lines=[]
    for i in cs.disasm(raw, start):
        a=f"0x{i.address:x}  {i.mnemonic} {i.op_str}"
        m=re.search(r"(edx|r8d|r9d|esi|edi|eax|ecx), 0x([0-9a-f]+)", i.op_str)
        if m:
            tok=int(m.group(2),16)
            if tok in id2name:
                a += "  ; TOKEN "+id2name[tok]
        lines.append(a)
        if i.mnemonic=="ret" and i.address>start+12:
            break
    if path:
        Path(path).write_text("\n".join(lines)+"\n", encoding="utf-8")
    return lines

# static vtable 0x29e58d8 CInGameIdler — slots +0x298 and +0x2f0
vt=0x29e58d8
raw=pe.read_rva(vt, 0x320) or b""
fn_298=struct.unpack_from("<Q", raw, 0x298)[0]-IMAGE
fn_2f0=struct.unpack_from("<Q", raw, 0x2f0)[0]-IMAGE
print("CInGameIdler vt+0x298", hex(fn_298), "vt+0x2f0", hex(fn_2f0))
# also print a few neighboring slots
for off in range(0x280, 0x310, 8):
    v=struct.unpack_from("<Q", raw, off)[0]
    if IMAGE<=v<IMAGE+0x4000000:
        print(f"  vt+{off:#x} {hex(v-IMAGE)}")

for start,tag,nb in ((fn_298,"idler_setpause_vt298",0x200),(fn_2f0,"idler_query_vt2f0",0x120)):
    lines=clip(start, nb, f"research/_t187_clip_{tag}_{hex(start)}.txt")
    print(f"\n======= {hex(start)} {tag} n={len(lines)} last={lines[-1] if lines else None} =====")
    print("\n".join(lines[:50]))

p=Proc(find_pid("hoi4.exe"))
try:
    session=detect_session(p, pe)
    print("\nsession idler", session.get("signals"))
    idler=int(session["signals"]["idler_ptr"],16)
    gs=int(session["signals"]["gs_ptr"],16)
    vt_live=p.ptr(idler)
    print("live idler", hex(idler), "vt rva", hex(vt_live-p.base), "rtti", _rtti_name_from_vtable(pe, vt_live-p.base))
    # confirm live vtable slots
    # read method ptrs from live vtable
    live_298=p.ptr(vt_live+0x298)
    live_2f0=p.ptr(vt_live+0x2f0)
    print("live +0x298", hex(live_298-p.base if live_298 else 0), "live +0x2f0", hex(live_2f0-p.base if live_2f0 else 0))
finally:
    p.close()
