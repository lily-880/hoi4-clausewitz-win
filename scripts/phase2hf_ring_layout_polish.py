#!/usr/bin/env python3
"""Phase 2hf: CDummyServer ring@+0xa0 INLINE layout polish (RO).

Corrects 2he presence-as-ptr misread: RING is an embedded blob at
server+0xa0 (not a heap pointer). Instant one-shot layout + seq.
No Post / no ring push / no midflight / no oi≠0 poll / never 5x / no speed write.
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

OUT = ROOT / "reports" / "phase2hf_ring_layout_polish.json"
SUMMARY = ROOT / "reports" / "phase2hf_summary.json"
DOC = ROOT / "docs" / "PHASE2HF_RING_LAYOUT_POLISH.md"

GS_PLAYER_TAG = 0x518
RING_BLOB = 0x40
# Prior 2fd/2gk: seq lives on DummyServer at +0xD0 (after ring region)
DUMMY_SEQ = 0xD0


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def i32(b, a):
    return struct.unpack("<i", b.read(a, 4))[0]


def try_u64(b, a):
    try:
        return u64(b, a)
    except Exception:
        return None


def try_u32(b, a):
    try:
        return u32(b, a)
    except Exception:
        return None


def player_tag(b, base):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    return i32(b, gs + GS_PLAYER_TAG)


def live_meta(b, base, pid, country_tag):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    hours = i32(b, gs + 0x484)
    d = datetime(1936, 1, 1, 0, 0) + timedelta(hours=int(hours))
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
    return {
        "pid": pid,
        "hours": hours,
        "ui_date": d.strftime("%Y-%m-%d %H:00"),
        "speed_policy": "pause-or-1x only (never write speed)",
        "country_tag_filter": country_tag,
        "scenario": "ITA ring@+0xa0 INLINE layout polish (no Post, no speed write)",
        "pending": pending,
        "stage_count": stage,
        "drain": drain,
        "exec": exec_c,
        "allow_post": False,
        "clock_note": (
            "hours@GS+0x484 may disagree with high drain/exec vs prior 2hd hours=357 "
            "same pid — treat as possible clock wrap / reload; do not write speed"
        ),
    }


def ring_layout(b, base):
    sess = try_u64(b, base + post_abi.G_SESSION)
    if not sess:
        return {"error": "no_session"}
    server = try_u64(b, sess + post_abi.CSession_SERVER)
    if not server:
        return {"error": "no_server", "sess": hex(sess)}
    vt = try_u64(b, server) or 0
    vt_rva = (vt - base) & 0xFFFFFFFF
    ring_addr = server + post_abi.CDummyServer_RING
    blob = b.read(ring_addr, RING_BLOB)
    u32s = [struct.unpack_from("<I", blob, i)[0] for i in range(0, RING_BLOB, 4)]
    # 2he misread: treating first u64 as "ptr" yields 0x1000000000 when u32[0]=0,u32[1]=0x10
    false_ptr = struct.unpack_from("<Q", blob, 0)[0]
    slot_a = struct.unpack_from("<Q", blob, 0x08)[0]
    slot_b = struct.unpack_from("<Q", blob, 0x10)[0]
    mid = struct.unpack_from("<Q", blob, 0x18)[0]
    seq = try_u32(b, server + DUMMY_SEQ)
    pend_h = try_u64(b, server + post_abi.CDummyServer_PENDING) or 0
    pend_c = try_u32(b, server + post_abi.CDummyServer_PENDING + 0x10)
    exec_h = try_u64(b, server + post_abi.CDummyServer_EXECLIST) or 0
    exec_c = try_u32(b, server + post_abi.CDummyServer_EXECLIST + 0x10)

    # Compare to 2gk snapshot shape (same process epoch often shares server)
    prior_gk = None
    try:
        gk = json.loads((ROOT / "reports" / "phase2gk_ring_embed_recipe_v2.json").read_text(encoding="utf-8"))
        snap = gk.get("live_ring_snapshot") or {}
        prior_gk = {
            "server": snap.get("server"),
            "ring_addr": snap.get("ring_addr"),
            "u32_0": snap.get("ring_u32_head", [None])[0] if snap.get("ring_u32_head") else None,
            "u32_1": snap.get("ring_u32_head", [None, None])[1] if snap.get("ring_u32_head") else None,
            "same_server": snap.get("server") == hex(server),
        }
    except Exception as e:
        prior_gk = {"error": str(e)}

    return {
        "session": hex(sess),
        "server": hex(server),
        "server_vt_rva": hex(vt_rva),
        "server_vt_match": vt_rva == post_abi.CDummyServer_VT,
        "ring_kind": "INLINE_BLOB",
        "ring_off": hex(post_abi.CDummyServer_RING),
        "ring_addr": hex(ring_addr),
        "ring_blob_hex": blob.hex(),
        "ring_u32": [hex(x) for x in u32s],
        "fields_ro": {
            "u32_0_index_or_flags": hex(u32s[0]),
            "u32_1_capacity_like": hex(u32s[1]),
            "capacity_like_equals_0x10": u32s[1] == 0x10,
            "qword_at_0x08": hex(slot_a),
            "qword_at_0x10": hex(slot_b),
            "qword_at_0x18": hex(mid),
            "seq_at_server_plus_0xd0": seq,
        },
        "correction_vs_2he": {
            "2he_read_first_u64_as_ptr": hex(false_ptr),
            "2he_claimed_present": True,
            "actual": (
                "RING@+0xa0 is INLINE struct on CDummyServer, not a heap pointer; "
                "u64@+0xa0 == pack(u32_0=0, u32_1=0x10) == 0x1000000000 under LE — "
                "false 'ptr' signal"
            ),
        },
        "pending": {"head": hex(pend_h) if pend_h else "0", "count": pend_c, "empty": pend_h == 0 and (pend_c or 0) == 0},
        "execlist": {"head": hex(exec_h) if exec_h else "0", "count": exec_c, "empty": exec_h == 0 and (exec_c or 0) == 0},
        "prior_2gk_compare": prior_gk,
        "semantics": "RO layout polish only — ring_embed / push still STUBBED (needs SAFE Post)",
    }


def patch_docs(meta, result, layout):
    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    t = t.replace(
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2he `FACTORY_EXECLIST_RING_CORNER`); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
        f"**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0 (2hf `{result}`); retry GitHub push when reachable. Still **NO ALLOW_POST**.",
    )
    # §6f can-feed: add RING_LAYOUT RO
    if "| `RING_LAYOUT` |" not in t and "| `CLOCK` |" in t:
        t = t.replace(
            "| `CLOCK` | hours/UI/counters | pending/stage/drain/exec — HIT |\n",
            "| `CLOCK` | hours/UI/counters | pending/stage/drain/exec — HIT |\n"
            "| `RING_LAYOUT` | Dummy ring@+0xa0 INLINE blob | RO layout + seq@+0xd0 — HIT 2hf "
            "(embed still STUBBED) |\n",
        )
    # HARD_DENY RING row clarify
    t = t.replace(
        "| `RING` | ring_embed / Dummy recreate | STUBBED — needs SAFE Post |\n",
        "| `RING` | ring_embed / Dummy recreate in-process | STUBBED — needs SAFE Post "
        "(layout RO ≠ embed) |\n",
    )
    row = (
        f"| **2hf** | `{result}` | ring@+0xa0 INLINE layout polish (correct 2he ptr misread) + clock note | "
        f"oi≠0 / midflight / Post HARD_DENY |\n"
    )
    if "| **2hf** |" not in t and "| **2he** |" in t:
        lines = t.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| **2he** |"):
                out.append(row)
        t = "".join(out)
    note = (
        f"**2hf ring layout polish:** result=`{result}` · kind=INLINE_BLOB · "
        f"cap_like={layout.get('fields_ro', {}).get('u32_1_capacity_like')} · "
        f"seq={layout.get('fields_ro', {}).get('seq_at_server_plus_0xd0')} · "
        f"hours={meta.get('hours')} UI={meta.get('ui_date')} drain={meta.get('drain')} · "
        f"allow_post=False · 2he ptr misread corrected.\n"
    )
    if "**2hf ring layout polish:**" not in t and "**2he factory+execlist corner:**" in t:
        idx = t.find("**2he factory+execlist corner:**")
        eol = t.find("\n", idx)
        if eol != -1:
            t = t[: eol + 1] + note + t[eol + 1 :]
    t = t.replace(
        "*Phase 2he · factory + execlist/ring corner · 2026-10-31 Asia/Shanghai*",
        "*Phase 2hf · ring@+0xa0 INLINE layout polish · 2026-10-31 Asia/Shanghai*",
    )
    land.write_text(t, encoding="utf-8")

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    t2 = t2.replace(
        "## Phase 2gj … 2he — checklist polish (CLOSED)",
        "## Phase 2gj … 2hf — checklist polish (CLOSED)",
    )
    row2 = (
        f"| 2hf | ring@+0xa0 INLINE layout polish (2he ptr misread corrected) | "
        f"**{result}** (Post still CLOSED) |\n"
    )
    if "| 2hf |" not in t2 and "| 2he |" in t2:
        lines = t2.splitlines(keepends=True)
        out = []
        for line in lines:
            out.append(line)
            if line.startswith("| 2he |"):
                out.append(row2)
        t2 = "".join(out)
    # agent card pointer note
    if "RING_LAYOUT" not in t2 and "## Agent card pointer" in t2:
        t2 = t2.replace(
            "`RING` / `POST` / `SPEED5X` | STUBBED / HARD_DENY / NEVER",
            "`RING` embed STUBBED; `RING_LAYOUT` RO HIT 2hf; `POST`/`SPEED5X` HARD_DENY/NEVER",
        )
    t2 = t2.replace(
        "*Phase 2he — factory + execlist/ring corner. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
        "*Phase 2hf — ring@+0xa0 INLINE layout polish. Gate stays CLOSED. 2026-10-31 Asia/Shanghai*",
    )
    safe.write_text(t2, encoding="utf-8")


def main():
    assert allow_post() is False
    pid = find_pid()
    if not pid:
        summary = {
            "phase": "2hf",
            "result": "NO_LIVE_PROCESS",
            "allow_post": False,
            "next_shortest_blocker": "NON-Post: restore live; still NO ALLOW_POST",
        }
        SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 1

    b = Backend()
    base = b.image_base
    tag = player_tag(b, base)
    meta = live_meta(b, base, pid, tag)
    layout = ring_layout(b, base)

    ok = (
        layout.get("ring_kind") == "INLINE_BLOB"
        and layout.get("server_vt_match") is True
        and layout.get("fields_ro", {}).get("capacity_like_equals_0x10") is True
        and "correction_vs_2he" in layout
    )
    result = "RING_INLINE_LAYOUT_POLISH" if ok else "RING_LAYOUT_PARTIAL"

    report = {
        "phase": "2hf",
        "result": result,
        "allow_post": False,
        "live": meta,
        "ring_layout": layout,
        "sha_base": "2a6cdc6",
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
        "phase": "2hf",
        "result": result,
        "allow_post": False,
        "live": meta,
        "ring_kind": layout.get("ring_kind"),
        "capacity_like_0x10": layout.get("fields_ro", {}).get("capacity_like_equals_0x10"),
        "seq": layout.get("fields_ro", {}).get("seq_at_server_plus_0xd0"),
        "2he_false_ptr": layout.get("correction_vs_2he", {}).get("2he_read_first_u64_as_ptr"),
        "execlist_empty": layout.get("execlist", {}).get("empty"),
        "pending_empty": layout.get("pending", {}).get("empty"),
        "next_shortest_blocker": (
            "NON-Post: human midflight CMove hex / SAFE Post for ring_embed OR later "
            "plan-dense Assign oi≠0 (2hf ring INLINE layout); push when GitHub "
            "reachable; still NO ALLOW_POST"
        ),
        "sha_base": "2a6cdc6",
        "semantics": "ring@+0xa0 INLINE blob polish; 2he ptr misread corrected; embed still STUBBED",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    fro = layout.get("fields_ro") or {}
    DOC.write_text(
        "\n".join(
            [
                "# Phase 2hf — CDummyServer ring@+0xa0 INLINE layout polish",
                "",
                f"**Result:** `{result}`",
                "",
                "**Correction vs 2he:** `RING@+0xa0` is an **INLINE blob** on `CDummyServer`, "
                "not a heap pointer. 2he `ptr=0x1000000000` was LE `u32[0]=0` + `u32[1]=0x10`.",
                "",
                f"**Layout (RO):** kind=INLINE_BLOB · addr=`{layout.get('ring_addr')}` · "
                f"u32_0=`{fro.get('u32_0_index_or_flags')}` · "
                f"u32_1_cap_like=`{fro.get('u32_1_capacity_like')}` · "
                f"q@+0x08=`{fro.get('qword_at_0x08')}` · "
                f"q@+0x10=`{fro.get('qword_at_0x10')}` · "
                f"seq@server+0xd0=`{fro.get('seq_at_server_plus_0xd0')}`",
                "",
                f"**Queues:** pending_empty={layout.get('pending', {}).get('empty')} · "
                f"execlist_empty={layout.get('execlist', {}).get('empty')}",
                "",
                f"**Live:** pid {meta['pid']} · hours={meta['hours']} · UI {meta['ui_date']} · "
                f"drain={meta['drain']} exec={meta['exec']} · allow_post=False",
                "",
                f"**Clock note:** {meta['clock_note']}",
                "",
                "**Semantics:** Layout RO advances agent readiness (`RING_LAYOUT`); "
                "in-process ring_embed / push remains STUBBED (needs SAFE Post). "
                "No Post / never 5x / no speed write.",
                "",
                "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed "
                "OR later Assign oi≠0; retry GitHub push when reachable. Still **NO ALLOW_POST**.",
                "",
                f"*Phase 2hf · 2026-10-31 Asia/Shanghai · sha_base 2a6cdc6*",
                "",
            ]
        ),
        encoding="utf-8",
    )

    patch_docs(meta, result, layout)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
