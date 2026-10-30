#!/usr/bin/env python3
"""Phase 2o: prove/reject ctor-caller Post hyps from 2n. READ-ONLY. Never post."""
from __future__ import annotations

import argparse
import json
import os
import struct
import sys
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "calling"))

import config
import offsets as O
from pe import PE
from mem import Proc, find_pid
from gamestate import detect_session, _rtti_name_from_vtable, _pdx_array

# From phase 2n ctor-caller soft ranking (non-dead prior)
HYPS = [
    0x25C3770,
    0x22C41E0,
    0x254AA00,
    0x25A0390,
    0x216E50,
    0x21A320,
    0xBA7270,
    0xBBB080,
]

# Previously rejected
KNOWN_DEAD = {
    0x25A009C: "SSO/refcount/destroy (2k/2l)",
    0x25A00D8: "SSO/destroy (2k/2l)",
    0x11F6F0: "registry/SSO (2l)",
    0x11F770: "registry/SSO (2l)",
    0x1F7640: "SSO (2l)",
    0x1B14F0: "App vt90 setter (2f)",
}


def text_blob(pe: PE):
    text = next(s for s in pe.sections if s.name == ".text")
    return text, pe.data[text.raw_ptr : text.raw_ptr + text.raw_size]


def decode_fn(pe: PE, fn: int, nbytes: int = 0x200) -> dict:
    text, blob = text_blob(pe)
    base = text.virtual_address
    if not (base <= fn < base + text.virtual_size):
        return {"error": "not in text", "fn": hex(fn)}
    off = fn - base
    raw = blob[off : off + nbytes]
    calls = []
    leas = []
    rip_loads = []
    stores_disp = []
    vt_calls = []
    i = 0
    while i < len(raw) - 6:
        at = fn + i
        b = raw
        if b[i] == 0xE8:
            rel = struct.unpack_from("<i", b, i + 1)[0]
            tgt = (at + 5 + rel) & 0xFFFFFFFF
            calls.append(hex(tgt))
            i += 5
            continue
        if b[i] == 0x48 and b[i + 1] == 0x8D and b[i + 2] in (0x05, 0x0D, 0x15, 0x1D, 0x25, 0x2D, 0x35, 0x3D):
            rel = struct.unpack_from("<i", b, i + 3)[0]
            tgt = (at + 7 + rel) & 0xFFFFFFFFFFFF
            leas.append(hex(tgt))
            i += 7
            continue
        # mov reg, [rip+rel]  48 8B 05/0D/...
        if b[i] == 0x48 and b[i + 1] == 0x8B and b[i + 2] in (0x05, 0x0D, 0x15, 0x1D, 0x25, 0x2D, 0x35, 0x3D):
            rel = struct.unpack_from("<i", b, i + 3)[0]
            tgt = (at + 7 + rel) & 0xFFFFFFFFFFFF
            rip_loads.append(hex(tgt))
            i += 7
            continue
        # call [reg+disp8]
        if b[i] == 0xFF and b[i + 1] in range(0x50, 0x58):
            vt_calls.append(hex(b[i + 2]))
            i += 3
            continue
        if b[i] == 0xFF and b[i + 1] in range(0x90, 0x98):
            disp = struct.unpack_from("<i", b, i + 2)[0]
            vt_calls.append(hex(disp))
            i += 6
            continue
        # mov [reg+disp8], reg — 89 4x / 48 89
        if b[i] == 0x89 and i + 2 < len(b):
            modrm = b[i + 1]
            if (modrm & 0xC0) == 0x40:  # disp8
                stores_disp.append(hex(b[i + 2]))
                i += 3
                continue
        if b[i] == 0x48 and b[i + 1] == 0x89 and i + 3 < len(b):
            modrm = b[i + 2]
            if (modrm & 0xC0) == 0x40:
                stores_disp.append(hex(b[i + 3]))
                i += 4
                continue
        i += 1
    return {
        "fn": hex(fn),
        "head": raw[:40].hex(),
        "ncalls": len(calls),
        "calls": calls[:20],
        "leas": leas[:16],
        "rip_loads": rip_loads[:16],
        "vt_calls": vt_calls[:12],
        "stores_disp8": stores_disp[:24],
        "known_dead": KNOWN_DEAD.get(fn),
    }


def e8_xrefs(pe: PE, target: int, limit: int = 30) -> list:
    text, blob = text_blob(pe)
    base = text.virtual_address
    hits = []
    i = 0
    while i < len(blob) - 5 and len(hits) < limit:
        if blob[i] == 0xE8:
            rel = struct.unpack_from("<i", blob, i + 1)[0]
            tgt = (base + i + 5 + rel) & 0xFFFFFFFF
            if tgt == target:
                hits.append(base + i)
            i += 5
        else:
            i += 1
    return hits


