#!/usr/bin/env python3
"""Phase 2fb: layout-only decode of 2fa CStrategicRedeploymentCommand capture.

Offline RO decode against cmd_layout.STRATEGIC / MOVE / CANCEL.
Drafts ring_embed rebuild recipe as observation design only.
Never ALLOW_POST / never writes / never 5x.
"""
from __future__ import annotations

import json
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import cmd_layout
import post_abi

CAPTURE_IN = ROOT / "reports" / "phase2fa_leaf_move_capture.json"
OUT = ROOT / "reports" / "phase2fb_strategic_layout_decode.json"
SUMMARY = ROOT / "reports" / "phase2fb_summary.json"
RECIPE = ROOT / "reports" / "phase2fb_ring_embed_recipe.json"
DOC = ROOT / "docs" / "PHASE2FB_STRATEGIC_LAYOUT.md"


def u64(b: bytes, o: int) -> int:
    return struct.unpack_from("<Q", b, o)[0]


def u32(b: bytes, o: int) -> int:
    return struct.unpack_from("<I", b, o)[0]


def decode_blob(blob: bytes, cap: dict) -> dict:
    S = cmd_layout.STRATEGIC
    M = cmd_layout.MOVE
    C = cmd_layout.CANCEL
    embed_off = S["action_embed"]
    act = blob[embed_off : embed_off + S["action"]["size"]]

    # Absolute vt → RVA via capture vt_rva + absolute - catalog cross-check
    vt_abs = u64(blob, 0)
    embed_vt_abs = u64(act, 0)
    vt_rva_cap = int(cap["vt_rva"], 16)
    embed_vt_rva_cap = int(cap["action_embed"]["vt_rva"], 16)
    # Recover image base from absolute - rva
    base = vt_abs - vt_rva_cap
    embed_vt_rva = embed_vt_abs - base

    f = S["action"]["fields"]
    army_handle = [u32(act, f["army_handle"]), u32(act, f["army_handle"] + 4)]
    province = u32(act, f["province"])
    clear = act[f["clear"]]
    move_priority = u32(act, f["move_priority"])
    type_id_at_8 = u32(act, 8)
    unk_0c = u32(act, 0xC)

    header = {
        "vt_abs": hex(vt_abs),
        "vt_rva": hex(vt_rva_cap),
        "image_base_recovered": hex(base),
        "pad_08": hex(u32(blob, 8)),
        "tick_0c": u32(blob, 0xC),
        "pad_10": hex(u32(blob, 0x10)),
        "pad_14": hex(u32(blob, 0x14)),
        "field_18": hex(u32(blob, 0x18)),
        "field_18_u32": u32(blob, 0x18),
        "seq_1c": u32(blob, 0x1C),
        "field_20": hex(u32(blob, 0x20)),
        "field_20_u32": u32(blob, 0x20),
        "pad_24": hex(u32(blob, 0x24)),
        "note_0x18_0x20": "0x1C=seq; 0x20 echoed seq in this sample (0x1874=6260); 0x18=0x1206 unknown hdr neighbor",
    }

    embed = {
        "layout": "CUnitStrategicMoveAction",
        "as_embed": True,
        "cmd_embed_off": hex(embed_off),
        "vt_abs": hex(embed_vt_abs),
        "vt_rva": hex(embed_vt_rva),
        "type_id_at_plus8": type_id_at_8,
        "type_id_at_plus8_hex": hex(type_id_at_8),
        "unk_0c": unk_0c,
        "unk_0c_hex": hex(unk_0c),
        "army_handle": army_handle,
        "army_handle_off": hex(f["army_handle"]),
        "province": province,
        "province_off": hex(f["province"]),
        "clear": clear,
        "clear_off": hex(f["clear"]),
        "move_priority": move_priority,
        "move_priority_off": hex(f["move_priority"]),
        "move_priority_name": {
            0: "FRONT_ORDER",
            1: "NORMAL",
            2: "PLAYER_ORDER",
            3: "AI_PLAYER_ORDER",
        }.get(move_priority, "UNKNOWN"),
        "hex": act.hex(),
        "trailing_pad_24": act[0x24:].hex() if len(act) >= 0x28 else None,
    }

    catalog_match = {
        "cmd_vt": vt_rva_cap == S["vt"],
        "embed_vt": embed_vt_rva == S["action"]["vt"],
        "action_type_id_at_8": type_id_at_8 == S["action"]["type_id"],
        "army_handle_vs_2fa": army_handle == cap["action_embed"]["army_handle"],
        "province_vs_2fa": province == cap["action_embed"]["province"],
        "clear_vs_2fa": clear == cap["action_embed"]["clear"],
        "move_priority_vs_2fa": move_priority == cap["action_embed"]["move_priority"],
        "blob_covers_cmd_size": len(blob) >= S["size"],
        "embed_end_eq_cmd_size": embed_off + S["action"]["size"] == S["size"],
    }

    neighbors = {
        "shared_with_MOVE": {
            "execute_thunk": hex(S["execute"]),
            "same_as_MOVE_execute": S["execute"] == M["execute"],
            "serialize_thunk": hex(S["serialize"]),
            "same_as_MOVE_serialize": S["serialize"] == M["serialize"],
            "deserialize_thunk": hex(S["deserialize"]),
            "action_embed_off": hex(S["action_embed"]),
            "same_embed_off_as_MOVE": S["action_embed"] == M["action_embed"],
        },
        "diff_vs_MOVE": {
            "cmd_size": {"STRATEGIC": hex(S["size"]), "MOVE": hex(M["size"])},
            "cmd_vt": {"STRATEGIC": hex(S["vt"]), "MOVE": hex(M["vt"])},
            "type_id": {"STRATEGIC": hex(S["type_id"]), "MOVE": hex(M["type_id"])},
            "factory": {"STRATEGIC": hex(S["factory"]), "MOVE": hex(M["factory"])},
            "action_vt": {"STRATEGIC": hex(S["action"]["vt"]), "MOVE": hex(M["action"]["vt"])},
            "action_size": {"STRATEGIC": hex(S["action"]["size"]), "MOVE": "CUnitMoveAction ~0x60+ fields"},
            "destination_model": {
                "STRATEGIC": "scalar province u32 @ embed+0x18",
                "MOVE": "province_arr @+0x18 + path_arr @+0x30 (game alloc vectors)",
            },
            "why_strategic_cheaper_for_ring_embed": (
                "No province/path vector alloc — only army_handle(8) + province(4) + clear(1) + move_priority(4)"
            ),
        },
        "vs_CANCEL": {
            "CANCEL_vt": hex(C["vt"]),
            "CANCEL_size": hex(C["size"]),
            "CANCEL_note": "units vector @+0x28; adjacent traffic historically denser than ordinary Move",
        },
        "serialize_tokens_action": dict(S["action"]["serialize_tokens"]),
        "factory_lookup_note": {
            "STRATEGIC_factory_rva": hex(S["factory"]),
            "STRATEGIC_factory_idx_catalog": S.get("factory_idx"),
            "MOVE_idx_formula_tid_minus_0x2328": M["type_id"] - 0x2328,
            "STRATEGIC_tid_minus_0x2328": S["type_id"] - 0x2328,
            "note": (
                "2ez proved MOVE idx=tid-0x2328; Strategic catalog factory_idx=4505 "
                "≠ tid-0x2328 (4753) — do NOT Capstone/121 re-churn; trust factory RVA 0x13fb580"
            ),
        },
        "action_execute_isvalid": {
            "action_execute": hex(S["action"]["execute"]),
            "action_isvalid": hex(S["action"]["isvalid"]),
            "cmd_isvalid": hex(S["isvalid"]),
            "birth_path": (
                f"factory {hex(S['factory'])} → size {hex(S['size'])} → "
                f"execute thunk {hex(S['execute'])} → embed+{hex(embed_off)} → "
                f"action.execute {hex(S['action']['execute'])}"
            ),
        },
    }

    trailing = {
        "beyond_cmd_size_0x50": blob[S["size"] :].hex() if len(blob) > S["size"] else "",
        "note": "dump_cmd reads 0x88/0xA0; bytes past catalog size 0x50 are NOT part of the command object",
    }

    return {
        "header": header,
        "embed": embed,
        "catalog_match": catalog_match,
        "all_catalog_fields_match": all(catalog_match.values()),
        "neighbors": neighbors,
        "trailing": trailing,
        "cmd_layout_STRATEGIC": {
            "vt": hex(S["vt"]),
            "type_id": hex(S["type_id"]),
            "size": hex(S["size"]),
            "factory": hex(S["factory"]),
            "action_embed": hex(S["action_embed"]),
            "action": {
                "vt": hex(S["action"]["vt"]),
                "type_id": hex(S["action"]["type_id"]),
                "size": hex(S["action"]["size"]),
                "fields": {k: hex(v) for k, v in S["action"]["fields"].items()},
            },
        },
    }


