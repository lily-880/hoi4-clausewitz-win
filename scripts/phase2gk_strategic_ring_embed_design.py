#!/usr/bin/env python3
"""Phase 2gk: deepen Strategic Dummy ring_embed DESIGN ONLY.

Compare sticky StartGame (2bq) structural RT vs Strategic offline (2fd).
Strengthen ring_embed recipe. Live RO Dummy ring snapshot only.
NO 2fb execute. NO Post. Never 5x. allow_post False.
"""
from __future__ import annotations

import json
import struct
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import cmd_layout
import post_abi
from config import allow_post
from process import Backend, find_pid

assert allow_post() is False

OUT = ROOT / "reports" / "phase2gk_strategic_ring_embed_design.json"
SUMMARY = ROOT / "reports" / "phase2gk_summary.json"
RECIPE = ROOT / "reports" / "phase2gk_ring_embed_recipe_v2.json"
DOC = ROOT / "docs" / "PHASE2GK_STRATEGIC_RING_EMBED_DESIGN.md"
TZ = timezone(timedelta(hours=8))


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def i32(b, a):
    return struct.unpack("<i", b.read(a, 4))[0]


def live_meta(b, base):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    hours = i32(b, gs + 0x484)
    d = datetime(1936, 1, 1) + timedelta(hours=int(hours))
    return {"hours": hours, "ui_date": d.strftime("%Y-%m-%d %H:00"), "gs": hex(gs)}


def compare_startgame_vs_strategic() -> dict:
    bq = json.loads((ROOT / "reports" / "phase2bq_live_re.json").read_text(encoding="utf-8"))
    fd = json.loads((ROOT / "reports" / "phase2fd_strategic_ring_recreate_ro.json").read_text(encoding="utf-8"))
    fb = json.loads((ROOT / "reports" / "phase2fb_ring_embed_recipe.json").read_text(encoding="utf-8"))
    sticky = bq["sticky_startgame"]
    rt = bq["live_buffer_dummy_rt"]
    off = fd["offline_rebuild"]
    S = cmd_layout.STRATEGIC
    SG = cmd_layout.STARTGAME

    return {
        "startgame_sticky_2bq": {
            "status": rt.get("status"),
            "mode": rt.get("mode"),
            "size": sticky.get("size"),
            "type_id": sticky.get("type_id"),
            "factory_match": sticky.get("factory_match"),
            "ser_des_inverse": rt.get("ser_des_inverse_offsets"),
            "header_token": rt.get("header_token"),
            "recreate_calls_factory_lookup": rt.get("recreate_calls_factory_lookup"),
            "live_inprocess_ring_embed": rt.get("live_inprocess_ring_embed"),
            "tok_ser_nop": sticky.get("tok_ser_nop"),
            "note": "Sticky post-exec StartGame is RO-observable without Post; proves recreate→factory_lookup structural path.",
        },
        "strategic_offline_2fd": {
            "status": off.get("status"),
            "bit_identical": off.get("bit_identical"),
            "size": off.get("size"),
            "type_id": hex(S["type_id"]),
            "factory_idx": S["factory_idx"],
            "fields": off.get("fields_used"),
            "live_inprocess_ring_embed": "STUBBED",
        },
        "shared_proven_RO": [
            "Dummy recreate FN 0x22d8ad0 readable + calls factory_lookup",
            "Factory table slot MATCH for Strategic idx 4753",
            "seq@+0x1C echoed @+0x20 on live land samples (Strategic/Cancel)",
            "action embed @+0x28 (Strategic/Move)",
            "Dummy RING@+0xa0 PENDING@+0x58 EXECLIST@+0x40",
            "FN_CMD_QUEUE_POST_SINK_DUMMY 0x23f5cd0 / DRAIN 0x23f64e0 (observe only)",
        ],
        "divergences": [
            {
                "item": "object lifetime without Post",
                "startgame": "sticky session@+0xf8 survives — RO sampleable",
                "strategic": "ephemeral stage/pending — needs midflight catch or Post to re-enter ring",
            },
            {
                "item": "serdes complexity",
                "startgame": "header token 0x1F3; tok_ser often NOP; size 0x28",
                "strategic": "action embed ser tokens + factory 0x50; action VT CUnitStrategicMoveAction",
            },
            {
                "item": "offline bit_identical",
                "startgame": "structural live OK (2bq) — not full hex rebuild harness",
                "strategic": "PASS bit_identical offline (2fd) from 2fa hex",
            },
        ],
        "design_implication": (
            "Strategic is the better offline rebuild target (bit_identical DONE). "
            "StartGame is the better live sticky RT sightline (no Post). "
            "Closing ring_embed still requires in-process Post/sink — HARD_DENY until human SAFE."
        ),
        "prior_recipe_ref": "reports/phase2fb_ring_embed_recipe.json",
        "prior_recipe_inputs": fb.get("inputs_from_live_sample"),
    }


