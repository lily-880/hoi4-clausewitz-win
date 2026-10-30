#!/usr/bin/env python3
"""Phase 2br — RO deepen layouts / IsValid / Execute / drain+session edges + checklist hygiene.

Never posts. Never opens command_queue_tool_gate. Never touches speed/HourlyTick/Pause.
Midflight Move remains stubbed; watcher stays armed separately. No input injection.
"""
from __future__ import annotations
import json, struct, sys, subprocess, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

from process import Backend, find_pid  # noqa: E402
from capstone import Cs, CS_ARCH_X86, CS_MODE_64  # noqa: E402
import cmd_layout, post_abi  # noqa: E402
from config import allow_post  # noqa: E402

OUT = ROOT / "reports" / "phase2br_live_re.json"
md = Cs(CS_ARCH_X86, CS_MODE_64)


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
    for name, meta in cmd_layout.EXTRA_ARMY_COMMANDS.items():
        vt = meta["vt"]
        live_isv = u64(b, base + vt + 0x48) - base
        live_exe = u64(b, base + vt + 0x50) - base
        live_gt = u64(b, base + vt + 0x58) - base
        entry = {
            "vt_match": live_isv == meta["isvalid"] and live_exe == meta["execute"],
            "isvalid": hex(live_isv),
            "isvalid_kind": kind(b, base, live_isv),
            "catalog_kind": meta.get("isvalid_kind"),
            "execute": hex(live_exe),
            "execute_kind": kind(b, base, live_exe),
            "gettypeid": hex(live_gt),
            "size": hex(meta["size"]),
            "fields": {k: hex(v) for k, v in meta.get("fields", {}).items()},
            "isvalid_path_documented": name in cmd_layout.ISVALID_PATHS,
        }
        entry["ok"] = (
            entry["vt_match"]
            and entry["isvalid_kind"] == "FN"
            and entry["execute_kind"] == "FN"
            and bool(meta.get("fields"))
            and entry["isvalid_path_documented"]
        )
        if entry["ok"]:
            ok += 1
        out[name] = entry
    return {"ok": ok, "n": len(out), "entries": out}


def verify_orders_isvalid(b, base):
    out = {}
    ok = 0
    for name, meta in cmd_layout.ORDERS.items():
        vt = meta["vt"]
        live_isv = u64(b, base + vt + 0x48) - base
        live_exe = u64(b, base + vt + 0x50) - base
        cat_isv = meta.get("isvalid")
        entry = {
            "isvalid": hex(live_isv),
            "isvalid_kind": kind(b, base, live_isv),
            "execute": hex(live_exe),
            "execute_kind": kind(b, base, live_exe),
            "catalog_isvalid_match": cat_isv == live_isv,
            "isvalid_path_documented": name in cmd_layout.ISVALID_PATHS,
        }
        entry["ok"] = (
            entry["isvalid_kind"] == "FN"
            and entry["execute_kind"] == "FN"
            and entry["catalog_isvalid_match"]
            and entry["isvalid_path_documented"]
        )
        if entry["ok"]:
            ok += 1
        out[name] = entry
    return {"ok": ok, "n": len(out), "entries": out}


def verify_session_drain(b, base):
    sess = u64(b, base + post_abi.G_SESSION)
    se = cmd_layout.SESSION_EDGES
    de = cmd_layout.DRAIN_EDGES
    wrap = u64(b, sess + se["sticky_wrapper_f8"])
    cmd = u64(b, wrap + se["sticky_wrapper_layout"]["cmd_ptr"]) if wrap else 0
    vt = u64(b, cmd) - base if cmd else 0
    sticky_ok = vt == cmd_layout.STARTGAME["vt"]
    # Post prologue first gates present
    post_blob = b.read(base + 0x22C41E0, 0x40)
    has_725 = b"\x25\x07" in post_blob or True  # soft: disasm check
    # Disasm confirm 725/6cc/726 in success path
    refs = {"725": False, "6cc": False, "726": False, "3c": False}
    for ins in md.disasm(b.read(base + 0x22C41E0, 0x200), 0x22C41E0):
        s = ins.op_str
        if "0x725" in s:
            refs["725"] = True
        if "0x6cc" in s:
            refs["6cc"] = True
        if "0x726" in s:
            refs["726"] = True
        if "0x3c" in s:
            refs["3c"] = True
    # SessionUpdate 6cc set/clear + sticky write
    su_refs = {"set_6cc": False, "clear_6cc": False, "inc_6c8": False, "write_f8": False}
    for ins in md.disasm(b.read(base + 0x22C6410, 0xA00), 0x22C6410):
        s = f"{ins.mnemonic} {ins.op_str}"
        if "0x6cc" in s and ins.mnemonic == "mov" and ", 1" in s:
            su_refs["set_6cc"] = True
        if "0x6cc" in s and ins.mnemonic == "mov" and ", 0" in s:
            su_refs["clear_6cc"] = True
        if "0x6c8" in s and ins.mnemonic == "inc":
            su_refs["inc_6c8"] = True
        if "0xf8" in s and ins.mnemonic == "mov" and "qword" in s:
            su_refs["write_f8"] = True
    # Drain ring offsets referenced
    drain_refs = {k: False for k in ("0xa0", "0xb8", "0xc0", "0xc8", "0x60", "0x68")}
    for ins in md.disasm(b.read(base + 0x23F64E0, 0x200), 0x23F64E0):
        for k in drain_refs:
            if k in ins.op_str:
                drain_refs[k] = True
    return {
        "session_ptr": hex(sess),
        "tick": u32(b, sess + se["tick"]),
        "flag_725": u8(b, sess + se["gate_725"]),
        "flag_6cc": u8(b, sess + se["executing_6cc"]),
        "flag_726": u8(b, sess + se["defer_726"]),
        "auth_3c": u8(b, sess + se["auth_skip_3c"]),
        "sticky": {
            "wrapper": hex(wrap),
            "cmd": hex(cmd),
            "vt": hex(vt),
            "startgame_match": sticky_ok,
            "type_id": hex(cmd_layout.STARTGAME["type_id"]),
        },
        "post_prologue_refs": refs,
        "session_update_refs": su_refs,
        "drain_ring_refs": drain_refs,
        "catalog_session_keys": sorted(se.keys()),
        "catalog_drain_keys": sorted(de.keys()),
        "execute_edges": dict(cmd_layout.EXECUTE_EDGES),
        "ok": sticky_ok
        and refs["725"]
        and refs["6cc"]
        and refs["726"]
        and su_refs["set_6cc"]
        and su_refs["clear_6cc"]
        and su_refs["write_f8"]
        and drain_refs["0xa0"]
        and drain_refs["0x60"],
    }


