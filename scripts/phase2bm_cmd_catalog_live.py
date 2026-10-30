"""Phase 2bm: RO live catalog — CCommand subtype VT slots, early gates, drain/ring, army subjects.
Never posts. Never changes game speed. Pause/1x only.
"""
from __future__ import annotations
import json, struct, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))
from process import Backend, find_pid
import post_abi, cmd_layout
from config import allow_post
from handle import resolve_handle, HANDLE_TYPE_ARMY
from province import resolve_province

OUT = ROOT / "reports" / "phase2bm_cmd_catalog_live.json"
GATE_TRUE = cmd_layout.POST_GATES["gate_stub_TRUE"]
GATE_FALSE = cmd_layout.POST_GATES["gate_stub_FALSE"]


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def u8(b, a):
    return b.read(a, 1)[0]


def gate_kind(rva: int) -> str:
    if rva == GATE_TRUE:
        return "TRUE"
    if rva == GATE_FALSE:
        return "FALSE"
    return f"custom:{hex(rva)}"


def vt_slots(b, base, vt_rva: int) -> dict:
    vt = base + vt_rva
    out = {}
    for name, off in cmd_layout.BASE["vt_slots"].items():
        fn = u64(b, vt + off)
        rva = fn - base if fn else 0
        out[name] = {"rva": hex(rva), "abs": hex(fn)}
        if name in ("gate_0x60", "gate_0x80"):
            out[name]["kind"] = gate_kind(rva)
    # type-id often written by PostExec/typeid slot — try reading mov imm at PostExec
    postexec = int(out["PostExec"]["rva"], 16)
    raw = b.read(base + postexec, 8)
    if raw[0] == 0xC7 and raw[1] == 0x02:
        out["type_id_imm"] = hex(struct.unpack_from("<I", raw, 2)[0])
    return out


def catalog_entry(b, base, name: str, info: dict) -> dict:
    vt = info["vt"]
    slots = vt_slots(b, base, vt)
    exp_exec = info.get("execute") or info.get("Execute")
    got_exec = int(slots["Execute"]["rva"], 16)
    entry = {
        "name": name,
        "vt": hex(vt),
        "size": hex(info["size"]) if "size" in info else None,
        "type_id_doc": hex(info["type_id"]) if "type_id" in info else None,
        "slots": slots,
        "execute_match": (got_exec == exp_exec) if exp_exec else None,
        "execute_doc": hex(exp_exec) if exp_exec else None,
        "gate_0x60": slots["gate_0x60"].get("kind"),
        "gate_0x80": slots["gate_0x80"].get("kind"),
    }
    if "clone" in info:
        entry["clone_doc"] = hex(info["clone"])
        entry["clone_match"] = int(slots["Clone"]["rva"], 16) == info["clone"]
    return entry


