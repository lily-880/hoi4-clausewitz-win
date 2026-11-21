# research/_t191_rtti_move_vts.py — static+live RTTI for Move factory types on 1.19.5
from __future__ import annotations
import json, struct, sys
from pathlib import Path

sys.path.insert(0, "calling")
from pe import PE
from mem import Proc, find_pid
from gamestate import _rtti_name_from_vtable
from process import Backend
import move_order as mo
import cancel_order as co
import post_abi

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
WANT = {
    "CArmy",
    "CMoveCommand",
    "CUnitMoveAction",
    "CCancelMovementCommand",
    "CStrategicRedeploymentCommand",
    "CUnitStrategicMoveAction",
    "CSupportAttackCommand",
}


def rtti_complete_object_locator_vts(pe: PE):
    """Find vtables by scanning for RTTI CompleteObjectLocator references in the executable image.

    MSVC x64: vtable[-1] is COL*; COL+0x0C is type descriptor RVA (or VA-relative).
    We reuse _rtti_name_from_vtable which expects vt RVA.
    """
    # Scan .rdata for possible vtable starts by trying every 8-byte aligned pointer
    # into .text, then asking _rtti_name_from_vtable. That's huge. Better: search
    # type descriptor strings and walk back.
    data = pe.data
    found = {}
    # Search decorated names
    needles = {name: (".?AV" + name + "@@").encode("ascii") for name in WANT}
    hits = {name: [] for name in WANT}
    for name, needle in needles.items():
        start = 0
        while True:
            i = data.find(needle, start)
            if i < 0:
                break
            hits[name].append(i)
            start = i + 1
    return {k: [pe_off_to_rva(pe, off) for off in v] for k, v in hits.items()}, hits


def pe_off_to_rva(pe, off):
    for s in pe.sections:
        if s.raw_ptr <= off < s.raw_ptr + s.raw_size:
            return s.virtual_address + (off - s.raw_ptr)
    return None


def find_vtables_for_typedef_rvas(pe, typedef_rvas):
    """COL references TypeDescriptor. Vtable is preceded by COL pointer."""
    # Build set of TypeDescriptor RVAs
    # MSVC 64-bit TypeDescriptor often starts 0x10 before the name string
    # (vfptr, spare, name). The string rva is typedef_rva; typedecl at string-0x10.
    data = pe.data
    results = {}
    # collect all 32-bit RVA references to typedecl
    # map rva -> file off
    def rva_to_off(rva):
        return pe.rva_to_off(rva)

    for name, rvas in typedef_rvas.items():
        vts = []
        for str_rva in rvas:
            if str_rva is None:
                continue
            typedecl_rva = str_rva - 0x10
            # search .rdata for a COL that contains typedecl_rva as a dword
            # COL layout: sig(4), offset(4), cdOffset(4), pTypeDescriptor(4 or 8), pClassDescriptor(4)
            # On x64 with /RTTI, these are often RVAs (32-bit) when signature is 1.
            target = struct.pack("<I", typedecl_rva)
            start = 0
            # only search rdata
            rdata = [s for s in pe.sections if s.name.startswith(".rdata") or s.name.startswith(".data")]
            for s in rdata:
                chunk = data[s.raw_ptr:s.raw_ptr + s.raw_size]
                off = 0
                while True:
                    j = chunk.find(target, off)
                    if j < 0:
                        break
                    # possible pTypeDescriptor at COL+0x0C
                    if j >= 0x0C and (j - 0x0C) % 4 == 0:
                        col_off = s.raw_ptr + (j - 0x0C)
                        col_rva = s.virtual_address + (j - 0x0C)
                        sig = struct.unpack_from("<I", data, col_off)[0]
                        # look for a pointer to this COL immediately before a vtable
                        col_rva_pack = struct.pack("<I", col_rva)
                        # search for 64-bit VA would need image base; also 32-bit RVA
                        # In PE, vtable[-8] often stores the image-base-relative? On MSVC x64,
                        # it's a 64-bit VA in the dumped image: image_base + col_rva
                        va = pe.image_base + col_rva
                        needle = struct.pack("<Q", va)
                        for s2 in rdata:
                            chunk2 = data[s2.raw_ptr:s2.raw_ptr + s2.raw_size]
                            k = 0
                            while True:
                                m = chunk2.find(needle, k)
                                if m < 0:
                                    break
                                # vtable starts 8 bytes after this COL pointer
                                vt_rva = s2.virtual_address + m + 8
                                vts.append({"vt_rva": hex(vt_rva), "col_rva": hex(col_rva), "sig": sig, "typedef_rva": hex(typedecl_rva)})
                                k = m + 1
                    off = j + 1
        # unique
        uniq = []
        seen = set()
        for item in vts:
            if item["vt_rva"] not in seen:
                seen.add(item["vt_rva"])
                uniq.append(item)
        results[name] = uniq
    return results


def main():
    pe = PE(EXE)
    typedef_rvas, raw_offs = rtti_complete_object_locator_vts(pe)
    vts = find_vtables_for_typedef_rvas(pe, typedef_rvas)
    out = {
        "image_base_preferred": hex(pe.image_base),
        "typedef_rvas": {k: [hex(x) if x is not None else None for x in v] for k, v in typedef_rvas.items()},
        "vtables": vts,
        "move_order_constants": {
            "ARMY_VT": hex(mo.ARMY_VT),
            "MOVE_VT": hex(mo.MOVE_VT),
            "ACTION_VT": hex(mo.ACTION_VT),
            "FACTORY_RVA": hex(mo.FACTORY_RVA),
            "CANCEL_VT": hex(co.CANCEL_VT),
            "CANCEL_FACTORY": hex(co.FACTORY_RVA),
        },
    }
    Path("research/t191_rtti_move_vts.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
