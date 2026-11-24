"""Read-only: dump every plan of every army (root plans in the army's arrays and
their children under +0x2D0, recursively) with raw bytes, to compare a plan the
user drew in the game UI with one built by our commands.

  python -I scripts/dump_plans.py --save NAME     write research/claude_live/plan_dumps/NAME.json
  python -I scripts/dump_plans.py --diff A B      compare two plans (army:plan_id) inside dumps
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "calling"))
import live_trial as lt  # noqa: E402
import orbat  # noqa: E402

OUT = ROOT / "research" / "claude_live" / "plan_dumps"
SIZE = 0x3C8  # COrderInstance allocation size (0xC41BB0)


def dump_instance(r, ip, depth=0):
    raw = r.p.read(ip, SIZE)
    arrays = {}
    for o in range(0, SIZE - 16, 8):
        d, c, n = struct.unpack_from("<QII", raw, o)
        if orbat._ptr(d) and 0 < n <= c <= 5000:
            try:
                first = struct.unpack("<Q", r.p.read(d, 8))[0]
                cls = r.cls(first) if orbat._ptr(first) else None
                vals = list(struct.unpack("<" + "I" * min(n, 64), r.p.read(d, 4 * min(n, 64))))
            except OSError:
                continue
            arrays[hex(o)] = {"size": n, "cls": cls, "u32": vals}
    row = dict(r.instance(ip, depth=9), ptr=hex(ip), raw=raw.hex(), arrays=arrays)
    row["children"] = [dump_instance(r, c, depth + 1) for c in r.arr(ip + 0x2D0, 256) if orbat._ptr(c)] if depth < 4 else []
    return row


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--save")
    ap.add_argument("--diff", nargs=2, metavar=("DUMP:ARMY:PLAN", "DUMP:ARMY:PLAN"))
    a = ap.parse_args(argv)
    if a.diff:
        def load(spec):
            name, army, plan = spec.split(":")
            data = json.loads((OUT / f"{name}.json").read_text(encoding="utf-8"))
            def walk(rows):
                for x in rows:
                    yield x
                    yield from walk(x["children"])
            for g in data["armies"]:
                if str(g["id"]) == army:
                    for x in walk(g["plans"]):
                        if str(x["plan_id"]) == plan:
                            return x
            raise SystemExit(f"not found: {spec}")
        p, q = load(a.diff[0]), load(a.diff[1])
        rp, rq = bytes.fromhex(p["raw"]), bytes.fromhex(q["raw"])
        print("type", p["type"], q["type"], "| path", len(p["path"]), len(q["path"]),
              "| children", len(p["children"]), len(q["children"]))
        print("arrays A", {k: (v["size"], v["cls"]) for k, v in p["arrays"].items()})
        print("arrays B", {k: (v["size"], v["cls"]) for k, v in q["arrays"].items()})
        for o in range(0x28, SIZE, 4):
            x, y = rp[o:o + 4], rq[o:o + 4]
            if x != y:
                print(f"  +{o:#05x}  {x.hex()}  {y.hex()}")
        return
    s = lt.Session(check_sha=False)
    r = orbat.Reader(s)
    out = {"clock": s.clock(), "armies": []}
    for tp in r.arr(s.country + 0x168, 64):
        for off in (0x80, 0x98):
            for g in r.arr(tp + off, 256):
                if not orbat._ptr(g):
                    continue
                plans = []
                for slot in (0x98, 0xB0, 0xC8):
                    plans += [dump_instance(r, ip) for ip in r.arr(g + slot, 256) if orbat._ptr(ip)]
                out["armies"].append({"id": r.handle(g)[1], "class": r.cls(g), "plans": plans})
    for g in out["armies"]:
        def brief(x, ind="    "):
            print(f"{ind}plan {x['plan_id']} type {x['type']} path {len(x['path'])} seed {x['seed']} "
                  f"members {x['members']} exec {x['can_execute']} f299 {x['flag_299']} children {len(x['children'])}")
            for c in x["children"]:
                brief(c, ind + "  ")
        print("army", g["id"], g["class"])
        for x in g["plans"]:
            brief(x)
    if a.save:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / f"{a.save}.json").write_text(json.dumps(out), encoding="utf-8")
        print("saved", OUT / f"{a.save}.json")


if __name__ == "__main__":
    main()
