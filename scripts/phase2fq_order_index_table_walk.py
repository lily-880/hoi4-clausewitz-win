#!/usr/bin/env python3
"""Phase 2fq: order_index→order-object table walk (RO) + bounded NF peek if thin.
No Post. Never 5x. allow_post must stay False.
"""
from __future__ import annotations

import json
import struct
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

from config import allow_post
from process import Backend, find_pid
import cmd_layout
import post_abi
from handle import resolve_handle, HANDLE_TYPE_ARMY

assert allow_post() is False, "allow_post must stay False"

ASSIGN_VT = cmd_layout.ORDERS["COrderAssignCommand"]["vt"]
EXECUTE_VT = cmd_layout.ORDERS["COrderExecuteCommand"]["vt"]
DELETE_VT = cmd_layout.ORDERS["COrderDeleteCommand"]["vt"]
NF_VT = cmd_layout.ORDERS["COrderNewFallbackCommand"]["vt"]
RF_VT = int(cmd_layout.ISVALID_PATHS["COrderReplaceFallbackCommands"]["vt"])

RTTI_VT = {
    "COrdersGroup": 0x29CED90,
    "COrdersGroupMember": 0x29CED48,
    "COrderInstance": 0x2A02558,
}

CA_HANDLE = 0x18
CA_PROVINCE = 0x28
CA_TAG = 0x1E0
PRIOR_OI6_ARMIES = {51, 1810, 1811, 1815, 1816}


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def try_read(b, a, n):
    try:
        return b.read(a, n)
    except Exception:
        return None


def live_meta(b, base):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    hours = struct.unpack("<i", b.read(gs + 0x484, 4))[0]
    d = datetime(1936, 1, 1) + timedelta(hours=int(hours))
    return {
        "pid": find_pid(),
        "hours": hours,
        "ui_date": d.strftime("%Y-%m-%d %H:00"),
        "speed_policy": "pause-or-1x only (never change speed)",
        "scenario": "ITA@1x order_index→object walk (no Post)",
    }


def decode_units(b, base, data, size):
    out = {"army": [], "other": [], "army_indices": []}
    if not data or size <= 0 or size > 64:
        return out
    blob = try_read(b, data, size * 8)
    if not blob:
        out["read_error"] = True
        return out
    for i in range(size):
        typ, ix = struct.unpack_from("<II", blob, i * 8)
        el = {"type": typ, "index": ix, "as_list": [typ, ix]}
        if typ == HANDLE_TYPE_ARMY:
            out["army_indices"].append(ix)
            try:
                ptr = resolve_handle(b, typ, ix, base)
                if ptr:
                    el["resolved"] = hex(ptr)
                    echo = list(struct.unpack("<II", b.read(ptr + CA_HANDLE, 8)))
                    el["echo"] = echo
                    el["echo_ok"] = echo == [typ, ix]
                    el["prov"] = u32(b, ptr + CA_PROVINCE)
                    el["tag"] = u32(b, ptr + CA_TAG)
            except Exception as e:
                el["err"] = str(e)
            out["army"].append(el)
        else:
            out["other"].append(el)
    return out


