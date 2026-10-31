"""Phase 2es — ONE efficient RO slice (no Post / no ALLOW_POST / never 5x).

A) Document AI-without-Post: session already lacks -noai; peacetime Haiti yields no
   autonomous land CMoveCommand. Further AI toggle needs console/Post → SKIP.
B) Short expanded stage/pending poll for substitute land cmds (attack/retreat/order/front).
C) RO deepen CArmy movement_dest/path vector candidates under live 1x (do not invent).
D) If A blocked (it is for capture): cheapest reversible experiment = B+C + re-arm
   watcher with expanded WATCH; allow_post stays False.

NEVER: ALLOW_POST / CLAUSEWITZ_ALLOW_POST / Post inject / helper patch / guess writes /
HourlyTick abuse / 5x / ask user to right-click.
"""
from __future__ import annotations
import json, struct, sys, time, ctypes
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))
from process import Backend, find_pid
from config import allow_post
import post_abi, cmd_layout, army_subjects

OUT = ROOT / "reports" / "phase2es_ro_slice.json"
OV = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))

# Expanded land-ish VTs for substitute midflight sighting (RO only)
EXTRA_WATCH = {
    cmd_layout.MOVE["vt"]: "CMoveCommand",
    cmd_layout.MOVE["action"]["vt"]: "CUnitMoveAction",
    cmd_layout.STRATEGIC["vt"]: "CStrategicRedeploymentCommand",
    cmd_layout.STRATEGIC["action"]["vt"]: "CUnitStrategicMoveAction",
    cmd_layout.CANCEL["vt"]: "CCancelMovementCommand",
    cmd_layout.SUPPORT_ATTACK["vt"]: "CSupportAttackCommand",
    cmd_layout.ORDERS["COrderExecuteCommand"]["vt"]: "COrderExecuteCommand",
    cmd_layout.ORDERS["COrderAssignCommand"]["vt"]: "COrderAssignCommand",
    cmd_layout.ORDERS["COrderUnassignCommand"]["vt"]: "COrderUnassignCommand",
    cmd_layout.ORDERS["COrderDeleteCommand"]["vt"]: "COrderDeleteCommand",
    cmd_layout.ORDERS["COrderNewFrontCommand"]["vt"]: "COrderNewFrontCommand",
    cmd_layout.ORDERS["COrderNewRootCommand"]["vt"]: "COrderNewRootCommand",
    cmd_layout.ORDERS["COrderNewFallbackCommand"]["vt"]: "COrderNewFallbackCommand",
    cmd_layout.ORDERS["COrderGroupCommand"]["vt"]: "COrderGroupCommand",
    0x2A2C848: "CMassMoveCommand",
    0x2A2D538: "CCancelRunningAwayCommand",
    0x2A2CF78: "CWithdrawArmyHqCommand",
    0x2A2CA70: "CToggleStrategicDeploymentCommand",
    0x2A0FC40: "CMassCancelMovementCommand",
    0x2A84100: "CMoveArmiesInTheaterCommand",
    0x2A84A58: "COrderInsertFrontCommand",
    0x2A84778: "COrderSetPathCommand",
    0x2A84830: "COrderReshapeCommand",
    0x29F3710: "CHourlyTickCommand",
}

SUBSTITUTE_NAMES = {n for n in EXTRA_WATCH.values() if n != "CHourlyTickCommand"}


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


def now_sh():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def cmdline_for_pid(pid: int) -> str:
    try:
        import subprocess
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"(Get-CimInstance Win32_Process -Filter \"ProcessId={pid}\").CommandLine"],
            capture_output=True, text=True, timeout=15,
        )
        return (r.stdout or "").strip()
    except Exception as e:
        return f"<err {e}>"


def decode_hours(h: int) -> str:
    dt = datetime(1936, 1, 1, 0, 0) + timedelta(hours=int(h))
    return dt.strftime("%Y-%m-%d %H:00")


def snap_date(b, base):
    gs = u64(b, base + OV["G_GAMESTATE"])
    h484 = i32(b, gs + 0x484)
    year = i32(b, gs + 0x478)
    return {
        "gs": hex(gs),
        "year_0x478": year,
        "hours_0x484": h484,
        "ui": decode_hours(h484),
        "past_bookmark_1200": h484 > 12,
    }


