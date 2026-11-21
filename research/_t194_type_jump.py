from __future__ import annotations
import json, re, struct, sys
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
sys.path.insert(0, "calling")
from pe import PE

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
pe = PE(EXE)
cs = Cs(CS_ARCH_X86, CS_MODE_64)

rdata = next(s for s in pe.sections if s.name.startswith(".rdata"))
rblob = pe.data[rdata.raw_ptr:rdata.raw_ptr+rdata.raw_size]

asserts = []
for m in re.finditer(rb"GetOrderType\(\)[^\x00]{0,80}", rblob):
    s = m.group().decode("latin1", "replace")
    asserts.append({"rva": hex(rdata.virtual_address+m.start()), "s": s})

# Also ORDER_ typenames that look like enum names (short, no tooltip)
enumish = []
for m in re.finditer(rb"\x00(ORDER_(MOVE|INVASION|PARADROP|AREA_DEFENSE|OFFENSIVE_LINE|DEFENSIVE_LINE|FRONT|FRONTLINE|GARRISON|FALLBACK|RETREAT|ATTACK|NAVAL_INVASION)[A-Z0-9_]*)\x00", rblob):
    enumish.append({"rva": hex(rdata.virtual_address+m.start()+1), "s": m.group(1).decode()})

# unique short ORDER_ type-like (no COLOR, no TOOLTIP, no HINT, no CONF graphics)
shorts = []
for m in re.finditer(rb"\x00(ORDER_[A-Z0-9_]+)\x00", rblob):
    s = m.group(1).decode()
    if any(k in s for k in ("COLOR","TOOLTIP","HINT","CONF","FADE","SMOOTH","CAMERA","CLICK","HEADER","DESC","PLAYER","FRIEND","ASSIGNMENT","PLANNING","HOTKEY","CONNECT","PROV_","FRONT_MAX","FRONT_SMOOTH","MOVE_SMOOTH","GROUP_BAD","EXTRA","OUTLINE","NAME_EXHAUST","ACCESS","ALT_","ARMY_CAP","OF_CONVERSION","CONFLICT")):
        continue
    shorts.append({"rva": hex(rdata.virtual_address+m.start()+1), "s": s})

raw = pe.data[pe.rva_to_off(0xfcc818):pe.rva_to_off(0xfcc818)+12*4]
entries = []
for i in range(12):
    off = struct.unpack_from("<I", raw, i*4)[0]
    entries.append({"type": i+2, "entry": hex(off)})

def disasm(rva, n=0x200):
    blob = pe.data[pe.rva_to_off(rva):pe.rva_to_off(rva)+n]
    return list(cs.disasm(blob, rva))

def rip_strings(rva, nbytes=0x200):
    ins = disasm(rva, nbytes)
    out = []
    ins_txt = []
    for i in ins:
        ins_txt.append(f"0x{i.address:x}  {i.mnemonic} {i.op_str}")
        if i.mnemonic in ("lea", "mov") and "rip" in i.op_str:
            m = re.search(r"rip ([\+\-]) 0x([0-9a-f]+)", i.op_str)
            if not m:
                continue
            disp = int(m.group(2), 16)
            tgt = i.address + i.size + (disp if m.group(1)=="+" else -disp)
            try:
                b = pe.data[pe.rva_to_off(tgt):pe.rva_to_off(tgt)+80]
            except Exception:
                continue
            if b"\x00" in b:
                b = b.split(b"\x00",1)[0]
            if b and all(32 <= x < 127 or x in (9,10,13) for x in b) and len(b) >= 3:
                out.append({"at": hex(i.address), "tgt": hex(tgt), "s": b.decode("latin1")})
        if i.mnemonic == "ret" and i.address > rva:
            break
    return out, ins_txt

entry_detail = []
for e in entries:
    off = int(e["entry"], 16)
    strs, ins_txt = rip_strings(off, 0x220)
    entry_detail.append({"type": e["type"], "entry": e["entry"], "strings": strs, "ins": ins_txt[:30]})

# xref GetOrderType assert strings back to code
text = next(s for s in pe.sections if s.name.startswith(".text"))
tblob = pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]
# also search lea rip to assert RVAs
assert_xrefs = []
for a in asserts:
    rva = int(a["rva"], 16)
    # search lea/mov rip-relative: need to scan is hard; instead search immediate address in .text as 64-bit VA? 
    # common: lea rdx, [rip+disp] pointing at string
    # We'll scan .text for the 32-bit RVA displacement pattern is messy.
    # Search for the preferred-base VA as qword and also 32-bit rva
    va = pe.image_base + rva
    pat = struct.pack("<Q", va)
    pat32 = struct.pack("<I", rva)
    hits = []
    start = 0
    chunk = tblob
    while len(hits) < 8:
        j = chunk.find(pat, start)
        if j < 0:
            break
        hits.append(hex(text.virtual_address+j))
        start = j+1
    a["qword_hits"] = hits
    # Also find rip-relative: for each 7-byte lea (48 8d 15 / 48 8d 0d / 4c 8d 05 etc)
    # We'll do a targeted capstone around cmp [reg+0x30], imm later.

rec = {
    "asserts": asserts,
    "enumish": enumish,
    "short_order_tokens": shorts,
    "jump_table": entries,
    "entry_detail": entry_detail,
}
Path("research/t194_type_jump.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
print("asserts:")
for a in asserts:
    print(a)
print("\nshort tokens:")
for s in shorts:
    print(s)
print("\nenumish:")
for s in enumish:
    print(s)
print("\njump entries strings:")
for e in entry_detail:
    print(f"type {e['type']} {e['entry']} strings={e['strings']}")
    for ln in e["ins"][:15]:
        print("   ", ln)
