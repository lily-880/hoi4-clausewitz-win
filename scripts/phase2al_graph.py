"""Phase 2al — consolidated Post→Execute RO graph + safe-enable gaps. No posting."""
from __future__ import annotations
import argparse, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "calling"))

GRAPH = {
    "speed_rule": "pause or 1x only; never 5x",
    "posting": "DISABLED until independently proven safe",
    "entry_FN_CMD_QUEUE_POST": {
        "rva": "0x22c41e0",
        "role": "CSession post/drop gate (session, cmd*)",
        "early_bypass_any_of": ["r8b", "session+0x725", "cmd.vt+0x80 TRUE", "cmd.vt+0x60 TRUE"],
        "during_exec_drop": "session+0x6cc && !session+0x726",
        "auth_skip": "session+0x3c==1 skips vt+0x90",
        "delivery": "server(session+0x40).vt+0x28(cmd)",
    },
    "DummyServer_Post": {
        "vt": "0x2bcb040",
        "Post_vt28": "0x23f5cd0",
        "stamps": "cmd+0x18 from server; seq via lock xadd server+0xd0 -> cmd+0x1c/+0x20",
        "serialize_recreate": "0x22d8ad0",
        "typeid_factory_lookup": "0x22d8d20",
        "typeid_factory_table": "0x35011e0",
        "ring_push": "server+0xa0",
        "destroy_original": "cmd.vt+0(edx=1)",
    },
    "serialize_slots": {
        "Write_shared_vt10": "0x22d9390 tags 0x1f3 header, 0x41 then vt+0xa0",
        "Read_shared_vt20": "0x22d90f0; payload via vt+0xa8",
        "Move_write_thunk": "0x1404590 -> action.vt+0xc0 0x12c3920",
        "Move_read_thunk": "0x1403570 -> action.vt+0xb8 0x12c3340",
    },
    "Move": {
        "vt": "0x2a2c790",
        "type_id": "0x28a2",
        "size": "0x88",
        "factory": "0x13fb000",
        "action_at": "+0x28",
        "action_vt": "0x2a1f648",
        "Execute_thunk": "0x13fc990 -> action.vt+0x48 0x12c2670",
        "apply": "0x12af450",
        "handle_resolve": "0x6e4800",
    },
    "drain_stage_execute": {
        "session_update": "0x22c6410 calls vt+0x30 @ 0x22c6521/543/64b",
        "drain": "0x23f64e0; store pending [server+0x58] @ 0x23f6629",
        "pending_getter_vt40": "lea [rcx+0x58]",
        "execlist_getter_vt78": "lea [rcx+0x40]",
        "stage": "session+0x48 / count +0x54",
        "state2_Execute_site": "0x22c6c9d",
        "execute_loop": "0x22c4710 pulls vt+0x78 then cmd.vt+0x50",
        "postexec_clone_vt68": "session+0xf8; StartGame Clone 0x16dd0d0 sticky",
    },
    "safe_enable_gaps": [
        "Tooling has never called Post on live process — no independent non-destructive proof",
        "No mid-flight Move captured (paused frees cmds; needs brief 1x + UI activity, never 5x)",
        "Action flag bytes +0x51..+0x55 names still TBD",
        "NetworkServer +0x40 execlist path unused in SP (Dummy uses +0x58 pending)",
        "command_queue remains DISABLED in tooling",
    ],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "research", "re-dumps", "phase2al_report.json"))
    args = ap.parse_args()
    out = {"phase": "2al", **GRAPH}
    if args.live:
        from process import Backend, find_pid
        ov = json.load(open(os.path.join(ROOT, "calling", "offsets_verified.json"), encoding="utf-8"))
        b = Backend(find_pid("hoi4.exe"))
        base = b.image_base

        def u64(a): return struct.unpack("<Q", b.read(a, 8))[0]
        def u32(a): return struct.unpack("<I", b.read(a, 4))[0]
        def u8(a): return b.read(a, 1)[0]

        idler = u64(base + ov["G_IDLER"])
        session = u64(u64(idler + 0x530) + 0x380)
        server = u64(session + 0x40)
        out["live"] = {
            "pid": b.pid,
            "tick": u32(session + 0x84),
            "drain": u32(session + 0x60),
            "exec": u32(session + 0x6C8),
            "seq": u32(server + 0xD0),
            "session_state_0x30": u32(session + 0x30),
            "session_0x725": u8(session + 0x725),
            "session_0x3c": u8(session + 0x3C),
            "lists_empty": u64(server + 0x40) == 0 and u64(server + 0x58) == 0,
            "postexec_count": u32(session + 0x108),
            "server_vt": hex(u64(server) - base),
            "paused_ok": u32(session + 0x84) == 1,
        }
        # spot-check key RVAs still map
        checks = {
            "FN_CMD_QUEUE_POST": 0x22C41E0,
            "Dummy_Post": 0x23F5CD0,
            "Move_factory": 0x13FB000,
            "Action_serialize": 0x12C3920,
            "typeid_table": 0x35011E0,
        }
        live_ok = {}
        for name, rva in checks.items():
            try:
                b.read(base + rva, 1)
                live_ok[name] = True
            except Exception as e:
                live_ok[name] = str(e)
        out["rva_readable"] = live_ok
        b.close()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
    print("wrote", args.out)
    if args.live:
        print("live", out["live"])
        print("rva_ok", out["rva_readable"])
    print("2al consolidated graph; posting DISABLED")


if __name__ == "__main__":
    main()
