#!/usr/bin/env python3
"""Phase 2bs — RO remaining subtypes + REMAINING fields + safer tool-gate analysis.

Never posts. Never opens command_queue_tool_gate. Never touches speed/HourlyTick/Pause.
Midflight Move remains stubbed; watcher stays armed separately. No input injection.
"""
from __future__ import annotations
import json, struct, sys, subprocess, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

from process import Backend, find_pid  # noqa: E402
import cmd_layout, post_abi  # noqa: E402
from config import allow_post  # noqa: E402

OUT = ROOT / "reports" / "phase2bs_live_re.json"


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


def verify_extra(b, base):
    out = {}
    ok = 0
    by_kind = {}
    for name, meta in cmd_layout.EXTRA_ARMY_COMMANDS.items():
        vt = meta["vt"]
        live_isv = u64(b, base + vt + 0x48) - base
        live_exe = u64(b, base + vt + 0x50) - base
        fac = factory_fn(b, base, meta["type_id"])
        entry = {
            "kind": meta.get("kind"),
            "vt_match": live_isv == meta["isvalid"] and live_exe == meta["execute"],
            "isvalid_kind": kind(b, base, live_isv),
            "execute_kind": kind(b, base, live_exe),
            "factory_match": fac == meta["factory"],
            "fields": bool(meta.get("fields")),
            "isvalid_path": name in cmd_layout.ISVALID_PATHS,
            "size": hex(meta["size"]),
            "type_id": hex(meta["type_id"]),
        }
        entry["ok"] = (
            entry["vt_match"]
            and entry["isvalid_kind"] == "FN"
            and entry["execute_kind"] == "FN"
            and entry["factory_match"]
            and entry["fields"]
            and entry["isvalid_path"]
        )
        if entry["ok"]:
            ok += 1
        by_kind.setdefault(meta.get("kind") or "?", 0)
        if entry["ok"]:
            by_kind[meta.get("kind") or "?"] += 1
        out[name] = entry
    return {"ok": ok, "n": len(out), "by_kind_ok": by_kind, "entries": out}


def verify_remaining(b, base):
    out = {}
    ok = 0
    for name, meta in cmd_layout.REMAINING_ARMY_ORDERS.items():
        vt = meta["vt"]
        live_isv = u64(b, base + vt + 0x48) - base
        live_exe = u64(b, base + vt + 0x50) - base
        entry = {
            "isvalid_kind": kind(b, base, live_isv),
            "execute_kind": kind(b, base, live_exe),
            "catalog_isvalid_match": meta.get("isvalid") == live_isv,
            "fields": bool(meta.get("fields")),
            "isvalid_path": name in cmd_layout.ISVALID_PATHS,
        }
        entry["ok"] = (
            entry["isvalid_kind"] == "FN"
            and entry["execute_kind"] == "FN"
            and entry["catalog_isvalid_match"]
            and entry["fields"]
            and entry["isvalid_path"]
        )
        if entry["ok"]:
            ok += 1
        out[name] = entry
    return {"ok": ok, "n": len(out), "entries": out}


def verify_tool_gate(b, base):
    tg = cmd_layout.TOOL_GATE_PREDICATES
    sess = u64(b, base + post_abi.G_SESSION)
    live_725 = u8(b, sess + 0x725)
    preds = []
    for p in tg["all_required_to_consider_enable"]:
        item = dict(p)
        if p["id"] == "session_725":
            item["live"] = live_725
        if p["id"] == "CLAUSEWITZ_ALLOW_POST":
            item["allow_post_live"] = False
        preds.append(item)
    # none may be "enabled"
    statuses = {p["status"] for p in tg["all_required_to_consider_enable"]}
    return {
        "catalog_status": tg["status"],
        "allow_post_catalog": tg["allow_post"],
        "allow_post_live": allow_post(),
        "predicates": preds,
        "action_this_phase": "analysis only — gate NOT opened",
        "any_predicate_allows_enable": False,
        "blocking_still": [
            p["id"]
            for p in tg["all_required_to_consider_enable"]
            if p["status"]
            not in ("closed", "ok", "necessary_not_sufficient", "policy")
        ],
        "ok": tg["status"] == "CLOSED_NOT_OPENED"
        and tg["allow_post"] is False
        and allow_post() is False
        and "hard-deny" in statuses
        and "STUBBED" in statuses,
    }


