import sys,re,json,struct,bisect
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from gamestate import _rtti_name_from_vtable

mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}
name2={i["name"]:i["token"] for i in mp}
pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
IMAGE=pe.image_base
text=next(s for s in pe.sections if s.name==".text")
text_raw=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]
text_rva=text.virtual_address
pd=next(s for s in pe.sections if s.name==".pdata")
raw_pd=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
functions=[struct.unpack_from("<III", raw_pd, o)[:2] for o in range(0,len(raw_pd)-11,12)]
starts=[x[0] for x in functions]

def func_of(rva):
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

def clip(start, end, path=None):
    raw=pe.read_rva(start, end-start) or b""
    lines=[]
    for i in cs.disasm(raw, start):
        a=f"0x{i.address:x}  {i.mnemonic} {i.op_str}"
        m=re.search(r"(edx|r8d|r9d|esi|edi|eax|ecx), 0x([0-9a-f]+)", i.op_str)
        if m:
            tok=int(m.group(2),16)
            if tok in id2name:
                a += "  ; TOKEN "+id2name[tok]
        lines.append(a)
        if i.mnemonic=="ret" and i.address>start+16 and path:
            break
    if path:
        Path(path).write_text("\n".join(lines)+"\n", encoding="utf-8")
    return lines

# CLandCombat writer
lines=clip(0x147fe80, 0x147fe80+0x800, "research/_t184_clip_landcombat_writer_0x147fe80.txt")
print("===== CLandCombat 0x147fe80 tokens/mem (first 80 useful) =====")
n=0
for ln in lines:
    if "TOKEN" in ln or re.search(r"\[r(bx|si|di|bp|1[0-5]|cx|14|15) \+", ln) or "lea r8" in ln or "0x22858a0" in ln:
        print(ln); n+=1
        if n>=80: break
print("total lines", len(lines), "ends", lines[-1] if lines else None)

# supply / isolated tokens
for n in ("in_supply","isolated","is_in_supply","is_isolated","out_of_supply","supply_ratio","has_supply"):
    if n in name2:
        print("TOKEN", n, hex(name2[n]))
print("fuzzy supply:")
for i in mp:
    if any(s in i["name"] for s in ("in_supply","isolated","out_of_supply","is_isolated","supply_isolated")):
        print(hex(i["token"]), i["name"])

# mov dword [reg+8], imm32  for command-like tokens
# encodings: C7 40 08 imm32  ( [rax+8] )
#            C7 41 08, C7 42 08, C7 43 08, C7 45 08, C7 46 08, C7 47 08
#            C7 44 24 08? stack
#            41 C7 40 08 / 41 C7 41 08 ... r8+8
order_tokens={}
for nm in ("move_order","support_attack","retreat","withdraw","strategic_redeployment","execute_order","training","exercise","garrison","idle","attack","move","hold"):
    if nm in name2:
        order_tokens[name2[nm]]=nm
# also names ending with _command that look unit-tactical
for i in mp:
    n=i["name"]
    if n.endswith("_command") and any(s in n for s in ("move","attack","retreat","train","exercise","garrison","hold","stop","cancel_move","support")):
        order_tokens[i["token"]]=n

print("searching stores of", {hex(k):v for k,v in order_tokens.items()})
hits={}
for tok,name in order_tokens.items():
    imm=struct.pack("<I", tok)
    found=[]
    for prefix in (b"\xc7\x40\x08", b"\xc7\x41\x08", b"\xc7\x42\x08", b"\xc7\x43\x08",
                   b"\xc7\x46\x08", b"\xc7\x47\x08", b"\x41\xc7\x40\x08", b"\x41\xc7\x41\x08",
                   b"\x41\xc7\x42\x08", b"\x41\xc7\x43\x08", b"\x41\xc7\x46\x08", b"\x41\xc7\x47\x08"):
        pat=prefix+imm
        for m in re.finditer(re.escape(pat), text_raw):
            at=text_rva+m.start()
            fo=func_of(at)
            found.append({"at":hex(at),"func":hex(fo[0]) if fo else None,"enc":prefix.hex()})
    hits[name]={"token":hex(tok),"n":len(found),"hits":found[:8]}
    print(name, hex(tok), "n", len(found), "funcs", sorted({h["func"] for h in found if h["func"]})[:8])

Path("research/t184_command_plus8_stores.json").write_text(json.dumps(hits, indent=2)+"\n", encoding="utf-8")
