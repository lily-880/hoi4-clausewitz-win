#!/usr/bin/env python3
"""Phase 2ge: longer war-day observe on CURRENT ETH @1x — NF/RF + CArmy path.
No relaunch unless dead. No Post. Never 5x. allow_post False. ≤90s max.
"""
from __future__ import annotations

import json
import struct
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

from config import allow_post
from process import Backend, find_pid
import post_abi
import cmd_layout
import army_subjects

assert allow_post() is False

OBSERVE_S = 90.0
INTERVAL_S = 0.08
ETH_TAG = 15
CA_VT_RVA = 0x29D6D68
CA_LAST_PATH_CAND = 0x2B4

NF_VT = cmd_layout.ORDERS["COrderNewFallbackCommand"]["vt"]
RF_VT = 0x2A84D38
NF_FIELDS = cmd_layout.ORDERS["COrderNewFallbackCommand"].get("fields") or {}

FOCUS_VT = {
    NF_VT: "COrderNewFallbackCommand",
    RF_VT: "COrderReplaceFallbackCommands",
    cmd_layout.ORDERS["COrderAssignCommand"]["vt"]: "COrderAssignCommand",
    cmd_layout.ORDERS["COrderExecuteCommand"]["vt"]: "COrderExecuteCommand",
}


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def i32(b, a):
    return struct.unpack("<i", b.read(a, 4))[0]


def try_u64(b, a):
    try:
        return u64(b, a)
    except Exception:
        return None


def try_read(b, a, n):
    try:
        return b.read(a, n)
    except Exception:
        return None


def looks_prov(v: int) -> bool:
    return 1 <= v <= 20000


def live_meta(b, base, scenario: str):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    hours = i32(b, gs + 0x484)
    d = datetime(1936, 1, 1) + timedelta(hours=int(hours))
    return {
        "pid": find_pid(),
        "hours": hours,
        "ui_date": d.strftime("%Y-%m-%d %H:00"),
        "speed_policy": "pause-or-1x only (never change speed)",
        "scenario": scenario,
        "cmdline_expect": "-gdpr-compliant -start_tag=ETH -start_speed=1",
        "gs": hex(gs),
    }


