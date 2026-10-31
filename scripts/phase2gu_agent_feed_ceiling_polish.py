#!/usr/bin/env python3
"""Phase 2gu: Agent-facing feed ceiling catalog polish (RO).

ONE slice. Catalog-only consolidate of 2gs perception + 2gt midflight empty
+ 2gp–2gr Assign/OG50 into LAND_POST §6d (what we can feed today / HARD_DENY).
No Post / no ALLOW_POST / never 5x / no recipe execute / no midflight re-poll.
Minimal probe: live_meta only (≤5s attach read).
"""
from __future__ import annotations

import json
import struct
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import post_abi
from config import allow_post
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2gu_agent_feed_ceiling.json"
SUMMARY = ROOT / "reports" / "phase2gu_summary.json"
DOC = ROOT / "docs" / "PHASE2GU_AGENT_FEED_CEILING.md"

GS_PLAYER_TAG = 0x518
PRIOR = ("2gp", "2gq", "2gr", "2gs", "2gt")


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def i32(b, a):
    return struct.unpack("<i", b.read(a, 4))[0]


def player_tag(b, base):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    return i32(b, gs + GS_PLAYER_TAG)


def live_meta(b, base, pid, country_tag, scenario):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    hours = i32(b, gs + 0x484)
    d = datetime(1936, 1, 1, 0, 0) + timedelta(hours=int(hours))
    pending = stage = drain = exec_c = None
    try:
        sess = u64(b, base + 0x34FFBE8)
        server = u64(b, sess + post_abi.CSession_SERVER)
        pending = u32(b, server + post_abi.CDummyServer_PENDING) if server else None
        stage = u32(b, sess + post_abi.CSession_STAGE_COUNT)
        drain = u32(b, sess + post_abi.CSession_DRAIN_COUNTER)
        exec_c = u32(b, sess + post_abi.CSession_EXEC_COUNTER)
    except Exception:
        pass
    return {
        "pid": pid,
        "hours": hours,
        "ui_date": d.strftime("%Y-%m-%d %H:00"),
        "speed_policy": "pause-or-1x only (never change speed)",
        "country_tag_filter": country_tag,
        "scenario": scenario,
        "pending": pending,
        "stage_count": stage,
        "drain": drain,
        "exec": exec_c,
        "allow_post": False,
    }


def load_prior_summaries():
    out = {}
    for ph in PRIOR:
        p = ROOT / "reports" / f"phase{ph}_summary.json"
        if p.exists():
            out[ph] = json.loads(p.read_text(encoding="utf-8"))
    return out


