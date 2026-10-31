#!/usr/bin/env python3
"""Phase 2fx: interpret Instance+0x70 vs +0x88 structure (RO).
Fuller sample: set algebra, order, pair/edge hypothesis. No Post. Never 5x.
"""
from __future__ import annotations

import json
import struct
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
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
TYPE_OG = 0x35
CP_VT = 0x29EE248
CP_ID = 0xA4
INST_VT = 0x2A02558
MAX_SIGHT_S = 10.0
MAX_ARR = 256  # fuller than 2fw's 32/64 caps


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def try_read(b, a, n):
    try:
        return b.read(a, n)
    except Exception:
        return None


def read_cpdx(b, base, addr):
    raw = try_read(b, addr, 0x18)
    if not raw:
        return None
    data, cap, size = struct.unpack_from("<Qii", raw, 0)
    plausible = data > 0x10000 and 0 <= size <= 8192 and size <= max(cap, size)
    return {
        "data": data,
        "size": size,
        "cap": cap,
        "plausible": plausible,
        "sentinel": base <= data < base + b.image_size,
    }


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
        "scenario": "ITA@1x Instance+0x70 vs +0x88 structure (no Post)",
        "gs": hex(gs),
    }


def i32(b, a):
    return struct.unpack("<i", b.read(a, 4))[0]


def stage_watch(b, base, seconds: float = MAX_SIGHT_S):
    sess = u64(b, base + post_abi.G_SESSION)
    t0 = time.time()
    counts = {}
    assigns = []
    seen = set()
    while time.time() - t0 < seconds:
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
            if rva != ASSIGN_VT:
                continue
            counts["COrderAssignCommand"] = counts.get("COrderAssignCommand", 0) + 1
            if ptr in seen:
                continue
            seen.add(ptr)
            oi = u32(b, ptr + 0x48)
            size = i32(b, ptr + 0x34)
            data = u64(b, ptr + 0x28)
            armies = []
            if data and 0 < size <= 64:
                blob = try_read(b, data, size * 8)
                if blob:
                    for j in range(size):
                        typ, ix = struct.unpack_from("<II", blob, j * 8)
                        if typ == HANDLE_TYPE_ARMY:
                            armies.append(ix)
            assigns.append({"order_index": oi, "army_indices": armies, "t": round(time.time() - t0, 3)})
    return {"elapsed_s": round(time.time() - t0, 1), "sight_counts": counts, "assigns": assigns}


def sight_assign_ois(b, base, seconds=MAX_SIGHT_S):
    sight = stage_watch(b, base, seconds)
    ois = set()
    for a in sight["assigns"]:
        ois.add(int(a["order_index"]))
    # prior 2fw nonempty + common hist
    for oi in (5, 6, 9, 13, 17, 22, 25, 38, 40, 44, 68, 70):
        ois.add(oi)
    # prior report nonempty
    prev = ROOT / "reports" / "phase2fw_88_vs_70.json"
    if prev.exists():
        try:
            pr = json.loads(prev.read_text(encoding="utf-8"))
            for r in pr.get("rows") or []:
                if r.get("n70"):
                    ois.add(int(r["oi"]))
        except Exception:
            pass
    return sorted(ois), sight


def resolve_inst(b, base, oi):
    hdr = resolve_handle(b, TYPE_OG, oi, base)
    if not hdr:
        return None
    og = hdr + 0x10
    a98 = read_cpdx(b, base, og + 0x98)
    if not a98 or not a98["plausible"] or a98["size"] < 1 or a98["sentinel"]:
        return None
    inst = u64(b, a98["data"])
    if inst < 0x10000:
        return None
    try:
        vt = u64(b, inst) - base
    except Exception:
        return None
    if vt != INST_VT:
        return {"oi": oi, "og": hex(og), "inst": hex(inst), "vt_ok": False, "vt": hex(vt)}
    return {"oi": oi, "og": hex(og), "inst": inst, "inst_hex": hex(inst), "vt_ok": True}


def read_u32_arr(b, base, arr):
    if not arr or not arr["plausible"] or arr["size"] <= 0 or arr["sentinel"]:
        return []
    n = min(arr["size"], MAX_ARR)
    blob = try_read(b, arr["data"], n * 4)
    if not blob:
        return []
    return [struct.unpack_from("<I", blob, i * 4)[0] for i in range(n)]


