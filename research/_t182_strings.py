import sys, re, json, struct
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

pats = [
    b"in_combat", b"InCombat", b"is_in_combat", b"in combat",
    b"current_combat", b"GetCombat", b"has_combat", b"combat_id",
    b"in_supply", b"isolated", b"supply_ratio", b"current_supply",
    b"army_current_supply", b"max_supply", b"out_of_supply",
    b"unit_order", b"UnitOrder", b"order_type", b"CUnitOrder",
    b"assigned_to", b"AssignedTo", b"army_group_id",
    b"is_moving", b"on_move", b"strategic_redeploy",
    b"CCombat", b"GS_COMBATS", b"combats",
]
# extract unique C-strings containing these
found=[]
seen=set()
for pat in pats:
    for m in re.finditer(pat, db, re.I):
        # expand to C string
        start=m.start()
        # walk back to previous NUL a bit
        lo=max(0, start-80)
        chunk=db[lo:m.end()+80]
        # find string bounds
        rel=start-lo
        a=chunk.rfind(b"\x00", 0, rel)+1
        b=chunk.find(b"\x00", rel)
        s=chunk[a:b].decode("latin1","replace") if b!=-1 else chunk[a:a+80].decode("latin1","replace")
        if len(s)<3 or len(s)>120: continue
        if not all(32<=ord(c)<127 or c in "\n\t" for c in s): continue
        rva=rva_of(lo+a)
        key=(rva,s)
        if key in seen: continue
        seen.add(key)
        found.append({"rva":hex(rva) if rva is not None else None, "s":s})

# sort and print most relevant
def score(e):
    s=e["s"].lower()
    return (0 if any(k in s for k in ("in_combat","is_in_combat","current_combat","in_supply","supply_ratio","isolated","unit_order","assigned_to","out_of_supply","army_current")) else 1, s)
found.sort(key=score)
print("count", len(found))
for e in found:
    sl=e["s"].lower()
    if any(k in sl for k in ("combat","supply","order","isolated","assigned","redeploy","in_supply","path","idle","moving")):
        # skip noisy lua errors unless short name
        if "error reading" in sl or "is not a lua" in sl: 
            if "nsupply" in sl or "nmilitary" in sl:
                if e["s"].isupper() or len(e["s"])<40:
                    print(e)
            continue
        print(e)
