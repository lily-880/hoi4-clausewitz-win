#!/usr/bin/env python3
"""Phase 2bt — RO land-army focus: attack / retreat / move / strategic redeploy.

Never posts. Never opens command_queue_tool_gate. Never touches speed/HourlyTick/Pause.
Midflight Move remains stubbed; watcher stays armed separately. No input injection.
Prioritizes land army over naval/production.
"""
from __future__ import annotations
import json, struct, sys, subprocess, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

from process import Backend, find_pid  # noqa: E402
import cmd_layout, post_abi, army_subjects  # noqa: E402
from config import allow_post  # noqa: E402

OUT = ROOT / "reports" / "phase2bt_live_re.json"


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


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
    return u64(b, base + cmd_layout.FACTORY_TABLE["rva"] + i * 8) - base


def watcher_alive():
    try:
        out = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' "
                "-and $_.CommandLine -match 'midflight' } | Select-Object -ExpandProperty ProcessId",
            ],
            text=True,
            errors="ignore",
            timeout=15,
        )
        pids = [int(x) for x in out.split() if x.strip().isdigit()]
        return {"alive": bool(pids), "pids": pids}
    except Exception as e:
        return {"alive": None, "error": str(e)}


def verify_support_attack(b, base):
    sa = cmd_layout.SUPPORT_ATTACK
    vt = sa["vt"]
    live_isv = u64(b, base + vt + 0x48) - base
    live_exe = u64(b, base + vt + 0x50) - base
    live_tid_fn = u64(b, base + vt + 0x58) - base
    fac = factory_fn(b, base, sa["type_id"])
    return {
        "name": sa["name"],
        "type_id": hex(sa["type_id"]),
        "size": hex(sa["size"]),
        "vt": hex(vt),
        "factory_doc": hex(sa["factory"]),
        "factory_live": hex(fac),
        "factory_match": fac == sa["factory"],
        "isvalid_doc": hex(sa["isvalid"]),
        "isvalid_live": hex(live_isv),
        "isvalid_match": live_isv == sa["isvalid"],
        "isvalid_kind": kind(b, base, live_isv),
        "execute_doc": hex(sa["execute"]),
        "execute_live": hex(live_exe),
        "execute_match": live_exe == sa["execute"],
        "execute_kind": kind(b, base, live_exe),
        "gettypeid_live": hex(live_tid_fn),
        "fields": {k: hex(v) for k, v in sa["fields"].items()},
        "serialize_tokens": {hex(k): hex(v) for k, v in sa["serialize_tokens"].items()},
        "gate_0x60_kind": sa["gate_0x60_kind"],
        "gate_0x80_kind": sa["gate_0x80_kind"],
    }


def verify_strategic_action(b, base):
    act = cmd_layout.STRATEGIC["action"]
    vt = act["vt"]
    live_isv = u64(b, base + vt + 0x48) - base
    live_exe = u64(b, base + vt + 0x50) - base
    return {
        "name": act["name"],
        "vt": hex(vt),
        "type_id": hex(act["type_id"]),
        "size": hex(act["size"]),
        "serialize": hex(act["serialize"]),
        "deserialize": hex(act["deserialize"]),
        "execute_doc": hex(act["execute"]),
        "execute_live": hex(live_exe),
        "execute_match": live_exe == act["execute"],
        "execute_kind": kind(b, base, live_exe),
        "isvalid_doc": hex(act["isvalid"]),
        "isvalid_live": hex(live_isv),
        "isvalid_match": live_isv == act["isvalid"],
        "isvalid_kind": kind(b, base, live_isv),
        "serialize_tokens": {hex(k): hex(v) for k, v in act["serialize_tokens"].items()},
        "fields": {k: hex(v) for k, v in act["fields"].items()},
    }


def verify_land_focus(b, base):
    out = {}
    ok = 0
    total = 0
    for name, meta in cmd_layout.LAND_ARMY_FOCUS["commands"].items():
        total += 1
        vt = meta.get("vt")
        tid = meta.get("type_id")
        entry = {"name": name, "role": meta.get("role"), "type_id": hex(tid) if tid else None}
        if vt:
            live_isv = u64(b, base + vt + 0x48) - base
            live_exe = u64(b, base + vt + 0x50) - base
            entry["vt"] = hex(vt)
            entry["isvalid_live"] = hex(live_isv)
            entry["isvalid_kind"] = kind(b, base, live_isv)
            entry["execute_live"] = hex(live_exe)
            entry["execute_kind"] = kind(b, base, live_exe)
            if "isvalid" in meta:
                entry["isvalid_match"] = live_isv == meta["isvalid"]
            if "execute" in meta:
                entry["execute_match"] = live_exe == meta["execute"]
            if "factory" in meta and tid:
                fac = factory_fn(b, base, tid)
                entry["factory_live"] = hex(fac)
                entry["factory_match"] = fac == meta["factory"]
            matched = all(
                entry.get(k, True) is True
                for k in ("isvalid_match", "execute_match", "factory_match")
                if k in entry
            )
            entry["ok"] = matched and entry["isvalid_kind"] == "FN"
            if entry["ok"]:
                ok += 1
        else:
            # alias-only — resolve from EXTRA/REMAINING/ORDERS
            alias = meta.get("layout_alias")
            entry["layout_alias"] = alias
            src = None
            if alias == "EXTRA_ARMY_COMMANDS":
                src = cmd_layout.EXTRA_ARMY_COMMANDS.get(name)
            elif alias == "REMAINING_ARMY_ORDERS":
                src = cmd_layout.REMAINING_ARMY_ORDERS.get(name)
            elif alias == "ORDERS":
                src = cmd_layout.ORDERS.get(name)
            if src and "vt" in src:
                vt = src["vt"]
                live_isv = u64(b, base + vt + 0x48) - base
                live_exe = u64(b, base + vt + 0x50) - base
                entry["vt"] = hex(vt)
                entry["isvalid_kind"] = kind(b, base, live_isv)
                entry["execute_kind"] = kind(b, base, live_exe)
                entry["ok"] = entry["isvalid_kind"] == "FN"
                if entry["ok"]:
                    ok += 1
            else:
                entry["ok"] = False
        out[name] = entry
    return {"ok": ok, "total": total, "commands": out}


