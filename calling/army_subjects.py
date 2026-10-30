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
        "note": "IsValid wrap 0x22d8ea0; midflight Move still required; land focus 2cd",
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


def delete_order_group_recipe(order_group_handle: list[int] | tuple[int, int]) -> dict[str, Any]:
    """CDeleteOrderGroupCommand — RO only."""
    return {
        "order_group_off": 0x28,
        "order_group": list(order_group_handle),
        "posting": "DISABLED",
    }


def order_delete_recipe(order_index: int = 0) -> dict[str, Any]:
    """COrderDeleteCommand — RO only."""
    return {
        "order_index_off": 0x30,
        "order_index": order_index,
        "posting": "DISABLED",
    }


def order_delete_all_recipe(subject_handle: list[int] | tuple[int, int] | None = None) -> dict[str, Any]:
    """COrderDeleteAllCommand — RO only."""
    return {
        "subject_or_vec_off": 0x28,
        "subject": list(subject_handle) if subject_handle else [],
        "posting": "DISABLED",
    }


def auto_merge_orders_recipe(subject_handle: list[int] | tuple[int, int] | None = None,
                             id_b: int = 0, id_c: int = 0) -> dict[str, Any]:
    """CAutoMergeOrdersCommand — RO only."""
    return {
        "subject_or_vec_off": 0x28,
        "subject": list(subject_handle) if subject_handle else [],
        "id_or_b_off": 0x2c,
        "id_or_b": id_b,
        "id_or_c_off": 0x30,
        "id_or_c": id_c,
        "posting": "DISABLED",
    }


def set_order_group_icon_recipe(order_group_handle: list[int] | tuple[int, int],
                                icon_or_color: int = 0) -> dict[str, Any]:
    """CSetOrderGroupIconAndColorCommand — RO only."""
    return {
        "order_group_off": 0x28,
        "order_group": list(order_group_handle),
        "icon_or_color_off": 0x30,
        "icon_or_color": icon_or_color,
        "posting": "DISABLED",
    }


def set_army_leader_recipe(leader_handle: list[int] | tuple[int, int],
                           deploy_army_hq: int = 0) -> dict[str, Any]:
    """CSetArmyLeaderCommand — RO only."""
    return {
        "leader_off": 0x28,
        "leader": list(leader_handle),
        "deploy_army_hq_off": 0x38,
        "deploy_army_hq": deploy_army_hq,
        "posting": "DISABLED",
    }


def set_army_template_recipe(army_handle: list[int] | tuple[int, int],
                             template_id: int = 0) -> dict[str, Any]:
    """CSetArmyTemplateCommand — RO only."""
    return {
        "army_off": 0x28,
        "army": list(army_handle),
        "template_off": 0x30,
        "template": template_id,
        "posting": "DISABLED",
    }


def railway_gun_manual_order_recipe(subject_handle: list[int] | tuple[int, int],
                                    order_or_prov: int = 0) -> dict[str, Any]:
    """CRailwayGunManualOrderCommand — RO only."""
    return {
        "subject_off": 0x28,
        "subject": list(subject_handle),
        "extra_30_off": 0x30,
        "order_or_prov_off": 0x40,
        "order_or_prov": order_or_prov,
        "posting": "DISABLED",
    }


def deploy_army_hq_recipe(subject_handle: list[int] | tuple[int, int],
                          id_or_b: int = 0) -> dict[str, Any]:
    """CDeployArmyHqCommand — RO only."""
    return {
        "subject_or_vec_off": 0x28,
        "subject": list(subject_handle),
        "id_or_b_off": 0x2c,
        "id_or_b": id_or_b,
        "posting": "DISABLED",
    }


def mass_move_recipe(army_rows: list[dict], dest_province: int) -> dict[str, Any]:
    """CMassMoveCommand — RO only."""
    handles = [list(r["handle"]) for r in army_rows]
    return {
        "units_vec_off": 0x28,
        "units": handles,
        "units_count_off": 0x34,
        "units_count": len(handles),
        "dest_off": 0x38,
        "dest_province": dest_province,
        "posting": "DISABLED",
    }


def toggle_strategic_deployment_recipe(subject_handle: list[int] | tuple[int, int]) -> dict[str, Any]:
    """CToggleStrategicDeploymentCommand — RO only."""
    return {
        "subject_or_vec_off": 0x28,
        "subject": list(subject_handle),
        "flag_30_off": 0x30,
        "posting": "DISABLED",
    }


def order_edit_root_recipe(subject_handle: list[int] | tuple[int, int] | None = None) -> dict[str, Any]:
    """COrderEditRootCommand — RO only."""
    return {
        "subject_or_vec_off": 0x28,
        "subject": list(subject_handle) if subject_handle else [],
        "posting": "DISABLED",
    }


def order_merge_roots_recipe(subject_handle: list[int] | tuple[int, int] | None = None) -> dict[str, Any]:
    """COrderMergeRootsCommand — RO only."""
    return {
        "subject_or_vec_off": 0x28,
        "subject": list(subject_handle) if subject_handle else [],
        "posting": "DISABLED",
    }


def order_block_sections_recipe(subject_handle: list[int] | tuple[int, int] | None = None) -> dict[str, Any]:
    """COrderBlockSectionsCommand — RO only."""
    return {
        "subject_or_vec_off": 0x28,
        "subject": list(subject_handle) if subject_handle else [],
        "posting": "DISABLED",
    }


def order_set_invasion_source_recipe(subject_handle: list[int] | tuple[int, int],
                                     source_id: int = 0) -> dict[str, Any]:
    """COrderSetInvasionSourceCommand — RO only."""
    return {
        "subject_or_vec_off": 0x28,
        "subject": list(subject_handle),
        "id_or_b_off": 0x30,
        "source_id": source_id,
        "posting": "DISABLED",
    }


def create_conveyor_recipe(subject_handle: list[int] | tuple[int, int] | None = None) -> dict[str, Any]:
    """CCreateConveyorCommand — RO only (encirclement-adjacent)."""
    return {
        "subject_or_vec_off": 0x28,
        "subject": list(subject_handle) if subject_handle else [],
        "posting": "DISABLED",
    }


def deploy_conveyor_recipe(subject_handle: list[int] | tuple[int, int] | None = None) -> dict[str, Any]:
    """CDeployConveyorCommand — RO only."""
    return {
        "subject_or_vec_off": 0x28,
        "subject": list(subject_handle) if subject_handle else [],
        "posting": "DISABLED",
    }


def set_orders_link_recipe(subject_handle: list[int] | tuple[int, int],
                           link_id: int = 0) -> dict[str, Any]:
    """CSetOrdersLinkCommand — RO only."""
    return {
        "subject_or_vec_off": 0x28,
        "subject": list(subject_handle),
        "link_id_off": 0x30,
        "link_id": link_id,
        "posting": "DISABLED",
    }


def set_army_leader_preferred_tactic_recipe(leader_or_army: list[int] | tuple[int, int],
                                            tactic: int = 0) -> dict[str, Any]:
    """CSetArmyLeaderPreferredTacticCommand — RO only."""
    return {
        "leader_or_army_off": 0x28,
        "leader_or_army": list(leader_or_army),
        "tactic_off": 0x30,
        "tactic": tactic,
        "posting": "DISABLED",
    }


def garrison_template_recipe(country_or_state: int, template_id: int = 0,
                             which: str = "country") -> dict[str, Any]:
    """CSetCountry/Main/StateGarrisonTemplateCommand sketch — RO only."""
    return {
        "which": which,
        "country_or_state_off": 0x28,
        "country_or_state": country_or_state,
        "template_off": 0x30,
        "template": template_id,
        "posting": "DISABLED",
    }


def insert_front_recipe(subject_handle: list[int] | tuple[int, int] | None = None,
                        id_b: int = 0, id_c: int = 0) -> dict[str, Any]:
    """COrderInsertFrontCommand — RO only."""
    return {
        "subject_or_vec_off": 0x28,
        "subject": list(subject_handle) if subject_handle else [],
        "id_or_b_off": 0x2c,
        "id_or_b": id_b,
        "id_or_c_off": 0x30,
        "id_or_c": id_c,
        "posting": "DISABLED",
    }


def reshape_front_recipe(subject_handle: list[int] | tuple[int, int] | None = None) -> dict[str, Any]:
    """COrderReshapeCommand — RO only."""
    return {
        "subject_or_vec_off": 0x28,
        "subject": list(subject_handle) if subject_handle else [],
        "posting": "DISABLED",
    }