def read_cprovince_ids(b, base, arr):
    if not arr or not arr["plausible"] or arr["size"] <= 0 or arr["sentinel"]:
        return [], 0, []
    n = min(arr["size"], MAX_ARR)
    blob = try_read(b, arr["data"], n * 8)
    if not blob:
        return [], 0, []
    ids = []
    ptrs = []
    vtok = 0
    for i in range(n):
        p = struct.unpack_from("<Q", blob, i * 8)[0]
        ptrs.append(p)
        if p < 0x10000:
            ids.append(None)
            continue
        try:
            vt = u64(b, p) - base
            if vt == CP_VT:
                vtok += 1
            ids.append(u32(b, p + CP_ID))
        except Exception:
            ids.append(None)
    return ids, vtok, ptrs


def analyze(u32s70, ids88):
    """Structural hypotheses; evidence only — no invent of field names beyond evidence."""
    ids88_clean = [x for x in ids88 if x is not None]
    set70 = set(u32s70)
    set88 = set(ids88_clean)
    out = {
        "n70": len(u32s70),
        "n88": len(ids88),
        "n88_clean": len(ids88_clean),
        "n70_unique": len(set70),
        "n88_unique": len(set88),
        "frac_70_in_88": (len(set70 & set88) / len(set70)) if set70 else None,
        "frac_88_in_70": (len(set70 & set88) / len(set88)) if set88 else None,
        "equal_as_sets": set70 == set88 and bool(set70),
        "70_subset_88": set70 <= set88 and bool(set70),
        "88_subset_70": set88 <= set70 and bool(set88),
    }

    # Multiset / duplicates in 88
    c88 = Counter(ids88_clean)
    out["dup_count_88"] = sum(1 for v in c88.values() if v > 1)
    out["max_freq_88"] = max(c88.values()) if c88 else 0
    out["top_freq_88"] = c88.most_common(5)

    # Pair / edge hypothesis: treat consecutive (even,odd) as undirected edges
    pairs = []
    if len(ids88_clean) >= 2 and len(ids88) == len(ids88_clean):
        # use raw ids88 including Nones skipped — prefer clean aligned if no None
        src = ids88_clean
    else:
        src = ids88_clean
    if len(src) >= 2:
        for i in range(0, len(src) - 1, 2):
            a, c = src[i], src[i + 1] if i + 1 < len(src) else None
            if c is not None:
                pairs.append((a, c))
    out["n88_even"] = (len(src) % 2 == 0)
    out["n_pairs"] = len(pairs)
    undirected = set()
    for a, c in pairs:
        undirected.add((min(a, c), max(a, c)))
    out["n_undirected_edges"] = len(undirected)
    nodes_from_pairs = set()
    for a, c in pairs:
        nodes_from_pairs.add(a)
        nodes_from_pairs.add(c)
    out["nodes_from_pairs"] = len(nodes_from_pairs)
    out["70_eq_pair_nodes"] = set70 == nodes_from_pairs and bool(set70)
    out["70_subset_pair_nodes"] = set70 <= nodes_from_pairs and bool(set70)
    out["pair_nodes_subset_70"] = nodes_from_pairs <= set70 and bool(nodes_from_pairs)
    out["frac_70_in_pair_nodes"] = (
        len(set70 & nodes_from_pairs) / len(set70) if set70 else None
    )

    # Order: is +0x70 a subsequence of first-of-each-pair / unique order-preserving from 88?
    firsts = [a for a, _ in pairs]
    out["70_equals_pair_firsts"] = u32s70 == firsts
    out["70_equals_unique_firsts_order"] = u32s70 == list(dict.fromkeys(firsts))

    # Consecutive adjacency in +0x70 vs undirected edges from pairs
    consec = []
    hit = 0
    miss = 0
    for i in range(len(u32s70) - 1):
        a, c = u32s70[i], u32s70[i + 1]
        e = (min(a, c), max(a, c))
        ok = e in undirected
        consec.append({"a": a, "b": c, "edge_in_88_pairs": ok})
        if ok:
            hit += 1
        else:
            miss += 1
    out["consec70_edge_hits"] = hit
    out["consec70_edge_miss"] = miss
    out["consec70_edge_frac"] = (hit / (hit + miss)) if (hit + miss) else None
    out["consec70_sample"] = consec[:12]

    # Also try overlapping pairs (i,i+1) for all i — denser graph hypothesis
    overlap_edges = set()
    for i in range(len(src) - 1):
        a, c = src[i], src[i + 1]
        overlap_edges.add((min(a, c), max(a, c)))
    hit2 = miss2 = 0
    for i in range(len(u32s70) - 1):
        a, c = u32s70[i], u32s70[i + 1]
        if (min(a, c), max(a, c)) in overlap_edges:
            hit2 += 1
        else:
            miss2 += 1
    out["consec70_overlap_edge_hits"] = hit2
    out["consec70_overlap_edge_miss"] = miss2
    out["consec70_overlap_edge_frac"] = (hit2 / (hit2 + miss2)) if (hit2 + miss2) else None

    # Position: for each 70 id, indices in 88
    pos = {}
    for pid in u32s70[:32]:
        pos[pid] = [i for i, x in enumerate(ids88_clean) if x == pid][:8]
    out["positions_70_in_88"] = pos

    # Hypothesis tags (evidence-gated)
    hyps = []
    if out["n88_even"] and out["n_pairs"] > 0 and out["70_eq_pair_nodes"]:
        hyps.append("H_edge_pairs_70_is_node_set")
    if out["n88_even"] and out["70_subset_pair_nodes"] and out["frac_70_in_pair_nodes"] == 1.0:
        hyps.append("H_edge_pairs_70_subset_nodes")
    if out.get("consec70_edge_frac") is not None and out["consec70_edge_frac"] >= 0.8:
        hyps.append("H_70_path_edges_match_88_pairs")
    if out.get("consec70_overlap_edge_frac") is not None and out["consec70_overlap_edge_frac"] >= 0.8:
        hyps.append("H_70_path_edges_match_88_overlap")
    if out["70_equals_pair_firsts"]:
        hyps.append("H_70_is_pair_firsts_sequence")
    if out["equal_as_sets"]:
        hyps.append("H_same_set")
    if out["70_subset_88"] and not out["equal_as_sets"]:
        hyps.append("H_70_subset_88_ids")
    if not hyps:
        hyps.append("H_unresolved_related_partial_overlap")
    out["hypotheses"] = hyps
    return out


