import sys,re,json
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}

raw=pe.read_rva(0x10d1c40, 0x400) or b""
lines=[]
for i in cs.disasm(raw, 0x10d1c40):
    a=f"0x{i.address:x}  {i.mnemonic} {i.op_str}"
    m=re.search(r"(edx|r8d|r9d|esi|edi|eax|ecx), 0x([0-9a-f]+)", i.op_str)
    if m:
        tok=int(m.group(2),16)
        if tok in id2name:
            a += "  ; TOKEN "+id2name[tok]
    lines.append(a)
    if i.mnemonic=="ret":
        break
Path("research/_t188_clip_orderinstance_writer_tail.txt").write_text("\n".join(lines)+"\n", encoding="utf-8")
print("n", len(lines), "last", lines[-1] if lines else None)
for ln in lines:
    if "TOKEN" in ln or "ret" in ln or "fallback" in ln or "execut" in ln:
        print(ln)

# find execution_type / execute_order / can_execute immediates in writers
import struct
text=[s for s in pe.sections if s.name==".text"][0]
blob=pe.read_rva(text.virtual_address, text.virtual_size) or b""
base=text.virtual_address
for name,tok in (("execution_type",0x36aa),("execute_order",0x3041),("can_execute",0x30b2),("order_execute_command",0x3040),("order_children",0x30b3)):
    imm=struct.pack("<I", tok)
    useful=[]
    start=0
    while True:
        k=blob.find(imm, start)
        if k<0: break
        if k>=1 and blob[k-1]==0xBA:
            useful.append(base+k-1)
        start=k+1
        if len(useful)>=12: break
    print(f"  {name} mov edx sites: " + " ".join(hex(a) for a in useful))