def connect_front_recipe(subject_handle: list[int] | tuple[int, int] | None = None) -> dict[str, Any]:
    """COrderConnectCommand — RO only."""
    return {
        "subject_or_vec_off": 0x28,
        "subject": list(subject_handle) if subject_handle else [],
        "posting": "DISABLED",
    }


def add_complete_plan_recipe(plan_subject: list[int] | tuple[int, int] | None = None) -> dict[str, Any]:
    """COrderAddNewCompletePlanCommand — RO only."""
    return {
        "plan_subject_off": 0x28,
        "plan_subject": list(plan_subject) if plan_subject else [],
        "units_or_path_off": 0x48,
        "posting": "DISABLED",
    }


def set_order_group_motorization_recipe(order_group_handle: list[int] | tuple[int, int],
                                        motorization: int = 0) -> dict[str, Any]:
    """CSetOrderGroupMotorizationCommand — RO only."""
    return {
        "order_group_off": 0x28,
        "order_group": list(order_group_handle),
        "motorization_off": 0x30,
        "motorization": motorization,
        "posting": "DISABLED",
    }


def set_order_group_name_recipe(order_group_handle: list[int] | tuple[int, int],
                                name: str = "") -> dict[str, Any]:
    """CSetOrderGroupNameCommand — RO only."""
    return {
        "order_group_off": 0x28,
        "order_group": list(order_group_handle),
        "name_sso_off": 0x30,
        "name": name,
        "posting": "DISABLED",
    }


def set_order_group_proximity_recipe(order_group_handle: list[int] | tuple[int, int],
                                     proximity: int = 0) -> dict[str, Any]:
    """CSetOrderGroupLeaderProximityCommand — RO only."""
    return {
        "order_group_off": 0x28,
        "order_group": list(order_group_handle),
        "proximity_off": 0x30,
        "proximity": proximity,
        "posting": "DISABLED",
    }


def order_unassign_recipe(units: list[list[int]] | None = None,
                          unassign_group: int = 0) -> dict[str, Any]:
    """COrderUnassignCommand — RO only."""
    units = units or []
    return {
        "units_data_off": 0x28,
        "units": units,
        "units_count_off": 0x34,
        "units_count": len(units),
        "unassign_group_off": 0x48,
        "unassign_group": unassign_group,
        "posting": "DISABLED",
    }


def order_set_paradrop_recipe(subject_handle: list[int] | tuple[int, int],
                              province_or_id: int = 0, which: str = "target") -> dict[str, Any]:
    """COrderSetParadropSource/TargetCommand — RO only."""
    return {
        "which": which,
        "subject_or_vec_off": 0x28,
        "subject": list(subject_handle),
        "id_off": 0x30,
        "province_or_id": province_or_id,
        "posting": "DISABLED",
    }


def order_set_training_recipe(subject_handle: list[int] | tuple[int, int],
                              training_flag: int = 1) -> dict[str, Any]:
    """COrderSetTrainingCommand — RO only."""
    return {
        "subject_or_vec_off": 0x28,
        "subject": list(subject_handle),
        "training_flag_off": 0x30,
        "training_flag": training_flag,
        "posting": "DISABLED",
    }


def remove_from_army_group_recipe(army_handle: list[int] | tuple[int, int],
                                  group_handle: list[int] | tuple[int, int]) -> dict[str, Any]:
    """CRemoveFromArmyGroupCommand — RO only."""
    return {
        "army_or_units_off": 0x28,
        "army_or_units": list(army_handle),
        "group_off": 0x30,
        "group": list(group_handle),
        "posting": "DISABLED",
    }


def disband_theater_group_recipe(theater_handle: list[int] | tuple[int, int]) -> dict[str, Any]:
    """CDisbandTheaterGroupCommand — RO only."""
    return {
        "theater_handle_off": 0x28,
        "theater_handle": list(theater_handle),
        "posting": "DISABLED",
    }


def reorder_theaters_recipe(theater_ids: list[int] | None = None) -> dict[str, Any]:
    """CReorderTheatersCommand — RO only."""
    theater_ids = theater_ids or []
    return {
        "theater_vec_off": 0x28,
        "theater_ids": theater_ids,
        "count_or_id_off": 0x30,
        "count": len(theater_ids),
        "posting": "DISABLED",
    }


def set_conveyor_field_recipe(subject_handle: list[int] | tuple[int, int],
                              field: str = "priority", value: int = 0) -> dict[str, Any]:
    """CSetConveyor* / ChangeConveyor* sketch — RO only."""
    return {
        "field": field,
        "subject_or_vec_off": 0x28,
        "subject": list(subject_handle),
        "value_off": 0x30,
        "value": value,
        "posting": "DISABLED",
    }


def remove_conveyor_recipe(subject_handle: list[int] | tuple[int, int],
                           which: str = "conveyor") -> dict[str, Any]:
    """CRemoveConveyor(Command|LineCommand) — RO only."""
    return {
        "which": which,
        "subject_or_vec_off": 0x28,
        "subject": list(subject_handle),
        "posting": "DISABLED",
    }


def learn_trait_recipe(leader_handle: list[int] | tuple[int, int],
                       trait: int = 0) -> dict[str, Any]:
    """CLearnTraitCommand — RO only."""
    return {
        "leader_off": 0x28,
        "leader": list(leader_handle),
        "trait_off": 0x30,
        "trait": trait,
        "posting": "DISABLED",
    }


def set_repair_order_recipe(subject_handle: list[int] | tuple[int, int],
                            order_or_flag: int = 1) -> dict[str, Any]:
    """CSetRepairOrderCommand — RO only."""
    return {
        "subject_off": 0x28,
        "subject": list(subject_handle),
        "order_or_flag_off": 0x30,
        "order_or_flag": order_or_flag,
        "posting": "DISABLED",
    }


def set_division_name_recipe(division_handle: list[int] | tuple[int, int],
                             name: str = "") -> dict[str, Any]:
    """CSetDivisionNameCommand — RO only."""
    return {
        "division_off": 0x28,
        "division": list(division_handle),
        "name_sso_off": 0x30,
        "name": name,
        "posting": "DISABLED",
    }


def upgrade_division_officer_recipe(subject_handle: list[int] | tuple[int, int],
                                    officer_or_id: int = 0) -> dict[str, Any]:
    """CUpgradeDivisionOfficerCommand — RO only."""
    return {
        "subject_off": 0x28,
        "subject": list(subject_handle),
        "officer_or_id_off": 0x30,
        "officer_or_id": officer_or_id,
        "posting": "DISABLED",
    }


def build_railway_recipe(from_to_or_vec: list[int] | tuple[int, int] | None = None) -> dict[str, Any]:
    """CBuildRailwayCommand — RO only (land logistics edge)."""
    return {
        "from_to_or_vec_off": 0x28,
        "from_to_or_vec": list(from_to_or_vec) if from_to_or_vec else [],
        "extra_off": 0x30,
        "posting": "DISABLED",
    }


def merge_armies_recipe(army_a: list[int] | tuple[int, int],
                        army_b: list[int] | tuple[int, int]) -> dict[str, Any]:
    """CMergeArmiesCommand — RO only."""
    return {
        "army_a_off": 0x28,
        "army_a": list(army_a),
        "army_b_off": 0x30,
        "army_b": list(army_b),
        "posting": "DISABLED",
    }


def delete_unit_recipe(unit_handle: list[int] | tuple[int, int]) -> dict[str, Any]:
    """CDeleteUnitCommand — RO only."""
    return {
        "unit_off": 0x28,
        "unit": list(unit_handle),
        "posting": "DISABLED",
    }


def transport_unit_recipe(unit_handle: list[int] | tuple[int, int],
                          dest_or_fleet: int = 0) -> dict[str, Any]:
    """CTransportUnitCommand — RO only (land embark edge)."""
    return {
        "unit_off": 0x28,
        "unit": list(unit_handle),
        "dest_or_fleet_off": 0x30,
        "dest_or_fleet": dest_or_fleet,
        "posting": "DISABLED",
    }


def set_theatre_recipe(subject_handle: list[int] | tuple[int, int],
                       theatre_id: int = 0) -> dict[str, Any]:
    """CSetTheatreCommand — RO only."""
    return {
        "subject_off": 0x28,
        "subject": list(subject_handle),
        "theatre_id_off": 0x30,
        "theatre_id": theatre_id,
        "posting": "DISABLED",
    }


def set_unit_name_recipe(unit_handle: list[int] | tuple[int, int],
                         name: str = "") -> dict[str, Any]:
    """CSetUnitNameCommand — RO only."""
    return {
        "unit_off": 0x28,
        "unit": list(unit_handle),
        "name_sso_off": 0x30,
        "name": name,
        "posting": "DISABLED",
    }


