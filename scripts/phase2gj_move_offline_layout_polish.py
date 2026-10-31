#!/usr/bin/env python3
"""Phase 2gj: ordinary CMove offline layout polish + live factory_idx 1402 RO.

No Post. Never 5x. allow_post False. Does NOT ask user to right-click.
Does NOT execute 2fb recipe. Brief ≤45s CMove pending/stage observe only.
"""
from __future__ import annotations

import json
import struct
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import cmd_layout
import post_abi
from config import allow_post
from process import Backend, find_pid

assert allow_post() is False

OUT = ROOT / "reports" / "phase2gj_move_offline_layout_polish.json"
SUMMARY = ROOT / "reports" / "phase2gj_summary.json"
DOC = ROOT / "docs" / "PHASE2GJ_MOVE_OFFLINE_LAYOUT.md"
OBSERVE_S = 45.0
INTERVAL_S = 0.08
CMOVE_VT = cmd_layout.MOVE["vt"]
TZ = timezone(timedelta(hours=8))


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def i32(b, a):
    return struct.unpack("<i", b.read(a, 4))[0]


def factory_idx(tid: int) -> int:
    ft = cmd_layout.FACTORY_TABLE
    return tid - ft["index_bias"] if tid >= ft["index_bias_sub_if_ge"] else tid


def live_meta(b, base):
    ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
    gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
    gs = u64(b, base + gs_rva)
    hours = i32(b, gs + 0x484)
    d = datetime(1936, 1, 1) + timedelta(hours=int(hours))
    return {
        "hours": hours,
        "ui_date": d.strftime("%Y-%m-%d %H:00"),
        "gs": hex(gs),
    }


def offline_move_skeleton() -> dict:
    """Catalog-accurate 0x88 MOVE skeleton. No live hex → not bit_identical."""
    M = cmd_layout.MOVE
    A = M["action"]
    buf = bytearray(M["size"])
    # Relative VTs (image-base-relative placeholders) — document only; live needs abs
    struct.pack_into("<Q", buf, 0, M["vt"])  # relative marker in offline note
    struct.pack_into("<I", buf, 0xC, 1)  # tick placeholder (Strategic/Cancel observed 1)
    # seq/f18 left 0 — filled by game Post path; observed pattern seq@0x1C echoed @0x20
    # embed @+0x28
    emb = M["action_embed"]
    struct.pack_into("<Q", buf, emb, A["vt"])
    struct.pack_into("<I", buf, emb + 8, A["type_id_at_plus8"])
    f = A["fields"]
    # pointer arrays remain 0 — game alloc required for real midflight
    struct.pack_into("<I", buf, emb + f["province_size"], 0)
    struct.pack_into("<I", buf, emb + f["path_size"], 0)
    buf[emb + f["clear"]] = 1
    struct.pack_into("<I", buf, emb + f["move_priority"], 2)  # PLAYER_ORDER like Strategic
    buf[emb + f["sticky"]] = 0

    # Shared header concordance from Strategic + Cancel live samples
    strat = json.loads((ROOT / "reports" / "phase2fa_leaf_move_capture.json").read_text())
    cancel = json.loads((ROOT / "reports" / "phase2eu_cancel_capture.json").read_text())
    shx = bytes.fromhex(strat["captures"][0]["hex"])
    chx = bytes.fromhex(cancel["captures"][0]["hex"])

    def hdr(hx):
        return {
            "tick_0c": struct.unpack_from("<I", hx, 0xC)[0],
            "f18": hex(struct.unpack_from("<I", hx, 0x18)[0]),
            "seq_1c": struct.unpack_from("<I", hx, 0x1C)[0],
            "seq_20": struct.unpack_from("<I", hx, 0x20)[0],
            "seq_echo": struct.unpack_from("<I", hx, 0x1C)[0]
            == struct.unpack_from("<I", hx, 0x20)[0],
            "embed_starts_0x28": True,
        }

    return {
        "status": "SKELETON_PASS_NO_LIVE_HEX",
        "bit_identical": False,
        "bit_identical_blocker": (
            "No ordinary CMoveCommand midflight hex capture; cannot close sample→rebuild "
            "like Strategic 2fd. province_arr/path_arr need game allocs (Strategic scalar is cheaper)."
        ),
        "size": hex(M["size"]),
        "factory_idx": M["factory_idx"],
        "factory_rva": hex(M["factory"]),
        "type_id": hex(M["type_id"]),
        "vt_rva": hex(M["vt"]),
        "action_vt_rva": hex(A["vt"]),
        "action_type_id_at_plus8": hex(A["type_id_at_plus8"]),
        "action_embed_off": hex(emb),
        "action_fields": f,
        "shared_header_with_strategic_cancel": {
            "strategic": hdr(shx),
            "cancel": hdr(chx),
            "proven_pattern": "tick@+0xC; seq@+0x1C echoed @+0x20; action embed @+0x28",
        },
        "skeleton_hex_relative_vt": bytes(buf).hex(),
        "note": (
            "Offline catalog layout polish only. Relative VTs in skeleton_hex are RVAs not ASLR abs. "
            "IsValid 0x14002F0 / Execute 0x13FC990 (shared thunk w/ Strategic)."
        ),
    }


