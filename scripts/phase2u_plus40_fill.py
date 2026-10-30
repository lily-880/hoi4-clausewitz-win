"""Phase 2u — pin +0x40 filler (NetworkServer, cmd+0x1a). RO."""
from __future__ import annotations
import argparse, json, os, struct, sys, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "calling"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "research", "re-dumps", "phase2u_report.json"))
    args = ap.parse_args()

    from process import Backend, find_pid
    from capstone import Cs, CS_ARCH_X86, CS_MODE_64

    b = Backend(find_pid("hoi4.exe"))
    base = b.image_base
    md = Cs(CS_ARCH_X86, CS_MODE_64)

    # Find function start for 0x23fa510 (walk back for int3/cc or prologue)
    rva = 0x23fa510
    blob = b.read(base + rva - 0x200, 0x200)
    start = None
    for i in range(len(blob) - 1, 0, -1):
        if blob[i] == 0xCC and blob[i - 1] == 0xCC:
            # next byte after int3s
            j = i + 1
            while j < len(blob) and blob[j] == 0xCC:
                j += 1
            start = rva - 0x200 + j
            break
    if start is None:
        start = 0x23fa400  # fallback
    print("fn candidate", hex(start))
    for insn in md.disasm(b.read(base + start, 0x40), base + start):
        print(f"  {hex(insn.address-base)}: {insn.mnemonic} {insn.op_str}")
        if insn.address - base > start + 0x20:
            break

    # Confirm DummyServer sink/drain never stores +0x40 as list head (already known)
    out = {
        "phase": "2u",
        "command_queue": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "server_plus_0x40_filler": {
            "pinned": True,
            "site": "0x23fa510..0x23fa5bb",
            "function_approx": hex(start),
            "object": "NetworkServer (rsi = this; same +0x40/+0x48/+0x50 and +0x58/+0x60/+0x68 layout)",
            "branch": "if cmd+0x1a != 0 → insert 0x20-node into +0x40/+0x48/+0x50; else → +0x58/+0x60/+0x68",
            "DummyServer_drain": "0x23f64e0 fills +0x58 ONLY (no +0x40 branch)",
            "consumer": "FN_EXECUTE_LOOP 0x22c4710 via CServer.vt+0x78 getter → &server+0x40",
        },
        "cmd_flag_0x1a": {
            "role": "selects execlist (+0x40) vs drain-pending (+0x58) on NetworkServer post",
            "also_gates": "session post-exec clone list (session+0xf8) after Execute",
        },
        "posting": "DISABLED",
    }
    if args.live:
        ov = json.load(open(os.path.join(ROOT, "calling", "offsets_verified.json"), encoding="utf-8"))

        def u64(a):
            return struct.unpack("<Q", b.read(a, 8))[0]

        def u32(a):
            return struct.unpack("<I", b.read(a, 4))[0]

        idler = u64(base + ov["G_IDLER"])
        session = u64(u64(idler + 0x530) + 0x380)
        server = u64(session + 0x40)
        out["live"] = {
            "pid": b.pid,
            "state": u32(session + 0x30),
            "server_plus_0x40": hex(u64(server + 0x40)),
            "server_plus_0x58": hex(u64(server + 0x58)),
            "drain": u32(session + 0x60),
            "exec": u32(session + 0x6c8),
            "note": "SP DummyServer: +0x40 stays empty unless NetworkServer path used",
        }
    b.close()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
    print("wrote", args.out)
    print("2u: +0x40 filler = NetworkServer when cmd+0x1a; posting DISABLED")


if __name__ == "__main__":
    main()