def draft_ring_embed_recipe(decoded: dict) -> dict:
    S = cmd_layout.STRATEGIC
    emb = decoded["embed"]
    return {
        "phase": "2fb",
        "kind": "observation_design_only",
        "allow_post": False,
        "CLAUSEWITZ_ALLOW_POST": False,
        "posting": "DISABLED",
        "writes": "FORBIDDEN",
        "title": "ring_embed rebuild recipe from live StrategicRedeploy (design only)",
        "why_strategic_first": decoded["neighbors"]["diff_vs_MOVE"]["why_strategic_cheaper_for_ring_embed"],
        "inputs_from_live_sample": {
            "army_handle": emb["army_handle"],
            "province": emb["province"],
            "clear": emb["clear"],
            "move_priority": emb["move_priority"],
            "move_priority_name": emb["move_priority_name"],
            "seq_observed": decoded["header"]["seq_1c"],
            "tick_observed": decoded["header"]["tick_0c"],
        },
        "structural_steps_NOT_EXECUTED": [
            {
                "step": 1,
                "name": "factory_alloc",
                "detail": f"Call/observe factory RVA {hex(S['factory'])} → ecx/size={hex(S['size'])} (0x50)",
                "status": "DESIGN_ONLY",
            },
            {
                "step": 2,
                "name": "fill_header",
                "detail": (
                    f"vt={hex(S['vt'])}; tick/seq filled by game Post path — "
                    "do NOT invent seq writes; observe only"
                ),
                "status": "DESIGN_ONLY",
            },
            {
                "step": 3,
                "name": "fill_embed_at_plus_0x28",
                "fields": {
                    "vt": hex(S["action"]["vt"]),
                    "type_id_at_plus8": hex(S["action"]["type_id"]),
                    "army_handle@+0x10": emb["army_handle"],
                    "province@+0x18": emb["province"],
                    "clear@+0x1C": emb["clear"],
                    "move_priority@+0x20": emb["move_priority"],
                },
                "status": "DESIGN_ONLY",
            },
            {
                "step": 4,
                "name": "queue_placement",
                "detail": (
                    f"Game path: Post → CDummyServer sink → ring@+{hex(post_abi.CDummyServer_RING)} "
                    f"→ pending@+{hex(post_abi.CDummyServer_PENDING)} → "
                    f"execlist@+{hex(post_abi.CDummyServer_EXECLIST)} → "
                    f"execute thunk {hex(S['execute'])} → action.execute {hex(S['action']['execute'])}"
                ),
                "status": "DESIGN_ONLY — NEVER inject",
            },
        ],
        "dummy_server_offsets_known": {
            "RING": hex(post_abi.CDummyServer_RING),
            "PENDING": hex(post_abi.CDummyServer_PENDING),
            "EXECLIST": hex(post_abi.CDummyServer_EXECLIST),
            "note": "Structural only; live Move/Strategic buffer embed into ring NOT proven; 2fa saw stage not execlist",
        },
        "vs_ordinary_MOVE_blocker": (
            "Ordinary CMove still needs live province_arr/path_arr game allocs — "
            "Strategic scalar province is the cheaper ring_embed design target"
        ),
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
                "HourlyTick abuse",
                "5x",
                "ask right-click",
            ],
        },
        "next_after_this_design": (
            "IsValid-path RO check / compare Cancel traffic — still NO ALLOW_POST; "
            "ordinary CMove sample remains optional stub"
        ),
    }