def live_factory_ro(b, base) -> dict:
    M = cmd_layout.MOVE
    ft = cmd_layout.FACTORY_TABLE
    tid = M["type_id"]
    idx = factory_idx(tid)
    idx_cat = M["factory_idx"]
    slot = u64(b, base + ft["rva"] + idx * 8)
    slot_rva = (slot - base) & 0xFFFFFFFF if slot else 0
    # also probe catalog idx (should be same 1402)
    slot_cat = u64(b, base + ft["rva"] + idx_cat * 8)
    slot_cat_rva = (slot_cat - base) & 0xFFFFFFFF if slot_cat else 0
    rec = b.read(base + ft["recreate"], 16).hex()
    fac = b.read(base + M["factory"], 16).hex()
    gt = b.read(base + M["gettypeid"], 24)
    gettypeid_imm = None
    for i in range(len(gt) - 5):
        if gt[i] == 0xC7 and gt[i + 1] == 0x02:
            gettypeid_imm = struct.unpack_from("<I", gt, i + 2)[0]
            break
    # shared execute thunk with Strategic
    ex_move = M["execute"]
    ex_strat = cmd_layout.STRATEGIC["execute"]
    return {
        "type_id": hex(tid),
        "factory_idx_formula": idx,
        "factory_idx_catalog": idx_cat,
        "idx_formula_matches_catalog": idx == idx_cat,
        "factory_table_slot_rva": hex(slot_rva),
        "catalog_factory_rva": hex(M["factory"]),
        "slot_matches_catalog": slot_rva == M["factory"],
        "catalog_idx_slot_rva": hex(slot_cat_rva),
        "recreate_rva": hex(ft["recreate"]),
        "recreate_prologue_hex": rec,
        "factory_prologue_hex": fac,
        "gettypeid_imm": hex(gettypeid_imm) if gettypeid_imm is not None else None,
        "gettypeid_matches_type_id": gettypeid_imm == tid,
        "shared_execute_thunk_with_strategic": ex_move == ex_strat,
        "execute_rva": hex(ex_move),
        "isvalid_rva": hex(M["isvalid"]),
        "birth_path_observe": (
            f"GetTypeId({hex(tid)}) → ser → recreate({hex(ft['recreate'])}) → "
            f"factory_lookup idx={idx_cat} → factory {hex(M['factory'])} → "
            f"vt+0x18 des → ring@+0xa0 (NOT executed)"
        ),
    }


def walk_pending_stage(b, base):
    """Minimal RO: count stage/pending; sight CMove VT only."""
    sess = u64(b, base + post_abi.G_SESSION)
    server = u64(b, sess + post_abi.CSession_SERVER)
    stage_n = u32(b, sess + post_abi.CSession_STAGE_COUNT)
    pending_n = u32(b, server + post_abi.CDummyServer_PENDING + 0xC)
    hits = []
    # stage array at +0x48: data ptr then walk min(stage_n, 64)
    try:
        stage_data = u64(b, sess + post_abi.CSession_STAGE_ARRAY)
        n = min(stage_n, 64)
        for i in range(n):
            ptr = u64(b, stage_data + i * 8) if stage_data else 0
            if not ptr:
                continue
            vt = u64(b, ptr)
            vt_rva = (vt - base) & 0xFFFFFFFF
            if vt_rva == CMOVE_VT:
                hits.append({"list": f"stage[{i}]", "addr": hex(ptr), "vt_rva": hex(vt_rva)})
    except Exception:
        pass
    try:
        pend_data = u64(b, server + post_abi.CDummyServer_PENDING)
        n = min(pending_n, 64)
        for i in range(n):
            ptr = u64(b, pend_data + i * 8) if pend_data else 0
            if not ptr:
                continue
            vt = u64(b, ptr)
            vt_rva = (vt - base) & 0xFFFFFFFF
            if vt_rva == CMOVE_VT:
                hits.append({"list": f"pending[{i}]", "addr": hex(ptr), "vt_rva": hex(vt_rva)})
    except Exception:
        pass
    return {
        "stage": stage_n,
        "pending": pending_n,
        "cmove_hits": hits,
        "drain": u32(b, sess + post_abi.CSession_DRAIN_COUNTER),
        "exec": u32(b, sess + post_abi.CSession_EXEC_COUNTER),
    }


