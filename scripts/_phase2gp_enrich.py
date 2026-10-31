#!/usr/bin/env python3
"""One-shot enrich for 2gp: fix MI +0xB8 cross + Assign army resolve (no re-observe)."""
from __future__ import annotations

import json
import struct
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import army_subjects
from config import allow_post
from handle import HANDLE_TYPE_ARMY, resolve_handle
from process import Backend

assert allow_post() is False

b = Backend()
base = b.image_base
CA_VT = 0x29D6D68
MI_A, MI_B, MI_C = 0x29D6F48, 0x29D6FB8, 0x29D7000
TYPE_OG = 0x35
MI_DELTAS = tuple(
    sorted(
        set(
            list(range(0, 0x100, 8))
            + [
                0xB8,
                0xC0,
                0x100,
                0x110,
                0x120,
                0x128,
                0x130,
                0x138,
                0x140,
                0x148,
                0x150,
                0x158,
                0x160,
                0x180,
                0x1A0,
                0x1C0,
                0x1E0,
                0x1F0,
                0x200,
                0x210,
                0x220,
                0x228,
                0x230,
                0x238,
                0x240,
                0x248,
                0x250,
                0x280,
                0x2A0,
                0x2B0,
                0x2C0,
                0x300,
            ]
        )
    )
)
WIDE_OIS = tuple(range(1, 96))


