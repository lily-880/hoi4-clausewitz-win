#!/usr/bin/env python3
"""Phase 2f — READ-ONLY resolve of idler Post-path + army presence.

Exercises the static shape:
  idler vt+0x90 → load [this+0x530] → jmp [rax+0x90]
without calling Post / without writes.

Also reports live CFrontEndIdler vs CInGameIdler, G_IDLER slot, and
full-heap CArmy / CArmyGroup / CUnit hit counts (expected 0 in frontend).

Usage:
  python scripts/phase2f_idler_postpath.py
  python scripts/phase2f_idler_postpath.py --out research/re-dumps/phase2f_idler.json
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "calling"))

import offsets as O
from mem import Proc
from pe import PE
import msvc_rtti as R


G_IDLER_RVA = 0x33DDB08
G_GAMESTATE_RVA = 0x33DD6B0
FE_VT = 0x29C6D30
IG_VT = O.PROVEN_STATIC["CInGameIdler_vtable"]
FE_VT90 = 0xB8DCA0
IG_VT90 = O.PROVEN_STATIC["CInGameIdler_vt_post_wrapper"]
APP_VT = 0x2796308
APP_VT90 = 0x1B14F0
QUEUE_FIELD = O.PROVEN_STATIC["CInGameIdler_queue_field_hyp"]


def name_from_vt(pe: PE, vt_rva: int):
    try:
        col_va = struct.unpack_from("<Q", pe.data, pe.rva_to_off(vt_rva - 8))[0]
        if not col_va:
            return None
        col_rva = col_va - pe.image_base if col_va >= pe.image_base else col_va
        td_rva = struct.unpack_from("<I", pe.data, pe.rva_to_off(col_rva) + 0x0C)[0]
        return pe.data[pe.rva_to_off(td_rva) + 0x10 :].split(b"\x00", 1)[0].decode("ascii", "replace")
    except Exception:
        return None


def decode_head(pe: PE, fn_rva: int, n: int = 64) -> str:
    return pe.data[pe.rva_to_off(fn_rva) : pe.rva_to_off(fn_rva) + n].hex()


def heap_vptr_counts(p: Proc, vtable_rvas, label_prefix: str) -> dict:
    needles = {("%s_%s" % (label_prefix, hex(v))): struct.pack("<Q", p.base + v) for v in vtable_rvas}
    counts = {k: 0 for k in needles}
    samples = {k: [] for k in needles}
    scanned = 0
    for m in p.regions(writable=True, min_size=0x1000):
        start, end = m["start"], m["end"]
        if p.base <= start < p.base + p.image_size:
            continue
        pos = start
        while pos < end:
            chunk = min(4 << 20, end - pos)
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
    return {
        "scanned_mb": scanned >> 20,
        "counts": {k: v for k, v in counts.items() if v},
        "samples": {k: v for k, v in samples.items() if v},
        "total_hits": sum(counts.values()),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--skip-heap", action="store_true", help="skip multi-GB army heap scan")
    args = ap.parse_args()

    pe_path = os.path.join(ROOT, "research", "re-dumps", "hoi4_1.19.4.exe")
    if not os.path.isfile(pe_path):
        # fall back to live module via Proc image path after attach
        pe_path = None

    p = Proc()
    if pe_path is None:
        pe_path = p.image_path
    pe = PE(pe_path)

    out = {
        "phase": "2f",
        "read_only": True,
        "pid": p.pid if hasattr(p, "pid") else None,
        "image_base": hex(p.base),
        "G_IDLER_rva": hex(G_IDLER_RVA),
        "G_GAMESTATE_rva": hex(G_GAMESTATE_RVA),
        "post_path": {},
        "armies": {},
        "fn_cmd_queue_post": None,
        "notes": [],
    }

    idler_ptr = p.u64(p.base + G_IDLER_RVA)
    gs_ptr = p.u64(p.base + G_GAMESTATE_RVA)
    out["idler_ptr"] = hex(idler_ptr) if idler_ptr else None
    out["gs_ptr"] = hex(gs_ptr) if gs_ptr else None

    if idler_ptr:
        vt = p.u64(idler_ptr)
        vt_rva = vt - p.base
        nm = name_from_vt(pe, vt_rva)
        out["idler_vtable_rva"] = hex(vt_rva)
        out["idler_rtti"] = nm
        q = p.u64(idler_ptr + QUEUE_FIELD)
        out["post_path"]["queue_field_offset"] = hex(QUEUE_FIELD)
        out["post_path"]["queue_obj"] = hex(q) if q else None
        if q:
            qvt = p.u64(q)
            qvt_rva = qvt - p.base
            out["post_path"]["queue_obj_vtable_rva"] = hex(qvt_rva)
            out["post_path"]["queue_obj_rtti"] = name_from_vt(pe, qvt_rva)
            # method at that object's vt+0x90
            try:
                method = struct.unpack_from("<Q", pe.data, pe.rva_to_off(qvt_rva + 0x90))[0]
                method_rva = method - pe.image_base
                out["post_path"]["resolved_vt90_method_rva"] = hex(method_rva)
                out["post_path"]["resolved_vt90_head"] = decode_head(pe, method_rva, 48)
            except Exception as e:
                out["post_path"]["resolved_vt90_error"] = str(e)

        if vt_rva == FE_VT:
            out["post_path"]["wrapper_rva"] = hex(FE_VT90)
            out["post_path"]["wrapper_note"] = (
                "CFrontEndIdler vt+0x90 forwards [this+0x530]→vt+0x90; "
                "live +0x530 is CGameApplication; App vt+0x90=0x1b14f0 is a "
                "field-+0x380 setter (CSession*), NOT Post"
            )
            out["notes"].append("session=frontend/lobby — CInGameIdler absent; Post target unresolved")
        elif vt_rva == IG_VT:
            out["post_path"]["wrapper_rva"] = hex(IG_VT90)
            out["post_path"]["wrapper_note"] = (
                "CInGameIdler vt+0x90 logs then forwards [this+0x530]→vt+0x90; "
                "characterize live +0x530 object's vt+0x90 before promoting FN_CMD_QUEUE_POST"
            )
            out["notes"].append("session=in-game idler live — characterize queue object (still no Post)")
        else:
            out["notes"].append("unexpected idler vtable %s (%s)" % (hex(vt_rva), nm))
    else:
        out["notes"].append("G_IDLER slot null")

    # Static reference shapes (always)
    out["static"] = {
        "CFrontEndIdler_vtable": hex(FE_VT),
        "CFrontEndIdler_vt90": hex(FE_VT90),
        "CInGameIdler_vtable": hex(IG_VT),
        "CInGameIdler_vt90": hex(IG_VT90),
        "CGameApplication_vtable": hex(APP_VT),
        "CGameApplication_vt90_setter": hex(APP_VT90),
        "CCommandQueue_rtti": "NONE",
    }

    if not args.skip_heap:
        army_vts = [O.PROVEN_STATIC["CArmy_vtable"]] + list(O.PROVEN_STATIC["CArmy_vtable_mi"])
        unit_vts = [O.PROVEN_STATIC["CUnit_vtable"]]
        ag = R.exact_type(pe, "CArmyGroup")
        ag_vts = [v["vtable_rva"] for v in (ag or {}).get("vtables") or []]
        out["armies"]["CArmy"] = heap_vptr_counts(p, army_vts, "CArmy")
        out["armies"]["CUnit"] = heap_vptr_counts(p, unit_vts, "CUnit")
        if ag_vts:
            out["armies"]["CArmyGroup"] = heap_vptr_counts(p, ag_vts, "CArmyGroup")
            out["armies"]["CArmyGroup_vtables"] = [hex(v) for v in ag_vts]
        if out["armies"]["CArmy"]["total_hits"] == 0:
            out["notes"].append(
                "0 live CArmy/CUnit/CArmyGroup heap hits — divisions stay stubbed "
                "(frontend or pre-spawn campaign)"
            )

    out["fn_cmd_queue_post"] = None
    out["command_queue"] = "DISABLED"

    text = json.dumps(out, indent=2)
    print(text)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        open(args.out, "w", encoding="utf-8").write(text)
        print("wrote", args.out, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
