# Disassemble CArmyLeader writer around +0x1048 / tokens
from __future__ import annotations
import json, struct, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"calling"))
from pe import PE

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
pe = PE(EXE)

# t183 cited 0xc7e8c0; 1.19.5 likely +0x70
candidates = [0xC7E8C0, 0xC7E930]
# also search for mov that uses 0x1048 near writer
# I'll dump pdata for both and a window, and scan .text for "cmp/mov [reg+0x1048]" in a known function

def pdata_fn(rva):
    # walk exception dir
    # reuse simple: just read bytes and capstone if available
    return None

try:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_64
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    md.detail = False
except Exception as e:
    print("NO_CAPSTONE", e)
    md = None

# find function bounds via pdata
# PE exception directory
def find_pdata(pe, rva):
    # try common helper
    for name in dir(pe):
        if "pdata" in name.lower() or "unwind" in name.lower() or "runtime" in name.lower():
            print("pe attr", name)

# parse IMAGE_DIRECTORY_ENTRY_EXCEPTION = 3
import pefile
# maybe pe.pe or pe.data
print("PE fields sample", [a for a in dir(pe) if not a.startswith("_")][:40])

# fallback: raw search around both RVAs
text = pe.section_bytes(".text") if hasattr(pe, "section_bytes") else None

# Use pe.read or file
data = Path(EXE).read_bytes()
# read pe headers for image base and section
import struct as st

def rva_to_off(pe_obj, rva):
    # use pe.py API
    if hasattr(pe_obj, "rva_to_offset"):
        return pe_obj.rva_to_offset(rva)
    if hasattr(pe_obj, "file_offset"):
        return pe_obj.file_offset(rva)
    return None

# inspect API
print("has", {n: hasattr(pe, n) for n in ("rva_to_offset","file_offset","read","section","sections","data","buf")})
