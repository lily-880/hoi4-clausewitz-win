#!/usr/bin/env python3
"""Phase 2cf — RO full land EXE proofs + order-group/offensive-line execution.

Never posts. Never opens command_queue_tool_gate. Never touches speed/HourlyTick/Pause.
Midflight Move remains stubbed; watcher stays armed separately. No input injection.
"""
from __future__ import annotations
import json, struct, sys, subprocess, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

from process import Backend, find_pid  # noqa: E402
import cmd_layout, post_abi, army_subjects  # noqa: E402
from config import allow_post  # noqa: E402

OUT = ROOT / "reports" / "phase2cf_live_re.json"


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u8(b, a):
    return b.read(a, 1)[0]


def kind(b, base, rva):
    blob = b.read(base + rva, 0x20)
    if blob[0:3] == b"\xb0\x01\xc3":
        return "TRUE"
    if blob[0:3] in (b"\x32\xc0\xc3", b"\x33\xc0\xc3", b"\x31\xc0\xc3"):
        return "FALSE"
    return "FN"


def factory_idx(tid):
    ft = cmd_layout.FACTORY_TABLE
    return tid - ft["index_bias"] if tid >= ft["index_bias_sub_if_ge"] else tid


def factory_fn(b, base, tid):
    i = factory_idx(tid)
    if i < 0 or i > cmd_layout.FACTORY_TABLE["max_index"]:
        return 0
    slot = u64(b, base + cmd_layout.FACTORY_TABLE["rva"] + i * 8)
    return (slot - base) if slot else 0


def watcher_alive():
    try:
        out = subprocess.check_output(
            [
                "powershell", "-NoProfile", "-Command",
                "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' "
                "-and $_.CommandLine -match 'midflight' } | Select-Object -ExpandProperty ProcessId",
            ],
            text=True, errors="ignore", timeout=15,
        )
        pids = [int(x) for x in out.split() if x.strip().isdigit()]
        return {"alive": bool(pids), "pids": pids}
    except Exception as e:
        return {"alive": None, "error": str(e)}


def resolve_meta(name, meta):
    m = dict(meta)
    if "vt" in m and "type_id" in m:
        return m
    alias = m.get("layout_alias")
    src = None
    if alias == "EXTRA_ARMY_COMMANDS":
        src = cmd_layout.EXTRA_ARMY_COMMANDS.get(name)
    elif alias == "REMAINING_ARMY_ORDERS":
        src = cmd_layout.REMAINING_ARMY_ORDERS.get(name)
    elif alias == "ORDERS":
        src = cmd_layout.ORDERS.get(name)
    if src:
        m = {**src, **m}
    # also from EXE proofs
    if name in cmd_layout.LAND_EXE_PROOFS["commands"]:
        p = cmd_layout.LAND_EXE_PROOFS["commands"][name]
        m.setdefault("vt", p.get("vt"))
        m.setdefault("type_id", p.get("type_id"))
        m.setdefault("isvalid", p.get("isvalid"))
        m.setdefault("execute", p.get("execute"))
    return m


def verify_cmd(b, base, name, meta):
    m = resolve_meta(name, meta)
    vt, tid = m.get("vt"), m.get("type_id")
    entry = {"name": name, "role": m.get("role")}
    if not vt:
        return {**entry, "ok": False, "err": "no_vt"}
    live_isv = u64(b, base + vt + 0x48) - base
    live_exe = u64(b, base + vt + 0x50) - base
    entry.update({
        "vt": hex(vt),
        "type_id": hex(tid) if tid else None,
        "isvalid_live": hex(live_isv),
        "isvalid_kind": kind(b, base, live_isv),
        "execute_live": hex(live_exe),
        "execute_kind": kind(b, base, live_exe),
    })
    if "isvalid" in m:
        entry["isvalid_match"] = live_isv == m["isvalid"]
    if "execute" in m:
        entry["execute_match"] = live_exe == m["execute"]
    if tid and "factory" in m:
        fac = factory_fn(b, base, tid)
        entry["factory_live"] = hex(fac)
        entry["factory_match"] = fac == m["factory"]
    entry["ok"] = (
        entry["isvalid_kind"] == "FN"
        and entry["execute_kind"] == "FN"
        and entry.get("isvalid_match", True)
        and entry.get("execute_match", True)
        and entry.get("factory_match", True)
    )
    return entry


