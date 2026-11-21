import sys,re,json
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

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
        if i.mnemonic=="ret" and i.address>start+16:
            break
    if path:
        Path(path).write_text("\n".join(lines)+"\n", encoding="utf-8")
    return lines

lines=clip(0x11105b0, 0xE00, "research/_t185_clip_plandcombat_assert_0x11105b0.txt")
print("n lines", len(lines), "end", lines[-1] if lines else None)
# print window around the two string refs
for needle in ("0x1110ec5", "0x1111243", "pLand", "2a04720", "2a04730"):
    pass
# find lea of those rvas in the clip
for i,ln in enumerate(lines):
    if any(s in ln for s in ("0x18f414a","0x18f3e6a","2a04720","2a04730","1110ec5","1111243")) or "rip +" in ln and "0x18" in ln:
        # print context
        pass

# print all lines around 0x1110e80-0x1110f40 and 0x1111200-0x1111280, plus any lea rip
print("\n===== lea/rip and window around pLandCombat xref =====")
for i,ln in enumerate(lines):
    addr=int(ln.split()[0],16)
    if ("lea" in ln and "rip" in ln) or (0x1110e80<=addr<=0x1110f80) or (0x11111f0<=addr<=0x11112c0) or "qword ptr [" in ln and any(r in ln for r in ("rcx","rbx","rsi","rdi","r14","r15","rbp")):
        # too many mem; just print lea rip + first 40 + two windows
        pass

print("--- all rip lea ---")
for ln in lines:
    if "rip" in ln:
        print(ln)

print("\n--- window 0x1110e80-0x1110fa0 ---")
for ln in lines:
    addr=int(ln.split()[0],16)
    if 0x1110e80<=addr<=0x1110fa0:
        print(ln)

print("\n--- window 0x11111f0-0x11112d0 ---")
for ln in lines:
    addr=int(ln.split()[0],16)
    if 0x11111f0<=addr<=0x11112d0:
        print(ln)

print("\n--- first 40 ---")
for ln in lines[:40]:
    print(ln)
