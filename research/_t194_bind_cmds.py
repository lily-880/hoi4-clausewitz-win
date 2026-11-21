from __future__ import annotations
import json, struct, sys, re
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
sys.path.insert(0, "calling")
from pe import PE
from mem import Proc, find_pid as mem_find_pid

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
TABLE = 0x35011E0
pe = PE(EXE)
cs = Cs(CS_ARCH_X86, CS_MODE_64)
p = Proc(mem_find_pid("hoi4.exe"))
base = p.base

def find_fn(rva):
    pdata = next(s for s in pe.sections if s.name.startswith(".pdata"))
    raw = pe.data[pdata.raw_ptr:pdata.raw_ptr + pdata.raw_size]
    n = len(raw) // 12
    lo, hi = 0, n - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        b, e, u = struct.unpack_from("<III", raw, mid * 12)
        if rva < b:
            hi = mid - 1
        elif rva >= e:
            lo = mid + 1
        else:
            return b, e
    return None

def pe_off_to_rva(off):
    for s in pe.sections:
        if s.raw_ptr <= off < s.raw_ptr + s.raw_size:
            return s.virtual_address + (off - s.raw_ptr)
    return None

def find_vt(name):
    needle = (".?AV" + name + "@@").encode("ascii")
    data = pe.data
    rvas = []
    start = 0
    while True:
        i = data.find(needle, start)
        if i < 0:
            break
        rvas.append(pe_off_to_rva(i))
        start = i + 1
    vts = []
    rdata = [s for s in pe.sections if s.name.startswith(".rdata") or s.name.startswith(".data")]
    for str_rva in rvas:
        if str_rva is None:
            continue
        typedecl = str_rva - 0x10
        target = struct.pack("<I", typedecl)
        for s in rdata:
            chunk = data[s.raw_ptr:s.raw_ptr + s.raw_size]
            off = 0
            while True:
                j = chunk.find(target, off)
                if j < 0:
                    break
                if j >= 0x0C:
                    col_rva = s.virtual_address + (j - 0x0C)
                    va = pe.image_base + col_rva
                    needle2 = struct.pack("<Q", va)
                    for s2 in rdata:
                        chunk2 = data[s2.raw_ptr:s2.raw_ptr + s2.raw_size]
                        k = 0
                        while True:
                            m = chunk2.find(needle2, k)
                            if m < 0:
                                break
                            vts.append(s2.virtual_address + m + 8)
                            k = m + 1
                off = j + 1
    return sorted(set(vts))

def slots(vt, n=16):
    raw = pe.data[pe.rva_to_off(vt):pe.rva_to_off(vt) + n * 8]
    out = []
    for i in range(n):
        q = struct.unpack_from("<Q", raw, i * 8)[0]
        rva = q - pe.image_base if pe.image_base <= q < pe.image_base + pe.size_of_image else None
        fn = find_fn(rva) if rva else None
        out.append({
            "slot": i,
            "rva": hex(rva) if rva else hex(q),
            "fn": (hex(fn[0]), hex(fn[1]), fn[1] - fn[0]) if fn else None,
        })
    return out

def factory(idx):
    slot = struct.unpack("<Q", p.read(base + TABLE + idx * 8, 8))[0]
    if not (base <= slot < base + p.image_size):
        return None, None, None
    rva = slot - base
    head = pe.data[pe.rva_to_off(rva):pe.rva_to_off(rva) + 16]
    size = None
    for i in range(0, 12):
        if head[i] == 0xB9:
            size = struct.unpack_from("<I", head, i + 1)[0]
            break
    return rva, head.hex(), size

# scan factory table for a vtable pointer appearing in the first 0x80 of a factory function
def find_idx_by_vt(vt_rva, max_idx=9000):
    needle = struct.pack("<Q", pe.image_base + vt_rva)
    hits = []
    # read table in one go
    table = p.read(base + TABLE, max_idx * 8)
    for idx in range(max_idx):
        slot = struct.unpack_from("<Q", table, idx * 8)[0]
        if not (base <= slot < base + p.image_size):
            continue
        rva = slot - base
        try:
            blob = pe.data[pe.rva_to_off(rva):pe.rva_to_off(rva) + 0x80]
        except Exception:
            continue
        if needle in blob:
            hits.append(idx)
            if len(hits) >= 3:
                break
    return hits

KNOWN = {
    "COrderExecuteCommand": 3352,
    "COrderAssignCommand": 3350,
    "COrderNewFrontCommand": 4095,
    "COrderNewFallbackCommand": 4271,
    "CSetArmyLeaderCommand": 3369,
}

names = [
    "COrderSetPathCommand",
    "COrderAssignCommand",
    "COrderExecuteCommand",
    "CPauseGame",
    "CCreateAreaDefenseCommand",
    "COrderNewFrontCommand",
    "COrderNewFallbackCommand",
    "CSetArmyLeaderCommand",
    "CCreateUnitLeaderCommand",
]

out = {}
for name in names:
    vts = find_vt(name)
    idx = KNOWN.get(name)
    if idx is None and vts:
        hits = find_idx_by_vt(vts[0])
        idx = hits[0] if hits else None
        idx_search = hits
    else:
        idx_search = None
    rec = {"idx": idx, "vts": [hex(v) for v in vts], "idx_search": idx_search}
    if idx is not None:
        rva, head, size = factory(idx)
        rec.update({"factory": hex(rva) if rva is not None else None, "head": head, "size": size})
    if vts:
        rec["slots"] = {hex(v): slots(v) for v in vts[:2]}
    out[name] = rec
    print(name, {k: rec[k] for k in rec if k != "slots"})

# disasm IsValid/Execute
def dump(rva, n, title, stop_ret=False):
    lines = []
    blob = pe.data[pe.rva_to_off(rva):pe.rva_to_off(rva) + n]
    for i in cs.disasm(blob, rva):
        lines.append(f"{hex(i.address)}  {i.mnemonic} {i.op_str}")
        if stop_ret and i.mnemonic == "ret" and i.address > rva + 0x20:
            break
    Path(f"research/_t194_clip_{title}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return lines

clips = {}
for name, rec in out.items():
    if not rec.get("vts"):
        continue
    sl = rec["slots"][rec["vts"][0]]
    isv = int(sl[9]["rva"], 16)
    exe = int(sl[10]["rva"], 16)
    rec["isvalid"] = hex(isv)
    rec["execute"] = hex(exe)
    li = dump(isv, 0x280, f"{name}_isvalid_{hex(isv)}", stop_ret=True)
    le = dump(exe, 0x300, f"{name}_execute_{hex(exe)}", stop_ret=False)
    clips[name] = {"isvalid_head": li[:60], "execute_head": le[:80]}
    print(f"\n======= {name} IsValid {hex(isv)} =====")
    for l in li[:50]:
        print(l)
    print(f"\n======= {name} Execute {hex(exe)} head =====")
    for l in le[:40]:
        print(l)

Path("research/t194_bind_cmds.json").write_text(json.dumps({"cmds": out, "clips_head": clips}, indent=2) + "\n", encoding="utf-8")
p.close()
print("\nWROTE research/t194_bind_cmds.json")