def feed_ceiling(priors: dict) -> dict:
    """Agent-facing: what RO perception can/can't feed land agent today."""
    gs = priors.get("2gs") or {}
    gt = priors.get("2gt") or {}
    return {
        "can_feed_today": [
            {
                "signal": "CArmy locate",
                "how": "handle type=51 + country_tag",
                "source": "2gp",
                "status": "HIT",
            },
            {
                "signal": "CArmy+0x200 multi-prov path candidates",
                "how": "tag-FP filtered; not demangled dest",
                "source": "2gm/2gs",
                "status": f"LIVE path nonempty={gs.get('path_nonempty')} multi={gs.get('path_multi')}",
            },
            {
                "signal": "Instance+0x70/+0x88 order/front maps",
                "how": "≠ army midflight dest; ⊀ +0x200 (2gn)",
                "source": "2gm/2gn",
                "status": "HIT",
            },
            {
                "signal": "OG+0x50 ≡ CArmy+0xB8 membership proxy",
                "how": "MI VT 0x29d6fb8",
                "source": "2gp–2gs",
                "status": f"walkback {gs.get('walkback_ok', '?')}/{gs.get('walkback_ok', 0) + gs.get('walkback_fail', 0)}",
            },
            {
                "signal": "Assign units type=51 → CArmy",
                "how": "when Assign sighted; oi@+0x48 often 0",
                "source": "2gp",
                "status": "HIT (oi=0 unset typical)",
            },
            {
                "signal": "Live clock/counters",
                "how": "hours/UI/pending/stage/drain/exec RO",
                "source": "live_meta",
                "status": "HIT",
            },
        ],
        "hard_deny_or_honest_empty": [
            {
                "signal": "CMove/SA/Cancel midflight hex (bit_identical)",
                "source": "2gj/2gt",
                "status": f"HONEST_EMPTY (2gt move={gt.get('move_hex', 0)} cancel={gt.get('cancel_hex', 0)})",
            },
            {
                "signal": "Named movement_dest demangle",
                "source": "2go",
                "status": "HONEST_EMPTY",
            },
            {
                "signal": "Assign units↔OI when order_index≠0",
                "source": "2gq/2gr/2gt",
                "status": f"QUIET (2gt assign_oi≠0={gt.get('assign_oi_nonzero', 0)})",
            },
            {
                "signal": "ring_embed / Dummy recreate in-process",
                "source": "2gk",
                "status": "STUBBED — needs SAFE Post",
            },
            {
                "signal": "Any Post / tool-gate / 2fb|2gk recipe execute",
                "source": "standing",
                "status": "HARD_DENY allow_post=False",
            },
            {
                "signal": "Demangled OG+0x50 / MI field name",
                "source": "2gp+",
                "status": "STUBBED",
            },
        ],
        "ceiling_note": (
            "Non-interactive RO cannot raise midflight/oi≠0 ceiling further without "
            "human leave midflight or SAFE Post for ring_embed. Catalog consolidates "
            "what agent may already consume RO."
        ),
    }


def patch_land_post(meta, ceiling):
    p = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = p.read_text(encoding="utf-8")
    section = """

## 6d. Agent feed ceiling — can feed today / HARD_DENY (2gu)

Catalog consolidate of §6b perception + §6c midflight empty + 2gp–2gr Assign/OG50.
**No Post. No recipe execute. allow_post False.**

### Can feed land agent today (RO)

| Signal | How | Status |
| --- | --- | --- |
| CArmy locate | handle type=51 + country_tag | HIT (2gp) |
| CArmy+0x200 multi-prov candidates | tag-FP; not demangled dest | LIVE nonempty/multi (2gs) |
| Instance+0x70/+0x88 order/front | ≠ midflight; ⊀ +0x200 | HIT (2gm/2gn) |
| OG+0x50 ≡ CArmy+0xB8 membership | MI VT `0x29d6fb8` | walkback live (2gs) |
| Assign units type=51 → CArmy | oi@`+0x48` often 0 | HIT when sighted (2gp) |
| Live clock/counters | hours/UI/pending/stage/drain/exec | HIT |

### HARD_DENY / honest-empty (do not invent)

| Signal | Status |
| --- | --- |
| CMove/SA/Cancel midflight hex | HONEST_EMPTY (2gt ≤90s non-interactive) |
| Named `movement_dest` | HONEST_EMPTY (2go) |
| Assign oi≠0 units↔OI | QUIET (2gq/2gr/2gt) |
| ring_embed / Dummy recreate | STUBBED — needs SAFE Post |
| Post / tool-gate / 2fb\\|2gk execute | HARD_DENY |
| Demangled OG+0x50 name | STUBBED |

**2gu live:** pid={pid} · hours={hours} · UI={ui} · allow_post=False.
**Ceiling:** non-interactive RO cannot raise midflight/oi≠0 further without human midflight or SAFE Post.

""".format(
        pid=meta.get("pid"),
        hours=meta.get("hours"),
        ui=meta.get("ui_date"),
    )
    # Insert §6d before ## 7 if missing; else replace existing §6d block
    if "## 6d. Agent feed ceiling" in t:
        start = t.index("## 6d. Agent feed ceiling")
        # find next ## after 6d
        nxt = t.find("\n## ", start + 4)
        if nxt == -1:
            t = t[:start] + section.strip() + "\n"
        else:
            t = t[:start] + section.strip() + "\n\n" + t[nxt + 1 :]
    else:
        marker = "## 7. Live RO snapshot"
        if marker in t:
            t = t.replace(marker, section.strip() + "\n\n" + marker)
        else:
            t = t.rstrip() + "\n" + section

    # Update §6 next-blocker line + phase table + footer
    t = t.replace(
        "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed (2gt non-interactive still empty) OR later Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.",
        "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2gu catalog: non-interactive ceiling reached); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
    )
    row_2gu = (
        "| **2gu** | `AGENT_FEED_CEILING_CATALOG_POLISH` | §6d can-feed / HARD_DENY consolidate "
        "(2gs+2gt+2gp–2gr); minimal live_meta | midflight hex / oi≠0 / Post HARD_DENY |\n"
    )
    if "| **2gu** |" not in t and "| **2gt** |" in t:
        # append after 2gt row
        lines = t.splitlines(keepends=True)
        out_lines = []
        for line in lines:
            out_lines.append(line)
            if line.startswith("| **2gt** |"):
                out_lines.append(row_2gu)
        t = "".join(out_lines)
    t = t.replace(
        "*Phase 2gt · midflight RO sample + agent-facing summary · 2026-10-31 Asia/Shanghai*",
        "*Phase 2gu · agent feed ceiling catalog polish · 2026-10-31 Asia/Shanghai*",
    )
    p.write_text(t, encoding="utf-8")


