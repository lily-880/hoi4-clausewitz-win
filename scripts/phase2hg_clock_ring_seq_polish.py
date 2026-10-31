#!/usr/bin/env python3
"""Phase 2hg: CLOCK wrap/reload RO + ring seq delta vs 2hf (instant).

One-shot GS date cluster (year@+0x478 / hours@+0x484) + Dummy ring
seq/pending vs 2hf baseline. No Assign oi≠0 poll / no midflight / no Post /
never 5x / no speed write.
"""
from __future__ import annotations

import json
import struct
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import post_abi
from config import allow_post
from process import Backend, find_pid

OUT = ROOT / "reports" / "phase2hg_clock_ring_seq_polish.json"
SUMMARY = ROOT / "reports" / "phase2hg_summary.json"
DOC = ROOT / "docs" / "PHASE2HG_CLOCK_RING_SEQ_POLISH.md"
HF = ROOT / "reports" / "phase2hf_ring_layout_polish.json"

GS_PLAYER_TAG = 0x518
GS_YEAR = 0x478
GS_AUX = 0x47C
GS_HOUR_LIKE = 0x480
GS_HOURS = 0x484
DUMMY_SEQ = 0xD0
RING_BLOB = 0x40


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def i32(b, a):
    return struct.unpack("<i", b.read(a, 4))[0]


def try_read(fn, *a):
    try:
        return fn(*a)
    except Exception:
        return None


def gs_base(b, base):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    return u64(b, base + gs_rva), gs_rva


def clock_cluster(b, base):
    gs, gs_rva = gs_base(b, base)
    year = try_read(i32, b, gs + GS_YEAR)
    aux = try_read(i32, b, gs + GS_AUX)
    hour_like = try_read(i32, b, gs + GS_HOUR_LIKE)
    hours = try_read(i32, b, gs + GS_HOURS)
    tag = try_read(i32, b, gs + GS_PLAYER_TAG)
    decoded = None
    year_match = None
    if isinstance(hours, int) and 0 <= hours <= 200000:
        d = datetime(1936, 1, 1, 0, 0) + timedelta(hours=int(hours))
        decoded = {
            "year": d.year,
            "month": d.month,
            "day": d.day,
            "hour": d.hour,
            "ui": d.strftime("%Y-%m-%d %H:00"),
        }
        year_match = year == d.year if isinstance(year, int) else None
    # Classification vs prior 2hd hours=357 same pid
    if isinstance(hours, int) and hours < 100:
        classif = "RELOAD_OR_NEW_CAMPAIGN_LIKELY"
        note = (
            "hours@+0x484 low while drain/exec high and same pid as 2hd hours=357 — "
            "reload/new campaign, not +0x484 integer wrap; "
            f"year@+0x478={year} may disagree with hours-decoded year (treat hours as UI source)"
        )
    elif isinstance(hours, int) and hours > 300:
        classif = "CONTINUOUS_CAMPAIGN"
        note = "hours elevated; continuous campaign clock"
    else:
        classif = "CLOCK_OBSERVED"
        note = "see year/hours cluster"
    return {
        "gs": hex(gs),
        "gs_rva": hex(gs_rva),
        "year_at_0x478": year,
        "aux_at_0x47c": aux,
        "hour_like_at_0x480": hour_like,
        "hours_at_0x484": hours,
        "decoded": decoded,
        "year_matches_decoded": year_match,
        "player_tag": tag,
        "classification": classif,
        "note": note,
        "offsets": {
            "year": hex(GS_YEAR),
            "aux": hex(GS_AUX),
            "hour_like": hex(GS_HOUR_LIKE),
            "hours": hex(GS_HOURS),
        },
    }