def build_recipe_v2(compare: dict, ring_live: dict | None) -> dict:
    S = cmd_layout.STRATEGIC
    A = S["action"]
    fb_inputs = compare["prior_recipe_inputs"]
    steps = [
        {
            "step": 1,
            "name": "factory_alloc",
            "detail": f"factory RVA {hex(S['factory'])} size {hex(S['size'])} via table idx {S['factory_idx']}",
            "proof": "LIVE_RO_MATCH_2fd",
            "status": "DESIGN_ONLY — do not call from tooling",
        },
        {
            "step": 2,
            "name": "fill_header",
            "detail": "vt Strategic; tick@+0xC; f18@+0x18; seq@+0x1C echoed @+0x20 (game Post fills seq)",
            "proof": "OFFLINE_BIT_IDENTICAL_2fd + shared header 2gj",
            "status": "DESIGN_ONLY — do NOT invent seq writes",
        },
        {
            "step": 3,
            "name": "fill_embed_at_plus_0x28",
            "fields": {
                "vt": hex(A["vt"]),
                "type_id_at_plus8": hex(A["type_id"]),
                "army_handle@+0x10": fb_inputs["army_handle"],
                "province@+0x18": fb_inputs["province"],
                "clear@+0x1C": fb_inputs["clear"],
                "move_priority@+0x20": fb_inputs["move_priority"],
            },
            "serialize_tokens": {str(k): v for k, v in A.get("serialize_tokens", {}).items()},
            "proof": "OFFLINE_BIT_IDENTICAL_2fd",
            "status": "DESIGN_ONLY",
        },
        {
            "step": 4,
            "name": "serialize_recreate_path",
            "detail": (
                f"GetTypeId → ser → recreate({hex(cmd_layout.FACTORY_TABLE['recreate'])}) → "
                f"factory_lookup idx={S['factory_idx']} → des → object"
            ),
            "proof": "STRUCTURAL_STARTGAME_2bq + factory/recreate RO_2fd",
            "status": "DESIGN_ONLY — StartGame sticky proves recreate↔lookup without Post",
        },
        {
            "step": 5,
            "name": "queue_placement_ring_embed",
            "detail": (
                "Post → FN_CMD_QUEUE_POST_SINK_DUMMY 0x23f5cd0 → ring@+0xa0 → "
                "pending@+0x58 → drain → execlist@+0x40 → execute thunk 0x13fc990 → action.execute"
            ),
            "proof": "OFFSETS_KNOWN_2bq_2br — live buffer push NOT proven",
            "status": "STUBBED — NEVER inject / NEVER Post this slice",
        },
    ]
    return {
        "phase": "2gk",
        "kind": "observation_design_only_v2",
        "allow_post": False,
        "CLAUSEWITZ_ALLOW_POST": False,
        "posting": "DISABLED",
        "writes": "FORBIDDEN",
        "executed_2fb_recipe": False,
        "title": "ring_embed rebuild recipe v2 — Strategic + StartGame sticky concordance",
        "why_strategic_first": (
            "Offline bit_identical DONE (2fd); scalar province (no path vector); "
            "shared execute thunk with MOVE; StartGame sticky supplies recreate structural sightline"
        ),
        "inputs_from_live_sample": fb_inputs,
        "structural_steps_NOT_EXECUTED": steps,
        "dummy_server_offsets_known": {
            "VT": hex(post_abi.CDummyServer_VT),
            "RING": hex(post_abi.CDummyServer_RING),
            "PENDING": hex(post_abi.CDummyServer_PENDING),
            "EXECLIST": hex(post_abi.CDummyServer_EXECLIST),
            "POST_SINK": hex(post_abi.FN_CMD_QUEUE_POST_SINK_DUMMY),
            "DRAIN": hex(post_abi.FN_CMD_QUEUE_DRAIN_DUMMY),
            "RECREATE": hex(cmd_layout.FACTORY_TABLE["recreate"]),
        },
        "startgame_vs_strategic": {
            "implication": compare["design_implication"],
            "shared_proven_RO": compare["shared_proven_RO"],
        },
        "live_ring_snapshot": ring_live,
        "gate": {
            "allow_post": False,
            "SAFE_POST": "CLOSED",
            "tool_gate": "CLOSED",
            "forbid": [
                "ALLOW_POST",
                "CLAUSEWITZ_ALLOW_POST",
                "Post inject",
                "helper patch",
                "guess writes",
                "2fb recipe execute",
                "HourlyTick abuse",
                "5x",
                "ask right-click",
            ],
        },
        "next_after_this_design": (
            "Human SAFE enable OR midflight CMove hex — ring_embed in-process remains STUBBED; "
            "still NO ALLOW_POST"
        ),
    }