def set_preferred_tactic_recipe(subject_handle: list[int] | tuple[int, int],
                                tactic: int = 0) -> dict[str, Any]:
    """CSetPreferredTacticCommand — RO only."""
    return {
        "subject_off": 0x28,
        "subject": list(subject_handle),
        "tactic_off": 0x30,
        "tactic": tactic,
        "posting": "DISABLED",
    }


def area_defense_recipe(subject_handle: list[int] | tuple[int, int],
                        which: str = "create", setting: int = 0) -> dict[str, Any]:
    """CCreate/Edit/Set AreaDefense* — RO only."""
    return {
        "which": which,
        "subject_or_vec_off": 0x28,
        "subject": list(subject_handle),
        "setting_off": 0x30,
        "setting": setting,
        "posting": "DISABLED",
    }


def pinned_strategic_region_recipe(region_id: int = 0,
                                   which: str = "toggle") -> dict[str, Any]:
    """CToggle/ReorderPinnedStrategicRegionCommand — RO only."""
    return {
        "which": which,
        "region_or_vec_off": 0x28,
        "region_id": region_id,
        "posting": "DISABLED",
    }


def selection_group_recipe(units: list[list[int]] | None = None) -> dict[str, Any]:
    """CSelectionGroupCommand — RO only."""
    units = units or []
    return {
        "units_off": 0x28,
        "units": units,
        "count_off": 0x34,
        "count": len(units),
        "posting": "DISABLED",
    }


def queue_unit_action_recipe(unit_handle: list[int] | tuple[int, int],
                             action: int = 0) -> dict[str, Any]:
    """CQueueUnitActionCommand — RO only."""
    return {
        "unit_off": 0x28,
        "unit": list(unit_handle),
        "action_off": 0x30,
        "action": action,
        "posting": "DISABLED",
    }


def promote_unit_leader_recipe(leader_handle: list[int] | tuple[int, int]) -> dict[str, Any]:
    """CPromoteUnitLeaderCommand — RO only."""
    return {
        "leader_off": 0x28,
        "leader": list(leader_handle),
        "posting": "DISABLED",
    }


def create_unit_leader_recipe(army_or_slot: list[int] | tuple[int, int] | None = None,
                              leader_def: int = 0) -> dict[str, Any]:
    """CCreateUnitLeaderCommand — RO only."""
    return {
        "army_or_slot_off": 0x28,
        "army_or_slot": list(army_or_slot) if army_or_slot else [],
        "leader_def_off": 0x30,
        "leader_def": leader_def,
        "posting": "DISABLED",
    }


def pending_reassign_target_recipe(unit_handle: list[int] | tuple[int, int],
                                   target: int = 0) -> dict[str, Any]:
    """CSetPendingReassignTargetCommand — RO only."""
    return {
        "unit_off": 0x28,
        "unit": list(unit_handle),
        "target_off": 0x30,
        "target": target,
        "posting": "DISABLED",
    }


def clear_repair_pins_recipe(subject_handle: list[int] | tuple[int, int] | None = None) -> dict[str, Any]:
    """CClearRepairPinsCommand — RO only."""
    return {
        "subject_or_vec_off": 0x28,
        "subject": list(subject_handle) if subject_handle else [],
        "posting": "DISABLED",
    }


def request_expeditionaries_recipe(subject_handle: list[int] | tuple[int, int],
                                   count_or_tag: int = 0) -> dict[str, Any]:
    """CRequestExpeditionariesCommand — RO only."""
    return {
        "subject_off": 0x28,
        "subject": list(subject_handle),
        "count_or_tag_off": 0x30,
        "count_or_tag": count_or_tag,
        "posting": "DISABLED",
    }


def give_medal_recipe(leader_handle: list[int] | tuple[int, int],
                      medal_id: int = 0) -> dict[str, Any]:
    """CGiveMedalCommand — RO only."""
    return {
        "leader_off": 0x28,
        "leader": list(leader_handle),
        "medal_id_off": 0x30,
        "medal_id": medal_id,
        "posting": "DISABLED",
    }


def trigger_ability_recipe(subject_handle: list[int] | tuple[int, int],
                           ability_id: int = 0) -> dict[str, Any]:
    """CTriggerAbilityCommand — RO only."""
    return {
        "subject_off": 0x28,
        "subject": list(subject_handle),
        "ability_id_off": 0x30,
        "ability_id": ability_id,
        "posting": "DISABLED",
    }


def retire_character_recipe(character_handle: list[int] | tuple[int, int]) -> dict[str, Any]:
    """CRetireCharacterCommand — RO only."""
    return {
        "character_off": 0x28,
        "character": list(character_handle),
        "posting": "DISABLED",
    }


def reinstate_exile_recipe(character_handle: list[int] | tuple[int, int]) -> dict[str, Any]:
    """CReinstateExileCommand — RO only."""
    return {
        "character_off": 0x28,
        "character": list(character_handle),
        "posting": "DISABLED",
    }


def amend_foreign_manpower_recipe(subject_handle: list[int] | tuple[int, int],
                                  amount: int = 0) -> dict[str, Any]:
    """CAmendForeignManpowerActionCommand — RO only."""
    return {
        "subject_off": 0x28,
        "subject": list(subject_handle),
        "amount_off": 0x30,
        "amount": amount,
        "posting": "DISABLED",
    }


def ai_store_wanted_divisions_recipe(subject_handle: list[int] | tuple[int, int],
                                     count: int = 0) -> dict[str, Any]:
    """CAiStoreTotalWantedNrDivisionsCommand — RO only."""
    return {
        "subject_off": 0x28,
        "subject": list(subject_handle),
        "count_off": 0x30,
        "count": count,
        "posting": "DISABLED",
    }


def country_reinforcement_priority_recipe(country_or_subject: list[int] | tuple[int, int] | int,
                                          priority: int = 0) -> dict[str, Any]:
    """CSetCountryReinforcementPriorityCommand — RO only."""
    subj = list(country_or_subject) if isinstance(country_or_subject, (list, tuple)) else [int(country_or_subject), 0]
    return {
        "subject_off": 0x28,
        "subject": subj,
        "priority_off": 0x30,
        "priority": priority,
        "posting": "DISABLED",
    }


def ai_force_concentration_recipe(subject_handle: list[int] | tuple[int, int],
                                  which: str = "store", target: int = 0) -> dict[str, Any]:
    """CAiStore/DiscardForceConcentrationTargetCommand — RO only."""
    return {
        "which": which,
        "subject_off": 0x28,
        "subject": list(subject_handle),
        "target_off": 0x30,
        "target": target,
        "posting": "DISABLED",
    }


def land_post_readiness_recipe() -> dict[str, Any]:
    """RO snapshot of SHARED_LAND_HELPERS / LAND_POST_READINESS — never posts."""
    try:
        import cmd_layout as _cl
        pr = getattr(_cl, "LAND_POST_READINESS", {}) or {}
        sh = getattr(_cl, "SHARED_LAND_HELPERS", {}) or {}
    except Exception as e:
        return {"error": str(e), "posting": "DISABLED"}
    helpers = sh.get("helpers") or {}
    primary = sum(1 for h in helpers.values() if h.get("tier") != "second_order")
    second = sum(1 for h in helpers.values() if h.get("tier") == "second_order")
    return {
        "phase": pr.get("phase") or sh.get("phase"),
        "helper_count": len(helpers),
        "primary_shared": primary,
        "second_order_hot": second,
        "by_class": pr.get("by_class") or sh.get("by_class"),
        "second_order_by_class": pr.get("second_order_by_class") or sh.get("second_order_by_class"),
        "by_tier": pr.get("by_tier") or sh.get("by_tier"),
        "execute_shared_unknown_count": pr.get("execute_shared_unknown_count") or sh.get("execute_shared_unknown_count"),
        "hot_execute_unknown_by_class": pr.get("hot_execute_unknown_by_class"),
        "expanded_roles_2cf": pr.get("expanded_roles_2cf"),
        "expanded_cores_2cg": pr.get("expanded_cores_2cg"),
        "expanded_cores_2ch": pr.get("expanded_cores_2ch"),
        "expanded_cores_2ci": pr.get("expanded_cores_2ci"),
        "named_helpers": pr.get("named_helpers"),
        "genuine_divergences": pr.get("genuine_divergences"),
        "coverage_2ci": pr.get("coverage_2ci"),
        "post_implications_2ci": pr.get("post_implications_2ci"),
        "unknown_second_order_count": pr.get("unknown_second_order_count") or sh.get("unknown_second_order_count"),
        "unknown_third_order_count": pr.get("unknown_third_order_count") or sh.get("unknown_third_order_count"),
        "cross_land_fresh_count": pr.get("cross_land_fresh_count") or sh.get("cross_land_fresh_count"),
        "core_expansions_2ch": pr.get("core_expansions_2ch"),
        "named_helpers": pr.get("named_helpers"),
        "isvalid_gate_helpers": pr.get("isvalid_gate_helpers"),
        "execute_body_helpers": pr.get("execute_body_helpers"),
        "role_post_paths": {
            role: {
                "commands": (meta or {}).get("commands"),
                "min_gates_intersection": (meta or {}).get("min_gates_intersection"),
                "soft_gates_majority": (meta or {}).get("soft_gates_majority"),
                "union_gates": (meta or {}).get("union_gates"),
            }
            for role, meta in ((pr.get("role_post_paths") or {}) or {}).items()
        },
        "preferred_cores": {
            k: {
                "core_commands": (m or {}).get("core_commands"),
                "min_gates_intersection": (m or {}).get("min_gates_intersection"),
                "coverage": (m or {}).get("coverage"),
                "basis": (m or {}).get("basis"),
                "excluded": (m or {}).get("excluded"),
            }
            for k, m in ((pr.get("preferred_cores") or {}) or {}).items()
        },
        "soft_to_hard_closures_2cg": pr.get("soft_to_hard_closures_2cg"),
        "soft_to_hard_closures_2ch": pr.get("soft_to_hard_closures_2ch"),
        "post_implications_2ch": pr.get("post_implications_2ch"),
        "requirements_before_any_post": pr.get("requirements_before_any_post"),
        "post_implications_2ce": pr.get("post_implications_2ce"),
        "post_implications_2cg": pr.get("post_implications_2cg"),
        "posting": "DISABLED",
        "allow_post": False,
        "tool_gate": "CLOSED_NOT_OPENED",
    }


