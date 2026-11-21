import sys,re,json,struct
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}

# jump table
raw=pe.read_rva(0xfcc818, 12*4) or b""
print("jump table 0xfcc818 (types 2..13, index=type-2):")
for i in range(12):
    off=struct.unpack_from("<I", raw, i*4)[0]
    typ=i+2
    print(f"  type {typ:2d}  entry=0x{off:x}")

# GetOrderType sites
def clip(start, n, path=None, until_ret=False):
    raw=pe.read_rva(start, n) or b""
    lines=[]
    for i in cs.disasm(raw, start):
        a=f"0x{i.address:x}  {i.mnemonic} {i.op_str}"
        m=re.search(r"(edx|r8d|r9d|esi|edi|eax|ecx), 0x([0-9a-f]+)", i.op_str)
        if m:
            tok=int(m.group(2),16)
            if tok in id2name:
                a += "  ; TOKEN "+id2name[tok]
        lines.append(a)
        if until_ret and i.mnemonic=="ret" and i.address>start+4:
            break
    if path:
        Path(path).write_text("\n".join(lines)+"\n", encoding="utf-8")
    return lines

print("\n======= 0x10b2c40 GetOrderType MOVE assert =====")
print("\n".join(clip(0x10b2c40, 0x80)[:40]))
print("\n======= 0x10b0370 INVASION assert =====")
print("\n".join(clip(0x10b0360, 0x80)[:40]))

# scan 0x10b0000-0x10d4000 for cmp dword [rXX+0x30], imm
text=[s for s in pe.sections if s.name==".text"][0]
blob=pe.read_rva(0x10b0000, 0x25000) or b""
print("\n======= cmp dword [reg+0x30], imm in 0x10b0000-0x10d5000 =====")
# capstone the region is huge; instead pattern: 83 7? 30 imm  or 81 7? 30 imm32 or 83 b? 30 00 00 00 imm
# 83 78 30 xx = cmp dword [rax+0x30], imm8
# 83 79 30, 83 7A, 83 7B, 83 7D, 83 7E, 83 7F
# 41 83 78/79/... 
# 81 78 30 imm32
hits=[]
for i in range(len(blob)-6):
    b=blob[i]
    # optional rex/prefix 41
    off=i
    if blob[i] in (0x41,0x44,0x45,0x4c,0x4d):
        off=i+1
        if off>=len(blob): continue
    if blob[off]==0x83 and off+3<len(blob):
        modrm=blob[off+1]
        # mod=01, disp8=0x30, /7 is cmp = modrm reg=7
        if (modrm & 0x38)==0x38 and blob[off+2]==0x30:
            # mod 01
            if (modrm & 0xC0)==0x40:
                imm=blob[off+3]
                hits.append((0x10b0000+i, f"cmp dword [r+0x30], {imm}"))
    if blob[off]==0x81 and off+6<len(blob):
        modrm=blob[off+1]
        if (modrm & 0x38)==0x38 and blob[off+2]==0x30 and (modrm & 0xC0)==0x40:
            imm=struct.unpack_from("<I", blob, off+3)[0]
            if imm<=20:
                hits.append((0x10b0000+i, f"cmp dword [r+0x30], {imm}"))

for va,s in hits:
    print(f"  0x{va:x}  {s}")

# executing-like tokens
print("\n=== execute/activated tokens ===")
for i in mp:
    n=i["name"].lower()
    if any(k in n for k in ("execut","activate","is_active","started","running","committed")):
        print(f"  0x{i['token']:x} {i['name']}")
