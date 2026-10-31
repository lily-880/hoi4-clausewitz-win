#!/usr/bin/env python3
"""Phase 2gm: perception RO deepen — CArmy path/movement_dest + Instance field map.

ONE RO slice. No Post / no ALLOW_POST / no 2fb|2gk execute / no tool-gate / never 5x.
Brief <=90s path poll OR single-pass deepen; Instance+0x70/+0x88/+0xe0/+0x100 catalog.
Honest empty OK. Catalog-only deltas to LAND_POST.
"""
from __future__ import annotations

import json
import struct
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import army_subjects
import post_abi
from config import allow_post
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2gm_carmy_path_instance_ro.json"
SUMMARY = ROOT / "reports" / "phase2gm_summary.json"
DOC = ROOT / "docs" / "PHASE2GM_CARMY_PATH_INSTANCE_RO.md"

CA_VT_RVA = 0x29D6D68
INST_VT = 0x2A84A38  # COrderInstance (from prior phases)
CP_VT = 0x29D3C68
CP_PROVINCE_ID = 0x18
TYPE_OG = 0x35
INDEX_LO, INDEX_HI = 1000, 1600
PATH_WINDOW_S = 60.0
PATH_INTERVAL_S = 3.0
GS_PLAYER_TAG = 0x518
SEED_OIS = (5, 6, 7, 9, 13, 17, 20, 22, 25, 38, 40, 44, 68, 70)

# Offline catalog — proven vs candidate (no invent)
INSTANCE_FIELD_CATALOG = [
    {
        "off": "0x70",
        "kind": "CPdxArray<u32>",
        "status": "PROVEN",
        "role": "ordered province ids for order/front path (NOT army midflight movement_dest)",
        "source": "2fx/2fy",
    },
    {
        "off": "0x88",
        "kind": "CPdxArray<CProvince*>",
        "status": "PROVEN",
        "role": "hub/neighbor province ptr pairs over +0x70 prefix",
        "source": "2fx",
    },
    {
        "off": "0xe0",
        "kind": "CPdxArray<u32> soft/candidates",
        "status": "PROVEN_SOFT",
        "role": "u32 stream; often empty or soft-shaped",
        "source": "2fy",
    },
    {
        "off": "0x100",
        "kind": "packed twin / soft VT 0x2794550",
        "status": "PROVEN_SOFT",
        "role": "twin array / soft object; not demangled named movement_dest",
        "source": "2fy/LAND_POST",
    },
]
CARMY_PATH_CATALOG = [
    {
        "field": "stdvec_u32 / CPdxArray u32 scan @ CArmy+0x40..0x780",
        "status": "CANDIDATE_SCAN",
        "role": "province-id shaped vectors; often current-only or empty at peacetime",
        "source": "2ff/2fh/2fy",
    },
    {
        "field": "actionish province_arr@+0x18 / path_arr@+0x30 layout pockets",
        "status": "CANDIDATE_LAYOUT",
        "role": "MoveAction-like embeds; live filled midflight STUBBED",
        "source": "2ff/2gj",
    },
    {
        "field": "named movement_dest",
        "status": "NOT_DEMANGLED",
        "role": "no demangled named field; do not invent destinations",
        "source": "2ff note",
    },
]


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


def looks_like_province_id(v: int) -> bool:
    return 1 <= v <= 20000


