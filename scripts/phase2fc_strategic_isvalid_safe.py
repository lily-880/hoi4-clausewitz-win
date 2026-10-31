#!/usr/bin/env python3
"""Phase 2fc: StrategicRedeploy IsValid-path RO + SAFE checklist update.

Catalog/docs only. Never ALLOW_POST / never execute ring_embed / never 5x.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import cmd_layout
import post_abi

OUT = ROOT / "reports" / "phase2fc_strategic_isvalid_path.json"
SUMMARY = ROOT / "reports" / "phase2fc_summary.json"
DOC = ROOT / "docs" / "PHASE2FC_STRATEGIC_ISVALID_SAFE.md"
SAFE_MD = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
SAFE_JSON = ROOT / "research" / "safe_enable_checklist.json"
RECIPE_2FB = ROOT / "reports" / "phase2fb_ring_embed_recipe.json"


def hx(v) -> str:
    if isinstance(v, str):
        return v if v.startswith("0x") else hex(int(v, 0))
    return hex(int(v))


def build_isvalid_map() -> dict:
    S = cmd_layout.STRATEGIC
    M = cmd_layout.MOVE
    iv = cmd_layout.ISVALID_PATHS
    wrap = iv["wrap"]
    s_iv = iv["CStrategicRedeploymentCommand"]
    m_iv = iv["CMoveCommand"]

    def norm_calls(xs):
        out = []
        for x in xs:
            out.append(hx(int(x, 16) if isinstance(x, str) else x))
        return out

    s_calls = norm_calls(s_iv["isvalid_calls"])
    m_calls = norm_calls(m_iv["isvalid_calls"])
    shared = [c for c in s_calls if c in m_calls]
    s_only = [c for c in s_calls if c not in m_calls]

    return {
        "wrap_isvalid": hx(wrap),
        "wrap_note": "Global IsValid wrap (catalog); used by queue validation plumbing",
        "command": {
            "name": S["name"],
            "vt": hx(S["vt"]),
            "type_id": hx(S["type_id"]),
            "type_id_dec": S["type_id"],
            "size": hx(S["size"]),
            "cmd_isvalid_fn": hx(S["isvalid"]),
            "cmd_isvalid_matches_ISVALID_PATHS": S["isvalid"]
            == (int(s_iv["isvalid"]) if not isinstance(s_iv["isvalid"], str) else int(s_iv["isvalid"], 0)),
            "shared_execute_thunk": hx(S["execute"]),
            "same_execute_thunk_as_MOVE": S["execute"] == M["execute"],
            "factory": hx(S["factory"]),
        },
        "action_embed": {
            "name": S["action"]["name"],
            "vt": hx(S["action"]["vt"]),
            "type_id": hx(S["action"]["type_id"]),
            "type_id_note": "live 2fa/2fb embed +0x08 == 0x364a",
            "size": hx(S["action"]["size"]),
            "embed_off": hx(S["action_embed"]),
            "action_isvalid_fn": hx(S["action"]["isvalid"]),
            "action_execute_fn": hx(S["action"]["execute"]),
            "isvalid_kind": S["action"].get("isvalid_kind"),
            "execute_kind": S["action"].get("execute_kind"),
            "fields": {k: hx(v) for k, v in S["action"]["fields"].items()},
        },
        "call_path_observation": {
            "order": [
                "Queue/Dummy validation may hit wrap IsValid 0x22d8ea0",
                f"CStrategicRedeploymentCommand.IsValid FN {hx(S['isvalid'])} (vt slot → thunk/body)",
                f"Embed CUnitStrategicMoveAction.IsValid FN {hx(S['action']['isvalid'])} (catalog kind FN)",
                f"On execute: shared thunk {hx(S['execute'])} → embed+{hx(S['action_embed'])} → action.execute {hx(S['action']['execute'])}",
            ],
            "isvalid_callees_catalog": s_calls,
            "post_gate_candidates_catalog": norm_calls(s_iv["post_gate_candidates"]),
            "vs_MOVE_isvalid_callees": {
                "shared": shared,
                "strategic_only": s_only,
                "move_callee_count": len(m_calls),
                "note": (
                    "Strategic IsValid callee set is SMALLER than MOVE "
                    "(3 vs 11 catalog entries) — cheaper gate surface; "
                    "do NOT Capstone re-churn callees"
                ),
            },
        },
        "must_be_true_before_any_future_Post": [
            {
                "id": "layout_match",
                "status": "DONE_2fb",
                "must": "cmd vt/size/embed offsets + action fields match live sample",
            },
            {
                "id": "live_leaf_sample",
                "status": "DONE_2fa_strategic",
                "must": "At least one live Strategic (or Move) leaf with populated embed",
                "have": "CStrategicRedeploymentCommand stage capture seq=6260",
            },
            {
                "id": "isvalid_path_documented",
                "status": "DONE_2fc",
                "must": "IsValid FN + action IsValid + wrap documented (this slice)",
            },
            {
                "id": "ring_recreate_proof",
                "status": "STUBBED",
                "must": (
                    "Captured/hand-built Strategic buffer survives Dummy recreate "
                    f"({hx(0x22d8ad0)}) into ring@+{hx(post_abi.CDummyServer_RING)} without corruption — "
                    "OBSERVATION/design only until SAFE opens"
                ),
            },
            {
                "id": "isvalid_live_pass_observation",
                "status": "STUBBED",
                "must": (
                    "Optional RO: observe game-issued Strategic passing IsValid on stage "
                    "(already implied by 2fa live leaf) — do NOT call IsValid from agent"
                ),
            },
            {
                "id": "human_allow_post_env",
                "status": "HARD_DENY",
                "must": "Human sets CLAUSEWITZ_ALLOW_POST=1 only after prior greens; allow_post() still hard-False until then",
            },
            {
                "id": "tool_gate_dedicated_slice",
                "status": "CLOSED_NOT_OPENED",
                "must": "Dedicated future slice opens tool-gate; NEVER this docs slice",
            },
            {
                "id": "never_post_filters",
                "status": "DONE_inventory",
                "must": "NEVER_POST speed/HourlyTick/Ping/Pause enforced",
            },
        ],
        "ordinary_CMove_layout_note": {
            "status": "catalog_complete_live_sample_stubbed",
            "vt": hx(M["vt"]),
            "type_id": hx(M["type_id"]),
            "size": hx(M["size"]),
            "action_vt": hx(M["action"]["vt"]),
            "action_embed": hx(M["action_embed"]),
            "fields": {k: hx(v) for k, v in M["action"]["fields"].items()},
            "why_strategic_preferred_now": (
                "MOVE needs province_arr/path_arr game allocs; Strategic is scalar province — "
                "cheaper ring_embed design target per 2fb"
            ),
            "do_not": "endless-hunt ordinary Move samples this slice",
        },
        "allow_post": False,
        "execute_recipe": False,
    }


def update_safe_md(iv_map: dict) -> None:
    text = SAFE_MD.read_text(encoding="utf-8")
    marker = "## Phase 2fc — Strategic alternate path (CHECKLIST ONLY)"
    section = f"""