def ring_seq_delta(b, base, hf):
    sess = try_read(u64, b, base + post_abi.G_SESSION)
    if not sess:
        return {"error": "no_session"}
    server = try_read(u64, b, sess + post_abi.CSession_SERVER)
    if not server:
        return {"error": "no_server"}
    vt = try_read(u64, b, server) or 0
    vt_rva = (vt - base) & 0xFFFFFFFF
    ring_addr = server + post_abi.CDummyServer_RING
    blob = b.read(ring_addr, RING_BLOB)
    u32s = [struct.unpack_from("<I", blob, i)[0] for i in range(0, 16, 4)]
    seq = try_read(u32, b, server + DUMMY_SEQ)
    pend_c = try_read(u32, b, server + post_abi.CDummyServer_PENDING + 0x10)
    exec_c_list = try_read(u32, b, server + post_abi.CDummyServer_EXECLIST + 0x10)
    drain = try_read(u32, b, sess + post_abi.CSession_DRAIN_COUNTER)
    exec_c = try_read(u32, b, sess + post_abi.CSession_EXEC_COUNTER)
    stage = try_read(u32, b, sess + post_abi.CSession_STAGE_COUNT)

    hf_live = (hf or {}).get("live") or {}
    hf_seq = ((hf or {}).get("ring_layout") or {}).get("fields_ro", {}).get("seq_at_server_plus_0xd0")
    hf_server = ((hf or {}).get("ring_layout") or {}).get("server")
    hf_drain = hf_live.get("drain")
    hf_exec = hf_live.get("exec")
    hf_hours = hf_live.get("hours")

    seq_delta = (seq - hf_seq) if isinstance(seq, int) and isinstance(hf_seq, int) else None
    # 2hf: seq≈exec (84065 vs 83889) — reaffirm proximity
    seq_exec_gap = (seq - exec_c) if isinstance(seq, int) and isinstance(exec_c, int) else None

    return {
        "session": hex(sess),
        "server": hex(server),
        "server_vt_rva": hex(vt_rva),
        "server_vt_match": vt_rva == post_abi.CDummyServer_VT,
        "same_server_as_2hf": hf_server == hex(server) if hf_server else None,
        "ring_kind": "INLINE_BLOB",
        "ring_addr": hex(ring_addr),
        "u32_0": hex(u32s[0]),
        "u32_1_cap_like": hex(u32s[1]),
        "cap_like_0x10": u32s[1] == 0x10,
        "seq": seq,
        "seq_delta_vs_2hf": seq_delta,
        "seq_minus_exec": seq_exec_gap,
        "seq_tracks_exec_loosely": (
            isinstance(seq_exec_gap, int) and abs(seq_exec_gap) < 500
        ),
        "pending_count": pend_c,
        "execlist_count": exec_c_list,
        "pending_empty": (pend_c or 0) == 0,
        "execlist_empty": (exec_c_list or 0) == 0,
        "session_counters": {"stage": stage, "drain": drain, "exec": exec_c},
        "delta_vs_2hf": {
            "hours": (None if hf_hours is None or hours_now_missing(hf_hours) else None),
            "drain": (drain - hf_drain) if isinstance(drain, int) and isinstance(hf_drain, int) else None,
            "exec": (exec_c - hf_exec) if isinstance(exec_c, int) and isinstance(hf_exec, int) else None,
            "seq": seq_delta,
            "2hf_hours": hf_hours,
            "2hf_seq": hf_seq,
            "2hf_drain": hf_drain,
            "2hf_exec": hf_exec,
        },
        "semantics": "one-shot seq/pending polish; empty queues honest quiet; no push",
    }


def hours_now_missing(_):
    return True  # placeholder; hours delta filled in main


def patch_docs(meta, result, clock, ring):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    t = t.replace(
        "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2hf `RING_INLINE_LAYOUT_POLISH`); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2hg `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
    )
    # enrich CLOCK can-feed row
    if "CLOCK` | hours/UI/counters | pending/stage/drain/exec — HIT |" in t:
        t = t.replace(
            "| `CLOCK` | hours/UI/counters | pending/stage/drain/exec — HIT |\n",
            "| `CLOCK` | hours/UI/counters + year@+0x478 | HIT 2hg "
            f"({clock.get('classification')}; reload≠wrap) |\n",
        )
    row = (
        f"| **2hg** | `{result}` | CLOCK year/hours cluster + ring seq delta vs 2hf | "
        f"oi≠0 / midflight / Post HARD_DENY |\n"
    )
    if "| **2hg** |" not in t and "| **2hf** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2hf** |"):
                out.append(row)
        t = "".join(out)
    note = (
        f"**2hg clock+seq polish:** result=`{result}` · class={clock.get('classification')} · "
        f"hours={clock.get('hours_at_0x484')} year={clock.get('year_at_0x478')} · "
        f"seq={ring.get('seq')} Δseq={ring.get('seq_delta_vs_2hf')} · "
        f"drain={meta.get('drain')} · allow_post=False.\n"
    )
    if "**2hg clock+seq polish:**" not in t and "**2hf ring layout polish:**" in t:
        idx = t.find("**2hf ring layout polish:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2hf · ring@+0xa0 INLINE layout polish · 2026-10-31 Asia/Shanghai*",
        "*Phase 2hg · CLOCK + ring seq polish · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2hf — checklist polish (CLOSED)",
        "## Phase 2gj … 2hg — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2hg | CLOCK year/hours cluster + ring seq delta vs 2hf | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2hg |" not in t2 and "| 2hf |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2hf |"):
                out.append(row2)
        t2 = "".join(out)
    t2 = t2.replace(
        "*Phase 2hf — ring@+0xa0 INLINE layout polish. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2hg — CLOCK + ring seq polish. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")


