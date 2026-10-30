"""Read-only CHandle resolve (Windows HOI4 1.19.4). Never posts commands."""
from __future__ import annotations
import struct
from .config import allow_post

FN_HANDLE_RESOLVE = 0x2284800
FN_HANDLE_HASH_LOOKUP = 0x2282810
HANDLE_TYPE_TABLE = 0x34FFC00
HANDLE_HASH_MUL = 0x49631A45
HANDLE_TYPE_ARMY = 0x33


def _sx32(v: int) -> int:
    v &= 0xFFFFFFFF
    return v - 0x100000000 if v >= 0x80000000 else v


def resolve_handle(backend, typ: int, index: int, image_base: int | None = None) -> int | None:
    """Return object pointer for (type, index), or None. Read-only."""
    if allow_post():  # noqa — gate exists; resolve itself is RO
        pass
    base = image_base if image_base is not None else backend.image_base

    def u64(a):
        return struct.unpack("<Q", backend.read(a, 8))[0]

    def u32(a):
        return struct.unpack("<I", backend.read(a, 4))[0]

    def u8(a):
        return backend.read(a, 1)[0]

    if typ < 0x64:
        reg = u64(base + HANDLE_TYPE_TABLE + typ * 8)
    else:
        return None  # large-type path not mirrored here yet
    if not reg:
        return None
    buckets = u64(reg + 8)
    mask = u32(reg + 0x14)
    key = ((typ & 0xFFFFFFFF) << 32) + (index & 0xFFFFFFFF)
    prod = (key * HANDLE_HASH_MUL) & 0xFFFFFFFFFFFFFFFF
    h = (_sx32(prod >> 32) ^ _sx32(prod)) & mask
    rax = buckets + h * 24
    cl = 1
    if u8(rax + 4) < cl:
        return None
    while True:
        if u32(rax + 0xC) == index and u32(rax + 8) == typ:
            return u64(rax + 0x10) - 0x10
        rax += 0x18
        cl += 1
        if cl > u8(rax + 4) or cl > 128:
            return None
