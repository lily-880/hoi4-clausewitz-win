# -*- coding: utf-8 -*-
from __future__ import annotations
import json, struct, sys
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

ROOT = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")
sys.path.insert(0, str(ROOT / "calling"))
from pe import PE

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
OUT = ROOT / "research" / "t197_identify_path_cmds.json"
TABLE = 0x35011E0
cs = Cs(CS_ARCH_X86, CS_MODE_64)


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


def disasm(pe, rva, n):
    off = pe.rva_to_off(rva)
    return [f"0x{i.address:x}  {i.mnemonic} {i.op_str}" for i in cs.disasm(pe.data[off:off+n], rva)]


def find_rip_to(pe, target, scan_start=0x18C0000, scan_end=0x1900000):
    off0 = pe.rva_to_off(scan_start)
    blob = pe.data[off0:pe.rva_to_off(scan_end)]
    hits = []
    # lea r64, [rip+rel] 48 8d 05 / 0d / 15 / 1d / 35 / 3d and 4c 8d 05 etc
    for pref in (bytes.fromhex("488D05"), bytes.fromhex("488D0D"), bytes.fromhex("488D15"),
                 bytes.fromhex("488D1D"), bytes.fromhex("4C8D05"), bytes.fromhex("4C8D0D"),
                 bytes.fromhex("488D35"), bytes.fromhex("488D3D")):
        start = 0
        while True:
            i = blob.find(pref, start)
            if i < 0 or i + len(pref) + 4 > len(blob):
                break
            rel = struct.unpack_from("<i", blob, i + len(pref))[0]
            inst = scan_start + i
            if inst + len(pref) + 4 + rel == target:
                fn_s, fn_e = find_fn(pe, inst)
                hits.append({"at": hex(inst), "fn": hex(fn_s) if fn_s else None})
            start = i + 1
    return hits


def table_index(pe, fn_rva):
    tab = pe.data[pe.rva_to_off(TABLE):pe.rva_to_off(TABLE) + 8000 * 8]
    va = 0x140000000 + fn_rva
    hits = []
    for i in range(8000):
        q = struct.unpack_from("<Q", tab, i * 8)[0]
        if q in (fn_rva, va):
            hits.append({"idx": i, "type_id": i + 0x2328})
    return hits


def rtti_name(pe, vt_rva):
    # typical: vt[-8] -> col, col+0x10 -> type desc, +0x14 or similar type name
    try:
        col = struct.unpack_from("<Q", pe.data, pe.rva_to_off(vt_rva - 8))[0]
        if col > 0x140000000:
            col -= 0x140000000
        # MSVC COL: +0x10 = type descriptor VA
        td = struct.unpack_from("<Q", pe.data, pe.rva_to_off(col + 0x10))[0]
        if td > 0x140000000:
            td -= 0x140000000
        # type desc: +0x10 name
        name = pe.data[pe.rva_to_off(td + 0x10):pe.rva_to_off(td + 0x10) + 80]
        return name.split(b"\x00", 1)[0].decode("latin1", "replace")
    except Exception as e:
        return f"err:{e}"


def main():
    pe = PE(EXE)
    out = {}
    for rva, n in ((0x18D1150, 0x280), (0x18D6660, 0x280)):
        lines = disasm(pe, rva, n)
        (ROOT / f"research/_t197_clip_fn_{rva:x}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        # find vtable refs: search for this execute rva in rdata as VA
        needle = struct.pack("<Q", 0x140000000 + rva)
        rdata = next(s for s in pe.sections if s.name.startswith(".rdata"))
        rb = pe.data[rdata.raw_ptr:rdata.raw_ptr + rdata.raw_size]
        slots = []
        s = 0
        while True:
            i = rb.find(needle, s)
            if i < 0:
                break
            slot = rdata.virtual_address + i
            # assume execute is often slot after isvalid, so vt might start earlier
            slots.append(hex(slot))
            s = i + 1
        rec = {"execute": hex(rva), "execute_slots": slots, "head": lines[:70],
               "calls": [ln for ln in lines if "  call " in ln][:30]}
        # for each slot, try rtti from 8-byte aligned starts around it
        names = []
        for slot_h in slots:
            slot = int(slot_h, 16)
            for back in range(0, 0x80, 8):
                vt = slot - back
                name = rtti_name(pe, vt)
                if name.startswith(".?AV"):
                    # find isvalid as previous slot if back==8
                    isvalid = struct.unpack_from("<Q", pe.data, pe.rva_to_off(slot - 8))[0]
                    if isvalid > 0x140000000:
                        isvalid -= 0x140000000
                    names.append({"vt": hex(vt), "name": name, "isvalid": hex(isvalid), "back": back})
                    break
        rec["rtti"] = names
        # factory: lea to each vt
        factories = []
        for nrec in names:
            vt = int(nrec["vt"], 16)
            refs = find_rip_to(pe, vt)
            for r in refs:
                fn = int(r["fn"], 16) if r["fn"] else None
                item = {**r, "in_table": table_index(pe, fn) if fn else [],
                        "fn_head": disasm(pe, fn, 0x70) if fn else None}
                factories.append(item)
        rec["factories"] = factories
        out[hex(rva)] = rec

    # live NewRoot sentinel addresses
    # already know 0x33EB2A0 is 0,0 — also confirm NewRoot rip
    out["newroot_isvalid_rip_note"] = "0x18df5fc+0x1b0bca8 and next cmp use same 0x33EB2A0/A4 as SetPath"

    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    compact = {}
    for k, rec in out.items():
        if not isinstance(rec, dict) or "execute" not in rec:
            compact[k] = rec
            continue
        compact[k] = {
            "rtti": rec["rtti"],
            "calls": rec["calls"],
            "head": rec["head"][:40],
            "factories": [
                {"at": f.get("at"), "fn": f.get("fn"), "in_table": f.get("in_table"), "fn_head": (f.get("fn_head") or [])[:25]}
                for f in rec["factories"]
            ],
        }
    print(json.dumps(compact, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
