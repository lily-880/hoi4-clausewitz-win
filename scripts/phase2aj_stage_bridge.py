"""Phase 2aj — pending +0x58 → session stage → Execute bridge. RO; posting DISABLED."""
from __future__ import annotations
import argparse, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "calling"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "research", "re-dumps", "phase2aj_report.json"))
    args = ap.parse_args()
    out = {
        "phase": "2aj",
        "command_queue": "DISABLED",
        "posting": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
    }
    if not args.live:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
        return

    from process import Backend, find_pid
    from capstone import Cs, CS_ARCH_X86, CS_MODE_64

    ov = json.load(open(os.path.join(ROOT, "calling", "offsets_verified.json"), encoding="utf-8"))
    b = Backend(find_pid("hoi4.exe"))
    base = b.image_base
    md = Cs(CS_ARCH_X86, CS_MODE_64)

    def u64(a): return struct.unpack("<Q", b.read(a, 8))[0]
    def u32(a): return struct.unpack("<I", b.read(a, 4))[0]
    def u8(a): return b.read(a, 1)[0]

    def disasm(rva, n=0x200, max_lines=80, stop_ret=False):
        lines = []
        for insn in md.disasm(b.read(base + rva, n), base + rva):
            lines.append(f"{hex(insn.address-base)}: {insn.mnemonic} {insn.op_str}")
            if stop_ret and insn.mnemonic == "ret":
                break
            if len(lines) >= max_lines:
                break
        return lines

    # Session update / state machine
    update = 0x22C6410
    exec_loop = 0x22C4710
    state2_site = 0x22C6C9D

    out["FN_SESSION_UPDATE"] = hex(update)
    out["FN_EXECUTE_LOOP"] = hex(exec_loop)
    out["STATE2_EXECUTE_SITE"] = hex(state2_site)

    # Disasm around state2 Execute site — back up to function-ish start
    # Show ±0x80 around site
    start = state2_site - 0x60
    out["state2_context"] = disasm(start, 0x120, max_lines=50, stop_ret=False)

    # Find references to session+0x48 / +0x54 (stage) in update and nearby
    # Scan update fn for 0x48/0x54/0x58 displacements
    upd_ops = []
    for insn in md.disasm(b.read(base + update, 0x400), base + update):
        s = insn.op_str
        if any(x in s for x in ("0x48", "0x54", "0x58", "0x6c8", "0xf8", "0x40")):
            upd_ops.append(f"{hex(insn.address-base)}: {insn.mnemonic} {s}")
        if insn.mnemonic == "ret" and insn.address - base > update + 0x80:
            break
        if len(upd_ops) >= 40:
            break
    out["session_update_stage_ops"] = upd_ops

    # Execute loop head — how it pulls server list
    out["execute_loop_head"] = disasm(exec_loop, 0x120, max_lines=40, stop_ret=False)
    el_ops = []
    for insn in md.disasm(b.read(base + exec_loop, 0x200), base + exec_loop):
        if any(x in insn.op_str for x in ("0x78", "0x40", "0x50", "0x48", "0x58")):
            el_ops.append(f"{hex(insn.address-base)}: {insn.mnemonic} {insn.op_str}")
        if insn.mnemonic == "ret" and insn.address - base > exec_loop + 0x40:
            break
    out["execute_loop_list_ops"] = el_ops

    # Who calls drain vt+0x30? Search for call sites — hard without xref db.
    # Instead: in session update, look for call [rax+0x30]
    drain_calls = []
    for insn in md.disasm(b.read(base + update, 0x600), base + update):
        if insn.mnemonic == "call" and "qword ptr [rax + 0x30]" in insn.op_str:
            drain_calls.append(hex(insn.address - base))
        if insn.mnemonic == "call" and "qword ptr [rax + 0x28]" in insn.op_str:
            drain_calls.append(f"{hex(insn.address-base)} POST_SLOT")
        if len(drain_calls) >= 15:
            break
    out["session_update_vt30_calls"] = drain_calls

    # StartGame sticky: vt+0x68 Clone?
    sg_vt = 0x2A5F448
    sg_68 = u64(base + sg_vt + 0x68)
    move_68 = u64(base + 0x2A2C790 + 0x68)
    out["Clone_vt68"] = {
        "StartGame": hex(sg_68 - base) if sg_68 else None,
        "Move": hex(move_68 - base) if move_68 else None,
        "stub_true": "0x188d90",
        "note": "postexec list keeps clones; StartGame sticky observed",
    }
    if sg_68 and base <= sg_68 < base + 0x4000000:
        out["StartGame_Clone_disasm"] = disasm(sg_68 - base, 0x80, max_lines=25, stop_ret=True)

    # Live snapshot
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
        "stage_count": u32(session + 0x54),
        "postexec_count": u32(session + 0x108),
        "lists": {"+0x40": hex(u64(server + 0x40)), "+0x58": hex(u64(server + 0x58))},
        "session_0x725": u8(session + 0x725),
    }

    out["bridge_summary"] = {
        "1": "Post -> ring +0xa0 (recreated cmd)",
        "2": "Session update calls server.vt+0x30 drain",
        "3": "Drain moves ring entries onto pending +0x58",
        "4": "State2 path stages pending into session +0x48/+0x54 then Execute @ 0x22c6c9d",
        "5": "FN_EXECUTE_LOOP also consumes execlist +0x40 (Network path / cmd+0x1a!=0)",
        "6": "After Execute, vt+0x68 Clone may land in postexec +0xf8 (StartGame sticky)",
    }

    b.close()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
    print("wrote", args.out)
    print("vt30_calls", drain_calls)
    print("upd_ops", len(upd_ops), "sample", upd_ops[:12])
    print("el_ops", el_ops[:12])
    print("Clone", out["Clone_vt68"])
    print("live", out["live"])


if __name__ == "__main__":
    main()
