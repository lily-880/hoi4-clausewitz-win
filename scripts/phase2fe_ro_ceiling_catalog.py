#!/usr/bin/env python3
"""Phase 2fe: RO ceiling doc + catalog factory_idx refresh + CMove layout note.

No Post. No tool-gate. No 2fb recipe. allow_post stays False.
"""
from __future__ import annotations

import json
import struct
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import cmd_layout
from config import allow_post

OUT = ROOT / "reports" / "phase2fe_ro_ceiling.json"
SUMMARY = ROOT / "reports" / "phase2fe_summary.json"
DOC = ROOT / "docs" / "PHASE2FE_RO_CEILING.md"
SAFE_MD = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
SAFE_JSON = ROOT / "research" / "safe_enable_checklist.json"
CMOVE_NOTE = ROOT / "docs" / "PHASE2FE_CMOVE_LAYOUT_NOTE.md"


def fidx(tid: int) -> int:
    ft = cmd_layout.FACTORY_TABLE
    return tid - ft["index_bias"] if tid >= ft["index_bias_sub_if_ge"] else tid


def cmover_note() -> dict:
    M = cmd_layout.MOVE
    S = cmd_layout.STRATEGIC
    return {
        "name": M["name"],
        "vt": hex(M["vt"]),
        "type_id": hex(M["type_id"]),
        "size": hex(M["size"]),
        "factory": hex(M["factory"]),
        "factory_idx": M.get("factory_idx"),
        "factory_idx_formula": fidx(M["type_id"]),
        "action_embed": hex(M["action_embed"]),
        "action": {
            "name": M["action"]["name"],
            "vt": hex(M["action"]["vt"]),
            "fields": {k: hex(v) for k, v in M["action"]["fields"].items()},
        },
        "vs_strategic": {
            "shared_execute_thunk": hex(M["execute"]) == hex(S["execute"]),
            "execute_thunk": hex(M["execute"]),
            "MOVE_needs": "province_arr + path_arr game allocs",
            "STRATEGIC_cheaper": "scalar province @ embed+0x18",
            "live_sample": "STUBBED — do not endless-hunt this slice",
        },
        "catalog_status": "COMPLETE",
        "live_sample_status": "STUBBED",
    }


def catalog_refresh() -> dict:
    return {
        "STRATEGIC.factory_idx": {
            "was_stale": 4505,
            "now": cmd_layout.STRATEGIC["factory_idx"],
            "formula": fidx(cmd_layout.STRATEGIC["type_id"]),
            "live_proof": "2fd table slot → 0x13fb580 MATCH",
        },
        "MOVE.factory_idx": {
            "now": cmd_layout.MOVE.get("factory_idx"),
            "formula": fidx(cmd_layout.MOVE["type_id"]),
            "live_proof": "2ez idx 1402",
        },
        "CANCEL.factory_idx": {
            "now": cmd_layout.CANCEL.get("factory_idx"),
            "formula": fidx(cmd_layout.CANCEL["type_id"]),
        },
    }


def update_safe() -> None:
    marker = "## Phase 2fe — RO ceiling (Post-gated remainder)"
    section = f"""
---

{marker}

**Gate remains CLOSED. allow_post False. tool-gate CLOSED. 2fb recipe NOT executed.**

### Strategic alternate path (RO complete ceiling)

| proof | state | phase |
| --- | --- | --- |
| Live Strategic leaf + embed | DONE | 2fa |
| Layout decode MATCH | DONE | 2fb |
| IsValid path documented | DONE | 2fc |
| Offline 0x50 bit-identical rebuild | **PASS** | 2fd |
| Live factory idx→slot MATCH | **PASS** (idx **4753**) | 2fd/2fe |
| In-process ring embed / Post | **STUBBED — needs Post** | — |
| Ordinary CMove live sample | STUBBED (catalog complete) | 2fe note |

### Exact next **human-gated** step (NOT agent-auto)

```
[ ] Human reviews SAFE + 2fd offline PASS
[ ] Human sets CLAUSEWITZ_ALLOW_POST=1 for ONE controlled experiment
[ ] Dedicated slice opens tool-gate with NEVER_POST filters
[ ] ONE Strategic (preferred) or Move Post at 1x; verify; pause; unset env
```

Until then: **agents must not Post, inject, patch helpers, or execute 2fb recipe.**

Catalog: `STRATEGIC.factory_idx` corrected 4505→**4753**; MOVE/CANCEL factory_idx filled.

*Phase 2fe — documentation + catalog only. Gate stays CLOSED.*
"""
    text = SAFE_MD.read_text(encoding="utf-8")
    if marker in text:
        head = text.split(marker)[0].rstrip()
        if head.endswith("---"):
            head = head[:-3].rstrip()
        SAFE_MD.write_text(head + "\n" + section, encoding="utf-8")
    else:
        SAFE_MD.write_text(text.rstrip() + "\n" + section, encoding="utf-8")

    j = json.loads(SAFE_JSON.read_text(encoding="utf-8"))
    j["notes_2fe"] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "allow_post": False,
        "ro_ceiling": "Strategic offline rebuild PASS + live factory wiring; in-process ring embed needs Post",
        "factory_idx_strategic": cmd_layout.STRATEGIC["factory_idx"],
        "ordinary_cmove_catalog": "COMPLETE",
        "ordinary_cmove_live": "STUBBED",
        "human_gated_next": "CLAUSEWITZ_ALLOW_POST=1 after review → tool-gate → one Strategic Post @1x",
        "gate": "CLOSED",
        "executed_2fb_recipe": False,
    }
    j["allow_post"] = False
    j["posting"] = "DISABLED"
    SAFE_JSON.write_text(json.dumps(j, indent=2), encoding="utf-8")


