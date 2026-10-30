#!/usr/bin/env python3
"""Phase 2h light — READ-ONLY Post/queue hunt + army→units walk.

Assumes live CInGameIdler (map). NO full-heap scan. NO writes. NO Post promote.

1) Scan CInGameIdler fields for typed ptrs (skip CGameApplication).
2) Decode sibling idler vt slots near +0x90 for other forwarders.
3) Walk player CO_ARMIES CArmy* → nested CPdxArray for CUnit*/division-like.
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "calling"))

import config
import offsets as O
from mem import Proc, find_pid
from pe import PE
from gamestate import (
    detect_session,
    _pdx_array,
    _rtti_name_from_vtable,
    probe_player_armies,
)


def ru64(p: Proc, a: int):
    b = p.try_read(a, 8)
    if not b or len(b) < 8:
        return None
    return struct.unpack_from("<Q", b, 0)[0]


def rtti_at(p: Proc, pe: PE, ptr: int):
    if not ptr or ptr < 0x10000:
        return None
    vt = ru64(p, ptr)
    if not vt or not (p.base <= vt < p.base + p.image_size):
        return None
    try:
        return _rtti_name_from_vtable(pe, vt - p.base)
    except Exception:
        return None


def scan_idler_typed(p: Proc, pe: PE, idler: int, lo=0, hi=0x900, step=8):
    hits = []
    for off in range(lo, hi, step):
        ptr = ru64(p, idler + off)
        if not ptr or ptr < 0x100000:
            continue
        # skip obvious non-heap image ptrs as objects
        if p.base <= ptr < p.base + p.image_size:
            continue
        name = rtti_at(p, pe, ptr)
        if not name:
            continue
        if "GameApplication" in name:
            continue
        hits.append({"off": hex(off), "ptr": hex(ptr), "rtti": name})
    return hits


def dump_vt_slots(pe: PE, vt_rva: int, slots):
    out = []
    for slot in slots:
        off = pe.rva_to_off(vt_rva + slot)
        if off is None:
            continue
        ptr = struct.unpack_from("<Q", pe.data, off)[0]
        mrva = ptr - pe.image_base if pe.image_base <= ptr < pe.image_base + 0x4000000 else None
        head = ""
        if mrva is not None:
            fo = pe.rva_to_off(mrva)
            head = pe.data[fo : fo + 32].hex()
        out.append({"slot": hex(slot), "method_rva": hex(mrva) if mrva else None, "head": head})
    return out


def decode_forwarder(pe: PE, fn_rva: int) -> dict:
    """Look for [this+disp] then jmp [rax+0x90]-style forwarders."""
    off = pe.rva_to_off(fn_rva)
    raw = pe.data[off : off + 96]
    info = {"fn_rva": hex(fn_rva), "head": raw[:48].hex(), "field_loads": [], "jmp_vt_slot": None}
    i = 0
    while i < len(raw) - 7:
        # mov r64, [r64+disp32]  48 8B 8x / 48 8B 8x
        if raw[i : i + 3] in (
            bytes([0x48, 0x8B, 0x81]),
            bytes([0x48, 0x8B, 0x89]),
            bytes([0x48, 0x8B, 0x91]),
            bytes([0x48, 0x8B, 0x83]),
            bytes([0x48, 0x8B, 0x8B]),
            bytes([0x48, 0x8B, 0x93]),
            bytes([0x48, 0x8B, 0xB9]),
            bytes([0x48, 0x8B, 0xBB]),
        ):
            disp = struct.unpack_from("<i", raw, i + 3)[0]
            info["field_loads"].append(hex(disp & 0xFFFFFFFF if disp < 0 else disp) if disp >= 0 else hex(disp))
            i += 7
            continue
        # FF 60/A0 xx = jmp [rax+imm]
        if raw[i] == 0xFF and raw[i + 1] in (0x60, 0x20):
            info["jmp_vt_slot"] = hex(raw[i + 2])
            break
        if raw[i] == 0xFF and raw[i + 1] == 0xA0:
            info["jmp_vt_slot"] = hex(struct.unpack_from("<i", raw, i + 2)[0])
            break
        if raw[i] == 0xC3:
            break
        i += 1
    return info


def walk_army_units(p: Proc, pe: PE, army_ptr: int, max_off=0x400):
    """Scan one CArmy for nested arrays whose first elems look like CUnit/Division."""
    found = []
    unit_vts = set([p.base + O.PROVEN_STATIC["CUnit_vtable"]])
    army_vts = set(
        [p.base + O.PROVEN_STATIC["CArmy_vtable"]]
        + [p.base + x for x in O.PROVEN_STATIC.get("CArmy_vtable_mi", [])]
    )
    for off in range(0, max_off, 8):
        arr = _pdx_array(p, army_ptr + off)
        if not arr or not (0 < arr["size"] <= 500 and arr["size"] <= arr["capacity"] <= 2000):
            continue
        if not arr["data"] or arr["data"] < 0x10000:
            continue
        # sample up to 3 elems
        names = []
        unitish = 0
        for i in range(min(arr["size"], 3)):
            elem = ru64(p, arr["data"] + i * 8)
            if not elem:
                continue
            evt = ru64(p, elem)
            nm = rtti_at(p, pe, elem)
            if nm:
                names.append(nm)
            if evt in unit_vts or (nm and any(k in nm for k in ("CUnit", "CDivision", "CLandUnit", "CArmy"))):
                # skip if array of armies inside army (unlikely)
                if nm and "CArmy@@" in nm and "Group" not in nm:
                    continue
                unitish += 1
        if unitish or (names and any(k in n for n in names for k in ("Unit", "Division", "Brigade", "Regiment"))):
            found.append(
                {
                    "army_off": hex(off),
                    "size": arr["size"],
                    "capacity": arr["capacity"],
                    "data": hex(arr["data"]),
                    "sample_rtti": names[:3],
                }
            )
    return found


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--max-armies", type=int, default=8, help="cap army walks (throttle)")
    args = ap.parse_args()

    pid = find_pid(config.EXE_NAME)
    if not pid:
        print(json.dumps({"error": "hoi4 not running"}))
        return 1
    p = Proc(pid)
    dump = os.path.join(ROOT, "research", "re-dumps", "hoi4_1.19.4.exe")
    pe = PE(dump if os.path.isfile(dump) else (p.image_path or ""))
    sess = detect_session(p, pe)
    out = {
        "phase": "2h-light",
        "read_only": True,
        "pid": pid,
        "session": sess.get("session"),
        "command_queue": "DISABLED",
        "fn_cmd_queue_post": None,
    }
    if not sess.get("in_game"):
        out["error"] = "need CInGameIdler"
        print(json.dumps(out, indent=2))
        return 3

    idler = sess["idler"]
    ip = int(idler["ptr"], 16) if isinstance(idler["ptr"], str) else idler["ptr"]
    out["idler"] = idler
    out["idler_typed_fields"] = scan_idler_typed(p, pe, ip)
    # vt neighborhood around post wrapper slot 0x90
    ig_vt = O.PROVEN_STATIC["CInGameIdler_vtable"]
    slots = list(range(0x70, 0xC0, 8))
    out["idler_vt_near_0x90"] = dump_vt_slots(pe, ig_vt, slots)
    fwd = []
    for s in out["idler_vt_near_0x90"]:
        if s["method_rva"]:
            d = decode_forwarder(pe, int(s["method_rva"], 16))
            d["slot"] = s["slot"]
            if d["field_loads"] or d["jmp_vt_slot"]:
                fwd.append(d)
    out["idler_forwarder_shapes"] = fwd

    # armies + units
    gs = sess["signals"].get("gs_ptr")
    gs_i = int(gs, 16) if isinstance(gs, str) else gs
    armies = probe_player_armies(p, pe, gs_i)
    out["armies"] = armies
    unit_walks = []
    divisions_total = 0
    best_off = None
    if armies.get("ok") and armies.get("array"):
        data = armies["array"]["data"]
        n = min(int(armies["armies_count"]), args.max_armies)
        for i in range(n):
            aptr = ru64(p, data + i * 8)
            if not aptr:
                continue
            hits = walk_army_units(p, pe, aptr)
            entry = {"army_index": i, "army_ptr": hex(aptr), "army_rtti": rtti_at(p, pe, aptr), "nested": hits}
            unit_walks.append(entry)
            for h in hits:
                if any("Unit" in x or "Division" in x for x in h.get("sample_rtti") or []):
                    divisions_total += h["size"]
                    best_off = h["army_off"]
    out["army_unit_walks"] = unit_walks
    # Light division-like markers on CArmy (no nested units expected on Windows)
    marker_hits = 0
    marker_n = 0
    if armies.get("ok") and armies.get("array"):
        data = armies["array"]["data"]
        marker_n = min(int(armies["armies_count"]), args.max_armies)
        for i in range(marker_n):
            aptr = ru64(p, data + i * 8)
            if not aptr:
                continue
            okm = 0
            for off, needle in (
                (O.HYPOTHESIS_STRUCT.get("CA_SUBUNIT_DEF", 0x138), "SubUnitDefinition"),
                (O.HYPOTHESIS_STRUCT.get("CA_PROVINCE", 0x1F0), "Province"),
                (O.HYPOTHESIS_STRUCT.get("CA_DIV_TEMPLATE", 0x3B8), "ReferencedDivisionTemplate"),
            ):
                child = ru64(p, aptr + off)
                nm = rtti_at(p, pe, child) if child else None
                if nm and needle in nm:
                    okm += 1
            if okm >= 3:
                marker_hits += 1
    out["divisions_hypothesis"] = {
        "count_sum_over_sampled_armies": divisions_total if divisions_total else None,
        "armies_sampled": len(unit_walks),
        "nested_off_seen": best_off,
        "army_division_markers": {"sampled": marker_n, "with_all_three": marker_hits},
        "divisions_count_if_markers": (
            armies.get("armies_count") if marker_n and marker_hits == marker_n else None
        ),
        "note": (
            "Windows: nested unit arrays empty; CArmy with SubUnitDef+Province+RefDivTemplate "
            "is division-level -- divisions_count := armies_count when markers match"
        ),
    }

    # queue candidates from typed idler fields (anything Command/Queue-ish)
    qcand = [
        h
        for h in out["idler_typed_fields"]
        if any(k in h["rtti"] for k in ("Command", "Queue", "Order", "Message", "Event"))
    ]
    out["queue_rtti_candidates"] = qcand
    out["notes"] = [
        "idler+0x530 remains CGameApplication — not listed in typed_fields (filtered)",
        "FN_CMD_QUEUE_POST stays null until a typed queue + Post-shaped vt slot is proven",
        "no full-heap scan",
    ]

    text = json.dumps(out, indent=2)
    print(text)
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        open(args.out, "w", encoding="utf-8").write(text)
    p.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