def move_command_recipe(army_row: dict[str, Any], dest_province_id: int,
                        clear: int = 0, move_priority: int = 0) -> dict[str, Any]:
    """CMoveCommand field map — RO docs only; never posts."""
    return {
        "unit_handle_off": 0x28,  # subject_lo/hi cluster @+0x28..; layout also marks 40
        "unit_handle": list(army_row["handle"]),
        "subject_lo_off": 0x28,
        "dest_or_arg0_off": 0x30,
        "dest_province": dest_province_id,
        "arg1_or_count_off": 0x34,
        "clear": clear,
        "move_priority": move_priority,
        "source_province_id": army_row.get("province_id"),
        "post_gate_candidates": [
            "0x2284800", "0x254aa00", "0x2607890", "0x1e1510", "0xc07b80", "0x11f240", "0x25c3770",
        ],
        "named_helpers": ["gamestate_instance_guard_b"],
        "note": "Shares Execute plumbing with CStrategicRedeploymentCommand; IsValid must pass live",
        "posting": "DISABLED",
    }


def order_reconnect_recipe(order_a: int = 0, order_b: int = 0, order_c: int = 0) -> dict[str, Any]:
    """COrderReconnectCommand — RO docs; mirrors connect subject/id cluster."""
    return {
        "subject_or_vec_off": 0x28,
        "id_or_b_off": 0x2C,
        "id_or_c_off": 0x30,
        "order_a": order_a,
        "order_b": order_b,
        "order_c": order_c,
        "post_gate_candidates": ["0x2284800", "0xbbb1e0", "0xc40230"],
        "named_helpers": ["gamestate_instance_guard"],
        "note": "GetOrderInstance path; subject pair required; posting DISABLED",
        "posting": "DISABLED",
    }


def replace_fallback_recipe(unit_handles: list[list[int]] | None = None,
                            province_or_path: int = 0) -> dict[str, Any]:
    """COrderReplaceFallbackCommands — RO docs only."""
    handles = unit_handles or []
    return {
        "subject_or_vec_off": 0x28,
        "units": [list(h) for h in handles],
        "units_count": len(handles),
        "province_or_path_off": 0x30,
        "province_or_path": province_or_path,
        "post_gate_candidates": ["0x2284800", "0xbbb1e0", "0xc40230"],
        "note": "Retreat/fallback replace; IsValid gates shared with NewFallback; posting DISABLED",
        "posting": "DISABLED",
    }


def land_role_post_path_recipe(role: str | None = None) -> dict[str, Any]:
    """RO: role → min IsValid gate intersection from LAND_POST_READINESS.role_post_paths."""
    try:
        import cmd_layout as _cl
        pr = getattr(_cl, "LAND_POST_READINESS", {}) or {}
    except Exception as e:
        return {"error": str(e), "posting": "DISABLED"}
    paths = pr.get("role_post_paths") or {}
    if role:
        meta = paths.get(role) or {}
        prefs = pr.get("preferred_cores") or {}
        # match preferred cores whose key starts with role
        matched = {
            k: {
                "core_commands": (m or {}).get("core_commands"),
                "min_gates_intersection": (m or {}).get("min_gates_intersection"),
                "coverage": (m or {}).get("coverage"),
                "basis": (m or {}).get("basis"),
                "excluded": (m or {}).get("excluded"),
            }
            for k, m in prefs.items()
            if k == f"{role}_core" or k.startswith(f"{role}_")
        }
        return {
            "role": role,
            "commands": meta.get("commands"),
            "command_count": meta.get("command_count") or len(meta.get("commands") or []),
            "min_gates_intersection": meta.get("min_gates_intersection"),
            "soft_gates_majority": meta.get("soft_gates_majority"),
            "cmds_with_gates": meta.get("cmds_with_gates"),
            "union_gates": meta.get("union_gates"),
            "union_body": meta.get("union_body"),
            "union_second": meta.get("union_second"),
            "union_exe_unknown_hot": meta.get("union_exe_unknown_hot"),
            "preferred_cores": matched,
            "posting": "DISABLED",
            "allow_post": False,
        }
    return {
        "roles": {
            r: {
                "command_count": m.get("command_count") or len(m.get("commands") or []),
                "min_gates_intersection": m.get("min_gates_intersection"),
                "soft_gates_majority": m.get("soft_gates_majority"),
                "union_exe_unknown_hot_count": len(m.get("union_exe_unknown_hot") or []),
            }
            for r, m in paths.items()
        },
        "posting": "DISABLED",
        "allow_post": False,
        "tool_gate": "CLOSED_NOT_OPENED",
    }


def land_execute_shared_unknown_recipe(limit: int = 16) -> dict[str, Any]:
    """RO catalog of Execute-shared unknown helpers (≥3 land Execute hits). Never posts."""
    try:
        import cmd_layout as _cl
        sh = getattr(_cl, "SHARED_LAND_HELPERS", {}) or {}
        pr = getattr(_cl, "LAND_POST_READINESS", {}) or {}
    except Exception as e:
        return {"error": str(e), "posting": "DISABLED"}
    helpers = sh.get("helpers") or {}
    rows = []
    for rva, h in helpers.items():
        if h.get("tier") != "execute_shared_unknown":
            continue
        rows.append({
            "rva": rva,
            "hits": h.get("hits_across_land_execute") or h.get("hits"),
            "class": h.get("class"),
            "strings": h.get("strings"),
        })
    rows.sort(key=lambda r: (-(r.get("hits") or 0), r["rva"]))
    return {
        "phase": pr.get("phase") or sh.get("phase"),
        "count": len(rows),
        "by_class": pr.get("hot_execute_unknown_by_class"),
        "top": rows[:limit],
        "posting": "DISABLED",
        "allow_post": False,
        "tool_gate": "CLOSED_NOT_OPENED",
    }


def theater_role_post_path_recipe() -> dict[str, Any]:
    """Convenience RO wrapper for theater role_post_paths (2cf expanded)."""
    return land_role_post_path_recipe("theater")


def order_group_role_post_path_recipe() -> dict[str, Any]:
    """Convenience RO wrapper for order_group role_post_paths (2cf expanded)."""
    return land_role_post_path_recipe("order_group")


def garrison_role_post_path_recipe() -> dict[str, Any]:
    """Convenience RO wrapper for garrison role_post_paths (2cf expanded)."""
    return land_role_post_path_recipe("garrison")

