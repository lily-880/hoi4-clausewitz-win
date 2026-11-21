import sys,re,json,struct
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}

# tokens in CState writer 0xa2bbc0-0xa2c2ca
raw=pe.read_rva(0xa2bbc0, 0xa2c2ca-0xa2bbc0+16) or b""
toks=[]
for i in cs.disasm(raw, 0xa2bbc0):
    m=re.search(r"(edx|r8d|r9d), 0x([0-9a-f]+)", i.op_str)
    if m:
        t=int(m.group(2),16)
        if t in id2name:
            toks.append(f"0x{i.address:x}  {i.mnemonic} {i.op_str}  ; TOKEN {id2name[t]}")
    if "0x18" in i.op_str and ("lea" in i.mnemonic or "cmp" in i.mnemonic or "mov" in i.mnemonic):
        toks.append(f"0x{i.address:x}  {i.mnemonic} {i.op_str}")
print("=== CState writer tokens / +0x18 ===")
print("\n".join(toks[:80]))
Path("research/_t189_clip_cstate_writer_tokens.txt").write_text("\n".join(toks)+"\n", encoding="utf-8")

# pdata for intel 0xd689f2
pdata=[s for s in pe.sections if s.name==".pdata"][0]
pblob=pe.read_rva(pdata.virtual_address, pdata.virtual_size) or b""
def func(addr):
    for i in range(0,len(pblob)-12,12):
        b,e,u=struct.unpack_from("<III", pblob, i)
        if b<=addr<e: return b,e
    return None,None
for site,name in ((0xd689f2,"intel_d689f2"),(0x123c3e8,"intel_123c3e8"),(0x1c3c7e7,"visible_1c3c7e7"),(0x7627c9,"intel_7627c9")):
    b,e=func(site)
    print(f"\n=== {name} func {hex(b) if b else None}-{hex(e) if e else None} site 0x{site:x} ===")
    if not b: continue
    raw=pe.read_rva(b, min(e-b, 0x300)) or b""
    found=[]
    for i in cs.disasm(raw, b):
        a=f"0x{i.address:x}  {i.mnemonic} {i.op_str}"
        m=re.search(r"(edx|r8d|r9d), 0x([0-9a-f]+)", i.op_str)
        if m:
            t=int(m.group(2),16)
            if t in id2name:
                a += "  ; TOKEN "+id2name[t]
                found.append(a)
    print("\n".join(found[:25]) or "(no tokens in first 0x300)")
