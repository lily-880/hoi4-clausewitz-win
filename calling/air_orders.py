"""Air wings for the commander (2026-11-26, user: the army commander becomes an army + air
commander; the air side is simple — attach the existing wings to armies and give them a mission).

Memory (1.19.5, found on exam-9 saves):
  CAirWing (vtable 0x29F7748), handle type 69 (0x45) at +0x18 (type,id);
    +0x38 CAirWingPool*; pool +0x20 CSubUnitDefinition* (name string at +0x8.., type flags +0x5A8);
    pool +0x40 CStrategicAir*; strategic air +0x90 (u16) = owner country index;
    +0x7C planes in the wing; +0xA0 mission bitmask.
  Mission bits (tallied over every AI wing): 0x1 air superiority (fighters), 0x2 close air support
    (CAS, tactical bombers), 0x8 strategic bombing, 0x800 training.
  Attachable to an army (native 0xFE6CC0): not in training, and type flags & 0x20A000 == 0.
  An army (orders group, resolved from its handle by handle.resolve_handle) lists attached wing
    objects at +0x80, count +0x8C (the game's resolver returns that address +0x10: +0x70/+0x7C).

Commands (factory / size / vtable / IsValid):
  CAttachAirWingToArmyCommand 0x19CF530 / 0x48 / 0x2A97728 / 0x19D3920:
    +0x28 array of wing handles, +0x40 army handle (T_GROUP, id).
  CStratAirSetMissionCommand  0x19CFF40 / 0x48 / 0x2A96BE8 / 0x19D4B30:
    +0x28 array of wing handles, +0x40 u32 mission bit, +0x44 u8 enable (UI posts 1).
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import orbat  # noqa: E402

T_WING = 69
WING_VT = 0x29F7748
MISSIONS = {"air_superiority": 0x1, "cas": 0x2, "strategic_bombing": 0x8, "training": 0x800}
NOT_ATTACHABLE_TYPE_FLAGS = 0x20A000
SKIP_TYPES = ("transport_plane",)  # attachable by the engine, but no use over the front

orbat.CMD.setdefault("air_attach", dict(factory=0x19CF530, size=0x48, vt=0x2A97728, isvalid=0x19D3920))
orbat.CMD.setdefault("air_mission", dict(factory=0x19CFF40, size=0x48, vt=0x2A96BE8, isvalid=0x19D4B30))


def _session():
    sys.path.insert(0, str(HERE.parent / "scripts"))
    import live_trial as lt
    return lt.Session(check_sha=False)


def own_wings(s=None, max_id: int = 4000) -> list[dict]:
    """The player's air wings: id, type, planes, missions, whether it can support an army, and the
    army it is attached to (None if free)."""
    from handle import resolve_handle
    s = s or _session()
    p = s.p

    class A:
        read = staticmethod(p.read)
        image_base = p.base

    def q(a):
        return struct.unpack("<Q", p.read(a, 8))[0]

    def i32(a):
        return struct.unpack("<i", p.read(a, 4))[0]

    def name_of(sud):
        for off in (0x8, 0x10, 0x18, 0x20, 0x28):
            try:
                raw = p.read(sud + off, 32)
                size, cap = struct.unpack_from("<QQ", raw, 16)
                if not 2 < size < 64:
                    continue
                txt = (p.read(struct.unpack_from("<Q", raw, 0)[0], size) if cap >= 16 else raw[:size]).decode("ascii")
                if txt.replace("_", "").isalnum():
                    return txt
            except Exception:
                continue
        return None

    me = s.player.get("player_index")
    vt = p.base + WING_VT
    # which army each wing is attached to
    attached = {}
    try:
        for th in orbat.snapshot(s)["theatres"]:
            for a in th["armies"]:
                obj = resolve_handle(A(), orbat.T_GROUP, a["id"], p.base)
                if not obj:
                    continue
                # the game's resolver returns this +0x10; its +0x70/+0x7C list is our +0x80/+0x8C
                n, data = i32(obj + 0x8C), q(obj + 0x80)
                for j in range(max(0, min(n, 500))):
                    attached[q(data + 8 * j)] = a["id"]
    except Exception:
        pass
    out = []
    for wid in range(max_id):
        o = resolve_handle(A(), T_WING, wid, p.base)
        if not o:
            continue
        obj = o if q(o) == vt else o - 0x10
        if q(obj) != vt:
            continue
        pool = q(obj + 0x38)
        if struct.unpack("<H", p.read(q(pool + 0x40) + 0x90, 2))[0] != me:
            continue
        sud = q(pool + 0x20)
        kind = name_of(sud)
        mask = i32(obj + 0xA0)
        flags = i32(sud + 0x5A8)
        out.append({"wing_id": wid, "type": kind, "planes": i32(obj + 0x7C),
                    "missions": [k for k, b in MISSIONS.items() if mask & b],
                    "can_support_army": not (mask & MISSIONS["training"]) and not (flags & NOT_ATTACHABLE_TYPE_FLAGS)
                    and kind not in SKIP_TYPES,
                    "army_id": attached.get(obj)})
    return out


def attach(army_id: int, wing_ids: list[int], live=True) -> dict:
    """CAttachAirWingToArmyCommand: these wings support this army (fly over its area)."""
    return orbat.post("air_attach", [(0x40, struct.pack("<II", orbat.T_GROUP, army_id))],
                      [(0x28, [(T_WING, w) for w in wing_ids])], live)


def set_mission(wing_ids: list[int], mission: str, on: bool = True, live=True) -> dict:
    """CStratAirSetMissionCommand for these wings."""
    return orbat.post("air_mission", [(0x40, struct.pack("<I", MISSIONS[mission])),
                                      (0x44, bytes([1 if on else 0, 0, 0]))],
                      [(0x28, [(T_WING, w) for w in wing_ids])], live)