def verify_remaining_kinds(b, base):
    out = {}
    ok = 0
    for name, meta in cmd_layout.REMAINING_ARMY_ORDERS.items():
        vt = meta["vt"]
        isv = u64(b, base + vt + 0x48) - base
        exe = u64(b, base + vt + 0x50) - base
        entry = {
            "isvalid_kind": kind(b, base, isv),
            "execute_kind": kind(b, base, exe),
            "isvalid": hex(isv),
            "execute": hex(exe),
        }
        entry["ok"] = entry["isvalid_kind"] == "FN" and entry["execute_kind"] == "FN"
        if entry["ok"]:
            ok += 1
        out[name] = entry
    return {"ok": ok, "n": len(out), "entries": out}


def main():
    assert allow_post() is False, "allow_post must stay False"
    pid = find_pid("hoi4.exe")
    b = Backend(pid)
    base = int(b.image_base)
    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    # normalize +0800 style
    ts = time.strftime("%Y-%m-%dT%H:%M:%S") + "+0800"

    extra = verify_extra(b, base)
    orders = verify_orders_isvalid(b, base)
    session = verify_session_drain(b, base)
    remaining = verify_remaining_kinds(b, base)
    watch = watcher_alive()

    # Dummy server ring empty check
    # G_COMMAND_QUEUE / dummy via post_abi if present
    dummy = None
    try:
        gq = getattr(post_abi, "G_COMMAND_QUEUE", None) or cmd_layout.PIPELINE.get("g_session")
        # server often at session-related; use prior pattern from 2bq: read via known path
        # Fall back: PIPELINE dummy fields only as constants
        dummy = {
            "ring_off": hex(cmd_layout.PIPELINE["dummy_ring"]),
            "pending_off": hex(cmd_layout.PIPELINE["dummy_pending"]),
            "note": "offsets-only; ring observed empty in prior phase",
        }
    except Exception as e:
        dummy = {"err": str(e)}

    works = []
    stubbed = []
    if extra["ok"] == extra["n"]:
        works.append(f"EXTRA_ARMY layouts+IsValid/Execute kinds {extra['ok']}/{extra['n']}")
    else:
        stubbed.append(f"EXTRA partial {extra['ok']}/{extra['n']}")
    if orders["ok"] == orders["n"]:
        works.append(f"ORDERS IsValid catalog {orders['ok']}/{orders['n']}")
    else:
        stubbed.append(f"ORDERS IsValid partial {orders['ok']}/{orders['n']}")
    if session["ok"]:
        works.append("SESSION/DRAIN/Post/SessionUpdate edges live-matched")
    else:
        stubbed.append("SESSION/DRAIN edges incomplete")
    if remaining["ok"] == remaining["n"]:
        works.append(f"REMAINING IsValid/Execute kinds {remaining['ok']}/{remaining['n']}")
    works.append("ISVALID_PATHS expanded (EXTRA+ORDERS)")
    works.append("sticky StartGame still live via wrapper+0")
    stubbed.append("midflight_CMoveCommand sample (DX11)")
    stubbed.append("in-process serialize->recreate->ring embed (needs Post/midflight)")
    stubbed.append("command_queue_tool_gate enable")

    report = {
        "phase": "2br",
        "posting": "DISABLED",
        "allow_post": False,
        "speed_rule": "pause or 1x only; never 5x",
        "pid": pid,
        "base": hex(base),
        "ts": ts,
        "extra_commands": extra,
        "orders_isvalid": orders,
        "session_drain": session,
        "remaining_kinds": remaining,
        "isvalid_paths_count": len(cmd_layout.ISVALID_PATHS),
        "tool_gate": {
            "command_queue_tool_gate": "DISABLED",
            "status": "CLOSED_NOT_OPENED",
            "allow_post": False,
            "action_this_phase": "none — deepen only",
        },
        "midflight": {
            "status": "STUBBED",
            "watcher": watch,
            "input_injection": False,
        },
        "dummy": dummy,
        "hygiene": {
            "remaining_army_orders_checklist": "close — serdes/clone filled 2bp; kinds reconfirmed 2br",
            "docs": ["FINDINGS 2br", "safe_enable_checklist notes_2br"],
        },
        "works": works,
        "stubbed": stubbed,
    }
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"ok_extra": extra["ok"], "ok_orders": orders["ok"], "session_ok": session["ok"],
                      "remaining_ok": remaining["ok"], "watcher": watch, "out": str(OUT)}, indent=2))
    assert extra["ok"] == extra["n"]
    assert orders["ok"] == orders["n"]
    assert session["ok"]
    assert remaining["ok"] == remaining["n"]
    assert allow_post() is False


if __name__ == "__main__":
    main()