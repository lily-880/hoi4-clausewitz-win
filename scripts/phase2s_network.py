"""Phase 2s4 — NetworkServer drain/post vs +0x40; finish Execute loop. RO."""
from __future__ import annotations
import os, struct, sys, json, re
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "calling"))
from process import Backend, find_pid
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

b = Backend(find_pid("hoi4.exe"))
base = b.image_base
md = Cs(CS_ARCH_X86, CS_MODE_64)
def rd(a,n): return b.read(a,n)

def dump(rva, size, label):
    print(f"\n######## {label} @ {hex(rva)} ########")
    for insn in md.disasm(rd(base+rva, size), base+rva):
        mark = ""
        if re.search(r"\+0x(40|58|60|68|a0|c8|d0|48|50|78|30|28)]", insn.op_str):
            mark = "  **"
        if insn.mnemonic == "call":
            mark += " CALL"
        print(f"{hex(insn.address-base)}: {insn.mnemonic} {insn.op_str}{mark}")
        if insn.mnemonic == "int3" and insn.address-base > rva+0x10:
            # only stop on int3 if we've progressed; skip early int3 in assert
            # for network drain use size limit instead
            pass
        if insn.address - base >= rva + size - 0x10:
            break

# Execute loop — larger, don't stop on int3
print("=== EXECUTE_LOOP continued (no int3 stop) ===")
count=0
for insn in md.disasm(rd(base+0x22c4710, 0x280), base+0x22c4710):
    mark=""
    if "0x50" in insn.op_str or "0x48" in insn.op_str or "0x78" in insn.op_str:
        mark=" **"
    if insn.mnemonic=="call": mark+=" CALL"
    print(f"{hex(insn.address-base)}: {insn.mnemonic} {insn.op_str}{mark}")
    count+=1
    if insn.mnemonic=="ret" and count>20:
        break

dump(0x23fb470, 0x300, "CNetworkServer DRAIN vt+0x30")
dump(0x23fa830, 0x280, "CNetworkServer POST vt+0x28")
dump(0x23f79f0, 0x200, "CNetworkServer CLEAR vt+0x48")

# Re-collect ALL Command@@ with army-ish names and non-abort Execute (full rescan narrow)
print("\n=== rescan army Command Execute ===")
ABORT=0x25c21e0
def find_cols(td):
    needle=struct.pack("<I", td); cols=[]
    for pos in range(0x2700000,0x3700000,0x100000):
        blob=rd(base+pos,0x100000); off=0
        while True:
            j=blob.find(needle,off)
            if j<0: break
            col=pos+j-0x0C
            try:
                sig=struct.unpack("<I", rd(base+col,4))[0]
            except Exception:
                off=j+1; continue
            if sig in (0,1): cols.append(col)
            off=j+1
    return cols
def find_vt(col):
    needle=struct.pack("<Q", base+col); vts=[]
    for pos in range(0x2700000,0x3700000,0x100000):
        blob=rd(base+pos,0x100000); off=0
        while True:
            j=blob.find(needle,off)
            if j<0: break
            vts.append(pos+j+8); off=j+1
    return vts

pat=re.compile(rb"\.?AVC\w*(Army|Front|Unit|Division|Order|Move|Retreat|Attack|Assign|Theatre|General|Admiral|Naval|Fleet|Ship|Wing|Air|Plane|Invasion|Embark|Convoy|Strike|Plan|Exercise|Reinforce|Deploy|Garrison|Selected|Hotkey|Combat|Mission)\w*Command@@")
# simpler: all *Command@@ then filter
army=[]
seen=set()
for pos in range(0x3100000, 0x3600000, 0x80000):
    blob=rd(base+pos,0x80000)
    off=0
    while True:
        j=blob.find(b"Command@@", off)
        if j<0: break
        start=j
        while start>0 and blob[start:start+4]!=b".?AV":
            start-=1
            if j-start>100:
                start=-1; break
        if start>=0:
            name=blob[start:j+9]
            try: ns=name.decode()
            except: off=j+1; continue
            if ns in seen:
                off=j+1; continue
            seen.add(ns)
            if not re.search(r"(Army|Front|Unit|Division|Order|Move|Retreat|Attack|Assign|Theatre|General|Admiral|Naval|Fleet|Ship|Wing|Air|Plane|Invasion|Embark|Convoy|Strike|Plan|Exercise|Reinforce|Deploy|Garrison|Selected|Hotkey|Combat|Mission|Retreat|Support)", ns, re.I):
                off=j+1; continue
            if re.search(r"(TriggerEntry|IsHighCommand|Tooltip|Gui|Button|IndustrialOrgTrait|String)", ns):
                off=j+1; continue
            td=pos+start-0x10
            for c in find_cols(td)[:3]:
                for vt in find_vt(c)[:2]:
                    s50=struct.unpack("<Q",rd(base+vt+0x50,8))[0]-base
                    s48=struct.unpack("<Q",rd(base+vt+0x48,8))[0]-base
                    if s50!=ABORT:
                        army.append({"name":ns,"vt":hex(vt),"Execute_0x50":hex(s50),"IsValid_0x48":hex(s48)})
                    break
                else:
                    continue
                break
        off=j+1

print(f"army commands with real Execute: {len(army)}")
for x in sorted(army, key=lambda z: z["name"])[:100]:
    print(f"  {x['name'][4:-2]} {x['Execute_0x50']}")

json.dump({
    "phase":"2s",
    "command_queue":"DISABLED",
    "network_drain":"0x23fb470",
    "network_post":"0x23fa830",
    "army_execute":army,
}, open(os.path.join(ROOT,"research","re-dumps","phase2s_network_army.json"),"w"), indent=2)
print("WROTE", len(army))
b.close()
