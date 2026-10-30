#!/usr/bin/env python3
"""Phase 2ap — army command catalog + safe-enable checklist + optional 1x midflight heap poll.

READ-ONLY. Never calls Post / never WriteProcessMemory for enqueue.
Speed rule: pause or 1x only (never 5x). Full-heap scans allowed.
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import sys
import time
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "calling"))

# Interest set for land micro (names are TypeDescriptor demangle cores)
ARMY_CMD_NEEDLES = (
    "CMoveCommand",
    "CCancelMovementCommand",
    "COrderExecuteCommand",
    "COrderAssignCommand",
    "COrderUnassignCommand",
    "COrderDeleteCommand",
    "COrderGroupCommand",
    "CArmyGroupCommand",
    "CSetArmyLeaderCommand",
    "COrderNewFrontCommand",
    "COrderNewRootCommand",
    "COrderNewFallbackCommand",
    "CStrategicRedeploy",
    "CRetreat",
    "CUnitRetreat",
    "CStopMovement",
    "CUnitMove",
    "CChatCommand",
    "CStartGameCommand",
    "CChangeGameSpeed",
    "CPause",
)

# Known from prior phases (Windows 1.19.4)
KNOWN = {
    "CMoveCommand": {"vt": 0x2A2C790, "type_id": 0x28A2, "size": 0x88},
    "CCancelMovementCommand": {"vt": 0x2A2C9B8, "type_id": 0x28AF, "size": 0x48},
    "COrderExecuteCommand": {"vt": 0x2A85468, "type_id": None, "size": None},
    "CChatCommand": {"vt": 0x2A27F28, "type_id": 0x184, "size": 0x98},
    "CStartGameCommand": {"vt": 0x2A5F448, "type_id": 0x359E, "size": 0x28},
}

SAFE_ENABLE_GAPS = [
    {
        "id": "no_tooling_post",
        "status": "open",
        "note": "Tooling has never called Post on live process — independent non-destructive proof missing",
    },
    {
        "id": "midflight_move_sample",
        "status": "open",
        "note": "Need brief 1x + activity to capture live CMoveCommand before free (never 5x)",
    },
    {
        "id": "action_flag_names",
        "status": "closed",
        "note": "Named in 2am/2an via token table (clear/safe/avoid/move_priority/sticky/...)",
    },
    {
        "id": "network_execlist_path",
        "status": "n/a_sp",
        "note": "CNetworkServer +0x40 execlist unused in SP DummyServer (+0x58 pending only)",
    },
    {
        "id": "command_queue_tool_gate",
        "status": "open",
        "note": "command_queue remains DISABLED in offsets/CLI until checklist closed",
    },
]


def _token_name(b, base, tok: int) -> str:
    arr = struct.unpack("<Q", b.read(base + 0x368F5A0, 8))[0]
    e = arr + tok * 32
    size = struct.unpack("<Q", b.read(e + 16, 8))[0]
    cap = struct.unpack("<Q", b.read(e + 24, 8))[0]
    if cap > 15 or size > 15:
        ptr = struct.unpack("<Q", b.read(e, 8))[0]
        return b.read(ptr, min(int(size), 80)).split(b"\x00")[0].decode("latin1", "replace")
    return b.read(e, int(size)).decode("latin1", "replace")


def _typeid_from_vt(b, base, vt: int):
    """Read type-id writer at vt+0x58 (mov dword [rdx], imm32)."""
    slot = struct.unpack("<Q", b.read(base + vt + 0x58, 8))[0]
    fn = slot - base
    raw = b.read(base + fn, 16)
    # C7 02 imm32  or  C7 01 / C7 00 variants
    if raw[0] == 0xC7 and raw[1] in (0x02, 0x01, 0x00, 0x03):
        return struct.unpack_from("<I", raw, 2)[0], fn
    # sometimes mov eax,imm ; mov [rdx],eax
    for i in range(0, 12):
        if raw[i] == 0xB8:
            return struct.unpack_from("<I", raw, i + 1)[0], fn
    return None, fn


def catalog_rtti(pe_path: str) -> list:
    from pe import PE
    from msvc_rtti import scan_type_names, find_col_and_vtable, demangle_simple

    pe = PE(pe_path)
    seen = set()
    out = []
    for needle in ARMY_CMD_NEEDLES:
        for h in scan_type_names(pe, needle, limit=40):
            n = h["name"]
            if n in seen:
                continue
            seen.add(n)
            info = find_col_and_vtable(pe, h["td_rva"])
            vts = []
            for v in info.get("vtables") or []:
                vr = v.get("vtable_rva")
                if vr and vr not in vts:
                    vts.append(vr)
            out.append(
                {
                    "name": n,
                    "plain": demangle_simple(n),
                    "td_rva": hex(h["td_rva"]),
                    "vtables": [hex(x) for x in vts[:4]],
                }
            )
    out.sort(key=lambda x: x["plain"])
    return out


def heap_poll(p, needles: dict, rounds: int = 8, sleep_s: float = 0.35) -> dict:
    """Repeated full-heap vptr scans; READ-ONLY."""
    from mem import Proc  # type check

    assert isinstance(p, Proc)
    totals = {k: 0 for k in needles}
    first_samples = {k: [] for k in needles}
    scanned_mb = 0
    t0 = time.time()
    for r in range(rounds):
        chunk = 4 << 20
        for m in p.regions(writable=True, min_size=0x1000):
            start, end = m["start"], m["end"]
            if p.base <= start < p.base + p.image_size:
                continue
            pos = start
            while pos < end:
                nread = min(chunk, end - pos)
                data = p.try_read(pos, nread)
                scanned_mb += nread >> 20
                if data:
                    for k, needle in needles.items():
                        off = 0
                        while True:
                            i = data.find(needle, off)
                            if i < 0:
                                break
                            if i % 8 == 0:
                                totals[k] += 1
                                if len(first_samples[k]) < 3:
                                    first_samples[k].append(hex(pos + i))
                            off = i + 8
                pos += nread
        if r + 1 < rounds:
            time.sleep(sleep_s)
    return {
        "rounds": rounds,
        "elapsed_s": round(time.time() - t0, 1),
        "approx_scanned_mb_sum": scanned_mb,
        "counts_sum": {k: v for k, v in totals.items() if v},
        "samples": {k: v for k, v in first_samples.items() if v},
    }


def session_counters(p) -> dict:
    ov = json.load(open(os.path.join(ROOT, "calling", "offsets_verified.json"), encoding="utf-8"))
    idler = p.u64(p.base + ov["G_IDLER"])
    app = p.u64(idler + 0x530)
    session = p.u64(app + 0x380)
    server = p.u64(session + 0x40)
    return {
        "pid": p.pid,
        "idler": hex(idler),
        "session": hex(session),
        "server": hex(server),
        "state_0x30": p.u32(session + 0x30),
        "drain_0x60": p.u32(session + 0x60),
        "exec_0x6c8": p.u32(session + 0x6c8),
        "seq_server_0xd0": p.u32(server + 0xD0),
        "session_0x725": p.u8(session + 0x725),
        "session_0x3c": p.u32(session + 0x3C),
        "pending_0x58": hex(p.u64(server + 0x58)),
        "execlist_0x40": hex(p.u64(server + 0x40)),
        "postexec_count": p.u32(session + 0x108),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--midflight", action="store_true", help="multi-round heap poll (use at 1x)")
    ap.add_argument("--rounds", type=int, default=6)
    ap.add_argument(
        "--out",
        default=os.path.join(ROOT, "research", "re-dumps", "phase2ap_report.json"),
    )
    ap.add_argument(
        "--checklist",
        default=os.path.join(ROOT, "research", "re-dumps", "safe_enable_checklist.json"),
    )
    args = ap.parse_args()

    out = {
        "phase": "2ap",
        "posting": "DISABLED",
        "command_queue": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "FN_CMD_QUEUE_POST": "0x22c41e0",
        "FN_CMD_QUEUE_POST_role": "CSession post/drop gate — known but writes DISABLED",
        "pipeline_summary": {
            "Post_gate": "0x22c41e0",
            "Dummy_Post_vt28": "0x23f5cd0",
            "serialize_recreate": "0x22d8ad0",
            "drain_vt30": "0x23f64e0",
            "session_update": "0x22c6410",
            "execute_loop": "0x22c4710",
            "CCommand_Execute_vt50": True,
        },
        "known_cmds": KNOWN,
        "safe_enable_gaps": SAFE_ENABLE_GAPS,
    }

    if args.live:
        import config
        from mem import Proc, find_pid
        from pe import PE

        pid = find_pid("hoi4.exe")
        if not pid:
            print("hoi4.exe not running", file=sys.stderr)
            return 2
        p = Proc(pid)
        out["live"] = session_counters(p)

        # Resolve type ids for known + discover RTTI
        pe_path = p.image_path or config.binary_path()
        rtti = catalog_rtti(pe_path)
        out["rtti_army_cmds"] = rtti

        resolved = {}
        for plain, meta in KNOWN.items():
            vt = meta["vt"]
            tid, fn = _typeid_from_vt(p.be, p.base, vt)
            resolved[plain] = {
                "vt": hex(vt),
                "type_id": hex(tid) if tid is not None else None,
                "typeid_fn": hex(fn),
                "size_hyp": meta.get("size"),
            }
        # Also try first vtable of each RTTI hit not in KNOWN
        for ent in rtti:
            plain = ent["plain"]
            if plain in resolved or not ent["vtables"]:
                continue
            vt = int(ent["vtables"][0], 16)
            try:
                tid, fn = _typeid_from_vt(p.be, p.base, vt)
            except OSError:
                continue
            resolved[plain] = {
                "vt": hex(vt),
                "type_id": hex(tid) if tid is not None else None,
                "typeid_fn": hex(fn),
                "discovered": True,
            }
        out["resolved_type_ids"] = resolved

        # Early gate / vt60/vt80 catalog for army cmds we care about
        gates = {}
        for plain, info in resolved.items():
            vt = int(info["vt"], 16)
            try:
                s60 = p.u64(p.base + vt + 0x60) - p.base
                s80 = p.u64(p.base + vt + 0x80) - p.base
                # TRUE stubs often tiny mov al,1; ret
                def stub_true(rva):
                    raw = p.read(p.base + rva, 4)
                    return raw[:3] in (b"\xb0\x01\xc3", b"\x33\xc0\xc3") or (
                        raw[0] == 0xB0 and raw[2] == 0xC3
                    )

                def stub_false(rva):
                    raw = p.read(p.base + rva, 4)
                    return raw[:3] == b"\x32\xc0\xc3" or (
                        raw[0] == 0xB0 and raw[1] == 0x00 and raw[2] == 0xC3
                    )

                gates[plain] = {
                    "vt60": hex(s60),
                    "vt80": hex(s80),
                    "vt60_true_stub": stub_true(s60),
                    "vt60_false_stub": stub_false(s60),
                    "vt80_true_stub": stub_true(s80),
                    "vt80_false_stub": stub_false(s80),
                }
            except OSError as e:
                gates[plain] = {"err": str(e)}
        out["early_gate_stubs"] = gates

        if args.midflight:
            needles = {}
            for plain, info in resolved.items():
                if ("Command" in plain) or plain in (
                    "CMoveCommand",
                    "CCancelMovementCommand",
                    "CChatCommand",
                    "COrderExecuteCommand",
                ):
                    vt = int(info["vt"], 16)
                    needles[plain] = struct.pack("<Q", p.base + vt)
            # Always include action vt
            needles["CUnitMoveAction"] = struct.pack("<Q", p.base + 0x2A1F648)
            out["midflight"] = heap_poll(p, needles, rounds=max(1, args.rounds))
            # Update checklist if we caught Move
            counts = out["midflight"].get("counts_sum") or {}
            if counts.get("CMoveCommand", 0) > 0:
                for g in SAFE_ENABLE_GAPS:
                    if g["id"] == "midflight_move_sample":
                        g["status"] = "closed"
                        g["note"] = f"captured counts={counts}; samples={out['midflight'].get('samples')}"
                        g["evidence"] = "phase2ap midflight heap poll at 1x"
            out["safe_enable_gaps"] = SAFE_ENABLE_GAPS

        p.be.close()

    # Always write checklist snapshot
    checklist = {
        "phase": "2ap",
        "posting": "DISABLED",
        "command_queue": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "FN_CMD_QUEUE_POST": "0x22c41e0",
        "gaps": SAFE_ENABLE_GAPS,
        "enable_when": [
            "Independent non-destructive Post proof on live SP DummyServer path",
            "At least one mid-flight CMoveCommand captured + serialize round-trip understood",
            "Explicit CLAUSEWITZ_ALLOW_POST=1 gate (separate from ALLOW_WRITE)",
            "Never auto-enable inside per-tick loops",
        ],
    }
    os.makedirs(os.path.dirname(args.checklist), exist_ok=True)
    json.dump(checklist, open(args.checklist, "w", encoding="utf-8"), indent=2)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
    print("wrote", args.out)
    print("wrote", args.checklist)
    print("posting DISABLED; FN_CMD_QUEUE_POST known 0x22c41e0")
    if out.get("resolved_type_ids"):
        for k, v in sorted(out["resolved_type_ids"].items()):
            print(f"  {k}: vt={v.get('vt')} tid={v.get('type_id')}")
    if out.get("midflight"):
        print("midflight", json.dumps(out["midflight"].get("counts_sum"), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