---

{marker}

**Gate remains CLOSED. allow_post stays False. Do not execute ring_embed.**

### Progress vs original enable sequence

| Step | Original | 2fc state |
| --- | --- | --- |
| 1 midflight leaf | CMove (+ embed) | **Strategic leaf CAPTURED (2fa)** + layout MATCH (2fb); ordinary CMove still STUBBED |
| 2 recreate/ring embed | Move or equivalent | **DESIGN drafted (2fb recipe)** — execution STUBBED; needs Dummy recreate proof |
| 3 human ALLOW_POST env | required | **HARD_DENY** — unset / ignored |
| 4 tool-gate | CLOSED | **CLOSED_NOT_OPENED** |
| 5 one land Post | forbidden | **FORBIDDEN** |

### Strategic IsValid path (observation)

- Wrap: `{iv_map['wrap_isvalid']}`
- Cmd IsValid: `{iv_map['command']['cmd_isvalid_fn']}` (type_id `{iv_map['command']['type_id']}`)
- Action IsValid: `{iv_map['action_embed']['action_isvalid_fn']}` (embed type_id `{iv_map['action_embed']['type_id']}`)
- Shared execute thunk w/ MOVE: `{iv_map['command']['shared_execute_thunk']}` → action.execute `{iv_map['action_embed']['action_execute_fn']}`
- Catalog IsValid callees: `{', '.join(iv_map['call_path_observation']['isvalid_callees_catalog'])}` (strategic-only `{', '.join(iv_map['call_path_observation']['vs_MOVE_isvalid_callees']['strategic_only']) or '—'})`

### Still blocking any Post (Strategic path)

1. Dummy ring recreate proof on Strategic sample — STUBBED  
2. Human `CLAUSEWITZ_ALLOW_POST=1` — HARD_DENY  
3. Tool-gate dedicated open — CLOSED  
4. NEVER invent writes / helper patches / recipe execution from agents  

Docs: `docs/PHASE2FC_STRATEGIC_ISVALID_SAFE.md`, `reports/phase2fc_strategic_isvalid_path.json`, `reports/phase2fb_ring_embed_recipe.json`.

*Phase 2fc — documentation only. Gate stays CLOSED.*
"""
    if marker in text:
        # replace from marker to EOF-ish previous 2fc if re-run: keep head, append fresh by cutting old
        head = text.split(marker)[0].rstrip()
        # also strip trailing --- before marker if present
        if head.endswith("---"):
            head = head[: -3].rstrip()
        SAFE_MD.write_text(head + "\n" + section, encoding="utf-8")
    else:
        SAFE_MD.write_text(text.rstrip() + "\n" + section, encoding="utf-8")


def update_safe_json(iv_map: dict) -> None:
    j = json.loads(SAFE_JSON.read_text(encoding="utf-8"))
    j["notes_2fc"] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "allow_post": False,
        "strategic_leaf": "CAPTURED_2fa",
        "strategic_layout": "MATCH_2fb",
        "strategic_isvalid_path": "DOCUMENTED_2fc",
        "cmd_isvalid": iv_map["command"]["cmd_isvalid_fn"],
        "action_isvalid": iv_map["action_embed"]["action_isvalid_fn"],
        "action_type_id": iv_map["action_embed"]["type_id"],
        "wrap": iv_map["wrap_isvalid"],
        "ring_embed_recipe": "DESIGN_ONLY_2fb",
        "ring_recreate_proof": "STUBBED",
        "ordinary_CMove_live": "STUBBED",
        "tool_gate": "CLOSED_NOT_OPENED",
        "gate": "CLOSED",
    }
    # refresh enable_when / blocks to acknowledge Strategic alternate without opening
    ew = j.get("enable_when") or []
    new_ew = []
    for item in ew:
        if isinstance(item, str) and "Mid-flight CMoveCommand" in item:
            new_ew.append(
                "Mid-flight leaf: Strategic CAPTURED+layout MATCH (2fa/2fb); ordinary CMove still STUBBED — ring recreate still required"
            )
        else:
            new_ew.append(item)
    if not any("Strategic CAPTURED" in str(x) for x in new_ew):
        new_ew.insert(
            1,
            "Mid-flight leaf: Strategic CAPTURED+layout MATCH (2fa/2fb); ordinary CMove still STUBBED — ring recreate still required",
        )
    j["enable_when"] = new_ew

    blocks = j.get("blocks_enabling_post") or []
    updated = False
    for b in blocks:
        if isinstance(b, dict) and b.get("id") == "midflight_CMoveCommand":
            b["status"] = "PARTIAL_strategic_ok_ordinary_move_stubbed"
            b["must"] = (
                "Live mid-flight leaf: Strategic DONE (2fa/2fb); ordinary CMove optional; "
                "IsValid path documented (2fc); ring recreate still required"
            )
            b["note"] = (
                "2fc: Strategic IsValid cmd 0x1402260 / action 0x12c2c20 / type_id 0x364a; "
                "gate CLOSED; allow_post False"
            )
            updated = True
    if not updated:
        blocks.insert(
            0,
            {
                "id": "midflight_CMoveCommand",
                "status": "PARTIAL_strategic_ok_ordinary_move_stubbed",
                "must": "Strategic DONE; ordinary CMove optional; ring recreate required",
                "note": "2fc IsValid path documented; gate CLOSED",
            },
        )
    # ensure ring block still stubbed
    has_ring = False
    for b in blocks:
        if isinstance(b, dict) and b.get("id") == "serialize_recreate_roundtrip":
            has_ring = True
            b["status"] = "structural_sticky_ok_strategic_design_only_execution_stubbed"
            b["note"] = (
                (b.get("note") or "")
                + " | 2fb ring_embed recipe DESIGN ONLY; 2fc forbids execution"
            )
    if not has_ring:
        blocks.append(
            {
                "id": "serialize_recreate_roundtrip",
                "status": "structural_sticky_ok_strategic_design_only_execution_stubbed",
                "must": "Prove Strategic (or Move) survives Dummy recreate into ring",
                "note": "2fb design only; 2fc forbids execution",
            }
        )
    j["blocks_enabling_post"] = blocks
    j["posting"] = "DISABLED"
    j["allow_post"] = False
    SAFE_JSON.write_text(json.dumps(j, indent=2), encoding="utf-8")


def main() -> int:
    iv_map = build_isvalid_map()
    OUT.write_text(json.dumps({"phase": "2fc", "allow_post": False, **iv_map}, indent=2), encoding="utf-8")
    update_safe_md(iv_map)
    update_safe_json(iv_map)

    recipe_exists = RECIPE_2FB.exists()
    DOC.write_text(
        f"""# Phase 2fc — Strategic IsValid path + SAFE checklist (RO)

**Result:** `STRATEGIC_ISVALID_PATH_DOCUMENTED_SAFE_STILL_CLOSED`  
**allow_post:** **False** · tool-gate **CLOSED** · never 5x · recipe **NOT executed**

## IsValid path (catalog + 2fb)

| piece | RVA |
|-------|-----|
| wrap IsValid | `{iv_map['wrap_isvalid']}` |
| CStrategicRedeploymentCommand.IsValid | `{iv_map['command']['cmd_isvalid_fn']}` |
| cmd type_id | `{iv_map['command']['type_id']}` (`0x35b9`) |
| CUnitStrategicMoveAction.IsValid | `{iv_map['action_embed']['action_isvalid_fn']}` |
| action type_id (@embed+8) | `{iv_map['action_embed']['type_id']}` |
| shared execute thunk (w/ MOVE) | `{iv_map['command']['shared_execute_thunk']}` |
| action.execute | `{iv_map['action_embed']['action_execute_fn']}` |

### Call path (observation only)

1. Queue/Dummy may hit wrap `{iv_map['wrap_isvalid']}`
2. Cmd IsValid `{iv_map['command']['cmd_isvalid_fn']}`
3. Action IsValid `{iv_map['action_embed']['action_isvalid_fn']}`
4. Execute: thunk `{iv_map['command']['shared_execute_thunk']}` → embed+`{iv_map['action_embed']['embed_off']}` → `{iv_map['action_embed']['action_execute_fn']}`

Catalog IsValid callees: `{', '.join(iv_map['call_path_observation']['isvalid_callees_catalog'])}`  
vs MOVE: shared `{', '.join(iv_map['call_path_observation']['vs_MOVE_isvalid_callees']['shared'])}`; strategic-only `{', '.join(iv_map['call_path_observation']['vs_MOVE_isvalid_callees']['strategic_only'])}`.

**Do not Capstone/121 re-churn these callees.**

## Must be true before any future Post

| id | status |
|----|--------|
| layout_match | DONE_2fb |
| live_leaf_sample | DONE_2fa_strategic |
| isvalid_path_documented | DONE_2fc |
| ring_recreate_proof | **STUBBED** |
| human ALLOW_POST env | **HARD_DENY** |
| tool-gate open | **CLOSED_NOT_OPENED** |

## Ordinary CMove (cheap note)

Catalog layout complete (`vt {iv_map['ordinary_CMove_layout_note']['vt']}`, size `{iv_map['ordinary_CMove_layout_note']['size']}`). Live sample still stubbed — **not hunted this slice**. Strategic remains cheaper ring_embed design target.

## SAFE updates

- `docs/SAFE_POST_ENABLE_CHECKLIST.md` — 2fc section appended; gate CLOSED
- `research/safe_enable_checklist.json` — `notes_2fc` + blocks refreshed; `allow_post: false`

2fb recipe present: **{recipe_exists}** — still DESIGN ONLY.

## Next shortest blocker

Dummy **ring recreate proof** design/observe for Strategic sample — **still NO ALLOW_POST**, do not execute recipe.

Script: `scripts/phase2fc_strategic_isvalid_safe.py`
""",
        encoding="utf-8",
    )

    summary = {
        "phase": "2fc",
        "result": "STRATEGIC_ISVALID_PATH_DOCUMENTED_SAFE_STILL_CLOSED",
        "scenario": "catalog/docs RO (live ETH@1x unchanged)",
        "allow_post": False,
        "tool_gate": "CLOSED",
        "cmd_isvalid": iv_map["command"]["cmd_isvalid_fn"],
        "action_isvalid": iv_map["action_embed"]["action_isvalid_fn"],
        "action_type_id": iv_map["action_embed"]["type_id"],
        "wrap_isvalid": iv_map["wrap_isvalid"],
        "shared_execute_thunk": iv_map["command"]["shared_execute_thunk"],
        "works": [
            "mapped Strategic IsValid cmd/action/wrap from catalogs",
            "documented must-be-true-before-Post gates",
            "updated SAFE_POST_ENABLE_CHECKLIST.md (still CLOSED)",
            "updated research/safe_enable_checklist.json notes_2fc",
            "ordinary CMove catalog note only — no Move hunt",
            "allow_post stays False; recipe not executed",
        ],
        "stubbed": [
            "ring_recreate_proof execution",
            "ring_embed execution",
            "ordinary CMove live sample",
            "SAFE_POST enable",
            "self-MOVE",
            "Post inject",
            "tool-gate open",
        ],
        "next_shortest_blocker": (
            "Dummy ring recreate proof (Strategic sample) — still NO ALLOW_POST; do not execute 2fb recipe"
        ),
        "parent_sha_base": "10a1a12",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