def stage_sight(b, base, seconds: float) -> dict:
    """Poll CSession stage array (proven 2fp path)."""
    sess = u64(b, base + post_abi.G_SESSION)
    watch = {
        ASSIGN_VT: "COrderAssignCommand",
        EXECUTE_VT: "COrderExecuteCommand",
        DELETE_VT: "COrderDeleteCommand",
        NF_VT: "COrderNewFallbackCommand",
        RF_VT: "COrderReplaceFallbackCommands",
    }
    t0 = time.time()
    sight_counts: dict[str, int] = {}
    assigns, executes, deletes, nfs, rfs = [], [], [], [], []
    seen = set()
    polls = 0
    while time.time() - t0 < seconds:
        polls += 1
        try:
            stage = u64(b, sess + post_abi.CSession_STAGE_ARRAY)
            scount = u32(b, sess + post_abi.CSession_STAGE_COUNT)
        except Exception:
            continue
        if not stage or not (0 < scount < 256):
            continue
        for i in range(scount):
            try:
                ptr = u64(b, stage + i * 8)
                vt = u64(b, ptr)
            except Exception:
                continue
            rva = vt - base
            name = watch.get(rva)
            if not name:
                continue
            sight_counts[name] = sight_counts.get(name, 0) + 1
            key = (name, ptr)
            if key in seen:
                continue
            seen.add(key)
            t = round(time.time() - t0, 3)
            try:
                if name == "COrderAssignCommand" and len(assigns) < 8:
                    data = u64(b, ptr + 0x28)
                    size = struct.unpack("<i", b.read(ptr + 0x34, 4))[0]
                    oi = u32(b, ptr + 0x48)
                    amin = b.read(ptr + 0x4C, 1)[0]
                    units = decode_units(b, base, data, size)
                    assigns.append(
                        {
                            "source": f"stage[{i}]",
                            "addr": hex(ptr),
                            "t": t,
                            "order_index": oi,
                            "assign_to_minimum_order": amin,
                            "units_size": size,
                            "units": units,
                            "army_lists": [e["as_list"] for e in units["army"]],
                        }
                    )
                elif name == "COrderExecuteCommand" and len(executes) < 8:
                    executes.append(
                        {
                            "source": f"stage[{i}]",
                            "addr": hex(ptr),
                            "t": t,
                            "order_index": u32(b, ptr + 0x30),
                        }
                    )
                elif name == "COrderDeleteCommand" and len(deletes) < 8:
                    deletes.append(
                        {
                            "source": f"stage[{i}]",
                            "addr": hex(ptr),
                            "t": t,
                            "order_index": u32(b, ptr + 0x30),
                        }
                    )
                elif name == "COrderNewFallbackCommand" and len(nfs) < 6:
                    raw = try_read(b, ptr, 0x60)
                    sub_t, sub_i = u32(b, ptr + 0x28), u32(b, ptr + 0x2C)
                    nfs.append(
                        {
                            "source": f"stage[{i}]",
                            "addr": hex(ptr),
                            "t": t,
                            "subject_handle": [sub_t, sub_i],
                            "subject_type_hex": hex(sub_t),
                            "hex": raw.hex() if raw else None,
                            "units_size": struct.unpack("<i", b.read(ptr + 0x3C, 4))[0],
                            "provinces_size": struct.unpack("<i", b.read(ptr + 0x54, 4))[0],
                        }
                    )
                elif name == "COrderReplaceFallbackCommands" and len(rfs) < 6:
                    raw = try_read(b, ptr, 0x60)
                    rfs.append(
                        {
                            "source": f"stage[{i}]",
                            "addr": hex(ptr),
                            "t": t,
                            "hex": raw.hex() if raw else None,
                        }
                    )
            except Exception as e:
                if name == "COrderAssignCommand" and len(assigns) < 8:
                    assigns.append({"addr": hex(ptr), "t": t, "error": str(e)})
        if polls % 500 == 0:
            time.sleep(0)
    return {
        "sess": hex(sess),
        "polls": polls,
        "elapsed_s": round(time.time() - t0, 1),
        "sight_counts": sight_counts,
        "assigns": assigns,
        "executes": executes,
        "deletes": deletes,
        "fallbacks": nfs,
        "replace_fallbacks": rfs,
    }


def writable_regions(b, base):
    out = []
    for m in b.regions():
        perms = m.get("perms") or ""
        if "w" not in perms:
            continue
        start, end = m["start"], m["end"]
        if base <= start < base + b.image_size:
            continue
        if end - start < 0x1000:
            continue
        out.append((start, end))
    return out


def heap_scan_vt(b, base, needles, max_samples=20, chunk=4 << 20, time_budget_s=75.0):
    counts = {k: 0 for k in needles}
    samples = {k: [] for k in needles}
    scanned = 0
    t0 = time.time()
    packed = {k: struct.pack("<Q", base + rva) for k, rva in needles.items()}
    for start, end in writable_regions(b, base):
        if time.time() - t0 > time_budget_s:
            break
        pos = start
        while pos < end:
            if time.time() - t0 > time_budget_s:
                break
            nread = min(chunk, end - pos)
            data = try_read(b, pos, nread)
            scanned += nread
            if data:
                for k, needle in packed.items():
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
        "counts": counts,
        "samples": {k: [hex(x) for x in v] for k, v in samples.items()},
        "sample_addrs": samples,
    }