def main():
    b = Backend(find_pid("hoi4.exe"))
    base = int(b.image_base)
    sess = u64(b, base + post_abi.G_SESSION)
    server = u64(b, sess + post_abi.CSession_SERVER)
    server_vt = u64(b, server) - base
    drain = u32(b, sess + post_abi.CSession_DRAIN_COUNTER)
    exec_c = u32(b, sess + post_abi.CSession_EXEC_COUNTER)
    seq = u32(b, server + 0xD0)
    state = u32(b, sess + post_abi.CSession_STATE)
    gate725 = u8(b, sess + 0x725)
    exec_flag = u8(b, sess + post_abi.CSession_EXECUTING_FLAG)
    tick = u32(b, sess + 0x84)

    # Dummy ring embed dump
    ring = server + post_abi.CDummyServer_RING
    ring_dump = {
        "lock": u32(b, ring),
        "buf": hex(u64(b, ring + 0x8)),
        "cap_or_field": u32(b, ring + 0x10),
        "raw_0x40": b.read(ring, 0x40).hex(),
        "pending_head": hex(u64(b, server + post_abi.CDummyServer_PENDING)) or None,
        "pending_count": u32(b, server + post_abi.CDummyServer_PENDING + 0x10),
        "execlist_count": u32(b, server + post_abi.CDummyServer_EXECLIST + 0x10),
        "seq": seq,
    }
    # sink/drain from live VT
    sink = u64(b, u64(b, server) + 0x28) - base
    drain_fn = u64(b, u64(b, server) + 0x30) - base

    cmds = {}
    # Move / Strategic / Cancel / StartGame / Chat
    for name, info in [
        ("CMoveCommand", cmd_layout.MOVE),
        ("CStrategicRedeploymentCommand", cmd_layout.STRATEGIC),
        ("CCancelMovementCommand", cmd_layout.CANCEL),
        ("CStartGameCommand", cmd_layout.STARTGAME),
        ("CChatCommand", cmd_layout.CHAT),
    ]:
        cmds[name] = catalog_entry(b, base, name, info)

    # Move action VT slots
    act = cmd_layout.MOVE["action"]
    act_slots = {}
    for off in range(0, 0xE0, 8):
        fn = u64(b, base + act["vt"] + off)
        if base <= fn < base + 0x5000000:
            act_slots[hex(off)] = hex(fn - base)
    cmds["CUnitMoveAction"] = {
        "vt": hex(act["vt"]),
        "slots_sample": {k: act_slots[k] for k in ("0x48", "0x50", "0xc0") if k in act_slots},
        "execute_doc": hex(act["execute"]),
        "execute_match": act_slots.get("0x48") == hex(act["execute"]),
        "isvalid_match": act_slots.get("0x50") == hex(act["isvalid"]),
        "serialize_match": act_slots.get("0xc0") == hex(act["serialize"]),
        "all_slots": act_slots,
    }

    orders = {}
    for name, info in cmd_layout.ORDERS.items():
        orders[name] = catalog_entry(b, base, name, info)

    # sticky StartGame still live?
    wrap = u64(b, sess + 0xF8)
    sticky = None
    if wrap:
        try:
            cmd = u64(b, wrap)
            vt = u64(b, cmd) - base
            sticky = {
                "wrapper": hex(wrap),
                "cmd": hex(cmd),
                "vt_rva": hex(vt),
                "is_startgame": vt == cmd_layout.STARTGAME["vt"],
                "tick": u32(b, cmd + 0xC),
                "seq": u32(b, cmd + 0x1C),
                "execlist_select": u8(b, cmd + 0x1A),
            }
        except Exception as e:
            sticky = {"error": str(e)}

    # Army subjects 17/17
    gs = u64(b, base + post_abi.G_GAMESTATE)
    army_ok = 0
    prov_ok = 0
    samples = []
    # reuse handle roster from prior: indices 1037..1053 type 0x33 — discover via country armies if helper available
    try:
        from gamestate import iter_player_armies
        for a in list(iter_player_armies(b, base, gs))[:17]:
            h = a.get("handle")
            pref = a.get("province_id")
            if h and resolve_handle(b, h[0], h[1], base):
                army_ok += 1
            if pref is not None and resolve_province(b, pref, base, gs) == pref:
                prov_ok += 1
            if len(samples) < 3:
                samples.append(a)
    except Exception as e:
        # fallback: sequential indices from prior HAI session
        for ix in range(1037, 1054):
            got = resolve_handle(b, HANDLE_TYPE_ARMY, ix, base)
            if got:
                army_ok += 1
                try:
                    pid = u32(b, got + 0x28)
                    pref = resolve_province(b, pid, base, gs)
                    if pref == pid:
                        prov_ok += 1
                    if len(samples) < 3:
                        samples.append({"ix": ix, "obj": hex(got), "province_id": pid, "prov_resolve": pref})
                except Exception:
                    pass
        army_note = f"fallback scan; iter_player_armies: {e}"
    else:
        army_note = "iter_player_armies"

    # Post prologue still intact
    post_bytes = b.read(base + post_abi.FN_CMD_QUEUE_POST, 8).hex()

    checks = []
    def add(name, ok, detail=None):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    add("allow_post_false", allow_post() is False, allow_post())
    add("server_vt_dummy", server_vt == post_abi.CDummyServer_VT, hex(server_vt))
    add("sink", sink == post_abi.FN_CMD_QUEUE_POST_SINK_DUMMY, hex(sink))
    add("drain_fn", drain_fn == post_abi.FN_CMD_QUEUE_DRAIN_DUMMY, hex(drain_fn))
    add("session_state_2", state == 2, state)
    add("gate_725_readable", True, gate725)
    add("move_execute", cmds["CMoveCommand"]["execute_match"], cmds["CMoveCommand"]["slots"]["Execute"]["rva"])
    add("move_gates_FALSE", cmds["CMoveCommand"]["gate_0x60"] == "FALSE" and cmds["CMoveCommand"]["gate_0x80"] == "FALSE")
    add("action_execute", cmds["CUnitMoveAction"]["execute_match"])
    add("strategic_execute", cmds["CStrategicRedeploymentCommand"]["execute_match"])
    add("oec_execute", orders["COrderExecuteCommand"]["execute_match"])
    add("startgame_sticky", sticky and sticky.get("is_startgame"), sticky)
    add("post_prologue", post_bytes.startswith("48895c2408"), post_bytes)
    add("army_handles", army_ok >= 17, f"{army_ok} ({army_note})")
    add("never_5x", True, "speed untouched; RO only")

    order_exec_ok = sum(1 for v in orders.values() if v.get("execute_match"))
    add("orders_execute_slots", order_exec_ok == len(orders), f"{order_exec_ok}/{len(orders)}")

    out = {
        "phase": "2bm",
        "posting": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "pid": find_pid("hoi4.exe"),
        "base": hex(base),
        "session": {
            "addr": hex(sess),
            "state": state,
            "drain": drain,
            "exec": exec_c,
            "tick": tick,
            "gate_725": gate725,
            "executing_flag_6cc": exec_flag,
        },
        "server": {
            "addr": hex(server),
            "vt_rva": hex(server_vt),
            "seq": seq,
            "sink_rva": hex(sink),
            "drain_rva": hex(drain_fn),
            "ring": ring_dump,
        },
        "commands": cmds,
        "orders": orders,
        "sticky_startgame": sticky,
        "army_samples": samples,
        "post_gates_doc": cmd_layout.POST_GATES,
        "pipeline": cmd_layout.PIPELINE,
        "checks": checks,
        "passed": sum(1 for c in checks if c["ok"]),
        "failed": sum(1 for c in checks if not c["ok"]),
        "all_ok": all(c["ok"] for c in checks),
        "blocks_post_enable": [
            "midflight_move_sample still stubbed (no live CMoveCommand captured this session)",
            "CLAUSEWITZ_ALLOW_POST must stay unset; allow_post() hard-denies",
            "command_queue_tool_gate open until midflight Move + explicit gate",
            "CMoveCommand early gates both FALSE — Post needs session+0x725 or r8b=1 (documented, not a write proof)",
            "Never Post C*GameSpeed* / HourlyTick (5x ban)",
        ],
        "note": "RO catalog + live VT verification only; NO Post / NO WriteProcessMemory",
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("phase", "passed", "failed", "all_ok", "blocks_post_enable", "session")}, indent=2))
    print("orders_execute", order_exec_ok, "/", len(orders))
    print("move_gates", cmds["CMoveCommand"]["gate_0x60"], cmds["CMoveCommand"]["gate_0x80"], "725=", gate725)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
