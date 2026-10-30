"""Phase 2r — pin CCommand Execute tick (READ-ONLY).

Proves CSession update 0x22c6410 state==2 path:
  server.vt+0x30 drain -> server.vt+0x40 (&+0x58) stage -> cmd.vt+0x50 Execute
  then 0x22c4710 loop over server.vt+0x78 (&+0x40) also Execute
CCommand: +0x48=IsValid (wrap 0x22d8ea0), +0x50=Execute, +0x58=post-exec
Posting DISABLED. pause/1x only.
"""
from __future__ import annotations
import argparse, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "calling"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument(
        "--out",
        default=os.path.join(ROOT, "research", "re-dumps", "phase2r_execute_tick.json"),
    )
    args = ap.parse_args()

    out = {
        "phase": "2r",
        "command_queue": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "FN_CMD_QUEUE_POST": "0x22c41e0",
        "CCommand_slots": {
            "0x48": {
                "role": "IsValid",
                "wrapper": "0x22d8ea0",
                "base": "0x25c21e0 abort",
            },
            "0x50": {
                "role": "Execute",
                "base": "0x25c21e0 abort",
                "note": "PRIOR 2q wrongly labeled +0x48 as Execute",
            },
            "0x58": {
                "role": "post-Execute hook",
                "base": "0x25c21e0 abort",
            },
        },
        "session_update": "0x22c6410",
        "execute_loop": "0x22c4710",
        "isvalid_wrap": "0x22d8ea0",
        "execute_site_A_staged": "0x22c6c9d",
        "execute_site_B_loop": "0x22c47dd",
        "sp_state2_pipeline": [
            "server = session+0x40 (live CDummyServer vt 0x2bcb040)",
            "call server.vt+0x30 RVA 0x23f64e0 drain ring+0xa0 to list +0x58/+0x60 count +0x68",
            "call server.vt+0x40 RVA 0x2e9e50 returns and this+0x58 (pending list header)",
            "stage cmds into session+0x48 array (count at session+0x54)",
            "per cmd: IsValid 0x22d8ea0 (cmd.vt+0x48); fail -> Discarding command xref 0x22c6e31",
            "Execute site A 0x22c6c9d: cmd.vt+0x50; inc session+0x6c8; cmd.vt+0x58",
            "then 0x22c4710 Execute site B via server.vt+0x78 RVA 0x247620 returns this+0x40",
        ],
        "server_list_headers": {
            "+0x40": "exec-list head/tail/count (getter vt+0x78)",
            "+0x58": "drain-pending head/tail/count (getter vt+0x40)",
        },
        "strings": {
            "Discarding command: ": {"rva": "0x2bb4678", "xref": "0x22c6e31"},
            "Executing command: ": {
                "rva": "0x2bb4660",
                "xref": "none found (likely unused)",
            },
        },
        "posting": "DISABLED",
    }

    if args.live:
        from process import Backend, find_pid

        b = Backend(find_pid("hoi4.exe"))
        base = b.image_base
        ov = json.load(
            open(os.path.join(ROOT, "calling", "offsets_verified.json"), encoding="utf-8")
        )

        def u64(a):
            return struct.unpack("<Q", b.read(a, 8))[0]

        def u32(a):
            return struct.unpack("<I", b.read(a, 4))[0]

        idler = u64(base + ov["G_IDLER"])
        app = u64(idler + 0x530)
        session = u64(app + 0x380)
        server = u64(session + 0x40)
        out["live"] = {
            "pid": b.pid,
            "image_base": hex(base),
            "idler_vt_rva": hex(u64(idler) - base),
            "server_vt_rva": hex(u64(server) - base),
            "session_state_0x30": u32(session + 0x30),
            "session_drain_counter_0x60": u32(session + 0x60),
            "session_exec_counter_0x6c8": u32(session + 0x6c8),
            "server_plus_0x40": hex(u64(server + 0x40)),
            "server_plus_0x58": hex(u64(server + 0x58)),
            "server_ring_0xc8": hex(u64(server + 0xc8)),
            "server_post_ids_0xd0": hex(u32(server + 0xd0)),
            "note": "paused lists empty; counters prove drain+execute ran earlier",
        }
        b.close()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
    summary = os.path.join(ROOT, "research", "re-dumps", "phase2r_summary.txt")
    open(summary, "w", encoding="utf-8").write(
        "Phase 2r: Execute tick pinned. CCommand Execute=vt+0x50 (not +0x48). "
        "Session update 0x22c6410 + loop 0x22c4710. FN_CMD_QUEUE_POST=0x22c41e0. "
        "Writes/posting DISABLED.\n"
    )
    print("wrote", args.out)
    print("Execute=vt+0x50; tick=0x22c6410/0x22c4710; posting DISABLED")


if __name__ == "__main__":
    main()
