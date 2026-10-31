#!/usr/bin/env python3
"""Phase 2gd: ETH war-dense relaunch @1x AI-on + bounded NF/RF + CArmy path RO.
No Post. Never 5x. allow_post False. Window 60–90s max after map ready.
"""
from __future__ import annotations

import importlib.util
import json
import struct
import subprocess
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

assert allow_post() is False, "allow_post must stay False"

OBSERVE_S = 75.0
INTERVAL_S = 0.08
HEAP_EVERY = 50
MAP_WAIT_S = 180.0
ETH_TAG = 15
CA_VT_RVA = 0x29D6D68
CA_LAST_PATH_CAND = 0x2B4  # WINDOWS_OFFSETS candidate only — not demangled name

NF_VT = cmd_layout.ORDERS["COrderNewFallbackCommand"]["vt"]
RF_VT = 0x2A84D38
NF_FIELDS = cmd_layout.ORDERS["COrderNewFallbackCommand"].get("fields") or {}

FOCUS_VT = {
    NF_VT: "COrderNewFallbackCommand",
    RF_VT: "COrderReplaceFallbackCommands",
    cmd_layout.ORDERS["COrderAssignCommand"]["vt"]: "COrderAssignCommand",
    cmd_layout.ORDERS["COrderExecuteCommand"]["vt"]: "COrderExecuteCommand",
}
# named catalog path-ish offs to sample (candidates; do not invent demangle)
NAMED_PATH_CANDS = {
    "last_path_cand_0x2b4": CA_LAST_PATH_CAND,  # soft catalog
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


def load_fj():
    spec = importlib.util.spec_from_file_location(
        "phase2fj_war_dense_observe", ROOT / "scripts" / "phase2fj_war_dense_observe.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def relaunch_eth() -> dict:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "launch_into_map.py"),
        "--start-tag",
        "ETH",
        "--speed",
        "1",
        "--allow-ai",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    return {
        "cmd": cmd,
        "rc": r.returncode,
        "stdout": (r.stdout or "")[-600:],
        "stderr": (r.stderr or "")[-300:],
    }


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


def sample_named_path_cands(b, base, rows):
    """Sample catalog soft offs + fj-style path vectors; label catalog names only."""
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
        for label, off in NAMED_PATH_CANDS.items():
            raw = try_read(b, obj + off, 4)
            if raw:
                v = struct.unpack("<I", raw)[0]
                rec["catalog_soft"][label] = {
                    "off": hex(off),
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
            match_cur = vals == [r.get("province_id")]
            if match_cur and len(vals) == 1:
                continue
            rec["vector_cands"].append({
                "off": hex(off),
                "n": len(vals),
                "province_ids": vals[:16],
                "named": False,  # scan offs are candidates only
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


def main():
    assert allow_post() is False
    scenario = "ETH war-dense relaunch @1x AI-on bounded NF/RF+path (no Post)"

    relaunch = relaunch_eth()
    if relaunch["rc"] != 0:
        summary = {
            "phase": "2gd",
            "allow_post": False,
            "result": "RELAUNCH_FAIL",
            "result_note": f"launch_into_map rc={relaunch['rc']}",
            "relaunch": relaunch,
            "works": ["allow_post False"],
            "stubbed": ["war-dense observe (relaunch failed)"],
            "next_shortest_blocker": "NON-Post: fix relaunch then retry; still NO ALLOW_POST",
        }
        (ROOT / "reports" / "phase2gd_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2)[:2000])
        return 1

    fj = load_fj()
    map_wait = fj.wait_map(MAP_WAIT_S)
    if not map_wait.get("ok"):
        summary = {
            "phase": "2gd",
            "allow_post": False,
            "result": "RELAUNCH_MAP_WAIT_FAIL",
            "result_note": "map wait timeout after ETH relaunch",
            "relaunch": relaunch,
            "map_wait": map_wait,
            "works": ["allow_post False; relaunch attempted"],
            "stubbed": ["war-dense observe (map not ready)"],
            "next_shortest_blocker": "NON-Post: relaunch map-ready then observe; still NO ALLOW_POST",
        }
        (ROOT / "reports" / "phase2gd_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps({"result": summary["result"], "map_wait": map_wait}, indent=2))
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
    soft_path_hits = 0

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
        path_hits = sample_named_path_cands(b, base, rows)
        if len(path_hits) > len(path_best):
            path_best = path_hits
        soft_path_hits = max(soft_path_hits, sum(
            1 for h in path_hits for c in h.get("catalog_soft", {}).values()
            if c.get("province_shaped")
        ))

        # early stop on rich NF or useful multi-prov path
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
    named_offs_documented = []
    # only document catalog soft if province-shaped and differs from current in samples
    for h in path_best:
        for label, c in (h.get("catalog_soft") or {}).items():
            if c.get("province_shaped"):
                named_offs_documented.append({
                    "label": label,
                    "off": c["off"],
                    "sample_u32": c["u32"],
                    "army": h.get("army"),
                    "note": "catalog soft candidate only — not demangled RTTI field name",
                })

    if rich_nf and useful_path:
        result = "war_dense_nf_rf_and_path_hits"
        note = f"NF/RF nonempty={len(rich_nf)}; path vectors nonempty armies={len(useful_path)}"
    elif rich_nf:
        result = "war_dense_nf_rf_hex_captured"
        note = f"NF/RF captures={len(nf_caps)} nonempty_fields={len(rich_nf)}; path vectors empty"
    elif useful_path:
        result = "war_dense_path_vector_nonempty__unnamed_offs"
        note = (
            f"path vector nonempty armies={len(useful_path)}; "
            f"offs are scan candidates (named=False); catalog soft 0x2b4 samples={len(named_offs_documented)}"
        )
    elif named_offs_documented:
        result = "war_dense_catalog_soft_path_only"
        note = f"no NF/RF; no multi-prov path vectors; catalog soft 0x2b4 province-shaped n={len(named_offs_documented)}"
    else:
        result = "war_dense_nf_rf_and_path_empty"
        note = (
            f"ETH@1x AI-on bounded {elapsed}s: NF/RF=0 path_vectors=0; honest empty "
            f"(same class as 2fj/2fk). polls={polls}"
        )

    works = [
        "allow_post False; never 5x; no Post/inject/tool-gate/2fb; Capstone not re-run",
        f"result={result}",
        "relaunch ETH -start_tag=ETH -start_speed=1 --allow-ai",
        f"bounded observe {elapsed}s polls={polls}",
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
        stubbed.append("live midflight NewFallback hex (empty this war-dense window)")
    if not useful_path:
        stubbed.append("named CArmy path-field offsets (no nonempty demangled path this window)")

    if result == "war_dense_nf_rf_and_path_empty":
        next_blocker = (
            "NON-Post: RO ceiling on war-dense NF/path in bounded window — "
            "longer war-day observe OR catalog-only leaf field polish; still NO ALLOW_POST"
        )
    elif "nf_rf" in result:
        next_blocker = (
            "NON-Post: deepen NF subject_handle semantic from live hex OR name CArmy path offs; "
            "still NO ALLOW_POST"
        )
    else:
        next_blocker = (
            "NON-Post: demangle/name recurring CArmy path-vector offs from war-dense hits; "
            "still NO ALLOW_POST"
        )

    detail = {
        "phase": "2gd",
        "allow_post": False,
        "relaunch": relaunch,
        "map_wait": map_wait,
        "live_start": meta0,
        "live_end": meta1,
        "observe": {
            "elapsed_s": elapsed,
            "polls": polls,
            "last_counters": last_counters,
            "sight_counts": sight,
            "nf_rf_captures": nf_caps[:8],
            "path_best_sample": path_best[:8],
            "catalog_soft_path_samples": named_offs_documented[:12],
            "useful_path_army_count": len(useful_path),
        },
    }
    summary = {
        "phase": "2gd",
        "allow_post": False,
        "result": result,
        "result_note": note,
        "live": meta1,
        "relaunch_ok": True,
        "map_wait_s": map_wait.get("elapsed_s"),
        "observe_s": elapsed,
        "polls": polls,
        "nf_rf_capture_count": len(nf_caps),
        "path_nonempty_armies": len(useful_path),
        "catalog_soft_path_n": len(named_offs_documented),
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_blocker,
    }

    out = ROOT / "reports"
    out.mkdir(exist_ok=True)
    (out / "phase2gd_war_dense.json").write_text(json.dumps(detail, indent=2), encoding="utf-8")
    (out / "phase2gd_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({
        "result": result,
        "note": note,
        "elapsed_s": elapsed,
        "polls": polls,
        "nf_rf": len(nf_caps),
        "path_armies": len(useful_path),
        "ui_date": meta1.get("ui_date"),
        "pid": meta1.get("pid"),
        "allow_post": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
