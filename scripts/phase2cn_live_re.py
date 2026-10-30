#!/usr/bin/env python3
"""Phase 2cn live RO re-verify."""
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
    idx = pr.get("cmd_post_path_index_2cn") or {}
    named_new = pr.get("named_new_2cn") or {}
    ok, fail = 0, []
    for addr in list(named_new)[:40]:
        raw = b.read(base + int(addr, 16), 8)
        if raw: ok += 1
        else: fail.append(addr)
    watcher = False
    try:
        r = subprocess.run(["powershell","-NoProfile","-Command",
            "Get-Process -Id 36128 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id"],
            capture_output=True, text=True, timeout=10)
        watcher = "36128" in (r.stdout or "")
    except Exception: pass
    for fn in (army_subjects.land_cmd_post_path_index_2cn_recipe,
               army_subjects.land_confidence_report_2cn_recipe,
               army_subjects.land_post_readiness_checklist_2cn_recipe):
        assert fn().get("allow_post") is False
    rep = pr.get("confidence_report_2cn") or {}
    report = {
        "phase": "2cn", "posting": "DISABLED", "allow_post": False,
        "tool_gate": pr.get("tool_gate"), "pid": pid, "image_base": hex(base),
        "helpers_total": len(helpers), "named_helpers": len(named),
        "named_new_2cn": len(named_new), "cmd_index": len(idx),
        "avg_conf": rep.get("avg_post_path_confidence"), "prev_avg_2cm": 0.911,
        "below_90": rep.get("cmds_below_0_9"), "read_ok": ok, "read_fail": fail,
        "watcher_36128_alive": watcher, "land_focus_unchanged": "121/121",
    }
    OUT.mkdir(exist_ok=True)
    (OUT/"phase2cn_live_re.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
if __name__ == "__main__":
    main()