def verify_sticky(b, base):
    sess = u64(b, base + post_abi.G_SESSION)
    wrap = u64(b, sess + 0xF8)
    cmd = u64(b, wrap) if wrap else 0
    vt = (u64(b, cmd) - base) if cmd else 0
    return {
        "wrapper": hex(wrap),
        "cmd": hex(cmd),
        "vt": hex(vt),
        "startgame_match": vt == cmd_layout.STARTGAME["vt"],
    }


def main():
    assert allow_post() is False
    pid = find_pid("hoi4.exe")
    b = Backend(pid)
    base = int(b.image_base)
    ts = time.strftime("%Y-%m-%dT%H:%M:%S") + "+0800"
    sess = u64(b, base + post_abi.G_SESSION)

    extra = verify_extra(b, base)
    remaining = verify_remaining(b, base)
    tool = verify_tool_gate(b, base)
    sticky = verify_sticky(b, base)
    watch = watcher_alive()

    works = []
    stubbed = []
    if extra["ok"] == extra["n"]:
        works.append(f"EXTRA_ARMY/naval/air/fleet layouts {extra['ok']}/{extra['n']}")
    else:
        stubbed.append(f"EXTRA partial {extra['ok']}/{extra['n']}")
    if remaining["ok"] == remaining["n"]:
        works.append(f"REMAINING fields+IsValid paths {remaining['ok']}/{remaining['n']}")
    else:
        stubbed.append(f"REMAINING partial {remaining['ok']}/{remaining['n']}")
    if tool["ok"]:
        works.append("TOOL_GATE_PREDICATES safer analysis CLOSED_NOT_OPENED")
    else:
        stubbed.append("tool gate analysis incomplete")
    if sticky["startgame_match"]:
        works.append("sticky StartGame still live")
    works.append(f"ISVALID_PATHS {len(cmd_layout.ISVALID_PATHS)}")
    stubbed.append("midflight_CMoveCommand sample (DX11)")
    stubbed.append("in-process serialize->recreate->ring embed (needs Post/midflight)")
    stubbed.append("command_queue_tool_gate enable")

    report = {
        "phase": "2bs",
        "posting": "DISABLED",
        "allow_post": False,
        "speed_rule": "pause or 1x only; never 5x",
        "pid": pid,
        "base": hex(base),
        "ts": ts,
        "session": {
            "ptr": hex(sess),
            "tick": u32(b, sess + 0x84),
            "flag_725": u8(b, sess + 0x725),
            "flag_6cc": u8(b, sess + 0x6CC),
            "flag_726": u8(b, sess + 0x726),
        },
        "extra_commands": extra,
        "remaining": remaining,
        "tool_gate": tool,
        "sticky": sticky,
        "isvalid_paths_count": len(cmd_layout.ISVALID_PATHS),
        "midflight": {
            "status": "STUBBED",
            "watcher": watch,
            "input_injection": False,
        },
        "works": works,
        "stubbed": stubbed,
    }
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "extra": f"{extra['ok']}/{extra['n']}",
                "remaining": f"{remaining['ok']}/{remaining['n']}",
                "tool_ok": tool["ok"],
                "sticky": sticky,
                "watcher": watch,
                "out": str(OUT),
            },
            indent=2,
        )
    )
    assert extra["ok"] == extra["n"]
    assert remaining["ok"] == remaining["n"]
    assert tool["ok"]
    assert sticky["startgame_match"]
    assert allow_post() is False


if __name__ == "__main__":
    main()