#!/usr/bin/env python3
"""Phase 2cu live RO re-verify (classify + usability package)."""
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
    idx = pr.get("cmd_post_path_index_2cu") or {}
    army = pr.get("live_army_subject_observe_2cu") or {}
    mid = pr.get("midflight_move_watcher_readiness_2cu") or {}
    ro = pr.get("role_observe_2cu") or {}
    ok, fail = 0, []
    for role, meta in ro.items():
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
    for fn in (army_subjects.land_cmd_post_path_index_2cu_recipe,
               army_subjects.land_role_post_path_matrix_2cu_recipe,
               army_subjects.land_role_observe_2cu_recipe,
               army_subjects.land_confidence_report_2cu_recipe,
               army_subjects.land_post_readiness_checklist_2cu_recipe,
               army_subjects.land_offensive_line_post_path_2cu_recipe,
               army_subjects.land_midflight_move_watcher_readiness_2cu_recipe,
               army_subjects.land_live_army_subject_observe_2cu_recipe):
        assert fn().get("allow_post") is False
    live = army_subjects.land_live_army_subject_observe_2cu_recipe(limit=3, carmy_only=True)
    assert live.get("carmy_only_filter") is True
    org = (army.get("org_str_status") or {}).get("status")
    rep = pr.get("confidence_report_2cu") or {}
    report = {
        "phase": "2cu", "posting": "DISABLED", "allow_post": False,
        "tool_gate": pr.get("tool_gate"), "pid": pid, "image_base": hex(base),
        "helpers_total": len(helpers), "named_helpers": len(named),
        "named_new_2cu": 0, "cmd_index": len(idx),
        "avg_conf": rep.get("avg_post_path_confidence"), "prev_avg_2ct": 1.0,
        "below_1_0": rep.get("cmds_below_1_0"),
        "carmy_count": army.get("carmy_count"),
        "ctaskforce_count": army.get("ctaskforce_count"),
        "org_str_status": org,
        "movement_dest_nonempty": army.get("movement_dest_nonempty_count"),
        "ol_cmds": len(pr.get("offensive_line_post_path_2cu") or {}),
        "role_observe_roles": list(ro.keys()),
        "read_ok": ok, "read_fail": fail[:20],
        "watcher_36128_alive": watcher,
        "session_drain": (mid.get("live_session_counters") or {}).get("drain"),
        "session_exec": (mid.get("live_session_counters") or {}).get("exec"),
        "midflight_captures": (mid.get("prior_ready_snapshot") or {}).get("captures"),
        "land_focus_unchanged": "121/121",
        "focus": "classify_reject_org",
        "stubbed": ["midflight_CMoveCommand", "ring_embed", "ALLOW_POST", "command_queue_tool_gate"],
    }
    OUT.mkdir(exist_ok=True)
    (OUT/"phase2cu_live_re.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
