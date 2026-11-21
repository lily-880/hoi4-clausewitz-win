import json,re,sys,struct,bisect
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

# token map
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={item["token"]:item["name"] for item in mp}

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
pd=next(s for s in pe.sections if s.name==".pdata")
raw_pd=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
functions=[struct.unpack_from("<III", raw_pd, o)[:2] for o in range(0,len(raw_pd)-11,12)]
starts=[x[0] for x in functions]
text=next(s for s in pe.sections if s.name==".text")
text_rva=text.virtual_address
text_raw=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]

def func_of(rva):
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

# print full secondary writer with token names and nearby mem ops
code=json.loads(Path("research/t165_army_secondary_writer.json").read_text(encoding="utf-8"))["code"]
print("===== CArmy secondary writer 0xced2e0 =====")
for item in code:
    a=item["asm"]
    extra=""
    m=re.search(r"edx, 0x([0-9a-f]+)", a)
    if m:
        tok=int(m.group(1),16)
        extra="  ; TOKEN "+id2name.get(tok, "?")
    print(item["rva"], a+extra)

# search mov edx, 0x34a6 (land_combat_id) and 0x174 (path) and 0x28a2 move_order, 0x2919 land_combat
print("\n===== xrefs mov edx, token =====")
interesting={
    0x34a6:"land_combat_id",
    0x174:"path",
    0x28a2:"move_order",
    0x2919:"land_combat",
    0x2916:"combat",
    0x34a3:"land_path",
    0x2fdf:"last_combat_date",
    0x2f57:"orders",
    0x385b:"is_assigned",
    0x2edb:"strategic_redeployment",
    0x3041:"execute_order",
    0x335f:"out_of_supply_days",
    0x35ba:"unit_controller_pause",
}
# encoding: ba xx xx 00 00  mov edx, imm32  (for tokens < 0x10000)
# or 41 ba for r10d etc. Also 89 or b8.
# Search BA followed by token little endian
for tok,name in interesting.items():
    imm=struct.pack("<I", tok)
    hits=[]
    for m in re.finditer(re.escape(b"\xba"+imm), text_raw):  # mov edx, imm32
        at=text_rva+m.start()
        fo=func_of(at)
        hits.append((hex(at), hex(fo[0]) if fo else None, hex(fo[1]-fo[0]) if fo else None))
    print(hex(tok), name, "mov edx hits", hits[:12], "count", len(hits))