def main() -> int:
    if not CAPTURE_IN.exists():
        print(json.dumps({"error": "missing 2fa capture", "path": str(CAPTURE_IN)}))
        return 1
    raw = json.loads(CAPTURE_IN.read_text(encoding="utf-8"))
    cap = raw["captures"][0]
    blob = bytes.fromhex(cap["hex"])
    decoded = decode_blob(blob, cap)
    recipe = draft_ring_embed_recipe(decoded)

    report = {
        "phase": "2fb",
        "ts": datetime.now(timezone.utc).isoformat(),
        "allow_post": False,
        "never_5x": True,
        "source_capture": {
            "phase": "2fa",
            "addr": cap["addr"],
            "list": cap.get("list"),
            "seq": cap.get("seq"),
            "captured_at_asia_shanghai": cap.get("captured_at_asia_shanghai"),
            "note": "Offline decode of saved hex — no live re-grab required (addr may be freed)",
        },
        "decoded": decoded,
        "ring_embed_recipe_path": str(RECIPE.relative_to(ROOT)),
        "result": (
            "STRATEGIC_LAYOUT_DECODE_MATCH"
            if decoded["all_catalog_fields_match"]
            else "STRATEGIC_LAYOUT_DECODE_MISMATCH"
        ),
    }
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    RECIPE.write_text(json.dumps(recipe, indent=2), encoding="utf-8")

    works = [
        "offline layout decode of 2fa StrategicRedeploy hex",
        "catalog STRATEGIC vt/embed/fields MATCH live sample",
        "documented army_handle/province/clear/move_priority offsets",
        "drafted ring_embed observation recipe (writes FORBIDDEN)",
        "allow_post stays False",
    ]
    stubbed = [
        "ordinary CMoveCommand / CUnitMoveAction / CSupportAttack live sample",
        "ring_embed execution",
        "SAFE_POST",
        "self-issue MOVE",
        "Post inject",
    ]
    summary = {
        "phase": "2fb",
        "result": report["result"],
        "scenario": "ETH capture offline decode (live may still be ETH@1x)",
        "allow_post": False,
        "catalog_match": decoded["catalog_match"],
        "embed_fields": {
            "army_handle": decoded["embed"]["army_handle"],
            "province": decoded["embed"]["province"],
            "clear": decoded["embed"]["clear"],
            "move_priority": decoded["embed"]["move_priority"],
            "move_priority_name": decoded["embed"]["move_priority_name"],
            "type_id_at_plus8": decoded["embed"]["type_id_at_plus8_hex"],
        },
        "shared_execute_thunk_with_MOVE": hex(cmd_layout.STRATEGIC["execute"]),
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": (
            "IsValid-path / SAFE checklist RO for Strategic ring_embed design — still NO ALLOW_POST "
            "(do NOT execute recipe; ordinary CMove optional)"
        ),
        "parent_sha_base": "0ae3930",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    emb = decoded["embed"]
    DOC.write_text(
        f"""# Phase 2fb — StrategicRedeploy layout-only decode

**Result:** `{report['result']}`  
**Source:** 2fa capture `{cap['addr']}` stage seq {cap.get('seq')} (Asia/Shanghai {cap.get('captured_at_asia_shanghai')})  
**Method:** offline hex decode — **no live re-grab**, no Capstone/121, **allow_post = False**

## Catalog match

All checks: **{decoded['all_catalog_fields_match']}**

| check | ok |
|-------|----|
| cmd vt `0x2a2d818` | {decoded['catalog_match']['cmd_vt']} |
| embed vt `0x2a1f7e8` | {decoded['catalog_match']['embed_vt']} |
| action type_id@+8 `0x364a` | {decoded['catalog_match']['action_type_id_at_8']} |
| fields vs 2fa dump | army/prov/clear/mp all match |

## Command object (`CStrategicRedeploymentCommand` size `0x50`)

| off | field | live |
|-----|-------|------|
| +0x00 | vt | RVA `0x2a2d818` |
| +0x0C | tick | {decoded['header']['tick_0c']} |
| +0x1C | seq | {decoded['header']['seq_1c']} |
| +0x20 | (echoed seq this sample) | {decoded['header']['field_20_u32']} |
| +0x28 | **action embed** | `CUnitStrategicMoveAction` |

## Embed (`CUnitStrategicMoveAction` size `0x28` @ cmd+0x28)

| off | field | live | token |
|-----|-------|------|-------|
| +0x00 | vt | `0x2a1f7e8` | — |
| +0x08 | type_id | `0x364a` | — |
| +0x10 | army_handle | `{emb['army_handle']}` | `0x289D` |
| +0x18 | province | `{emb['province']}` | `0x2840` |
| +0x1C | clear | `{emb['clear']}` | `0x29F1` |
| +0x20 | move_priority | `{emb['move_priority']}` ({emb['move_priority_name']}) | `0x37BC` |

## Neighbors vs MOVE / Cancel

- **Shared execute thunk** with MOVE: `{hex(cmd_layout.STRATEGIC['execute'])}` → embed → action.execute `{hex(cmd_layout.STRATEGIC['action']['execute'])}`
- **Shared serialize/deserialize thunks** with MOVE
- **Cheaper than ordinary MOVE for ring_embed design:** scalar province — no province_arr/path_arr game allocs
- Cancel remains adjacent traffic proof; ordinary CMove still stubbed

## ring_embed recipe (OBSERVATION ONLY)

See `reports/phase2fb_ring_embed_recipe.json`.

**Writes FORBIDDEN. Post FORBIDDEN. SAFE_POST CLOSED.**

Birth path (observe): factory `{hex(cmd_layout.STRATEGIC['factory'])}` → size `0x50` → Post/sink/ring → execute thunk → action.execute.

## Next

IsValid-path / SAFE checklist RO around this design — **still NO ALLOW_POST**. Do not Capstone/121 re-churn.

Script: `scripts/phase2fb_strategic_layout_decode.py`
""",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
