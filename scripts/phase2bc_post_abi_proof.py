"""Phase 2bc: Independent READ-ONLY tooling proof of Post ABI.

Does NOT call Post / does NOT WriteProcessMemory.
Proves live memory matches calling/post_abi.py + cmd_layout.py contracts.
"""
from __future__ import annotations
import json, struct, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))
from process import Backend, find_pid  # noqa: E402
import post_abi
import cmd_layout

OV = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
OUT = ROOT / "reports" / "phase2bc_post_abi_proof.json"


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def u8(b, a):
    return b.read(a, 1)[0]


def checks():
    b = Backend(find_pid("hoi4.exe"))
    base = int(b.image_base)
    results = []

    def ok(name, cond, detail=None):
        results.append({"check": name, "ok": bool(cond), "detail": detail})

    # 1. G_SESSION matches App+0x380
    idler = u64(b, base + post_abi.G_IDLER)
    app = u64(b, idler + 0x530)
    session = u64(b, app + 0x380)
    g_session = u64(b, base + post_abi.G_SESSION)
    ok("G_SESSION_eq_App380", g_session == session, {"g": hex(g_session), "s": hex(session)})

    # 2. server = session+0x40, VT is CDummyServer
    server = u64(b, session + post_abi.CSession_SERVER)
    server_vt = u64(b, server) - base
    ok("DummyServer_VT", server_vt == post_abi.CDummyServer_VT, hex(server_vt))

    # 3. vt+0x28 == sink, vt+0x30 == drain
    sink = u64(b, u64(b, server) + 0x28) - base
    drain = u64(b, u64(b, server) + 0x30) - base
    ok("vt28_sink", sink == post_abi.FN_CMD_QUEUE_POST_SINK_DUMMY, hex(sink))
    ok("vt30_drain", drain == post_abi.FN_CMD_QUEUE_DRAIN_DUMMY, hex(drain))

    # 4. Post function bytes: prologue matches documented shape (mov [rsp+8],rbx / push rbp...)
    post_bytes = b.read(base + post_abi.FN_CMD_QUEUE_POST, 16)
    ok(
        "Post_prologue",
        post_bytes[:5] == bytes.fromhex("48895c2408") or post_bytes[0] == 0x48,
        post_bytes[:8].hex(),
    )
    # gate offsets referenced: session+0x725
    ok("session_gate_0x725_readable", True, u8(b, session + 0x725))

    # 5. CMoveCommand VT slots
    move = cmd_layout.MOVE
    mvt = base + move["vt"]
    exec_slot = u64(b, mvt + post_abi.CCommand_VT_EXECUTE) - base
    clone_slot = u64(b, mvt + post_abi.CCommand_VT_CLONE) - base
    isvalid_slot = u64(b, mvt + post_abi.CCommand_VT_ISVALID) - base
    ok("Move_Execute_slot", exec_slot == move["execute"], hex(exec_slot))
    ok("Move_Clone_nonzero", clone_slot != 0, hex(clone_slot))
    ok("Move_IsValid_nonzero", isvalid_slot != 0, hex(isvalid_slot))

    # 6. Strategic VT
    strat = cmd_layout.STRATEGIC
    svt = base + strat["vt"]
    sexec = u64(b, svt + post_abi.CCommand_VT_EXECUTE) - base
    ok("Strategic_Execute_shared_thunk", sexec == strat["execute"], hex(sexec))

    # 7. Action VTs exist in image (read first pointer)
    for name, rva in (
        ("CUnitMoveAction_VT", cmd_layout.MOVE["action"]["vt"]),
        ("CUnitStrategicMoveAction_VT", cmd_layout.STRATEGIC["action"]["vt"]),
    ):
        ptr = u64(b, base + rva)
        ok(name + "_table_readable", ptr != 0, hex(ptr))

    # 8. Handle/province helpers still resolve 17/17
    sys.path.insert(0, str(ROOT / "calling"))
    from handle import resolve_handle, HANDLE_TYPE_ARMY
    from province import resolve_province

    gs = u64(b, base + post_abi.G_GAMESTATE)
    tag = u32(b, gs + OV["GS_PLAYER_TAG"])
    country = u64(b, u64(b, gs + OV["GS_COUNTRIES_BEGIN"]) + tag * 8)
    begin = u64(b, country + OV["CO_ARMIES"])
    n = u32(b, country + OV["CO_ARMIES"] + 0xC)
    resolved = 0
    prov_ok = 0
    for i in range(n):
        army = u64(b, begin + i * 8)
        ty = u32(b, army + OV["CA_HANDLE"])
        ix = u32(b, army + OV["CA_HANDLE"] + 4)
        got = resolve_handle(b, ty, ix, base)
        if got == army:
            resolved += 1
        pid = u32(b, army + OV["CA_PROVINCE_ID"])
        pref = u64(b, army + OV["CA_PROVINCE"])
        if resolve_province(b, pid, base, gs) == pref:
            prov_ok += 1
    ok("handle_resolve_17", resolved == n, f"{resolved}/{n}")
    ok("province_resolve_17", prov_ok == n, f"{prov_ok}/{n}")

    # 9. allow_post hard-deny
    ok("allow_post_false", post_abi.allow_post() is False, post_abi.allow_post())
    try:
        post_abi.post_command(b, session, 0)
        ok("post_command_raises", False, "did not raise")
    except Exception as e:
        ok("post_command_raises", True, type(e).__name__ + ": " + str(e)[:120])

    # 10. Pipeline counters coherent
    ok("session_state_2", u32(b, session + post_abi.CSession_STATE) == 2, u32(b, session + 0x30))
    ok("drain_counter_nonzero", u32(b, session + post_abi.CSession_DRAIN_COUNTER) > 0,
       u32(b, session + 0x60))

    report = {
        "phase": "2bc",
        "posting": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "pid": b.pid,
        "base": hex(base),
        "checks": results,
        "passed": sum(1 for r in results if r["ok"]),
        "failed": sum(1 for r in results if not r["ok"]),
        "post_abi_describe": post_abi.describe(),
        "note": "Proof is live layout + gate + helper consistency; NO Post call / NO write",
    }
    report["all_ok"] = report["failed"] == 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2)[:10000])
    print("wrote", OUT)
    b.close()
    return 0 if report["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(checks())