def optional_live_date():
    try:
        from process import Backend, find_pid

        pid = find_pid("hoi4.exe")
        b = Backend(pid)
        base = int(b.image_base)
        ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
        gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
        gs = struct.unpack("<Q", b.read(base + gs_rva, 8))[0]
        hours = struct.unpack("<I", b.read(gs + 0x484, 4))[0]
        d = date(1936, 1, 1) + timedelta(days=hours // 24)
        return {"pid": pid, "hours": hours, "ui_date": f"{d.isoformat()} {hours % 24:02d}:00"}
    except Exception as e:
        return {"error": str(e)}


def main() -> int:
    assert allow_post() is False
    refresh = catalog_refresh()
    assert refresh["STRATEGIC.factory_idx"]["now"] == 4753
    assert refresh["STRATEGIC.factory_idx"]["formula"] == 4753
    cm = cmover_note()
    update_safe()
    live = optional_live_date()

    CMOVE_NOTE.write_text(
        f"""# Phase 2fe — Ordinary CMove layout note (catalog only)

**Live sample:** STUBBED — not hunted this slice.  
**Catalog:** COMPLETE.

| field | value |
|-------|-------|
| vt | `{cm['vt']}` |
| type_id | `{cm['type_id']}` |
| size | `{cm['size']}` |
| factory | `{cm['factory']}` |
| factory_idx | **{cm['factory_idx']}** (formula {cm['factory_idx_formula']}) |
| action embed | `{cm['action_embed']}` → `{cm['action']['name']}` `{cm['action']['vt']}` |

Action fields: `{json.dumps(cm['action']['fields'])}`

vs Strategic: shared execute thunk `{cm['vs_strategic']['execute_thunk']}`; Move needs province/path **vectors**; Strategic scalar province is cheaper for any future Post experiment.

allow_post **False**.
""",
        encoding="utf-8",
    )

    report = {
        "phase": "2fe",
        "ts": datetime.now(timezone.utc).isoformat(),
        "allow_post": False,
        "executed_2fb_recipe": False,
        "tool_gate": "CLOSED",
        "catalog_refresh": refresh,
        "cmove_layout_note": cm,
        "ro_ceiling": {
            "strategic_path": "COMPLETE through offline rebuild + factory RO (2fa–2fd)",
            "blocked_on": "in-process Dummy ring embed / Post (human-gated)",
            "ordinary_cmove_live": "STUBBED",
        },
        "human_gated_next": [
            "Human reviews SAFE + 2fd PASS",
            "Human sets CLAUSEWITZ_ALLOW_POST=1 for one experiment",
            "Dedicated slice opens tool-gate with NEVER_POST",
            "ONE Strategic Post @1x; verify; pause; unset env",
        ],
        "live": live,
        "result": "RO_CEILING_DOCUMENTED_CATALOG_FACTORY_IDX_FIXED_SAFE_STILL_CLOSED",
    }
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    DOC.write_text(
        f"""# Phase 2fe — RO ceiling + catalog refresh

**Result:** `{report['result']}`  
**allow_post:** **False** · tool-gate **CLOSED** · never 5x · recipe **NOT executed**

## Catalog refresh

- `STRATEGIC.factory_idx` **4505 → 4753** (2fd live MATCH)
- `MOVE.factory_idx` = **1402**
- `CANCEL.factory_idx` = **1415**

## Ordinary CMove

Catalog complete — see `docs/PHASE2FE_CMOVE_LAYOUT_NOTE.md`. Live sample **not** hunted.

## RO ceiling

Strategic path DONE through offline rebuild + factory wiring.  
**Remaining value that needs Post is human-gated** — agents stop at this ceiling.

### Exact next human-gated step

1. Human reviews SAFE + 2fd PASS  
2. Human sets `CLAUSEWITZ_ALLOW_POST=1` for one experiment  
3. Dedicated slice opens tool-gate (NEVER_POST)  
4. ONE Strategic Post @1x → verify → pause → unset  

## Live

{json.dumps(live)}

Script: `scripts/phase2fe_ro_ceiling_catalog.py`
""",
        encoding="utf-8",
    )

    summary = {
        "phase": "2fe",
        "result": report["result"],
        "scenario": "catalog+SAFE RO ceiling (ETH@1x if live)",
        "allow_post": False,
        "tool_gate": "CLOSED",
        "pid": live.get("pid"),
        "ui_date": live.get("ui_date"),
        "hours": live.get("hours"),
        "strategic_factory_idx": 4753,
        "works": [
            "fixed STRATEGIC.factory_idx 4505→4753",
            "filled MOVE/CANCEL factory_idx",
            "CMove catalog layout note (no live hunt)",
            "SAFE RO ceiling + exact human-gated next step",
            "allow_post stays False; recipe not executed",
        ],
        "stubbed": [
            "in-process ring embed",
            "2fb recipe execution",
            "ordinary CMove live sample",
            "SAFE_POST / ALLOW_POST",
            "self-MOVE",
            "tool-gate open",
            "Post inject",
        ],
        "next_shortest_blocker": (
            "HUMAN-GATED: review SAFE + set CLAUSEWITZ_ALLOW_POST=1 for one Strategic Post @1x "
            "(agent RO ceiling reached) — still NO auto ALLOW_POST"
        ),
        "parent_sha_base": "90078c3",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