def verify_map(b, base, mapping, resolve=True):
    out, ok = {}, 0
    for name, meta in mapping.items():
        entry = verify_cmd(b, base, name, meta if resolve else meta)
        out[name] = entry
        if entry.get("ok"):
            ok += 1
    return {"ok": ok, "total": len(out), "commands": out}


def verify_exe_proofs(b, base):
    out, ok = {}, 0
    for name, meta in cmd_layout.LAND_EXE_PROOFS["commands"].items():
        live_exe = kind(b, base, meta["execute"])
        live_isv = kind(b, base, meta["isvalid"])
        # also check vt slots if present
        vt_ok = True
        if "vt" in meta:
            slot_exe = u64(b, base + meta["vt"] + 0x50) - base
            slot_isv = u64(b, base + meta["vt"] + 0x48) - base
            vt_ok = slot_exe == meta["execute"] and slot_isv == meta["isvalid"]
        entry = {
            "execute": hex(meta["execute"]),
            "execute_kind_live": live_exe,
            "isvalid": hex(meta["isvalid"]),
            "isvalid_kind_live": live_isv,
            "vt_slots_match": vt_ok,
            "field_map": {k: hex(v) if isinstance(v, int) else v for k, v in meta.get("field_map", {}).items()},
            "ok": live_exe == "FN" and live_isv == "FN" and vt_ok,
        }
        if entry["ok"]:
            ok += 1
        out[name] = entry
    return {"ok": ok, "total": len(out), "commands": out}