def verify_core_layouts(b, base):
    cores = {}
    for key, layout in (
        ("MOVE", cmd_layout.MOVE),
        ("STRATEGIC", cmd_layout.STRATEGIC),
        ("CANCEL", cmd_layout.CANCEL),
    ):
        vt = layout["vt"]
        live_isv = u64(b, base + vt + 0x48) - base
        live_exe = u64(b, base + vt + 0x50) - base
        cores[key] = {
            "name": layout["name"],
            "vt": hex(vt),
            "type_id": hex(layout["type_id"]),
            "isvalid_kind": kind(b, base, live_isv),
            "execute_kind": kind(b, base, live_exe),
            "isvalid_match": live_isv == layout["isvalid"] if "isvalid" in layout else None,
            "execute_match": live_exe == layout.get("execute", -1) if "execute" in layout else None,
        }
    return cores


def hai_recipes(b, base):
    rows = army_subjects.iter_armies_by_index(b, base, country_tag=15)[:3]
    out = []
    for r in rows:
        dest = (r["province_id"] + 1) & 0xFFFF  # placeholder dest; RO only
        out.append({
            "handle": list(r["handle"]),
            "province_id": r["province_id"],
            "move": army_subjects.move_action_recipe(r),
            "strategic": army_subjects.strategic_redeploy_recipe(r, dest),
            "support_attack": army_subjects.support_attack_recipe(r, dest),
            "cancel": army_subjects.cancel_movement_recipe([r]),
            "fallback": army_subjects.fallback_order_recipe(1),
            "cancel_running_away": army_subjects.cancel_running_away_recipe([r]),
        })
    return out


def session_hygiene(b, base):
    sess = u64(b, base + post_abi.G_SESSION)
    # tick / speed-ish fields used in prior phases
    tick = u32(b, sess + 0x725) if sess else None
    # allow_post from config
    return {
        "sess": hex(sess) if sess else None,
        "tick_725": tick,
        "allow_post": bool(allow_post()),
        "tool_gate": cmd_layout.TOOL_GATE_PREDICATES.get("status")
        if hasattr(cmd_layout, "TOOL_GATE_PREDICATES")
        else None,
    }


def main():
    pid = find_pid("hoi4.exe") or find_pid("hoi4")
    if not pid:
        raise SystemExit("hoi4 not found")
    b = Backend(pid)
    base = b.image_base
    t0 = time.time()

    report = {
        "phase": "2bt",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "pid": pid,
        "image_base": hex(base),
        "posting": "DISABLED",
        "focus": "land army attack/retreat/move/strategic_redeploy",
        "support_attack": verify_support_attack(b, base),
        "strategic_action": verify_strategic_action(b, base),
        "land_focus": verify_land_focus(b, base),
        "core_layouts": verify_core_layouts(b, base),
        "isvalid_paths_count": len(cmd_layout.ISVALID_PATHS),
        "hai_recipes": hai_recipes(b, base),
        "isvalid_notes": army_subjects.isvalid_path_notes(),
        "hygiene": session_hygiene(b, base),
        "watcher": watcher_alive(),
        "stubbed": [
            "midflight_CMoveCommand",
            "in_process_ring_embed",
            "command_queue_tool_gate_enable",
            "ALLOW_POST",
        ],
        "elapsed_s": round(time.time() - t0, 3),
    }

    # tool gate status string
    tgp = getattr(cmd_layout, "TOOL_GATE_PREDICATES", {})
    report["tool_gate_status"] = tgp.get("status", tgp.get("verdict", "CLOSED_NOT_OPENED"))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps({
        "phase": "2bt",
        "support_ok": report["support_attack"]["factory_match"] and report["support_attack"]["isvalid_match"],
        "strat_act_ok": report["strategic_action"]["isvalid_match"] and report["strategic_action"]["execute_match"],
        "land_focus": f"{report['land_focus']['ok']}/{report['land_focus']['total']}",
        "isvalid_paths": report["isvalid_paths_count"],
        "hai": len(report["hai_recipes"]),
        "allow_post": report["hygiene"]["allow_post"],
        "tick_725": report["hygiene"]["tick_725"],
        "watcher": report["watcher"],
        "out": str(OUT),
    }, indent=2))


if __name__ == "__main__":
    main()
