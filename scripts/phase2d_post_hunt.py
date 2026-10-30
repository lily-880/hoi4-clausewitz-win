#!/usr/bin/env python3
"""Phase 2d: bounded static hunt for FN_CMD_QUEUE_POST / queue entry points.

READ-ONLY. Never enables writes. Writes research/re-dumps/phase2d_post_hunt.json
(and prints a summary). Policy: FN_CMD_QUEUE_POST stays null unless a single
clear Post callee is proven — this script only catalogues candidates.
"""
from __future__ import annotations

import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "calling"))

from pe import PE  # noqa: E402
from msvc_rtti import catalog, exact_type, scan_type_names  # noqa: E402
from stringscan import find_ascii_all, rip_lea_xrefs  # noqa: E402

CMD_VT = 0x279F4A0


def text_blob(pe: PE):
    text = next(s for s in pe.sections if s.name == ".text")
    return text, pe.data[text.raw_ptr : text.raw_ptr + text.raw_size]


def rip_string_xrefs(pe: PE, str_rva: int, max_hits: int = 20) -> list:
    return rip_lea_xrefs(pe, str_rva, max_hits=max_hits)


def nearby_calls(pe: PE, insn_rva: int, window: int = 0x80) -> list:
    """Collect E8 rel32 call targets near a string LEA (likely wrappers)."""
    text, blob = text_blob(pe)
    base = text.virtual_address
    off = insn_rva - base
    lo = max(0, off - window)
    hi = min(len(blob) - 5, off + window)
    calls = []
    for i in range(lo, hi):
        if blob[i] != 0xE8:
            continue
        rel = struct.unpack_from("<i", blob, i + 1)[0]
        tgt = (base + i + 5 + rel) & 0xFFFFFFFF
        if base <= tgt < base + text.virtual_size:
            calls.append({"call_rva": hex(base + i), "target_rva": hex(tgt), "near_lea": hex(insn_rva)})
    return calls


def main():
    exe = os.path.join(ROOT, "research", "re-dumps", "hoi4_1.19.4.exe")
    if not os.path.isfile(exe):
        # fall back via config
        import config

        exe = config.binary_path(required=True)
    pe = PE(exe)
    out = {
        "policy": "FN_CMD_QUEUE_POST DISABLED — candidates only, no writes",
        "CCommand_vtable": hex(CMD_VT),
        "rtti": {},
        "strings": {},
        "string_lea_xrefs": {},
        "nearby_calls_sample": [],
        "FN_CMD_QUEUE_POST": None,
    }

    # RTTI names of interest
    names = [
        b".?AVCCommandQueue@@",
        b".?AVCCommand@@",
        b"QueueCommand",
        b"PostCommand",
        b"ExecuteCommand",
        b"CommandQueue",
    ]
    cat = catalog(pe)
    for n in (b"CCommandQueue", b"CQueuedCommand", b"CNetCommand", b"CGameCommand", b"CPdxCommand"):
        hits = scan_type_names(pe, n.decode() if isinstance(n, bytes) else n)
        out["rtti"][n.decode()] = {
            "substring_hit_count": len(hits),
            "sample": hits[:8],
        }
    exact = exact_type(pe, ".?AVCCommandQueue@@")
    out["rtti"]["exact_CCommandQueue"] = exact

    for label in (b"QueueCommand", b"PostCommand", b"ExecuteCommand", b"AddCommand", b"PushCommand"):
        rvas = find_ascii_all(pe, label)
        out["strings"][label.decode()] = [hex(r) for r in rvas[:16]]
        xrefs = []
        for r in rvas[:8]:
            for x in rip_string_xrefs(pe, r, max_hits=8):
                xrefs.append({**x, "insn_rva": hex(x["insn_rva"]), "string_rva": hex(r)})
                out["nearby_calls_sample"].extend(nearby_calls(pe, x["insn_rva"])[:6])
        out["string_lea_xrefs"][label.decode()] = xrefs[:20]

    # Cap call sample
    out["nearby_calls_sample"] = out["nearby_calls_sample"][:40]
    # Dedup call targets as soft candidates
    targets = sorted({c["target_rva"] for c in out["nearby_calls_sample"]})
    out["soft_call_target_candidates"] = targets[:30]
    out["note"] = (
        "Soft call targets near QueueCommand/PostCommand string LEAs are NOT proven Post. "
        "Do not set FN_CMD_QUEUE_POST from this list."
    )

    path = os.path.join(ROOT, "research", "re-dumps", "phase2d_post_hunt.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(out, open(path, "w", encoding="utf-8"), indent=2)
    print(
        json.dumps(
            {
                "FN_CMD_QUEUE_POST": None,
                "exact_CCommandQueue": bool(exact),
                "QueueCommand_strings": len(out["strings"].get("QueueCommand", [])),
                "PostCommand_strings": len(out["strings"].get("PostCommand", [])),
                "soft_call_targets": len(targets),
                "out": path,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
