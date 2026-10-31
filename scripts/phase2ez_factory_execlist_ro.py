#!/usr/bin/env python3
"""Phase 2ez: MOVE factory-site RO + DummyServer execlist peek (NO Post).

A) Capstone disasm of CMoveCommand factory + limited .text xref scan for calls to it.
B) Short live poll of DummyServer EXECLIST (+0x40) / pending / stage for MOVE VTs.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))
sys.path.insert(0, str(ROOT / "scripts"))

import cmd_layout
import post_abi
from process import Backend, find_pid
import phase2bm_midflight_ready as mf

OUT = ROOT / "reports" / "phase2ez_factory_execlist_ro.json"
SUMMARY = ROOT / "reports" / "phase2ez_summary.json"
DOC = ROOT / "docs" / "PHASE2EZ_FACTORY_EXECLIST.md"

LEAF = {
    cmd_layout.MOVE["vt"]: "CMoveCommand",
    cmd_layout.MOVE["action"]["vt"]: "CUnitMoveAction",
    cmd_layout.STRATEGIC["vt"]: "CStrategicRedeploymentCommand",
    cmd_layout.STRATEGIC["action"]["vt"]: "CUnitStrategicMoveAction",
    cmd_layout.CANCEL["vt"]: "CCancelMovementCommand",
    0x2A2C848: "CMassMoveCommand",
    0x2A0FC40: "CMassCancelMovementCommand",
    0x2A2CB28: "CSupportAttackCommand",
}
WATCH_EDGE = set(LEAF.values()) | {
    "COrderAssignCommand",
    "COrderUnassignCommand",
    "CHourlyTickCommand",
}


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def try_u64(b, a):
    try:
        return u64(b, a)
    except Exception:
        return None


def live_hours(b, base):
    try:
        ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
        gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
        gs = u64(b, base + gs_rva)
        hours = u32(b, gs + 0x484)
        d = date(1936, 1, 1) + timedelta(days=hours // 24)
        return {"hours": hours, "ui_date": f"{d.isoformat()} {hours % 24:02d}:00"}
    except Exception as e:
        return {"error": str(e)}


def disasm_fn(b, base, rva, max_bytes=0x120, label=""):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_64

    addr = base + rva
    blob = b.read(addr, max_bytes)
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    md.detail = False
    out = []
    for insn in md.disasm(blob, addr):
        out.append(
            {
                "rva": hex(insn.address - base),
                "addr": hex(insn.address),
                "mnem": insn.mnemonic,
                "op": insn.op_str,
            }
        )
        if insn.mnemonic in ("ret", "retn") and len(out) > 4:
            break
        if len(out) >= 48:
            break
    # collect call/jmp targets
    calls = []
    for insn in md.disasm(blob, addr):
        if insn.mnemonic in ("call", "jmp") and insn.op_str.startswith("0x"):
            try:
                tgt = int(insn.op_str, 16)
                calls.append({"at_rva": hex(insn.address - base), "mnem": insn.mnemonic, "target_rva": hex(tgt - base)})
            except Exception:
                pass
        if insn.mnemonic == "ret":
            break
    return {"label": label, "fn_rva": hex(rva), "insns": out, "call_jmp_targets": calls}


def scan_call_xrefs(b, base, target_rva, text_rva_start=0x1000, text_size=0x2800000, stride=0x100000, max_hits=24):
    """Scan image for E8 rel32 that land on target_rva. Limited windows to stay cheap."""
    target = base + target_rva
    hits = []
    # Prefer known code ranges around land/cmd cluster + session update
    windows = [
        (0x12C0000, 0x200000),   # action / move cluster
        (0x13F0000, 0x200000),   # Move factory neighborhood
        (0x22C0000, 0x180000),   # SessionUpdate / Post / Execute loop
        (0x23F0000, 0x100000),   # DummyServer drain/sink
    ]
    for start, size in windows:
        pos = base + start
        end = pos + size
        while pos < end and len(hits) < max_hits:
            n = min(stride, end - pos)
            try:
                data = b.read(pos, n)
            except Exception:
                pos += n
                continue
            i = 0
            while i < len(data) - 5 and len(hits) < max_hits:
                if data[i] == 0xE8:
                    rel = struct.unpack_from("<i", data, i + 1)[0]
                    at = pos + i
                    dest = at + 5 + rel
                    if dest == target:
                        hits.append({"caller_rva": hex(at - base), "target_rva": hex(target_rva), "kind": "E8"})
                i += 1
            pos += n
    return hits


def walk_ptr_list(b, base, head, limit=48):
    hits, seen, cur = [], set(), head
    while cur and cur not in seen and len(hits) < limit:
        seen.add(cur)
        vt = try_u64(b, cur)
        if vt is None:
            break
        rva = vt - base
        name = LEAF.get(rva) or mf.WATCH.get(rva)
        if name and name in WATCH_EDGE:
            try:
                hits.append({"source": "execlist_or_pending", **mf.dump_cmd(b, base, cur, name)})
            except Exception as e:
                hits.append({"addr": hex(cur), "name": name, "error": str(e)})
        nxt = try_u64(b, cur + 8)
        if not nxt or nxt == cur:
            break
        cur = nxt
    return hits


def sample_execlist(b, base, sess, server):
    pending_h = try_u64(b, server + post_abi.CDummyServer_PENDING) or 0
    execlist_h = try_u64(b, server + post_abi.CDummyServer_EXECLIST) or 0
    stage = try_u64(b, sess + post_abi.CSession_STAGE_ARRAY) or 0
    scount = u32(b, sess + post_abi.CSession_STAGE_COUNT)
    counters = {
        "drain": u32(b, sess + post_abi.CSession_DRAIN_COUNTER),
        "exec": u32(b, sess + post_abi.CSession_EXEC_COUNTER),
        "seq": u32(b, server + 0xD0),
        "stage_count": scount,
        "execlist_head": hex(execlist_h) if execlist_h else None,
        "pending_head": hex(pending_h) if pending_h else None,
    }
    hits = []
    hits.extend([{**h, "list": "execlist"} for h in walk_ptr_list(b, base, execlist_h)])
    hits.extend([{**h, "list": "pending"} for h in walk_ptr_list(b, base, pending_h)])
    if stage and 0 < scount < 64:
        for i in range(scount):
            ptr = try_u64(b, stage + i * 8)
            if not ptr:
                continue
            vt = try_u64(b, ptr)
            if vt is None:
                continue
            rva = vt - base
            name = LEAF.get(rva) or mf.WATCH.get(rva)
            if not name or name not in WATCH_EDGE:
                continue
            try:
                hits.append({"list": f"stage[{i}]", **mf.dump_cmd(b, base, ptr, name)})
            except Exception as e:
                hits.append({"list": f"stage[{i}]", "addr": hex(ptr), "name": name, "error": str(e)})
    return hits, counters


def kill_midflight():
    import subprocess

    ps = (
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
        "Where-Object { $_.CommandLine -match 'phase2bm_midflight_ready' } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=45.0)
    ap.add_argument("--burst", type=int, default=16)
    ap.add_argument("--no-kill-watcher", action="store_true")
    args = ap.parse_args()

    if not args.no_kill_watcher:
        kill_midflight()
        time.sleep(0.3)

    pid = find_pid("hoi4.exe")
    if not pid:
        print(json.dumps({"error": "no hoi4"}))
        return 1
    b = Backend(pid)
    base = int(b.image_base)
    sess = u64(b, base + post_abi.G_SESSION)
    server = u64(b, sess + post_abi.CSession_SERVER)

    # --- A: factory-site RO ---
    move_factory = cmd_layout.MOVE["factory"]
    move_exec = cmd_layout.MOVE["execute"]
    action_exec = cmd_layout.MOVE["action"]["execute"]
    action_factory = None  # UnitMoveAction may not have separate factory in layout
    sites = {
        "CMoveCommand_factory": disasm_fn(b, base, move_factory, label="CMoveCommand.factory"),
        "CMoveCommand_execute_thunk": disasm_fn(b, base, move_exec, label="CMoveCommand.execute"),
        "CUnitMoveAction_execute": disasm_fn(b, base, action_exec, label="CUnitMoveAction.execute"),
        "FN_CMD_QUEUE_POST": disasm_fn(b, base, post_abi.FN_CMD_QUEUE_POST, max_bytes=0x80, label="Post"),
        "FN_EXECUTE_LOOP": disasm_fn(b, base, post_abi.FN_EXECUTE_LOOP, max_bytes=0xA0, label="ExecuteLoopB"),
    }
    # SupportAttack factory if present
    try:
        sa_fac = 0x13FB5E0
        sites["CSupportAttackCommand_factory"] = disasm_fn(b, base, sa_fac, label="CSupportAttack.factory")
    except Exception as e:
        sites["CSupportAttackCommand_factory"] = {"error": str(e)}

    xref_move_factory = scan_call_xrefs(b, base, move_factory)
    xref_move_exec = scan_call_xrefs(b, base, move_exec, max_hits=16)
    xref_action_exec = scan_call_xrefs(b, base, action_exec, max_hits=16)

    factory_graph = {
        "move_vt": hex(cmd_layout.MOVE["vt"]),
        "move_action_vt": hex(cmd_layout.MOVE["action"]["vt"]),
        "move_factory_rva": hex(move_factory),
        "move_execute_thunk_rva": hex(move_exec),
        "action_execute_rva": hex(action_exec),
        "post_rva": hex(post_abi.FN_CMD_QUEUE_POST),
        "sink_dummy_rva": hex(post_abi.FN_CMD_QUEUE_POST_SINK_DUMMY),
        "drain_rva": hex(post_abi.FN_CMD_QUEUE_DRAIN_DUMMY),
        "session_update_rva": hex(post_abi.FN_SESSION_UPDATE),
        "execute_site_a_rva": hex(post_abi.EXECUTE_SITE_A),
        "execute_loop_b_rva": hex(post_abi.FN_EXECUTE_LOOP),
        "dummy_execlist_off": hex(post_abi.CDummyServer_EXECLIST),
        "call_xrefs_to_move_factory": xref_move_factory,
        "call_xrefs_to_move_execute_thunk": xref_move_exec,
        "call_xrefs_to_action_execute": xref_action_exec,
        "hint": (
            "Birth path catalog: UI/AI constructs via factory (or factory_lookup tid) → "
            "FN_CMD_QUEUE_POST → Dummy sink → pending/stage → Execute vt+0x50 (site A) / execlist loop B. "
            "Xrefs enumerate who CALL factory/execute in scanned windows."
        ),
    }

    # --- B: short execlist observe ---
    t0 = time.time()
    polls = edge_events = burst_samples = 0
    sight = {}
    sight_first = {}
    leaf_hits = []
    execlist_nonempty_polls = 0
    prev = None
    last_counters = None
    snapshots = []

    while time.time() - t0 < args.seconds:
        polls += 1
        hits, last_counters = sample_execlist(b, base, sess, server)
        if last_counters.get("execlist_head") and last_counters["execlist_head"] != "0x0":
            # head pointer non-null doesn't mean list has watched cmds
            pass
        if any(h.get("list") == "execlist" for h in hits):
            execlist_nonempty_polls += 1
        edge = False
        if prev is not None:
            edge = (
                last_counters["drain"] != prev["drain"]
                or last_counters["exec"] != prev["exec"]
                or last_counters["seq"] != prev["seq"]
            )
        if edge:
            edge_events += 1
            for _ in range(args.burst):
                burst_samples += 1
                h2, c2 = sample_execlist(b, base, sess, server)
                last_counters = c2
                hits.extend(h2)
                if any(h.get("name") in LEAF.values() for h in h2):
                    break
        prev = dict(last_counters)

        interesting = [h for h in hits if h.get("name") != "CHourlyTickCommand"]
        if interesting and len(snapshots) < 12:
            snapshots.append(
                {
                    "t": round(time.time() - t0, 2),
                    "counters": dict(last_counters),
                    "hits": interesting[:16],
                }
            )

        for h in hits:
            name = h.get("name") or "?"
            key = f"{h.get('list')}:{name}"
            sight[key] = sight.get(key, 0) + 1
            if name not in sight_first:
                sight_first[name] = {
                    "list": h.get("list"),
                    "addr": h.get("addr"),
                    "vt_rva": h.get("vt_rva"),
                    "poll": polls,
                }
            if name in LEAF.values() and name.startswith(("CMove", "CUnitMove", "CSupport", "CMassMove", "CStrategic", "CUnitStrategic")):
                if name in (
                    "CMoveCommand",
                    "CUnitMoveAction",
                    "CSupportAttackCommand",
                    "CMassMoveCommand",
                    "CStrategicRedeploymentCommand",
                    "CUnitStrategicMoveAction",
                ):
                    leaf_hits.append(h)

        if leaf_hits:
            break

    uniq, seen = [], set()
    for h in leaf_hits:
        a = h.get("addr")
        if a in seen:
            continue
        seen.add(a)
        uniq.append(h)

    actionable = bool(xref_move_factory) or bool(uniq) or bool(snapshots)
    if uniq:
        result = "LEAF_MOVE_ON_EXECLIST_OR_QUEUE"
    elif xref_move_factory:
        result = "FACTORY_XREFS_DOCUMENTED_NO_LIVE_MOVE"
    else:
        result = "FACTORY_DISASM_DONE_SPARSE_XREFS_NO_LIVE_MOVE"

    next_recipe = {
        "name": "UI right-click → Post call-stack RO (no inject)",
        "steps": [
            "From call_xrefs_to_move_factory, pick top callers; RO-map which sit under AI/order planner vs UI",
            "OR short ETH@1x window with denser Cancel while watching execlist head only (no heap)",
            "Still never Post / never ask user to right-click / never 5x",
        ],
        "why": "Factory birth sites + Post path known; live leaf buffer still missing — need denser natural Move traffic or accept sample gap for SAFE_POST",
    }

    date_info = live_hours(b, base)
    report = {
        "phase": "2ez",
        "ts": datetime.now(timezone.utc).isoformat(),
        "allow_post": False,
        "never_5x": True,
        "pid": pid,
        "image_base": hex(base),
        "date": date_info,
        "factory_graph": factory_graph,
        "sites_summary": {
            k: {
                "fn_rva": v.get("fn_rva"),
                "insn_n": len(v.get("insns") or []),
                "call_jmp_n": len(v.get("call_jmp_targets") or []),
                "first_insns": (v.get("insns") or [])[:8],
                "calls": (v.get("call_jmp_targets") or [])[:8],
            }
            for k, v in sites.items()
            if isinstance(v, dict)
        },
        "execlist_observe": {
            "seconds": round(time.time() - t0, 1),
            "polls": polls,
            "edge_events": edge_events,
            "burst_samples": burst_samples,
            "execlist_watched_polls": execlist_nonempty_polls,
            "sight_counts": sight,
            "sight_first": sight_first,
            "snapshots_n": len(snapshots),
            "snapshots_tail": snapshots[-4:],
            "leaf_hits": uniq[:6],
            "last_counters": last_counters,
        },
        "result": result,
        "next_cheapest_recipe": next_recipe,
    }
    # Keep full site disasm in a nested file-friendly way (trim huge)
    report["sites_full_calls"] = {k: (v.get("call_jmp_targets") or []) for k, v in sites.items() if isinstance(v, dict)}
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    # also store fuller disasm separately (first 24 insns each)
    (ROOT / "reports" / "phase2ez_factory_disasm.json").write_text(
        json.dumps({k: {"fn_rva": v.get("fn_rva"), "insns": (v.get("insns") or [])[:24], "calls": v.get("call_jmp_targets")} for k, v in sites.items() if isinstance(v, dict)}, indent=2),
        encoding="utf-8",
    )

    works = [
        "MOVE factory + execute thunk + action execute Capstone RO disasm",
        f"call xrefs to factory: {len(xref_move_factory)}; to exec thunk: {len(xref_move_exec)}; to action exec: {len(xref_action_exec)}",
        f"execlist+pending+stage observe {report['execlist_observe']['seconds']}s",
        "allow_post stays False",
    ]
    if uniq:
        works.append(f"LEAF on queue: {[u.get('name') for u in uniq]}")
    stubbed = []
    if not uniq:
        stubbed.extend(["live CMoveCommand", "CUnitMoveAction", "CSupportAttackCommand"])
    stubbed.extend(["ring_embed", "SAFE_POST", "self-issue MOVE"])

    summary = {
        "phase": "2ez",
        "result": result,
        "scenario": "ITA @1x AI-on",
        "pid": pid,
        "ui_date": date_info.get("ui_date"),
        "hours": date_info.get("hours"),
        "factory_rva": hex(move_factory),
        "xref_factory_n": len(xref_move_factory),
        "xref_factory": xref_move_factory[:12],
        "xref_action_exec_n": len(xref_action_exec),
        "execlist_seconds": report["execlist_observe"]["seconds"],
        "sight_counts": sight,
        "leaf_names_hit": [u.get("name") for u in uniq],
        "allow_post": False,
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_recipe["name"] + " — still NO ALLOW_POST",
        "next_cheapest_recipe": next_recipe,
        "birth_path_hint": factory_graph["hint"],
    }
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    DOC.write_text(
        f"""# Phase 2ez — MOVE factory-site + execlist RO