def read_u32_stdvec(b, begin, end, cap, max_n=64):
    if not begin or not end or end < begin:
        return None
    nbytes = end - begin
    if nbytes % 4 != 0 or nbytes > max_n * 4 or nbytes == 0:
        return None
    if cap and cap < end:
        return None
    blob = try_read(b, begin, nbytes)
    if not blob or len(blob) != nbytes:
        return None
    return list(struct.unpack("<" + "I" * (nbytes // 4), blob))


def live_meta(b, base, pid, country_tag):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    hours = i32(b, gs + 0x484)
    d = datetime(1936, 1, 1, 0, 0) + timedelta(hours=int(hours))
    sess = try_u64(b, base + post_abi.G_SESSION) if hasattr(post_abi, "G_SESSION") else None
    pending = stage = drain = exec_c = None
    try:
        sess = u64(b, base + 0x34FFBE8)
        server = u64(b, sess + post_abi.CSession_SERVER)
        pending = u32(b, server + post_abi.CDummyServer_PENDING) if server else None
        stage = u32(b, sess + post_abi.CSession_STAGE_COUNT)
        drain = u32(b, sess + post_abi.CSession_DRAIN_COUNTER)
        exec_c = u32(b, sess + post_abi.CSession_EXEC_COUNTER)
    except Exception:
        pass
    return {
        "pid": pid,
        "hours": hours,
        "ui_date": d.strftime("%Y-%m-%d %H:00"),
        "speed_policy": "pause-or-1x only (never change speed)",
        "country_tag_filter": country_tag,
        "scenario": "ITA@1x perception path+Instance RO (no Post)",
        "pending": pending,
        "stage_count": stage,
        "drain": drain,
        "exec": exec_c,
        "allow_post": False,
    }


def player_tag(b, base):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    return i32(b, gs + GS_PLAYER_TAG)


def scan_army_path_cands(b, base, primary, current_prov):
    blob = try_read(b, primary, 0x800) or b""
    cands = []
    for off in range(0x40, min(len(blob) - 24, 0x780), 8):
        begin, end, cap = struct.unpack_from("<QQQ", blob, off)
        if begin < 0x10000 or end < begin:
            continue
        vals = read_u32_stdvec(b, begin, end, cap, max_n=64)
        if not vals or not all(looks_like_province_id(v) for v in vals):
            continue
        cands.append({
            "kind": "stdvec_u32",
            "off": hex(off),
            "n": len(vals),
            "province_ids": vals[:32],
            "matches_current_only": vals == [current_prov] if current_prov is not None else False,
        })
    for off in range(0x40, min(len(blob) - 24, 0x780), 8):
        data, cap, size = struct.unpack_from("<Qii", blob, off)
        if data < 0x10000 or size <= 0 or size > 64 or size > max(cap, size):
            continue
        if base <= data < base + getattr(b, "image_size", 0):
            continue
        blob2 = try_read(b, data, size * 4)
        if not blob2:
            continue
        vals = [struct.unpack_from("<I", blob2, i * 4)[0] for i in range(size)]
        if not all(looks_like_province_id(v) for v in vals):
            continue
        if any(c["off"] == hex(off) for c in cands):
            continue
        cands.append({
            "kind": "cpdx_u32",
            "off": hex(off),
            "n": len(vals),
            "province_ids": vals[:32],
            "matches_current_only": vals == [current_prov] if current_prov is not None else False,
        })
    useful = [c for c in cands if not c["matches_current_only"] or c["n"] > 1]
    return useful if useful else cands


def deepen_paths(b, base, rows, country_tag=None):
    carmy_vt = base + CA_VT_RVA
    deepened = []
    nonempty = 0
    multi = 0
    tag_fps = 0
    for r in rows:
        obj = r["army"]
        vt = try_u64(b, obj)
        if vt and vt != carmy_vt:
            continue
        cands = scan_army_path_cands(b, base, obj, r.get("province_id"))
        filtered = []
        for c in cands:
            ids = c.get("province_ids") or []
            if country_tag is not None and len(ids) == 1 and ids[0] == country_tag:
                tag_fps += 1
                continue
            if c.get("matches_current_only") and c.get("n", 0) <= 1:
                continue
            filtered.append(c)
        status = "nonempty_candidate" if filtered else ("current_only_or_tag_fp" if cands else "empty_or_absent")
        if filtered:
            nonempty += 1
            if any(c["n"] > 1 for c in filtered):
                multi += 1
        deepened.append({
            "index": r["index"],
            "handle": list(r["handle"]),
            "province_id": r["province_id"],
            "army": hex(obj),
            "movement_dest_status": status,
            "vector_cands": filtered[:4],
        })
    return {
        "carmy_rows": len(deepened),
        "movement_dest_nonempty_count": nonempty,
        "multi_province_cand_count": multi,
        "tag_singleton_fps_filtered": tag_fps,
        "armies_sample": deepened[:24],
        "note": "Candidates only; country_tag singletons filtered; empty means do NOT invent destinations.",
    }


def resolve_handle(b, typ, idx, base):
    """Minimal type/index table resolve (same pattern as prior phases)."""
    try:
        from process import resolve_type_index  # type: ignore
        return resolve_type_index(b, typ, idx)
    except Exception:
        pass
    # Fallback via army_subjects if available
    try:
        fn = getattr(army_subjects, "resolve_handle", None) or getattr(army_subjects, "resolve_type_index", None)
        if fn:
            return fn(b, typ, idx, base)
    except Exception:
        pass
    return None


def read_cpdx(b, base, addr):
    try:
        data = u64(b, addr)
        cap = i32(b, addr + 8)
        size = i32(b, addr + 12)
    except Exception:
        return None
    sentinel = base <= data < base + getattr(b, "image_size", 0x40000000)
    plausible = data > 0x10000 and 0 <= size <= 4096 and size <= max(cap, size) + 8
    return {"data": data, "cap": cap, "size": size, "plausible": plausible, "sentinel": sentinel}


def read_inst_fields(b, base, oi):
    hdr = None
    # Prefer process helpers used in 2fy via inline table walk if import fails
    try:
        # reuse pattern: find via army_subjects internal if exposed
        from calling import handle_table  # noqa
    except Exception:
        pass
    # Inline: G_HANDLES pattern from prior scripts — soft try
    try:
        ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
        # Many phases use Backend.resolve — try getattr
        res = getattr(b, "resolve", None)
        if callable(res):
            hdr = res(TYPE_OG, oi)
    except Exception:
        hdr = None
    if hdr is None:
        # Scan via army_subjects.iter if available for OGs — skip if not
        return {"oi": oi, "ok": False, "reason": "no_resolve"}
    try:
        og = hdr + 0x10 if isinstance(hdr, int) else None
        if og is None:
            return {"oi": oi, "ok": False, "reason": "bad_hdr"}
        a98 = read_cpdx(b, base, og + 0x98)
        if not a98 or not a98["plausible"] or a98["size"] < 1 or a98["sentinel"]:
            return {"oi": oi, "ok": False, "reason": "no_inst_arr"}
        inst = u64(b, a98["data"])
        vt = u64(b, inst) - base
        if vt != INST_VT:
            return {"oi": oi, "ok": False, "vt": hex(vt), "reason": "vt_mismatch"}
        out = {"oi": oi, "ok": True, "inst": hex(inst), "vt_ok": True}
        for off, key in ((0x70, "arr70"), (0x88, "arr88"), (0xE0, "arr_e0"), (0x100, "arr_100")):
            arr = read_cpdx(b, base, inst + off)
            if not arr or not arr["plausible"]:
                out[key] = None
                continue
            info = {k: arr[k] for k in ("size", "cap", "plausible", "sentinel")}
            info["data_hex"] = hex(arr["data"])
            if arr["size"] > 0 and not arr["sentinel"]:
                n = min(arr["size"], 64)
                blob = try_read(b, arr["data"], n * 4)
                u32s = []
                if blob and len(blob) >= n * 4:
                    u32s = [struct.unpack_from("<I", blob, i * 4)[0] for i in range(n)]
                info["u32_stream"] = u32s[:32]
                info["u32_all_province_shaped"] = bool(u32s) and all(looks_like_province_id(v) for v in u32s)
                # ptr kinds for +0x88
                if off == 0x88:
                    blobp = try_read(b, arr["data"], min(arr["size"], 32) * 8)
                    kinds = Counter()
                    if blobp:
                        for i in range(min(arr["size"], 32)):
                            p = struct.unpack_from("<Q", blobp, i * 8)[0]
                            if p < 0x10000:
                                kinds["nullish"] += 1
                                continue
                            try:
                                vr = u64(b, p) - base
                            except Exception:
                                kinds["unreadable"] += 1
                                continue
                            if vr == CP_VT:
                                kinds["CProvince"] += 1
                            elif vr == CA_VT_RVA:
                                kinds["CArmy"] += 1
                            elif vr == INST_VT:
                                kinds["COrderInstance"] += 1
                            else:
                                kinds[f"vt_{hex(vr)}"] += 1
                    info["ptr_kinds"] = dict(kinds)
            out[key] = info
        return out
    except Exception as e:
        return {"oi": oi, "ok": False, "reason": str(e)}


def try_resolve_og(b, base, oi):
    """Resolve OG header via handle-table helpers used across phases."""
    # Import pattern from phase2fy if present as module-level
    candidates = [
        "scripts.phase2fy_army_path_vs_70",
    ]
    # Inline copy of resolve from process
    for name in ("resolve_handle", "resolve_type_index", "lookup_handle"):
        fn = getattr(b, name, None)
        if callable(fn):
            try:
                return fn(TYPE_OG, oi)
            except TypeError:
                try:
                    return fn(b, TYPE_OG, oi, base)
                except Exception:
                    pass
            except Exception:
                pass
    # Fall back: read handle table from army_subjects
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "phase2fy", ROOT / "scripts" / "phase2fy_army_path_vs_70.py"
        )
        mod = importlib.util.module_from_spec(spec)
        # Don't exec full main — just steal resolve_handle if defined at import
        # Safer: read source for resolve_handle function body via prior known API
    except Exception:
        pass
    return None


def bounded_path_poll(b, base, country_tag, seconds=PATH_WINDOW_S, interval=PATH_INTERVAL_S):
    t0 = time.time()
    best = None
    ticks = 0
    while time.time() - t0 < seconds:
        rows = army_subjects.iter_armies_by_index(b, base, INDEX_LO, INDEX_HI, country_tag=country_tag)
        carmy_vt = base + CA_VT_RVA
        carmy = []
        for r in rows:
            vt = try_u64(b, r["army"])
            if vt == carmy_vt and r.get("handle_ok") and r.get("province_id_ok"):
                carmy.append(r)
        paths = deepen_paths(b, base, carmy, country_tag=country_tag)
        ticks += 1
        if best is None or paths["movement_dest_nonempty_count"] > best["movement_dest_nonempty_count"]:
            best = paths
            best["tick"] = ticks
            best["elapsed_s"] = round(time.time() - t0, 2)
        if paths["movement_dest_nonempty_count"] > 0 and paths.get("multi_province_cand_count", 0) > 0:
            break
        time.sleep(interval)
    if best is None:
        best = {
            "carmy_rows": 0,
            "movement_dest_nonempty_count": 0,
            "multi_province_cand_count": 0,
            "armies_sample": [],
            "tick": ticks,
            "elapsed_s": round(time.time() - t0, 2),
        }
    best["poll_ticks"] = ticks
    best["poll_window_s"] = seconds
    return best


def sample_instances(b, base):
    """Try seed OIs using phase2fy resolve_handle by importing helpers carefully."""
    # Load resolve_handle + read_inst70 from phase2fy without running main
    import importlib.util
    import types

    path = ROOT / "scripts" / "phase2fy_army_path_vs_70.py"
    src = path.read_text(encoding="utf-8")
    # Strip main invocation
    if 'if __name__' in src:
        src = src.split('if __name__')[0]
    mod = types.ModuleType("phase2fy_helpers")
    mod.__file__ = str(path)
    # Provide expected globals
    sys.modules["phase2fy_helpers"] = mod
    try:
        exec(compile(src, str(path), "exec"), mod.__dict__)
    except Exception as e:
        return {"error": f"import_helpers_failed: {e}", "rows": []}
    rows = []
    with70 = 0
    with88 = 0
    for oi in SEED_OIS:
        try:
            inst = mod.read_inst70(b, base, oi)
        except Exception as e:
            rows.append({"oi": oi, "ok": False, "reason": str(e)})
            continue
        if not inst or not inst.get("vt_ok"):
            rows.append({"oi": oi, "ok": False, "inst": inst})
            continue
        a70 = inst.get("arr70") or {}
        a88 = inst.get("arr88") or {}
        if a70.get("u32_all_province_shaped") and a70.get("u32_stream"):
            with70 += 1
        if (a88.get("ptr_kinds") or {}).get("CProvince"):
            with88 += 1
        rows.append({
            "oi": oi,
            "ok": True,
            "inst": inst.get("inst"),
            "arr70_n": (a70.get("size") if a70 else None),
            "arr70_province_shaped": a70.get("u32_all_province_shaped"),
            "arr70_sample": (a70.get("u32_stream") or [])[:12],
            "arr88_size": a88.get("size") if a88 else None,
            "arr88_ptr_kinds": a88.get("ptr_kinds") if a88 else None,
            "arr_e0_size": (inst.get("arr_e0") or {}).get("size"),
            "arr_100_size": (inst.get("arr_100") or {}).get("size"),
            "arr_e0_sample": ((inst.get("arr_e0") or {}).get("u32_stream") or [])[:8],
            "arr_100_sample": ((inst.get("arr_100") or {}).get("u32_stream") or [])[:8],
        })
    return {
        "seed_ois": list(SEED_OIS),
        "ok_count": sum(1 for r in rows if r.get("ok")),
        "with_70_province_shaped": with70,
        "with_88_cprovince": with88,
        "rows": rows,
    }


def write_doc(rep: dict) -> None:
    live = rep.get("live") or {}
    paths = rep.get("path_poll") or {}
    inst = rep.get("instance_sample") or {}
    DOC.write_text(
        "\n".join([
            "# Phase 2gm — CArmy path / movement_dest + Instance field RO",
            "",
            f"**Result:** `{rep.get('result')}`  ",
            f"**Live:** pid {live.get('pid')} · {live.get('ui_date')} · hours={live.get('hours')} · tag={live.get('country_tag_filter')}  ",
            f"**Path nonempty:** {paths.get('movement_dest_nonempty_count')} / {paths.get('carmy_rows')} "
            f"(multi-prov {paths.get('multi_province_cand_count')}) · poll {paths.get('elapsed_s')}s / {paths.get('poll_ticks')} ticks  ",
            f"**Instance seed OK:** {inst.get('ok_count')} · +0x70 shaped {inst.get('with_70_province_shaped')} · +0x88 CProvince {inst.get('with_88_cprovince')}  ",
            "",
            "**allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb/2gk **NOT executed**",
            "",
            "## Offline field catalog (perception map)",
            "",
            "### COrderInstance",
            "",
            "| off | kind | status | role |",
            "| --- | --- | --- | --- |",
        ]
        + [
            f"| `{r['off']}` | `{r['kind']}` | **{r['status']}** | {r['role']} |"
            for r in INSTANCE_FIELD_CATALOG
        ]
        + [
            "",
            "### CArmy path / movement_dest",
            "",
            "| field | status | role |",
            "| --- | --- | --- |",
        ]
        + [
            f"| `{r['field']}` | **{r['status']}** | {r['role']} |"
            for r in CARMY_PATH_CATALOG
        ]
        + [
            "",
            "## Works",
            "",
            "- Offline Instance+CArmy perception field catalog (proven vs candidate)",
            "- Bounded ≤60s ITA CArmy path-vector RO deepen (no invent)",
            "- Seed-OI Instance +0x70/+0x88/+0xe0/+0x100 sample (when resolve works)",
            "",
            "## Stubbed / HARD_DENY",
            "",
            "- named demangled `movement_dest` field",
            "- in-process ring_embed · Post · ALLOW_POST · tool-gate · 2fb/2gk execute",
            "- CMove midflight hex · Post inject · ask-user right-click",
            "",
            f"**Next shortest blocker (NON-Post):** {rep.get('next_shortest_blocker')}",
            "",
            "Script: `scripts/phase2gm_carmy_path_instance_ro.py`",
            "",
            f"*Phase 2gm · {rep.get('captured_at_shanghai')} Asia/Shanghai*",
            "",
        ]),
        encoding="utf-8",
    )


def main() -> int:
    assert allow_post() is False, "allow_post must stay False"
    pid = find_pid()
    live = {"pid": pid}
    paths = {}
    inst = {}
    err = None
    if not pid:
        err = "no hoi4 pid"
    else:
        try:
            b = Backend(pid)
            base = int(b.image_base)
            tag = player_tag(b, base)
            live = live_meta(b, base, pid, tag)
            # Prefer short poll; stop early on multi-province hit
            paths = bounded_path_poll(b, base, tag)
            inst = sample_instances(b, base)
            live = live_meta(b, base, pid, tag)  # refresh hours
        except Exception as e:
            err = str(e)

    shanghai = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
    nonempty = (paths or {}).get("movement_dest_nonempty_count", 0)
    multi = (paths or {}).get("multi_province_cand_count", 0)
    inst_ok = (inst or {}).get("ok_count", 0)
    with70 = (inst or {}).get("with_70_province_shaped", 0)

    if err and not paths:
        result = "CARMY_PATH_INSTANCE_RO_NO_LIVE"
    elif multi > 0:
        result = "CARMY_PATH_INSTANCE_RO_MULTI_PROV_HIT"
    elif nonempty > 0:
        result = "CARMY_PATH_INSTANCE_RO_NONEMPTY_CAND"
    elif with70 > 0 or inst_ok > 0:
        result = "CARMY_PATH_INSTANCE_RO_INSTANCE_HIT_PATH_EMPTY"
    else:
        result = "CARMY_PATH_INSTANCE_RO_HONEST_EMPTY"

    next_blocker = (
        "NON-Post: gate CLOSED; human midflight CMove hex OR human SAFE Post for Strategic "
        "ring_embed; retry GitHub push when auth reachable — still NO ALLOW_POST"
    )
    if multi == 0 and nonempty == 0:
        next_blocker = (
            "NON-Post: path/movement_dest still empty this window (RO ceiling) — "
            "human midflight CMove hex OR SAFE Post for ring_embed; push when GitHub reachable; "
            "still NO ALLOW_POST"
        )

    rep = {
        "phase": "2gm",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "captured_at_shanghai": shanghai,
        "allow_post": False,
        "executed_2fb_recipe": False,
        "executed_2gk_recipe": False,
        "tool_gate": "CLOSED",
        "result": result,
        "error": err,
        "live": live,
        "offline_catalog": {
            "instance_fields": INSTANCE_FIELD_CATALOG,
            "carmy_path_fields": CARMY_PATH_CATALOG,
        },
        "path_poll": {
            k: paths.get(k)
            for k in (
                "carmy_rows",
                "movement_dest_nonempty_count",
                "multi_province_cand_count",
                "poll_ticks",
                "poll_window_s",
                "elapsed_s",
                "armies_sample",
                "note",
            )
        } if paths else {},
        "instance_sample": inst,
        "works": [
            "offline Instance+CArmy perception field catalog",
            "bounded <=60s CArmy path-vector RO deepen",
            "seed-OI Instance +0x70/+0x88/+0xe0/+0x100 sample",
        ],
        "stubbed": [
            "named demangled movement_dest",
            "in-process ring_embed",
            "2fb/2gk execute",
            "ALLOW_POST",
            "tool-gate",
            "CMove midflight hex",
            "Post inject",
        ],
        "next_shortest_blocker": next_blocker,
    }
    OUT.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2gm",
                "result": result,
                "allow_post": False,
                "live": live,
                "path_nonempty": nonempty,
                "path_multi": multi,
                "instance_ok": inst_ok,
                "instance_70_shaped": with70,
                "next_shortest_blocker": next_blocker,
                "sha_base": "55c73f0",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    write_doc(rep)
    print(json.dumps({"result": result, "live": live, "nonempty": nonempty, "multi": multi, "inst_ok": inst_ok}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
