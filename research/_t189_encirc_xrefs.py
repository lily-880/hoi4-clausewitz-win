import sys,re,json,struct
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}

text=[s for s in pe.sections if s.name==".text"][0]
blob=pe.read_rva(text.virtual_address, text.virtual_size) or b""
base=text.virtual_address

targets={
    0x2a460a0: "EncirclementPoints_assert",
    0x27a62b0: "highlight_encirclements",
    0x27a62c8: "toggle_highlight_encirclements",
}
# also MAP_INTEL_VISIBILITY_CUTOFFS
rdata=[s for s in pe.sections if s.name==".rdata"][0]
rblob=pe.read_rva(rdata.virtual_address, rdata.virtual_size) or b""
for m in re.finditer(rb"MAP_INTEL_VISIBILITY_CUTOFFS", rblob):
    va=rdata.virtual_address+m.start()
    targets[va]="MAP_INTEL_VISIBILITY_CUTOFFS"
    print("cutoff string", hex(va))

hits={k:[] for k in targets}
pos=0
while True:
    j=blob.find(b"\x8d", pos)
    if j<0: break
    pos=j+1
    start=j
    rex=None
    if j>=1 and 0x40<=blob[j-1]<=0x4F:
        start=j-1
        rex=blob[j-1]
    if j+6>len(blob): continue
    modrm=blob[j+1]
    if (modrm & 0xC7)!=0x05: continue
    disp=struct.unpack_from("<i", blob, j+2)[0]
    insn_len=(1 if rex is not None else 0)+1+1+4
    rip=base+start+insn_len
    tgt=rip+disp
    if tgt in targets:
        hits[tgt].append(base+start)

print("lea hits")
for va,name in targets.items():
    print(f"  {name} 0x{va:x}: " + " ".join(hex(a) for a in hits[va][:15]), "n=",len(hits[va]))

# dump around first EncirclementPoints xref
for va,addrs in hits.items():
    if not addrs: continue
    a=addrs[0]
    # find nearby function start roughly
    raw=pe.read_rva(a-0x80, 0x120) or b""
    print(f"\n======= around 0x{a:x} for {targets[va]} =====")
    for i in cs.disasm(raw, a-0x80):
        if abs(i.address-a)<0x60 or i.address==a:
            s=f"0x{i.address:x}  {i.mnemonic} {i.op_str}"
            if i.address==a:
                s += "  ; LEA TARGET"
            print(s)
