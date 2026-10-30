#!/usr/bin/env python3
"""Phase 2bu — RO land cancel/abort + frontline/plan + theater deepen.

Never posts. Never opens command_queue_tool_gate. Never touches speed/HourlyTick/Pause.
Midflight Move remains stubbed; watcher stays armed separately. No input injection.
Naval/production out of scope.
"""
from __future__ import annotations
import json, struct, sys, subprocess, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

from process import Backend, find_pid  # noqa: E402
import cmd_layout, post_abi, army_subjects  # noqa: E402
from config import allow_post  # noqa: E402

OUT = ROOT / "reports" / "phase2bu_live_re.json"


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


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


def verify_cmd(b, base, name, meta):
    vt = meta.get("vt")
    tid = meta.get("type_id")
    entry = {"name": name, "role": meta.get("role")}
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
    if "isvalid" in meta:
        entry["isvalid_match"] = live_isv == meta["isvalid"]
    if "execute" in meta:
        entry["execute_match"] = live_exe == meta["execute"]
    if tid and "factory" in meta:
        fac = factory_fn(b, base, tid)
        entry["factory_live"] = hex(fac)
        entry["factory_match"] = fac == meta["factory"]
    entry["ok"] = (
        entry["isvalid_kind"] == "FN"
        and entry["execute_kind"] == "FN"
        and entry.get("isvalid_match", True)
        and entry.get("execute_match", True)
        and entry.get("factory_match", True)
    )
    return entry


def verify_land_focus(b, base):
    out = {}
    ok = 0
    for name, meta in cmd_layout.LAND_ARMY_FOCUS["commands"].items():
        # resolve alias vt if needed
        m = dict(meta)
        if "vt" not in m:
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
        entry = verify_cmd(b, base, name, m)
        out[name] = entry
        if entry.get("ok"):
            ok += 1
    return {"ok": ok, "total": len(out), "commands": out}


def verify_exe_proofs(b, base):
    out = {}
    ok = 0
    for name, meta in cmd_layout.LAND_EXE_PROOFS["commands"].items():
        live_kind = kind(b, base, meta["execute"])
        isv_kind = kind(b, base, meta["isvalid"])
        entry = {
            "execute": hex(meta["execute"]),
            "execute_kind_live": live_kind,
            "isvalid": hex(meta["isvalid"]),
            "isvalid_kind_live": isv_kind,
            "field_map": {k: hex(v) for k, v in meta.get("field_map", {}).items()},
            "ok": live_kind == "FN" and isv_kind == "FN",
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
        out.append({
            "handle": list(r["handle"]),
            "province_id": r["province_id"],
            "move": army_subjects.move_action_recipe(r),
            "strategic": army_subjects.strategic_redeploy_recipe(r, dest),
            "support_attack": army_subjects.support_attack_recipe(r, dest),
            "cancel": army_subjects.cancel_movement_recipe([r]),
            "mass_cancel": army_subjects.mass_cancel_movement_recipe([r]),
            "fallback": army_subjects.fallback_order_recipe(1),
            "cancel_running_away": army_subjects.cancel_running_away_recipe([r]),
            "new_front": army_subjects.new_front_recipe([list(r["handle"])]),
            "set_path": army_subjects.set_path_recipe(1, 0, 0),
            "set_collapse": army_subjects.set_collapse_recipe([0, 1], 1),
            "order_execute": army_subjects.order_execute_recipe(0, 1, 0),
            "assign_theater": army_subjects.assign_theater_group_recipe(list(r["handle"]), 1),
        })
    return out


def main():
    assert not allow_post(), "ALLOW_POST must stay False"
    pid = find_pid("hoi4.exe") or find_pid("hoi4")
    if not pid:
        raise SystemExit("hoi4 not found")
    b = Backend(pid)
    base = int(b.image_base)
    t0 = time.time()
    sess = u64(b, base + post_abi.G_SESSION)

    report = {
        "phase": "2bu",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "pid": pid,
        "image_base": hex(base),
        "posting": "DISABLED",
        "focus": "land cancel/abort + frontline/plan + theater",
        "land_focus": verify_land_focus(b, base),
        "exe_proofs": verify_exe_proofs(b, base),
        "isvalid_paths_count": len(cmd_layout.ISVALID_PATHS),
        "groups": {
            k: cmd_layout.LAND_ARMY_FOCUS[k]
            for k in cmd_layout.LAND_ARMY_FOCUS
            if k.endswith("_group")
        },
        "hai_recipes": hai_recipes(b, base),
        "isvalid_notes": army_subjects.isvalid_path_notes(),
        "hygiene": {
            "sess": hex(sess),
            "tick_725": u8(b, sess + 0x725),
            "allow_post": bool(allow_post()),
        },
        "watcher": watcher_alive(),
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
        "phase": "2bu",
        "land_focus": f"{report['land_focus']['ok']}/{report['land_focus']['total']}",
        "exe_proofs": f"{report['exe_proofs']['ok']}/{report['exe_proofs']['total']}",
        "isvalid_paths": report["isvalid_paths_count"],
        "hai": len(report["hai_recipes"]),
        "allow_post": report["hygiene"]["allow_post"],
        "tick_725": report["hygiene"]["tick_725"],
        "watcher": report["watcher"],
        "groups": {k: len(v) for k, v in report["groups"].items()},
        "out": str(OUT),
    }, indent=2))


if __name__ == "__main__":
    main()