def classify(dec: dict, pe: PE, p=None) -> dict:
    """Heuristic classification — never promotes Post."""
    reasons = []
    role = "unknown"
    fn = int(dec["fn"], 16)
    if dec.get("known_dead"):
        return {"role": "REJECTED", "reasons": [dec["known_dead"]]}

    # string LEAs?
    for lea in dec.get("leas") or []:
        rva = int(lea, 16)
        try:
            raw = pe.read_rva(rva, 64) or b""
        except Exception:
            raw = b""
        if raw.startswith(b".?AV") or b"Command" in raw or b"queue" in raw.lower() or b"Queue" in raw:
            reasons.append("lea_str:" + raw.split(b"\0")[0][:60].decode("ascii", "replace"))

    # RIP loads of globals — live type if attached
    live_globals = []
    if p is not None:
        for rg in dec.get("rip_loads") or []:
            rva = int(rg, 16)
            # treat as RVA to a pointer slot in image
            if rva < pe.size_of_image:
                va = p.base + rva
                ptr = p.try_read(va, 8)
                if ptr and len(ptr) == 8:
                    val = struct.unpack_from("<Q", ptr, 0)[0]
                    entry = {"rva": rg, "val": hex(val)}
                    if val > 0x10000 and not (p.base <= val < p.base + p.image_size):
                        vt_b = p.try_read(val, 8)
                        if vt_b and len(vt_b) == 8:
                            vt = struct.unpack_from("<Q", vt_b, 0)[0]
                            if p.base <= vt < p.base + p.image_size:
                                entry["rtti"] = _rtti_name_from_vtable(pe, vt - p.base)
                    live_globals.append(entry)

    # patterns
    if dec["ncalls"] == 0 and not dec.get("vt_calls"):
        role = "leaf_or_data"
        reasons.append("no calls")
    if any(int(c, 16) in KNOWN_DEAD for c in dec.get("calls") or []):
        reasons.append("calls_known_dead")
    # Post-shaped guess: few calls, has stores, maybe vt call — STILL unproven
    if 1 <= dec["ncalls"] <= 5 and dec.get("stores_disp8"):
        reasons.append("few_calls_with_stores")
    if dec.get("vt_calls"):
        reasons.append("has_virtual_calls:" + ",".join(dec["vt_calls"][:4]))

    return {"role": role, "reasons": reasons, "live_globals": live_globals}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--out", default="research/re-dumps/phase2o_post_hyps.json")
    args = ap.parse_args()

    pe = PE(config.binary_path(required=True))
    p = None
    sess = None
    if args.live:
        p = Proc(find_pid(config.EXE_NAME))
        sess = detect_session(p, pe)

    out = {
        "phase": "2o",
        "read_only": True,
        "FN_CMD_QUEUE_POST": None,
        "session": None
        if not sess
        else {
            "pid": p.pid,
            "idler": (sess.get("signals") or {}).get("idler_class"),
            "gs": (sess.get("signals") or {}).get("gs_ptr"),
        },
        "hyps": [],
        "notes": [],
    }

    for fn in HYPS:
        dec = decode_fn(pe, fn)
        xrefs = e8_xrefs(pe, fn, limit=25)
        dec["xref_count"] = len(xrefs)
        dec["xref_sample"] = [hex(x) for x in xrefs[:8]]
        dec["class"] = classify(dec, pe, p)
        # also classify callees briefly
        callee_notes = []
        for c in (dec.get("calls") or [])[:8]:
            ci = int(c, 16)
            if ci in KNOWN_DEAD:
                callee_notes.append({"tgt": c, "dead": KNOWN_DEAD[ci]})
            else:
                cd = decode_fn(pe, ci, 0x80)
                callee_notes.append(
                    {
                        "tgt": c,
                        "ncalls": cd.get("ncalls"),
                        "rip": (cd.get("rip_loads") or [])[:4],
                        "head": cd.get("head"),
                    }
                )
        dec["callees"] = callee_notes
        out["hyps"].append(dec)

    out["notes"].append("No hyp independently proven as FN_CMD_QUEUE_POST")
    out["notes"].append("posting DISABLED")

    # Summarize reject vs keep-open
    keep = []
    reject = []
    for h in out["hyps"]:
        reasons = (h.get("class") or {}).get("reasons") or []
        if h.get("known_dead") or "calls_known_dead" in reasons and h["ncalls"] <= 2:
            reject.append(h["fn"])
        else:
            keep.append(
                {
                    "fn": h["fn"],
                    "xrefs": h.get("xref_count"),
                    "reasons": reasons,
                    "rip": h.get("rip_loads"),
                    "live": (h.get("class") or {}).get("live_globals"),
                }
            )
    out["keep_open"] = keep
    out["likely_reject"] = reject

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    summary = {
        "FN_CMD_QUEUE_POST": None,
        "keep_open": keep,
        "likely_reject": reject,
    }
    Path("research/re-dumps/phase2o_summary.txt").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2)[:5000])
    if p:
        p.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
