import sys,re
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")

all_names=set()
for s in pe.sections:
    blob=pe.read_rva(s.virtual_address, s.virtual_size) or b""
    for m in re.finditer(rb"\.\?AV[A-Za-z0-9_@]+", blob):
        all_names.add(m.group().decode("latin1"))
print("RTTI total", len(all_names))
for n in sorted(all_names):
    if any(k.lower() in n.lower() for k in ("alert","crisis","encirc","fog","spotted","visibility")):
        print(" ", n)

print("\n=== encirclement / crisis cstrings ===")
rdata=[s for s in pe.sections if s.name==".rdata"][0]
rblob=pe.read_rva(rdata.virtual_address, rdata.virtual_size) or b""
seen=set()
for m in re.finditer(rb".{0,20}encircl[a-z_]*", rblob, re.I):
    a=m.start()
    while a>0 and 32<=rblob[a-1]<127: a-=1
    b=m.end()
    while b<len(rblob) and 32<=rblob[b]<127: b+=1
    s=rblob[a:b].decode("latin1")
    if s in seen: continue
    seen.add(s)
    if "Error reading" in s or "no lua" in s: continue
    print(f"  0x{rdata.virtual_address+a:x} {s[:200]}")
print("encirc strings", len(seen))

print("\n=== crisis cstrings ===")
seen=set()
for m in re.finditer(rb".{0,15}crisis[a-z_]*", rblob, re.I):
    a=m.start()
    while a>0 and 32<=rblob[a-1]<127: a-=1
    b=m.end()
    while b<len(rblob) and 32<=rblob[b]<127: b+=1
    s=rblob[a:b].decode("latin1")
    if s in seen: continue
    seen.add(s)
    if "Error reading" in s or "no lua" in s: continue
    print(f"  0x{rdata.virtual_address+a:x} {s[:200]}")
