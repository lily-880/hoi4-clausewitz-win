"""Static string + RIP-relative xref helpers for PE32+ hoi4.exe."""
from __future__ import annotations

import struct
from typing import Dict, Iterable, List, Optional, Tuple

from pe import PE


def find_ascii(pe: PE, needle: bytes, section: str = ".rdata") -> List[int]:
    """Return RVAs of exact ASCII (or UTF-8) occurrences in a section (default .rdata)."""
    sec = next((s for s in pe.sections if s.name == section), None)
    if not sec:
        return []
    blob = pe.data[sec.raw_ptr : sec.raw_ptr + sec.raw_size]
    out = []
    start = 0
    while True:
        i = blob.find(needle, start)
        if i < 0:
            break
        out.append(sec.virtual_address + i)
        start = i + 1
    return out


def find_ascii_all(pe: PE, needle: bytes) -> List[int]:
    out = []
    for s in pe.sections:
        blob = pe.data[s.raw_ptr : s.raw_ptr + s.raw_size]
        start = 0
        while True:
            i = blob.find(needle, start)
            if i < 0:
                break
            out.append(s.virtual_address + i)
            start = i + 1
    return out


def rip_lea_xrefs(pe: PE, target_rva: int, max_hits: int = 64) -> List[dict]:
    """Find LEA r64, [rip+disp32] and MOV r64, [rip+disp32] that resolve to target_rva.

    Patterns (x86-64):
      48 8D 05/0D/15/1D/25/2D/35/3D  disp32   LEA r64, [rip+disp]
      48 8B 05/0D/15/1D/25/2D/35/3D  disp32   MOV r64, [rip+disp]
      4C 8D / 4C 8B similarly for r8-r15
    disp is relative to the *next* instruction (rip after the 7-byte insn).
    """
    text = next((s for s in pe.sections if s.name == ".text"), None)
    if not text:
        return []
    blob = pe.data[text.raw_ptr : text.raw_ptr + text.raw_size]
    hits = []
    # rex.w + 8D/8B + ModRM with mod=00 rm=101 (rip-relative) => ModRM in {0x05,0x0D,...,0x3D}
    for i in range(len(blob) - 7):
        b0, b1, b2 = blob[i], blob[i + 1], blob[i + 2]
        if b0 not in (0x48, 0x4C):
            continue
        if b1 not in (0x8D, 0x8B):
            continue
        if (b2 & 0xC7) != 0x05:  # mod=00, rm=101
            continue
        disp = struct.unpack_from("<i", blob, i + 3)[0]
        insn_rva = text.virtual_address + i
        next_rva = insn_rva + 7
        abs_rva = (next_rva + disp) & 0xFFFFFFFF
        # PE image usually < 4GB preferred; keep unsigned compare in image
        if abs_rva == target_rva:
            hits.append(
                {
                    "insn_rva": insn_rva,
                    "op": "lea" if b1 == 0x8D else "mov",
                    "rex": b0,
                    "modrm": b2,
                    "disp": disp,
                    "target_rva": target_rva,
                }
            )
            if len(hits) >= max_hits:
                break
    return hits


def data_pointer_slots(pe: PE, target_rva: int, max_hits: int = 32) -> List[int]:
    """Find .data / .rdata qwords that equal preferred_image_base + target_rva (relocated absolute).

    In the file on disk, absolute addresses are usually preferred ImageBase + RVA
    before relocation is applied at load. Searching for that absolute helps find
    vtable slots and global initializers.
    """
    abs_val = pe.image_base + target_rva
    needle = struct.pack("<Q", abs_val)
    hits = []
    for s in pe.sections:
        if s.name not in (".data", ".rdata"):
            continue
        blob = pe.data[s.raw_ptr : s.raw_ptr + s.raw_size]
        start = 0
        while True:
            i = blob.find(needle, start)
            if i < 0:
                break
            if i % 8 == 0:
                hits.append(s.virtual_address + i)
                if len(hits) >= max_hits:
                    return hits
            start = i + 1
    return hits