def live_ring_ro(b, base) -> dict:
    sess = u64(b, base + post_abi.G_SESSION)
    server = u64(b, sess + post_abi.CSession_SERVER)
    vt = u64(b, server)
    vt_rva = (vt - base) & 0xFFFFFFFF
    ring = server + post_abi.CDummyServer_RING
    blob = b.read(ring, 64)
    pending_n = u32(b, server + post_abi.CDummyServer_PENDING + 0xC)
    execlist_n = u32(b, server + post_abi.CDummyServer_EXECLIST + 0xC)
    # ring cap/idx from 2bq layout: +0x00 lock?, observed fields
    ring_u32 = [struct.unpack_from("<I", blob, i)[0] for i in range(0, 16, 4)]
    return {
        "session": hex(sess),
        "server": hex(server),
        "server_vt_rva": hex(vt_rva),
        "server_vt_match": vt_rva == post_abi.CDummyServer_VT,
        "ring_addr": hex(ring),
        "ring_blob_hex": blob.hex(),
        "ring_u32_head": [hex(x) for x in ring_u32],
        "pending_count": pending_n,
        "execlist_count": execlist_n,
        "drain": u32(b, sess + post_abi.CSession_DRAIN_COUNTER),
        "exec": u32(b, sess + post_abi.CSession_EXEC_COUNTER),
        "note": "RO snapshot only — no ring push / no Post / recipe NOT executed",
    }


