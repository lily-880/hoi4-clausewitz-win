#!/usr/bin/env python3
"""Phase 2ap light midflight — single-pass heap scan for key army cmd vptrs only.

READ-ONLY. Prefer game at 1x. Never 5x. Never posts.
"""
from __future__ import annotations
import json, os, struct, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "calling"))

TARGETS = {
    "CMoveCommand": 0x2A2C790,
    "CCancelMovementCommand": 0x2A2C9B8,
    "CStrategicRedeploymentCommand": 0x2A2D818,
    "COrderExecuteCommand": 0x2A85468,
    "CChatCommand": 0x2A27F28,
    "CUnitMoveAction": 0x2A1F648,
    "CStartGameCommand": 0x2A5F448,
}


def main():
    from mem import Proc, find_pid

    pid = find_pid("hoi4.exe")
    if not pid:
        print("no hoi4", file=sys.stderr)
        return 2
    p = Proc(pid)
    needles = {k: struct.pack("<Q", p.base + vt) for k, vt in TARGETS.items()}
    counts = {k: 0 for k in needles}
    samples = {k: [] for k in needles}
    scanned = 0
    t0 = time.time()
    chunk = 8 << 20
    for m in p.regions(writable=True, min_size=0x1000):
        start, end = m["start"], m["end"]
        if p.base <= start < p.base + p.image_size:
            continue
        pos = start
        while pos < end:
            n = min(chunk, end - pos)
            data = p.try_read(pos, n)
            scanned += n
            if data:
                for k, needle in needles.items():
                    off = 0
                    while True:
                        i = data.find(needle, off)
                        if i < 0:
                            break
                        if i % 8 == 0:
                            counts[k] += 1
                            if len(samples[k]) < 4:
                                samples[k].append(hex(pos + i))
                        off = i + 8
            pos += n
    # session counters
    ov = json.load(open(os.path.join(ROOT, "calling", "offsets_verified.json"), encoding="utf-8"))
    idler = p.u64(p.base + ov["G_IDLER"])
    session = p.u64(p.u64(idler + 0x530) + 0x380)
    server = p.u64(session + 0x40)
    out = {
        "phase": "2ap-midflight-light",
        "posting": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "pid": p.pid,
        "elapsed_s": round(time.time() - t0, 1),
        "scanned_mb": scanned >> 20,
        "counts": {k: v for k, v in counts.items() if v},
        "samples": {k: v for k, v in samples.items() if v},
        "session": {
            "state": p.u32(session + 0x30),
            "drain": p.u32(session + 0x60),
            "exec": p.u32(session + 0x6c8),
            "seq": p.u32(server + 0xD0),
            "pending": hex(p.u64(server + 0x58)),
            "execlist": hex(p.u64(server + 0x40)),
        },
        "caught_move": counts.get("CMoveCommand", 0) > 0,
        "caught_strategic": counts.get("CStrategicRedeploymentCommand", 0) > 0,
    }
    path = os.path.join(ROOT, "research", "re-dumps", "phase2ap_midflight_light.json")
    json.dump(out, open(path, "w", encoding="utf-8"), indent=2)
    print("wrote", path)
    print(json.dumps(out, indent=2))
    p.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
