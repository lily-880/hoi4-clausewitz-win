# -*- coding: utf-8 -*-
from __future__ import annotations
import json, struct, sys
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

ROOT = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")
sys.path.insert(0, str(ROOT / "calling"))
from pe import PE

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
cs = Cs(CS_ARCH_X86, CS_MODE_64)
OUT = ROOT / "research" / "t197_xref_path_helpers.json"


def find_fn(pe, rva):
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
    return None, None


def callers(pe, target):
    text = next(s for s in pe.sections if s.name.startswith(".text"))
    blob = pe.data[text.raw_ptr:text.raw_ptr + text.raw_size]
    base = text.virtual_address
    hits = []
    start = 0
    while True:
        i = blob.find(b"\xE8", start)
        if i < 0 or i + 5 > len(blob):
            break
        rel = struct.unpack_from("<i", blob, i + 1)[0]
        inst = base + i
        if inst + 5 + rel == target:
            fn_s, fn_e = find_fn(pe, inst)
            hits.append({"at": hex(inst), "fn": hex(fn_s) if fn_s else None})
        start = i + 1
        if len(hits) > 40:
            break
    return hits


def disasm(pe, rva, n=0x40):
    off = pe.rva_to_off(rva)
    return [f"0x{i.address:x}  {i.mnemonic} {i.op_str}" for i in cs.disasm(pe.data[off:off+n], rva)]


def main():
    pe = PE(EXE)
    out = {}
    for tgt in (0x18D6660, 0x18D1150, 0xC41720, 0xC41B60):
        hits = callers(pe, tgt)
        recs = []
        for h in hits:
            rec = dict(h)
            if h["fn"]:
                rec["head"] = disasm(pe, int(h["fn"], 16), 0x30)
            recs.append(rec)
        out[hex(tgt)] = recs
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
