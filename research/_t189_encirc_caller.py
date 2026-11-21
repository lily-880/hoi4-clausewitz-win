import sys,re,json,struct
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}

# pdata for 0x156cab2
pdata=[s for s in pe.sections if s.name==".pdata"][0]
pblob=pe.read_rva(pdata.virtual_address, pdata.virtual_size) or b""
hit=None
for i in range(0,len(pblob)-12,12):
    begin,end,unw=struct.unpack_from("<III", pblob, i)
    if begin <= 0x156cab2 < end:
        hit=(begin,end); break
print("caller func", hex(hit[0]), hex(hit[1]) if hit else None, "size", (hit[1]-hit[0]) if hit else None)

def tokens_in(start, nbytes, path=None):
    raw=pe.read_rva(start, nbytes) or b""
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

start=hit[0] if hit else 0x156c800
lines,toks=tokens_in(start, min((hit[1]-hit[0]) if hit else 0x400, 0x800), "research/_t189_clip_encirc_caller_0x156cab2.txt")
print("caller n", len(lines), "last", lines[-1] if lines else None)
print("TOKENS:")
print("\n".join(toks) if toks else "(none)")
print("\n--- first 50 / calls ---")
for ln in lines[:50]:
    if any(k in ln for k in ("call ","TOKEN","lea r","mov r13","mov rcx","0x1571ef0","ret")):
        print(ln)
# print around the call
print("\n--- around 0x156cab2 ---")
for ln in lines:
    addr=int(ln.split()[0],16)
    if 0x156ca80 <= addr <= 0x156cb00:
        print(ln)

# token sites for visible/intel/army_intel/alerts with more opcodes
text=[s for s in pe.sections if s.name==".text"][0]
blob=pe.read_rva(text.virtual_address, text.virtual_size) or b""
base=text.virtual_address
print("\n=== token immediates (any preceding byte) ===")
for name,tok in (("visible",0x2d2a),("alerts",0x2d42),("intel",0x30ec),("army_intel",0x4b36),("detected",0x4b06)):
    imm=struct.pack("<I", tok)
    sites=[]
    starti=0
    while True:
        k=blob.find(imm, starti)
        if k<0: break
        prev=blob[k-1] if k>=1 else 0
        # typical mov r32, imm = B8+reg or BA, or 41 BA, or C7
        if prev in (0xB8,0xB9,0xBA,0xBB,0xB8,0xBF,0xBE,0xBD) or (k>=2 and blob[k-2] in (0x41,0x44,0x45) and prev in (0xB8,0xB9,0xBA,0xBB)) or prev==0xC7 or (k>=2 and blob[k-2]==0xC7):
            sites.append((base+k-1, prev))
        starti=k+1
        if len(sites)>=12: break
    print(f"  {name} 0x{tok:x}: " + " ".join(f"0x{a:x}(op={pr:02x})" for a,pr in sites[:12]), "n", len(sites))