def land_preferred_core_recipe(core_name: str | None = None) -> dict[str, Any]:
    """RO: preferred role cores that close soft_gates_majority into hard intersections on subsets."""
    try:
        import cmd_layout as _cl
        pr = getattr(_cl, "LAND_POST_READINESS", {}) or {}
    except Exception as e:
        return {"error": str(e), "posting": "DISABLED"}
    prefs = pr.get("preferred_cores") or {}
    if core_name:
        m = prefs.get(core_name) or {}
        return {
            "core": core_name,
            "core_commands": m.get("core_commands"),
            "min_gates_intersection": m.get("min_gates_intersection"),
            "coverage": m.get("coverage"),
            "basis": m.get("basis"),
            "excluded": m.get("excluded"),
            "posting": "DISABLED",
            "allow_post": False,
            "tool_gate": "CLOSED_NOT_OPENED",
        }
    return {
        "cores": {
            k: {
                "coverage": (m or {}).get("coverage"),
                "min_gates_intersection": (m or {}).get("min_gates_intersection"),
                "basis": (m or {}).get("basis"),
                "n_core": len((m or {}).get("core_commands") or []),
                "n_excluded": len((m or {}).get("excluded") or []),
            }
            for k, m in prefs.items()
        },
        "soft_to_hard_closures_2cg": pr.get("soft_to_hard_closures_2cg"),
        "posting": "DISABLED",
        "allow_post": False,
        "tool_gate": "CLOSED_NOT_OPENED",
    }


def land_unknown_second_order_recipe(limit: int = 16) -> dict[str, Any]:
    """RO catalog of unknown_second_order helpers mined from execute_shared_unknown. Never posts."""
    try:
        import cmd_layout as _cl
        sh = getattr(_cl, "SHARED_LAND_HELPERS", {}) or {}
        pr = getattr(_cl, "LAND_POST_READINESS", {}) or {}
    except Exception as e:
        return {"error": str(e), "posting": "DISABLED"}
    helpers = sh.get("helpers") or {}
    rows = []
    for rva, h in helpers.items():
        if h.get("tier") != "unknown_second_order":
            continue
        rows.append({
            "rva": rva,
            "hits": h.get("hits"),
            "class": h.get("class"),
            "caller_groups": h.get("caller_groups"),
        })
    rows.sort(key=lambda r: (-(r.get("hits") or 0), r["rva"]))
    return {
        "phase": pr.get("phase") or sh.get("phase"),
        "count": len(rows),
        "top": rows[:limit],
        "posting": "DISABLED",
        "allow_post": False,
        "tool_gate": "CLOSED_NOT_OPENED",
    }


def attack_core_post_path_recipe() -> dict[str, Any]:
    return land_preferred_core_recipe("attack_core")


def move_army_core_post_path_recipe() -> dict[str, Any]:
    return land_preferred_core_recipe("move_army_core")


def frontline_core_post_path_recipe() -> dict[str, Any]:
    return land_preferred_core_recipe("frontline_core")


def retreat_fallback_core_post_path_recipe() -> dict[str, Any]:
    return land_preferred_core_recipe("retreat_fallback_core")

def land_cross_fresh_helper_recipe(limit: int = 16) -> dict[str, Any]:
    """RO catalog of cross_land_fresh helpers mined in 2ch deepen. Never posts."""
    try:
        import cmd_layout as _cl
        sh = getattr(_cl, "SHARED_LAND_HELPERS", {}) or {}
        pr = getattr(_cl, "LAND_POST_READINESS", {}) or {}
    except Exception as e:
        return {"error": str(e), "posting": "DISABLED"}
    helpers = sh.get("helpers") or {}
    rows = []
    for rva, h in helpers.items():
        if h.get("tier") != "cross_land_fresh":
            continue
        rows.append({
            "rva": rva,
            "hits": h.get("hits"),
            "class": h.get("class"),
            "caller_groups": h.get("caller_groups"),
        })
    rows.sort(key=lambda r: (-(r.get("hits") or 0), r["rva"]))
    return {
        "phase": pr.get("phase") or sh.get("phase"),
        "count": len(rows),
        "top": rows[:limit],
        "posting": "DISABLED",
        "allow_post": False,
        "tool_gate": "CLOSED_NOT_OPENED",
    }


def garrison_bbb_core_post_path_recipe() -> dict[str, Any]:
    return land_preferred_core_recipe("garrison_bbb_core")


def frontline_bbb_core_post_path_recipe() -> dict[str, Any]:
    return land_preferred_core_recipe("frontline_bbb_core")


def move_theater_core_post_path_recipe() -> dict[str, Any]:
    return land_preferred_core_recipe("move_theater_core")


def theater_garrison_prio_core_post_path_recipe() -> dict[str, Any]:
    return land_preferred_core_recipe("theater_garrison_prio_core")


def strategic_unit_redeploy_core_post_path_recipe() -> dict[str, Any]:
    return land_preferred_core_recipe("strategic_unit_redeploy_core")


def cancel_abort_core_post_path_recipe() -> dict[str, Any]:
    return land_preferred_core_recipe("cancel_abort_core")

def land_named_gate_recipe() -> dict[str, Any]:
    """RO: named IsValid/shared helper labels from LAND_POST_READINESS. Never posts."""
    try:
        import cmd_layout as _cl
        pr = getattr(_cl, "LAND_POST_READINESS", {}) or {}
        sh = getattr(_cl, "SHARED_LAND_HELPERS", {}) or {}
    except Exception as e:
        return {"error": str(e), "posting": "DISABLED"}
    named = pr.get("named_helpers") or {}
    helpers = sh.get("helpers") or {}
    rows = []
    for rva, label in sorted(named.items(), key=lambda kv: kv[1]):
        h = helpers.get(rva) or {}
        rows.append({
            "rva": rva,
            "name": label,
            "tier": h.get("tier"),
            "class": h.get("class"),
            "hits": h.get("hits"),
            "looks_like_isvalid_gate": (h.get("post_readiness") or {}).get("looks_like_isvalid_gate"),
        })
    return {
        "phase": pr.get("phase"),
        "count": len(rows),
        "gates": rows,
        "posting": "DISABLED",
        "allow_post": False,
        "tool_gate": "CLOSED_NOT_OPENED",
    }


def land_genuine_divergence_recipe(role: str | None = None) -> dict[str, Any]:
    """RO catalog of documented genuine IsValid divergences (separate Post paths if ever)."""
    try:
        import cmd_layout as _cl
        pr = getattr(_cl, "LAND_POST_READINESS", {}) or {}
    except Exception as e:
        return {"error": str(e), "posting": "DISABLED"}
    rows = list(pr.get("genuine_divergences") or [])
    if role:
        rows = [r for r in rows if r.get("role") == role or role in str(r.get("core") or "")]
    return {
        "phase": pr.get("phase"),
        "count": len(rows),
        "divergences": rows,
        "coverage": pr.get("coverage_2ci"),
        "posting": "DISABLED",
        "allow_post": False,
        "tool_gate": "CLOSED_NOT_OPENED",
        "note": "Divergences are observe-only documentation — never merge into primary soft gates for Post",
    }


def land_execute_unknown_shared_recipe(limit: int = 16) -> dict[str, Any]:
    """RO catalog of land_execute_unknown_shared helpers (2ci). Never posts."""
    try:
        import cmd_layout as _cl
        sh = getattr(_cl, "SHARED_LAND_HELPERS", {}) or {}
        pr = getattr(_cl, "LAND_POST_READINESS", {}) or {}
    except Exception as e:
        return {"error": str(e), "posting": "DISABLED"}
    helpers = sh.get("helpers") or {}
    rows = []
    for rva, h in helpers.items():
        if h.get("tier") != "land_execute_unknown_shared":
            continue
        rows.append({
            "rva": rva,
            "hits": h.get("hits"),
            "class": h.get("class"),
            "name": h.get("name"),
            "caller_groups": h.get("caller_groups"),
        })
    rows.sort(key=lambda r: (-(r.get("hits") or 0), r["rva"]))
    return {
        "phase": pr.get("phase") or sh.get("phase"),
        "count": len(rows),
        "top": rows[:limit],
        "posting": "DISABLED",
        "allow_post": False,
        "tool_gate": "CLOSED_NOT_OPENED",
    }


def railwaygun_divergence_recipe() -> dict[str, Any]:
    """RO: RailwayGun attack-role genuine divergences."""
    return {
        "manual": land_preferred_core_recipe("railwaygun_manual_core"),
        "name": land_preferred_core_recipe("railwaygun_name_core"),
        "posting": "DISABLED",
        "allow_post": False,
    }



# --- Phase 2cj: named helper expansion + OL unique execute + post-path checklist (READ-ONLY) ---

