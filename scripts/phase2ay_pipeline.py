"""Phase 2ay: promote Post->Execute SP pipeline + RO heap census (writes DISABLED)."""
from __future__ import annotations
import json, struct, sys, time
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
OUT = ROOT / "reports" / "phase2ay_pipeline.json"
DUMP = ROOT / "research" / "re-dumps" / "phase2ay_pipeline.json"


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def rtti_name(b, base, obj):
    try:
        vt = u64(b, obj)
        col = u64(b, vt - 8)
        td = u64(b, col + 0x10)
        raw = b.read(td + 0x10, 64)
        return raw.split(b"\x00", 1)[0].decode("latin1", "replace")
    except Exception:
        return None


def disasm(b, base, rva, n=0x100):
    code = b.read(base + rva, n)
    lines = []
    for insn in md.disasm(code, base + rva):
        lines.append(f"0x{insn.address - base:x}: {insn.mnemonic} {insn.op_str}")
        if insn.mnemonic == "ret" and len(lines) > 8:
            break
        if len(lines) >= 48:
            break
    return lines


def find_call_xrefs(b, base, target_rva, scan_start=0x100000, scan_end=0x2600000):
    hits = []
    start = scan_start
    while start < scan_end:
        chunk = min(0x200000, scan_end - start)
        data = b.read(base + start, chunk)
        i = 0
        while True:
            j = data.find(b"\xe8", i)
            if j < 0 or j + 5 > len(data):
                break
            rel = struct.unpack_from("<i", data, j + 1)[0]
            abs_rva = start + j + 5 + rel
            if abs_rva == target_rva:
                hits.append(start + j)
            i = j + 1
        start += chunk
    return hits


