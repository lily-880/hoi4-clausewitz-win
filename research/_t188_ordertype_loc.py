import sys,re,json
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}

def func_start(rva):
    # walk back looking at int3/cc or typical prolog; use pdata if possible
    # simple: search pdata
    return rva

def disasm(start, nbytes, until_ret=False):
    raw=pe.read_rva(start, nbytes) or b""
    lines=[]
    for i in cs.disasm(raw, start):
        a=f"0x{i.address:x}  {i.mnemonic} {i.op_str}"
        m=re.search(r"(edx|r8d|r9d|esi|edi|eax|ecx), 0x([0-9a-f]+)", i.op_str)
        if m:
            tok=int(m.group(2),16)
            if tok in id2name:
                a += "  ; TOKEN "+id2name[tok]
        # annotate lea to known
        lines.append(a)
        if until_ret and i.mnemonic=="ret" and i.address>start+8:
            break
    return lines

# find function starts via .pdata? skip - window around first xref
# Disassemble from 0xfc9f00 or find start by going back for push rbp / sub rsp
def find_start(around, back=0x200):
    raw=pe.read_rva(around-back, back+8) or b""
    # look for INT3 followed by typical prolog, or "mov qword [rsp+8]" etc
    # scan disasm of the window for last ret before around, then next insn
    last=around-back
    # try common: 40 53 / 48 89 5c / 48 83 ec / 55 48 8b ec
    candidates=[]
    for off in range(0, back):
        # int3 then non-int3
        if off+1<len(raw) and raw[off]==0xCC and raw[off+1]!=0xCC:
            candidates.append(around-back+off+1)
    # pick last candidate before around
    c=[x for x in candidates if x<=around]
    return c[-1] if c else around-back

start=find_start(0xfca238, 0x400)
print("approx start", hex(start))
# maybe too early; print first 20 after start and also dump 0xfc9e00-0xfcb400 focusing on cmp/jmp/lea
lines=disasm(0xfc9e00, 0x1600)
# filter interesting
print("--- cmps / switches / rets / leas ---")
for ln in lines:
    if any(k in ln for k in ("cmp ","test ","je ","jne ","ja ","jmp ","ret","lea r","lea rcx","lea rdx","lea r8","lea r9","call ")):
        # keep if nearby order or cmp imm small
        if any(k in ln for k in ("cmp ","ja ","jae ","jmp 0xfc","je 0xfc","jne 0xfc","ret","0x29f","call ")):
            print(ln)

# save full clip
Path("research/_t188_clip_order_loc_0xfc9e00.txt").write_text("\n".join(lines)+"\n", encoding="utf-8")
print("saved", len(lines))
