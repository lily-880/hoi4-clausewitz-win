import sys,re,json,struct
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}
pdata=[s for s in pe.sections if s.name==".pdata"][0]
pblob=pe.read_rva(pdata.virtual_address, pdata.virtual_size) or b""

def func(addr):
    for i in range(0,len(pblob)-12,12):
        b,e,u=struct.unpack_from("<III", pblob, i)
        if b<=addr<e: return b,e
    return None,None

def tokens(start, size, path=None):
    raw=pe.read_rva(start, size) or b""
    lines=[]; toks=[]
    for i in cs.disasm(raw, start):
        a=f"0x{i.address:x}  {i.mnemonic} {i.op_str}"
        m=re.search(r"(edx|r8d|r9d|esi|edi|eax|ecx), 0x([0-9a-f]+)", i.op_str)
        if m:
            t=int(m.group(2),16)
            if t in id2name:
                a += "  ; TOKEN "+id2name[t]
                toks.append(a)
        lines.append(a)
        if i.mnemonic=="ret" and i.address>start+8:
            break
    if path:
        Path(path).write_text("\n".join(lines)+"\n", encoding="utf-8")
    return lines, toks

for site,name in ((0x15ab8c4,"need_15ab8c4"),(0x108660d,"army_need_108660d"),(0xcc7a50,"cc7a50_writer"),(0x15ab543,"manpower_pool_15ab543"),(0x1f4ee,"deploy_queue_1f4ee")):
    b,e=func(site)
    print(f"\n======= {name} site 0x{site:x} func {hex(b) if b else None}-{hex(e) if e else None} =====")
    start=b or (site-0x40)
    size=min((e-start) if e and b else 0x200, 0x400)
    lines,toks=tokens(start, size, f"research/_t190_clip_{name}.txt")
    print("tokens:")
    print("\n".join(toks) if toks else "(none in window)")
    # also print 8 lines around site
    print("-- around site --")
    for ln in lines:
        try:
            addr=int(ln.split()[0],16)
        except Exception:
            continue
        if site-0x20 <= addr <= site+0x20:
            print(ln)