def main():
    ov = json.loads(OV_PATH.read_text(encoding="utf-8"))
    pid = find_pid("hoi4.exe")
    b = Backend(pid)
    base = int(b.image_base)
    report = {
        "phase": "2ay",
        "pid": pid,
        "base": hex(base),
        "posting": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "FN_CMD_QUEUE_POST": hex(ov["FN_CMD_QUEUE_POST"]),
    }

    idler = u64(b, base + ov["G_IDLER"])
    app = u64(b, idler + 0x530)
    session = u64(b, app + 0x380)
    server = u64(b, session + 0x40)
    report["live"] = {
        "idler": hex(idler),
        "idler_rtti": rtti_name(b, base, idler),
        "app": hex(app),
        "app_rtti": rtti_name(b, base, app),
        "session": hex(session),
        "session_rtti": rtti_name(b, base, session),
        "server": hex(server),
        "server_rtti": rtti_name(b, base, server),
        "server_vt_rva": hex(u64(b, server) - base),
        "session_state_0x30": u32(b, session + 0x30),
        "session_drain_counter_0x60": u32(b, session + 0x60),
        "session_exec_counter_0x6c8": u32(b, session + 0x6c8),
        "session_executing_flag_0x6cc": u32(b, session + 0x6cc),
        "session_stage_count_0x54": u32(b, session + 0x54),
        "session_postexec_count_0x108": u32(b, session + 0x108),
        "pending_head_0x58": hex(u64(b, server + 0x58)),
        "pending_tail_0x60": hex(u64(b, server + 0x60)),
        "pending_count_0x68": u32(b, server + 0x68),
        "execlist_head_0x40": hex(u64(b, server + 0x40)),
        "execlist_tail_0x48": hex(u64(b, server + 0x48)),
        "execlist_count_0x50": u32(b, server + 0x50),
        "ring_count_0xc8": u64(b, server + 0xc8),
        "ring_seqish_0xd0": u32(b, server + 0xd0),
    }

    g_cq = 0x34FFBE8
    try:
        cq = u64(b, base + g_cq)
        report["G_COMMAND_QUEUE_hyp"] = {
            "rva": hex(g_cq),
            "ptr": hex(cq),
            "rtti": rtti_name(b, base, cq) if cq else None,
            "matches_session": cq == session,
        }
    except Exception as e:
        report["G_COMMAND_QUEUE_hyp"] = {"error": str(e)}

    report["disasm"] = {
        "Post_0x22c41e0": disasm(b, base, 0x22C41E0, 0x140),
        "SessionUpdate_0x22c6410_head": disasm(b, base, 0x22C6410, 0x100),
        "ExecuteSiteA_0x22c6c80": disasm(b, base, 0x22C6C80, 0x80),
        "ExecuteLoop_0x22c4710": disasm(b, base, 0x22C4710, 0x80),
        "Drain_0x23f64e0_head": disasm(b, base, 0x23F64E0, 0x100),
        "Sink_0x23f5cd0_head": disasm(b, base, 0x23F5CD0, 0x100),
    }

    t0 = time.time()
    post_xrefs = find_call_xrefs(b, base, 0x22C41E0, 0x100000, 0x2600000)
    drain_xrefs = find_call_xrefs(b, base, 0x23F64E0, 0x100000, 0x2600000)
    report["xrefs"] = {
        "Post_call_count": len(post_xrefs),
        "Post_call_sample": [hex(x) for x in post_xrefs[:30]],
        "Drain_call_count": len(drain_xrefs),
        "Drain_call_sample": [hex(x) for x in drain_xrefs[:30]],
        "xref_scan_sec": round(time.time() - t0, 2),
    }

    vt_map = {
        "CMoveCommand": 0x2A2C790,
        "CCancelMovement": 0x2A2C9B8,
        "CStrategicRedeploymentCommand": ov.get("CStrategicRedeploymentCommand_VT", 0x2A2D818),
        "CHourlyTickCommand": ov.get("CHourlyTickCommand_VT", 0x29F3710),
        "COrderExecuteCommand": 0x2A85468,
        "CChatCommand": 0x2A27F28,
        "CStartGameCommand": 0x2A5F448,
        "CCommand_base": 0x279F4A0,
    }
    patterns = {name: struct.pack("<Q", base + rva) for name, rva in vt_map.items()}
    hits = {name: [] for name in patterns}

    regions = list(b.regions())
    report["heap_scan"] = {"region_count": len(regions)}
    scanned = 0
    t1 = time.time()
    img_lo, img_hi = base, base + 0x38A3000
    for entry in regions:
        base_addr = int(entry["start"])
        size = int(entry["end"]) - base_addr
        perms = entry.get("perms") or ""
        if size <= 0 or size > 0x20000000:
            continue
        if img_lo <= base_addr < img_hi:
            continue
        if "r" not in perms:
            continue
        off = 0
        while off < size:
            chunk = min(0x100000, size - off)
            try:
                data = b.read(base_addr + off, chunk)
            except Exception:
                break
            scanned += chunk
            for name, pat in patterns.items():
                start_i = 0
                while len(hits[name]) < 40:
                    j = data.find(pat, start_i)
                    if j < 0:
                        break
                    if ((base_addr + off + j) % 8) == 0:
                        hits[name].append(hex(base_addr + off + j))
                    start_i = j + 8
            off += chunk
        if time.time() - t1 > 180:
            report["heap_scan"]["timeout"] = True
            break

    report["heap_scan"]["bytes_scanned"] = scanned
    report["heap_scan"]["sec"] = round(time.time() - t1, 2)
    report["heap_scan"]["hits"] = {k: {"count": len(v), "sample": v[:8]} for k, v in hits.items()}

    samples = {}
    for name in ("CMoveCommand", "CStrategicRedeploymentCommand", "CHourlyTickCommand", "CCancelMovement", "CCommand_base"):
        for addr_s in hits.get(name, [])[:3]:
            addr = int(addr_s, 16)
            try:
                blob = b.read(addr, 0x90)
                samples.setdefault(name, []).append({
                    "obj": addr_s,
                    "words": [hex(struct.unpack_from("<Q", blob, i)[0]) for i in range(0, 0x40, 8)],
                    "rtti": rtti_name(b, base, addr),
                })
            except Exception as e:
                samples.setdefault(name, []).append({"obj": addr_s, "error": str(e)})
    report["object_samples"] = samples

    report["pipeline_summary"] = [
        "UI/AI -> FN_CMD_QUEUE_POST 0x22c41e0(session, cmd)",
        "Post -> server.vt+0x28 sink 0x23f5cd0 enqueues into DummyServer ring at +0xa0",
        "Session update 0x22c6410 (state==2): server.vt+0x30 drain 0x23f64e0 clones ring -> pending +0x58",
        "Stage into session+0x48; IsValid vt+0x48; Execute site A 0x22c6c9d via cmd.vt+0x50",
        "Second loop 0x22c4710 via execlist +0x40 (getter vt+0x78)",
        "CMoveCommand Execute 0x13fc990 thunks into embedded CUnitMoveAction",
    ]
    report["safe_enable_gaps_still_open"] = [
        "no_tooling_post (independent non-destructive Post proof)",
        "midflight_move_sample (SP Dummy frees army cmds inside tick)",
    ]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    DUMP.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, indent=2)
    OUT.write_text(text, encoding="utf-8")
    DUMP.write_text(text, encoding="utf-8")
    slim = {k: report[k] for k in report if k != "disasm"}
    slim["disasm_keys"] = list(report["disasm"].keys())
    print(json.dumps(slim, indent=2)[:12000])
    print("wrote", OUT)
    b.close()


if __name__ == "__main__":
    main()
