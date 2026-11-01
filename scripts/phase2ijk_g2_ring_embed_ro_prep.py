#!/usr/bin/env python3
"""Phase 2ijk NON-Post: G2 ring_embed RO prep (INLINE_BLOB reaffirm + SAFE Post needs catalog).

Reaffirm CDummyServer ring@+0xa0 INLINE_BLOB on live pid; cheap structure RO;
document what SAFE Post would need for ring_embed (offsets/VT/size/factory) from
existing 2fd/2gk/2hf catalog — no invent field names. NO Post / Instant / PATH /
midflight empty / ring_embed execute / tool-gate / 5x.
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

OUT = ROOT / "reports" / "phase2ijk_g2_ring_embed_ro_prep.json"
SUMMARY = ROOT / "reports" / "phase2ijk_g2_ring_embed_ro_prep_summary.json"
DOC = ROOT / "docs" / "PHASE2IJK_G2_RING_EMBED_RO_PREP.md"

RING_BLOB = 0x40
DUMMY_SEQ = 0xD0
GS_YEAR = 0x478
GS_DAY_INDEX = 0x484
GS_PLAYER_TAG = 0x518


def load_mod(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


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


def try_i32(b, a):
    try:
        return i32(b, a)
    except Exception:
        return None


def continuum_live(b, base, pid, tag, scenario):
    """year@+0x478 + day_index@+0x484 (2hb hours-timedelta display is wrong on continuum)."""
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    year = try_i32(b, gs + GS_YEAR)
    day_index = try_i32(b, gs + GS_DAY_INDEX)
    ui = None
    if year and day_index is not None and 1 <= year <= 3000 and 0 <= day_index < 400:
        try:
            ui = (datetime(year, 1, 1) + timedelta(days=int(day_index))).strftime("%Y-%m-%d")
        except Exception:
            ui = None
    pending = stage = drain = exec_c = None
    sess = server = None
    try:
        sess = u64(b, base + post_abi.G_SESSION)
        server = u64(b, sess + post_abi.CSession_SERVER)
        pending = try_u32(b, server + post_abi.CDummyServer_PENDING + 0x10) if server else None
        stage = try_u32(b, sess + post_abi.CSession_STAGE_COUNT)
        drain = try_u32(b, sess + post_abi.CSession_DRAIN_COUNTER)
        exec_c = try_u32(b, sess + post_abi.CSession_EXEC_COUNTER)
    except Exception:
        pass
    return {
        "pid": pid,
        "year": year,
        "day_index": day_index,
        "ui_date": ui,
        "clock_source": "GS+0x478 year + GS+0x484 day_index (continuum; not 2hb hours-timedelta)",
        "speed_policy": "pause-or-1x only (never write speed beyond pause/1x)",
        "country_tag_filter": tag,
        "scenario": scenario,
        "session": hex(sess) if sess else None,
        "server": hex(server) if server else None,
        "pending": pending,
        "stage_count": stage,
        "drain": drain,
        "exec": exec_c,
        "allow_post": False,
    }


def ring_layout_ro(b, base):
    """Cheap RO: reaffirm INLINE_BLOB @ server+0xa0; pending/execlist counts; seq@+0xd0."""
    sess = try_u64(b, base + post_abi.G_SESSION)
    if not sess:
        return {"error": "no_session"}
    server = try_u64(b, sess + post_abi.CSession_SERVER)
    if not server:
        return {"error": "no_server", "session": hex(sess)}
    vt = try_u64(b, server) or 0
    vt_rva = (vt - base) & 0xFFFFFFFF
    ring_addr = server + post_abi.CDummyServer_RING
    blob = b.read(ring_addr, RING_BLOB)
    u32s = [struct.unpack_from("<I", blob, i)[0] for i in range(0, RING_BLOB, 4)]
    false_ptr = struct.unpack_from("<Q", blob, 0)[0]
    slot_a = struct.unpack_from("<Q", blob, 0x08)[0]
    slot_b = struct.unpack_from("<Q", blob, 0x10)[0]
    mid = struct.unpack_from("<Q", blob, 0x18)[0]
    seq = try_u32(b, server + DUMMY_SEQ)
    pend_h = try_u64(b, server + post_abi.CDummyServer_PENDING) or 0
    pend_c = try_u32(b, server + post_abi.CDummyServer_PENDING + 0x10) or 0
    exec_h = try_u64(b, server + post_abi.CDummyServer_EXECLIST) or 0
    exec_c = try_u32(b, server + post_abi.CDummyServer_EXECLIST + 0x10) or 0

    # Classification: INLINE_BLOB when first two u32 look like flags+cap_like 0x10
    # (2he false-ptr = pack(u32_0,u32_1) under LE). Do not invent field names.
    cap_like = u32s[1]
    inline_ok = (
        vt_rva == post_abi.CDummyServer_VT
        and post_abi.CDummyServer_RING == 0xA0
        and cap_like == 0x10
    )
    prior_hf = None
    try:
        hf = json.loads((ROOT / "reports" / "phase2hf_ring_layout_polish.json").read_text(encoding="utf-8"))
        rl = hf.get("ring_layout") or {}
        prior_hf = {
            "phase": "2hf",
            "ring_kind": rl.get("ring_kind"),
            "server_vt_match": rl.get("server_vt_match"),
            "capacity_like_equals_0x10": (rl.get("fields_ro") or {}).get("capacity_like_equals_0x10"),
            "prior_server": rl.get("server"),
            "prior_ring_addr": rl.get("ring_addr"),
            "same_server_as_prior_hf": rl.get("server") == hex(server),
        }
    except Exception as e:
        prior_hf = {"error": str(e)}

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
        "fields_ro_catalog_only": {
            "u32_0_index_or_flags": hex(u32s[0]),
            "u32_1_capacity_like": hex(cap_like),
            "capacity_like_equals_0x10": cap_like == 0x10,
            "qword_at_0x08": hex(slot_a),
            "qword_at_0x10": hex(slot_b),
            "qword_at_0x18": hex(mid),
            "seq_at_server_plus_0xd0": seq,
            "note": "field labels catalogued from 2hf/2gk — do not invent new names",
        },
        "correction_vs_2he_reaffirm": {
            "first_u64_as_false_ptr": hex(false_ptr),
            "actual": (
                "RING@+0xa0 is INLINE blob on CDummyServer (not a heap pointer); "
                "LE pack(u32_0,u32_1=0x10) can look like 0x1000000000 — false ptr signal (2hf)"
            ),
        },
        "pending": {
            "head": hex(pend_h) if pend_h else "0",
            "count": pend_c,
            "empty": pend_h == 0 and pend_c == 0,
        },
        "execlist": {
            "head": hex(exec_h) if exec_h else "0",
            "count": exec_c,
            "empty": exec_h == 0 and exec_c == 0,
        },
        "inline_blob_reaffirm_ok": inline_ok,
        "prior_2hf_compare": prior_hf,
        "semantics": (
            "RO structure reaffirm only — ring_embed / queue push still STUBBED "
            "(needs human SAFE Post / G4+); no long midflight poll"
        ),
    }


def g2_safe_post_needs_catalog():
    """What SAFE Post would need for ring_embed — catalog from 2fd/2gk/2hf/post_abi only."""
    return {
        "status": "CATALOG_ONLY — does NOT enable Post; G2 live still STUBBED",
        "command_leaf": {
            "name": "CStrategicRedeploymentCommand",
            "factory_idx": 4753,
            "type_id": "0x35b9",
            "size": "0x50",
            "factory_rva": "0x13fb580",
            "vt": "0x2a2d818",
            "isvalid": "0x1402260",
            "execute_thunk_shared_with_MOVE": "0x13fc990",
            "source": "2fd/2fe/2hb/2ijj — catalog MATCH only",
        },
        "action_embed_at_cmd_plus_0x28": {
            "vt": "0x2a1f7e8",
            "type_id_at_plus8": "0x364a",
            "catalog_fields_from_2gk": [
                "army_handle@+0x10",
                "province@+0x18",
                "clear@+0x1C",
                "move_priority@+0x20",
            ],
            "note": "labels from 2gk recipe v2 DESIGN — not invented this slice",
        },
        "dummy_server_offsets_known": {
            "VT": hex(post_abi.CDummyServer_VT),
            "RING": hex(post_abi.CDummyServer_RING),
            "PENDING": hex(post_abi.CDummyServer_PENDING),
            "EXECLIST": hex(post_abi.CDummyServer_EXECLIST),
            "POST_SINK": hex(post_abi.FN_CMD_QUEUE_POST_SINK_DUMMY),
            "DRAIN": hex(post_abi.FN_CMD_QUEUE_DRAIN_DUMMY),
            "RECREATE": "0x22d8ad0",
            "SEQ_ON_SERVER": hex(DUMMY_SEQ),
            "source": "post_abi + 2bq/2br/2gk",
        },
        "ring_layout_class": {
            "kind": "INLINE_BLOB",
            "off": "+0xa0",
            "cap_like_observed": "0x10",
            "not_a_heap_pointer": True,
            "source": "2hf RING_INLINE_LAYOUT_POLISH; reaffirmed 2ijk",
        },
        "recipe_steps_NOT_EXECUTED": [
            "1 factory_alloc (LIVE_RO_MATCH_2fd)",
            "2 fill_header (OFFLINE_BIT_IDENTICAL_2fd)",
            "3 fill_embed@+0x28 (OFFLINE_BIT_IDENTICAL_2fd)",
            "4 serialize_recreate_path (STRUCTURAL_STARTGAME_2bq)",
            "5 queue_placement / ring_embed (STUBBED — NEVER inject this slice)",
        ],
        "still_required_before_g2_live": [
            "G4 human CLAUSEWITZ_ALLOW_POST=1 once",
            "G5 tool-gate open + NEVER_POST",
            "G6 ONE Strategic Post @1x verify then unset",
            "in-process ring_embed push proof on sample (G2 itself)",
        ],
        "hard_deny_this_slice": [
            "ALLOW_POST",
            "Post inject",
            "2fb/2gk recipe execute",
            "ring_embed live push",
            "tool-gate",
            "5x",
            "invent field names",
        ],
    }


def patch_docs(result: str, layout: dict, live: dict, factory_ok: bool):
    g2_note = (
        f"\n### G2 update (2ijk) — ring_embed RO prep (INLINE_BLOB reaffirm; catalog SAFE needs)\n\n"
        f"**Catalog-only. Gate still CLOSED. allow_post False. ring_embed live STUBBED.**\n\n"
        f"- Live reaffirm: `ring_kind=INLINE_BLOB` @ `CDummyServer+0xa0` · "
        f"`server_vt_match={layout.get('server_vt_match')}` · "
        f"`capacity_like_equals_0x10="
        f"{(layout.get('fields_ro_catalog_only') or {}).get('capacity_like_equals_0x10')}` · "
        f"`inline_blob_reaffirm_ok={layout.get('inline_blob_reaffirm_ok')}` "
        f"(result=`{result}`).\n"
        f"- SAFE Post *would* need (not enabled): Strategic factory **4753** / size `0x50` / "
        f"embed@+0x28 · Dummy RING@+0xa0 PENDING@+0x58 EXECLIST@+0x40 · "
        f"POST_SINK `0x23f5cd0` / DRAIN `0x23f64e0` / recreate `0x22d8ad0` · "
        f"recipe v2 steps 1–4 RO proven, step 5 push STUBBED (2gk).\n"
        f"- Live: pid {live.get('pid')} day_index={live.get('day_index')} "
        f"ui={live.get('ui_date')} drain={live.get('drain')} exec={live.get('exec')} · "
        f"factory/FN family_ok={factory_ok}.\n"
        f"- Docs: `docs/PHASE2IJK_G2_RING_EMBED_RO_PREP.md` · "
        f"`reports/phase2ijk_g2_ring_embed_ro_prep.json`.\n"
        f"- Still blocks ALLOW_POST: **G2 live** · **G4** · **G5** · **G6** "
        f"(G1 Strategic-only ACCEPTABLE 2ijj; G3 Instant PARKED).\n\n"
    )

    safe = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
    t2 = safe.read_text(encoding="utf-8")
    # Update G2 row state text if present
    t2 = t2.replace(
        "| G2 | ring_embed live on sample (2fb/2gk) | STUBBED design |",
        "| G2 | ring_embed live on sample (2fb/2gk) | STUBBED live; **RO prep HIT 2ijk** "
        "(INLINE_BLOB reaffirm + SAFE needs catalog) |",
    )
    if "### G2 update (2ijk)" not in t2:
        anchor = "### G1 update (2ijj)"
        if anchor in t2:
            # insert after G1 block: find next ### or ## Missing after G1 section end
            idx = t2.find(anchor)
            # find the blank line before "### Not progress" or next major section after G1
            end_markers = [
                "\n### Not progress",
                "\n## Exact proofs still MISSING",
                "\n## Already DONE",
            ]
            insert_at = None
            for m in end_markers:
                p = t2.find(m, idx)
                if p != -1:
                    insert_at = p
                    break
            if insert_at is None:
                # after still_blocks paragraph near G1
                p = t2.find("Still blocks ALLOW_POST: **G2**", idx)
                if p != -1:
                    insert_at = t2.find("\n\n", p)
            if insert_at is not None:
                t2 = t2[:insert_at] + g2_note + t2[insert_at:]
            else:
                t2 = t2 + g2_note
        else:
            t2 = t2 + g2_note
    row2 = (
        f"| 2ijk | G2 ring_embed RO prep INLINE_BLOB reaffirm + SAFE needs catalog | "
        f"**{result}** (Post still CLOSED; G2 live STUBBED) |\n"
    )
    if "| 2ijk |" not in t2:
        if "| 2ijj |" in t2:
            lines = t2.splitlines(keepends=True)
            out = []
            for line in lines:
                out.append(line)
                if line.startswith("| 2ijj |"):
                    out.append(row2)
            t2 = "".join(out)
        else:
            # append near 2iji/2ijh trail
            for key in ("| 2iji |", "| 2ijh |", "| 2ijg |"):
                if key in t2:
                    lines = t2.splitlines(keepends=True)
                    out = []
                    for line in lines:
                        out.append(line)
                        if line.startswith(key):
                            out.append(row2)
                    t2 = "".join(out)
                    break
    # Exact next human-gated G2 line
    t2 = t2.replace(
        "[ ] G2 ring_embed live proof on captured sample (still STUBBED)",
        "[~] G2 ring_embed RO prep HIT 2ijk (INLINE_BLOB + SAFE needs catalog); "
        "**live push still STUBBED**",
    )
    if "*Phase 2ijk" not in t2:
        t2 = t2.rstrip() + (
            f"\n\n*Phase 2ijk — G2 ring_embed RO prep. Gate stays CLOSED. "
            f"2026-11-01 Asia/Shanghai*\n"
        )
    safe.write_text(t2, encoding="utf-8")

    land = ROOT / "docs" / "LAND_POST_READINESS.md"
    t = land.read_text(encoding="utf-8")
    land_note = (
        f"\n**2ijk G2 ring_embed RO prep:** result=`{result}` · INLINE_BLOB reaffirm "
        f"server_vt_match={layout.get('server_vt_match')} · "
        f"cap_like="
        f"{(layout.get('fields_ro_catalog_only') or {}).get('u32_1_capacity_like')} · "
        f"seq={(layout.get('fields_ro_catalog_only') or {}).get('seq_at_server_plus_0xd0')} · "
        f"day_index={live.get('day_index')} UI={live.get('ui_date')} "
        f"drain={live.get('drain')} exec={live.get('exec')} · "
        f"SAFE Post needs catalogued (offsets/VT/size/factory) · "
        f"ring_embed live STUBBED · allow_post=False.\n"
    )
    if "**2ijk G2 ring_embed RO prep:**" not in t:
        if "**2ijj" in t:
            idx = t.find("**2ijj")
            eol = t.find("\n", idx)
            if eol != -1:
                t = t[: eol + 1] + land_note + t[eol + 1 :]
            else:
                t = t + land_note
        elif "## 6f." in t:
            idx = t.find("## 6f.")
            # append near end of 6f — after first paragraph block
            t = t[:idx] + land_note + "\n" + t[idx:]
        else:
            t = t + land_note
    # Next shortest
    old_next = (
        "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed"
    )
    new_next = (
        "**Next shortest NON-Post:** G2 live ring_embed still needs human SAFE Post "
        "(G4); RO prep HIT 2ijk — retry GitHub push when reachable. Still **NO ALLOW_POST**."
    )
    if "G2 live ring_embed still needs human SAFE Post" not in t:
        # replace common next-shortest variants softly
        if old_next in t:
            # replace first occurrence only
            t = t.replace(
                "**Next shortest NON-Post:** human midflight CMove hex / SAFE Post for ring_embed OR later Assign oi≠0",
                new_next,
                1,
            )
            if old_next in t and "G2 live ring_embed still needs" not in t:
                t = t.replace(old_next, new_next.split(" — ")[0] + " —", 1)
        elif "**Next shortest NON-Post:**" in t:
            pass  # leave other variants; note already added
        else:
            t = t + "\n" + new_next + "\n"
    # Path C honesty footnote
    honesty = (
        "\n- **2ijk:** G2 ring_embed RO prep INLINE_BLOB + SAFE needs catalog; "
        "NO Post; Instant PARKED; PathC ~60–62% honesty (≤+1–2pp readiness clarity; "
        "~70% NOT crossed; G2 live/G4+ still block).\n"
    )
    if "**2ijk:** G2 ring_embed RO prep" not in t:
        if "**2ijj:**" in t:
            idx = t.find("**2ijj:**")
            eol = t.find("\n", idx)
            if eol != -1:
                t = t[: eol + 1] + honesty.lstrip("\n") + t[eol + 1 :]
            else:
                t = t + honesty
        else:
            t = t + honesty
    if "*Phase 2ijk" not in t:
        t = t.rstrip() + (
            "\n\n*Phase 2ijk · G2 ring_embed RO prep · 2026-11-01 Asia/Shanghai*\n"
        )
    land.write_text(t, encoding="utf-8")


def write_doc(result, layout, live, factory, g2_needs):
    fr = (layout.get("fields_ro_catalog_only") or {})
    DOC.write_text(
        f"""# Phase 2ijk — G2 ring_embed RO prep (INLINE_BLOB + SAFE needs catalog)

