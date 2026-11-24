"""Read-only probe of a plan (COrderInstance): dump arrays inside the object so
we can see where the engine keeps the front path, assigned units and state.
Usage: probe_plan.py ARMY_ID [--save NAME] [--diff NAME]"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "calling"))
import live_trial as lt  # noqa: E402
import orbat  # noqa: E402

SIZE = 0x400
OUT = ROOT / "research" / "claude_live" / "plan_probe"


def find_group(r, gid):
    for tp in r.arr(r.s.country + 0x168, 64):
        for off in (0x80, 0x98):
            for g in r.arr(tp + off, 256):
                if orbat._ptr(g) and r.handle(g)[1] == gid:
                    return g
    return 0


def main(argv):
    gid = int(argv[0])
    s = lt.Session(check_sha=False)
    r = orbat.Reader(s)
    g = find_group(r, gid)
    out = {"group": hex(g), "instances": []}
    for off in (0x98, 0xB0, 0xC8):
        for ip in r.arr(g + off, 256):
            raw = s.p.read(ip, SIZE)
            arrays = {}
            for o in range(0, SIZE - 16, 8):
                data, cap, size = struct.unpack_from("<QII", raw, o)
                if orbat._ptr(data) and 0 < size <= cap <= 4096:
                    head = s.p.read(data, min(size, 16) * 8)
                    arrays[hex(o)] = {"size": size, "u32": list(struct.unpack("<" + "I" * min(size * 2, 32), head[:min(size * 2, 32) * 4])),
                                      "ptr_cls": [r.cls(struct.unpack_from("<Q", head, 8 * k)[0]) for k in range(min(size, 4))]}
            out["instances"].append({"slot": hex(off), "ptr": hex(ip), "cls": r.cls(ip), "raw": raw.hex(), "arrays": arrays})
    # group-level arrays too
    raw = s.p.read(g, 0x300)
    garr = {}
    for o in range(0, 0x300 - 16, 8):
        data, cap, size = struct.unpack_from("<QII", raw, o)
        if orbat._ptr(data) and 0 < size <= cap <= 4096:
            head = s.p.read(data, min(size, 4) * 8)
            garr[hex(o)] = {"size": size, "cls": [r.cls(struct.unpack_from("<Q", head, 8 * k)[0]) for k in range(min(size, 4))]}
    out["group_arrays"] = garr
    OUT.mkdir(parents=True, exist_ok=True)
    if "--save" in argv:
        (OUT / (argv[argv.index("--save") + 1] + ".json")).write_text(json.dumps(out), encoding="utf-8")
    print("group arrays", json.dumps(garr))
    for inst in out["instances"]:
        print(inst["slot"], inst["cls"], json.dumps(inst["arrays"])[:1500])
    if "--diff" in argv:
        old = json.loads((OUT / (argv[argv.index("--diff") + 1] + ".json")).read_text(encoding="utf-8"))
        for a, b in zip(old["instances"], out["instances"]):
            ra, rb = bytes.fromhex(a["raw"]), bytes.fromhex(b["raw"])
            ch = [hex(o) for o in range(0, SIZE, 4) if ra[o:o + 4] != rb[o:o + 4]]
            print("changed dwords", ch)


if __name__ == "__main__":
    main(sys.argv[1:])