def peek_object(b, addr, n=0x100):
    blob = try_read(b, addr, n)
    if not blob:
        return {"addr": hex(addr), "read_error": True}
    u32s = list(struct.unpack("<" + "I" * (len(blob) // 4), blob[: len(blob) // 4 * 4]))
    oi_offs = [i * 4 for i, v in enumerate(u32s) if v in (1, 6, 25)]
    army_offs = [i * 4 for i, v in enumerate(u32s) if v in PRIOR_OI6_ARMIES]
    return {
        "addr": hex(addr),
        "hex_head": blob[:64].hex(),
        "oi_edge_offs": oi_offs[:16],
        "u32_at_oi_edges": {hex(o): u32s[o // 4] for o in oi_offs[:16]},
        "prior_army_idx_offs": army_offs[:16],
    }


def backref_owners(b, base, targets, max_per=10, chunk=4 << 20, time_budget_s=55.0):
    needles = {t: struct.pack("<Q", t) for t in targets}
    owners = {t: [] for t in targets}
    scanned = 0
    t0 = time.time()
    for start, end in writable_regions(b, base):
        if time.time() - t0 > time_budget_s:
            break
        if all(len(owners[t]) >= max_per for t in targets):
            break
        pos = start
        while pos < end:
            if time.time() - t0 > time_budget_s:
                break
            if all(len(owners[t]) >= max_per for t in targets):
                break
            nread = min(chunk, end - pos)
            data = try_read(b, pos, nread)
            scanned += nread
            if data:
                for t, needle in needles.items():
                    if len(owners[t]) >= max_per:
                        continue
                    off = 0
                    while len(owners[t]) < max_per:
                        i = data.find(needle, off)
                        if i < 0:
                            break
                        if i % 8 == 0:
                            slot = pos + i
                            if slot != t:
                                owners[t].append(slot)
                        off = i + 8
            pos += nread
    return {
        "scanned_mb": scanned >> 20,
        "elapsed_s": round(time.time() - t0, 1),
        "owners": {hex(t): [hex(s) for s in v] for t, v in owners.items()},
    }


def try_index_from_slot(b, slot, obj):
    """Recover CPdxArray {data,cap,size,alloc} whose data[i] slot holds obj."""
    results = []
    window = 0x400
    start = max(0, slot - window)
    blob = try_read(b, start, window + 8)
    if not blob:
        return results
    rel = slot - start
    for hoff in range(0, rel, 8):
        if hoff + 0x18 > len(blob):
            break
        data, cap, size, alloc = struct.unpack_from("<QiiQ", blob, hoff)
        if size < 0 or size > 4096 or cap < size or cap > 8192 or data == 0:
            continue
        if data <= slot < data + size * 8 and (slot - data) % 8 == 0:
            idx = (slot - data) // 8
            results.append(
                {
                    "array_header": hex(start + hoff),
                    "data": hex(data),
                    "capacity": cap,
                    "size": size,
                    "index": idx,
                    "obj": hex(obj),
                }
            )
    return results


def main():
    assert allow_post() is False
    b = Backend()
    base = int(b.image_base)
    live0 = live_meta(b, base)
    print("[2fq] live", live0["ui_date"], "pid", live0["pid"], flush=True)

    # A: short Assign sight (15s) for live oi anchors, then heap walk
    print("[2fq] Assign stage sight 15s…", flush=True)
    sight_short = stage_sight(b, base, seconds=15.0)
    live_ois = sorted({a["order_index"] for a in sight_short["assigns"] if "order_index" in a})
    live_armies = sorted(
        {
            ix
            for a in sight_short["assigns"]
            for ix in (a.get("units") or {}).get("army_indices") or []
        }
    )
    print(
        "[2fq] assigns",
        len(sight_short["assigns"]),
        "ois",
        live_ois,
        "counts",
        sight_short["sight_counts"],
        flush=True,
    )

    print("[2fq] heap scan order RTTI ≤75s…", flush=True)
    heap = heap_scan_vt(b, base, RTTI_VT, max_samples=20, time_budget_s=75.0)
    print("[2fq] heap", heap["counts"], "mb", heap["scanned_mb"], flush=True)

    peeks = {}
    for kind, addrs in heap["sample_addrs"].items():
        peeks[kind] = [peek_object(b, a) for a in addrs[:8]]

    table_hits = []
    inst_addrs = heap["sample_addrs"].get("COrderInstance", [])[:6]
    grp_addrs = heap["sample_addrs"].get("COrdersGroup", [])[:4]
    targets = inst_addrs + grp_addrs
    backref = {"note": "no samples"}
    if targets:
        print("[2fq] backref ≤55s for", len(targets), "objs…", flush=True)
        backref = backref_owners(b, base, targets, max_per=10, time_budget_s=55.0)
        for t in targets:
            kind = "COrderInstance" if t in inst_addrs else "COrdersGroup"
            for slot_hex in backref["owners"].get(hex(t), [])[:10]:
                slot = int(slot_hex, 16)
                for cand in try_index_from_slot(b, slot, t):
                    cand["obj_kind"] = kind
                    cand["matches_live_oi"] = (cand["index"] in live_ois) if live_ois else None
                    cand["matches_prior_oi6"] = cand["index"] == 6
                    table_hits.append(cand)
        print("[2fq] table candidates", len(table_hits), flush=True)

    matched = [c for c in table_hits if c.get("matches_live_oi") or c.get("matches_prior_oi6")]

    # B: bounded NF/RF if A thin
    nf_extra = None
    nf_ran = False
    a_thin = (heap["counts"].get("COrderInstance", 0) == 0 and heap["counts"].get("COrdersGroup", 0) == 0) or not matched
    if a_thin:
        # credit any NF already seen in short sight; else watch more
        if sight_short["fallbacks"] or sight_short["replace_fallbacks"]:
            nf_extra = {
                "skipped_extra": True,
                "reason": "hits already in short sight",
                "fallbacks": sight_short["fallbacks"],
                "replace_fallbacks": sight_short["replace_fallbacks"],
            }
        else:
            print("[2fq] A thin — NF/RF stage sight ≤70s…", flush=True)
            nf_ran = True
            nf_extra = stage_sight(b, base, seconds=70.0)
            # keep only NF/RF fields to limit noise
            nf_extra = {
                "elapsed_s": nf_extra["elapsed_s"],
                "sight_counts": nf_extra["sight_counts"],
                "fallbacks": nf_extra["fallbacks"],
                "replace_fallbacks": nf_extra["replace_fallbacks"],
                "assigns_n": len(nf_extra["assigns"]),
                "assign_ois": sorted(
                    {a["order_index"] for a in nf_extra["assigns"] if "order_index" in a}
                ),
            }
            # merge late assigns into live_ois for report
            for a in nf_extra.get("assign_ois") or []:
                if a not in live_ois:
                    live_ois.append(a)
            live_ois = sorted(set(live_ois))
            print(
                "[2fq] NF hits",
                len(nf_extra.get("fallbacks") or []),
                "RF",
                len(nf_extra.get("replace_fallbacks") or []),
                flush=True,
            )

    live1 = live_meta(b, base)

    works = [
        "allow_post False; never 5x; no Post/inject/tool-gate/2fb",
        f"heap COrderInstance={heap['counts'].get('COrderInstance', 0)} "
        f"COrdersGroup={heap['counts'].get('COrdersGroup', 0)} "
        f"COrdersGroupMember={heap['counts'].get('COrdersGroupMember', 0)}",
        f"stage Assign n={len(sight_short['assigns'])} ois={live_ois} "
        f"sight_counts={sight_short['sight_counts']}",
    ]
    nf_hits = list((nf_extra or {}).get("fallbacks") or []) + list(
        (nf_extra or {}).get("replace_fallbacks") or []
    )
    if matched:
        works.append(
            "order_index→object: CPdxArray slot index matches live/prior oi; "
            f"sample index={matched[0]['index']} obj={matched[0]['obj']} "
            f"header={matched[0]['array_header']} kind={matched[0]['obj_kind']}"
        )
        result = "order_index_table_walk_partial"
    elif table_hits:
        works.append(
            f"CPdxArray owner slots ({len(table_hits)}) found; index≠live/prior oi — raw only, no invent"
        )
        result = "table_owners_unmatched_oi"
    elif heap["counts"].get("COrderInstance", 0) or heap["counts"].get("COrdersGroup", 0):
        works.append("order RTTI heap live; backref/index inconclusive this slice")
        result = "heap_live_walk_inconclusive"
    else:
        works.append(
            "order RTTI heap=0 (same class as 2cw) despite Assign oi traffic — "
            "battle-plan order_index may not land in COrderInstance/COrdersGroup"
        )
        result = "heap_empty_ceiling"

    if nf_hits:
        sh = nf_hits[0].get("subject_handle") or nf_hits[0].get("hex")
        works.append(f"NF/RF midflight hit n={len(nf_hits)} first={sh}")
        if result.startswith("heap_empty"):
            result = "nf_midflight_partial"

    stubbed = [
        "in-process ring embed",
        "2fb recipe execution",
        "ordinary CMove live leaf",
        "SAFE_POST / ALLOW_POST",
        "self-MOVE",
        "tool-gate open",
        "Post inject",
        "path-vector nonempty",
        "HourlyTick abuse",
        "Capstone/121 re-churn",
    ]
    if not nf_hits:
        stubbed.append("NewFallback subject type-id table")
        stubbed.append("live midflight NewFallback hex")
    if not matched:
        stubbed.append("order_index→COrder* proven catalog root")

    if matched:
        next_b = (
            "NON-Post: confirm RTTI of object owning CPdxArray header; "
            "map Execute order_index@+0x30→same slot; still NO ALLOW_POST"
        )
    elif nf_hits and nf_hits[0].get("subject_handle"):
        next_b = (
            "NON-Post: map NF subject_handle type-id "
            f"{nf_hits[0].get('subject_type_hex')} via handle catalogs; still NO ALLOW_POST"
        )
    else:
        next_b = (
            "NON-Post RO ceiling: order RTTI heap empty + no NF/RF midflight this window; "
            "next cheapest=army→TH_FRONTS pointer RO or repeat short NF watch after plan change; "
            "still NO ALLOW_POST"
        )

    report = {
        "phase": "2fq",
        "ts": datetime.now(timezone.utc).isoformat(),
        "result": result,
        "allow_post": False,
        "tool_gate": "CLOSED",
        "never_5x": True,
        "executed_2fb_recipe": False,
        "parent_sha_base": "7168db5",
        "rtti_vt_rvas": {k: hex(v) for k, v in RTTI_VT.items()},
        "rf_vt": hex(RF_VT),
        "live_at_start": live0,
        "live": live1,
        "sight_short": sight_short,
        "live_order_indices": live_ois,
        "live_army_indices": live_armies,
        "heap": {
            "scanned_mb": heap["scanned_mb"],
            "elapsed_s": heap["elapsed_s"],
            "counts": heap["counts"],
            "samples": heap["samples"],
        },
        "object_peeks": peeks,
        "backref": {
            k: backref[k]
            for k in backref
            if k in ("scanned_mb", "elapsed_s", "owners", "note")
        },
        "table_walk_candidates": table_hits[:40],
        "matched_oi_table": matched[:20],
        "nf_midflight_ran": nf_ran,
        "nf_midflight": nf_extra,
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_b,
    }
    (ROOT / "reports").mkdir(parents=True, exist_ok=True)
    (ROOT / "reports" / "phase2fq_order_index_table_walk.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    summary = {
        "phase": "2fq",
        "result": result,
        "allow_post": False,
        "pid": live1["pid"],
        "ui_date": live1["ui_date"],
        "hours": live1["hours"],
        "scenario": live1["scenario"],
        "heap_counts": heap["counts"],
        "live_order_indices": live_ois,
        "matched_n": len(matched),
        "table_candidates_n": len(table_hits),
        "nf_midflight_ran": nf_ran,
        "nf_hits": len(nf_hits),
        "sight_counts_short": sight_short["sight_counts"],
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_b,
        "parent_sha_base": "7168db5",
    }
    (ROOT / "reports" / "phase2fq_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
