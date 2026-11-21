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

# RIP-relative lea/mov targets to these strings
targets={
    0x29f6428: "ORDER_DEFENSIVE_LINE",
    0x29f6560: "ORDER_OFFENSIVE_LINE",
    0x29f6630: "ORDER_INVASION",
    0x29f6750: "ORDER_PARADROP",
    0x29f6880: "ORDER_AREA_DEFENSE",
    0x2a02c18: "assert_ORDER_INVASION",
    0x2a02cb8: "assert_ne_ORDER_MOVE",
    0x2a02d50: "assert_ORDER_MOVE",
    0x2a86ef0: "assert_INVASION_or_PARADROP",
    0x2aa1598: "tut_frontline",
    0x2aa15a8: "tut_offensive_order",
    0x2a03830: "root_order_instance_frontline",
}

# scan for lea/mov with rip-rel 32
# E8 is call; 48 8D 15 / 4C 8D 15 / 48 8D 0D / 4C 8D 0D / 48 8D 05 / 4C 8D 05 / 48 8D 1D etc
# also 48 8D 05 disp32, 4C 8D 05, 48 8D 0D, 4C 8D 0D, 48 8D 15, 4C 8D 15, 48 8D 1D, 4C 8D 1D, 48 8D 35, 4C 8D 35, 48 8D 3D, 4C 8D 3D
#  lea r64, [rip+disp] is rex + 8D /r  with modrm 05/0D/15/1D/25/2D/35/3D and mod=00
hits={k:[] for k in targets}
# generic: find 8D with rip-rel
i=0
n=len(blob)
base=text.virtual_address
# faster: for each possible 8D, check
# also FF 15 etc not needed
# pattern: optional rex (40-4f) then 8D then modrm in {0x05,0x0D,0x15,0x1D,0x25,0x2D,0x35,0x3D} then disp32
rex_or_none = True
pos=0
count=0
while True:
    j=blob.find(b"\x8d", pos)
    if j<0: break
    pos=j+1
    # check rex immediately before
    start=j
    rex=None
    if j>=1 and 0x40<=blob[j-1]<=0x4F:
        start=j-1
        rex=blob[j-1]
    if j+1+1+4>n: continue
    modrm=blob[j+1]
    if (modrm & 0xC7) != 0x05:  # mod=00 r/m=101 rip-rel
        continue
    disp=struct.unpack_from("<i", blob, j+2)[0]
    rip=base+j+6  # after lea opcode+modrm+disp (rex not in length after 8d)
    # instruction length: (1 if rex else 0)+1+1+4, RIP is end of insn
    insn_len = (1 if rex is not None else 0)+1+1+4
    rip=base+start+insn_len
    tgt=rip+disp
    if tgt in targets:
        hits[tgt].append(base+start)
        count+=1

print("lea hits", count)
for va,name in targets.items():
    addrs=hits[va]
    print(f"  {name} 0x{va:x} xrefs={len(addrs)} " + " ".join(hex(a) for a in addrs[:12]))

# also search immediates for tokens
tokens={"order_instance":0x35f7,"area_defense":0x4c2e,"fallback":0x33d8,"front":0x29e0,"virtual_fallback":0x35f3,"vertices":0x101,"garrison":0x2928}
# mov edx, imm32 = BA imm32; mov r8d/r9d etc
print("\n=== token immediates (BA/B8-BF / C7) first 20 each ===")
for name,tok in tokens.items():
    imm=struct.pack("<I", tok)
    locs=[]
    start=0
    while True:
        k=blob.find(imm, start)
        if k<0: break
        # preceding opcode-ish
        rva=base+k
        locs.append(rva)
        start=k+1
        if len(locs)>=30:
            break
    # filter those with mov edx/r8d nearby: look at byte before imm
    useful=[]
    for rva in locs:
        off=rva-base
        prev=blob[max(0,off-3):off]
        # BA = mov edx,imm32
        if off>=1 and blob[off-1]==0xBA:
            useful.append(rva-1)
        elif off>=1 and blob[off-1] in (0xB8,0xB9,0xBB,0xBF):
            useful.append(rva-1)
        elif off>=2 and blob[off-2]==0xC7:  # mov dword [..], imm? maybe
            useful.append(rva-2)
        elif off>=3 and blob[off-3]==0xC7:
            useful.append(rva-3)
    print(f"  {name} 0x{tok:x} raw={len(locs)} mov-imm={len(useful)} " + " ".join(hex(a) for a in useful[:15]))