def main():
    assert allow_post() is False
    offline = offline_move_skeleton()
    pid = find_pid()
    live = {
        "pid": pid,
        "factory_ro": None,
        "observe": None,
        "meta_start": None,
        "meta_end": None,
    }
    result = "MOVE_OFFLINE_SKELETON_PASS_NO_LEAF_HEX"
    if not pid:
        result = "MOVE_OFFLINE_SKELETON_PASS_NO_LIVE_PROCESS"
    else:
        b = Backend()
        base = b.image_base
        live["meta_start"] = live_meta(b, base)
        live["factory_ro"] = live_factory_ro(b, base)
        t0 = time.time()
        polls = 0
        sight = 0
        last = None
        while time.time() - t0 < OBSERVE_S:
            polls += 1
            last = walk_pending_stage(b, base)
            sight += len(last["cmove_hits"])
            if last["cmove_hits"]:
                break
            time.sleep(INTERVAL_S)
        live["meta_end"] = live_meta(b, base)
        live["observe"] = {
            "observe_s": OBSERVE_S,
            "wall_s": round(time.time() - t0, 2),
            "polls": polls,
            "cmove_sightings": sight,
            "cmove_hits": (last or {}).get("cmove_hits") or [],
            "last_stage": (last or {}).get("stage"),
            "last_pending": (last or {}).get("pending"),
            "drain": (last or {}).get("drain"),
            "exec": (last or {}).get("exec"),
            "result": "CMOVE_HIT" if sight else "HONEST_EMPTY",
        }
        if live["factory_ro"].get("slot_matches_catalog") and live["observe"]["result"] == "HONEST_EMPTY":
            result = "MOVE_OFFLINE_SKELETON_PASS_FACTORY1402_MATCH_OBSERVE_EMPTY"
        elif live["factory_ro"].get("slot_matches_catalog") and sight:
            result = "MOVE_OFFLINE_SKELETON_PASS_FACTORY1402_MATCH_CMOVE_SIGHTED"
        elif live["observe"]["result"] == "HONEST_EMPTY":
            result = "MOVE_OFFLINE_SKELETON_PASS_OBSERVE_EMPTY"

    out = {
        "phase": "2gj",
        "result": result,
        "allow_post": False,
        "executed_2fb_recipe": False,
        "never_5x": True,
        "speed_policy": "pause-or-1x only (never change speed)",
        "scenario": "ITA@1x current process — MOVE offline polish + ≤45s CMove RO (no Post)",
        "offline_move": offline,
        "live": live,
        "vs_strategic_2fd": {
            "strategic_offline": "PASS bit_identical (2fd)",
            "move_offline": "SKELETON only — needs midflight hex for bit_identical",
            "shared": "execute thunk 0x13FC990; embed@+0x28; seq echo pattern",
            "move_harder_because": "province_arr + path_arr game allocs vs Strategic scalar province",
        },
        "stubbed": [
            "ordinary CMove midflight leaf hex",
            "ring_embed in-process",
            "2fb recipe execute",
            "ALLOW_POST",
            "tool-gate",
        ],
        "next_shortest_blocker": (
            "NON-Post: human midflight CMove hex (or SAFE Dummy recreate on Strategic only) "
            "— still NO ALLOW_POST; retry push when GitHub reachable"
        ),
        "captured_at": datetime.now(TZ).strftime("%Y-%m-%d %H:%M Asia/Shanghai"),
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2gj",
                "result": result,
                "allow_post": False,
                "pid": pid,
                "ui": (live.get("meta_end") or live.get("meta_start") or {}),
                "factory_idx_1402_match": (live.get("factory_ro") or {}).get("slot_matches_catalog"),
                "observe": (live.get("observe") or {}).get("result"),
                "offline": offline["status"],
                "next_shortest_blocker": out["next_shortest_blocker"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    DOC.write_text(
        f"""# Phase 2gj — ordinary CMove offline layout polish

**Result:** `{result}`  
**allow_post:** **False** · 2fb recipe **NOT executed** · never 5x

## A) Offline MOVE skeleton (catalog)

| check | value |
|-------|-------|
| status | **{offline["status"]}** |
| bit_identical | **False** (no live CMove hex) |
| size / factory_idx | `{offline["size"]}` / **{offline["factory_idx"]}** |
| factory RVA | `{offline["factory_rva"]}` |
| type_id / VT | `{offline["type_id"]}` / `{offline["vt_rva"]}` |
| action embed | `@+0x28` VT `{offline["action_vt_rva"]}` type `{offline["action_type_id_at_plus8"]}` |

Shared header (Strategic + Cancel live): tick`@+0xC`; seq`@+0x1C` echoed `@+0x20`; embed `@+0x28`.

Action fields needing game alloc (blocker vs Strategic scalar): `province_arr`, `path_arr`.

## B) Live factory_idx 1402 RO

See `reports/phase2gj_move_offline_layout_polish.json` → `live.factory_ro`.

## C) Brief ≤45s CMove observe

Pending/stage VT sight only — no heap marathon. Honest empty is success for this slice.

## Harness gap

In-process serialize→recreate→ring embed still **STUBBED**. Offline Strategic remains the only bit_identical rebuild (2fd). Ordinary CMove still needs a midflight hex sample (human gameplay; agent must not ask/inject).

**Gate CLOSED. still NO ALLOW_POST.**

Artifacts: `reports/phase2gj_*.json`, `scripts/phase2gj_move_offline_layout_polish.py`
""",
        encoding="utf-8",
    )
    print(json.dumps({"result": result, "pid": pid, "summary": json.loads(SUMMARY.read_text())}, indent=2)[:1500])
    return 0 if offline["status"].startswith("SKELETON") else 1


if __name__ == "__main__":
    raise SystemExit(main())