**Result:** `{result}`  
**allow_post:** False

## Factory / Execute (catalog + live disasm)

| Symbol | RVA |
|--------|-----|
| CMoveCommand factory | `{hex(move_factory)}` |
| CMoveCommand execute thunk | `{hex(move_exec)}` |
| CUnitMoveAction execute | `{hex(action_exec)}` |
| FN_CMD_QUEUE_POST | `{hex(post_abi.FN_CMD_QUEUE_POST)}` |
| Dummy sink / drain | `{hex(post_abi.FN_CMD_QUEUE_POST_SINK_DUMMY)}` / `{hex(post_abi.FN_CMD_QUEUE_DRAIN_DUMMY)}` |
| Execute site A / loop B | `{hex(post_abi.EXECUTE_SITE_A)}` / `{hex(post_abi.FN_EXECUTE_LOOP)}` |
| DummyServer EXECLIST | `+{hex(post_abi.CDummyServer_EXECLIST)}` |

Call xrefs → factory (scanned windows): **{len(xref_move_factory)}**  
See `reports/phase2ez_factory_disasm.json` + `phase2ez_factory_execlist_ro.json`.

## Execlist observe ({report['execlist_observe']['seconds']}s ITA@1x)

Sight: `{sight}`  
Leaf Move: **{len(uniq)}**

## Next

{next_recipe['name']} — still **NO ALLOW_POST**.
""",
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
