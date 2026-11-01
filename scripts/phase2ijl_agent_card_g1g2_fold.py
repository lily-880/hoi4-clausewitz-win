#!/usr/bin/env python3
"""Phase 2ijl NON-Post: agent card polish folding G1 Strategic-only + G2 RO prep.

Catalog READY/PARKED/HARD_DENY with G1–G6 gate states after 2ijj/2ijk.
Cheap live clock + MOVE-family factory/FN RO reaffirm. NO Post / Instant /
PATH densify / midflight / ring_embed execute / ask ALLOW_POST.
"""
from __future__ import annotations

import importlib.util
import json
import struct
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import post_abi
from config import allow_post
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2ijl_agent_card_g1g2_fold.json"
SUMMARY = ROOT / "reports" / "phase2ijl_agent_card_g1g2_fold_summary.json"
DOC = ROOT / "docs" / "PHASE2IJL_AGENT_CARD_G1G2_FOLD.md"

GS_YEAR = 0x478
GS_DAY = 0x484
GS_PLAYER_TAG = 0x518


def load_hb():
    spec = importlib.util.spec_from_file_location(
        "p2hb", ROOT / "scripts/phase2hb_move_family_fn_polish.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def i32(b, a):
    return struct.unpack("<i", b.read(a, 4))[0]


def continuum_live(b, base, pid, tag, scenario):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    year = i32(b, gs + GS_YEAR)
    day_index = i32(b, gs + GS_DAY)
    ui = None
    if 1 <= year <= 3000 and 0 <= day_index < 400:
        try:
            ui = (datetime(year, 1, 1) + timedelta(days=int(day_index))).strftime("%Y-%m-%d")
        except Exception:
            ui = None
    pending = stage = drain = exec_c = None
    try:
        sess = u64(b, base + post_abi.G_SESSION)
        server = u64(b, sess + post_abi.CSession_SERVER)
        pending = u32(b, server + post_abi.CDummyServer_PENDING + 0x10) if server else None
        stage = u32(b, sess + post_abi.CSession_STAGE_COUNT)
        drain = u32(b, sess + post_abi.CSession_DRAIN_COUNTER)
        exec_c = u32(b, sess + post_abi.CSession_EXEC_COUNTER)
    except Exception:
        pass
    clock_class = "CONTINUOUS" if not (year == 1936 and day_index < 48) else "RELOAD_OR_NEW_CAMPAIGN"
    return {
        "pid": pid,
        "year": year,
        "day_index": day_index,
        "ui_date": ui,
        "clock_class": clock_class,
        "clock_source": "GS+0x478 year + GS+0x484 day_index",
        "speed_policy": "pause-or-1x only (never write speed beyond pause/1x)",
        "country_tag_filter": tag,
        "scenario": scenario,
        "pending": pending,
        "stage_count": stage,
        "drain": drain,
        "exec": exec_c,
        "allow_post": False,
    }


def agent_card():
    return {
        "READY": [
            {
                "id": "CLOCK",
                "what": "year@+0x478, day_index@+0x484, ui_date; drain/exec/pending; CONTINUOUS when day>=48",
            },
            {
                "id": "PATH200",
                "what": "CArmy+0x60 nonempty/multi; latest STABLE multi 2643→[3945,2679] oi=448 (2ijg); no further densify as unlock",
            },
            {
                "id": "OG50MI",
                "what": "OG+0x50 ≡ CArmy+0xB8 MI VT 0x29d6fb8 membership proxy (name STUBBED)",
            },
            {
                "id": "FACTORY_FN",
                "what": "MOVE/SA/Cancel/Strategic + Assign/Unassign/Execute factory + VT FN MATCH (2ha/2hb; reaffirm 2ijl)",
            },
            {
                "id": "STRAT_G1",
                "what": "G1 Strategic-only ACCEPTABLE (2ijj): offline 2fd bit_identical + 2gk DESIGN + live Strat 4753/FN MATCH — alternate to ordinary CMove midflight for SAFE Post *discussion*",
            },
            {
                "id": "RING_LAYOUT",
                "what": "Dummy ring@+0xa0 INLINE_BLOB RO (2hf; reaffirm 2ijk) — layout only, not embed",
            },
            {
                "id": "G2_RO_PREP",
                "what": "G2 RO prep HIT (2ijk): INLINE_BLOB + SAFE Post needs catalog (offsets/VT/size/factory) — live push still STUBBED",
            },
            {
                "id": "VT_CATALOG",
                "what": "INST_VT=0x2A02558 CP_VT=0x29EE248 catalog-only until wartime/midflight",
            },
            {
                "id": "PATH_NE_INST",
                "what": "PATH/OG50 perception ≠ Instant-validated order honesty",
            },
        ],
        "PARKED": [
            {
                "id": "INSTANT",
                "resume_when": "wartime OR human midflight CMove (G3); peacetime Instant/Inst70/ARR88/tri70 empty re-polls FORBIDDEN",
            },
            {
                "id": "MIDFLIGHT_EMPTY",
                "resume_when": "human leave / plan-dense window; 2gt+2gv HONEST_EMPTY ceiling",
            },
            {
                "id": "PATH_OG50_DENSIFY",
                "resume_when": "never as unlock path — diminishing returns after 2ijg STABLE",
            },
            {
                "id": "ASSIGN_OI_QUIET",
                "resume_when": "non-quiet Assign oi≠0 sight",
            },
            {
                "id": "G2_LIVE",
                "resume_when": "human SAFE Post (G4) then in-process ring_embed push proof — RO prep alone insufficient",
            },
        ],
        "HARD_DENY": [
            {"id": "ALLOW_POST", "rule": "allow_post / CLAUSEWITZ_ALLOW_POST must stay False until human G4"},
            {"id": "POST_INJECT", "rule": "Post inject / helper patch / guess writes"},
            {"id": "RING_EMBED_LIVE", "rule": "ring_embed live / 2fb/2gk recipe execute"},
            {"id": "TOOL_GATE", "rule": "tool-gate open / HourlyTick abuse"},
            {"id": "SPEED5X", "rule": "5x / speed-mem write beyond pause/1x"},
            {"id": "INVENT_NAMES", "rule": "invent OG+0x50 or other field names"},
            {"id": "CAPSTONE121", "rule": "Capstone/121 re-churn"},
            {"id": "ASK_USER_POST", "rule": "ask user to right-click or enable Post from automated slices"},
        ],
        "GATES_G1_G6": {
            "G1": {
                "state": "ACCEPTABLE via Strategic-only (2ijj)",
                "note": "ordinary CMove midflight still STUBBED/optional under Strategic-only; does NOT enable Post",
            },
            "G2": {
                "state": "RO prep HIT (2ijk); live push STUBBED",
                "note": "INLINE_BLOB + SAFE needs catalogued; in-process embed still needs G4+",
            },
            "G3": {"state": "PARKED peacetime Instant", "note": "wartime/midflight only"},
            "G4": {"state": "HARD_DENY until human", "note": "CLAUSEWITZ_ALLOW_POST=1 once — executor cannot flip"},
            "G5": {"state": "CLOSED_NOT_OPENED", "note": "tool-gate + NEVER_POST"},
            "G6": {"state": "FORBIDDEN now", "note": "ONE Strategic Post @1x after G4/G5"},
        },
    }


def write_doc(result, live, polish, card, calendar_ok):
    ready_rows = "\n".join(f"| `{r['id']}` | {r['what']} |" for r in card["READY"])
    parked_rows = "\n".join(f"| `{r['id']}` | {r['resume_when']} |" for r in card["PARKED"])
    deny_rows = "\n".join(f"| `{r['id']}` | {r['rule']} |" for r in card["HARD_DENY"])
    gate_rows = "\n".join(
        f"| {k} | {v['state']} | {v['note']} |" for k, v in card["GATES_G1_G6"].items()
    )
    DOC.write_text(
        f"""# Phase 2ijl — Agent card fold G1 Strategic-only + G2 RO prep

**Result:** `{result}`  
**allow_post:** **False** · Instant peacetime **PARKED** · ring_embed live **STUBBED** · never 5x  
**Not this slice:** PATH/OG50 densify · Instant polls · Post / tool-gate / ask ALLOW_POST

## Live clock + factory RO reaffirm

pid {live.get("pid")} · {live.get("clock_class")} · day_index={live.get("day_index")} ui={live.get("ui_date")} ·  
drain={live.get("drain")} exec={live.get("exec")} · calendar_ok={calendar_ok} ·  
all_factory_match={polish.get("all_factory_match")} · all_fn_match={polish.get("all_fn_match")} ·  
strategic_4753_match={polish.get("strategic_4753_match")} · allow_post=False · speed 1x CLI untouched

## Agent-facing card (Path C land) — post-2ijj/2ijk

### READY (use RO now)

| ID | What agent can rely on |
| --- | --- |
{ready_rows}

### PARKED (do not re-poll / wait gate)

| ID | Resume when |
| --- | --- |
{parked_rows}

### HARD_DENY (never without human SAFE Post)

| ID | Rule |
| --- | --- |
{deny_rows}

### SAFE Post gates G1–G6 (catalog; CLOSED)

| Gate | State | Note |
| --- | --- |
{gate_rows}

## Path C honesty (t50u)

Baseline ~60%. This slice is **agent-card clarity** folding G1 ACCEPTABLE + G2 RO prep HIT — ≤+1–2pp readiness docs, **not** +10pp unlock. Overall still **~60–62%**. **~70% milestone NOT crossed** while G2 live / G4+ block Post.

## Artifacts

- `scripts/phase2ijl_agent_card_g1g2_fold.py`
- `reports/phase2ijl_agent_card_g1g2_fold.json`
- Folded LAND_POST §6f + SAFE_POST

## Next shortest blocker

Human **G4** `CLAUSEWITZ_ALLOW_POST=1` (executor cannot flip) → G5 tool-gate → G2 live ring_embed / G6 one Strategic Post @1x. Instant PARKED. No more NON-Post densify/poll churn.

*Phase 2ijl · 2026-11-01 Asia/Shanghai*
""",
        encoding="utf-8",
    )


def patch_docs(result, live, polish):
    fold_block = (
        f"\n### 2ijl agent card — G1 Strategic-only + G2 RO prep fold (catalog)\n\n"
        f"See `docs/PHASE2IJL_AGENT_CARD_G1G2_FOLD.md`. Folds **2ijj G1 ACCEPTABLE** + "
        f"**2ijk G2 RO prep HIT** into one READY/PARKED/HARD_DENY card with G1–G6 states.\n\n"
        f"- **READY (+G1/G2 RO):** prior 2ijh surfaces + Strategic-only G1 ACCEPTABLE + "
        f"ring INLINE_BLOB / G2 RO prep catalog (live embed still STUBBED).\n"
        f"- **PARKED:** Instant peacetime; midflight empty; PATH/OG50 densify; G2 **live** "
        f"until human SAFE Post.\n"
        f"- **HARD_DENY:** allow_post / Post / ring_embed live / tool-gate / 5x / invent names / "
        f"ask-user Post / Capstone/121.\n"
        f"- **Gates:** G1 ACCEPTABLE (Strategic-only) · G2 RO HIT / live STUBBED · G3 PARKED · "
        f"G4/G5/G6 human-gated CLOSED.\n"
        f"- Live reaffirm: pid {live.get('pid')} day_index={live.get('day_index')} "
        f"ui={live.get('ui_date')} factory/FN "
        f"{polish.get('all_factory_match')}/{polish.get('all_fn_match')} Strat4753="
        f"{polish.get('strategic_4753_match')}.\n"
        f"- **Path C honesty (t50u):** still ~60–62%; this fold ≤+1–2pp clarity; "
        f"~70% NOT crossed (G2 live / G4+).\n\n"
    )

    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    if "### 2ijl agent card" not in t:
        # insert after 2ijj block if present, else after 2iji
        for anchor in (
            "### 2ijj G1 Strategic-only acceptance (catalog)",
            "### 2iji SAFE Post gate checklist (catalog)",
            "### 2ijh agent card",
        ):
            if anchor in t:
                idx = t.find(anchor)
                # find next ### after this block
                nxt = t.find("\n### ", idx + len(anchor))
                if nxt == -1:
                    nxt = t.find("\n## ", idx + len(anchor))
                if nxt != -1:
                    t = t[:nxt] + fold_block + t[nxt:]
                else:
                    t = t + fold_block
                break
        else:
            t = t + fold_block
    # Update human-gated checklist A/B lines lightly
    t = t.replace(
        "[ ] A  Ordinary CMove (+ embed) live midflight hex  — OR Strategic-only + human SAFE Post for ring_embed\n"
        "[ ] B  Ring-embed recreate proof on captured buffer\n",
        "[~] A  G1 Strategic-only ACCEPTABLE (2ijj); ordinary CMove midflight still optional/STUBBED\n"
        "[~] B  G2 RO prep HIT (2ijk INLINE_BLOB + needs catalog); **live ring_embed still STUBBED**\n",
        1,
    )
    honesty = (
        "- **2ijl:** agent card fold G1 ACCEPTABLE + G2 RO prep; NO Post; Instant PARKED; "
        "PathC ~60–62% honesty (≤+1–2pp; ~70% NOT crossed).\n"
    )
    if "**2ijl:** agent card fold" not in t:
        if "**2ijk:**" in t:
            idx = t.find("**2ijk:**")
            eol = t.find("\n", idx)
            if eol != -1:
                t = t[: eol + 1] + honesty + t[eol + 1 :]
            else:
                t = t + honesty
        else:
            t = t + honesty
    if "*Phase 2ijl" not in t:
        t = t.rstrip() + "\n\n*Phase 2ijl · agent card G1+G2 fold · 2026-11-01 Asia/Shanghai*\n"
    # next shortest
    if "Next shortest NON-Post:** Human G4" not in t and "G4 CLAUSEWITZ_ALLOW_POST" not in t:
        t = t.replace(
            "**Next shortest NON-Post:** G2 live ring_embed still needs human SAFE Post (G4); RO prep HIT 2ijk — retry GitHub push when reachable. Still **NO ALLOW_POST**.",
            "**Next shortest NON-Post:** Human G4 CLAUSEWITZ_ALLOW_POST=1 (executor cannot flip) → G5 → G2 live/G6; agent card folded 2ijl. Still **NO ALLOW_POST**.",
            1,
        )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    g_note = (
        f"\n### Agent card fold (2ijl) — catalog only\n\n"
        f"**Gate remains CLOSED. allow_post False.**\n\n"
        f"Single READY/PARKED/HARD_DENY card after G1 Strategic-only ACCEPTABLE (2ijj) + "
        f"G2 RO prep HIT (2ijk). See `docs/PHASE2IJL_AGENT_CARD_G1G2_FOLD.md`.\n\n"
        f"Still blocks ALLOW_POST: **G2 live** · **G4** · **G5** · **G6**. "
        f"G3 Instant PARKED. Executor cannot flip G4.\n\n"
    )
    if "### Agent card fold (2ijl)" not in t2:
        if "### G2 update (2ijk)" in t2:
            idx = t2.find("### G2 update (2ijk)")
            nxt = t2.find("\n### ", idx + 5)
            if nxt == -1:
                nxt = t2.find("\n## ", idx + 5)
            if nxt != -1:
                t2 = t2[:nxt] + g_note + t2[nxt:]
            else:
                t2 = t2 + g_note
        else:
            t2 = t2 + g_note
    row = (
        f"| 2ijl | agent card fold G1 Strategic-only + G2 RO prep | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2ijl |" not in t2:
        for key in ("| 2ijk |", "| 2ijj |", "| 2iji |"):
            if key in t2:
                lines = t2.splitlines(keepends=True)
                out = []
                for line in lines:
                    out.append(line)
                    if line.startswith(key):
                        out.append(row)
                t2 = "".join(out)
                break
    if "*Phase 2ijl" not in t2:
        t2 = t2.rstrip() + (
            "\n\n*Phase 2ijl — agent card G1+G2 fold. Gate stays CLOSED. "
            "2026-11-01 Asia/Shanghai*\n"
        )
    safe.write_text(t2, encoding="utf-8")


def main() -> int:
    assert allow_post() is False
    hb = load_hb()
    pid = find_pid()
    if not pid:
        SUMMARY.write_text(
            json.dumps(
                {
                    "phase": "2ijl",
                    "result": "NO_LIVE_PROCESS",
                    "allow_post": False,
                    "next_shortest_blocker": "relaunch ITA@1x; still NO ALLOW_POST",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(json.dumps({"result": "NO_LIVE_PROCESS"}, indent=2))
        return 1

    b = Backend(pid)
    base = b.image_base
    tag = hb.player_tag(b, base)
    scenario = "ITA@1x agent card G1+G2 fold RO (no Post, no Instant, no densify)"
    s0 = continuum_live(b, base, pid, tag, scenario)
    time.sleep(2)
    s1 = continuum_live(b, base, pid, tag, scenario)
    polish = hb.factory_and_fn(b, base)
    card = agent_card()

    family_ok = bool(polish.get("all_factory_match")) and bool(polish.get("all_fn_match"))
    strat_ok = bool(polish.get("strategic_4753_match")) and bool(
        polish.get("fn_match", {}).get("STRATEGIC")
    )
    calendar_ok = (s1.get("day_index") or 0) > (s0.get("day_index") or 0) or (
        (s1.get("exec") or 0) > (s0.get("exec") or 0)
    ) or ((s1.get("drain") or 0) > (s0.get("drain") or 0))

    if family_ok and strat_ok and calendar_ok:
        result = "AGENT_CARD_G1G2_FOLD_HIT"
    elif family_ok and strat_ok:
        result = "AGENT_CARD_G1G2_FOLD_HIT_CLOCK_FLAT"
    else:
        result = "AGENT_CARD_G1G2_FOLD_PARTIAL"

    out = {
        "phase": "2ijl",
        "slice": "agent_card_g1_strategic_g2_ro_prep_fold_NONPOST",
        "result": result,
        "allow_post": False,
        "post_executed": False,
        "ring_embed_executed": False,
        "instant_parked": True,
        "path_og50_densify": False,
        "midflight_poll": False,
        "asked_user_allow_post": False,
        "agent_card": card,
        "move_family_polish": {
            "all_factory_match": polish.get("all_factory_match"),
            "all_fn_match": polish.get("all_fn_match"),
            "factory_match": polish.get("factory_match"),
            "fn_match": polish.get("fn_match"),
            "strategic_4753_match": polish.get("strategic_4753_match"),
            "expected_idx": polish.get("expected_idx"),
        },
        "live": s1,
        "calendar_sample": {"s0": s0, "s1": s1, "calendar_ok": calendar_ok},
        "path_c_progress_honesty": (
            "~60–62%; agent-card fold of G1 ACCEPTABLE + G2 RO prep is ≤+1–2pp "
            "clarity — does NOT unlock Post or cross ~70% while G2 live / G4+ remain"
        ),
        "doc": "docs/PHASE2IJL_AGENT_CARD_G1G2_FOLD.md",
        "hard_deny": [
            "ALLOW_POST",
            "Post inject",
            "2fb/2gk recipe execute",
            "ring_embed live",
            "tool-gate",
            "Instant empty re-poll",
            "PATH densify",
            "long midflight empty poll",
            "5x",
            "ask user ALLOW_POST",
            "invent field names",
        ],
    }
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    brief_keys = (
        "phase",
        "result",
        "allow_post",
        "agent_card",
        "move_family_polish",
        "live",
        "calendar_sample",
        "path_c_progress_honesty",
        "doc",
    )
    SUMMARY.write_text(
        json.dumps({k: out[k] for k in brief_keys}, indent=2, default=str),
        encoding="utf-8",
    )
    write_doc(result, s1, polish, card, calendar_ok)
    patch_docs(result, s1, polish)
    print(
        json.dumps(
            {
                "result": result,
                "all_factory_match": polish.get("all_factory_match"),
                "all_fn_match": polish.get("all_fn_match"),
                "strategic_4753_match": polish.get("strategic_4753_match"),
                "calendar_ok": calendar_ok,
                "allow_post": False,
                "g1": card["GATES_G1_G6"]["G1"]["state"],
                "g2": card["GATES_G1_G6"]["G2"]["state"],
                "live": {
                    "pid": s1.get("pid"),
                    "year": s1.get("year"),
                    "day_index": s1.get("day_index"),
                    "ui_date": s1.get("ui_date"),
                    "clock_class": s1.get("clock_class"),
                    "drain": s1.get("drain"),
                    "exec": s1.get("exec"),
                },
            },
            indent=2,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
