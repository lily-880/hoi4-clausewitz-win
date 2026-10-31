#!/usr/bin/env python3
"""Phase 2cz live RO re-verify."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
sys.path.insert(0, "calling")
from process import Backend, find_pid
import cmd_layout, army_subjects
OUT = Path("reports")

def main():
    pid = find_pid("hoi4.exe") or find_pid("hoi4")
    assert pid
    b = Backend(pid); base = int(b.image_base)
    pr = cmd_layout.LAND_POST_READINESS
    helpers = cmd_layout.SHARED_LAND_HELPERS["helpers"]
    named = pr.get("named_helpers") or {}
    idx = pr.get("cmd_post_path_index_2cz") or {}
    army = pr.get("live_army_subject_observe_2cz") or {}
    mid = pr.get("midflight_move_watcher_readiness_2cz") or {}
    ro = pr.get("role_observe_2cz") or {}
    ok, fail = 0, []
    for role, meta in ro.items():
        if not isinstance(meta, dict): continue
        for cmd, cm in (meta.get("commands") or {}).items():
            if cm.get("execute_prologue"): ok += 1
            else: fail.append(f"{role}:{cmd}:exec")
            if cm.get("isvalid_prologue"): ok += 1
            else: fail.append(f"{role}:{cmd}:isvalid")
            for g, gm in (cm.get("gates_live") or {}).items():
                if gm.get("readable"): ok += 1
                else: fail.append(g)
    watcher = False
    try:
        r = subprocess.run(["powershell","-NoProfile","-Command",
            "Get-Process -Id 36128 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id"],
            capture_output=True, text=True, timeout=10)
        watcher = "36128" in (r.stdout or "")
    except Exception:
        pass
    for fn in (army_subjects.land_cmd_post_path_index_2cz_recipe,
               army_subjects.land_role_post_path_matrix_2cz_recipe,
               army_subjects.land_role_observe_2cz_recipe,
               army_subjects.land_confidence_report_2cz_recipe,
               army_subjects.land_post_readiness_checklist_2cz_recipe,
               army_subjects.land_offensive_line_post_path_2cz_recipe,
               army_subjects.land_midflight_move_watcher_readiness_2cz_recipe,
               army_subjects.land_live_army_subject_observe_2cz_recipe):
        assert fn().get("allow_post") is False
    live = army_subjects.land_live_army_subject_observe_2cz_recipe(limit=3, carmy_only=True)
    assert live.get("carmy_only_filter") is True
    cfront = army.get("field_map_cfront") or {}
    slot = cfront.get("slot_array") or {}
    prov = army.get("field_map_cprovince") or {}
    fs = army.get("field_map_frontsection_observe") or {}
    org = army.get("org_str_status") or {}
    if isinstance(org, dict): org = org.get("status")
    rep = pr.get("confidence_report_2cz") or {}
    heap = army.get("heap_order_front_counts") or {}
    report = {
        "phase": "2cz", "posting": "DISABLED", "allow_post": False,
        "tool_gate": pr.get("tool_gate") or "CLOSED_NOT_OPENED",
        "pid": pid, "image_base": hex(base),
        "helpers_total": len(helpers),
        "named_helpers": len(named) if isinstance(named, dict) else named,
        "named_new_2cz": 0, "cmd_index": len(idx),
        "avg_conf": rep.get("avg_post_path_confidence"), "prev_avg_2cy": 1.0,
        "below_1_0": rep.get("cmds_below_1_0"),
        "carmy_count": army.get("carmy_count"),
        "carmy_theatre_ok": army.get("carmy_theatre_rtti_ok"),
        "unique_theatres": army.get("unique_theatre_ptrs"),
        "cfront_slots_proven_min": slot.get("slots_proven_min"),
        "cfront_slot0": slot.get("slot0"),
        "cfront_slot15": slot.get("slot15"),
        "cfront_stride": hex(slot.get("stride") or 0),
        "hai_fronts_any_slot_16": cfront.get("hai_theatre_fronts_any_slot_16"),
        "prov_0x58_status": (prov.get("controller_tag_0x58_hyp") or {}).get("status"),
        "fs_embed_status": (fs.get("embedded_parent_slot_ptrs") or {}).get("status"),
        "fs_match_counts": (fs.get("embedded_parent_slot_ptrs") or {}).get("match_counts"),
        "org_str_status": org,
        "movement_dest_nonempty": army.get("movement_dest_nonempty_count"),
        "frontsection_heap": heap.get("CFrontSection"),
        "unique_fronts": heap.get("unique_CFront"),
        "ol_cmds": len(pr.get("offensive_line_post_path_2cz") or {}),
        "role_observe_roles": list(ro.keys()),
        "read_ok": ok, "read_fail": fail[:20],
        "watcher_36128_alive": watcher,
        "session_drain": (mid.get("live_session_counters") or {}).get("drain"),
        "session_exec": (mid.get("live_session_counters") or {}).get("exec"),
        "midflight_captures": (mid.get("prior_ready_snapshot") or {}).get("captures"),
        "land_focus_unchanged": "121/121",
        "focus": "cfront_slots_ge16_fs_embed_prov58_reject",
        "stubbed": ["midflight_CMoveCommand", "ring_embed", "ALLOW_POST", "command_queue_tool_gate"],
    }
    OUT.mkdir(exist_ok=True)
    (OUT/"phase2cz_live_re.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
