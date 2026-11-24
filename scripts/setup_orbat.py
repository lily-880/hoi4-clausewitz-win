"""Build an order of battle on the test save and put armies on border fronts.

Plan (dry run prints it; --live posts it, game must be paused):
  * divisions not yet in an army are grouped by land region and, inside the home
    region, ordered by land distance from a southern anchor province, then cut into
    armies of at most ARMY_MAX divisions;
  * armies facing the primary enemy go on that enemy's CFront; armies are grouped
    into army groups of at most AG_MAX armies;
  * generals / field marshals are taken from GENERALS / MARSHALS in order (the
    engine's IsValid decides who may command what).
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "calling"))
import live_trial as lt  # noqa: E402
import orbat  # noqa: E402

ARMY_MAX = 24
AG_MAX = 3
GENERALS = [349, 331, 355, 339, 348, 341, 343, 345, 336, 338]   # Küchler, Kluge, Blaskowitz, Guderian, Hoth, Kleist, Weichs, Reinhardt, Paulus, Manstein
MARSHALS = [342, 330, 344]                                       # Bock, Rundstedt, Leeb


def fronts_by_enemy(s, r):
    tp = r.arr(s.country + 0x168, 64)[0]
    out = {}
    for fp in r.arr(tp + 0x50, 256):
        d, c, n = struct.unpack("<QII", s.p.read(fp + 0x38, 16))
        if n:
            enemy = s.u32(d)
            out.setdefault(s.tag(enemy), []).append(r.handle(fp)[1])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--enemy", default="POL")
    ap.add_argument("--anchor", type=int, default=6590, help="southern anchor province for ordering")
    ap.add_argument("--army-groups", action="store_true")
    a = ap.parse_args(argv)
    import live_input
    cap = live_input.capture()
    ext = cap["commander_ext"]
    units = cap["observation"]["world"]["own_units"]
    s = lt.Session(check_sha=False)
    r = orbat.Reader(s)
    snap = orbat.snapshot(s)
    in_army = {u for t in snap["theatres"] for g in t["armies"] for u in g["unit_ids"]}
    used_leaders = {l["leader_id"] for l in snap["leaders"] if l["assigned_group"]}
    free = [u for u in units if u["unit_id"] not in in_army]
    reg = ext["topology"]["region_of_province"]
    home = max(ext["topology"]["regions"], key=lambda x: x["provinces"])["region"]
    # land distance from the anchor over our + allied + enemy-held land (bounded BFS)
    dist = {a.anchor: 0}
    dq = deque([a.anchor])
    want = {u["province_id"] for u in free}
    while dq and not want <= set(dist) and len(dist) < 4000:
        x = dq.popleft()
        for n in s.land_neighbors(x).get("neighbors") or []:
            if n not in dist:
                dist[n] = dist[x] + 1
                dq.append(n)
    groups: dict = {}
    for u in free:
        rg = reg.get(str(u["province_id"]), reg.get(u["province_id"]))
        groups.setdefault("home" if rg == home or rg is None else f"region{rg}", []).append(u)
    plan = []
    for key, us in sorted(groups.items()):
        us.sort(key=lambda u: (dist.get(u["province_id"], 999), u["unit_id"]))
        for i in range(0, len(us), ARMY_MAX):
            chunk = us[i:i + ARMY_MAX]
            plan.append({"key": key, "unit_ids": [u["unit_id"] for u in chunk],
                         "names": [u.get("name") for u in chunk[:3]]})
    fronts = fronts_by_enemy(s, r)
    front_ids = fronts.get(a.enemy, [])
    print("free divisions", len(free), "armies planned", len(plan), "fronts vs", a.enemy, front_ids)
    for p in plan:
        print(" ", p["key"], len(p["unit_ids"]), [n.encode("ascii", "replace").decode() for n in p["names"] if n])
    if not a.live:
        return
    generals = [g for g in GENERALS if g not in used_leaders]
    marshals = [m for m in MARSHALS if m not in used_leaders]
    made = []
    for p in plan:
        before = {g["id"] for t in orbat.snapshot(s)["theatres"] for g in t["armies"]}
        res = orbat.create_army(1, p["unit_ids"])
        after = [g for t in orbat.snapshot(s)["theatres"] for g in t["armies"] if g["id"] not in before]
        if not res.get("ok") or not after:
            print("create army failed", res)
            continue
        gid = after[0]["id"]
        while generals:
            lid = generals.pop(0)
            if orbat.appoint(lid, gid).get("ok"):
                break
        for fid in front_ids[:1]:
            orbat.post("new_root", [(0x28, struct.pack("<II", 53, gid)), (0x48, struct.pack("<II", 66, fid))],
                       [(0x30, [(0x33, u) for u in p["unit_ids"]])])
        made.append(gid)
        print("army", gid, "units", len(p["unit_ids"]))
    # army groups over the new armies
    for i in range(0, len(made) if a.army_groups else 0, AG_MAX):
        chunk = made[i:i + AG_MAX]
        before = {g["id"] for t in orbat.snapshot(s)["theatres"] for g in t["army_groups"]}
        orbat.create_army_group(1, chunk)
        after = [g for t in orbat.snapshot(s)["theatres"] for g in t["army_groups"] if g["id"] not in before]
        if after and marshals:
            orbat.appoint(marshals.pop(0), after[0]["id"])
        print("army group", after[0]["id"] if after else None, chunk)
    snap = orbat.snapshot(s)
    out = ROOT / "research" / "claude_live" / "orbat_snapshot.json"
    out.write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved", out)


if __name__ == "__main__":
    main()
