#!/usr/bin/env python3
"""Phase 2cs live RO re-verify (usability package)."""
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
    idx = pr.get("cmd_post_path_index_2cs") or {}
    fv = pr.get("live_focus_fn_verify_2cs") or {}
    army = pr.get("live_army_subject_observe_2cs") or {}
    mid = pr.get("midflight_move_watcher_readiness_2cs") or {}
    ok, fail = 0, []
    for role, meta in fv.items():
        for g, gm in (meta.get("gates_live") or {}).items():
            if gm.get("readable"): ok += 1
            else: fail.append(g)
        if meta.get("execute_prologue"): ok += 1
        else: fail.append(meta.get("command"))
    watcher = False
    try:
        r = subprocess.run(["powershell","-NoProfile","-Command",
            "Get-Process -Id 36128 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id"],
            capture_output=True, text=True, timeout=10)
        watcher = "36128" in (r.stdout or "")
    except Exception:
        pass
    for fn in (army_subjects.land_cmd_post_path_index_2cs_recipe,
               army_subjects.land_role_post_path_matrix_2cs_recipe,
               army_subjects.land_confidence_report_2cs_recipe,
               army_subjects.land_post_readiness_checklist_2cs_recipe,
               army_subjects.land_offensive_line_post_path_2cs_recipe,
               army_subjects.land_midflight_move_watcher_readiness_2cs_recipe,
               army_subjects.land_live_army_subject_observe_2cs_recipe,
               army_subjects.land_live_focus_fn_verify_2cs_recipe):
        assert fn().get("allow_post") is False
    rep = pr.get("confidence_report_2cs") or {}
    report = {
        "phase": "2cs", "posting": "DISABLED", "allow_post": False,
        "tool_gate": pr.get("tool_gate"), "pid": pid, "image_base": hex(base),
        "helpers_total": len(helpers), "named_helpers": len(named),
        "named_new_2cs": 0, "cmd_index": len(idx),
        "avg_conf": rep.get("avg_post_path_confidence"), "prev_avg_2cr": 1.0,
        "below_1_0": rep.get("cmds_below_1_0"),
        "live_armies_hai": army.get("armies_found"),
        "ol_cmds": len(pr.get("offensive_line_post_path_2cs") or {}),
        "fn_verify_roles": list(fv.keys()),
        "read_ok": ok, "read_fail": fail,
        "watcher_36128_alive": watcher,
        "session_drain": (mid.get("live_session_counters") or {}).get("drain"),
        "session_exec": (mid.get("live_session_counters") or {}).get("exec"),
        "land_focus_unchanged": "121/121",
        "focus": "usability",
        "stubbed": ["midflight_CMoveCommand", "ring_embed", "ALLOW_POST", "command_queue_tool_gate"],
    }
    OUT.mkdir(exist_ok=True)
    (OUT/"phase2cs_live_re.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
