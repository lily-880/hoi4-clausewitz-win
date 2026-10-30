"""Read-only province resolve (Windows HOI4 1.19.4)."""
from __future__ import annotations
import struct

G_GAMESTATE = 0x33DD6B0
GS_PROVINCES_BEGIN = 0x2B0
GS_PROVINCES_SIZE = 0x2BC
FN_PROVINCE_RESOLVE = 0x1E07F0


def resolve_province(backend, province_id: int, image_base: int | None = None, gs: int | None = None) -> int | None:
    """Return CProvince* for id, or None. Mirrors FN_PROVINCE_RESOLVE."""
    base = image_base if image_base is not None else backend.image_base

    def u64(a):
        return struct.unpack("<Q", backend.read(a, 8))[0]

    def u32(a):
        return struct.unpack("<I", backend.read(a, 4))[0]

    if gs is None:
        gs = u64(base + G_GAMESTATE)
    if province_id < 1:
        return None
    n = u32(gs + GS_PROVINCES_SIZE)
    if province_id >= n:
        return None
    arr = u64(gs + GS_PROVINCES_BEGIN)
    return u64(arr + province_id * 8)
