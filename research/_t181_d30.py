import json, os, sys, struct, re, bisect
from pathlib import Path
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"
sys.path.insert(0, str(Path("calling").resolve()))
from mem import Proc, find_pid
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

live=json.loads(Path("research/t180_landindex_and_edges.json").read_text(encoding="utf-8"))
has=set()
for p in live["provinces"]:
    if any(e["b10"] in (2,3) for e in p["edges"]):
        has.add(p["province_id"])

proc=Proc(find_pid("hoi4.exe"))
try:
    print("pid b8+0x20 .. +0x50")
    for rec in live["provinces"]:
        b8=int(rec["b8"],16)
        blob=proc.read(b8+0x20, 0x40)
        fields={hex(off):struct.unpack_from("<I", blob, off-0x20)[0] for off in range(0x20,0x50,4)}
        print(rec["province_id"], "river" if rec["province_id"] in has else "plain", fields, "bytes30-37", blob[0x10:0x18].hex())
finally:
    proc.close()

# static: writes to [reg+0x30] / [reg+0x34] in adjacency parser 0xab3660 and nearby
pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
# search in ab3660 clip first
text=Path("research/_t180_clip_0xab3660.txt").read_text(encoding="utf-8")
print("===== ab3660 ins with 0x30/0x34 =====")
for l in text.splitlines():
    if "+ 0x30]" in l or "+ 0x34]" in l or "+ 0x2c]" in l or "+ 0x44]" in l:
        print(l)