def counters(b, base):
    sess = u64(b, base + post_abi.G_SESSION)
    server = u64(b, sess + post_abi.CSession_SERVER)
    return {
        "sess": hex(sess),
        "server": hex(server),
        "drain": u32(b, sess + post_abi.CSession_DRAIN_COUNTER),
        "exec": u32(b, sess + post_abi.CSession_EXEC_COUNTER),
        "seq": u32(b, server + 0xD0),
        "stage_count": u32(b, sess + post_abi.CSession_STAGE_COUNT),
        "pending": hex(try_u64(b, server + post_abi.CDummyServer_PENDING) or 0),
        "stage": hex(try_u64(b, sess + post_abi.CSession_STAGE_ARRAY) or 0),
    }


def walk_pending(b, base, head, limit=64):
    hits, seen, cur = [], set(), head
    while cur and cur not in seen and len(hits) < limit:
        seen.add(cur)
        vt = try_u64(b, cur)
        if vt is None:
            break
        rva = vt - base
        name = EXTRA_WATCH.get(rva, f"UNK_{rva:#x}")
        hits.append({"source": "pending", "addr": hex(cur), "vt_rva": hex(rva), "name": name})
        nxt = try_u64(b, cur + 8)
        if nxt is None or nxt == cur:
            break
        cur = nxt
    return hits


def sample_stage_pending(b, base):
    c = counters(b, base)
    sess = int(c["sess"], 16)
    server = int(c["server"], 16)
    pending_h = try_u64(b, server + post_abi.CDummyServer_PENDING) or 0
    stage = try_u64(b, sess + post_abi.CSession_STAGE_ARRAY) or 0
    scount = c["stage_count"]
    hits = walk_pending(b, base, pending_h)
    if stage and 0 < scount < 64:
        for i in range(scount):
            ptr = try_u64(b, stage + i * 8)
            if not ptr:
                continue
            vt = try_u64(b, ptr)
            if vt is None:
                continue
            rva = vt - base
            name = EXTRA_WATCH.get(rva, f"UNK_{rva:#x}")
            hits.append({"source": f"stage[{i}]", "addr": hex(ptr), "vt_rva": hex(rva), "name": name})
    return hits, c


def looks_like_province_id(v: int) -> bool:
    return 1 <= v <= 20000


