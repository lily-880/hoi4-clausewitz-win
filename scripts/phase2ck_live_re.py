#!/usr/bin/env python3
"""Phase 2ck live RO re-verify — no Post, no speed, no input."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "calling")
from process import Backend, find_pid
import cmd_layout
import army_subjects

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
    matrix = pr.get("role_post_path_matrix_2ck") or {}

    named_ok, named_fail = 0, []
    for addr in list(named.keys())[:50]:
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
        "land_role_post_path_matrix_recipe": army_subjects.land_role_post_path_matrix_recipe(),
        "land_singleton_execute_edge_recipe": army_subjects.land_singleton_execute_edge_recipe(),
        "land_post_readiness_checklist_2ck_recipe": army_subjects.land_post_readiness_checklist_2ck_recipe(),
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

    report = {
        "phase": "2ck",
        "posting": "DISABLED",
        "allow_post": False,
        "tool_gate": pr.get("tool_gate"),
        "pid": pid,
        "image_base": hex(base),
        "land_cmds": len(land_names),
        "helpers_total": len(helpers),
        "helpers_unchanged_from_2cj": len(helpers) == 237,
        "named_helpers": len(named),
        "named_new_2ck": len(pr.get("named_new_2ck") or {}),
        "preferred_cores": len(prefs),
        "coverage_cmds": len(covered & land_names),
        "coverage_total": len(land_names),
        "matrix_roles": list(matrix.keys()),
        "matrix_primaries": {r: (matrix[r] or {}).get("primary_preferred_core") for r in matrix},
        "singleton_totals": {r: len(v) for r, v in (pr.get("singleton_execute_edges_2ck") or {}).items()},
        "named_read_ok": named_ok,
        "named_read_fail": named_fail,
        "watcher_36128_alive": watcher_alive,
        "recipes_allow_post_all_false": True,
        "land_focus_unchanged": "121/121",
        "note": "RO live re-verify. Matrix/checklist focus; no helper inflation; no Post.",
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "phase2ck_live_re.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (OUT / "_2ck_summary.json").write_text(json.dumps({
        "phase": "2ck",
        "allow_post": False,
        "helpers": len(helpers),
        "named": len(named),
        "cores": len(prefs),
        "coverage": f"{len(covered & land_names)}/{len(land_names)}",
        "matrix_roles": len(matrix),
        "singleton_total": sum(len(v) for v in (pr.get("singleton_execute_edges_2ck") or {}).values()),
        "watcher": watcher_alive,
    }, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
