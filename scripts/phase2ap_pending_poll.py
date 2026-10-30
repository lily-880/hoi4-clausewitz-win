#!/usr/bin/env python3
"""Phase 2ap — rapid READ-ONLY poll of pending/staging/execlist for mid-flight cmds.

Avoids full-heap. Prefer 1x. Never posts. Never 5x.
"""
from __future__ import annotations
import json, os, struct, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "calling"))

VT_NAMES = {
    0x2A2C790: "CMoveCommand",
    0x2A2C9B8: "CCancelMovementCommand",
    0x2A2D818: "CStrategicRedeploymentCommand",
    0x2A85468: "COrderExecuteCommand",
    0x2A27F28: "CChatCommand",
    0x2A5F448: "CStartGameCommand",
    0x2A1F648: "CUnitMoveAction",
    0x2A83ED8: "CArmyGroupCommand",
    0x2A84498: "COrderAssignCommand",
    0x2A843E0: "COrderDeleteCommand",
    0x2A83D68: "COrderGroupCommand",
    0x2A84C80: "COrderNewFallbackCommand",
    0x2A84B10: "COrderNewFrontCommand",
    0x2A84DF0: "COrderNewRootCommand",
    0x2A84550: "COrderUnassignCommand",
    0x2A85520: "CSetArmyLeaderCommand",
}


def classify(p, base, cmd):
    if not cmd:
        return None
    try:
        vt = p.u64(cmd) - base
    except OSError:
        return {"cmd": hex(cmd), "err": "read"}
    return {
        "cmd": hex(cmd),
        "vt": hex(vt),
        "name": VT_NAMES.get(vt, "?"),
        "plus8": p.u8(cmd + 8),
        "plus_0x1a": p.u8(cmd + 0x1A),
        "type_id_field_hyp": p.u32(cmd + 0xC) if False else None,
    }


def walk_list(p, head, limit=32):
    out = []
    seen = set()
    node = head
    while node and node not in seen and len(out) < limit:
        seen.add(node)
        try:
            cmd = p.u64(node)
            nxt = p.u64(node + 0x10)
        except OSError:
            break
        out.append({"node": hex(node), **(classify(p, p.base, cmd) or {})})
        node = nxt
    return out


def walk_array(p, data, count, limit=64):
    out = []
    if not data or count <= 0:
        return out
    n = min(int(count), limit)
    for i in range(n):
        try:
            cmd = p.u64(data + i * 8)
        except OSError:
            break
        c = classify(p, p.base, cmd)
        if c:
            c["idx"] = i
            out.append(c)
    return out


def main():
    from mem import Proc, find_pid

    ap_rounds = 400
    sleep_s = 0.02
    if len(sys.argv) > 1:
        ap_rounds = int(sys.argv[1])
    pid = find_pid("hoi4.exe")
    if not pid:
        print("no hoi4", file=sys.stderr)
        return 2
    p = Proc(pid)
    ov = json.load(open(os.path.join(ROOT, "calling", "offsets_verified.json"), encoding="utf-8"))
    idler = p.u64(p.base + ov["G_IDLER"])
    session = p.u64(p.u64(idler + 0x530) + 0x380)
    server = p.u64(session + 0x40)

    seen_names = {}
    captures = []
    t0 = time.time()
    max_exec = 0
    for i in range(ap_rounds):
        pending = p.u64(server + 0x58)
        execlist = p.u64(server + 0x40)
        stage_data = p.u64(session + 0x48)
        stage_count = p.u32(session + 0x54)
        postexec = p.u64(session + 0xF8)
        exec_n = p.u32(session + 0x6C8)
        max_exec = max(max_exec, exec_n)
        batches = []
        if pending:
            batches.append(("pending", walk_list(p, pending)))
        if execlist:
            batches.append(("execlist", walk_list(p, execlist)))
        if stage_count:
            batches.append(("stage", walk_array(p, stage_data, stage_count)))
        if postexec:
            batches.append(("postexec", walk_list(p, postexec, limit=8)))
        for src, items in batches:
            for it in items:
                name = it.get("name") or "?"
                seen_names[name] = seen_names.get(name, 0) + 1
                if name not in ("?", "CStartGameCommand") and len(captures) < 40:
                    captures.append({"src": src, "i": i, **it})
                elif name == "CMoveCommand" or name == "CStrategicRedeploymentCommand":
                    captures.append({"src": src, "i": i, **it})
        time.sleep(sleep_s)

    out = {
        "phase": "2ap-pending-poll",
        "posting": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "pid": p.pid,
        "rounds": ap_rounds,
        "elapsed_s": round(time.time() - t0, 1),
        "seen_names": seen_names,
        "captures_sample": captures[:40],
        "caught_move": any(c.get("name") == "CMoveCommand" for c in captures),
        "caught_strategic": any(c.get("name") == "CStrategicRedeploymentCommand" for c in captures),
        "final": {
            "drain": p.u32(session + 0x60),
            "exec": p.u32(session + 0x6C8),
            "seq": p.u32(server + 0xD0),
            "max_exec_seen": max_exec,
            "pending": hex(p.u64(server + 0x58)),
            "execlist": hex(p.u64(server + 0x40)),
            "stage_count": p.u32(session + 0x54),
        },
    }
    path = os.path.join(ROOT, "research", "re-dumps", "phase2ap_pending_poll.json")
    json.dump(out, open(path, "w", encoding="utf-8"), indent=2)
    print("wrote", path)
    print(json.dumps({k: out[k] for k in ("seen_names", "caught_move", "caught_strategic", "final", "elapsed_s")}, indent=2))
    print("captures", len(captures))
    for c in captures[:12]:
        print(" ", c.get("src"), c.get("name"), c.get("cmd"))
    p.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