def land_named_helper_expansion_recipe(command_name: str | None = None) -> dict:
    """Map named IsValid/Execute helpers to land cmds (2cj). Observe-only; never hook/Post."""
    try:
        import cmd_layout as _cl
    except Exception as e:
        return {"error": str(e), "posting": "DISABLED", "allow_post": False}
    pr = getattr(_cl, "LAND_POST_READINESS", {}) or {}
    helpers = (getattr(_cl, "SHARED_LAND_HELPERS", {}) or {}).get("helpers") or {}
    named = pr.get("named_helpers") or {}
    focus = (getattr(_cl, "LAND_ARMY_FOCUS", {}) or {}).get("commands") or {}
    ivp = getattr(_cl, "ISVALID_PATHS", {}) or {}
    out = {
        "phase": "2cj",
        "allow_post": False,
        "posting": "DISABLED",
        "named_count": len(named),
        "by_helper": {},
        "note": "Named helpers are documentation labels for RO Capstone hits; do not patch/hook.",
    }
    for addr, label in named.items():
        h = helpers.get(addr) or {}
        cmds = []
        for n, meta in ivp.items():
            if not isinstance(meta, dict):
                continue
            calls = set(meta.get("isvalid_calls") or [])
            if addr in calls:
                cmds.append(n)
        out["by_helper"][addr] = {
            "name": label,
            "tier": h.get("tier"),
            "class": h.get("class"),
            "caller_groups": h.get("caller_groups"),
            "isvalid_cmds_sample": cmds[:12],
            "post_readiness": h.get("post_readiness"),
            "do_not_hook_for_post": True,
        }
    if command_name:
        out["filter_command"] = command_name
        out["command_role"] = (focus.get(command_name) or {}).get("role")
    return out


def offensive_line_execute_recipe(command_name: str | None = None) -> dict:
    """Offensive-line Execute unique helpers cataloged in 2cj. Docs only."""
    try:
        import cmd_layout as _cl
    except Exception as e:
        return {"error": str(e), "posting": "DISABLED", "allow_post": False}
    pr = getattr(_cl, "LAND_POST_READINESS", {}) or {}
    ol = pr.get("offensive_line_execute_2cj") or pr.get("offensive_line_execute_2ci") or {}
    named = pr.get("named_helpers") or {}
    out = {
        "phase": "2cj",
        "allow_post": False,
        "posting": "DISABLED",
        "commands": {},
        "note": "OL unique Execute RVAs cataloged as offensive_line_unique_execute; still observe-only.",
    }
    for n, meta in ol.items():
        if command_name and n != command_name:
            continue
        still = meta.get("still_unique_unknown") or []
        cataloged = meta.get("known_or_cataloged") or []
        out["commands"][n] = {
            "n_exe_calls": meta.get("n_exe_calls"),
            "cataloged": cataloged,
            "still_unique_unknown": still,
            "named": {a: named.get(a) for a in cataloged if a in named},
            "fully_cataloged": not still,
            "do_not_post": True,
        }
    out["fully_cataloged_count"] = sum(1 for v in out["commands"].values() if v.get("fully_cataloged"))
    out["total"] = len(out["commands"])
    return out


def land_post_path_checklist_recipe(role: str | None = None) -> dict:
    """Document preferred-core Post readiness paths WITHOUT enabling Post (2cj)."""
    try:
        import cmd_layout as _cl
    except Exception as e:
        return {"error": str(e), "posting": "DISABLED", "allow_post": False}
    pr = getattr(_cl, "LAND_POST_READINESS", {}) or {}
    prefs = pr.get("preferred_cores") or {}
    divs = pr.get("genuine_divergences") or []
    checklist = pr.get("post_readiness_checklist_2cj") or {}
    role_paths = pr.get("role_post_paths") or {}
    focus = (getattr(_cl, "LAND_ARMY_FOCUS", {}) or {}).get("commands") or {}
    out = {
        "phase": "2cj",
        "allow_post": False,
        "posting": "DISABLED",
        "tool_gate": pr.get("tool_gate") or "CLOSED_NOT_OPENED",
        "requirements_before_any_post": pr.get("requirements_before_any_post"),
        "do_not": (checklist.get("do_not") or [
            "enable ALLOW_POST",
            "patch/hook helpers",
            "Post inject",
            "HourlyTick / GameSpeed writes",
            "guess writes",
        ]),
        "preferred_cores": {},
        "genuine_divergences": [],
        "note": "Checklist for future Post readiness docs. ALLOW_POST remains False.",
    }
    for k, m in prefs.items():
        if role:
            cmds = m.get("core_commands") or []
            if cmds:
                r0 = (focus.get(cmds[0]) or {}).get("role")
                if r0 != role and not k.startswith(role):
                    continue
            elif not k.startswith(role):
                continue
        out["preferred_cores"][k] = {
            "min_gates_intersection": m.get("min_gates_intersection"),
            "coverage": m.get("coverage"),
            "genuine_divergence": m.get("genuine_divergence", False),
            "basis": m.get("basis"),
            "allow_post": False,
        }
    for d in divs:
        if role and d.get("role") and d.get("role") != role:
            continue
        out["genuine_divergences"].append(d)
    if role and role in role_paths:
        out["role_soft"] = role_paths[role]
    return out


def land_divergence_gate_delta_recipe(core: str | None = None) -> dict:
    """Expose refined divergence gate deltas vs primary role cores (2cj)."""
    try:
        import cmd_layout as _cl
    except Exception as e:
        return {"error": str(e), "posting": "DISABLED", "allow_post": False}
    divs = (getattr(_cl, "LAND_POST_READINESS", {}) or {}).get("genuine_divergences") or []
    out = {
        "phase": "2cj",
        "allow_post": False,
        "divergences": [],
        "note": "Gate deltas are Capstone IsValid call set differences — not Post enablement.",
    }
    for d in divs:
        if d.get("full_role_hard_empty"):
            continue
        if core and d.get("core") != core:
            continue
        out["divergences"].append(d)
    return out


# --- Phase 2ck: role post-path matrix + singleton edge docs (READ-ONLY) ---

def land_role_post_path_matrix_recipe(role: str | None = None) -> dict:
    """Per-role Post readiness paths (preferred cores, named gates, steps). Docs only — never enables Post."""
    try:
        import cmd_layout as _cl
    except Exception as e:
        return {"error": str(e), "posting": "DISABLED", "allow_post": False}
    pr = getattr(_cl, "LAND_POST_READINESS", {}) or {}
    matrix = pr.get("role_post_path_matrix_2ck") or {}
    out = {
        "phase": "2ck",
        "allow_post": False,
        "posting": "DISABLED",
        "tool_gate": pr.get("tool_gate") or "CLOSED_NOT_OPENED",
        "roles": {},
        "note": "Use preferred_core hard gates per role; soft gates are advisory. Do not Post.",
    }
    for r, meta in matrix.items():
        if role and r != role:
            continue
        out["roles"][r] = meta
    out["role_count"] = len(out["roles"])
    return out


def land_singleton_execute_edge_recipe(role: str | None = None) -> dict:
    """Document singleton (hit=1) execute edges without cataloging helpers (anti-inflation)."""
    try:
        import cmd_layout as _cl
    except Exception as e:
        return {"error": str(e), "posting": "DISABLED", "allow_post": False}
    pr = getattr(_cl, "LAND_POST_READINESS", {}) or {}
    edges = pr.get("singleton_execute_edges_2ck") or {}
    out = {
        "phase": "2ck",
        "allow_post": False,
        "posting": "DISABLED",
        "edges": {},
        "note": "Singletons documented only — not added to SHARED_LAND_HELPERS.",
    }
    for r, items in edges.items():
        if role and r != role:
            continue
        out["edges"][r] = items
    out["total"] = sum(len(v) for v in out["edges"].values())
    return out


def land_post_readiness_checklist_2ck_recipe(role: str | None = None) -> dict:
    """Consolidated 2ck checklist + optional role matrix slice. ALLOW_POST remains False."""
    try:
        import cmd_layout as _cl
    except Exception as e:
        return {"error": str(e), "posting": "DISABLED", "allow_post": False}
    pr = getattr(_cl, "LAND_POST_READINESS", {}) or {}
    checklist = dict(pr.get("post_readiness_checklist_2ck") or {})
    matrix = pr.get("role_post_path_matrix_2ck") or {}
    out = {
        "phase": "2ck",
        "allow_post": False,
        "posting": "DISABLED",
        "tool_gate": pr.get("tool_gate") or "CLOSED_NOT_OPENED",
        "checklist": checklist,
        "role_slice": matrix.get(role) if role else None,
        "do_not": checklist.get("do_not") or [
            "enable ALLOW_POST",
            "patch/hook helpers",
            "Post inject",
            "HourlyTick / GameSpeed writes",
            "guess writes",
        ],
        "note": "Checklist for future Post readiness docs only.",
    }
    return out


