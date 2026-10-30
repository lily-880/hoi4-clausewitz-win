"""Phase 2t — CMoveCommand→CUnitMoveAction; session post-exec list; staging. RO."""
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
        default=os.path.join(ROOT, "research", "re-dumps", "phase2t_report.json"),
    )
    args = ap.parse_args()
    out = {
        "phase": "2t",
        "command_queue": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "CMoveCommand": {
            "vt": "0x2a2c790",
            "size": "0x58",
            "ctors_lea_vt": ["0x13f6bef", "0x13f939c", "0x13fb039"],
            "factory_alloc": "0x13fb060",
            "IsValid_0x48": "0x14002f0 thunk -> CUnitMoveAction.vt+0x50 @ 0x12c2ca0",
            "Execute_0x50": "0x13fc990 thunk -> CUnitMoveAction.vt+0x48 @ 0x12c2670",
            "embedded_at_0x28": "CUnitMoveAction",
        },
        "CUnitMoveAction": {
            "vt": "0x2a1f648",
            "rtti": ".?AVCUnitMoveAction@@",
            "type_id_at_plus8": "0x3648",
            "real_execute": "0x12c2670",
            "real_isvalid": "0x12c2ca0",
            "sub_ctor": "0x12c1770",
        },
        "session_staging": {
            "+0x48": "CCommand* array begin",
            "+0x50": "capacity",
            "+0x54": "count",
            "filled_from": "server+0x58 drain-pending via FN_SESSION_UPDATE",
        },
        "session_post_exec_list": {
            "+0xf8": "head",
            "+0x100": "tail",
            "+0x108": "count",
            "node": "0x20 bytes; [0]=cloned cmd (vt+0x68), [0x10]=next",
            "filled_when": "after Execute, cmd.vt+0x60 true and cmd+8/+0x1a flags allow",
            "note": "NOT server+0x40; +0x40 filler still UNPINNED",
        },
        "execlist_plus_0x40": {
            "shape": "same 0x20 node list as +0x58 (cmd@[0], next@[0x10]); freed in FN_EXECUTE_LOOP",
            "filler": "still UNPINNED after 2t",
        },
        "pre_execute_helper": "0x23f7ed0 (called with server,cmd when session+0x38 in {0,1,2}?)",
        "posting": "DISABLED",
    }
    if args.live:
        from process import Backend, find_pid

        ov = json.load(
            open(os.path.join(ROOT, "calling", "offsets_verified.json"), encoding="utf-8")
        )
        b = Backend(find_pid("hoi4.exe"))
        base = b.image_base

        def u64(a):
            return struct.unpack("<Q", b.read(a, 8))[0]

        def u32(a):
            return struct.unpack("<I", b.read(a, 4))[0]

        idler = u64(base + ov["G_IDLER"])
        session = u64(u64(idler + 0x530) + 0x380)
        out["live"] = {
            "pid": b.pid,
            "state": u32(session + 0x30),
            "stage_count_0x54": u32(session + 0x54),
            "post_exec_count_0x108": u32(session + 0x108),
            "post_exec_head_0xf8": hex(u64(session + 0xf8)),
            "drain": u32(session + 0x60),
            "exec": u32(session + 0x6c8),
        }
        b.close()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
    print("wrote", args.out)
    print("2t: CMoveCommand->CUnitMoveAction@+0x28; session+0xf8 post-exec list; posting DISABLED")


if __name__ == "__main__":
    main()