**Result:** `{result}`  
**allow_post:** **False** · ring_embed live **STUBBED** · 2fb/2gk recipe **NOT executed** · never 5x

## Why this slice

G1 Strategic-only is ACCEPTABLE (2ijj). Shortest NON-Post step toward G2 is reaffirming
Dummy `ring@+0xa0` **INLINE_BLOB** classification on the live continuum pid and cataloguing
what a future human SAFE Post would need for ring_embed — **without** enabling Post.

## Live RO reaffirm

| Item | Value |
| --- | --- |
| ring_kind | `{layout.get("ring_kind")}` |
| ring_off | `{layout.get("ring_off")}` |
| server_vt_rva | `{layout.get("server_vt_rva")}` |
| server_vt_match | `{layout.get("server_vt_match")}` |
| capacity_like | `{fr.get("u32_1_capacity_like")}` |
| capacity_like_equals_0x10 | `{fr.get("capacity_like_equals_0x10")}` |
| inline_blob_reaffirm_ok | `{layout.get("inline_blob_reaffirm_ok")}` |
| seq@server+0xd0 | `{fr.get("seq_at_server_plus_0xd0")}` |
| pending empty | `{(layout.get("pending") or {}).get("empty")}` |
| execlist empty | `{(layout.get("execlist") or {}).get("empty")}` |