# --- Phase 2cl: per-cmd post-path index + enriched matrix (READ-ONLY) ---

def land_cmd_post_path_index_recipe(command_name: str | None = None, role: str | None = None) -> dict:
    """Per-command Post readiness index (recommended_core + named gates). Docs only — never enables Post."""
    try:
        import cmd_layout as _cl
    except Exception as e:
        return {"error": str(e), "posting": "DISABLED", "allow_post": False}
    pr = getattr(_cl, "LAND_POST_READINESS", {}) or {}
    idx = pr.get("cmd_post_path_index_2cl") or {}
    out = {
        "phase": "2cl",
        "allow_post": False,
        "posting": "DISABLED",
        "tool_gate": pr.get("tool_gate") or "CLOSED_NOT_OPENED",
        "commands": {},
        "note": "Look up cmd → recommended_core + required_gates. Do not Post.",
    }
    for n, meta in idx.items():
        if command_name and n != command_name:
            continue
        if role and meta.get("role") != role:
            continue
        out["commands"][n] = meta
    out["count"] = len(out["commands"])
    out["fully_named_required_gates"] = sum(
        1 for v in out["commands"].values() if not v.get("unnamed_gates_remaining")
    )
    return out


def land_role_post_path_matrix_2cl_recipe(role: str | None = None) -> dict:
    """Enriched 2cl role matrix (gate naming completeness). Docs only."""
    try:
        import cmd_layout as _cl
    except Exception as e:
        return {"error": str(e), "posting": "DISABLED", "allow_post": False}
    pr = getattr(_cl, "LAND_POST_READINESS", {}) or {}
    matrix = pr.get("role_post_path_matrix_2cl") or pr.get("role_post_path_matrix_2ck") or {}
    out = {
        "phase": "2cl",
        "allow_post": False,
        "posting": "DISABLED",
        "tool_gate": pr.get("tool_gate") or "CLOSED_NOT_OPENED",
        "roles": {},
        "note": "Enriched matrix with gates_fully_named per preferred core.",
    }
    for r, meta in matrix.items():
        if role and r != role:
            continue
        out["roles"][r] = meta
    out["role_count"] = len(out["roles"])
    return out


def land_post_readiness_checklist_2cl_recipe(command_name: str | None = None) -> dict:
    """2cl checklist + optional cmd index slice. ALLOW_POST remains False."""
    try:
        import cmd_layout as _cl
    except Exception as e:
        return {"error": str(e), "posting": "DISABLED", "allow_post": False}
    pr = getattr(_cl, "LAND_POST_READINESS", {}) or {}
    checklist = dict(pr.get("post_readiness_checklist_2cl") or {})
    idx = pr.get("cmd_post_path_index_2cl") or {}
    out = {
        "phase": "2cl",
        "allow_post": False,
        "posting": "DISABLED",
        "tool_gate": pr.get("tool_gate") or "CLOSED_NOT_OPENED",
        "checklist": checklist,
        "command_slice": idx.get(command_name) if command_name else None,
        "do_not": checklist.get("do_not") or [
            "enable ALLOW_POST",
            "patch/hook helpers",
            "Post inject",
            "HourlyTick / GameSpeed writes",
            "guess writes",
        ],
        "note": "Checklist + cmd index for future Post readiness docs only.",
    }
    return out


# --- Phase 2cm: gate_label_only closed + cmd index 121/121 (READ-ONLY) ---

def land_cmd_post_path_index_2cm_recipe(command_name: str | None = None, role: str | None = None) -> dict:
    """Per-command Post readiness index 2cm (121/121, confidence). Docs only — never enables Post."""
    try:
        import cmd_layout as _cl
    except Exception as e:
        return {"error": str(e), "posting": "DISABLED", "allow_post": False}
    pr = getattr(_cl, "LAND_POST_READINESS", {}) or {}
    idx = pr.get("cmd_post_path_index_2cm") or pr.get("cmd_post_path_index_2cl") or {}
    out = {
        "phase": "2cm",
        "allow_post": False,
        "posting": "DISABLED",
        "tool_gate": pr.get("tool_gate") or "CLOSED_NOT_OPENED",
        "commands": {},
        "note": "121/121 index; gate_label_only closed. Do not Post.",
    }
    for n, meta in idx.items():
        if command_name and n != command_name:
            continue
        if role and meta.get("role") != role:
            continue
        out["commands"][n] = meta
    out["count"] = len(out["commands"])
    out["fully_named_required_gates"] = sum(
        1 for v in out["commands"].values() if not v.get("unnamed_gates_remaining")
    )
    confs = [v.get("post_path_confidence") or 0 for v in out["commands"].values()]
    out["avg_post_path_confidence"] = round(sum(confs) / max(1, len(confs)), 3) if confs else 0
    return out


def land_gate_label_promoted_recipe() -> dict:
    """List Capstone-promoted gate_label_only helpers (2cm). Observe-only."""
    try:
        import cmd_layout as _cl
    except Exception as e:
        return {"error": str(e), "posting": "DISABLED", "allow_post": False}
    pr = getattr(_cl, "LAND_POST_READINESS", {}) or {}
    promoted = pr.get("promoted_gate_labels_2cm") or {}
    helpers = (getattr(_cl, "SHARED_LAND_HELPERS", {}) or {}).get("helpers") or {}
    out = {
        "phase": "2cm",
        "allow_post": False,
        "posting": "DISABLED",
        "gate_label_only_closed": bool(pr.get("gate_label_only_closed_2cm")),
        "remaining_gate_label_only": len(pr.get("gate_label_only_2cl") or {}),
        "promoted": {},
        "note": "Promoted from gate_label_only via Capstone RO; do not patch/hook/Post.",
    }
    for addr, label in promoted.items():
        h = helpers.get(addr) or {}
        out["promoted"][addr] = {
            "name": label,
            "tier": h.get("tier"),
            "class": h.get("class"),
            "calls": h.get("calls"),
            "field_offs": h.get("field_offs"),
            "post_readiness": h.get("post_readiness"),
            "do_not_hook_for_post": True,
        }
    out["count"] = len(out["promoted"])
    return out


def land_post_readiness_checklist_2cm_recipe(command_name: str | None = None) -> dict:
    """2cm checklist + optional cmd index slice. ALLOW_POST remains False."""
    try:
        import cmd_layout as _cl
    except Exception as e:
        return {"error": str(e), "posting": "DISABLED", "allow_post": False}
    pr = getattr(_cl, "LAND_POST_READINESS", {}) or {}
    checklist = dict(pr.get("post_readiness_checklist_2cm") or {})
    idx = pr.get("cmd_post_path_index_2cm") or {}
    out = {
        "phase": "2cm",
        "allow_post": False,
        "posting": "DISABLED",
        "tool_gate": pr.get("tool_gate") or "CLOSED_NOT_OPENED",
        "checklist": checklist,
        "command_slice": idx.get(command_name) if command_name else None,
        "do_not": checklist.get("do_not") or [
            "enable ALLOW_POST",
            "patch/hook helpers",
            "Post inject",
            "HourlyTick / GameSpeed writes",
            "guess writes",
        ],
        "note": "Checklist for future Post readiness docs only.",
    }
    return out


# --- Phase 2cn: confidence raise + soft unnamed closed (READ-ONLY) ---

def land_cmd_post_path_index_2cn_recipe(command_name: str | None = None, role: str | None = None) -> dict:
    """Per-command Post readiness index 2cn (confidence-raised). Docs only."""
    try:
        import cmd_layout as _cl
    except Exception as e:
        return {"error": str(e), "posting": "DISABLED", "allow_post": False}
    pr = getattr(_cl, "LAND_POST_READINESS", {}) or {}
    idx = pr.get("cmd_post_path_index_2cn") or pr.get("cmd_post_path_index_2cm") or {}
    out = {
        "phase": "2cn",
        "allow_post": False,
        "posting": "DISABLED",
        "tool_gate": pr.get("tool_gate") or "CLOSED_NOT_OPENED",
        "commands": {},
        "note": "Prefer higher post_path_confidence. Do not Post.",
    }
    for n, meta in idx.items():
        if command_name and n != command_name:
            continue
        if role and meta.get("role") != role:
            continue
        out["commands"][n] = meta
    out["count"] = len(out["commands"])
    confs = [v.get("post_path_confidence") or 0 for v in out["commands"].values()]
    out["avg_post_path_confidence"] = round(sum(confs) / max(1, len(confs)), 3) if confs else 0
    out["cmds_below_0_9"] = sum(1 for c in confs if c < 0.9)
    out["fully_named_required_gates"] = sum(
        1 for v in out["commands"].values() if not v.get("unnamed_gates_remaining")
    )
    return out


