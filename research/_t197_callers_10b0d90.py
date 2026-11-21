# -*- coding: utf-8 -*-
from __future__ import annotations
import json, struct, sys
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

ROOT = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")
sys.path.insert(0, str(ROOT / "calling"))
from pe import PE

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
OUT = ROOT / "research" / "t197_callers_10b0d90.json"
cs = Cs(CS_ARCH_X86, CS_MODE_64)
TARGET = 0x10B0D90


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


def disasm(pe, rva, n=0x80):
    off = pe.rva_to_off(rva)
    return [f"0x{i.address:x}  {i.mnemonic} {i.op_str}" for i in cs.disasm(pe.data[off:off+n], rva)]


def main():
    pe = PE(EXE)
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
        inst_rva = base + i
        end = inst_rva + 5
        if end + rel == TARGET:
            fn_s, fn_e = find_fn(pe, inst_rva)
            hits.append({
                "call_at": hex(inst_rva),
                "fn_start": hex(fn_s) if fn_s else None,
                "fn_end": hex(fn_e) if fn_e else None,
            })
        start = i + 1
        if len(hits) > 80:
            break
    # unique functions
    fns = {}
    for h in hits:
        k = h["fn_start"]
        fns.setdefault(k, []).append(h["call_at"])
    recs = []
    for fn, calls in fns.items():
        recs.append({
            "fn": fn,
            "calls": calls,
            "head": disasm(pe, int(fn, 16), 0x60) if fn else None,
        })
    out = {"n_hits": len(hits), "hits": hits, "functions": recs}

    # NewRoot IsValid
    lines = disasm(pe, 0x18DF5E0, 0x200)
    out["newroot_isvalid"] = lines
    (ROOT / "research/_t197_clip_COrderNewRootCommand_isvalid_0x18df5e0.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "n_hits": len(hits),
        "functions": [{"fn": r["fn"], "calls": r["calls"], "head": r["head"][:20]} for r in recs],
        "newroot_isvalid": lines[:80],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
