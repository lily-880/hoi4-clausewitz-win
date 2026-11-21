# -*- coding: utf-8 -*-
from __future__ import annotations
import json, struct, sys
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

ROOT = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")
sys.path.insert(0, str(ROOT / "calling"))
from pe import PE
from mem import Proc, find_pid as mem_find_pid
from gamestate import detect_session
from province import resolve_province
from input_loaded_fields import LoadedReader, province_land_neighbors

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
OUT = ROOT / "research" / "t197_setpath_factory2.json"
TABLE = 0x35011E0
EXPECTED_PID = 12948
cs = Cs(CS_ARCH_X86, CS_MODE_64)


def find_rip_refs(pe, target_rva, scan_rva_start=0x1800000, scan_rva_end=0x1A00000):
    """Find lea/mov rip-relative that resolve to target_rva in a .text window."""
    hits = []
    off0 = pe.rva_to_off(scan_rva_start)
    blob = pe.data[off0:pe.rva_to_off(scan_rva_end)]
    # crude: search for rel32 such that instr_end + rel = target
    # lea r64, [rip+rel] is 48 8d xx rel32, or 4c 8d, or 8d.
    # Also lea rax,[rip+disp] 48 8D 05 rel32
    patterns_prefixes = [
        bytes.fromhex("488D05"),  # lea rax,[rip+d]
        bytes.fromhex("488D0D"),  # lea rcx
        bytes.fromhex("488D15"),  # lea rdx
        bytes.fromhex("488D1D"),  # lea rbx
        bytes.fromhex("4C8D05"),  # lea r8
        bytes.fromhex("4C8D0D"),
        bytes.fromhex("4C8D15"),
        bytes.fromhex("4C8D1D"),
        bytes.fromhex("488D35"),  # lea rsi
        bytes.fromhex("488D3D"),  # lea rdi
    ]
    for pref in patterns_prefixes:
        start = 0
        while True:
            i = blob.find(pref, start)
            if i < 0:
                break
            if i + len(pref) + 4 > len(blob):
                break
            rel = struct.unpack_from("<i", blob, i + len(pref))[0]
            inst_rva = scan_rva_start + i
            end_rva = inst_rva + len(pref) + 4
            if end_rva + rel == target_rva:
                hits.append({"rva": hex(inst_rva), "pref": pref.hex(), "rel": rel})
            start = i + 1
            if len(hits) > 40:
                return hits
    return hits


def factory_index_for(pe, fn_rva):
    tab_off = pe.rva_to_off(TABLE)
    # compare both VA and RVA
    va = 0x140000000 + fn_rva
    blob = pe.data[tab_off:tab_off + 8000 * 8]
    hits = []
    for i in range(8000):
        q = struct.unpack_from("<Q", blob, i * 8)[0]
        if q in (fn_rva, va):
            hits.append({"idx": i, "type_id": i + 0x2328, "stored": hex(q)})
    return hits


def disasm(pe, rva, n=0x80):
    off = pe.rva_to_off(rva)
    return [f"0x{i.address:x}  {i.mnemonic} {i.op_str}" for i in cs.disasm(pe.data[off:off+n], rva)]


def find_fn_start(pe, rva):
    """Walk back to likely function start using .pdata if possible."""
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


def main():
    pe = PE(EXE)
    out = {"authorized_by": ["pt183u", "pt180u"]}
    targets = {"vt_start_0x2a84fe0": 0x2A84FE0, "isvalid_slot_0x2a85028": 0x2A85028}
    for name, tgt in targets.items():
        refs = find_rip_refs(pe, tgt, 0x1000000, 0x1C00000)
        recs = []
        for r in refs:
            inst = int(r["rva"], 16)
            start, end = find_fn_start(pe, inst)
            rec = {**r, "fn_start": hex(start) if start else None, "fn_end": hex(end) if end else None}
            if start:
                rec["in_table"] = factory_index_for(pe, start)
                rec["fn_head"] = disasm(pe, start, 0xA0)
            recs.append(rec)
        out[name] = recs

    # also search a bit more broadly if empty: whole .text for lea to 0x2a84fe0
    if not out["vt_start_0x2a84fe0"] and not out["isvalid_slot_0x2a85028"]:
        text = next(s for s in pe.sections if s.name.startswith(".text"))
        out["fallback_note"] = "no lea in 0x10xxxx-0x1cxxxx; scanning full .text"
        refs = find_rip_refs(pe, 0x2A84FE0, text.virtual_address, text.virtual_address + text.virtual_size)
        out["fulltext_refs_n"] = len(refs)
        out["fulltext_refs"] = refs[:20]

    # neighbors via resolve_province pointer + land neighbors
    pid = mem_find_pid("hoi4.exe")
    out["pid"] = pid
    if pid == EXPECTED_PID:
        p = Proc(pid)
        try:
            session = detect_session(p, pe)
            gs = int(session["signals"]["gs_ptr"], 16)

            def rtti(a):
                return None
            r = LoadedReader(p.read, rtti)
            neigh = {}
            for prov in (12757, 2072, 7944, 5097):
                try:
                    ptr = resolve_province(p, prov, image_base=p.base, gs=gs)
                    if isinstance(ptr, dict):
                        ptr = ptr.get("ptr") or ptr.get("province") or ptr
                    if isinstance(ptr, str):
                        ptr = int(ptr, 16)
                    lands, ev = province_land_neighbors(r, ptr)
                    neigh[str(prov)] = {"ptr": hex(ptr) if isinstance(ptr, int) else ptr, "land": lands}
                except Exception as e:
                    neigh[str(prov)] = {"error": str(e)}
            out["neighbors"] = neigh
        finally:
            p.close()

    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    compact = {k: out[k] for k in out if k != "neighbors"}
    compact["neighbors"] = out.get("neighbors")
    print(json.dumps(compact, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
