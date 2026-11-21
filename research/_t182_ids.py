import sys, re, json
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
db=pe.data

def rva_of(off):
    for s in pe.sections:
        if s.raw_ptr <= off < s.raw_ptr + s.raw_size:
            return s.virtual_address + (off - s.raw_ptr)
    return None

# focused exact and nearby identifier strings
needles = [
    b"in_combat\x00", b"is_in_combat\x00", b"InCombat\x00",
    b"current_combat\x00", b"GetCombat\x00", b"has_combat\x00",
    b"in_supply\x00", b"is_in_supply\x00", b"isolated\x00",
    b"army_current_supply_ratio\x00", b"max_supply\x00",
    b"out_of_supply\x00", b"current_supply\x00",
    b"supply_ratio\x00", b"supply_consumption\x00",
    b"unit_order\x00", b"UnitOrder\x00", b"order_type\x00",
    b"assigned_to\x00", b"AssignedTo\x00",
    b"army_id\x00", b"army_group_id\x00",
    b"strategic_redeployment\x00", b"strategic_redeployment_command\x00",
    b"is_moving\x00", b"in_combat_with\x00",
    b"CLandCombat\x00", b"CCombat\x00",
]
# also regex for short tokens
extra_pats = [
    rb"in_combat[_a-zA-Z0-9]*",
    rb"is_in_combat[_a-zA-Z0-9]*",
    rb"current_combat[_a-zA-Z0-9]*",
    rb"combat_id[_a-zA-Z0-9]*",
    rb"in_supply[_a-zA-Z0-9]*",
    rb"is_isolated[_a-zA-Z0-9]*",
    rb"isolated[_a-zA-Z0-9]*",
    rb"unit_order[_a-zA-Z0-9]*",
    rb"army_order[_a-zA-Z0-9]*",
    rb"current_order[_a-zA-Z0-9]*",
    rb"assigned_to[_a-zA-Z0-9]*",
    rb"IsInCombat[A-Za-z0-9_]*",
    rb"GetCombat[A-Za-z0-9_]*",
    rb"HasOrder[A-Za-z0-9_]*",
    rb"GetOrder[A-Za-z0-9_]*",
]

def cstr_at_fileoff(off):
    # back up
    lo=max(0,off-0)
    # if mid-string, walk back
    while off>0 and db[off-1] not in (0,) and 32<=db[off-1]<127:
        off-=1
        if off < lo-200: break
    end=db.find(b"\x00", off)
    s=db[off:end].decode("ascii","replace") if end!=-1 else ""
    return off,s

found={}
for pat in extra_pats:
    for m in re.finditer(pat, db):
        off,s=cstr_at_fileoff(m.start())
        if not (2<len(s)<=80): continue
        if not re.fullmatch(r"[A-Za-z0-9_.:<>]+", s) and " " in s and len(s)>40:
            continue
        rva=rva_of(off)
        found[(rva,s)]={"rva":hex(rva) if rva else None,"s":s}

# RTTI
rtti=[]
for m in re.finditer(rb"\.\?AV[ -~]{0,160}(?:Combat|Order|Supply|Theatre|ArmyGroup|FieldMarshal|Command)[ -~]{0,80}@@", db):
    rva=rva_of(m.start())
    s=m.group().decode("ascii","replace")
    # skip helpers/allocators unless short
    if "Allocator" in s or "Binder" in s or "Func_impl" in s or "DefineRegistry" in s:
        continue
    if len(s)<80:
        rtti.append({"rva":hex(rva) if rva else None,"s":s})

print("IDENTIFIERS")
for e in sorted(found.values(), key=lambda x: x["s"].lower()):
    s=e["s"]
    if s.startswith(".?AV") or "NDefines" in s or "Error" in s: continue
    print(e)

print("\nRTTI short")
# unique rtti
seen=set()
for e in rtti:
    if e["s"] in seen: continue
    seen.add(e["s"])
    print(e)

Path("research/t182_combat_order_strings.json").write_text(json.dumps({"ids":list(found.values()),"rtti":rtti}, indent=2)+"\n", encoding="utf-8")
print("wrote", len(found), "ids", len(rtti), "rtti")
