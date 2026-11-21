import sys, struct, json, re, bisect
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from gamestate import _rtti_name_from_vtable

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
IMAGE=pe.image_base
cs=Cs(CS_ARCH_X86, CS_MODE_64)
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))

# RTTI for vtable slot 0x29fb138 containing 0x14a8ec0
# walk back 8-byte slots until COL-like or first entry
def rtti_at_vtable(vt_rva):
    return _rtti_name_from_vtable(pe, vt_rva)

# try this slot and previous slots (up to 40)
names=[]
for i in range(0, 48):
    vt=0x29fb138 - 8*i
    n=_rtti_name_from_vtable(pe, vt)
    if n:
        names.append((i, hex(vt), n))
print("rtti walking back from 0x29fb138", names[:15])

# also try after
names2=[]
for i in range(0, 8):
    n=_rtti_name_from_vtable(pe, 0x29fb138+8*i)
    if n: names2.append((i,n))
print("forward", names2)

# command-like tokens
cmds=[]
for item in mp:
    n=item["name"]
    if any(s in n for s in ("move_command","attack_command","retreat","support_attack","strategic_redeploy","exercise","training","garrison","idle","order")) and "assign" not in n:
        if n.endswith("_command") or n in ("retreat","withdraw","support_attack","strategic_redeployment","execute_order") or "order" in n:
            cmds.append((hex(item["token"]), n))
print("command-ish tokens", len(cmds))
for t,n in sorted(cmds, key=lambda x:x[1])[:80]:
    print(t, n)

# InCombat string context
def read_cstr(rva, before=32, after=80):
    off=pe.rva_to_off(rva-before)
    blob=pe.data[off:off+before+after]
    return blob

for rva,label in ((0x29f9547,"InCombat("),(0x283234b,"is in combat")):
    blob=read_cstr(rva, 40, 80)
    # printable window
    s=bytes(b if 32<=b<127 else 46 for b in blob)
    print(label, hex(rva), s)

# utf16 search
textsec=next(s for s in pe.sections if s.name==".rdata")
# already have ascii. Look at 0x29f9547 nearby as utf8 function signature