def main():
    b = Backend()
    base = b.image_base
    meta = live_meta(b, base)
    ois, sight = sight_assign_ois(b, base)
    print("SIGHT", sight.get("sight_counts"), "assigns", len(sight["assigns"]), flush=True)
    rows = []
    hyp_counter = Counter()
    for oi in ois:
        link = resolve_inst(b, base, oi)
        if not link or not link.get("vt_ok"):
            rows.append({"oi": oi, "ok": False, "link": link})
            continue
        inst = link["inst"]
        a70 = read_cpdx(b, base, inst + 0x70)
        a88 = read_cpdx(b, base, inst + 0x88)
        u32s = read_u32_arr(b, base, a70)
        ids88, vtok, _ptrs = read_cprovince_ids(b, base, a88)
        if not u32s and not ids88:
            rows.append({
                "oi": oi,
                "ok": True,
                "empty": True,
                "a70": {k: a70[k] for k in ("size", "cap", "plausible", "sentinel")} if a70 else None,
                "a88": {k: a88[k] for k in ("size", "cap", "plausible", "sentinel")} if a88 else None,
            })
            continue
        an = analyze(u32s, ids88)
        for h in an["hypotheses"]:
            hyp_counter[h] += 1
        rows.append({
            "oi": oi,
            "ok": True,
            "empty": False,
            "vt_ok_88": vtok,
            "a70_size": (a70 or {}).get("size"),
            "a88_size": (a88 or {}).get("size"),
            "u32s70": u32s,
            "ids88": ids88,
            "analysis": an,
        })

    nonempty = [r for r in rows if r.get("ok") and not r.get("empty") and r.get("analysis")]
    # Aggregate honest result
    result = "inst70_88_structure_unresolved"
    note = "partial overlap only; no strong structural hyp across samples"
    if nonempty:
        fracs = [r["analysis"]["frac_70_in_88"] for r in nonempty if r["analysis"]["frac_70_in_88"] is not None]
        pair_eq = sum(1 for r in nonempty if r["analysis"].get("70_eq_pair_nodes"))
        path_pair = sum(
            1
            for r in nonempty
            if (r["analysis"].get("consec70_edge_frac") or 0) >= 0.8
        )
        path_ov = sum(
            1
            for r in nonempty
            if (r["analysis"].get("consec70_overlap_edge_frac") or 0) >= 0.8
        )
        subset = sum(1 for r in nonempty if r["analysis"].get("70_subset_88"))
        even = sum(1 for r in nonempty if r["analysis"].get("n88_even"))
        if path_pair >= max(1, len(nonempty) // 2) and pair_eq >= max(1, len(nonempty) // 2):
            result = "inst88_edge_pairs__inst70_path_nodes"
            note = "+0x88 even-length CProvince* stream fits edge-pair packing; +0x70 matches pair-node set and consecutive edges hit pair set"
        elif path_ov >= max(1, len(nonempty) // 2) and subset >= max(1, len(nonempty) // 2):
            result = "inst88_overlap_edges__inst70_pathlike"
            note = "+0x70 consecutive pairs mostly present as adjacent elems in +0x88; +0x70 ⊆ +0x88 ids"
        elif even == len(nonempty) and pair_eq >= max(1, len(nonempty) // 2):
            result = "inst88_even_pairs__inst70_pair_nodes"
            note = "+0x88 even; +0x70 equals undirected-pair node set on ≥half samples; path-edge frac mixed"
        elif subset == len(nonempty):
            result = "inst70_subset_of_inst88_ids"
            note = "all nonempty: set(+0x70) ⊆ set(+0x88 CProvince ids); not equal; pair/path hyp weak"
        else:
            result = "inst70_88_related_partial_overlap"
            note = f"mean frac_70_in_88={sum(fracs)/len(fracs):.3f}" if fracs else note

    out = {
        "phase": "2fx",
        "allow_post": False,
        "result": result,
        "result_note": note,
        "live": meta,
        "ois_tried": ois,
        "sight": {"sight_counts": sight.get("sight_counts"), "n_assigns": len(sight.get("assigns") or []), "elapsed_s": sight.get("elapsed_s")},
        "hyp_counter": dict(hyp_counter),
        "n_nonempty": len(nonempty),
        "rows": rows,
        "works": [
            "allow_post False; never 5x; no Post/inject/tool-gate/2fb; Capstone not re-run",
            f"fuller read cap={MAX_ARR} for +0x70 u32 and +0x88 CProvince*",
            f"result={result}",
            f"hyp_counter={dict(hyp_counter)}",
            f"nonempty_struct_rows={len(nonempty)}",
        ],
        "stubbed": [
            "in-process ring embed",
            "2fb recipe execution",
            "ordinary CMove live leaf",
            "SAFE_POST / ALLOW_POST",
            "self-MOVE",
            "tool-gate open",
            "Post inject",
            "path-vector nonempty confirm as named movement path",
            "HourlyTick abuse",
            "Capstone/121 re-churn",
            "NewFallback subject type-id table",
            "live midflight NewFallback hex",
            "army path/history field beyond current province",
            "named Instance +0xe0/+0x100",
            "demangled RTTI string dump for VT 0x29d6fb8 beyond catalog",
        ],
        "next_shortest_blocker": (
            "NON-Post: if structure hyp solid, name +0x70/+0x88 roles from evidence OR "
            "army path/history beyond current province OR bounded NF/RF; still NO ALLOW_POST"
        ),
    }
    (ROOT / "reports" / "phase2fx_70_88_structure.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8"
    )
    summary = {k: out[k] for k in out if k != "rows"}
    # compact row briefs
    summary["row_briefs"] = []
    for r in nonempty:
        a = r["analysis"]
        summary["row_briefs"].append({
            "oi": r["oi"],
            "n70": a["n70"],
            "n88": a["n88"],
            "vt_ok_88": r["vt_ok_88"],
            "frac_70_in_88": a["frac_70_in_88"],
            "n88_even": a["n88_even"],
            "n_pairs": a["n_pairs"],
            "70_eq_pair_nodes": a["70_eq_pair_nodes"],
            "consec_pair_frac": a["consec70_edge_frac"],
            "consec_overlap_frac": a["consec70_overlap_edge_frac"],
            "hyps": a["hypotheses"],
            "sample70": r["u32s70"][:10],
            "sample88": r["ids88"][:12],
        })
    (ROOT / "reports" / "phase2fx_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps({
        "result": result,
        "note": note,
        "live": meta,
        "hyp_counter": dict(hyp_counter),
        "briefs": summary["row_briefs"],
        "allow_post": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
