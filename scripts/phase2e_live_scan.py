#!/usr/bin/env python3
"""Phase 2e incremental LIVE read-only scan: idler, queue field, CArmy arrays, date.

Requires running hoi4.exe with a campaign loaded. Never writes. Never posts.
Prints JSON summary; optional --out path for full dump under research/re-dumps/.
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "calling"))

from mem import Proc  # noqa: E402
import offsets as O  # noqa: E402
from pe import PE  # noqa: E402
from msvc_rtti import find_col_and_vtable, scan_type_names  # noqa: E402

IDLER_QUEUE_FIELD_HYP = 0x530  # from phase2e static decode of idler vt+0x90
ARMY_VT_FALLBACK = [0x29D6D68, 0x29D6F48, 0x29D6FB8, 0x29D7000]


def _recover_army_rvas(pe: PE) -> list:
    hits = [h for h in scan_type_names(pe, "CArmy", limit=20) if h.get("name") == ".?AVCArmy@@"]
    if not hits:
        return ARMY_VT_FALLBACK
    col = find_col_and_vtable(pe, hits[0]["td_rva"])
    return [v["vtable_rva"] for v in col.get("vtables", [])] or ARMY_VT_FALLBACK


def _pdx(p, addr):
    d = p.try_read(addr, 0x10)
    if not d:
        return None
    data, cap, size = struct.unpack_from("<Qii", d, 0)
    return {"data": data, "capacity": cap, "size": size}


def hunt_army_arrays(p, country: int, army_runtime: set, max_off: int = 0x1800) -> list:
    blob = p.try_read(country, max_off)
    if not blob:
        return []
    hits = []
    for off in range(0, len(blob) - 0x10, 8):
        arr_data = struct.unpack_from("<Q", blob, off)[0]
        cap_i, size_i = struct.unpack_from("<ii", blob, off + 8)
        if not (1 <= size_i <= 800 and size_i <= cap_i <= 2000 and arr_data > 0x10000):
            continue
        arr = p.try_read(arr_data, min(size_i, 8) * 8)
        if not arr:
            continue
        match = 0
        for j in range(min(size_i, 8)):
            obj = struct.unpack_from("<Q", arr, j * 8)[0]
            vb = p.try_read(obj, 8) if obj > 0x10000 else None
            if vb and struct.unpack_from("<Q", vb, 0)[0] in army_runtime:
                match += 1
        if match >= 1:
            hits.append({"off": hex(off), "size": size_i, "cap": cap_i, "matches": match})
    return hits


def scan_idler(p, max_bytes: int = 256 << 20) -> dict:
    vts = [
        O.PROVEN_STATIC["CInGameIdler_vtable"],
        0x29E5C00,
        0x29E5C20,
        0x29E5C40,
        O.PROVEN_STATIC["CGameIdler_vtable"],
    ]
    needles = {hex(r): struct.pack("<Q", p.base + r) for r in vts}
    counts = {k: 0 for k in needles}
    samples = {k: [] for k in needles}
    scanned = 0
    for m in p.regions(writable=True, min_size=0x1000):
        start, end = m["start"], m["end"]
        if p.base <= start < p.base + p.image_size:
            continue
        pos = start
        while pos < end:
            chunk = min(2 << 20, end - pos)
            data = p.try_read(pos, chunk)
            scanned += chunk
            if data:
                for k, n in needles.items():
                    off = 0
                    while True:
                        i = data.find(n, off)
                        if i < 0:
                            break
                        if i % 8 == 0:
                            counts[k] += 1
                            if len(samples[k]) < 2:
                                samples[k].append(hex(pos + i))
                        off = i + 8
            pos += chunk
            if scanned >= max_bytes:
                break
        if scanned >= max_bytes:
            break
    return {"scanned_bytes": scanned, "counts": counts, "samples": samples}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    ap.add_argument("--max-heap-mb", type=int, default=256)
    args = ap.parse_args()

    p = Proc()
    gs_rva = O.WINDOWS_GLOBALS.get("G_GAMESTATE")
    out = {
        "policy": "read-only live scan; FN_CMD_QUEUE_POST untouched",
        "pid": p.pid,
        "base": hex(p.base),
        "G_GAMESTATE": hex(gs_rva) if gs_rva else None,
    }
    if not gs_rva:
        out["error"] = "G_GAMESTATE not loaded"
        print(json.dumps(out, indent=2))
        return 1

    gs = p.ptr(p.base + gs_rva)
    out["gs_ptr"] = hex(gs)
    year = p.i32(gs + 0x478)
    aux = p.i32(gs + 0x47C)
    out["date"] = {
        "year_at_0x478": year,
        "aux_at_0x47c": aux,
        "note": "aux may be day-of-year hypothesis; NOT promoted to full Y-M-D without UI proof",
    }

    countries = _pdx(p, gs + 0x310)
    tag = p.i32(gs + 0x518)
    out["countries"] = countries
    out["player_tag"] = tag

    exe = os.path.join(ROOT, "research", "re-dumps", "hoi4_1.19.4.exe")
    pe = PE(exe if os.path.isfile(exe) else __import__("config").binary_path(required=True))
    army_rvas = _recover_army_rvas(pe)
    army_runtime = {p.base + r for r in army_rvas}
    out["CArmy_vtable_rvas"] = [hex(r) for r in army_rvas]

    army_hits = []
    if countries and countries["data"]:
        raw = p.try_read(countries["data"], countries["size"] * 8)
        cps = [struct.unpack_from("<Q", raw, i * 8)[0] for i in range(countries["size"])]
        # player + majors
        targets = []
        if 0 <= tag < len(cps) and cps[tag]:
            targets.append(("player", cps[tag]))
        majors = _pdx(p, gs + 0x328)
        if majors and majors["data"]:
            mraw = p.try_read(majors["data"], majors["size"] * 8)
            for i in range(majors["size"]):
                targets.append(("major_%d" % i, struct.unpack_from("<Q", mraw, i * 8)[0]))
        for label, cp in targets:
            if not cp:
                continue
            h = hunt_army_arrays(p, cp, army_runtime)
            army_hits.append({"who": label, "country": hex(cp), "hits": h})
            # Linux CO_ARMIES 0x290 probe
            a290 = _pdx(p, cp + 0x290)
            army_hits[-1]["linux_CO_ARMIES_0x290"] = a290
    out["army_array_hunt"] = army_hits
    out["divisions_count"] = None
    out["divisions_note"] = "stubbed — no CArmy* CPdxArray proven on live countries this run"

    out["idler_heap"] = scan_idler(p, max_bytes=args.max_heap_mb << 20)
    # If any idler sample, try +0x530
    queue_probes = []
    for samples in out["idler_heap"]["samples"].values():
        for s in samples:
            obj = int(s, 16)
            q = p.ptr(obj + IDLER_QUEUE_FIELD_HYP)
            entry = {"idler": s, "field": hex(IDLER_QUEUE_FIELD_HYP), "value": hex(q) if q else None}
            if q and q > 0x10000:
                vb = p.try_read(q, 8)
                if vb:
                    vp = struct.unpack_from("<Q", vb, 0)[0]
                    entry["queue_vptr_rva"] = hex(vp - p.base) if vp >= p.base else hex(vp)
                    # dump vt+0x90
                    if vp >= p.base:
                        slot = p.ptr(vp + 0x90)
                        entry["queue_vt_plus_0x90"] = hex(slot - p.base) if slot and slot >= p.base else (hex(slot) if slot else None)
            queue_probes.append(entry)
    out["queue_field_probes"] = queue_probes
    out["FN_CMD_QUEUE_POST"] = None

    text = json.dumps(out, indent=2)
    print(text)
    if args.out:
        path = args.out
        if not os.path.isabs(path):
            path = os.path.join(ROOT, path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w", encoding="utf-8").write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
