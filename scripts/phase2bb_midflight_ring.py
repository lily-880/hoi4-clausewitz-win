"""Phase 2bb: RO mid-flight capture via ring/pending/stage + army action scan.

Never posts. Never writes. pause/1x only (never 5x).
Strategy:
  1) Tight-poll DummyServer ring slots + pending/stage/postexec
  2) Optionally tap Space once to unpause (caller decides)
  3) Scan player CArmy objects for embedded/referenced CUnitMoveAction / Strategic action VTs
     (these linger after Execute — mid-flight *equivalent* sample)
"""
from __future__ import annotations
import json, struct, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))
from process import Backend, find_pid  # noqa: E402

OV = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
OUT = ROOT / "reports" / "phase2bb_midflight.json"

VT = {
    0x2A2C790: "CMoveCommand",
    0x2A2C9B8: "CCancelMovement",
    0x2A2D818: "CStrategicRedeploymentCommand",
    0x29F3710: "CHourlyTickCommand",
    0x2A85468: "COrderExecuteCommand",
    0x2A27F28: "CChatCommand",
    0x2A1F648: "CUnitMoveAction",
    0x2A1F7E8: "CUnitStrategicMoveAction",
}


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def u8(b, a):
    return b.read(a, 1)[0]


def rtti(b, base, obj):
    try:
        vt = u64(b, obj)
        col = u64(b, vt - 8)
        td = u64(b, col + 0x10)
        return b.read(td + 0x10, 80).split(b"\0", 1)[0].decode("latin1", "replace")
    except Exception:
        return None


def classify(b, base, cmd):
    if not cmd or cmd < 0x10000:
        return None
    try:
        vt = u64(b, cmd) - base
    except Exception:
        return {"cmd": hex(cmd), "err": "read"}
    return {
        "cmd": hex(cmd),
        "vt": hex(vt),
        "name": VT.get(vt, "?"),
        "rtti": rtti(b, base, cmd),
        "word18": u32(b, cmd + 0x18) if True else None,
        "word1c": u32(b, cmd + 0x1C),
    }


def walk_slist(b, base, head, next_off=0x10, limit=32):
    """Pending/execlist appear as nodes: [cmd*][+0x10 next] (2ap convention)."""
    out, seen, node = [], set(), head
    while node and node not in seen and len(out) < limit:
        seen.add(node)
        try:
            cmd = u64(b, node)
            nxt = u64(b, node + next_off)
        except Exception:
            break
        c = classify(b, base, cmd)
        if c:
            c["node"] = hex(node)
            out.append(c)
        node = nxt
    return out


def read_ring(b, base, server):
    """Best-effort dump of DummyServer ring embed @+0xa0."""
    embed = server + 0xA0
    lock = u32(b, embed + 0x0)
    buf = u64(b, server + 0xB0)
    maskish = u64(b, server + 0xB8)
    head = u64(b, server + 0xC0)
    count = u64(b, server + 0xC8)
    seq = u32(b, server + 0xD0)
    slots = []
    # Try interpret buf as array of ptr-sized entries for count slots
    if buf and count and count < 64:
        for i in range(int(count)):
            try:
                # common lock-free ring: slot = buf + ((head-i) & mask) * stride
                # unknown stride — try 8 and 16
                for stride in (8, 16, 24):
                    p = u64(b, buf + i * stride)
                    c = classify(b, base, p)
                    if c and c.get("name") not in (None, "?"):
                        slots.append({"i": i, "stride": stride, **c})
                        break
            except Exception:
                pass
    return {
        "lock": lock,
        "buf": hex(buf),
        "maskish": hex(maskish),
        "head": hex(head),
        "count": count,
        "seq": seq,
        "decoded_slots": slots[:16],
    }


def scan_army_actions(b, base, country):
    """Scan each CArmy for pointers to MoveAction / StrategicMoveAction VTs."""
    begin = u64(b, country + OV["CO_ARMIES"])
    n = u32(b, country + OV["CO_ARMIES"] + 0xC)
    move_vt = base + 0x2A1F648
    strat_vt = base + 0x2A1F7E8
    move_cmd_vt = base + 0x2A2C790
    hits = []
    for i in range(n):
        army = u64(b, begin + i * 8)
        if not army:
            continue
        blob = b.read(army, 0x500)
        for off in range(0, 0x500, 8):
            p = struct.unpack_from("<Q", blob, off)[0]
            if p in (move_vt, strat_vt, move_cmd_vt):
                # vptr at army+off means embedded object
                hits.append({
                    "army_idx": i,
                    "army": hex(army),
                    "embed_off": hex(off),
                    "kind": "embed_vt",
                    "name": VT.get(p - base, "?"),
                    "handle": [u32(b, army + OV["CA_HANDLE"]), u32(b, army + OV["CA_HANDLE"] + 4)],
                    "province_id": u32(b, army + OV["CA_PROVINCE_ID"]),
                })
            elif 0x10000 < p < 0x7FFFFFFFFFFF:
                try:
                    vt = u64(b, p)
                except Exception:
                    continue
                if vt in (move_vt, strat_vt, move_cmd_vt):
                    # dump action fields
                    fields = {}
                    name = VT.get(vt - base, "?")
                    if name == "CUnitMoveAction":
                        fields = {
                            "unit_handle": [u32(b, p + 0x10), u32(b, p + 0x14)],
                            "province_size": u32(b, p + 0x24),
                            "path_size": u32(b, p + 0x3C),
                            "clear": u8(b, p + 0x50),
                            "safe": u8(b, p + 0x51),
                            "move_priority": u32(b, p + 0x58),
                        }
                        # first province if any
                        try:
                            arr = u64(b, p + 0x18)
                            if arr and fields["province_size"]:
                                fields["province0"] = u32(b, arr)
                        except Exception:
                            pass
                    elif name == "CUnitStrategicMoveAction":
                        fields = {
                            "army_handle": [u32(b, p + 0x10), u32(b, p + 0x14)],
                            "province": u32(b, p + 0x18),
                            "clear": u8(b, p + 0x1C),
                            "move_priority": u32(b, p + 0x20),
                        }
                    hits.append({
                        "army_idx": i,
                        "army": hex(army),
                        "ptr_off": hex(off),
                        "obj": hex(p),
                        "kind": "ptr",
                        "name": name,
                        "rtti": rtti(b, base, p),
                        "fields": fields,
                        "handle": [u32(b, army + OV["CA_HANDLE"]), u32(b, army + OV["CA_HANDLE"] + 4)],
                        "province_id": u32(b, army + OV["CA_PROVINCE_ID"]),
                    })
    return hits