def hai_recipes(b, base):
    rows = army_subjects.iter_armies_by_index(b, base, country_tag=15)[:3]
    out = []
    for r in rows:
        dest = (r["province_id"] + 1) & 0xFFFF
        og = [0, 1]  # placeholder order-group handle
        out.append({
            "handle": list(r["handle"]),
            "province_id": r["province_id"],
            "move": army_subjects.move_action_recipe(r),
            "strategic": army_subjects.strategic_redeploy_recipe(r, dest),
            "support_attack": army_subjects.support_attack_recipe(r, dest),
            "cancel": army_subjects.cancel_movement_recipe([r]),
            "mass_cancel": army_subjects.mass_cancel_movement_recipe([r]),
            "fallback": army_subjects.fallback_order_recipe(1),
            "new_front": army_subjects.new_front_recipe([list(r["handle"])]),
            "set_path": army_subjects.set_path_recipe(1),
            "set_collapse": army_subjects.set_collapse_recipe([0, 1]),
            "order_execute": army_subjects.order_execute_recipe(),
            "assign_theater": army_subjects.assign_theater_group_recipe(list(r["handle"]), 1),
            "exec_type": army_subjects.set_order_group_execution_type_recipe(og, 1),
            "cohesion": army_subjects.set_order_group_cohesion_recipe(og, 0),
            "assign_army_group": army_subjects.assign_to_army_group_recipe(list(r["handle"]), og),
            "order_assign": army_subjects.order_assign_recipe(og),
            "collapse_conveyor": army_subjects.collapse_conveyor_recipe(og),
            "delete_order_group": army_subjects.delete_order_group_recipe(og),
            "order_delete": army_subjects.order_delete_recipe(0),
            "order_delete_all": army_subjects.order_delete_all_recipe(og),
            "auto_merge": army_subjects.auto_merge_orders_recipe(og),
            "icon": army_subjects.set_order_group_icon_recipe(og, 0),
            "set_army_leader": army_subjects.set_army_leader_recipe(list(r["handle"]), 0),
            "set_army_template": army_subjects.set_army_template_recipe(list(r["handle"]), 0),
            "railway_gun": army_subjects.railway_gun_manual_order_recipe(list(r["handle"]), dest),
            "deploy_hq": army_subjects.deploy_army_hq_recipe(list(r["handle"]), 0),
            "mass_move": army_subjects.mass_move_recipe([r], dest),
            "toggle_strategic": army_subjects.toggle_strategic_deployment_recipe(list(r["handle"])),
            "edit_root": army_subjects.order_edit_root_recipe(og),
            "merge_roots": army_subjects.order_merge_roots_recipe(og),
            "block_sections": army_subjects.order_block_sections_recipe(og),
            "invasion_source": army_subjects.order_set_invasion_source_recipe(og, 0),
            "create_conveyor": army_subjects.create_conveyor_recipe(og),
            "deploy_conveyor": army_subjects.deploy_conveyor_recipe(og),
            "orders_link": army_subjects.set_orders_link_recipe(og, 0),
            "leader_tactic": army_subjects.set_army_leader_preferred_tactic_recipe(list(r["handle"]), 0),
            "insert_front": army_subjects.insert_front_recipe(og),
            "reshape_front": army_subjects.reshape_front_recipe(og),
            "connect_front": army_subjects.connect_front_recipe(og),
            "complete_plan": army_subjects.add_complete_plan_recipe(og),
            "garrison_template": army_subjects.garrison_template_recipe(15, 0, "country"),
            "motorization": army_subjects.set_order_group_motorization_recipe(og, 0),
            "og_name": army_subjects.set_order_group_name_recipe(og, ""),
            "proximity": army_subjects.set_order_group_proximity_recipe(og, 0),
            "unassign": army_subjects.order_unassign_recipe([list(r["handle"])], 0),
            "paradrop_target": army_subjects.order_set_paradrop_recipe(og, dest, "target"),
            "training": army_subjects.order_set_training_recipe(og, 1),
            "remove_army_group": army_subjects.remove_from_army_group_recipe(list(r["handle"]), og),
            "disband_theater": army_subjects.disband_theater_group_recipe(og),
            "reorder_theaters": army_subjects.reorder_theaters_recipe([1, 2]),
            "conveyor_priority": army_subjects.set_conveyor_field_recipe(og, "priority", 0),
            "remove_conveyor": army_subjects.remove_conveyor_recipe(og),
            "learn_trait": army_subjects.learn_trait_recipe(list(r["handle"]), 0),
            "repair_order": army_subjects.set_repair_order_recipe(list(r["handle"]), 1),
            "division_name": army_subjects.set_division_name_recipe(list(r["handle"]), ""),
            "upgrade_officer": army_subjects.upgrade_division_officer_recipe(list(r["handle"]), 0),
            "build_railway": army_subjects.build_railway_recipe(list(r["handle"])),
            "merge_armies": army_subjects.merge_armies_recipe(list(r["handle"]), list(r["handle"])),
            "delete_unit": army_subjects.delete_unit_recipe(list(r["handle"])),
            "transport_unit": army_subjects.transport_unit_recipe(list(r["handle"]), dest),
            "set_theatre": army_subjects.set_theatre_recipe(list(r["handle"]), 0),
            "set_unit_name": army_subjects.set_unit_name_recipe(list(r["handle"]), ""),
            "preferred_tactic": army_subjects.set_preferred_tactic_recipe(list(r["handle"]), 0),
            "area_defense": army_subjects.area_defense_recipe(list(r["handle"]), "create", 0),
            "pinned_strategic": army_subjects.pinned_strategic_region_recipe(0, "toggle"),
            "selection_group": army_subjects.selection_group_recipe([list(r["handle"])]),
            "queue_unit_action": army_subjects.queue_unit_action_recipe(list(r["handle"]), 0),
            "promote_leader": army_subjects.promote_unit_leader_recipe(list(r["handle"])),
            "create_leader": army_subjects.create_unit_leader_recipe(list(r["handle"]), 0),
            "pending_reassign": army_subjects.pending_reassign_target_recipe(list(r["handle"]), dest),
            "clear_repair_pins": army_subjects.clear_repair_pins_recipe(list(r["handle"])),
            "expeditionaries": army_subjects.request_expeditionaries_recipe(list(r["handle"]), 0),
            "give_medal": army_subjects.give_medal_recipe(list(r["handle"]), 0),
            "trigger_ability": army_subjects.trigger_ability_recipe(list(r["handle"]), 0),
            "retire_character": army_subjects.retire_character_recipe(list(r["handle"])),
            "reinstate_exile": army_subjects.reinstate_exile_recipe(list(r["handle"])),
            "foreign_manpower": army_subjects.amend_foreign_manpower_recipe(list(r["handle"]), 0),
            "ai_wanted_divs": army_subjects.ai_store_wanted_divisions_recipe(list(r["handle"]), 0),
            "country_reinforce_prio": army_subjects.country_reinforcement_priority_recipe(15, 0),
            "ai_force_conc": army_subjects.ai_force_concentration_recipe(list(r["handle"]), "store", dest),
            "post_readiness": army_subjects.land_post_readiness_recipe(),
            "role_post_path_move": army_subjects.land_role_post_path_recipe("move"),
            "role_post_path_theater": army_subjects.theater_role_post_path_recipe(),
            "role_post_path_order_group": army_subjects.order_group_role_post_path_recipe(),
            "role_post_path_garrison": army_subjects.garrison_role_post_path_recipe(),
            "exe_shared_unknown": army_subjects.land_execute_shared_unknown_recipe(8),
            "move_command": army_subjects.move_command_recipe(r, dest),
            "order_reconnect": army_subjects.order_reconnect_recipe(0, 0, 0),
            "replace_fallback": army_subjects.replace_fallback_recipe([list(r["handle"])], dest),
        })
    return out


