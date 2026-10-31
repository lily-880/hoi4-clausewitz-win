"""Phase 2bm midflight-ready watcher (RO).

Polls DummyServer pending / stage / small writable heap windows for known army-cmd VTs.
Does NOT inject input, does NOT Post, does NOT change speed.
Intended to run while a real user right-clicks a move; safe to leave armed overnight.

Phase 2em: edge-burst re-poll when drain/exec/seq advances; RO sightline log for any
watched VT (incl. CHourlyTickCommand) without breaking for non-Move. Still NEVER Posts.

Usage:
  python scripts/phase2bm_midflight_ready.py [--seconds 120] [--interval 0.05]
  Long arm (preferred): --seconds 86400 --interval 0.02 --heap-every 0 --burst-on-edge 12
  Heartbeat: reports/midflight_watcher_heartbeat.json
  Instant capture: reports/midflight_cmove_capture.json
  Sightline: reports/midflight_watcher_sightline.json
"""
from __future__ import annotations
import argparse, json, struct, sys, time
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))
from process import Backend, find_pid
import post_abi, cmd_layout

OUT = ROOT / "reports" / "phase2bm_midflight_ready.json"
HEARTBEAT = ROOT / "reports" / "midflight_watcher_heartbeat.json"
CAPTURE = ROOT / "reports" / "midflight_cmove_capture.json"
SIGHTLINE = ROOT / "reports" / "midflight_watcher_sightline.json"
ARMY_MOVE_NAMES = (
    "CMoveCommand", "CUnitMoveAction", "CStrategicRedeploymentCommand",
    "CUnitStrategicMoveAction", "CCancelMovementCommand",
)
WATCH = {
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
    cmd_layout.CHAT["vt"]: "CChatCommand",
    cmd_layout.STARTGAME["vt"]: "CStartGameCommand",
}


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def try_u64(b, a):
    try:
        return u64(b, a)
    except Exception:
        return None


def _u32(buf, off):
    return struct.unpack_from("<I", buf, off)[0]


def _u64(buf, off):
    return struct.unpack_from("<Q", buf, off)[0]


def dump_unit_move_action(act: bytes, base: int, *, as_embed: bool) -> dict:
    """Phase 2eo: full CUnitMoveAction field decode (cmd_layout.MOVE.action.fields)."""
    need = 0x60  # through sticky@0x5C
    if len(act) < need:
        return {"error": f"short action buf {len(act)}<{need}", "hex": act.hex()}
    vt_raw = _u64(act, 0)
    return {
        "layout": "CUnitMoveAction",
        "as_embed": as_embed,
        "vt_rva": hex(vt_raw - base) if vt_raw >= base else hex(vt_raw),
        "type_id_at_plus8": _u32(act, 8),
        "unit_handle": [_u32(act, 0x10), _u32(act, 0x14)],
        "province_arr": hex(_u64(act, 0x18)),
        "province_size": _u32(act, 0x24),
        "path_arr": hex(_u64(act, 0x30)),
        "path_size": _u32(act, 0x3C),
        "clear": act[0x50],
        "safe": act[0x51],
        "safe_until_end": act[0x52],
        "safe_nonsafe_fb": act[0x53],
        "avoid": act[0x55],
        "move_priority": _u32(act, 0x58),
        "sticky": act[0x5C],
        "hex": act[:need].hex(),
    }


def dump_strategic_move_action(act: bytes, base: int, *, as_embed: bool) -> dict:
    """Phase 2eo: CUnitStrategicMoveAction fields (cmd_layout.STRATEGIC.action.fields)."""
    need = 0x28
    if len(act) < need:
        return {"error": f"short strategic action {len(act)}<{need}", "hex": act.hex()}
    vt_raw = _u64(act, 0)
    return {
        "layout": "CUnitStrategicMoveAction",
        "as_embed": as_embed,
        "vt_rva": hex(vt_raw - base) if vt_raw >= base else hex(vt_raw),
        "army_handle": [_u32(act, 0x10), _u32(act, 0x14)],
        "province": _u32(act, 0x18),
        "clear": act[0x1C],
        "move_priority": _u32(act, 0x20),
        "hex": act[:need].hex(),
    }


