"""Read-only probe: the player's order of battle (armies / army groups / leaders).

CArmy (division) +0xC0 -> COrdersGroup (army, 集团军) per earlier research (t192);
COrdersGroup +0x88 leader, +0x1B8 parent CArmyGroup. Offsets come from 1.19.4
notes, so every pointer is checked by RTTI class name before use.
"""
from __future__ import annotations

import json
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "calling"))

import live_trial as lt  # noqa: E402
from gamestate import _rtti_name_from_vtable  # noqa: E402


def main():
    s = lt.Session(check_sha=False)
    p = s.p

    def ptr(x):
        return 0x10000 < x < 0x7FFFFFFFFFFF

    cache = {}

    def cls(a):
        try:
            if not ptr(a):
                return None
            vt = s.q(a) - p.base
            if not 0 < vt < 0x4000000:
                return None
            if vt not in cache:
                cache[vt] = _rtti_name_from_vtable(s.pe, vt)
            return cache[vt]
        except Exception:
            return None

    data, cap, n = struct.unpack("<QII", p.read(s.country + 0x290, 16))
    armies = struct.unpack("<" + "Q" * n, p.read(data, 8 * n))
    print("divisions", n)
    off_hits = Counter()
    groups = defaultdict(list)
    for a in armies:
        uid = s.u32(a + 0x1C)
        # find candidate COrdersGroup pointers in the first 0x690 bytes
        raw = p.read(a, 0x690)
        for off in range(0, 0x690, 8):
            v = struct.unpack_from("<Q", raw, off)[0]
            if ptr(v):
                c = cls(v)
                if c and ("Order" in c or "ArmyGroup" in c or "Leader" in c):
                    off_hits[(off, c)] += 1
        og = s.q(a + 0xC0)
        groups[og].append(uid)
    for (off, c), k in sorted(off_hits.items()):
        print(f"  CArmy+{off:#x} -> {c}: {k}")
    print("groups by +0xC0:", {hex(k): len(v) for k, v in groups.items()})
    for og, members in groups.items():
        print(hex(og), cls(og), len(members))


if __name__ == "__main__":
    main()