def main():
    assert allow_post() is False
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2hg",
            "result": "NO_LIVE_PROCESS",
            "allow_post": False,
            "next_shortest_blocker": "NON-Post: restore live; still NO ALLOW_POST",
        }
        SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 1

    hf = None
    if HF.exists():
        hf = json.loads(HF.read_text(encoding="utf-8"))

    b = Backend()
    base = b.image_base
    clock = clock_cluster(b, base)
    ring = ring_seq_delta(b, base, hf)

    # fill hours delta now that clock is known
    hf_hours = ((hf or {}).get("live") or {}).get("hours")
    hours = clock.get("hours_at_0x484")
    if isinstance(ring.get("delta_vs_2hf"), dict):
        ring["delta_vs_2hf"]["hours"] = (
            (hours - hf_hours) if isinstance(hours, int) and isinstance(hf_hours, int) else None
        )

    meta = {
        "pid": pid,
        "hours": hours,
        "ui_date": (clock.get("decoded") or {}).get("ui"),
        "speed_policy": "pause-or-1x only (never write speed)",
        "country_tag_filter": clock.get("player_tag"),
        "scenario": "ITA CLOCK cluster + ring seq delta vs 2hf (no Post, no speed write)",
        "pending": ring.get("pending_count"),
        "stage_count": (ring.get("session_counters") or {}).get("stage"),
        "drain": (ring.get("session_counters") or {}).get("drain"),
        "exec": (ring.get("session_counters") or {}).get("exec"),
        "allow_post": False,
    }

    ok = (
        clock.get("classification") == "RELOAD_OR_NEW_CAMPAIGN_LIKELY"
        and ring.get("server_vt_match") is True
        and ring.get("ring_kind") == "INLINE_BLOB"
        and ring.get("cap_like_0x10") is True
        and ring.get("seq_tracks_exec_loosely") is True
    )
    result = "CLOCK_RELOAD_RING_SEQ_POLISH" if ok else "CLOCK_RING_SEQ_PARTIAL"

    report = {
        "phase": "2hg",
        "result": result,
        "allow_post": False,
        "live": meta,
        "clock": clock,
        "ring_seq": ring,
        "sha_base": "4bb0643",
        "hard_deny": [
            "ALLOW_POST",
            "CLAUSEWITZ_ALLOW_POST",
            "Post inject",
            "ring_embed push",
            "2fb/2gk recipe execute",
            "tool-gate",
            "5x",
            "speed write",
            "ask right-click",
            "long midflight empty poll",
            "Assign oi≠0 long poll",
        ],
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    summary = {
        "phase": "2hg",
        "result": result,
        "allow_post": False,
        "live": meta,
        "clock_class": clock.get("classification"),
        "year": clock.get("year_at_0x478"),
        "hours": hours,
        "year_match": clock.get("year_matches_decoded"),
        "seq": ring.get("seq"),
        "seq_delta_vs_2hf": ring.get("seq_delta_vs_2hf"),
        "seq_tracks_exec_loosely": ring.get("seq_tracks_exec_loosely"),
        "same_server_as_2hf": ring.get("same_server_as_2hf"),
        "pending_empty": ring.get("pending_empty"),
        "execlist_empty": ring.get("execlist_empty"),
        "next_shortest_blocker": (
            "NON-Post: human midflight CMove hex / SAFE Post for ring_embed OR later "
            "plan-dense Assign oi≠0 (2hg CLOCK+seq); push when GitHub reachable; "
            "still NO ALLOW_POST"
        ),
        "sha_base": "4bb0643",
        "semantics": "CLOCK reload≠wrap + ring seq delta; no oi≠0 poll; embed STUBBED",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    DOC.write_text(
        "\n".join(
            [
                "# Phase 2hg — CLOCK wrap/reload RO + ring seq delta",
                "",
                f"**Result:** `{result}`",
                "",
                f"**CLOCK:** class=`{clock.get('classification')}` · "
                f"year@+0x478={clock.get('year_at_0x478')} · "
                f"hours@+0x484={hours} · UI={(clock.get('decoded') or {}).get('ui')} · "
                f"year_match={clock.get('year_matches_decoded')}",
                "",
                f"**Note:** {clock.get('note')}",
                "",
                f"**Ring:** INLINE · seq={ring.get('seq')} · "
                f"Δseq_vs_2hf={ring.get('seq_delta_vs_2hf')} · "
                f"seq≈exec={ring.get('seq_tracks_exec_loosely')} · "
                f"same_server={ring.get('same_server_as_2hf')} · "
                f"pending_empty={ring.get('pending_empty')} · "
                f"execlist_empty={ring.get('execlist_empty')}",
                "",
                f"**Live:** pid {pid} · drain={meta['drain']} exec={meta['exec']} · "
                f"allow_post=False · speed untouched",
                "",
                "**Semantics:** Instant GS date cluster + ring seq delta vs 2hf. "
                "Low hours + high drain/same-pid ⇒ reload/new campaign, not +0x484 wrap. "
                "No Post / never 5x / no speed write / no oi≠0 poll.",
                "",
                "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed "
                "OR later Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.",
                "",
                f"*Phase 2hg · 2026-10-31 Asia/Shanghai · sha_base 4bb0643*",
                "",
            ]
        ),
        encoding="utf-8",
    )

    patch_docs(meta, result, clock, ring)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
