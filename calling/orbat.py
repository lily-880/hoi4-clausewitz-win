"""Order of battle: theatres, armies (COrdersGroup), army groups (CArmyGroup),
leaders, plans (COrderInstance) and the commands that change them.

Read side and command layouts come from the t192/t193/t198 live research on
1.19.5 (records in research/t19x_checkpoint.md):
  country +0x168  theatres (CTheatre*), handle {67, id}
    theatre +0x68  divisions (CArmy*), +0x80 armies, +0x98 army groups, +0xC8 theater groups
  COrdersGroup / CArmyGroup: handle {53, id} at +0x8; name msvc string +0x160;
    +0x50 members (interface ptr; CArmy = ptr - 0xB8), +0x88 leader (CArmyLeader*),
    +0x98 / +0xB0 / +0xC8 COrderInstance* arrays, +0x1B8 parent CArmyGroup* (army)
  CArmyGroup +0x230 child armies
  CArmy +0xC0 its COrdersGroup*
  country +0xFF0 -> +0x70 leaders (CArmyLeader*, handle {4713, id} at +0x8),
    leader +0x1048 assignment handle {53, group id}
  COrderInstance +0x244 id, +0x30 type, +0x70 path (u32 provinces), +0x210 scheduled
    members, +0x248 can_execute, +0x258 seed edge (NewRoot)

Commands (factory RVA, object size, vtable RVA, IsValid RVA):
  COrderGroupCommand     0x18D0140 0x60 0x2A84560 0x18DF050  create army
      +0x28 flag 0, +0x30 vector<handle{0x33,unit}>, +0x48 theatre {67,id}, +0x50/+0x58 0
  CArmyGroupCommand      0x18CF780 0x80 0x2A846E0 0x18DDFE0  create army group
      +0x28 theatre {67,id}, +0x30 vector<handle{53,army}>, +0x48 stride-24 array 0, +0x60 0
  CSetArmyLeaderCommand  0x18D0C10 0x40 0x2A85E20 0x18E0540  appoint
      +0x28 leader {4713,id}, +0x30 group {53,id}, +0x38 deploy_hq 0
  COrderNewRootCommand   0x18D0440 0x70 0x2A856A0 0x18DF5E0  new root plan (front line)
      +0x28 group {53,id}, +0x48/+0x4C seed edge (own province, enemy province)
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

T_UNIT, T_GROUP, T_THEATRE, T_LEADER = 0x33, 53, 67, 4713

CMD = {
    "group": dict(factory=0x18D0140, size=0x60, vt=0x2A84560, isvalid=0x18DF050),
    "army_group": dict(factory=0x18CF780, size=0x80, vt=0x2A846E0, isvalid=0x18DDFE0),
    "leader": dict(factory=0x18D0C10, size=0x40, vt=0x2A85E20, isvalid=0x18E0540),
    "new_root": dict(factory=0x18D0440, size=0x70, vt=0x2A856A0, isvalid=0x18DF5E0),
    # IsValid 0x18DF550: +0x28 group handle, +0x30 optional handle, +0x50 path (size +0x5C),
    # +0x68 parent plan id (must exist in the group's instance tree), +0x6D/+0x6E flags not both set
    "new_front": dict(factory=0x18D03B0, size=0x70, vt=0x2A853A0, isvalid=0x18DF550),
    # +0x28 group, +0x30 plan id, +0x34 execute (1) / stop (0), +0x35 flag
    "execute": dict(factory=0x18D00E0, size=0x38, vt=0x2A85D60, isvalid=0x18DEFB0),
}


def _ptr(x):
    return type(x) is int and 0x10000 < x < 0x7FFFFFFFFFFF


class Reader:
    def __init__(self, session):
        self.s = session
        self.p = session.p
        self._cls = {}

    def q(self, a):
        return struct.unpack("<Q", self.p.read(a, 8))[0]

    def u32(self, a):
        return struct.unpack("<I", self.p.read(a, 4))[0]

    def arr(self, a, bound=4096):
        data, cap, size = struct.unpack("<QII", self.p.read(a, 16))
        if not (0 <= size <= cap <= bound) or (size and not _ptr(data)):
            return []
        return list(struct.unpack("<" + "Q" * size, self.p.read(data, 8 * size))) if size else []

    def u32arr(self, a, bound=4096):
        data, cap, size = struct.unpack("<QII", self.p.read(a, 16))
        if not (0 <= size <= cap <= bound) or (size and not _ptr(data)):
            return []
        return list(struct.unpack("<" + "I" * size, self.p.read(data, 4 * size))) if size else []

    def cls(self, a):
        from gamestate import _rtti_name_from_vtable
        if not _ptr(a):
            return None
        try:
            vt = self.q(a) - self.p.base
        except OSError:
            return None
        if not 0 < vt < 0x4000000:
            return None
        if vt not in self._cls:
            try:
                self._cls[vt] = _rtti_name_from_vtable(self.s.pe, vt)
            except Exception:
                self._cls[vt] = None
        return self._cls[vt]

    def string(self, a):
        blob = self.p.read(a, 32)
        n, cap = struct.unpack_from("<QQ", blob, 16)
        if not 0 <= n <= 1024 or cap < n:
            return None
        raw = blob[:n] if cap <= 15 else self.p.read(struct.unpack_from("<Q", blob)[0], n)
        return raw.decode("utf-8", "replace")

    def handle(self, a):
        return struct.unpack("<II", self.p.read(a + 0x8, 8))

    def instance(self, ip, depth=0):
        row = {"plan_id": self.u32(ip + 0x244), "type": self.u32(ip + 0x30),
               "path": self.u32arr(ip + 0x70), "can_execute": self.p.read(ip + 0x248, 1)[0],
               "seed": list(struct.unpack("<II", self.p.read(ip + 0x258, 8))),
               "members": len(self.arr(ip + 0x210)), "class": self.cls(ip),
               "flag_299": self.p.read(ip + 0x299, 1)[0]}
        if depth < 4:  # +0x2D0 children (front segments / offensive lines), +0x2B8 parents
            row["children"] = [self.instance(c, depth + 1) for c in self.arr(ip + 0x2D0, 256) if _ptr(c)]
        return row

    def group(self, gp):
        t, gid = self.handle(gp)
        lp = self.q(gp + 0x88)
        members = []
        for mp in self.arr(gp + 0x50):
            ap = mp - 0xB8
            if self.cls(ap) == ".?AVCArmy@@":
                members.append(self.u32(ap + 0x1C))
        plans = []
        for off in (0x98, 0xB0, 0xC8):
            for ip in self.arr(gp + off, 256):
                if _ptr(ip):
                    plans.append(dict(self.instance(ip), slot=hex(off)))
        row = {"id": gid, "handle_type": t, "class": self.cls(gp), "name": self.string(gp + 0x160),
               "leader_id": self.handle(lp)[1] if _ptr(lp) else None,
               "unit_ids": members, "plans": plans}
        if row["class"] == ".?AVCArmyGroup@@":
            row["army_ids"] = [self.handle(x)[1] for x in self.arr(gp + 0x230, 256) if _ptr(x)]
        else:
            parent = self.q(gp + 0x1B8)
            row["army_group_id"] = self.handle(parent)[1] if _ptr(parent) else None
        return row

    def theatres(self):
        out = []
        for tp in self.arr(self.s.country + 0x168, 64):
            if not _ptr(tp):
                continue
            t, tid = self.handle(tp)
            out.append({"id": tid, "handle_type": t, "name": self.string(tp + 0x18),
                        "unit_ids": [self.u32(a + 0x1C) for a in self.arr(tp + 0x68) if _ptr(a)],
                        "armies": [self.group(g) for g in self.arr(tp + 0x80, 256) if _ptr(g)],
                        "army_groups": [self.group(g) for g in self.arr(tp + 0x98, 256) if _ptr(g)],
                        "theater_groups": len(self.arr(tp + 0xC8, 256))})
        return out

    def leaders(self):
        cc = self.q(self.s.country + 0xFF0)
        out = []
        for lp in self.arr(cc + 0x70, 1024):
            if not _ptr(lp):
                continue
            t, lid = self.handle(lp)
            at = struct.unpack("<II", self.p.read(lp + 0x1048, 8))
            out.append({"leader_id": lid, "handle_type": t, "key": self.string(lp + 0x20),
                        "assigned_group": at[1] if at[0] == T_GROUP else None})
        return out


def post(kind: str, fields: list[tuple[int, bytes]], vectors: list[tuple[int, list[tuple[int, int]]]] = (),
         live: bool = True) -> dict:
    """Build one command with the game's own factory, fill fields, IsValid, then
    one gated Post. Buffers come from the game's ucrt malloc and are never freed
    (freeing posted buffers crashed the game before). Requires the game paused."""
    import os
    import time
    sys.path.insert(0, str(HERE.parent / "scripts"))
    import live_trial as lt
    import move_order as mo
    import post_abi
    from config import allow_post

    spec = CMD[kind]
    s = lt.Session(check_sha=False)
    clk = s.clock()
    rep = {"kind": kind, "clock": clk}
    if clk.get("pause") != 1:
        return dict(rep, ok=False, stop="NOT_PAUSED")
    pid, base = s.pid, s.p.base
    made = mo._remote(pid, base + spec["factory"], wait_ms=5000)
    cmd = made.get("rax") or 0
    if made.get("wait") != 0 or not _ptr(cmd):
        return dict(rep, ok=False, stop="FACTORY_FAIL")
    vt = struct.unpack("<Q", s.p.read(cmd, 8))[0] - base
    if vt != spec["vt"]:
        return dict(rep, ok=False, stop="FACTORY_VT_MISMATCH", vt=hex(vt))
    for off, handles in vectors:
        buf = mo._game_malloc(pid, max(16, 8 * len(handles)))
        mo._write(pid, buf, b"".join(struct.pack("<II", a, b_) for a, b_ in handles))
        mo._write(pid, cmd + off, struct.pack("<QII", buf, len(handles), len(handles)))
    for off, data in fields:
        mo._write(pid, cmd + off, data)
    valid = mo._remote(pid, base + spec["isvalid"], {"rcx": cmd}, wait_ms=5000)
    ok_valid = valid.get("wait") == 0 and (valid.get("rax") or 0) & 0xFF == 1
    rep["isvalid"] = ok_valid
    if not ok_valid or not live:
        return dict(rep, ok=False if not ok_valid else True, stop=None if ok_valid else "ISVALID_FALSE", posted=False)
    if s.clock().get("pause") != 1:
        return dict(rep, ok=False, stop="UNPAUSED_BEFORE_POST")
    os.environ["CLAUSEWITZ_ALLOW_POST"] = "1"
    lt.MARKER.write_text("claude orbat: one gated Post on the user's test save.\n", encoding="utf-8")
    try:
        if not allow_post():
            return dict(rep, ok=False, stop="GATE_CLOSED")
        sess = struct.unpack("<Q", s.p.read(base + post_abi.G_SESSION, 8))[0]
        posted = mo._remote(pid, base + post_abi.FN_CMD_QUEUE_POST, {"rcx": sess, "rdx": cmd, "r8": 1}, wait_ms=8000)
    finally:
        os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
        if lt.MARKER.exists():
            lt.MARKER.unlink()
    time.sleep(0.5)
    rep["posted"] = posted.get("wait") == 0 and (posted.get("rax") or 0) & 0xFF == 1
    rep["ok"] = rep["posted"]
    return rep


def create_army(theatre_id: int, unit_ids: list[int], live=True) -> dict:
    return post("group", [(0x28, bytes(8)), (0x48, struct.pack("<II", T_THEATRE, theatre_id)), (0x50, bytes(16))],
                [(0x30, [(T_UNIT, u) for u in unit_ids])], live)


def create_army_group(theatre_id: int, army_ids: list[int], live=True) -> dict:
    return post("army_group", [(0x28, struct.pack("<II", T_THEATRE, theatre_id)), (0x48, bytes(16)),
                               (0x60, bytes(8))],
                [(0x30, [(T_GROUP, a) for a in army_ids])], live)


def appoint(leader_id: int, group_id: int, live=True) -> dict:
    return post("leader", [(0x28, struct.pack("<II", T_LEADER, leader_id)),
                           (0x30, struct.pack("<II", T_GROUP, group_id)), (0x38, struct.pack("<I", 0))], [], live)


def front_line(group_id: int, front_id: int, unit_ids: list[int], live=True) -> dict:
    """Front line along a border CFront {66,id}. +0x50=1 (copied to plan +0x260) makes the
    engine lay the line along the border; without it the plan has no path and is not drawn
    (compared with a line the user drew in the UI, 2026-11-24)."""
    return post("new_root", [(0x28, struct.pack("<II", T_GROUP, group_id)),
                             (0x48, struct.pack("<II", 66, front_id)), (0x50, struct.pack("<I", 1))],
                [(0x30, [(T_UNIT, u) for u in unit_ids])], live)


def offensive_line(group_id: int, front_plan_id: int, path: list[int], unit_ids: list[int], live=True) -> dict:
    """Offensive line (arrow) under a front line: path = enemy provinces, from one touching the
    front to the objective. Becomes a child plan (+0x2D0) with +0x299=1."""
    return new_front(group_id, front_plan_id, path, unit_ids=unit_ids, live=live)


def execute(group_id: int, plan_id: int, on: bool = True, flag_35: int = 0, live=True) -> dict:
    return post("execute", [(0x28, struct.pack("<II", T_GROUP, group_id)),
                            (0x30, struct.pack("<IBB", plan_id, 1 if on else 0, flag_35))], [], live)


def new_front(group_id: int, parent_plan_id: int, path: list[int], unit_ids: list[int] = (),
              flag_6c: int = 0, flag_6d: int = 0, flag_6e: int = 0, live=True) -> dict:
    """Child plan under a root. Path: u32 province ids (with flag_6e=0 they must belong to the
    root front's enemy area, i.e. enemy provinces). +0x38: unit handles {0x33,id}."""
    sys.path.insert(0, str(HERE.parent / "scripts"))
    import move_order as mo
    import live_trial as lt
    s = lt.Session(check_sha=False)
    buf = mo._game_malloc(s.pid, max(16, 4 * len(path)))
    mo._write(s.pid, buf, struct.pack("<" + "I" * len(path), *path))
    return post("new_front", [(0x28, struct.pack("<II", T_GROUP, group_id)), (0x30, bytes(8)),
                              (0x50, struct.pack("<QII", buf, len(path), len(path))),
                              (0x68, struct.pack("<I", parent_plan_id)),
                              (0x6C, bytes([flag_6c, flag_6d, flag_6e, 0]))],
                [(0x38, [(T_UNIT, u) for u in unit_ids])] if unit_ids else [], live)


FRONTS_FILE = HERE / "tables" / "army_fronts.json"


def front_handles(session) -> dict:
    """Border fronts of the first theatre by opposing country tag: {tag: [front ids]}."""
    r = Reader(session)
    out = {}
    for tp in r.arr(session.country + 0x168, 64)[:1]:
        for fp in r.arr(tp + 0x50, 256):
            d, c, n = struct.unpack("<QII", session.p.read(fp + 0x38, 16))
            if n:
                out.setdefault(session.tag(session.u32(d)), []).append(r.handle(fp)[1])
    return out


def ensure_fronts(live=True) -> list[dict]:
    """Plans anchored on a CFront are dropped by the engine whenever the border changes
    (observed 2026-11-24). Re-create the root plan of every army listed in
    tables/army_fronts.json ({"army_id": "ENEMY_TAG"}) that currently has none."""
    import json
    try:
        want = json.loads(FRONTS_FILE.read_text(encoding="utf-8")).get("armies", {})
    except (OSError, ValueError):
        return []
    sys.path.insert(0, str(HERE.parent / "scripts"))
    import live_trial as lt
    s = lt.Session(check_sha=False)
    snap = snapshot(s)
    fronts = front_handles(s)
    done = []
    for t in snap["theatres"]:
        for a in t["armies"]:
            tag = want.get(str(a["id"]))
            has_line = any(p["path"] and p["members"] for p in a["plans"])
            if not tag or has_line or not a["unit_ids"] or not fronts.get(tag):
                continue
            res = front_line(a["id"], fronts[tag][0], a["unit_ids"], live)
            done.append({"army_id": a["id"], "enemy": tag, "front_id": fronts[tag][0], "ok": res.get("ok")})
    return done


def snapshot(session=None) -> dict:
    if session is None:
        sys.path.insert(0, str(HERE.parent / "scripts"))
        import live_trial as lt
        session = lt.Session(check_sha=False)
    r = Reader(session)
    return {"theatres": r.theatres(), "leaders": r.leaders()}


if __name__ == "__main__":
    import json
    snap = snapshot()
    for t in snap["theatres"]:
        print("theatre", t["id"], t["handle_type"], t["name"], "units", len(t["unit_ids"]),
              "armies", len(t["armies"]), "army_groups", len(t["army_groups"]), "theater_groups", t["theater_groups"])
    print("leaders", len(snap["leaders"]), "assigned", [l for l in snap["leaders"] if l["assigned_group"]][:5])
    print(json.dumps(snap["leaders"][:3], ensure_ascii=True))