def main():
    assert not allow_post(), "ALLOW_POST must stay False"
    pid = find_pid("hoi4.exe") or find_pid("hoi4")
    b = Backend(pid)
    base = int(b.image_base)
    t0 = time.time()
    sess = u64(b, base + post_abi.G_SESSION)

    land = verify_map(b, base, cmd_layout.LAND_ARMY_FOCUS["commands"])
    proofs = verify_exe_proofs(b, base)

    report = {
        "phase": "2cf",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "pid": pid,
        "image_base": hex(base),
        "posting": "DISABLED",
        "focus": "Execute-shared unknowns + theater/order_group/garrison role paths (RO)",
        "land_focus": {"ok": land["ok"], "total": land["total"], "commands": land["commands"]},
        "exe_proofs": proofs,
        "isvalid_paths_count": len(cmd_layout.ISVALID_PATHS),
        "groups": {k: v for k, v in cmd_layout.LAND_ARMY_FOCUS.items() if k.endswith("_group")},
        "hai_recipes": hai_recipes(b, base),
        "isvalid_notes": army_subjects.isvalid_path_notes(),
        "hygiene": {
            "sess": hex(sess),
            "tick_725": u8(b, sess + 0x725),
            "allow_post": bool(allow_post()),
        },
        "watcher": watcher_alive(),
        "shared_helpers": len(getattr(cmd_layout, "SHARED_LAND_HELPERS", {}).get("helpers") or {}),
        "post_readiness_phase": (getattr(cmd_layout, "LAND_POST_READINESS", {}) or {}).get("phase"),
        "named_helpers": len((getattr(cmd_layout, "LAND_POST_READINESS", {}) or {}).get("named_helpers") or {}),
        "second_order_hot": (getattr(cmd_layout, "LAND_POST_READINESS", {}) or {}).get("second_order_helper_count"),
        "execute_shared_unknown": (getattr(cmd_layout, "LAND_POST_READINESS", {}) or {}).get("execute_shared_unknown_count"),
        "helpers_total": (getattr(cmd_layout, "LAND_POST_READINESS", {}) or {}).get("helpers_total"),
        "by_tier": (getattr(cmd_layout, "LAND_POST_READINESS", {}) or {}).get("by_tier"),
        "role_post_paths": list(((getattr(cmd_layout, "LAND_POST_READINESS", {}) or {}).get("role_post_paths") or {}).keys()),
        "isvalid_gate_helpers": len((getattr(cmd_layout, "LAND_POST_READINESS", {}) or {}).get("isvalid_gate_helpers") or {}),
        "execute_body_helpers": len((getattr(cmd_layout, "LAND_POST_READINESS", {}) or {}).get("execute_body_helpers") or {}),
        "tool_gate_status": getattr(cmd_layout, "TOOL_GATE_PREDICATES", {}).get(
            "status", getattr(cmd_layout, "TOOL_GATE_PREDICATES", {}).get("verdict", "CLOSED_NOT_OPENED")
        ),
        "stubbed": [
            "midflight_CMoveCommand",
            "in_process_ring_embed",
            "command_queue_tool_gate_enable",
            "ALLOW_POST",
        ],
        "elapsed_s": round(time.time() - t0, 3),
    }
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps({
        "phase": "2cf",
        "land_focus": f"{land['ok']}/{land['total']}",
        "exe_proofs": f"{proofs['ok']}/{proofs['total']}",
        "isvalid_paths": report["isvalid_paths_count"],
        "hai": len(report["hai_recipes"]),
        "allow_post": report["hygiene"]["allow_post"],
        "tick_725": report["hygiene"]["tick_725"],
        "watcher": report["watcher"],
        "groups": {k: len(v) for k, v in report["groups"].items()},
        "failed_focus": [n for n, e in land["commands"].items() if not e.get("ok")],
        "failed_proofs": [n for n, e in proofs["commands"].items() if not e.get("ok")],
        "out": str(OUT),
    }, indent=2))


if __name__ == "__main__":
    main()
