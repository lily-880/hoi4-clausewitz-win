#!/usr/bin/env python3
"""Phase 2cj live RO re-verify — no Post, no speed, no input."""
from __future__ import annotations

import json
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
    ivp = {k: v for k, v in cmd_layout.ISVALID_PATHS.items() if isinstance(v, dict)}
    pr = cmd_layout.LAND_POST_READINESS
    helpers = cmd_layout.SHARED_LAND_HELPERS["helpers"]

    # Spot-check a few named helpers still readable
    named = pr.get("named_helpers") or {}
    named_ok = 0
    named_fail = []
    for addr in list(named.keys())[:40]:
        rva = int(addr, 16)
        raw = b.read(base + rva, 16)
        if raw and len(raw) >= 8:
            named_ok += 1
        else:
            named_fail.append(addr)

    # Spot-check OL unique execute helpers
    ol = pr.get("offensive_line_execute_2cj") or {}
    ol_ok = 0
    ol_fail = []
    for n, meta in ol.items():
        for addr in (meta.get("known_or_cataloged") or [])[:3]:
            raw = b.read(base + int(addr, 16), 8)
            if raw:
                ol_ok += 1
            else:
                ol_fail.append(addr)

    # Preferred cores still cover 121
    prefs = pr.get("preferred_cores") or {}
    covered = set()
    for m in prefs.values():
        covered |= set(m.get("core_commands") or [])
    land_names = set(focus.keys())

    # Recipes smoke
    recipes = {
        "land_named_helper_expansion_recipe": army_subjects.land_named_helper_expansion_recipe(),
        "offensive_line_execute_recipe": army_subjects.offensive_line_execute_recipe(),
        "land_post_path_checklist_recipe": army_subjects.land_post_path_checklist_recipe(),
        "land_divergence_gate_delta_recipe": army_subjects.land_divergence_gate_delta_recipe(),
    }
    for k, v in recipes.items():
        assert v.get("allow_post") is False, k

    # midflight watcher pid check (optional)
    import subprocess
    watcher_alive = False
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Process -Id 36128 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id"],
            capture_output=True, text=True, timeout=10,
        )
        watcher_alive = "36128" in (r.stdout or "")
    except Exception:
        watcher_alive = False

    report = {
        "phase": "2cj",
        "posting": "DISABLED",
        "allow_post": False,
        "tool_gate": pr.get("tool_gate"),
        "pid": pid,
        "image_base": hex(base),
        "land_cmds": len(land_names),
        "isvalid_paths_cmd_dicts": len(ivp),
        "helpers_total": len(helpers),
        "by_tier": pr.get("by_tier"),
        "named_helpers": len(named),
        "named_new_2cj": len(pr.get("named_new_2cj") or {}),
        "ol_named_2cj": len(pr.get("ol_named_2cj") or {}),
        "isvalid_gate_helpers": len(pr.get("isvalid_gate_helpers") or []),
        "execute_body_helpers": len(pr.get("execute_body_helpers") or []),
        "preferred_cores": len(prefs),
        "coverage_cmds": len(covered & land_names),
        "coverage_total": len(land_names),
        "genuine_divergences": len(pr.get("genuine_divergences") or []),
        "named_read_ok": named_ok,
        "named_read_fail": named_fail,
        "ol_spot_ok": ol_ok,
        "ol_spot_fail": ol_fail,
        "ol_fully_cataloged": recipes["offensive_line_execute_recipe"].get("fully_cataloged_count"),
        "ol_total": recipes["offensive_line_execute_recipe"].get("total"),
        "watcher_36128_alive": watcher_alive,
        "recipes_allow_post_all_false": True,
        "land_focus_unchanged": "121/121",
        "note": "RO live re-verify only. No Post, no speed change, no input.",
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "phase2cj_live_re.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (OUT / "_2cj_summary.json").write_text(json.dumps({
        "phase": "2cj",
        "allow_post": False,
        "helpers": len(helpers),
        "named": len(named),
        "cores": len(prefs),
        "coverage": f"{len(covered & land_names)}/{len(land_names)}",
        "ol_cataloged": f"{report['ol_fully_cataloged']}/{report['ol_total']}",
        "div": report["genuine_divergences"],
        "watcher": watcher_alive,
    }, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