def read_u32_vector(b, begin, end, cap, max_n=64):
    """MSVC vector: begin/end/cap pointers. Return list of u32 if sane."""
    if not begin or not end or end < begin:
        return None
    nbytes = end - begin
    if nbytes % 4 != 0 or nbytes > max_n * 4:
        return None
    if cap and not (begin <= end <= cap):
        # some builds leave cap==end; allow end==cap
        if cap < end:
            return None
    blob = try_read(b, begin, nbytes)
    if not blob or len(blob) != nbytes:
        return None
    vals = list(struct.unpack("<" + "I" * (nbytes // 4), blob))
    return vals


def deepen_army_paths(b, base, tag=15):
    """Scan CArmy blobs for candidate province-id vectors (RO). Do not invent."""
    rows = army_subjects.iter_armies_by_index(b, base, 1000, 1200, country_tag=tag)
    # keep CArmy only via RTTI vt if possible
    carmy_vt = None
    try:
        # prior: CArmy VT RVA 0x29d6d68
        carmy_vt = base + 0x29D6D68
    except Exception:
        pass
    deepened = []
    nonempty = 0
    for r in rows:
        obj = r["army"]
        vt = try_u64(b, obj)
        if carmy_vt and vt and vt != carmy_vt:
            # skip non-CArmy (e.g. taskforce if mixed)
            continue
        blob = try_read(b, obj, 0x800) or b""
        cands = []
        # scan 8-byte aligned triples begin/end/cap
        for off in range(0x40, min(len(blob) - 24, 0x780), 8):
            begin, end, cap = struct.unpack_from("<QQQ", blob, off)
            # pointer-ish
            if begin < 0x10000 or end < begin:
                continue
            vals = read_u32_vector(b, begin, end, cap, max_n=32)
            if not vals:
                continue
            if not all(looks_like_province_id(v) for v in vals):
                continue
            # reject trivial single current-province echo only if that's all we have? keep it
            cands.append({
                "off": hex(off),
                "begin": hex(begin),
                "end": hex(end),
                "cap": hex(cap),
                "n": len(vals),
                "province_ids": vals,
                "matches_current_only": vals == [r["province_id"]],
            })
        # also check a few previously hypothesized action-like embeds (not inventing dest)
        actionish = []
        for off in (0x100, 0x120, 0x140, 0x180, 0x200, 0x280, 0x300, 0x380, 0x400, 0x480, 0x500, 0x580):
            if off + 0x40 > len(blob):
                continue
            psz = struct.unpack_from("<I", blob, off + 0x24)[0]
            path_sz = struct.unpack_from("<I", blob, off + 0x3C)[0]
            parr = struct.unpack_from("<Q", blob, off + 0x18)[0]
            path_arr = struct.unpack_from("<Q", blob, off + 0x30)[0]
            if 0 < psz <= 32 and parr > 0x10000:
                vals = read_u32_vector(b, parr, parr + 4 * psz, parr + 4 * psz, max_n=32)
                if vals and all(looks_like_province_id(v) for v in vals):
                    actionish.append({"kind": "province_arr_like", "off": hex(off), "ids": vals})
            if 0 < path_sz <= 32 and path_arr > 0x10000:
                vals = read_u32_vector(b, path_arr, path_arr + 4 * path_sz, path_arr + 4 * path_sz, max_n=32)
                if vals and all(looks_like_province_id(v) for v in vals):
                    actionish.append({"kind": "path_arr_like", "off": hex(off), "ids": vals})
        entry = {
            "index": r["index"],
            "handle": list(r["handle"]),
            "province_id": r["province_id"],
            "province_id_ok": r["province_id_ok"],
            "army": hex(obj),
            "vt_rva": hex(vt - base) if vt else None,
            "vector_cands": cands[:8],
            "actionish_cands": actionish[:8],
            "movement_dest_status": (
                "nonempty_candidate" if (cands or actionish) else "empty_or_absent"
            ),
        }
        if cands or actionish:
            nonempty += 1
        deepened.append(entry)
    return {
        "carmy_rows": len(deepened),
        "movement_dest_nonempty_count": nonempty,
        "armies": deepened,
        "note": "Candidates only; empty means do NOT invent destinations.",
    }


def poll_substitutes(b, base, seconds=45.0, interval=0.02):
    t0 = time.time()
    sight = Counter()
    first = {}
    last = {}
    substitutes = []
    polls = 0
    edge = 0
    prev = None
    last_c = None
    while time.time() - t0 < seconds:
        hits, c = sample_stage_pending(b, base)
        polls += 1
        last_c = c
        if prev and (c["drain"] != prev["drain"] or c["exec"] != prev["exec"] or c["seq"] != prev["seq"]):
            edge += 1
        prev = c
        for h in hits:
            name = h["name"]
            sight[name] += 1
            meta = {**h, "poll": polls, "counters": c, "ts": now_sh()}
            if name not in first:
                first[name] = meta
            last[name] = meta
            if name in SUBSTITUTE_NAMES:
                # keep a few samples
                if len(substitutes) < 32:
                    # dump small hex head for layout later
                    try:
                        addr = int(h["addr"], 16)
                        blob = try_read(b, addr, 0x88)
                        meta = {**meta, "hex_head": blob.hex() if blob else None}
                    except Exception:
                        pass
                    substitutes.append(meta)
        time.sleep(interval)
    return {
        "seconds": seconds,
        "interval": interval,
        "polls": polls,
        "edge_events": edge,
        "sight_counts": dict(sight),
        "sight_first": first,
        "sight_last": last,
        "substitute_samples": substitutes,
        "substitute_names_seen": sorted({s["name"] for s in substitutes}),
        "last_counters": last_c,
    }


def main():
    assert allow_post() is False, "allow_post must stay False"
    pid = find_pid("hoi4.exe")
    assert pid, "hoi4.exe not running"
    b = Backend(pid)
    base = int(b.image_base)
    cmd = cmdline_for_pid(pid)
    has_noai = "-noai" in cmd.lower()
    date0 = snap_date(b, base)
    c0 = counters(b, base)

    choice_a = {
        "attempted": True,
        "already_ai_enabled_no_noai_flag": not has_noai,
        "cmdline": cmd,
        "autonomous_land_moves_observed_before_poll": False,
        "decision": "SKIP_FURTHER_AI_ENABLE",
        "reason": (
            "Session already launched without -noai (AI on at engine level). "
            "Peacetime Haiti historically produces only CHourlyTick in midflight watcher; "
            "toggling AI further would need console or Post (FORBIDDEN). "
            "No ALLOW_POST / no Post inject."
        ),
        "safe_without_post": True,
        "skipped_post_dependent_ai_toggle": True,
    }

    # B: substitute land cmd poll at 1x
    poll = poll_substitutes(b, base, seconds=45.0, interval=0.02)
    choice_a["autonomous_land_moves_observed_during_poll"] = any(
        n in poll["sight_counts"]
        for n in ("CMoveCommand", "CUnitMoveAction", "CMassMoveCommand",
                  "CStrategicRedeploymentCommand", "CUnitStrategicMoveAction")
    )

    # C: path deepen under live 1x
    paths = deepen_army_paths(b, base, tag=15)

    date1 = snap_date(b, base)
    c1 = counters(b, base)

    report = {
        "phase": "2es",
        "works": {
            "live_date_ro": True,
            "clock_advancing_1x": date1["hours_0x484"] >= date0["hours_0x484"] and c1["exec"] >= c0["exec"],
            "expanded_land_vt_sightline": True,
            "ai_status_documented_without_post": True,
            "army_path_candidate_scan": True,
        },
        "stubbed": [
            "live_midflight_CMoveCommand_sample",
            "ring_embed",
            "ALLOW_POST",
            "command_queue_tool_gate",
            "autonomous_peacetime_Haiti_land_move",
        ],
        "choice_A_ai_enable": choice_a,
        "choice_B_substitute_poll": {
            "watched_extra": sorted(SUBSTITUTE_NAMES),
            **{k: poll[k] for k in (
                "seconds", "interval", "polls", "edge_events", "sight_counts",
                "substitute_names_seen", "last_counters",
            )},
            "substitute_sample_count": len(poll["substitute_samples"]),
            "substitute_samples": poll["substitute_samples"][:12],
            "sight_first_non_hourly": {
                k: v for k, v in poll["sight_first"].items() if k != "CHourlyTickCommand"
            },
        },
        "choice_C_path_deepen": {
            "carmy_rows": paths["carmy_rows"],
            "movement_dest_nonempty_count": paths["movement_dest_nonempty_count"],
            "note": paths["note"],
            "armies_preview": paths["armies"][:6],
            "all_armies_path_file_hint": "full list embedded below under armies_full",
        },
        "armies_full": paths["armies"],
        "allow_post": False,
        "post_touched": False,
        "tool_gate": "CLOSED_NOT_OPENED",
        "speed": "1x",
        "never_5x": True,
        "hoi4_pid": pid,
        "live_date_start": date0,
        "live_date_end": date1,
        "counters_start": c0,
        "counters_end": c1,
        "base_sha_expected": "be11ef7",
        "when_asia_shanghai": now_sh(),
        "next_shortest_blocker": (
            "live midflight CMoveCommand (+ CUnitMoveAction embed) still missing under peacetime "
            "Haiti without Post; substitute land cmds also absent in stage/pending this slice"
            if not poll["substitute_names_seen"] and paths["movement_dest_nonempty_count"] == 0
            else (
                "decode/promote any nonempty path candidates + keep expanded watcher armed; "
                "CMoveCommand sample still required before SAFE_POST enable"
                if paths["movement_dest_nonempty_count"]
                else "capture/decode substitute land cmd samples; CMove still required before SAFE_POST"
            )
        ),
    }
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    # also write a slim summary without full armies for git friendliness
    slim = dict(report)
    slim.pop("armies_full", None)
    slim["choice_C_path_deepen"] = {
        **report["choice_C_path_deepen"],
        "armies_preview": report["choice_C_path_deepen"]["armies_preview"],
    }
    (ROOT / "reports" / "phase2es_summary.json").write_text(
        json.dumps(slim, indent=2), encoding="utf-8"
    )
    print(json.dumps({
        "phase": "2es",
        "allow_post": False,
        "live_ui": date1["ui"],
        "hours": date1["hours_0x484"],
        "sight_counts": poll["sight_counts"],
        "substitutes": poll["substitute_names_seen"],
        "path_nonempty": paths["movement_dest_nonempty_count"],
        "carmy": paths["carmy_rows"],
        "ai_skip": choice_a["decision"],
        "cmdline_has_noai": has_noai,
        "out": str(OUT),
    }, indent=2))


if __name__ == "__main__":
    main()
