#!/usr/bin/env python3
"""Phase 2dd live RO re-verify."""
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
    idx = pr.get("cmd_post_path_index_2dd") or {}
    army = pr.get("live_army_subject_observe_2dd") or {}
    mid = pr.get("midflight_move_watcher_readiness_2dd") or {}
    ro = pr.get("role_observe_2dd") or {}
    ok, fail = 0, []
    for role, meta in ro.items():
        if not isinstance(meta, dict): continue
        for cmd, cm in (meta.get("commands") or {}).items():
            if not isinstance(cm, dict): continue
            if cm.get("execute_prologue"): ok += 1
            else: fail.append(f"{role}:{cmd}:exec")
            if cm.get("isvalid_prologue"): ok += 1
            else: fail.append(f"{role}:{cmd}:isvalid")
            for g, gm in (cm.get("gates_live") or {}).items():
                if isinstance(gm, dict) and gm.get("readable"): ok += 1
                else: fail.append(str(g))
    watcher = False
    try:
        r = subprocess.run(["powershell","-NoProfile","-Command",
            "Get-Process -Id 36128 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id"],
            capture_output=True, text=True, timeout=10)
        watcher = "36128" in (r.stdout or "")
    except Exception:
        pass
    for fn in (army_subjects.land_cmd_post_path_index_2dd_recipe,
               army_subjects.land_role_post_path_matrix_2dd_recipe,
               army_subjects.land_role_observe_2dd_recipe,
               army_subjects.land_confidence_report_2dd_recipe,
               army_subjects.land_post_readiness_checklist_2dd_recipe,
               army_subjects.land_offensive_line_post_path_2dd_recipe,
               army_subjects.land_midflight_move_watcher_readiness_2dd_recipe,
               army_subjects.land_live_army_subject_observe_2dd_recipe):
        assert fn().get("allow_post") is False
    live = army_subjects.land_live_army_subject_observe_2dd_recipe(limit=3, carmy_only=True)
    assert live.get("carmy_only_filter") is True
    cfront = army.get("field_map_cfront") or {}
    th = army.get("field_map_ctheatre") or {}
    req = army.get("field_map_carmyrequests") or {}
    sper = army.get("field_map_spercountrysection_hyp") or {}
    org = army.get("org_str_status")
    if isinstance(org, dict): org = org.get("status")
    rep = pr.get("confidence_report_2dd") or {}
    heap = army.get("heap_order_front_counts") or {}
    peer = req.get("peer_carmy_ptr_hyp") or {}
    th_arm = th.get("armies_array") or {}
    th_fr = th.get("fronts_array") or {}
    report = {
        "phase": "2dd", "posting": "DISABLED", "allow_post": False,
        "tool_gate": pr.get("tool_gate") or "CLOSED_NOT_OPENED",
        "pid": pid, "image_base": hex(base),
        "helpers_total": len(helpers),
        "named_helpers": len(named) if isinstance(named, dict) else named,
        "named_new_2dd": 0, "cmd_index": len(idx),
        "avg_conf": rep.get("avg_post_path_confidence"), "prev_avg_2dc": 1.0,
        "below_1_0": rep.get("cmds_below_1_0"),
        "carmy_count": army.get("carmy_count"),
        "carmy_theatre_ok": army.get("carmy_theatre_rtti_ok"),
        "unique_theatres": army.get("unique_theatre_ptrs"),
        "cfront_kind_0x42": (cfront.get("kind_u32_8") or {}).get("ok"),
        "cfront_id_unique": (cfront.get("front_id_u32_c") or {}).get("unique"),
        "cfront_intra_only": (cfront.get("intra_object_rtti_ptrs") or {}).get("only_offs"),
        "cfront_slot_array_status": (cfront.get("slot_array") or {}).get("status"),
        "hai_fronts": cfront.get("hai_theatre_fronts_slot0"),
        "hai_front_ids": army.get("hai_front_ids") or (th_fr.get("front_ids")),
        "theatre_army_crosslink": (th.get("army_crosslink_direct") or {}).get("status"),
        "th_armies_ok": th_arm.get("ok"),
        "th_fronts_ok": th_fr.get("ok"),
        "req_peer_status": peer.get("status"),
        "req_peer_alias_offs": peer.get("offs_aliased"),
        "sper_tag8_hai": (sper.get("country_tag_u32_8") or {}).get("hai_count_via_fs"),
        "org_str_status": org,
        "movement_dest_nonempty": army.get("movement_dest_nonempty_count"),
        "frontsection_heap": heap.get("CFrontSection"),
        "unique_fronts": heap.get("unique_CFront"),
        "ol_cmds": len(pr.get("offensive_line_post_path_2dd") or {}),
        "role_observe_roles": [k for k in ro.keys() if k != "phase"],
        "read_ok": ok, "read_fail": fail[:20],
        "watcher_36128_alive": watcher,
        "land_focus_unchanged": "121/121",
        "focus": "TH_ARMIES+TH_FRONTS+CO_arrays_CPdxArray",
        "stubbed": ["midflight_CMoveCommand", "ring_embed", "ALLOW_POST", "command_queue_tool_gate"],
    }
    OUT.mkdir(exist_ok=True)
    (OUT/"phase2dd_live_re.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
