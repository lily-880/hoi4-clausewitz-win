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

# filename at 0x1110ebe lea rdx, [rip + 0x1683858]
# 0x1110ebe+7+0x1683858 = file rva
file_rva=0x1110ec5+0x1683858  # wait, lea is at 0x1110ebe, instruction is 7 bytes: 0x1110ebe+7+disp
# lea rdx, [rip+0x1683858] at 0x1110ebe; next is 0x1110ec5, so rip=0x1110ec5, dest=0x1110ec5+0x1683858
print("filename rva", hex(0x1110ec5+0x1683858))
print("expr rva", hex(0x1110ecc+0x18f3854))  # lea rcx at 0x1110ec5, rip=0x1110ecc
# check
for addr,disp,label in (
    (0x1110ec5, 0x1683858, "file pLand"),
    (0x1110ecc, 0x18f3854, "expr pLand"),
    (0x1111243, 0x16834da, "file pMove"),
    (0x111124a, 0x18f34e6, "expr pMove"),
):
    rva=addr+disp
    raw=pe.read_rva(rva, 80) or b""
    s=raw.split(b"\x00")[0].decode("ascii","replace")
    print(label, hex(rva), s)

print("\n======= 0x25c38b0 =====")
lines=clip(0x25c38b0, 0x100, "research/_t185_clip_25c38b0.txt")
print("\n".join(lines[:40]))

print("\n======= 0xc52e90 GetMovingTo? =====")
lines=clip(0xc52e90, 0x120, "research/_t185_clip_c52e90.txt")
print("\n".join(lines))

print("\n======= 0xc51a90 =====")
lines=clip(0xc51a90, 0x120, "research/_t185_clip_c51a90.txt")
print("\n".join(lines))

print("\n======= 0xc4f950 =====")
lines=clip(0xc4f950, 0x80, "research/_t185_clip_c4f950.txt")
print("\n".join(lines))

print("\n======= 0xc45310 (CArmy+0xb8) =====")
lines=clip(0xc45310, 0x120, "research/_t185_clip_c45310.txt")
print("\n".join(lines))

# rsi assignments in 0x11105b0 before 0x1110e75
print("\n======= rsi / r14 / combat-like in 0x11105b0 before assert =====")
lines=Path("research/_t185_clip_plandcombat_assert_0x11105b0.txt").read_text(encoding="utf-8").splitlines()
for ln in lines:
    addr=int(ln.split()[0],16)
    if addr>0x1110e80:
        break
    if any(s in ln for s in ("rsi", "r14", "0x1f0", "combat", "call 0xc", "lea rcx, [r14")):
        print(ln)