def decode_nf(b, base, addr, name):
    blob = try_read(b, addr, 0x60) or b""
    out = {
        "name": name,
        "addr": hex(addr),
        "vt_rva": hex(struct.unpack_from("<Q", blob, 0)[0] - base) if len(blob) >= 8 else None,
        "hex": blob.hex(),
        "fields_decoded": {},
    }
    if len(blob) < 0x58:
        return out
    sh = NF_FIELDS.get("subject_handle", 0x28)
    out["fields_decoded"]["subject_handle"] = [
        struct.unpack_from("<I", blob, sh)[0],
        struct.unpack_from("<I", blob, sh + 4)[0],
    ]
    ud, ucap, ucnt = (
        NF_FIELDS.get("units_data", 0x30),
        NF_FIELDS.get("units_capacity", 0x38),
        NF_FIELDS.get("units_count", 0x3C),
    )
    pd, pcap, psz = (
        NF_FIELDS.get("provinces_data", 0x48),
        NF_FIELDS.get("provinces_capacity", 0x50),
        NF_FIELDS.get("provinces_size", 0x54),
    )
    out["fields_decoded"]["units"] = {
        "data": hex(struct.unpack_from("<Q", blob, ud)[0]),
        "capacity": struct.unpack_from("<i", blob, ucap)[0],
        "count": struct.unpack_from("<i", blob, ucnt)[0],
    }
    pdata = struct.unpack_from("<Q", blob, pd)[0]
    psize = struct.unpack_from("<i", blob, psz)[0]
    ids = []
    if 0 < psize <= 32 and pdata > 0x10000:
        raw = try_read(b, pdata, min(psize, 16) * 4) or b""
        ids = [struct.unpack_from("<I", raw, i * 4)[0] for i in range(len(raw) // 4)]
    out["fields_decoded"]["provinces"] = {
        "data": hex(pdata),
        "capacity": struct.unpack_from("<i", blob, pcap)[0],
        "size": psize,
        "ids_sample": ids,
    }
    return out


def sample_nf_rf(b, base):
    sess = u64(b, base + post_abi.G_SESSION)
    server = u64(b, sess + post_abi.CSession_SERVER)
    pending_h = try_u64(b, server + post_abi.CDummyServer_PENDING) or 0
    stage = try_u64(b, sess + post_abi.CSession_STAGE_ARRAY) or 0
    scount = u32(b, sess + post_abi.CSession_STAGE_COUNT)
    drain = u32(b, sess + post_abi.CSession_DRAIN_COUNTER)
    exec_c = u32(b, sess + post_abi.CSession_EXEC_COUNTER)
    seq = u32(b, server + 0xD0)
    hits = []
    seen = set()
    cur = pending_h
    while cur and cur not in seen and len(hits) < 64:
        seen.add(cur)
        vt = try_u64(b, cur)
        if vt is None:
            break
        name = FOCUS_VT.get(vt - base)
        if name and "Fallback" in name:
            hits.append({"source": "pending", **decode_nf(b, base, cur, name)})
        elif name:
            hits.append({"source": "pending", "name": name, "addr": hex(cur), "vt_rva": hex(vt - base)})
        nxt = try_u64(b, cur + 8)
        if not nxt or nxt == cur:
            break
        cur = nxt
    if stage and 0 < scount < 64:
        for i in range(scount):
            ptr = try_u64(b, stage + i * 8)
            if not ptr:
                continue
            vt = try_u64(b, ptr)
            if vt is None:
                continue
            name = FOCUS_VT.get(vt - base)
            if not name:
                continue
            if "Fallback" in name:
                hits.append({"source": f"stage[{i}]", **decode_nf(b, base, ptr, name)})
            else:
                hits.append({"source": f"stage[{i}]", "name": name, "addr": hex(ptr), "vt_rva": hex(vt - base)})
    return hits, {"drain": drain, "exec": exec_c, "seq": seq, "stage_count": scount}


def sample_paths(b, base, rows):
    vt_want = base + CA_VT_RVA
    out = []
    for r in rows:
        obj = r["army"]
        vt = try_u64(b, obj)
        if vt != vt_want:
            continue
        rec = {
            "index": r.get("index"),
            "army": hex(obj),
            "province_id": r.get("province_id"),
            "catalog_soft": {},
            "vector_cands": [],
        }
        raw4 = try_read(b, obj + CA_LAST_PATH_CAND, 4)
        if raw4:
            v = struct.unpack("<I", raw4)[0]
            rec["catalog_soft"]["last_path_cand_0x2b4"] = {
                "off": hex(CA_LAST_PATH_CAND),
                "u32": v,
                "province_shaped": looks_prov(v),
            }
        blob = try_read(b, obj, 0x800) or b""
        for off in range(0x40, min(len(blob) - 24, 0x780), 8):
            begin, end, cap = struct.unpack_from("<QQQ", blob, off)
            if begin < 0x10000 or end < begin or end - begin > 0x400:
                continue
            n = (end - begin) // 4
            if n < 1 or n > 64:
                continue
            raw = try_read(b, begin, min(n, 32) * 4) or b""
            vals = list(struct.unpack("<" + "I" * (len(raw) // 4), raw)) if raw else []
            if not vals or not all(looks_prov(v) for v in vals):
                continue
            if vals == [r.get("province_id")] and len(vals) == 1:
                continue
            rec["vector_cands"].append({
                "off": hex(off),
                "n": len(vals),
                "province_ids": vals[:16],
                "named": False,
                "catalog_name": None,
            })
            if len(rec["vector_cands"]) >= 4:
                break
        if rec["vector_cands"] or any(
            (c.get("province_shaped") and c.get("u32") != r.get("province_id"))
            for c in rec["catalog_soft"].values()
        ):
            out.append(rec)
    return out


def catalog_leaf_snapshot():
    """B-ready: deltas-only catalog polish snapshot from 2fl/2fm maps (no Capstone)."""
    nf = cmd_layout.ORDERS["COrderNewFallbackCommand"]
    isv = getattr(cmd_layout, "ISVALID_PATHS", None) or getattr(cmd_layout, "ORDER_ISVALID", None)
    nf_isv = None
    if isinstance(isv, dict):
        nf_isv = isv.get("COrderNewFallbackCommand")
    # also try module-level dicts from 2fl
    for attr in dir(cmd_layout):
        if "isvalid" in attr.lower() and attr.isupper():
            d = getattr(cmd_layout, attr)
            if isinstance(d, dict) and "COrderNewFallbackCommand" in d:
                nf_isv = d["COrderNewFallbackCommand"]
                break
    return {
        "source": "cmd_layout ORDERS (2fl/2fm already baked; no Capstone re-run)",
        "COrderNewFallbackCommand": {
            "vt": hex(nf["vt"]),
            "type_id": hex(nf.get("type_id", 0)),
            "factory_idx": nf.get("factory_idx"),
            "size": nf.get("size"),
            "fields": nf.get("fields"),
            "fields_note": nf.get("fields_note"),
            "isvalid_entry": nf_isv,
        },
        "RF_vt_soft": hex(RF_VT),
        "delta_vs_prior": (
            "no new Capstone; catalog already carries 2fm packing "
            "(+0x54=provinces_size, subject_handle@+0x28, units@+0x30, provinces@+0x48); "
            "factory_idx=4271 from 2fg tid-0x2328"
        ),
    }


def main():
    assert allow_post() is False
    scenario = "ETH longer war-day observe @1x AI-on (current process; no Post)"

    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2ge",
            "allow_post": False,
            "result": "NO_LIVE_PROCESS",
            "result_note": "hoi4 not found; did not relaunch this slice",
            "works": ["allow_post False"],
            "stubbed": ["war-day observe (no process)"],
            "next_shortest_blocker": "NON-Post: restore ETH@1x then observe; still NO ALLOW_POST",
            "catalog_polish": catalog_leaf_snapshot(),
        }
        (ROOT / "reports" / "phase2ge_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2)[:1500])
        return 1

    b = Backend()
    base = b.image_base
    meta0 = live_meta(b, base, scenario)

    t0 = time.time()
    polls = 0
    nf_caps = []
    path_best = []
    sight = {}
    last_counters = None
    soft_docs = []

    while time.time() - t0 < OBSERVE_S:
        polls += 1
        hits, last_counters = sample_nf_rf(b, base)
        for h in hits:
            name = h.get("name") or "?"
            sight[name] = sight.get(name, 0) + 1
            if name in ("COrderNewFallbackCommand", "COrderReplaceFallbackCommands"):
                if not any(c.get("addr") == h.get("addr") for c in nf_caps):
                    nf_caps.append(h)

        rows = army_subjects.iter_armies_by_index(b, base, 1000, 1400, country_tag=ETH_TAG)
        path_hits = sample_paths(b, base, rows)
        if len(path_hits) > len(path_best):
            path_best = path_hits
        for h in path_hits:
            for label, c in (h.get("catalog_soft") or {}).items():
                if c.get("province_shaped"):
                    soft_docs.append({
                        "label": label,
                        "off": c["off"],
                        "sample_u32": c["u32"],
                        "army": h.get("army"),
                    })

        rich_nf = [
            c for c in nf_caps
            if (c.get("fields_decoded") or {}).get("provinces", {}).get("size", 0) > 0
            or (c.get("fields_decoded") or {}).get("units", {}).get("count", 0) > 0
        ]
        useful_path = [h for h in path_best if h.get("vector_cands")]
        if rich_nf or useful_path:
            break
        time.sleep(INTERVAL_S)

    elapsed = round(time.time() - t0, 2)
    meta1 = live_meta(b, base, scenario)
    useful_path = [h for h in path_best if h.get("vector_cands")]
    rich_nf = [
        c for c in nf_caps
        if (c.get("fields_decoded") or {}).get("provinces", {}).get("size", 0) > 0
        or (c.get("fields_decoded") or {}).get("units", {}).get("count", 0) > 0
    ]
    catalog = catalog_leaf_snapshot()

    if rich_nf and useful_path:
        result = "war_day_nf_rf_and_path_hits"
        note = f"NF/RF nonempty={len(rich_nf)}; path vectors nonempty armies={len(useful_path)}"
    elif rich_nf:
        result = "war_day_nf_rf_hex_captured"
        note = f"NF/RF captures={len(nf_caps)} nonempty_fields={len(rich_nf)}; path empty"
    elif useful_path:
        result = "war_day_path_vector_nonempty__unnamed_offs"
        note = f"path nonempty armies={len(useful_path)}; offs unnamed scan candidates"
    elif soft_docs:
        result = "war_day_catalog_soft_path_only"
        note = f"no NF/RF; no multi-prov vectors; soft 0x2b4 n={len(soft_docs)}"
    else:
        result = "war_day_nf_rf_and_path_empty"
        note = (
            f"ETH war-day hours {meta0['hours']}→{meta1['hours']} bounded {elapsed}s: "
            f"NF/RF=0 path=0; honest empty (denser window than 2gd day-1 dawn). polls={polls}"
        )

    works = [
        "allow_post False; never 5x; no Post/inject/tool-gate/2fb; Capstone not re-run",
        f"result={result}",
        "current-process observe (no relaunch)",
        f"bounded {elapsed}s polls={polls} hours {meta0['hours']}→{meta1['hours']}",
    ]
    stubbed = [
        "in-process ring embed",
        "2fb recipe execution",
        "ordinary CMove live leaf",
        "SAFE_POST / ALLOW_POST",
        "self-MOVE",
        "tool-gate open",
        "Post inject",
        "HourlyTick abuse",
        "Capstone/121 re-churn",
        "named +0x100 elem class beyond allocator soft-VT",
        "named +0xe0 role beyond u32 province stream",
        "demangled RTTI string dump for VT 0x29d6fb8 beyond catalog",
        "demangled CArmy path field names (scan offs remain candidates)",
    ]
    if not nf_caps:
        stubbed.append("live midflight NewFallback hex (empty this war-day window)")
    if not useful_path:
        stubbed.append("named CArmy path-field offsets (no nonempty demangled path this window)")

    # If empty: include catalog polish deltas (Preferred B alongside A empty)
    if result == "war_day_nf_rf_and_path_empty":
        works.append("catalog-only leaf polish snapshot from 2fl/2fm (deltas only; no Capstone)")
        next_blocker = (
            "NON-Post: RO ceiling — war-day NF/path empty through hours~14–; "
            "next cheapest is Assign/Unassign edge deepen or leaf IsValid gate RO polish; "
            "still NO ALLOW_POST"
        )
    elif "nf_rf" in result:
        next_blocker = (
            "NON-Post: deepen NF subject_handle semantic from live hex OR name CArmy path offs; "
            "still NO ALLOW_POST"
        )
    else:
        next_blocker = (
            "NON-Post: demangle/name recurring CArmy path-vector offs from war-day hits; "
            "still NO ALLOW_POST"
        )

    detail = {
        "phase": "2ge",
        "allow_post": False,
        "live_start": meta0,
        "live_end": meta1,
        "observe": {
            "elapsed_s": elapsed,
            "polls": polls,
            "last_counters": last_counters,
            "sight_counts": sight,
            "nf_rf_captures": nf_caps[:8],
            "path_best_sample": path_best[:8],
            "catalog_soft_path_samples": soft_docs[:12],
            "useful_path_army_count": len(useful_path),
        },
        "catalog_polish": catalog,
    }
    summary = {
        "phase": "2ge",
        "allow_post": False,
        "result": result,
        "result_note": note,
        "live": meta1,
        "observe_s": elapsed,
        "polls": polls,
        "nf_rf_capture_count": len(nf_caps),
        "path_nonempty_armies": len(useful_path),
        "catalog_soft_path_n": len(soft_docs),
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_blocker,
        "catalog_polish_delta": catalog.get("delta_vs_prior"),
    }

    out = ROOT / "reports"
    out.mkdir(exist_ok=True)
    (out / "phase2ge_war_day.json").write_text(json.dumps(detail, indent=2), encoding="utf-8")
    (out / "phase2ge_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({
        "result": result,
        "note": note,
        "elapsed_s": elapsed,
        "polls": polls,
        "nf_rf": len(nf_caps),
        "path_armies": len(useful_path),
        "ui_start": meta0.get("ui_date"),
        "ui_end": meta1.get("ui_date"),
        "pid": meta1.get("pid"),
        "allow_post": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
