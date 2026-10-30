"""Phase 2ai — ring→drain→stage walk + sticky cmd heap probe; RO; posting DISABLED."""
from __future__ import annotations
import argparse, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "calling"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--heap", action="store_true", help="full-heap scan for known cmd vtables (ALLOWED)")
    ap.add_argument("--out", default=os.path.join(ROOT, "research", "re-dumps", "phase2ai_report.json"))
    args = ap.parse_args()
    out = {
        "phase": "2ai",
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

    def disasm(rva, n=0x180, max_lines=60, stop_ret=False):
        lines = []
        for insn in md.disasm(b.read(base + rva, n), base + rva):
            lines.append(f"{hex(insn.address-base)}: {insn.mnemonic} {insn.op_str}")
            if stop_ret and insn.mnemonic == "ret":
                break
            if len(lines) >= max_lines:
                break
        return lines

    # Drain DummyServer vt+0x30 = 0x23f64e0
    drain = 0x23F64E0
    out["Dummy_drain_0x30"] = hex(drain)
    out["Dummy_drain_disasm"] = disasm(drain, 0x200, max_lines=70, stop_ret=False)

    # Find stores to [reg+0x58] or lea involving 0x58 in drain
    stores = []
    for insn in md.disasm(b.read(base + drain, 0x280), base + drain):
        if "0x58" in insn.op_str or "0x40" in insn.op_str or "0xa0" in insn.op_str:
            stores.append(f"{hex(insn.address-base)}: {insn.mnemonic} {insn.op_str}")
        if insn.mnemonic == "ret" and insn.address - base > drain + 0x40:
            break
    out["Dummy_drain_list_ops"] = stores

    # Session stage path: after drain, state2 Execute site uses pending
    # FN_EXECUTE_LOOP 0x22c4710 pulls vt+0x78 = +0x40
    # state2 path uses vt+0x40 = +0x58
    out["pipeline"] = {
        "Post": "server.vt+0x28 @ 0x23f5cd0",
        "serialize_recreate": "0x22d8ad0",
        "ring_push": "server+0xa0",
        "drain": "server.vt+0x30 @ 0x23f64e0 -> pending +0x58",
        "pending_getter": "vt+0x40 -> &server+0x58",
        "execlist_getter": "vt+0x78 -> &server+0x40",
        "FN_EXECUTE_LOOP": "0x22c4710 pulls execlist +0x40",
        "state2_Execute": "0x22c6c9d after stage from pending",
    }

    idler = u64(base + ov["G_IDLER"])
    session = u64(u64(idler + 0x530) + 0x380)
    server = u64(session + 0x40)
    live = {
        "pid": b.pid,
        "tick": u32(session + 0x84),
        "drain": u32(session + 0x60),
        "exec": u32(session + 0x6C8),
        "seq": u32(server + 0xD0),
        "session_0x725": u8(session + 0x725),
        "session_0x3c": u8(session + 0x3C),
        "session_state_0x30": u32(session + 0x30),
        "server_0x40": hex(u64(server + 0x40)),
        "server_0x58": hex(u64(server + 0x58)),
        "server_0xa0_lock": hex(u32(server + 0xA0)),
        "server_0xb0": hex(u64(server + 0xB0)),
        "server_0xc8": hex(u64(server + 0xC8)),
        "stage_count_0x54": u32(session + 0x54),
        "postexec_count_0x108": u32(session + 0x108),
    }
    out["live"] = live

    # Sticky StartGame: scan postexec list and optional heap
    postexec_head = u64(session + 0xF8)
    sticky = []
    if postexec_head:
        # walk a few nodes conservatively
        node = postexec_head
        for _ in range(8):
            if not node:
                break
            try:
                cmd = u64(node)  # layout unknown — try node+0 as cmd* or node is cmd
                vt = u64(cmd)
                sticky.append({"node": hex(node), "obj": hex(cmd), "vt": hex(vt - base)})
                node = u64(node + 8)
            except Exception as e:
                sticky.append({"error": str(e), "node": hex(node)})
                break
    out["postexec_walk"] = sticky

    heap_hits = {}
    if args.heap:
        # Full-heap scan ALLOWED — writable maps only; READ-ONLY (never b.write)
        vts = {
            "CMoveCommand": base + 0x2A2C790,
            "CCancelMovementCommand": base + 0x2A2C9B8,
            "CChatCommand": base + 0x2A27F28,
            "CStartGameCommand": base + 0x2A5F448,
            "CDummyServer": base + 0x2BCB040,
        }
        pats = {n: struct.pack("<Q", vt) for n, vt in vts.items()}
        for name in vts:
            heap_hits[name] = []
        scanned = 0
        for m in b.maps:
            perms = m.get("perms") or ""
            if "w" not in perms:
                continue
            start = m["start"]
            end = m["end"]
            size = end - start
            if size <= 0 or size > 0x20000000:
                continue
            try:
                blob = b.read(start, size)
            except Exception:
                continue
            scanned += size
            for name, pat in pats.items():
                if len(heap_hits[name]) >= 8:
                    continue
                off = 0
                while len(heap_hits[name]) < 8:
                    i = blob.find(pat, off)
                    if i < 0:
                        break
                    heap_hits[name].append(hex(start + i))
                    off = i + 8
        out["heap_scanned_MB"] = round(scanned / (1024 * 1024), 1)
        out["heap_hit_counts"] = {k: len(v) for k, v in heap_hits.items()}
        out["heap_hits"] = heap_hits

    out["safe_enable_still_blocked_because"] = [
        "No tooling Post call has been independently proven non-destructive on live SP",
        "Mid-flight Move sample absent while paused (cmds freed after Execute)",
        "Need brief 1x + player activity to capture live serialize round-trip (never 5x)",
        "Semantic labels for action vector elements (unit/province) still unnamed",
    ]

    b.close()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
    print("wrote", args.out)
    print("drain ops sample", stores[:15])
    print("live", live)
    print("heap", out.get("heap_hits") or out.get("heap_scanned_MB"))
    print("postexec", sticky[:5])


if __name__ == "__main__":
    main()
