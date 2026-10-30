#!/usr/bin/env python3
"""Static Phase-2 offset scan against hoi4.exe (no running process required)."""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "calling"))

import config
from pe import PE
from msvc_rtti import catalog, demangle_simple
from stringscan import find_ascii_all, rip_lea_xrefs


def main():
    exe = os.environ.get("HOI4_EXE") or config.binary_path(required=True)
    # Prefer research dump copy if present
    dump = os.path.join(ROOT, "research", "re-dumps", "hoi4_1.19.4.exe")
    if os.path.isfile(dump):
        exe = dump
    print("Scanning", exe, file=sys.stderr)
    pe = PE(exe)
    cat = catalog(pe)
    # Also plain strings of interest
    plain = {}
    for s in (
        b"CGameState",
        b"CCommandQueue",
        b"CInGameIdler",
        b"CLandCombat",
        b"PostCommand",
        b"CanExecute",
    ):
        rvas = find_ascii_all(pe, s)
        plain[s.decode()] = {
            "rvas": [hex(r) for r in rvas[:20]],
            "xrefs_sample": [
                {**h, "insn_rva": hex(h["insn_rva"])}
                for r in rvas[:2]
                for h in rip_lea_xrefs(pe, r, max_hits=8)
            ][:16],
        }
    out = {
        "exe": exe,
        "image_base": hex(pe.image_base),
        "size_of_image": hex(pe.size_of_image),
        "rtti": {},
        "plain_strings": plain,
    }
    for name, info in cat.items():
        out["rtti"][name] = {
            "type_descriptors": [
                {**td, "name_rva": hex(td["name_rva"]), "td_rva": hex(td["td_rva"]), "demangled": demangle_simple(td["name"])}
                for td in info.get("type_descriptors", [])
            ],
            "cols": [hex(c) for c in info.get("cols", [])[:20]],
            "vtables": [
                {
                    "col_rva": hex(v["col_rva"]),
                    "col_ptr_slot": hex(v["col_ptr_slot"]),
                    "vtable_rva": hex(v["vtable_rva"]),
                }
                for v in info.get("vtables", [])[:20]
            ],
            "name_xrefs": [
                {**x, "insn_rva": hex(x["insn_rva"])} for x in info.get("name_xrefs", [])[:20]
            ],
        }
    json.dump(out, sys.stdout, indent=2)
    print(file=sys.stderr)
    # Write beside dump
    out_path = os.path.join(ROOT, "research", "re-dumps", "static_scan.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("Wrote", out_path, file=sys.stderr)


if __name__ == "__main__":
    main()
