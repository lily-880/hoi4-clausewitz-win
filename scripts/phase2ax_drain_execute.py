"""Phase 2ax: DummyServer drain → pending list; hunt Execute consumer (RO)."""
from __future__ import annotations
import json, struct, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))
from process import Backend, find_pid  # noqa: E402

try:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_64
except ImportError:
    print("capstone missing"); sys.exit(1)

md = Cs(CS_ARCH_X86, CS_MODE_64)
OV_PATH = ROOT / "calling" / "offsets_verified.json"


def load_ov():
    return json.loads(OV_PATH.read_text(encoding="utf-8"))


def find_lea_xrefs(b, base, target_rva: int, scan_start=0x2000000, scan_end=0x2800000):
    """Find rip-relative LEA/MOV that mention target (best-effort pattern for call sites)."""
    hits = []
    # Also find call <target> relative
    for start in range(scan_start, scan_end, 0x100000):
        chunk = min(0x100000, scan_end - start)
        data = b.read(base + start, chunk)
        # E8 rel32 call
        i = 0
        while True:
            j = data.find(b"\xe8", i)
            if j < 0 or j + 5 > len(data):
                break
            rel = struct.unpack_from("<i", data, j + 1)[0]
            abs_rva = start + j + 5 + rel
            if abs_rva == target_rva:
                hits.append(("call", start + j))
            i = j + 1
        # FF 15 / indirect skip for now
    return hits


def disasm_fn(b, base, rva, n=0x120):
    code = b.read(base + rva, n)
    lines = []
    for insn in md.disasm(code, base + rva):
        lines.append(f"0x{insn.address-base:x}: {insn.mnemonic} {insn.op_str}")
        if insn.mnemonic == "ret" and len(lines) > 5:
            break
    return lines


def main():
    ov = load_ov()
    pid = find_pid("hoi4.exe")
    b = Backend(pid)
    base = b.image_base
    report = {"pid": pid, "base": hex(base)}

    drain = ov["FN_CMD_QUEUE_POST_DRAIN_DUMMY"]
    sink = ov["FN_CMD_QUEUE_POST_SINK_DUMMY"]
    post = ov["FN_CMD_QUEUE_POST"]
    report["drain_rva"] = hex(drain)
    report["sink_rva"] = hex(sink)
    report["post_rva"] = hex(post)

    # Document drain ABI (verified by disasm)
    report["drain_abi"] = {
        "ring_lock": "+0xa0 (dword spinlock)",
        "ring_buf": "+0xb0",
        "ring_maskish": "+0xb8",
        "ring_head": "+0xc0",
        "ring_count": "+0xc8",
        "clone_vt": "+0x68",
        "pending_head": "+0x58",
        "pending_tail": "+0x60",
        "pending_count": "+0x68 (dword)",
        "destroy_orig_vt0": True,
        "execute_in_drain": False,
        "note": "Drain clones into pending list; Execute is NOT in drain",
    }

    # Live DummyServer: find via sink function's this — walk from idler fields
    idler = struct.unpack("<Q", b.read(base + ov["G_IDLER"], 8))[0]
    report["idler"] = hex(idler)

    # Heuristic: scan idler object for ptr to object whose vt has sink at some slot
    # Known: DummyServer.vt+0x28 == sink 0x23f5cd0
    sink_abs = base + sink
    candidates = []
    blob = b.read(idler, 0x400)
    for off in range(0, 0x400, 8):
        p = struct.unpack_from("<Q", blob, off)[0]
        if p < 0x10000 or p > 0x7fffffffffff:
            continue
        try:
            vt = struct.unpack("<Q", b.read(p, 8))[0]
            slot5 = struct.unpack("<Q", b.read(vt + 0x28, 8))[0]
            if slot5 == sink_abs:
                candidates.append((off, p, vt - base))
        except Exception:
            pass
    report["dummy_from_idler"] = [
        {"idler_off": hex(o), "obj": hex(p), "vt_rva": hex(v)} for o, p, v in candidates
    ]

    # Also scan GS neighborhood
    gs = struct.unpack("<Q", b.read(base + ov["G_GAMESTATE"], 8))[0]
    blob = b.read(gs, 0x800)
    for off in range(0, 0x800, 8):
        p = struct.unpack_from("<Q", blob, off)[0]
        if p < 0x10000:
            continue
        try:
            vt = struct.unpack("<Q", b.read(p, 8))[0]
            slot5 = struct.unpack("<Q", b.read(vt + 0x28, 8))[0]
            if slot5 == sink_abs:
                candidates.append((0x10000 + off, p, vt - base))
        except Exception:
            pass
    # dedupe by obj
    seen = set()
    uniq = []
    for o, p, v in candidates:
        if p in seen:
            continue
        seen.add(p)
        uniq.append((o, p, v))
    report["dummy_candidates"] = [
        {"tag": hex(o), "obj": hex(p), "vt_rva": hex(v)} for o, p, v in uniq
    ]

    for o, p, v in uniq[:3]:
        # Dump pending list
        head = struct.unpack("<Q", b.read(p + 0x58, 8))[0]
        tail = struct.unpack("<Q", b.read(p + 0x60, 8))[0]
        count = struct.unpack("<I", b.read(p + 0x68, 4))[0]
        ring_c = struct.unpack("<Q", b.read(p + 0xc8, 8))[0]
        report.setdefault("live_dummy", []).append({
            "obj": hex(p),
            "pending_head": hex(head),
            "pending_tail": hex(tail),
            "pending_count": count,
            "ring_count": ring_c,
        })

    # Xrefs to drain
    xrefs = find_lea_xrefs(b, base, drain, 0x2200000, 0x2600000)
    report["drain_call_xrefs_sample"] = [{"kind": k, "rva": hex(r)} for k, r in xrefs[:20]]
    report["drain_call_xref_count"] = len(xrefs)

    # Disasm callers briefly
    callers = []
    for kind, rva in xrefs[:8]:
        # back up a bit to function start heuristic
        callers.append({"site": hex(rva), "context": disasm_fn(b, base, max(0, rva - 0x40), 0xa0)[:25]})
    report["drain_callers_ctx"] = callers

    # Strategic VT slot 13 = clone (+0x68)
    if "CStrategicRedeploymentCommand_VT" in ov:
        vt = ov["CStrategicRedeploymentCommand_VT"]
        clone = struct.unpack("<Q", b.read(base + vt + 0x68, 8))[0]
        report["strategic_clone_rva"] = hex(clone - base)
        # Common Execute candidates: often after serialize slots — dump first 8
        slots = []
        for i in range(16):
            slots.append(hex(struct.unpack("<Q", b.read(base + vt + i * 8, 8))[0] - base))
        report["strategic_vt0_15"] = slots

    out = ROOT / "reports" / "phase2ax_drain_execute.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in report if k != "drain_callers_ctx"}, indent=2))
    print("wrote", out)
    b.close()


if __name__ == "__main__":
    main()
