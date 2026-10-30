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

def cancel_movement_recipe(army_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Fields for CCancelMovementCommand — units vector of army handles. RO docs only."""
    handles = [list(r["handle"]) for r in army_rows]
    return {
        "units_data_off": 0x28,  # CANCEL.fields.units_data
        "units_count_off": 0x34,
        "sticky_off": 0x40,
        "unit_handles": handles,
        "count": len(handles),
        "note": "vector must be game-allocated CHandle[count]; do NOT hand-wave WPM",
        "posting": "DISABLED",
    }


def strategic_redeploy_recipe(army_row: dict[str, Any], dest_province_id: int,
                              clear: int = 0, move_priority: int = 0) -> dict[str, Any]:
    """Alias with explicit clear/priority — same layout as strategic_action_recipe."""
    r = strategic_action_recipe(army_row, dest_province_id)
    r["clear"] = clear
    r["move_priority"] = move_priority
    return r


def isvalid_path_notes() -> dict[str, Any]:
    """Execute/IsValid path docs (calling/cmd_layout.ISVALID_PATHS). Never calls into game."""
    try:
        from . import cmd_layout
    except ImportError:
        import cmd_layout
    return {
        "wrap": hex(cmd_layout.ISVALID_PATHS["wrap"]),
        "posting": "DISABLED",
        "move": cmd_layout.ISVALID_PATHS["CMoveCommand"],
        "strategic": cmd_layout.ISVALID_PATHS["CStrategicRedeploymentCommand"],
        "cancel": cmd_layout.ISVALID_PATHS["CCancelMovementCommand"],
        "order_execute": cmd_layout.ISVALID_PATHS["COrderExecuteCommand"],
        "support_attack": cmd_layout.ISVALID_PATHS.get("CSupportAttackCommand"),
        "replace_fallback": cmd_layout.ISVALID_PATHS.get("COrderReplaceFallbackCommands"),
        "army_group_fallback": cmd_layout.ISVALID_PATHS.get("CSetSelectedArmyGroupFallback"),
        "land_army_focus": getattr(cmd_layout, "LAND_ARMY_FOCUS", {}).get("priority"),
        "cancel_abort": getattr(cmd_layout, "LAND_ARMY_FOCUS", {}).get("cancel_abort_group"),
        "frontline": getattr(cmd_layout, "LAND_ARMY_FOCUS", {}).get("frontline_group"),
        "theater": getattr(cmd_layout, "LAND_ARMY_FOCUS", {}).get("theater_group"),
        "land_exe_proofs": list(getattr(cmd_layout, "LAND_EXE_PROOFS", {}).get("commands", {})),
        "order_group": getattr(cmd_layout, "LAND_ARMY_FOCUS", {}).get("order_group_group"),
        "note": "IsValid wrap 0x22d8ea0; midflight Move still required; land focus 2bv",
    }



def support_attack_recipe(army_row: dict[str, Any], target_province_id: int) -> dict[str, Any]:
    """Fields for CSupportAttackCommand — RO docs only, no alloc/post."""
    return {
        "unit_or_attacker_handle_off": 0x28,
        "unit_or_attacker_handle": list(army_row["handle"]),
        "target_province_off": 0x30,
        "target_province": target_province_id,
        "serialize_tokens": {"handle": 0x28A3, "province": 0x286D},
        "source_province_id": army_row["province_id"],
        "note": "IsValid validates handle@+0x28; do NOT hand-wave WPM",
        "posting": "DISABLED",
    }


def army_group_fallback_recipe(army_group_handle: list[int] | tuple[int, int],
                               fallback_flag: int = 1) -> dict[str, Any]:
    """CSetSelectedArmyGroupFallback subject fields — RO docs only."""
    return {
        "army_group_off": 0x28,
        "army_group": list(army_group_handle),
        "fallback_flag_off": 0x30,
        "fallback_flag": fallback_flag,
        "note": "Battle-plan army-group fallback; do NOT hand-wave WPM",
        "posting": "DISABLED",
    }


def cancel_running_away_recipe(army_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """CCancelRunningAwayCommand — units vector of army handles. RO docs only."""
    handles = [list(r["handle"]) for r in army_rows]
    return {
        "units_vec_off": 0x28,
        "unit_handles": handles,
        "count": len(handles),
        "note": "vector must be game-allocated; do NOT hand-wave WPM",
        "posting": "DISABLED",
    }


def withdraw_army_hq_recipe(hq_handle: list[int] | tuple[int, int]) -> dict[str, Any]:
    """CWithdrawArmyHqCommand — RO docs only."""
    return {
        "hq_handle_off": 0x28,
        "hq_handle": list(hq_handle),
        "note": "Withdraw HQ; do NOT hand-wave WPM",
        "posting": "DISABLED",
    }


def fallback_order_recipe(fallback_flag_or_id: int = 1) -> dict[str, Any]:
    """COrderNewFallbackCommand / COrderReplaceFallbackCommands — RO docs only."""
    return {
        "fallback_flag_or_id_off": 0x54,
        "fallback_flag_or_id": fallback_flag_or_id,
        "note": "IsValid checks@+0x54; battle-plan subject wiring TBD; posting DISABLED",
        "posting": "DISABLED",
    }


def mass_cancel_movement_recipe(army_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """CMassCancelMovementCommand — units vec@+0x28 count@+0x34. RO docs only."""
    handles = [list(r["handle"]) for r in army_rows]
    return {
        "units_vec_off": 0x28,
        "units_count_off": 0x34,
        "unit_handles": handles,
        "count": len(handles),
        "note": "Execute iterates count@+0x34; vector must be game-allocated; posting DISABLED",
        "posting": "DISABLED",
    }


def order_execute_recipe(order_index: int = 0, execute_order: int = 1, all_flag: int = 0) -> dict[str, Any]:
    """COrderExecuteCommand — battle-plan execute. RO docs only."""
    return {
        "order_index_off": 0x30,
        "order_index": order_index,
        "execute_order_off": 0x34,
        "execute_order": execute_order,
        "all_off": 0x35,
        "all": all_flag,
        "note": "Subject pair@+0x28 required by IsValid; posting DISABLED",
        "posting": "DISABLED",
    }


def new_front_recipe(unit_handles: list[list[int]] | None = None, blitz: int = 0, withdraw: int = 0) -> dict[str, Any]:
    """COrderNewFrontCommand field sketch — RO docs only."""
    return {
        "sub_group_off": 0x30,
        "units_data_off": 0x38,
        "units_count_off": 0x44,
        "path_off": 0x50,
        "attach_off": 0x68,
        "split_from_off": 0x6C,
        "blitz_off": 0x6D,
        "blitz": blitz,
        "withdraw_off": 0x6E,
        "withdraw": withdraw,
        "unit_handles": unit_handles or [],
        "note": "Front geometry/path must be game-allocated; posting DISABLED",
        "posting": "DISABLED",
    }


def set_path_recipe(order_id_a: int, order_id_b: int = 0, order_id_c: int = 0) -> dict[str, Any]:
    """COrderSetPathCommand — RO docs only."""
    return {
        "order_id_a_off": 0x28,
        "order_id_a": order_id_a,
        "order_id_b_off": 0x2C,
        "order_id_b": order_id_b,
        "order_id_c_off": 0x30,
        "order_id_c": order_id_c,
        "path_payload_off": 0x38,
        "note": "Path payload must be game-allocated; posting DISABLED",
        "posting": "DISABLED",
    }


def set_collapse_recipe(order_handle: list[int] | tuple[int, int], collapse_flag: int = 1) -> dict[str, Any]:
    """COrderSetCollapseCommand — RO docs only."""
    h = list(order_handle)
    return {
        "order_handle_lo_off": 0x28,
        "order_handle_lo": h[0] if h else 0,
        "order_handle_hi_off": 0x2C,
        "order_handle_hi": h[1] if len(h) > 1 else 0,
        "collapse_flag_or_id_off": 0x30,
        "collapse_flag_or_id": collapse_flag,
        "note": "Front/order collapse; posting DISABLED",
        "posting": "DISABLED",
    }


def assign_theater_group_recipe(subject_handle: list[int] | tuple[int, int],
                                theater_or_group: int) -> dict[str, Any]:
    """CAssignToTheaterGroupCommand — RO docs only."""
    return {
        "subject_off": 0x28,
        "subject_handle": list(subject_handle),
        "theater_or_group_off": 0x3C,
        "theater_or_group": theater_or_group,
        "note": "Theater assign; posting DISABLED",
        "posting": "DISABLED",
    }


def set_order_group_execution_type_recipe(order_group_handle: list[int] | tuple[int, int],
                                         execution_type: int = 1) -> dict[str, Any]:
    """CSetOrderGroupExecutionTypeCommand — offensive-line/plan execution type. RO only."""
    return {
        "order_group_off": 0x28,
        "order_group": list(order_group_handle),
        "execution_type_off": 0x30,
        "execution_type": execution_type,
        "note": "Sets order-group execution type (balanced/rush/etc.); posting DISABLED",
        "posting": "DISABLED",
    }


def set_order_group_cohesion_recipe(order_group_handle: list[int] | tuple[int, int],
                                    cohesion_type: int = 0) -> dict[str, Any]:
    """CSetOrderGroupCohesionTypeCommand — RO only."""
    return {
        "order_group_off": 0x28,
        "order_group": list(order_group_handle),
        "cohesion_type_off": 0x30,
        "cohesion_type": cohesion_type,
        "posting": "DISABLED",
    }


def assign_to_army_group_recipe(army_handle: list[int] | tuple[int, int],
                                group_handle: list[int] | tuple[int, int]) -> dict[str, Any]:
    """CAssignToArmyGroupCommand — RO only."""
    return {
        "army_or_units_off": 0x28,
        "army_or_units": list(army_handle),
        "group_off": 0x30,
        "group": list(group_handle),
        "note": "Assign army to army group; posting DISABLED",
        "posting": "DISABLED",
    }


def order_assign_recipe(order_subject: list[int] | tuple[int, int] | None = None) -> dict[str, Any]:
    """COrderAssignCommand sketch — RO only."""
    return {
        "subject_or_vec_off": 0x28,
        "subject": list(order_subject) if order_subject else [],
        "units_or_path_off": 0x34,
        "note": "Assign units to order; vector/path game-allocated; posting DISABLED",
        "posting": "DISABLED",
    }


def collapse_conveyor_recipe(subject_handle: list[int] | tuple[int, int]) -> dict[str, Any]:
    """CCollapseConveyorCommand — RO only."""
    return {
        "subject_handle_off": 0x28,
        "subject_handle": list(subject_handle),
        "posting": "DISABLED",
    }