def dump_cancel_fields(blob: bytes) -> dict:
    """Phase 2eo: CCancelMovementCommand fields."""
    if len(blob) < 0x48:
        return {"error": f"short cancel {len(blob)}", "hex": blob.hex()}
    return {
        "layout": "CCancelMovementCommand",
        "units_data": hex(_u64(blob, 0x28)),
        "units_count": _u32(blob, 0x34),
        "sticky": blob[0x40],
    }


def dump_cmd(b, base, addr, name):
    # Move cmd size 0x88; read enough for embeds / cancel
    blob = b.read(addr, 0xA0)
    vt = struct.unpack_from("<Q", blob, 0)[0] - base
    out = {
        "name": name,
        "addr": hex(addr),
        "vt_rva": hex(vt),
        "tick": struct.unpack_from("<I", blob, 0xC)[0] if len(blob) >= 0x10 else None,
        "seq": struct.unpack_from("<I", blob, 0x1C)[0] if len(blob) >= 0x20 else None,
        "hex": blob[:0x88].hex() if len(blob) >= 0x88 else blob.hex(),
        "captured_at_asia_shanghai": datetime.now().strftime("%Y-%m-%d %H:%M:%S %z"),
        "phase_decode": "2eo",
    }
    if name == "CMoveCommand" and len(blob) >= 0x28 + 0x60:
        out["action_embed"] = dump_unit_move_action(blob[0x28:], base, as_embed=True)
    elif name == "CUnitMoveAction":
        out["action_fields"] = dump_unit_move_action(blob, base, as_embed=False)
    elif name == "CStrategicRedeploymentCommand" and len(blob) >= 0x28 + 0x28:
        out["action_embed"] = dump_strategic_move_action(blob[0x28:], base, as_embed=True)
    elif name == "CUnitStrategicMoveAction":
        out["action_fields"] = dump_strategic_move_action(blob, base, as_embed=False)
    elif name == "CCancelMovementCommand":
        out["cancel_fields"] = dump_cancel_fields(blob)
    return out


def walk_ptr_list(b, base, head, limit=64):
    hits = []
    seen = set()
    cur = head
    while cur and cur not in seen and len(hits) < limit:
        seen.add(cur)
        vt = try_u64(b, cur)
        if vt is None:
            break
        name = WATCH.get(vt - base)
        if name:
            try:
                hits.append(dump_cmd(b, base, cur, name))
            except Exception as e:
                hits.append({"addr": hex(cur), "name": name, "error": str(e)})
        nxt = try_u64(b, cur + 8)
        if nxt is None or nxt == cur:
            break
        cur = nxt
    return hits


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def army_move_filter(captures):
    return [c for c in captures if c.get("name") in ARMY_MOVE_NAMES]


