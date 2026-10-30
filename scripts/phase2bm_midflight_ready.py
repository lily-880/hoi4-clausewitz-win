"""Phase 2bm midflight-ready watcher (RO).

Polls DummyServer pending / stage / small writable heap windows for known army-cmd VTs.
Does NOT inject input, does NOT Post, does NOT change speed.
Intended to run while a real user right-clicks a move; safe to leave armed overnight.

Usage:
  python scripts/phase2bm_midflight_ready.py [--seconds 120] [--interval 0.05]
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
WATCH = {
    cmd_layout.MOVE["vt"]: "CMoveCommand",
    cmd_layout.MOVE["action"]["vt"]: "CUnitMoveAction",
    cmd_layout.STRATEGIC["vt"]: "CStrategicRedeploymentCommand",
    cmd_layout.STRATEGIC["action"]["vt"]: "CUnitStrategicMoveAction",
    cmd_layout.CANCEL["vt"]: "CCancelMovementCommand",
    cmd_layout.ORDERS["COrderExecuteCommand"]["vt"]: "COrderExecuteCommand",
    cmd_layout.ORDERS["COrderAssignCommand"]["vt"]: "COrderAssignCommand",
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


def dump_cmd(b, base, addr, name):
    blob = b.read(addr, min(0x88, 0xA0))
    vt = struct.unpack_from("<Q", blob, 0)[0] - base
    out = {
        "name": name,
        "addr": hex(addr),
        "vt_rva": hex(vt),
        "tick": struct.unpack_from("<I", blob, 0xC)[0],
        "seq": struct.unpack_from("<I", blob, 0x1C)[0],
        "hex": blob.hex(),
        "captured_at_asia_shanghai": datetime.now().strftime("%Y-%m-%d %H:%M:%S %z"),
    }
    if name == "CMoveCommand" and len(blob) >= 0x88:
        act = blob[0x28:]
        out["action_embed"] = {
            "vt_rva": hex(struct.unpack_from("<Q", act, 0)[0] - base),
            "unit_handle": [
                struct.unpack_from("<I", act, 0x10)[0],
                struct.unpack_from("<I", act, 0x14)[0],
            ],
            "province_size": struct.unpack_from("<I", act, 0x24)[0],
            "path_size": struct.unpack_from("<I", act, 0x3C)[0],
            "clear": act[0x50],
            "safe": act[0x51],
            "move_priority": struct.unpack_from("<I", act, 0x58)[0],
            "sticky": act[0x5C],
        }
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


def scan_heap_needles(b, base, limit_mb=512):
    """Light writable scan for watched VTs (not full 8GB every poll)."""
    needles = {name: struct.pack("<Q", base + vt) for vt, name in WATCH.items()}
    found = []
    scanned = 0
    for m in b.regions(writable=True, min_size=0x1000) if hasattr(b, "regions") else []:
        start, end = m["start"], m["end"]
        if base <= start < base + 0x4000000:
            continue
        pos = start
        while pos < end and scanned < (limit_mb << 20) and len(found) < 8:
            n = min(2 << 20, end - pos)
            try:
                data = b.read(pos, n)
            except Exception:
                pos += n
                scanned += n
                continue
            scanned += n
            for name, needle in needles.items():
                idx = 0
                while True:
                    j = data.find(needle, idx)
                    if j < 0:
                        break
                    addr = pos + j
                    # skip image
                    if not (base <= addr < base + 0x4000000):
                        try:
                            found.append(dump_cmd(b, base, addr, name))
                        except Exception:
                            found.append({"addr": hex(addr), "name": name, "partial": True})
                        if len(found) >= 8:
                            return found, scanned
                    idx = j + 8
            pos += n
    return found, scanned


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=30.0)
    ap.add_argument("--interval", type=float, default=0.05)
    ap.add_argument("--heap-every", type=int, default=40, help="heap scan every N polls (0=never)")
    ap.add_argument("--heap-mb", type=int, default=256)
    args = ap.parse_args()

    b = Backend(find_pid("hoi4.exe"))
    base = int(b.image_base)
    sess = u64(b, base + post_abi.G_SESSION)
    server = u64(b, sess + post_abi.CSession_SERVER)
    t0 = time.time()
    polls = 0
    captures = []
    last_counters = None
    # If Backend has no regions, skip heap path
    has_regions = hasattr(b, "regions")
    if not has_regions:
        # try Proc
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
        pending_h = try_u64(b, server + post_abi.CDummyServer_PENDING) or 0
        stage = try_u64(b, sess + post_abi.CSession_STAGE_ARRAY) or 0
        scount = u32(b, sess + post_abi.CSession_STAGE_COUNT)
        drain = u32(b, sess + post_abi.CSession_DRAIN_COUNTER)
        exec_c = u32(b, sess + post_abi.CSession_EXEC_COUNTER)
        seq = u32(b, server + 0xD0)
        last_counters = {"drain": drain, "exec": exec_c, "seq": seq, "stage_count": scount}

        for hit in walk_ptr_list(b, base, pending_h):
            if hit.get("name") in ("CMoveCommand", "CUnitMoveAction", "CStrategicRedeploymentCommand", "CCancelMovementCommand"):
                captures.append({"source": "pending", **hit})
        if stage and 0 < scount < 64:
            for i in range(scount):
                ptr = try_u64(b, stage + i * 8)
                if not ptr:
                    continue
                vt = try_u64(b, ptr)
                if vt is None:
                    continue
                name = WATCH.get(vt - base)
                if name in ("CMoveCommand", "CUnitMoveAction", "CStrategicRedeploymentCommand", "CCancelMovementCommand"):
                    try:
                        captures.append({"source": f"stage[{i}]", **dump_cmd(b, base, ptr, name)})
                    except Exception as e:
                        captures.append({"source": f"stage[{i}]", "addr": hex(ptr), "name": name, "error": str(e)})

        if args.heap_every and polls % args.heap_every == 0 and region_src is not None and has_regions:
            # lightweight: only when armed long; use Proc.regions if Backend lacks
            src = region_src
            # adapt: Backend may not have regions — use Proc
            try:
                from mem import Proc
                src = Proc(find_pid("hoi4.exe"))
                found, scanned = [], 0
                needles = {name: struct.pack("<Q", base + vt) for vt, name in WATCH.items()
                           if name.startswith("CMove") or name.startswith("CUnit") or name.startswith("CStrategic") or name.startswith("CCancel")}
                scanned = 0
                for m in src.regions(writable=True, min_size=0x1000):
                    start, end = m["start"], m["end"]
                    if base <= start < base + 0x4000000:
                        continue
                    pos = start
                    while pos < end and scanned < (args.heap_mb << 20) and len(found) < 4:
                        n = min(2 << 20, end - pos)
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
            break
        time.sleep(args.interval)

    army_move_hits = [c for c in captures if c.get("name") in (
        "CMoveCommand", "CUnitMoveAction", "CStrategicRedeploymentCommand",
        "CUnitStrategicMoveAction", "CCancelMovementCommand")]
    out = {
        "phase": "2bm_midflight_ready",
        "posting": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x; no input injection",
        "seconds": args.seconds,
        "interval": args.interval,
        "polls": polls,
        "last_counters": last_counters,
        "captures": captures,
        "caught_army_move": bool(army_move_hits),
        "note": "Armed RO watcher. Empty captures expected while paused with no user right-click.",
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({
        "polls": polls,
        "caught_army_move": out["caught_army_move"],
        "captures": len(captures),
        "last_counters": last_counters,
        "wrote": str(OUT),
    }, indent=2))


if __name__ == "__main__":
    main()
