#!/usr/bin/env python3
"""Phase 2o string/soft-call hunt for FN_CMD_QUEUE_POST. READ-ONLY. Never post."""
from __future__ import annotations

import json
import os
import struct
import sys
from collections import Counter
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "calling"))

import config
from pe import PE
from stringscan import find_ascii_all, rip_lea_xrefs

NEEDLES = [
    b"Failed to execute",
    b"command queue",
    b"CommandQueue",
    b"PostCommand",
    b"AddCommand",
    b"ExecuteCommand",
    b"queue command",
    b"Queued command",
    b"CCommand",
    b"Cannot execute",
    b"execute command",
    b"Invalid command",
    b"command executed",
    b"SyncCommand",
    b"HandleCommand",
    b"Failed to post",
    b"post command",
    b"PushCommand",
    b"Enqueue",
    b"CCommandQueue",
    b"ProcessCommands",
    b"DoCommand",
    b"RunCommand",
]


def main() -> int:
    pe = PE(config.binary_path(required=True))
    text = next(s for s in pe.sections if s.name == ".text")
    blob = pe.data[text.raw_ptr : text.raw_ptr + text.raw_size]
    base = text.virtual_address
    found = {}
    soft_global = Counter()

    for n in NEEDLES:
        rvas = find_ascii_all(pe, n)
        entries = []
        for rva in rvas[:10]:
            raw = pe.read_rva(rva, 96) or b""
            s = raw.split(b"\0")[0].decode("ascii", "replace")
            xrefs = rip_lea_xrefs(pe, rva, max_hits=16)
            soft = Counter()
            lea_rvAs = []
            for xr in xrefs:
                insn = xr["insn_rva"] if isinstance(xr, dict) else int(xr)
                lea_rvAs.append(hex(insn))
                off = insn - base
                for i in range(max(0, off - 0x80), min(len(blob) - 5, off + 0x80)):
                    if blob[i] != 0xE8:
                        continue
                    rel = struct.unpack_from("<i", blob, i + 1)[0]
                    tgt = (base + i + 5 + rel) & 0xFFFFFFFF
                    if base <= tgt < base + text.virtual_size:
                        soft[tgt] += 1
                        soft_global[tgt] += 1
            entries.append(
                {
                    "rva": hex(rva),
                    "str": s[:100],
                    "lea_xrefs": lea_rvAs[:12],
                    "soft_top": [{"tgt": hex(t), "hits": h} for t, h in soft.most_common(10)],
                }
            )
        found[n.decode("ascii")] = entries

    out = {
        "FN_CMD_QUEUE_POST": None,
        "note": "string LEA + nearby E8 soft catalog; Posting DISABLED until proven",
        "needles": found,
        "soft_global_top": [{"tgt": hex(t), "hits": h} for t, h in soft_global.most_common(40)],
    }
    dump = Path(ROOT) / "research" / "re-dumps" / "phase2o_strings.json"
    dump.parent.mkdir(parents=True, exist_ok=True)
    dump.write_text(json.dumps(out, indent=2), encoding="utf-8")

    for k, v in found.items():
        if v:
            print(k, "hits", len(v), "first", v[0]["str"][:70], "soft", v[0]["soft_top"][:3])
        else:
            print(k, "NONE")
    print("SOFT_GLOBAL_TOP", out["soft_global_top"][:15])
    print("wrote", dump)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