def sample_queues(b, base, sess, server):
    """One RO pass over pending + stage; return (move_hits, all_watched_hits, counters)."""
    pending_h = try_u64(b, server + post_abi.CDummyServer_PENDING) or 0
    stage = try_u64(b, sess + post_abi.CSession_STAGE_ARRAY) or 0
    scount = u32(b, sess + post_abi.CSession_STAGE_COUNT)
    drain = u32(b, sess + post_abi.CSession_DRAIN_COUNTER)
    exec_c = u32(b, sess + post_abi.CSession_EXEC_COUNTER)
    seq = u32(b, server + 0xD0)
    counters = {"drain": drain, "exec": exec_c, "seq": seq, "stage_count": scount}
    watched = []
    for hit in walk_ptr_list(b, base, pending_h):
        watched.append({"source": "pending", **hit})
    if stage and 0 < scount < 64:
        for i in range(scount):
            ptr = try_u64(b, stage + i * 8)
            if not ptr:
                continue
            vt = try_u64(b, ptr)
            if vt is None:
                continue
            name = WATCH.get(vt - base)
            if not name:
                continue
            try:
                watched.append({"source": f"stage[{i}]", **dump_cmd(b, base, ptr, name)})
            except Exception as e:
                watched.append({"source": f"stage[{i}]", "addr": hex(ptr), "name": name, "error": str(e)})
    moves = [h for h in watched if h.get("name") in ARMY_MOVE_NAMES]
    return moves, watched, counters


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=30.0)
    ap.add_argument("--interval", type=float, default=0.05)
    ap.add_argument("--heap-every", type=int, default=0, help="heap scan every N polls (0=never; default off to save CPU)")
    ap.add_argument("--heap-mb", type=int, default=256)
    ap.add_argument("--heartbeat-every", type=int, default=40, help="write heartbeat every N polls (0=off)")
    ap.add_argument("--burst-on-edge", type=int, default=12,
                    help="extra immediate RO samples when drain/exec/seq advances (0=off; Phase 2em)")
    ap.add_argument("--sightline-every", type=int, default=200,
                    help="persist sightline JSON every N polls (0=off)")
    args = ap.parse_args()

    b = Backend(find_pid("hoi4.exe"))
    base = int(b.image_base)
    sess = u64(b, base + post_abi.G_SESSION)
    server = u64(b, sess + post_abi.CSession_SERVER)
    t0 = time.time()
    polls = 0
    captures = []
    last_counters = None
    prev_counters = None
    sight_counts = {}
    sight_first = {}
    sight_last = {}
    edge_events = 0
    burst_samples = 0
    has_regions = hasattr(b, "regions")
    if not has_regions:
        try:
            from mem import Proc
            p = Proc(find_pid("hoi4.exe"))
            has_regions = hasattr(p, "regions")
            region_src = p
        except Exception:
            region_src = None
    else:
        region_src = b

    while time.time() - t0 < args.seconds:
        polls += 1
        moves, watched, last_counters = sample_queues(b, base, sess, server)

        edge = False
        if prev_counters is not None:
            edge = (
                last_counters["drain"] != prev_counters["drain"]
                or last_counters["exec"] != prev_counters["exec"]
                or last_counters["seq"] != prev_counters["seq"]
            )
        if edge:
            edge_events += 1
        if edge and args.burst_on_edge > 0:
            for _ in range(args.burst_on_edge):
                burst_samples += 1
                m2, w2, c2 = sample_queues(b, base, sess, server)
                last_counters = c2
                moves.extend(m2)
                watched.extend(w2)
                if m2:
                    break
        prev_counters = dict(last_counters)

        for hit in watched:
            name = hit.get("name") or "?"
            sight_counts[name] = sight_counts.get(name, 0) + 1
            meta = {
                "source": hit.get("source"),
                "addr": hit.get("addr"),
                "vt_rva": hit.get("vt_rva"),
                "poll": polls,
                "counters": dict(last_counters),
                "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S %z"),
            }
            if name not in sight_first:
                sight_first[name] = meta
            sight_last[name] = meta

        for hit in moves:
            captures.append(hit)

        if args.heap_every and polls % args.heap_every == 0 and region_src is not None and has_regions:
            try:
                from mem import Proc
                src = Proc(find_pid("hoi4.exe"))
                found, scanned = [], 0
                needles = {
                    name: struct.pack("<Q", base + vt)
                    for vt, name in WATCH.items()
                    if name.startswith(("CMove", "CUnit", "CStrategic", "CCancel"))
                }
                for m in src.regions(writable=True, min_size=0x1000):
                    start_m, end_m = m["start"], m["end"]
                    if base <= start_m < base + 0x4000000:
                        continue
                    pos = start_m
                    while pos < end_m and scanned < (args.heap_mb << 20) and len(found) < 4:
                        n = min(2 << 20, end_m - pos)
                        data = src.try_read(pos, n) if hasattr(src, "try_read") else None
                        if data is None:
                            try:
                                data = src.read(pos, n)
                            except Exception:
                                data = None
                        scanned += n
                        if data:
                            for name, needle in needles.items():
                                j = data.find(needle)
                                if j >= 0:
                                    addr = pos + j
                                    try:
                                        found.append(dump_cmd(b, base, addr, name))
                                    except Exception:
                                        found.append({"addr": hex(addr), "name": name})
                        pos += n
                    if len(found) >= 4:
                        break
                for hit in found:
                    if hit.get("name", "").startswith(("CMove", "CUnit", "CStrategic", "CCancel")):
                        captures.append({"source": "heap", "scanned_mb": scanned >> 20, **hit})
            except Exception:
                pass

        if captures:
            army_move_hits = army_move_filter(captures)
            snap = {
                "phase": "2em_midflight_capture",
                "posting": "DISABLED",
                "allow_post": False,
                "speed_rule": "pause or 1x only; never 5x; no input injection",
                "caught_army_move": bool(army_move_hits),
                "polls": polls,
                "last_counters": last_counters,
                "captures": captures,
                "sight_counts": sight_counts,
                "captured_at_asia_shanghai": datetime.now().strftime("%Y-%m-%d %H:%M:%S %z"),
                "note": "Instant RO capture dump. Do NOT Post. Pause game after capture.",
            }
            write_json(CAPTURE, snap)
            write_json(OUT, {**snap, "phase": "2bm_midflight_ready", "seconds": args.seconds, "interval": args.interval})
            write_json(SIGHTLINE, {
                "phase": "2em_sightline",
                "posting": "DISABLED",
                "allow_post": False,
                "sight_counts": sight_counts,
                "sight_first": sight_first,
                "sight_last": sight_last,
                "edge_events": edge_events,
                "burst_samples": burst_samples,
                "polls": polls,
                "last_counters": last_counters,
                "ts_asia_shanghai": datetime.now().strftime("%Y-%m-%d %H:%M:%S %z"),
            })
            break

        if args.heartbeat_every and polls % args.heartbeat_every == 0:
            write_json(HEARTBEAT, {
                "phase": "2em_midflight_heartbeat",
                "posting": "DISABLED",
                "allow_post": False,
                "polls": polls,
                "elapsed_s": round(time.time() - t0, 1),
                "last_counters": last_counters,
                "captures": 0,
                "caught_army_move": False,
                "heap_every": args.heap_every,
                "interval": args.interval,
                "burst_on_edge": args.burst_on_edge,
                "edge_events": edge_events,
                "burst_samples": burst_samples,
                "sight_counts": sight_counts,
                "sightline_ok": bool(sight_counts),
                "ts_asia_shanghai": datetime.now().strftime("%Y-%m-%d %H:%M:%S %z"),
                "note": "RO heartbeat; edge-burst armed. Move capture still needs live land order (peacetime Haiti AI-on alone insufficient).",
            })
        if args.sightline_every and polls % args.sightline_every == 0:
            write_json(SIGHTLINE, {
                "phase": "2em_sightline",
                "posting": "DISABLED",
                "allow_post": False,
                "sight_counts": sight_counts,
                "sight_first": sight_first,
                "sight_last": sight_last,
                "edge_events": edge_events,
                "burst_samples": burst_samples,
                "polls": polls,
                "last_counters": last_counters,
                "ts_asia_shanghai": datetime.now().strftime("%Y-%m-%d %H:%M:%S %z"),
            })
        time.sleep(args.interval)

    army_move_hits = army_move_filter(captures)
    out = {
        "phase": "2bm_midflight_ready",
        "posting": "DISABLED",
        "allow_post": False,
        "speed_rule": "pause or 1x only; never 5x; no input injection",
        "seconds": args.seconds,
        "interval": args.interval,
        "heap_every": args.heap_every,
        "burst_on_edge": args.burst_on_edge,
        "polls": polls,
        "last_counters": last_counters,
        "captures": captures,
        "caught_army_move": bool(army_move_hits),
        "sight_counts": sight_counts,
        "edge_events": edge_events,
        "burst_samples": burst_samples,
        "heartbeat": str(HEARTBEAT),
        "capture_path": str(CAPTURE),
        "sightline_path": str(SIGHTLINE),
        "note": "Armed RO watcher (2em edge-burst+sightline). Empty Move captures expected without live land order; Phase 2es expanded land VT sightline.",
    }
    write_json(OUT, out)
    write_json(SIGHTLINE, {
        "phase": "2em_sightline",
        "posting": "DISABLED",
        "allow_post": False,
        "sight_counts": sight_counts,
        "sight_first": sight_first,
        "sight_last": sight_last,
        "edge_events": edge_events,
        "burst_samples": burst_samples,
        "polls": polls,
        "last_counters": last_counters,
        "caught_army_move": bool(army_move_hits),
        "ts_asia_shanghai": datetime.now().strftime("%Y-%m-%d %H:%M:%S %z"),
    })
    if army_move_hits and not CAPTURE.exists():
        write_json(CAPTURE, {**out, "phase": "2em_midflight_capture"})
    print(json.dumps({
        "polls": polls,
        "caught_army_move": out["caught_army_move"],
        "captures": len(captures),
        "sight_counts": sight_counts,
        "edge_events": edge_events,
        "burst_samples": burst_samples,
        "last_counters": last_counters,
        "wrote": str(OUT),
        "heartbeat": str(HEARTBEAT),
        "sightline": str(SIGHTLINE),
    }))


if __name__ == "__main__":
    main()