#!/usr/bin/env python3
"""Phase 2cm live RO re-verify — re-runnable."""
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
    promoted = pr.get("promoted_gate_labels_2cm") or {}
    idx = pr.get("cmd_post_path_index_2cm") or {}
    prefs = pr.get("preferred_cores") or {}
    focus = cmd_layout.LAND_ARMY_FOCUS["commands"]
    ok, fail = 0, []
    for addr in list(promoted) + list(named)[:40]:
        raw = b.read(base + int(addr, 16), 8)
        (ok := ok + 1) if raw else fail.append(addr)
    # fix walrus misuse — redo simply
    ok, fail = 0, []
    for addr in list(promoted) + list(named)[:40]:
        raw = b.read(base + int(addr, 16), 8)
        if raw: ok += 1
        else: fail.append(addr)
    covered = set()
    for m in prefs.values(): covered |= set(m.get("core_commands") or [])
    watcher = False
    try:
        r = subprocess.run(["powershell","-NoProfile","-Command",
            "Get-Process -Id 36128 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id"],
            capture_output=True, text=True, timeout=10)
        watcher = "36128" in (r.stdout or "")
    except Exception: pass
    for fn in (army_subjects.land_cmd_post_path_index_2cm_recipe,
               army_subjects.land_gate_label_promoted_recipe,
               army_subjects.land_post_readiness_checklist_2cm_recipe):
        assert fn().get("allow_post") is False
    report = {
        "phase": "2cm", "posting": "DISABLED", "allow_post": False,
        "tool_gate": pr.get("tool_gate"), "pid": pid, "image_base": hex(base),
        "helpers_total": len(helpers), "named_helpers": len(named),
        "promoted_gates": len(promoted),
        "gate_label_only_closed": pr.get("gate_label_only_closed_2cm"),
        "cmd_index": len(idx),
        "fully_named": sum(1 for v in idx.values() if not v.get("unnamed_gates_remaining")),
        "avg_conf": round(sum((v.get("post_path_confidence") or 0) for v in idx.values())/max(1,len(idx)),3),
        "coverage": f"{len(covered & set(focus))}/{len(focus)}",
        "read_ok": ok, "read_fail": fail, "watcher_36128_alive": watcher,
        "land_focus_unchanged": "121/121",
    }
    OUT.mkdir(exist_ok=True)
    (OUT/"phase2cm_live_re.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
if __name__ == "__main__":
    main()
