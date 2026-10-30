"""Phase 2ad durable — SP drain→+0x58→Execute; DummyServer Post feeds ring. RO."""
from __future__ import annotations
import argparse, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "calling"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "research", "re-dumps", "phase2ad_report.json"))
    args = ap.parse_args()
    out = {
        "phase": "2ad",
        "command_queue": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "posting": "DISABLED — serialize/recreate path not independently proven safe",
        "sp_state2_pipeline": {
            "session_state": 2,
            "steps": [
                "server.vt+0x30 drain: pop ring (server+0xb0/+0xc8) -> cmd.vt+0x68 clone -> list server+0x58",
                "server.vt+0x40 => &server+0x58",
                "Session Update stages cmds into session+0x48 array",
                "call cmd.vt+0x50 Execute @ 0x22c6c9d",
                "also FN_EXECUTE_LOOP uses server+0x40 (MP/state4 path)",
            ],
        },
        "dummy_post_revised": {
            "worker0_is_server": True,
            "ring": "server+0xa0 lock / +0xb0 data / +0xb8 / +0xc0 / +0xc8 count",
            "stores": "helper 0x22d8ad0 recreate-from-serialize buffer (not raw pointer)",
            "then": "cmd.vt+0(edx=1) destroy original",
            "feeds_execute": "YES via ring->drain->+0x58->state2 Execute — BUT requires valid serialize",
        },
        "vt_slots": {
            "server_vt_0x30_drain": "0x23f64e0",
            "server_vt_0x40_pending_list": "0x2e9e50 lea rax,[rcx+0x58]",
            "server_vt_0x78_exec_list": "0x247620 lea rax,[rcx+0x40]",
        },
        "checklist_update": [
            "DummyServer Post can reach Execute IF serialize+recreate succeeds",
            "Hand-built Move must implement/survive vt+0x58 serialize path",
            "OR insert already-valid cmd into ring/+0x58 bypassing serialize (unproven)",
            "Prove mid-flight: Post known-good UI cmd echo OR observe ring non-empty after UI move",
            "Until proven: posting DISABLED",
        ],
    }
    if args.live:
        from process import Backend, find_pid
        from capstone import Cs, CS_ARCH_X86, CS_MODE_64

        ov = json.load(open(os.path.join(ROOT, "calling", "offsets_verified.json"), encoding="utf-8"))
        b = Backend(find_pid("hoi4.exe"))
        base = b.image_base
        md = Cs(CS_ARCH_X86, CS_MODE_64)

        def u64(a):
            return struct.unpack("<Q", b.read(a, 8))[0]

        def u32(a):
            return struct.unpack("<I", b.read(a, 4))[0]

        def u8(a):
            return b.read(a, 1)[0]

        idler = u64(base + ov["G_IDLER"])
        session = u64(u64(idler + 0x530) + 0x380)
        server = u64(session + 0x40)
        # confirm Execute site 0x22c6c9d
        site = []
        for insn in md.disasm(b.read(base + 0x22C6C80, 0x40), base + 0x22C6C80):
            site.append(f"{hex(insn.address-base)}: {insn.mnemonic} {insn.op_str}")
        out["live"] = {
            "pid": b.pid,
            "state": u32(session + 0x30),
            "server_vt": hex(u64(server) - base),
            "ring_count_0xc8": u64(server + 0xc8),
            "list_0x40": hex(u64(server + 0x40)),
            "list_0x58": hex(u64(server + 0x58)),
            "seq_0xd0": u32(server + 0xd0),
            "exec": u32(session + 0x6c8),
            "staging_0x54": u32(session + 0x54),
            "execute_site_disasm": site,
        }
        b.close()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
    print("wrote", args.out)
    print("2ad: SP pipeline ring->+0x58->Execute; Post serialize path; DISABLED")


if __name__ == "__main__":
    main()