def patch_safe_post():
    p = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t = p.read_text(encoding="utf-8")
    t = t.replace(
        "## Phase 2gj … 2gt — checklist polish (CLOSED)",
        "## Phase 2gj … 2gu — checklist polish (CLOSED)",
    )
    row = (
        "| 2gu | §6d agent feed ceiling (can-feed / HARD_DENY); catalog-only | "
        "**AGENT_FEED_CEILING_CATALOG_POLISH** (Post still CLOSED) |\n"
    )
    if "| 2gu |" not in t and "| 2gt |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2gt |"):
                out.append(row)
        t = "".join(out)
    t = t.replace(
        "*Phase 2gt — midflight RO sample + agent summary. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2gu — agent feed ceiling catalog polish. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    p.write_text(t, encoding="utf-8")


def main():
    assert allow_post() is False
    scenario = "ITA@1x agent feed ceiling catalog polish (no Post)"
    priors = load_prior_summaries()
    ceiling = feed_ceiling(priors)

    pid = find_pid()
    if not pid:
        meta = {
            "pid": None,
            "hours": None,
            "ui_date": None,
            "speed_policy": "pause-or-1x only (never change speed)",
            "country_tag_filter": None,
            "scenario": scenario,
            "pending": None,
            "stage_count": None,
            "drain": None,
            "exec": None,
            "allow_post": False,
        }
        tag = None
        result = "AGENT_FEED_CEILING_CATALOG_POLISH_NO_LIVE"
    else:
        b = Backend()
        base = b.image_base
        tag = player_tag(b, base)
        meta = live_meta(b, base, pid, tag, scenario)
        result = "AGENT_FEED_CEILING_CATALOG_POLISH"

    next_b = (
        "NON-Post: agent feed ceiling cataloged — human midflight CMove hex / SAFE Post "
        "for ring_embed OR later plan-dense Assign oi≠0; push when GitHub reachable; "
        "still NO ALLOW_POST"
    )
    works = [
        "allow_post False; never 5x; no Post/inject/tool-gate/2fb/2gk",
        "LAND_POST §6d can-feed / HARD_DENY consolidate (2gs+2gt+2gp–2gr)",
        "SAFE_POST 2gu row",
        "minimal live_meta only (no midflight re-poll)",
    ]
    stubbed = [
        "demangled OG+0x50 / MI field name",
        "named movement_dest",
        "ring_embed execute",
        "2fb/2gk recipe execute",
        "ALLOW_POST / CLAUSEWITZ_ALLOW_POST",
        "tool-gate open",
        "CMove midflight hex",
        "Post inject",
        "Assign oi≠0 units↔OI confirm",
        "Capstone/121 re-churn",
        "ask user right-click",
    ]

    sh = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
    report = {
        "phase": "2gu",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "captured_at_shanghai": sh,
        "allow_post": False,
        "executed_2fb_recipe": False,
        "executed_2gk_recipe": False,
        "tool_gate": "CLOSED",
        "result": result,
        "live": meta,
        "prior_summaries_keys": sorted(priors.keys()),
        "feed_ceiling": ceiling,
        "works": works,
        "stubbed": stubbed,
        "next_shortest_blocker": next_b,
        "sha_base": "ca1aaa5",
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    summary = {
        "phase": "2gu",
        "result": result,
        "allow_post": False,
        "live": meta,
        "can_feed_n": len(ceiling["can_feed_today"]),
        "hard_deny_n": len(ceiling["hard_deny_or_honest_empty"]),
        "next_shortest_blocker": next_b,
        "sha_base": "ca1aaa5",
        "semantics": "§6d agent feed ceiling; catalog 2gs+2gt+2gp–2gr; no Post",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    can_lines = [
        f"- **{x['signal']}** — {x['how']} · `{x['status']}` · src {x['source']}"
        for x in ceiling["can_feed_today"]
    ]
    deny_lines = [
        f"- **{x['signal']}** — `{x['status']}` · src {x['source']}"
        for x in ceiling["hard_deny_or_honest_empty"]
    ]
    DOC.write_text(
        "\n".join(
            [
                "# Phase 2gu — Agent feed ceiling catalog polish (RO)",
                "",
                f"**Result:** `{result}`",
                f"**Live:** pid {meta.get('pid')} · {meta.get('ui_date')} · hours={meta.get('hours')} · tag={tag} · @1x",
                f"**Feed:** can_feed={len(ceiling['can_feed_today'])} · hard_deny/empty={len(ceiling['hard_deny_or_honest_empty'])}",
                "",
                "**allow_post:** **False** · tool-gate **CLOSED** · never 5x · 2fb/2gk **NOT executed**",
                "",
                "## Can feed land agent today (see LAND_POST §6d)",
                "",
                *can_lines,
                "",
                "## HARD_DENY / honest-empty",
                "",
                *deny_lines,
                "",
                f"**Ceiling note:** {ceiling['ceiling_note']}",
                "",
                "## Works / stubbed",
                "",
                "- Works: §6d feed ceiling; SAFE_POST 2gu; minimal live_meta",
                "- Stubbed: midflight hex; named dest; ring_embed; Post; Assign oi≠0 HIT",
                "",
                "**Next shortest blocker (NON-Post):** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0; push when GitHub reachable; still **NO ALLOW_POST**.",
                "",
                "Script: `scripts/phase2gu_agent_feed_ceiling_polish.py`",
                "Reports: `reports/phase2gu_agent_feed_ceiling.json`, `reports/phase2gu_summary.json`",
                "",
                f"*Phase 2gu · {sh} Asia/Shanghai*",
                "",
            ]
        ),
        encoding="utf-8",
    )

    patch_land_post(meta, ceiling)
    patch_safe_post()

    print(
        json.dumps(
            {
                "result": result,
                "live": {
                    "pid": meta.get("pid"),
                    "hours": meta.get("hours"),
                    "ui_date": meta.get("ui_date"),
                    "speed_policy": meta.get("speed_policy"),
                    "country_tag_filter": tag,
                    "scenario": scenario,
                    "pending": meta.get("pending"),
                    "stage_count": meta.get("stage_count"),
                    "allow_post": False,
                },
                "can_feed_n": len(ceiling["can_feed_today"]),
                "hard_deny_n": len(ceiling["hard_deny_or_honest_empty"]),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
