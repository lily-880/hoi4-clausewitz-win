"""Read-only army → Move/Strategic subject wiring (Windows HOI4 1.19.4).

Never posts. Builds field recipes from live CArmy handles/provinces.
"""
from __future__ import annotations
import struct
from typing import Any

try:
    from .handle import resolve_handle, HANDLE_TYPE_ARMY
    from .province import resolve_province
    from . import post_abi
except ImportError:
    from handle import resolve_handle, HANDLE_TYPE_ARMY
    from province import resolve_province
    import post_abi

CA_HANDLE = 0x18
CA_PROVINCE_ID = 0x28
CA_COUNTRY_TAG = 0x1E0
CP_ID = 0xA4


def _u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def _u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def iter_armies_by_index(backend, image_base: int, index_lo: int = 1000, index_hi: int = 1200,
                         country_tag: int | None = 15) -> list[dict[str, Any]]:
    """RO scan handle table for army indices; optional country filter (HAI=15)."""
    gs = _u64(backend, image_base + post_abi.G_GAMESTATE)
    out = []
    for ix in range(index_lo, index_hi):
        obj = resolve_handle(backend, HANDLE_TYPE_ARMY, ix, image_base)
        if not obj:
            continue
        h_ty = _u32(backend, obj + CA_HANDLE)
        h_ix = _u32(backend, obj + CA_HANDLE + 4)
        prov_id = _u32(backend, obj + CA_PROVINCE_ID)
        tag = _u32(backend, obj + CA_COUNTRY_TAG)
        if country_tag is not None and tag != country_tag:
            continue
        pref = resolve_province(backend, prov_id, image_base, gs)
        pid_a4 = _u32(backend, pref + CP_ID) if pref else None
        out.append({
            "army": obj,
            "handle": (h_ty, h_ix),
            "index": ix,
            "province_id": prov_id,
            "province": pref,
            "province_id_ok": pid_a4 == prov_id,
            "country_tag": tag,
            "handle_ok": h_ty == HANDLE_TYPE_ARMY and h_ix == ix,
        })
    return out


def move_action_recipe(army_row: dict[str, Any]) -> dict[str, Any]:
    """Fields for CUnitMoveAction embed (cmd+0x28) — documentation only, no alloc/post."""
    return {
        "unit_handle_off": 0x10,
        "unit_handle": list(army_row["handle"]),
        "province_arr_off": 0x18,
        "province_size_off": 0x24,
        "path_arr_off": 0x30,
        "path_size_off": 0x3C,
        "note": "path/province vectors must be valid game allocs; do NOT hand-wave WriteProcessMemory",
        "source_province_id": army_row["province_id"],
        "posting": "DISABLED",
    }


def strategic_action_recipe(army_row: dict[str, Any], dest_province_id: int) -> dict[str, Any]:
    return {
        "army_handle_off": 0x10,
        "army_handle": list(army_row["handle"]),
        "province_off": 0x18,
        "province": dest_province_id,
        "clear_off": 0x1C,
        "move_priority_off": 0x20,
        "posting": "DISABLED",
    }