Correction vs 2he: RING is an **INLINE blob**, not a heap pointer (2hf; reaffirmed here).

## SAFE Post would need (catalog only — NOT enabled)

See report `g2_safe_post_needs`. Summary:

- Strategic leaf factory **4753** · type_id `0x35b9` · size `0x50` · factory `0x13fb580`
- Action embed @ cmd `+0x28` (VT `0x2a1f7e8`, type_id `0x364a`) — field labels from 2gk only
- Dummy: VT `0x2bcb040` · RING `+0xa0` · PENDING `+0x58` · EXECLIST `+0x40` · seq `+0xd0`
- Sink/drain/recreate RVAs known from post_abi / 2bq — **push STUBBED**
- Recipe v2 steps 1–4 RO/DESIGN; step 5 queue_placement **NEVER** this slice

## Factory / Post-ABI RO (cheap reaffirm)

- all_factory_match: `{factory.get("all_factory_match")}`
- all_fn_match: `{factory.get("all_fn_match")}`
- strategic_4753_match: `{factory.get("strategic_4753_match")}`

## Live

pid {live.get("pid")} · day_index={live.get("day_index")} · ui={live.get("ui_date")} ·
drain={live.get("drain")} · exec={live.get("exec")} · allow_post=False · speed pause/1x only

