"""Leader traits for the commander (2026-11-27: the user's 27-day demonstration gave the army-group
commander offensive field-marshal traits and an army commander fortress_buster).

Memory (1.19.5): global at RVA 0x33DD518 -> CUnitLeaderDatabase; +0x70 array of all land-leader
traits (CUnitLeaderTrait*, 131 in vanilla 1.19.5), +0x88 the same without the 10 field-marshal
traits; a trait's name std::string at +0x10, +0xE8 (i32) == 1 for assignable traits.
A leader (orbat leaders list, CArmyLeader) holds its traits at +0xDC8 (pointer array), count +0xDD4.

Command CLearnTraitCommand: factory 0x18CFB40 / size 0x38 / vtable 0x2A86720 / IsValid 0x18DE450;
+0x28 leader handle (T_LEADER, id), +0x30 CUnitLeaderTrait*. IsValid tells whether the leader can
learn the trait now (rank, prerequisites, free trait points), so the candidate list is asked of the
game itself instead of re-implementing those rules.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import orbat  # noqa: E402

G_LEADER_DB = 0x33DD518
orbat.CMD.setdefault("learn_trait", dict(factory=0x18CFB40, size=0x38, vt=0x2A86720, isvalid=0x18DE450))


def _session():
    sys.path.insert(0, str(HERE.parent / "scripts"))
    import live_trial as lt
    return lt.Session(check_sha=False)


def _reader(s):
    p = s.p

    def q(a):
        return struct.unpack("<Q", p.read(a, 8))[0]

    def i32(a):
        return struct.unpack("<i", p.read(a, 4))[0]

    def sstr(a):
        raw = p.read(a, 32)
        size, cap = struct.unpack_from("<QQ", raw, 16)
        if not 0 < size < 80:
            return None
        b = p.read(struct.unpack_from("<Q", raw, 0)[0], size) if cap >= 16 else raw[:size]
        return b.decode("ascii", "replace")
    return q, i32, sstr


def trait_table(s=None) -> dict[str, dict]:
    """name -> {"ptr", "assignable", "field_marshal_only"}"""
    s = s or _session()
    q, i32, sstr = _reader(s)
    db = q(s.p.base + G_LEADER_DB)
    allp = [q(q(db + 0x70) + 8 * j) for j in range(max(0, min(i32(db + 0x7C), 2000)))]
    general = {q(q(db + 0x88) + 8 * j) for j in range(max(0, min(i32(db + 0x94), 2000)))}
    out = {}
    for t in allp:
        name = sstr(t + 0x10)
        if name:
            out[name] = {"ptr": t, "assignable": i32(t + 0xE8) == 1, "field_marshal_only": t not in general}
    return out


def leader_traits(s=None) -> dict[int, list[str]]:
    s = s or _session()
    q, i32, sstr = _reader(s)
    r = orbat.Reader(s)
    out = {}
    for lp in r.arr(q(s.country + 0xFF0) + 0x70, 1024):
        if not lp:
            continue
        _, lid = r.handle(lp)
        n, arr = i32(lp + 0xDD4), q(lp + 0xDC8)
        out[lid] = [sstr(q(arr + 8 * j) + 0x10) for j in range(max(0, min(n, 40)))]
    return out


def can_learn(leader_id: int, trait_ptr: int) -> bool:
    """The game's own IsValid for CLearnTraitCommand (built, checked, never posted)."""
    r = orbat.post("learn_trait", [(0x28, struct.pack("<II", orbat.T_LEADER, leader_id)),
                                   (0x30, struct.pack("<Q", trait_ptr))], [], live=False)
    return bool(r.get("isvalid"))


def learnable(leader_ids: list[int], s=None) -> dict[int, list[str]]:
    """For each leader: the assignable traits the game would let it learn right now."""
    s = s or _session()
    table = trait_table(s)
    has = leader_traits(s)
    out = {}
    for lid in leader_ids:
        cand = [n for n, t in table.items() if t["assignable"] and n not in (has.get(lid) or [])]
        out[lid] = [n for n in cand if can_learn(lid, table[n]["ptr"])]
    return out


def learn(leader_id: int, trait: str, live=True) -> dict:
    table = trait_table()
    if trait not in table:
        return {"ok": False, "stop": "UNKNOWN_TRAIT"}
    return orbat.post("learn_trait", [(0x28, struct.pack("<II", orbat.T_LEADER, leader_id)),
                                      (0x30, struct.pack("<Q", table[trait]["ptr"]))], [], live)


CACHE_FILE = HERE / "tables" / "learnable_traits.json"
CACHE_DAYS = 7


def commanders_view(leader_ids: list[int], game_hour: int | None, s=None) -> list[dict]:
    """For the leaders who command a formation: current traits and the assignable traits the game
    would let each learn now. The learnable list costs ~13 s per leader (one IsValid per candidate),
    so it is cached per leader and refreshed after CACHE_DAYS game days or when its traits change."""
    import json
    s = s or _session()
    has = leader_traits(s)
    try:
        cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    table = None
    out = []
    for lid in leader_ids:
        cur = has.get(lid) or []
        row = cache.get(str(lid))
        stale = (row is None or row.get("traits") != cur or game_hour is None or row.get("hour") is None
                 or game_hour < row["hour"] or game_hour - row["hour"] > CACHE_DAYS * 24)
        if stale:
            table = table or trait_table(s)
            cand = [n for n, t in table.items() if t["assignable"] and n not in cur]
            row = {"traits": cur, "hour": game_hour,
                   "learnable": [n for n in cand if can_learn(lid, table[n]["ptr"])]}
            cache[str(lid)] = row
        out.append({"leader_id": lid, "traits": cur, "learnable_traits": row["learnable"]})
    try:
        CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    return out


def forget(leader_id: int) -> None:
    """Drop a leader's cached list (after it learned a trait)."""
    import json
    try:
        cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        cache.pop(str(leader_id), None)
        CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    except (OSError, ValueError):
        pass
