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
        if i.mnemonic=="ret" and i.address>start+8:
            break
    if path:
        Path(path).write_text("\n".join(lines)+"\n", encoding="utf-8")
    return lines

# find func starts: 0xd8ed13 was in func 0xd8ed13? earlier said func 0xd8ed13 — actually "func 0xd8ed13" from pdata of lea site 0xd8ee7b, func 0xd8ed13
for start,tag,nb in (
    (0xd7da30,"getter_0xd7da30",0x80),
    (0xd7db8b,"getter_0xd7db8b",0x80),
    (0xd7dc10,"getter_0xd7dc10",0x80),
    (0xd7deb0,"getter_0xd7deb0",0x80),
    (0xd7e050,"getter_0xd7e050",0x80),
    (0xd7fcd4,"getter_0xd7fcd4",0x80),
    (0xd7fdf0,"store_0xd7fdf0",0x200),
    (0xd79480,"ctor_0xd79480",0x200),
    (0xd8ed13,"status_writer_2e8_0xd8ed13",0x200),
    (0xd82c10,"use_0xd82c10",0x40),
    (0xd89510,"use_0xd89510",0x80),
):
    lines=clip(start, nb, f"research/_t186_clip_{tag}.txt")
    toks=[ln for ln in lines if "TOKEN" in ln or "0x2e8" in ln or "call 0xd8f" in ln or "call 0x254" in ln]
    print(f"\n======= {hex(start)} {tag} n={len(lines)} last={lines[-1] if lines else None} =====")
    if len(lines)<=20:
        print("\n".join(lines))
    else:
        for ln in lines:
            if "TOKEN" in ln or "0x2e8" in ln or "War" in ln or "ret" in ln.split()[-1:]:
                print(ln)
        print("  --- first 15 ---")
        print("\n".join(lines[:15]))
