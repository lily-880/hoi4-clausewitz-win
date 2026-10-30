#!/usr/bin/env python3
"""Phase 2n: full-heap READ-ONLY hunt for FN_CMD_QUEUE_POST / live Command owners.

Catalog Command/Queue-ish RTTI, resolve vtables, heap-scan live instances,
then backref-scan sample CCommand* to find owner objects that may be queues.
NEVER posts/writes. FN_CMD_QUEUE_POST stays null unless independently proven.
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import sys
import time
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "calling"))

import config  # noqa: E402
import offsets as O  # noqa: E402
from pe import PE  # noqa: E402
from mem import Proc, find_pid  # noqa: E402
from msvc_rtti import scan_type_names, find_col_and_vtable, demangle_simple  # noqa: E402
from gamestate import detect_session, _rtti_name_from_vtable, _pdx_array  # noqa: E402


KEYWORDS = (
    "Command",
    "Queue",
    "CmdList",
    "OrderQueue",
    "ActionQueue",
    "Dispatcher",
    "Listener",
)


def catalog_interesting(pe: PE, limit_per: int = 80) -> list:
    seen = set()
    out = []
    for kw in KEYWORDS:
        for h in scan_type_names(pe, kw, limit=limit_per):
            n = h["name"]
            if n in seen or len(n) > 96:
                continue
            seen.add(n)
            info = find_col_and_vtable(pe, h["td_rva"])
            vts = []
            for v in info.get("vtables") or []:
                vr = v.get("vtable_rva")
                if vr and vr not in vts:
                    vts.append(vr)
            out.append(
                {
                    "name": n,
                    "plain": demangle_simple(n),
                    "td_rva": h["td_rva"],
                    "vtables": vts[:6],
                }
            )
    out.sort(key=lambda x: x["name"])
    return out


def heap_scan_needles(p: Proc, needles: dict, max_samples: int = 4, chunk: int = 4 << 20) -> dict:
    counts = {k: 0 for k in needles}
    samples = {k: [] for k in needles}
    scanned = 0
    t0 = time.time()
    for m in p.regions(writable=True, min_size=0x1000):
        start, end = m["start"], m["end"]
        if p.base <= start < p.base + p.image_size:
            continue
        pos = start
        while pos < end:
            nread = min(chunk, end - pos)
            data = p.try_read(pos, nread)
            scanned += nread
            if data:
                for k, needle in needles.items():
                    off = 0
                    while True:
                        i = data.find(needle, off)
                        if i < 0:
                            break
                        if i % 8 == 0:
                            counts[k] += 1
                            if len(samples[k]) < max_samples:
                                samples[k].append(pos + i)
                        off = i + 8
            pos += nread
    return {
        "scanned_mb": scanned >> 20,
        "elapsed_s": round(time.time() - t0, 1),
        "counts": {k: v for k, v in counts.items() if v},
        "samples": {k: [hex(x) for x in v] for k, v in samples.items() if v},
        "total_hits": sum(counts.values()),
    }


def backref_scan(p: Proc, targets: list, max_owners_per: int = 8, chunk: int = 4 << 20) -> dict:
    if not targets:
        return {"owners": [], "scanned_mb": 0}
    needles = {t: struct.pack("<Q", t) for t in targets}
    owners = {t: [] for t in targets}
    scanned = 0
    t0 = time.time()
    done = False
    for m in p.regions(writable=True, min_size=0x1000):
        if done:
            break
        start, end = m["start"], m["end"]
        if p.base <= start < p.base + p.image_size:
            continue
        pos = start
        while pos < end:
            nread = min(chunk, end - pos)
            data = p.try_read(pos, nread)
            scanned += nread
            if data:
                for t, needle in needles.items():
                    if len(owners[t]) >= max_owners_per:
                        continue
                    off = 0
                    while len(owners[t]) < max_owners_per:
                        i = data.find(needle, off)
                        if i < 0:
                            break
                        if i % 8 == 0:
                            slot = pos + i
                            if slot != t:
                                owners[t].append(slot)
                        off = i + 8
            pos += nread
            if all(len(owners[t]) >= max_owners_per for t in targets):
                done = True
                break
    classified = []
    for t, slots in owners.items():
        for slot in slots:
            entry = {"cmd": hex(t), "slot": hex(slot), "delta_from_cmd": slot - t}
            for back in (0, 8, 16, 24, 32, 40, 48, 64, 0x80, 0x100):
                cand = slot - back
                arr = _pdx_array(p, cand)
                if (
                    arr
                    and arr["data"] == slot
                    and 0 < arr["size"] <= 100000
                    and arr["size"] <= arr["capacity"]
                ):
                    entry["array_at"] = hex(cand)
                    entry["array_size"] = arr["size"]
                    entry["array_cap"] = arr["capacity"]
                    break
            for base_off in (
                0, 8, 0x10, 0x18, 0x20, 0x28, 0x30, 0x40, 0x50, 0x60, 0x80, 0xA0, 0x100, 0x200
            ):
                ob = slot - base_off
                if ob < 0x10000:
                    continue
                vb = p.try_read(ob, 8)
                if not vb:
                    continue
                vt = struct.unpack_from("<Q", vb, 0)[0]
                if not (p.base <= vt < p.base + p.image_size):
                    continue
                entry.setdefault("owner_hyps", []).append(
                    {"obj": hex(ob), "vt": hex(vt), "off_to_slot": base_off}
                )
                if len(entry.get("owner_hyps") or []) >= 4:
                    break
            classified.append(entry)
    return {
        "scanned_mb": scanned >> 20,
        "elapsed_s": round(time.time() - t0, 1),
        "owners": classified,
    }


def enrich_owners_rtti(pe: PE, p: Proc, back: dict) -> None:
    for e in back.get("owners") or []:
        for h in e.get("owner_hyps") or []:
            vt = int(h["vt"], 16)
            h["rtti"] = _rtti_name_from_vtable(pe, vt - p.base)


def inspect_cmd_sample(pe: PE, p: Proc, cmd: int) -> dict:
    vt = struct.unpack_from("<Q", p.try_read(cmd, 8) or b"\0" * 8, 0)[0]
    rtti = (
        _rtti_name_from_vtable(pe, vt - p.base)
        if p.base <= vt < p.base + p.image_size
        else None
    )
    blob = p.try_read(cmd, 0x80) or b""
    fields = []
    for off in range(0, len(blob) - 7, 8):
        v = struct.unpack_from("<Q", blob, off)[0]
        kind = "?"
        if p.base <= v < p.base + p.image_size:
            kind = "img"
        elif v > 0x10000:
            kind = "heap?"
        fields.append({"off": hex(off), "val": hex(v), "kind": kind})
    return {"ptr": hex(cmd), "vt": hex(vt), "rtti": rtti, "fields": fields[:16]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--out", default="research/re-dumps/phase2n_cmd_heap_hunt.json")
    ap.add_argument("--max-cmd-samples", type=int, default=6)
    args = ap.parse_args()

    pe = PE(config.binary_path(required=True))
    out = {
        "phase": "2n",
        "read_only": True,
        "FN_CMD_QUEUE_POST": None,
        "rtti_interesting": [],
        "heap": {},
        "backrefs": {},
        "cmd_samples": [],
        "notes": [],
    }

    interesting = catalog_interesting(pe)
    out["rtti_interesting"] = interesting
    out["rtti_count"] = len(interesting)
    out["rtti_queueish"] = [
        x
        for x in interesting
        if any(k in x["plain"] for k in ("Queue", "CmdList", "Dispatcher"))
    ]
    out["rtti_commandish"] = [
        x for x in interesting if "Command" in x["plain"] and "Queue" not in x["plain"]
    ][:60]

    if not args.live:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(
            json.dumps(
                {
                    "FN": None,
                    "rtti": len(interesting),
                    "queueish": [x["plain"] for x in out["rtti_queueish"][:40]],
                },
                indent=2,
            )
        )
        return 0

    p = Proc(find_pid(config.EXE_NAME))
    sess = detect_session(p, pe)
    out["session"] = {
        "pid": p.pid,
        "in_game": sess.get("in_game"),
        "idler": (sess.get("signals") or {}).get("idler_class"),
        "gs": (sess.get("signals") or {}).get("gs_ptr"),
    }

    needles = {}
    cmd_vt = O.PROVEN_STATIC.get("CCommand_vtable", 0x279F4A0)
    needles["CCommand"] = struct.pack("<Q", p.base + cmd_vt)

    for x in out["rtti_queueish"][:16]:
        for vt in x["vtables"][:2]:
            label = "%s_%s" % (x["plain"][:40], hex(vt))
            needles[label] = struct.pack("<Q", p.base + vt)

    for plain in (
        "CChatCommand",
        "CClientPingCommand",
        "CChangeGameSpeedCommand",
        "CSetPauseCommand",
        "CHumanCommand",
        "CNavalMissionCommand",
    ):
        matches = [x for x in interesting if x["plain"] == plain]
        for x in matches[:1]:
            for vt in x["vtables"][:1]:
                needles["%s_%s" % (plain, hex(vt))] = struct.pack("<Q", p.base + vt)

    print("heap-scanning %d needles..." % len(needles), flush=True)
    heap = heap_scan_needles(p, needles, max_samples=args.max_cmd_samples)
    out["heap"] = heap
    print(
        "heap done MB=%s hits=%s s=%s"
        % (heap.get("scanned_mb"), heap.get("total_hits"), heap.get("elapsed_s")),
        flush=True,
    )

    cmd_ptrs = []
    for label, samples in (heap.get("samples") or {}).items():
        if label.startswith("CCommand") or "Command" in label:
            for s in samples:
                cmd_ptrs.append(int(s, 16))
    # unique preserve order
    seen = set()
    uniq = []
    for c in cmd_ptrs:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    cmd_ptrs = uniq[: args.max_cmd_samples]
    out["cmd_samples"] = [inspect_cmd_sample(pe, p, c) for c in cmd_ptrs]

    print("backref-scanning %d cmds..." % len(cmd_ptrs), flush=True)
    back = backref_scan(p, cmd_ptrs, max_owners_per=6)
    enrich_owners_rtti(pe, p, back)
    out["backrefs"] = back
    print(
        "backrefs done MB=%s owners=%s s=%s"
        % (back.get("scanned_mb"), len(back.get("owners") or []), back.get("elapsed_s")),
        flush=True,
    )

    rtti_set = {}
    for e in back.get("owners") or []:
        for h in e.get("owner_hyps") or []:
            nm = h.get("rtti") or "?"
            rtti_set[nm] = rtti_set.get(nm, 0) + 1
        if e.get("array_at"):
            out.setdefault("array_owners", []).append(
                {"cmd": e["cmd"], "array_at": e["array_at"], "size": e.get("array_size")}
            )
    out["owner_rtti_hist"] = dict(sorted(rtti_set.items(), key=lambda kv: -kv[1])[:40])
    out["notes"].append("FN_CMD_QUEUE_POST remains null — heap owners catalogued only")
    out["notes"].append("posting DISABLED")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    summary = {
        "FN_CMD_QUEUE_POST": None,
        "rtti_interesting": len(interesting),
        "queueish": [x["plain"] for x in out["rtti_queueish"][:30]],
        "heap_counts": heap.get("counts"),
        "heap_mb": heap.get("scanned_mb"),
        "owner_rtti_hist": out["owner_rtti_hist"],
        "array_owners": out.get("array_owners"),
        "cmd_sample_rtti": [c.get("rtti") for c in out["cmd_samples"]],
    }
    Path("research/re-dumps/phase2n_summary.txt").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2)[:4000])
    p.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