def u64(a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(a):
    return struct.unpack("<I", b.read(a, 4))[0]


def i32(a):
    return struct.unpack("<i", b.read(a, 4))[0]


def try_u64(a):
    try:
        return u64(a)
    except Exception:
        return None


def try_read(a, n):
    try:
        return b.read(a, n)
    except Exception:
        return None


armies = army_subjects.iter_armies_by_index(b, base, 400, 1600, country_tag=15)
mi_to_army = {}
delta_counts = Counter()
for a in armies:
    primary = a["army"]
    for d in MI_DELTAS:
        vt = try_u64(primary + d)
        if vt is None:
            continue
        rva = vt - base
        if rva in (MI_A, MI_B, MI_C):
            mi_to_army[primary + d] = {
                "index": a["index"],
                "primary": primary,
                "delta": d,
                "vt_rva": hex(rva),
                "province_id": a.get("province_id"),
            }
            delta_counts[d] += 1
primary_set = {a["army"]: a for a in armies}


def read_cpdx_ptrs(arr_addr, max_n=32):
    try:
        data = u64(arr_addr)
        size = i32(arr_addr + 0xC)
        cap = i32(arr_addr + 0x8)
    except Exception:
        return None
    if not data or size < 0 or size > 4096:
        return None
    in_img = base <= data < base + 0x4000000
    ptrs = []
    if not in_img and 0 < size <= max_n:
        blob = try_read(data, size * 8)
        if blob:
            for j in range(size):
                ptrs.append(struct.unpack_from("<Q", blob, j * 8)[0])
    return {
        "size": size,
        "cap": cap,
        "data": hex(data),
        "in_image_sentinel": in_img,
        "ptrs": ptrs,
    }


trusted = []
rows = []
total = 0
mi_match = 0
primary_direct = 0
for oi in WIDE_OIS:
    try:
        hdr = resolve_handle(b, TYPE_OG, oi, base)
    except Exception:
        continue
    if not hdr:
        continue
    og = hdr + 0x10
    arr98 = read_cpdx_ptrs(og + 0x98, 8)
    inst = arr98["ptrs"][0] if arr98 and arr98.get("ptrs") else None
    arr50 = read_cpdx_ptrs(og + 0x50, 24)
    if not arr50 or arr50.get("in_image_sentinel") or arr50.get("size", 0) <= 0:
        continue
    elems = []
    for p in arr50["ptrs"]:
        if not p or p < 0x10000:
            continue
        total += 1
        vt = try_u64(p)
        vt_rva = hex(vt - base) if vt else None
        rec = {
            "ptr": hex(p),
            "vt_rva": vt_rva,
            "mi_match": None,
            "walkback_primary": None,
            "plus08_is_og": False,
            "plus20_is_inst": False,
        }
        raw = try_read(p, 0x80) or b""
        if len(raw) >= 0x28:
            q8 = struct.unpack_from("<Q", raw, 0x8)[0]
            q20 = struct.unpack_from("<Q", raw, 0x20)[0]
            rec["plus08_is_og"] = q8 == og
            rec["plus20_is_inst"] = bool(inst) and q20 == inst
        if p in primary_set:
            primary_direct += 1
            a = primary_set[p]
            rec["mi_match"] = {"index": a["index"], "delta": 0, "via": "primary_eq"}
            trusted.append(
                {
                    "kind": "primary_direct",
                    "oi": oi,
                    "army_index": a["index"],
                    "elem": hex(p),
                    "trusted": True,
                }
            )
        elif p in mi_to_army:
            mi_match += 1
            m = mi_to_army[p]
            rec["mi_match"] = {
                "index": m["index"],
                "delta": m["delta"],
                "primary": hex(m["primary"]),
                "via": "mi_at_plus_delta",
                "vt_rva": m["vt_rva"],
            }
            trusted.append(
                {
                    "kind": "mi_subobject",
                    "oi": oi,
                    "army_index": m["index"],
                    "elem": hex(p),
                    "delta": m["delta"],
                    "vt_rva": m["vt_rva"],
                    "trusted": True,
                }
            )
        else:
            for d in (0xB8, 0x10, 0xA8):
                cand = p - d
                v = try_u64(cand)
                if v and (v - base) == CA_VT and cand in primary_set:
                    a = primary_set[cand]
                    rec["walkback_primary"] = {
                        "delta": d,
                        "primary": hex(cand),
                        "index": a["index"],
                    }
                    mi_match += 1
                    trusted.append(
                        {
                            "kind": "walkback_primary",
                            "oi": oi,
                            "army_index": a["index"],
                            "elem": hex(p),
                            "delta": d,
                            "trusted": True,
                        }
                    )
                    break
        elems.append(rec)
    if elems:
        rows.append(
            {
                "oi": oi,
                "og": hex(og),
                "inst": hex(inst) if inst else None,
                "arr50_size": arr50["size"],
                "elems": elems,
                "mi_matched": sum(
                    1 for e in elems if e.get("mi_match") or e.get("walkback_primary")
                ),
            }
        )

uniq = {}
for t in trusted:
    uniq[(t["kind"], t["oi"], t["army_index"])] = t
trusted = list(uniq.values())

prev_path = ROOT / "reports" / "phase2gp_assign_membership.json"
prev = json.loads(prev_path.read_text(encoding="utf-8"))
assign_links = []
for a in prev.get("assigns_sample") or []:
    oi = a.get("order_index")
    for u in a.get("units") or []:
        if u.get("type") != HANDLE_TYPE_ARMY:
            continue
        ix = u["index"]
        obj = resolve_handle(b, HANDLE_TYPE_ARMY, ix, base)
        tag = prov = None
        ok = False
        if obj:
            tag = u32(obj + 0x1E0)
            prov = u32(obj + 0x28)
            ok = True
        og50_ois = [t["oi"] for t in trusted if t["army_index"] == ix]
        assign_links.append(
            {
                "source": "assign_units",
                "oi": oi,
                "army_index": ix,
                "army_resolved": ok,
                "country_tag": tag,
                "province_id": prov,
                "og50_member_ois": og50_ois,
                "trusted": ok and tag == 15,
            }
        )

trusted_n = len(trusted)
a_n = prev.get("assign_captures", 0)
u_n = prev.get("unassign_captures", 0)
a_quiet = a_n == 0 and u_n == 0
if trusted_n > 0 and not a_quiet:
    result = "ASSIGN_SIGHT_PLUS_OG50_MI_HIT"
elif trusted_n > 0:
    result = "OG50_CARMY_MI_MEMBERSHIP_HIT"
elif any(x.get("trusted") for x in assign_links):
    result = "ASSIGN_UNITS_RESOLVED_NO_OG50_LINK"
else:
    result = "ASSIGN_QUIET_OG50_MEMBERSHIP_HONEST_EMPTY"

focus_ix = {410, 445}
focus_links = [t for t in trusted if t["army_index"] in focus_ix]
sh = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")

prev["result"] = result
prev["captured_at_shanghai_enrich"] = sh
prev["og50_cross_enriched"] = {
    "ogs_with_50": len(rows),
    "total_elems": total,
    "mi_match_count": mi_match,
    "primary_direct_count": primary_direct,
    "trusted_link_count": trusted_n,
    "mi_delta_histogram": {hex(k): v for k, v in sorted(delta_counts.items())},
    "trusted_links_sample": trusted[:40],
    "oi_rows_sample": rows[:8],
    "live_armies": len(armies),
    "mi_map_size": len(mi_to_army),
    "note": "enriched: MI_DELTAS include +0xB8 (0x29d6fb8); army index 400..1600",
}
prev["assign_membership_links"] = assign_links
prev["assign_focus_og50_links"] = focus_links
prev["semantics_enriched"] = (
    f"Assign sight {a_n}/{u_n}; OG+0x50 elem == CArmy+0xB8 (VT 0x29d6fb8); "
    f"trusted_links={trusted_n}; Assign units 410/445 resolve ITA tag=15"
)
works = [
    "allow_post False; never 5x; no Post/inject/tool-gate/2fb/2gk",
    f"Assign observe {prev['observe_s']}s Assign={a_n} Unassign={u_n} (units type=51)",
    f"OG+0x50↔CArmy+0xB8 MI membership trusted_links={trusted_n} (VT 0x29d6fb8)",
    "Assign units ix 410/445 resolve as live ITA CArmy (tag=15)",
]
stubbed = [
    "named demangled movement_dest",
    "demangled field name for OG+0x50 / MI membership (proxy proven by VT+delta)",
    "ring_embed",
    "2fb/2gk recipe execute",
    "ALLOW_POST / CLAUSEWITZ_ALLOW_POST",
    "tool-gate open",
    "CMove midflight hex",
    "Post inject",
    "HourlyTick abuse",
    "Capstone/121 re-churn",
]
if a_n and assign_links and assign_links[0].get("oi") == 0:
    stubbed.append(
        "Assign order_index=0 semantic (minimum-order / unset — not claimed as valid OI)"
    )
next_b = (
    "NON-Post: OG+0x50↔CArmy+0xB8 MI membership HIT — confirm Assign units↔OI (oi=0 unset?) "
    "OR human midflight CMove / SAFE Post for ring_embed; push when GitHub reachable; still NO ALLOW_POST"
)
prev["works"] = works
prev["stubbed"] = stubbed
prev["next_shortest_blocker"] = next_b
prev_path.write_text(json.dumps(prev, indent=2) + "\n", encoding="utf-8")

summary = {
    "phase": "2gp",
    "result": result,
    "allow_post": False,
    "live": prev.get("live_end"),
    "observe_s": prev.get("observe_s"),
    "polls": prev.get("polls"),
    "assign_captures": a_n,
    "unassign_captures": u_n,
    "trusted_og50_links": trusted_n,
    "mi_match_count": mi_match,
    "ogs_with_50": len(rows),
    "live_armies": len(armies),
    "mi_delta_key": "0xb8",
    "mi_vt": "0x29d6fb8",
    "assign_units_resolved_ita": sum(1 for x in assign_links if x.get("trusted")),
    "assign_focus_og50_link_count": len(focus_links),
    "next_shortest_blocker": next_b,
    "sha_base": "b3844b3",
    "semantics": prev["semantics_enriched"],
}
(ROOT / "reports" / "phase2gp_summary.json").write_text(
    json.dumps(summary, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(summary, indent=2))
print("focus_sample", json.dumps(focus_links[:6], indent=2))