def main():
    assert allow_post() is False
    compare = compare_startgame_vs_strategic()
    pid = find_pid()
    meta = None
    ring_live = None
    if pid:
        b = Backend()
        base = b.image_base
        meta = live_meta(b, base)
        meta["pid"] = pid
        ring_live = live_ring_ro(b, base)
    recipe = build_recipe_v2(compare, ring_live)
    RECIPE.write_text(json.dumps(recipe, indent=2), encoding="utf-8")

    result = "STRATEGIC_RING_EMBED_DESIGN_V2_STARTGAME_CONCORDANCE"
    if ring_live and not ring_live.get("server_vt_match"):
        result = "STRATEGIC_RING_EMBED_DESIGN_V2_RING_VT_MISMATCH"
    elif not pid:
        result = "STRATEGIC_RING_EMBED_DESIGN_V2_NO_LIVE_PROCESS"

    out = {
        "phase": "2gk",
        "result": result,
        "allow_post": False,
        "executed_2fb_recipe": False,
        "never_5x": True,
        "speed_policy": "pause-or-1x only (never change speed)",
        "scenario": "ITA@1x — Strategic ring_embed DESIGN v2 + StartGame sticky concordance (no Post)",
        "compare": compare,
        "live": {"meta": meta, "ring": ring_live},
        "recipe_path": str(RECIPE.relative_to(ROOT)),
        "stubbed": [
            "in-process ring_embed push",
            "2fb/2gk recipe execute",
            "ALLOW_POST",
            "tool-gate",
            "ordinary CMove midflight hex",
        ],
        "works": [
            "Strategic offline bit_identical (prior 2fd) cited",
            "StartGame sticky structural RT (prior 2bq) cited",
            "recipe v2 steps 1-4 DESIGN with proof tags; step 5 STUBBED",
            "live Dummy ring RO snapshot" if ring_live else "offline design only",
        ],
        "next_shortest_blocker": (
            "NON-Post ceiling: ring_embed in-process needs human SAFE Post OR midflight CMove hex; "
            "retry push when GitHub reachable — still NO ALLOW_POST"
        ),
        "captured_at": datetime.now(TZ).strftime("%Y-%m-%d %H:%M Asia/Shanghai"),
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2gk",
                "result": result,
                "allow_post": False,
                "executed_2fb_recipe": False,
                "pid": pid,
                "ui": meta,
                "ring_vt_match": (ring_live or {}).get("server_vt_match"),
                "pending": (ring_live or {}).get("pending_count"),
                "execlist": (ring_live or {}).get("execlist_count"),
                "recipe": str(RECIPE.relative_to(ROOT)),
                "next_shortest_blocker": out["next_shortest_blocker"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    DOC.write_text(
        f"""# Phase 2gk — Strategic ring_embed DESIGN v2 (StartGame concordance)

**Result:** `{result}`  
**allow_post:** **False** · 2fb/2gk recipe **NOT executed** · never 5x

## Why this slice

2fd already has Strategic offline **bit_identical PASS**. Remaining gap is in-process ring push (Post).  
2bq StartGame sticky proves recreate→factory_lookup **without Post**. This slice merges those proofs into recipe v2 — **DESIGN ONLY**.

## Concordance

| Track | Proof | Ring embed |
| --- | --- | --- |
| StartGame sticky (2bq) | STRUCTURAL_LIVE_OK · ser↔des token 0x1F3 · recreate→lookup | **STUBBED** |
| Strategic offline (2fd) | bit_identical PASS · factory idx 4753 MATCH | **STUBBED** |
| Shared header (2gj) | tick@+0xC · seq echo · embed@+0x28 | n/a |

**Implication:** Strategic = best offline rebuild; StartGame = best live sticky sightline.  
Closing ring_embed still needs Post/sink — **HARD_DENY**.

## Recipe v2 steps (NOT executed)

1. factory_alloc — LIVE_RO_MATCH_2fd  
2. fill_header — OFFLINE_BIT_IDENTICAL + shared header  
3. fill_embed@+0x28 — OFFLINE_BIT_IDENTICAL  
4. serialize_recreate_path — STRUCTURAL StartGame + factory RO  
5. queue_placement / ring_embed — **STUBBED** (NEVER inject)

Artifact: `reports/phase2gk_ring_embed_recipe_v2.json`

## Live Dummy ring RO

See report `live.ring` — pending/execlist counts only; no push.

## Gate

**CLOSED.** still **NO ALLOW_POST**. No tool-gate. No Capstone/121.

Next: human SAFE enable **or** midflight CMove hex — not agent Post.
""",
        encoding="utf-8",
    )
    print(json.dumps(json.loads(SUMMARY.read_text()), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