def main():
    rounds = 600
    sleep_s = 0.005
    do_space = "--space" in sys.argv
    for a in sys.argv[1:]:
        if a.isdigit():
            rounds = int(a)

    b = Backend(find_pid("hoi4.exe"))
    base = int(b.image_base)
    idler = u64(b, base + OV["G_IDLER"])
    session = u64(b, u64(b, idler + 0x530) + 0x380)
    server = u64(b, session + 0x40)
    gs = u64(b, base + OV["G_GAMESTATE"])
    tag = u32(b, gs + OV["GS_PLAYER_TAG"])
    country = u64(b, u64(b, gs + OV["GS_COUNTRIES_BEGIN"]) + tag * 8)

    report = {
        "phase": "2bb",
        "posting": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "pid": b.pid,
        "space_tap": False,
        "captures": [],
        "seen_names": {},
        "army_actions_before": scan_army_actions(b, base, country),
    }

    if do_space:
        try:
            import ctypes
            user32 = ctypes.windll.user32
            # focus best-effort
            user32.keybd_event(0x20, 0, 0, 0)
            time.sleep(0.05)
            user32.keybd_event(0x20, 0, 2, 0)
            report["space_tap"] = True
            time.sleep(0.2)
        except Exception as e:
            report["space_error"] = str(e)

    t0 = time.time()
    max_ring = 0
    for i in range(rounds):
        ring = read_ring(b, base, server)
        max_ring = max(max_ring, int(ring["count"] or 0))
        pending_h = u64(b, server + 0x58)
        execlist_h = u64(b, server + 0x40)
        stage_data = u64(b, session + 0x48)
        stage_count = u32(b, session + 0x54)
        postexec_h = u64(b, session + 0xF8)

        batches = []
        if ring["decoded_slots"]:
            batches.append(("ring", ring["decoded_slots"]))
        if pending_h:
            batches.append(("pending", walk_slist(b, base, pending_h)))
        if execlist_h:
            batches.append(("execlist", walk_slist(b, base, execlist_h)))
        if stage_count:
            arr = []
            for j in range(min(stage_count, 32)):
                c = classify(b, base, u64(b, stage_data + j * 8))
                if c:
                    c["idx"] = j
                    arr.append(c)
            batches.append(("stage", arr))
        if postexec_h:
            batches.append(("postexec", walk_slist(b, base, postexec_h, limit=8)))

        for src, items in batches:
            for it in items:
                name = it.get("name") or "?"
                report["seen_names"][name] = report["seen_names"].get(name, 0) + 1
                if name in (
                    "CMoveCommand",
                    "CStrategicRedeploymentCommand",
                    "CCancelMovement",
                    "CUnitMoveAction",
                    "CUnitStrategicMoveAction",
                    "COrderExecuteCommand",
                ):
                    report["captures"].append({"src": src, "i": i, **it})
        time.sleep(sleep_s)

    report["elapsed_s"] = round(time.time() - t0, 2)
    report["max_ring_count"] = max_ring
    report["army_actions_after"] = scan_army_actions(b, base, country)
    report["final"] = {
        "drain": u32(b, session + 0x60),
        "exec": u32(b, session + 0x6C8),
        "seq": u32(b, server + 0xD0),
        "pending": hex(u64(b, server + 0x58)),
        "stage_count": u32(b, session + 0x54),
        "ring": read_ring(b, base, server),
    }
    report["caught_move_cmd"] = any(c.get("name") == "CMoveCommand" for c in report["captures"])
    report["caught_move_action"] = any(
        x.get("name") == "CUnitMoveAction"
        for x in (report["army_actions_before"] + report["army_actions_after"] + report["captures"])
    )
    report["caught_strategic_action"] = any(
        x.get("name") == "CUnitStrategicMoveAction"
        for x in (report["army_actions_before"] + report["army_actions_after"] + report["captures"])
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    slim = {k: report[k] for k in report if k not in ("captures",)}
    slim["captures_n"] = len(report["captures"])
    slim["captures_sample"] = report["captures"][:12]
    slim["army_actions_before_n"] = len(report["army_actions_before"])
    slim["army_actions_after_n"] = len(report["army_actions_after"])
    slim["army_actions_sample"] = (report["army_actions_after"] or report["army_actions_before"])[:8]
    print(json.dumps(slim, indent=2)[:12000])
    print("wrote", OUT)
    b.close()


if __name__ == "__main__":
    main()
