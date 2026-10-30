#!/usr/bin/env python3
"""Phase 2g — session gate + READ-ONLY Post-path / army resolve.

Classifies G_IDLER (CFrontEndIdler vs CInGameIdler). If frontend, prints a
clear USER ACTION and exits 3 without polling. If in-game, resolves
idler+0x530 typed object and optionally full-heap CArmy/CArmyGroup counts.
Never posts. FN_CMD_QUEUE_POST stays null until proven.

Usage:
  python scripts/phase2g_session_postpath.py
  python scripts/phase2g_session_postpath.py --heap
  python scripts/phase2g_session_postpath.py --out research/re-dumps/phase2g.json
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
from mem import Proc, find_pid
from pe import PE
from gamestate import detect_session, _pdx_array, _rtti_name_from_vtable
import config
import msvc_rtti as R


QUEUE_OFF = O.PROVEN_STATIC["CInGameIdler_queue_field_hyp"]
IG_VT90 = O.PROVEN_STATIC["CInGameIdler_vt_post_wrapper"]
FE_VT90 = O.PROVEN_STATIC.get("CFrontEndIdler_vt_forward", 0xB8DCA0)
APP_VT90 = O.PROVEN_STATIC.get("CGameApplication_vt90_setter", 0x1B14F0)


def decode_head(pe: PE, fn_rva: int, n: int = 64) -> str:
    return pe.data[pe.rva_to_off(fn_rva) : pe.rva_to_off(fn_rva) + n].hex()


def characterize_vt90(pe: PE, method_rva: int) -> dict:
    """Static shape notes — never call the method."""
    head = decode_head(pe, method_rva, 96)
    info = {
        "method_rva": hex(method_rva),
        "head": head[:96],
        "role_hypothesis": "unknown",
        "fields": [],
        "is_app_setter": method_rva == APP_VT90,
        "is_idler_wrapper": method_rva in (IG_VT90, FE_VT90),
    }
    if method_rva == APP_VT90:
        info["role_hypothesis"] = "REJECT_as_Post — CGameApplication setter(+0x380)"
        return info
    if method_rva in (IG_VT90, FE_VT90):
        info["role_hypothesis"] = "idler forwarder [this+0x530]->vt+0x90 (not leaf Post)"
        return info
    # light field scan
    raw = pe.data[pe.rva_to_off(method_rva) : pe.rva_to_off(method_rva) + 160]
    i = 0
    while i < len(raw) - 7:
        if raw[i : i + 3] in (
            bytes([0x48, 0x8B, 0x81]),
            bytes([0x48, 0x8B, 0x89]),
            bytes([0x48, 0x8B, 0x91]),
            bytes([0x48, 0x8B, 0x83]),
            bytes([0x48, 0x8B, 0x8B]),
        ):
            info["fields"].append(hex(struct.unpack_from("<i", raw, i + 3)[0]))
            i += 7
            continue
        if raw[i] == 0xC3:
            info["ret_at"] = i
            break
        i += 1
    info["role_hypothesis"] = (
        "CANDIDATE_only — needs CCommand* arg proof + enqueue side effects before promote"
    )
    return info


def heap_counts(p: Proc, vtable_rvas, label: str) -> dict:
    needles = {("%s_%s" % (label, hex(v))): struct.pack("<Q", p.base + v) for v in vtable_rvas}
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


def try_divisions(p: Proc, pe: PE) -> dict:
    """If GS+countries live, scan player country for CArmy* arrays (RO)."""
    ggs = O.WINDOWS_GLOBALS.get("G_GAMESTATE")
    if not isinstance(ggs, int):
        return {"ok": False, "reason": "no G_GAMESTATE"}
    gs = p.u64(p.base + ggs)
    if not gs:
        return {"ok": False, "reason": "null GS"}
    countries = _pdx_array(p, gs + O.HYPOTHESIS_STRUCT["GS_COUNTRIES"])
    tag = p.i32(gs + O.HYPOTHESIS_STRUCT["GS_PLAYER_TAG"])
    out = {
        "ok": False,
        "countries": countries,
        "player_tag": tag,
        "army_arrays": [],
        "divisions_count": None,
    }
    if not countries or not (50 <= countries["size"] <= 2000):
        out["reason"] = "countries array implausible"
        return out
    if not (0 <= tag < countries["size"]):
        out["reason"] = "bad player tag"
        return out
    cptr = p.u64(countries["data"] + tag * 8)
    out["country_ptr"] = hex(cptr)
    army_vts = set(
        [p.base + O.PROVEN_STATIC["CArmy_vtable"]]
        + [p.base + x for x in O.PROVEN_STATIC.get("CArmy_vtable_mi", [])]
    )
    ag = O.PROVEN_STATIC.get("CArmyGroup_vtable")
    if ag:
        army_vts.add(p.base + ag)
    for off in range(0, 0x800, 8):
        arr = _pdx_array(p, cptr + off)
        if not arr or not (0 < arr["size"] <= 500 and arr["size"] <= arr["capacity"] <= 2000):
            continue
        if not arr["data"] or arr["data"] < 0x10000:
            continue
        hits = 0
        first_nm = None
        for i in range(min(arr["size"], 5)):
            try:
                elem = p.u64(arr["data"] + i * 8)
                if not elem:
                    continue
                evt = p.u64(elem)
                if evt in army_vts:
                    hits += 1
                    first_nm = _rtti_name_from_vtable(pe, evt - p.base)
                else:
                    nm = (
                        _rtti_name_from_vtable(pe, evt - p.base)
                        if p.base <= evt < p.base + p.image_size
                        else None
                    )
                    if nm and any(x in nm for x in ("Army", "Unit", "Division")):
                        hits += 1
                        first_nm = nm
            except OSError:
                pass
        if hits:
            out["army_arrays"].append(
                {
                    "country_offset": hex(off),
                    "size": arr["size"],
                    "capacity": arr["capacity"],
                    "data": hex(arr["data"]),
                    "first_rtti": first_nm,
                }
            )
    if out["army_arrays"]:
        # prefer largest army-like array as divisions_count hypothesis
        best = max(out["army_arrays"], key=lambda a: a["size"])
        out["divisions_count"] = best["size"]
        out["divisions_offset_hyp"] = best["country_offset"]
        out["ok"] = True
        out["note"] = "promoted — CO_ARMIES@0x290 CArmy* (hands_off + paused HAI samples); armies_count not divisions"
    else:
        out["reason"] = "no CArmy*/CArmyGroup* arrays on player country"
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--heap", action="store_true", help="full-heap CArmy/CUnit/CArmyGroup scan")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    pid = find_pid(config.EXE_NAME)
    if not pid:
        msg = {
            "phase": "2g",
            "error": "hoi4.exe not running",
            "user_action": "LOAD_CAMPAIGN_MAP",
            "guidance": "Start HOI4, load a campaign/save until the map is visible, then re-run this script.",
        }
        print(json.dumps(msg, indent=2))
        return 1

    p = Proc(pid)
    pe_path = os.path.join(ROOT, "research", "re-dumps", "hoi4_1.19.4.exe")
    pe = PE(pe_path if os.path.isfile(pe_path) else p.image_path)

    session = detect_session(p, pe)
    out = {
        "phase": "2g",
        "read_only": True,
        "pid": pid,
        "image_base": hex(p.base),
        "session": session,
        "post_path": None,
        "armies": None,
        "divisions": None,
        "fn_cmd_queue_post": None,
        "command_queue": "DISABLED",
        "notes": [],
    }

    # Banner for humans (also in JSON)
    if session.get("user_action") == "LOAD_CAMPAIGN_MAP":
        banner = (
            "\n*** USER ACTION REQUIRED: LOAD_CAMPAIGN_MAP ***\n"
            "Session is '%s' (idler=%s). Load a campaign/save until the map UI "
            "is visible, then re-run this command. No polling — one-shot check.\n"
            % (session.get("session"), (session.get("signals") or {}).get("idler_class"))
        )
        print(banner, file=sys.stderr)
        out["notes"].append(session.get("guidance"))
        # Still record static Post-path shape for frontend (known dead for Post)
        idler = session.get("idler") or {}
        out["post_path"] = {
            "state": "frontend_dead_end_for_Post",
            "wrapper_rva": hex(FE_VT90),
            "field_0x530_rtti": idler.get("field_0x530_rtti"),
            "resolved_vt90": characterize_vt90(pe, APP_VT90),
            "fn_cmd_queue_post": None,
        }
        if args.heap:
            army_vts = [O.PROVEN_STATIC["CArmy_vtable"]] + list(
                O.PROVEN_STATIC.get("CArmy_vtable_mi") or []
            )
            out["armies"] = {
                "CArmy": heap_counts(p, army_vts, "CArmy"),
                "note": "expected 0 hits while frontend",
            }
        text = json.dumps(out, indent=2)
        print(text)
        if args.out:
            os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
            open(args.out, "w", encoding="utf-8").write(text)
        p.close()
        return 3

    # in-game path
    idler = session.get("idler") or {}
    idler_ptr = int(idler["ptr"], 16)
    q = p.u64(idler_ptr + QUEUE_OFF)
    post = {
        "state": "in_game_resolve",
        "wrapper_rva": hex(IG_VT90),
        "queue_field": hex(QUEUE_OFF),
        "queue_obj": hex(q) if q else None,
    }
    if q:
        qvt = p.u64(q)
        qvt_rva = qvt - p.base
        post["queue_obj_vtable_rva"] = hex(qvt_rva)
        post["queue_obj_rtti"] = _rtti_name_from_vtable(pe, qvt_rva)
        try:
            method = struct.unpack_from("<Q", pe.data, pe.rva_to_off(qvt_rva + 0x90))[0]
            method_rva = method - pe.image_base
            post["resolved_vt90"] = characterize_vt90(pe, method_rva)
            if post["resolved_vt90"].get("is_app_setter"):
                out["notes"].append("in-game +0x530 still Application setter — unexpected; do not promote")
            else:
                out["notes"].append(
                    "CANDIDATE vt+0x90=%s (%s) — NOT promoted; need CCommand*+enqueue proof"
                    % (hex(method_rva), post.get("queue_obj_rtti"))
                )
        except Exception as e:
            post["resolved_vt90_error"] = str(e)
    else:
        out["notes"].append("idler+0x530 null")
    out["post_path"] = post
    out["fn_cmd_queue_post"] = None  # never auto-promote

    out["divisions"] = try_divisions(p, pe)
    if args.heap:
        army_vts = [O.PROVEN_STATIC["CArmy_vtable"]] + list(
            O.PROVEN_STATIC.get("CArmy_vtable_mi") or []
        )
        unit_vts = [O.PROVEN_STATIC["CUnit_vtable"]]
        ag = R.exact_type(pe, "CArmyGroup")
        ag_vts = [v["vtable_rva"] for v in (ag or {}).get("vtables") or []]
        out["armies"] = {
            "CArmy": heap_counts(p, army_vts, "CArmy"),
            "CUnit": heap_counts(p, unit_vts, "CUnit"),
        }
        if ag_vts:
            out["armies"]["CArmyGroup"] = heap_counts(p, ag_vts, "CArmyGroup")

    text = json.dumps(out, indent=2)
    print(text)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        open(args.out, "w", encoding="utf-8").write(text)
    p.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
