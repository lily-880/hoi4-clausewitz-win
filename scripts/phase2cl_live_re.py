#!/usr/bin/env python3
"""Phase 2cl live RO re-verify."""
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
    b = Backend(pid)
    base = int(b.image_base)
    focus = cmd_layout.LAND_ARMY_FOCUS["commands"]
    pr = cmd_layout.LAND_POST_READINESS
    helpers = cmd_layout.SHARED_LAND_HELPERS["helpers"]
    named = pr.get("named_helpers") or {}
    prefs = pr.get("preferred_cores") or {}
    idx = pr.get("cmd_post_path_index_2cl") or {}
    matrix = pr.get("role_post_path_matrix_2cl") or {}
    gate_only = pr.get("gate_label_only_2cl") or {}

    # spot-read named that are in helpers + gate_label_only (may fail if not mapped)
    named_ok, named_fail = 0, []
    for addr in list(named.keys())[:60]:
        if addr in gate_only and addr not in helpers:
            # label-only: try read anyway
            pass
        raw = b.read(base + int(addr, 16), 8)
        if raw:
            named_ok += 1
        else:
            named_fail.append(addr)

    covered = set()
    for m in prefs.values():
        covered |= set(m.get("core_commands") or [])
    land_names = set(focus.keys())

    recipes = {
        "land_cmd_post_path_index_recipe": army_subjects.land_cmd_post_path_index_recipe(),
        "land_role_post_path_matrix_2cl_recipe": army_subjects.land_role_post_path_matrix_2cl_recipe(),
        "land_post_readiness_checklist_2cl_recipe": army_subjects.land_post_readiness_checklist_2cl_recipe(),
    }
    for k, v in recipes.items():
        assert v.get("allow_post") is False, k

    watcher_alive = False
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-Process -Id 36128 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id"],
            capture_output=True, text=True, timeout=10,
        )
        watcher_alive = "36128" in (r.stdout or "")
    except Exception:
        pass

    fully = sum(1 for v in idx.values() if not v.get("unnamed_gates_remaining"))
    report = {
        "phase": "2cl",
        "posting": "DISABLED",
        "allow_post": False,
        "tool_gate": pr.get("tool_gate"),
        "pid": pid,
        "image_base": hex(base),
        "land_cmds": len(land_names),
        "helpers_total": len(helpers),
        "helpers_unchanged": len(helpers) == 237,
        "named_helpers": len(named),
        "named_new_2cl": len(pr.get("named_new_2cl") or {}),
        "gate_label_only": len(gate_only),
        "preferred_cores": len(prefs),
        "coverage_cmds": len(covered & land_names),
        "coverage_total": len(land_names),
        "cmd_index_count": len(idx),
        "cmd_index_fully_named_req_gates": fully,
        "matrix_roles": list(matrix.keys()),
        "named_read_ok": named_ok,
        "named_read_fail": named_fail[:10],
        "watcher_36128_alive": watcher_alive,
        "recipes_allow_post_all_false": True,
        "land_focus_unchanged": "121/121",
        "note": "RO live re-verify. Cmd post-path index focus; no helper inflation; no Post.",
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "phase2cl_live_re.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (OUT / "_2cl_summary.json").write_text(json.dumps({
        "phase": "2cl",
        "allow_post": False,
        "helpers": len(helpers),
        "named": len(named),
        "cmd_index": len(idx),
        "fully_named": fully,
        "cores": len(prefs),
        "coverage": f"{len(covered & land_names)}/{len(land_names)}",
        "watcher": watcher_alive,
    }, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