def land_confidence_report_2cn_recipe(role: str | None = None) -> dict:
    """Confidence report + optional role filter. Docs only."""
    try:
        import cmd_layout as _cl
    except Exception as e:
        return {"error": str(e), "posting": "DISABLED", "allow_post": False}
    pr = getattr(_cl, "LAND_POST_READINESS", {}) or {}
    rep = dict(pr.get("confidence_report_2cn") or {})
    matrix = pr.get("role_post_path_matrix_2cn") or {}
    out = {
        "phase": "2cn",
        "allow_post": False,
        "posting": "DISABLED",
        "report": rep,
        "role_slice": matrix.get(role) if role else None,
        "note": "Naming-only confidence raise; helpers unchanged; never Post.",
    }
    return out


def land_post_readiness_checklist_2cn_recipe(command_name: str | None = None) -> dict:
    """2cn checklist + optional cmd slice. ALLOW_POST remains False."""
    try:
        import cmd_layout as _cl
    except Exception as e:
        return {"error": str(e), "posting": "DISABLED", "allow_post": False}
    pr = getattr(_cl, "LAND_POST_READINESS", {}) or {}
    checklist = dict(pr.get("post_readiness_checklist_2cn") or {})
    idx = pr.get("cmd_post_path_index_2cn") or {}
    return {
        "phase": "2cn",
        "allow_post": False,
        "posting": "DISABLED",
        "tool_gate": pr.get("tool_gate") or "CLOSED_NOT_OPENED",
        "checklist": checklist,
        "command_slice": idx.get(command_name) if command_name else None,
        "do_not": checklist.get("do_not") or [
            "enable ALLOW_POST", "patch/hook helpers", "Post inject",
            "HourlyTick / GameSpeed writes", "guess writes",
        ],
        "note": "Checklist for future Post readiness docs only.",
    }


# --- Phase 2co: Capstone deep-resolve + shared second-order (READ-ONLY) ---

def land_cmd_post_path_index_2co_recipe(command_name: str | None = None, role: str | None = None) -> dict:
    """Per-command Post readiness index 2co (Capstone confidence raise). Docs only."""
    try:
        import cmd_layout as _cl
    except Exception as e:
        return {"error": str(e), "posting": "DISABLED", "allow_post": False}
    pr = getattr(_cl, "LAND_POST_READINESS", {}) or {}
    idx = pr.get("cmd_post_path_index_2co") or pr.get("cmd_post_path_index_2cn") or {}
    out = {
        "phase": "2co",
        "allow_post": False,
        "posting": "DISABLED",
        "tool_gate": pr.get("tool_gate") or "CLOSED_NOT_OPENED",
        "commands": {},
        "note": "Prefer higher post_path_confidence. Thin wrappers named via Capstone; do not Post.",
    }
    for n, meta in idx.items():
        if command_name and n != command_name:
            continue
        if role and meta.get("role") != role:
            continue
        out["commands"][n] = meta
    out["count"] = len(out["commands"])
    confs = [v.get("post_path_confidence") or 0 for v in out["commands"].values()]
    out["avg_post_path_confidence"] = round(sum(confs) / max(1, len(confs)), 3) if confs else 0
    out["cmds_below_0_9"] = sum(1 for c in confs if c < 0.9)
    out["fully_named_required_gates"] = sum(
        1 for v in out["commands"].values() if not v.get("unnamed_gates_remaining")
    )
    return out


def land_confidence_report_2co_recipe(role: str | None = None) -> dict:
    """Confidence report 2co + optional role filter. Docs only."""
    try:
        import cmd_layout as _cl
    except Exception as e:
        return {"error": str(e), "posting": "DISABLED", "allow_post": False}
    pr = getattr(_cl, "LAND_POST_READINESS", {}) or {}
    rep = dict(pr.get("confidence_report_2co") or {})
    matrix = pr.get("role_post_path_matrix_2co") or {}
    out = {
        "phase": "2co",
        "allow_post": False,
        "posting": "DISABLED",
        "report": rep,
        "role_slice": matrix.get(role) if role else None,
        "deep_thin_named": len(pr.get("deep_resolved_execute_helpers_2co") or {}),
        "note": "Capstone naming; SHARED helpers only grew via hits>=2; never Post.",
    }
    return out


def land_post_readiness_checklist_2co_recipe(command_name: str | None = None) -> dict:
    """2co checklist + optional cmd slice. ALLOW_POST remains False."""
    try:
        import cmd_layout as _cl
    except Exception as e:
        return {"error": str(e), "posting": "DISABLED", "allow_post": False}
    pr = getattr(_cl, "LAND_POST_READINESS", {}) or {}
    checklist = dict(pr.get("post_readiness_checklist_2co") or {})
    idx = pr.get("cmd_post_path_index_2co") or {}
    return {
        "phase": "2co",
        "allow_post": False,
        "posting": "DISABLED",
        "tool_gate": pr.get("tool_gate") or "CLOSED_NOT_OPENED",
        "checklist": checklist,
        "command_slice": idx.get(command_name) if command_name else None,
        "do_not": checklist.get("do_not") or [
            "enable ALLOW_POST", "patch/hook helpers", "Post inject",
            "HourlyTick / GameSpeed writes", "guess writes",
        ],
        "note": "Checklist for future Post readiness docs only.",
    }


# --- Phase 2cp: soft-6 Capstone structural close (READ-ONLY) ---

def land_cmd_post_path_index_2cp_recipe(command_name: str | None = None, role: str | None = None) -> dict:
    """Per-command Post readiness index 2cp. Docs only."""
    try:
        import cmd_layout as _cl
    except Exception as e:
        return {"error": str(e), "posting": "DISABLED", "allow_post": False}
    pr = getattr(_cl, "LAND_POST_READINESS", {}) or {}
    idx = pr.get("cmd_post_path_index_2cp") or pr.get("cmd_post_path_index_2co") or {}
    out = {
        "phase": "2cp",
        "allow_post": False,
        "posting": "DISABLED",
        "tool_gate": pr.get("tool_gate") or "CLOSED_NOT_OPENED",
        "commands": {},
        "note": "Below-0.9 closed via Capstone structural names. Do not Post.",
    }
    for n, meta in idx.items():
        if command_name and n != command_name:
            continue
        if role and meta.get("role") != role:
            continue
        out["commands"][n] = meta
    out["count"] = len(out["commands"])
    confs = [v.get("post_path_confidence") or 0 for v in out["commands"].values()]
    out["avg_post_path_confidence"] = round(sum(confs) / max(1, len(confs)), 3) if confs else 0
    out["cmds_below_0_9"] = sum(1 for c in confs if c < 0.9)
    out["fully_named_required_gates"] = sum(
        1 for v in out["commands"].values() if not v.get("unnamed_gates_remaining")
    )
    return out


def land_confidence_report_2cp_recipe(role: str | None = None) -> dict:
    """Confidence report 2cp + optional role filter. Docs only."""
    try:
        import cmd_layout as _cl
    except Exception as e:
        return {"error": str(e), "posting": "DISABLED", "allow_post": False}
    pr = getattr(_cl, "LAND_POST_READINESS", {}) or {}
    rep = dict(pr.get("confidence_report_2cp") or {})
    matrix = pr.get("role_post_path_matrix_2cp") or {}
    return {
        "phase": "2cp",
        "allow_post": False,
        "posting": "DISABLED",
        "report": rep,
        "role_slice": matrix.get(role) if role else None,
        "note": "SHARED helpers unchanged; structural Capstone names only; never Post.",
    }


def land_post_readiness_checklist_2cp_recipe(command_name: str | None = None) -> dict:
    """2cp checklist + optional cmd slice. ALLOW_POST remains False."""
    try:
        import cmd_layout as _cl
    except Exception as e:
        return {"error": str(e), "posting": "DISABLED", "allow_post": False}
    pr = getattr(_cl, "LAND_POST_READINESS", {}) or {}
    checklist = dict(pr.get("post_readiness_checklist_2cp") or {})
    idx = pr.get("cmd_post_path_index_2cp") or {}
    return {
        "phase": "2cp",
        "allow_post": False,
        "posting": "DISABLED",
        "tool_gate": pr.get("tool_gate") or "CLOSED_NOT_OPENED",
        "checklist": checklist,
        "command_slice": idx.get(command_name) if command_name else None,
        "do_not": checklist.get("do_not") or [
            "enable ALLOW_POST", "patch/hook helpers", "Post inject",
            "HourlyTick / GameSpeed writes", "guess writes",
        ],
        "note": "Checklist for future Post readiness docs only.",
    }