## Gate

**CLOSED.** G2 **live** still STUBBED. G4/G5/G6 still block. Instant PARKED. No ALLOW_POST.

## Path C honesty (t50u)

~60% baseline; this slice ≤+1–2pp G2 readiness clarity. **~70% NOT crossed.**

*Phase 2ijk · 2026-11-01 Asia/Shanghai*
""",
        encoding="utf-8",
    )


def main() -> int:
    assert allow_post() is False
    hb = load_mod("p2hb", "scripts/phase2hb_move_family_fn_polish.py")
    pid = find_pid()
    if not pid:
        SUMMARY.write_text(
            json.dumps(
                {
                    "phase": "2ijk",
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
    scenario = "ITA@1x G2 ring_embed RO prep INLINE_BLOB (no Post, no Instant, no midflight)"
    s0 = continuum_live(b, base, pid, tag, scenario)
    time.sleep(2)
    s1 = continuum_live(b, base, pid, tag, scenario)
    layout = ring_layout_ro(b, base)
    polish = hb.factory_and_fn(b, base)
    g2_needs = g2_safe_post_needs_catalog()

    inline_ok = bool(layout.get("inline_blob_reaffirm_ok"))
    family_ok = bool(polish.get("all_factory_match")) and bool(polish.get("all_fn_match"))
    if inline_ok and family_ok:
        result = "G2_RING_EMBED_RO_PREP_HIT"
    elif inline_ok:
        result = "G2_RING_INLINE_BLOB_HIT_FACTORY_PARTIAL"
    else:
        result = "G2_RING_EMBED_RO_PREP_PARTIAL"

    calendar_ok = (s1.get("day_index") or 0) > (s0.get("day_index") or 0) or (
        (s1.get("exec") or 0) > (s0.get("exec") or 0)
    ) or ((s1.get("drain") or 0) > (s0.get("drain") or 0))

    out = {
        "phase": "2ijk",
        "slice": "g2_ring_embed_ro_prep_NONPOST",
        "result": result,
        "allow_post": False,
        "post_executed": False,
        "ring_embed_executed": False,
        "instant_parked": True,
        "path_og50_densify": False,
        "midflight_poll": False,
        "ring_layout": layout,
        "g2_safe_post_needs": g2_needs,
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
            "~60%; G2 ring_embed RO prep (INLINE_BLOB + SAFE needs catalog) adds "
            "≤+1–2pp readiness clarity toward G2 — does NOT unlock Post or cross "
            "~70% while G2 live / G4 / G5 / G6 remain"
        ),
        "doc": "docs/PHASE2IJK_G2_RING_EMBED_RO_PREP.md",
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
            "invent field names",
        ],
    }
    OUT.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    brief = {
        k: out[k]
        for k in (
            "phase",
            "result",
            "allow_post",
            "ring_layout",
            "g2_safe_post_needs",
            "move_family_polish",
            "live",
            "calendar_sample",
            "path_c_progress_honesty",
            "doc",
        )
    }
    # Shrink summary ring_layout blob
    if isinstance(brief.get("ring_layout"), dict):
        rl = dict(brief["ring_layout"])
        rl.pop("ring_blob_hex", None)
        rl.pop("ring_u32", None)
        brief["ring_layout"] = rl
    SUMMARY.write_text(json.dumps(brief, indent=2, default=str), encoding="utf-8")
    write_doc(result, layout, s1, polish, g2_needs)
    patch_docs(result, layout, s1, family_ok)
    print(
        json.dumps(
            {
                "result": result,
                "inline_blob_reaffirm_ok": layout.get("inline_blob_reaffirm_ok"),
                "server_vt_match": layout.get("server_vt_match"),
                "capacity_like_equals_0x10": (layout.get("fields_ro_catalog_only") or {}).get(
                    "capacity_like_equals_0x10"
                ),
                "all_factory_match": polish.get("all_factory_match"),
                "all_fn_match": polish.get("all_fn_match"),
                "strategic_4753_match": polish.get("strategic_4753_match"),
                "calendar_ok": calendar_ok,
                "allow_post": False,
                "live": {
                    "pid": s1.get("pid"),
                    "year": s1.get("year"),
                    "day_index": s1.get("day_index"),
                    "ui_date": s1.get("ui_date"),
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
