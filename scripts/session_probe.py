#!/usr/bin/env python3
"""Bounded live session probe: lobby vs in-campaign via idler/GS vptrs.

Read-only. Writes research/re-dumps/session_probe.json.
Exits 0 if in-campaign signal, 3 if lobby/menu, 1 if not running.
"""
from __future__ import annotations

import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "calling"))

from mem import Proc, find_pid  # noqa: E402
import config  # noqa: E402
import offsets as O  # noqa: E402

VT = {
    "CGameState": O.PROVEN_STATIC["CGameState_vtable"],
    "CGameState_sec": O.PROVEN_STATIC["CGameState_vtable_secondary"],
    "CCurrentGameState": O.PROVEN_STATIC["CCurrentGameState_vtable"],
    "CInGameIdler": O.PROVEN_STATIC["CInGameIdler_vtable"],
    "CGameIdler": O.PROVEN_STATIC["CGameIdler_vtable"],
}

MAX_REGION = 16 << 20
MAX_HITS = 8


def scan_heap_vptrs(p: Proc, vt_rvas: dict) -> dict:
    rt = {n: p.base + r for n, r in vt_rvas.items()}
    needles = {n: struct.pack("<Q", a) for n, a in rt.items()}
    hits = {n: [] for n in vt_rvas}
    scanned = 0
    for m in p.regions(writable=True, min_size=0x1000):
        start, end = m["start"], m["end"]
        size = end - start
        if size > MAX_REGION:
            continue
        if p.base <= start < p.base + p.image_size:
            continue
        data = p.try_read(start, size)
        if not data:
            continue
        scanned += len(data)
        for n, needle in needles.items():
            if len(hits[n]) >= MAX_HITS:
                continue
            off = 0
            while len(hits[n]) < MAX_HITS:
                i = data.find(needle, off)
                if i < 0:
                    break
                if i % 8 == 0:
                    hits[n].append(start + i)
                off = i + 8
        if all(len(hits[n]) >= MAX_HITS for n in hits):
            break
    return scanned, {n: [hex(a) for a in addrs] for n, addrs in hits.items()}


def probe_static_candidates(p: Proc, candidates: list) -> list:
    """If phase2c wrote .data store RVAs, read each slot and check object vptr."""
    gs_vts = {
        p.base + O.PROVEN_STATIC["CGameState_vtable"],
        p.base + O.PROVEN_STATIC["CGameState_vtable_secondary"],
        p.base + O.PROVEN_STATIC["CCurrentGameState_vtable"],
        p.base + O.PROVEN_STATIC["CCurrentGameState_vtable_secondary"],
    }
    from gamestate import looks_like_gamestate

    results = []
    for c in candidates[:40]:
        rva = int(c["global_rva_candidate"], 16)
        slot = p.base + rva
        ptr = p.ptr(slot)
        entry = {"global_rva": hex(rva), "slot": hex(slot), "value": hex(ptr) if ptr else None}
        if ptr and ptr > 0x10000:
            obj = p.try_read(ptr, 8)
            if obj:
                vptr = struct.unpack_from("<Q", obj, 0)[0]
                entry["vptr"] = hex(vptr)
                entry["vptr_is_gs"] = vptr in gs_vts
                if entry["vptr_is_gs"]:
                    entry["probe"] = looks_like_gamestate(p, ptr)
        results.append(entry)
    return results


def main():
    pid = find_pid(config.EXE_NAME)
    out_path = os.path.join(ROOT, "research", "re-dumps", "session_probe.json")
    if not pid:
        json.dump({"running": False, "session": "not_running"}, open(out_path, "w"), indent=2)
        print(json.dumps({"running": False}))
        return 1
    p = Proc(pid)
    scanned, hits = scan_heap_vptrs(p, VT)
    in_campaign = bool(hits.get("CInGameIdler") or hits.get("CGameState") or hits.get("CCurrentGameState"))
    lobby = (not in_campaign) and bool(hits.get("CGameIdler") or True)
    session = "in_campaign" if in_campaign else "lobby_or_menu_or_unloaded"

    cand_path = os.path.join(ROOT, "research", "re-dumps", "phase2c_recover.json")
    cand_results = []
    verified = None
    if os.path.isfile(cand_path):
        data = json.load(open(cand_path, encoding="utf-8"))
        cands = data.get("G_GAMESTATE_static_candidates") or []
        cand_results = probe_static_candidates(p, cands)
        for r in cand_results:
            if r.get("vptr_is_gs") and r.get("probe", {}).get("ok"):
                verified = r
                # write runtime override (gitignored pattern) — heuristic live verify
                ov = os.path.join(ROOT, "calling", "offsets_runtime.json")
                json.dump(
                    {
                        "G_GAMESTATE": int(r["global_rva"], 16),
                        "status": "live-verified-heuristic",
                        "probe": r["probe"],
                        "session": session,
                    },
                    open(ov, "w"),
                    indent=2,
                )
                O.WINDOWS_GLOBALS["G_GAMESTATE"] = int(r["global_rva"], 16)
                break

    report = {
        "running": True,
        "pid": pid,
        "image_base": hex(p.base),
        "session": session,
        "guidance": O.TARGET,
        "note": (
            "Load a campaign/save until the map is visible, then re-run session-probe / live-gs."
            if session != "in_campaign"
            else "In-campaign signal present; check G_GAMESTATE candidates."
        ),
        "heap_vptr_hits": hits,
        "scanned_bytes": scanned,
        "static_candidate_probes": cand_results[:20],
        "verified_G_GAMESTATE": verified,
        "command_queue": "DISABLED",
    }
    json.dump(report, open(out_path, "w", encoding="utf-8"), indent=2)
    print(json.dumps({
        "session": session,
        "pid": pid,
        "hits": {k: len(v) for k, v in hits.items()},
        "verified_G_GAMESTATE": verified["global_rva"] if verified else None,
    }, indent=2))
    p.close()
    return 0 if session == "in_campaign" else 3


if __name__ == "__main__":
    sys.exit(main())
