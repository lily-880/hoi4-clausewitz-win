import sys,os,re,json,struct,collections
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
        if i.mnemonic=="ret" and i.address>start+8:
            break
    if path:
        Path(path).write_text("\n".join(lines)+"\n", encoding="utf-8")
    return lines

# 0xc08170
print("======= 0xc08170 =====")
print("\n".join(clip(0xc08170, 0x80, "research/_t186_clip_c08170.txt")))

# active_relations region of diplomacy writer
lines=Path("research/_t186_clip_diplomacystatus_writer_0xdad1a0.txt").read_text(encoding="utf-8").splitlines()
print("\n======= 0xdad1a0 first 80 + capitulated window =====")
for ln in lines[:80]:
    print(ln)
print("...")
for ln in lines:
    addr=int(ln.split()[0],16)
    if 0xdad660<=addr<=0xdad6c0 or "capitul" in ln.lower() or "active_relations" in ln or "0x2e43" in ln:
        print(ln)

# print more context around active_relations and capitulated
print("\n======= around tokens with mem =====")
for i,ln in enumerate(lines):
    if "TOKEN" in ln:
        for x in lines[max(0,i-8):i+6]:
            print(x)
        print("---")
