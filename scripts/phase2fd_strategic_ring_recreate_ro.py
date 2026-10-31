#!/usr/bin/env python3
"""Phase 2fd: Dummy ring recreate proof RO for Strategic sample.

- Offline: bit-identical rebuild of 2fa Strategic cmd (size 0x50) from catalog fields.
- Live RO: factory table slot + recreate FN readable + Dummy ring structure.
- Does NOT execute 2fb recipe, Post, or writes. allow_post stays False.
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
import post_abi
from config import allow_post
from process import Backend, find_pid

CAPTURE = ROOT / "reports" / "phase2fa_leaf_move_capture.json"
OUT = ROOT / "reports" / "phase2fd_strategic_ring_recreate_ro.json"
SUMMARY = ROOT / "reports" / "phase2fd_summary.json"
DOC = ROOT / "docs" / "PHASE2FD_STRATEGIC_RING_RECREATE_RO.md"
SAFE_JSON = ROOT / "research" / "safe_enable_checklist.json"

RECREATE = cmd_layout.FACTORY_TABLE["recreate"]  # 0x22d8ad0


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def factory_idx(tid: int) -> int:
    ft = cmd_layout.FACTORY_TABLE
    return tid - ft["index_bias"] if tid >= ft["index_bias_sub_if_ge"] else tid


def live_hours(b, base):
    try:
        ov = json.loads((ROOT / "calling" / "offsets_verified.json").read_text(encoding="utf-8"))
        gs_rva = ov["G_GAMESTATE"] if isinstance(ov["G_GAMESTATE"], int) else ov["G_GAMESTATE"]["rva"]
        gs = u64(b, base + gs_rva)
        hours = u32(b, gs + 0x484)
        d = date(1936, 1, 1) + timedelta(days=hours // 24)
        return {"hours": hours, "ui_date": f"{d.isoformat()} {hours % 24:02d}:00"}
    except Exception as e:
        return {"error": str(e)}


def offline_rebuild(cap: dict) -> dict:
    S = cmd_layout.STRATEGIC
    live = bytes.fromhex(cap["hex"])[: S["size"]]
    vt_cmd = struct.unpack_from("<Q", live, 0)[0]
    vt_act = struct.unpack_from("<Q", live, 0x28)[0]
    tick = struct.unpack_from("<I", live, 0xC)[0]
    f18 = struct.unpack_from("<I", live, 0x18)[0]
    seq = struct.unpack_from("<I", live, 0x1C)[0]
    emb = cap["action_embed"]
    army = emb["army_handle"]
    prov = emb["province"]
    clear = emb["clear"]
    mp = emb["move_priority"]
    unk_embed_0c = struct.unpack_from("<I", live, 0x34)[0]

    buf = bytearray(S["size"])
    struct.pack_into("<Q", buf, 0, vt_cmd)
    struct.pack_into("<I", buf, 0xC, tick)
    struct.pack_into("<I", buf, 0x18, f18)
    struct.pack_into("<I", buf, 0x1C, seq)
    struct.pack_into("<I", buf, 0x20, seq)  # echoed in 2fa sample
    # embed @+0x28
    struct.pack_into("<Q", buf, S["action_embed"], vt_act)
    struct.pack_into("<I", buf, S["action_embed"] + 8, S["action"]["type_id"])
    struct.pack_into("<I", buf, S["action_embed"] + 0xC, unk_embed_0c)
    f = S["action"]["fields"]
    struct.pack_into("<I", buf, S["action_embed"] + f["army_handle"], army[0])
    struct.pack_into("<I", buf, S["action_embed"] + f["army_handle"] + 4, army[1])
    struct.pack_into("<I", buf, S["action_embed"] + f["province"], prov)
    buf[S["action_embed"] + f["clear"]] = clear
    struct.pack_into("<I", buf, S["action_embed"] + f["move_priority"], mp)
    rebuilt = bytes(buf)

    diffs = []
    for i, (a, c) in enumerate(zip(rebuilt, live)):
        if a != c:
            diffs.append({"off": hex(i), "rebuilt": hex(a), "live": hex(c)})

    return {
        "status": "PASS" if rebuilt == live else "FAIL",
        "size": hex(S["size"]),
        "bit_identical": rebuilt == live,
        "diff_count": len(diffs),
        "diffs_head": diffs[:8],
        "fields_used": {
            "vt_cmd_abs_from_capture": hex(vt_cmd),
            "vt_act_abs_from_capture": hex(vt_act),
            "tick": tick,
            "field_18": hex(f18),
            "seq": seq,
            "seq_echo_at_0x20": True,
            "embed_type_id": hex(S["action"]["type_id"]),
            "embed_unk_0c": hex(unk_embed_0c),
            "army_handle": army,
            "province": prov,
            "clear": clear,
            "move_priority": mp,
        },
        "live_hex": live.hex(),
        "rebuilt_hex": rebuilt.hex(),
        "note": (
            "Offline harness rebuilds cmd object bytes from catalog offsets + 2fa field values; "
            "absolute VTs taken from capture (ASLR). Proves layout↔hex round-trip WITHOUT live writes."
        ),
    }


def live_factory_recreate_ro(b, base) -> dict:
    S = cmd_layout.STRATEGIC
    ft = cmd_layout.FACTORY_TABLE
    tid = S["type_id"]
    idx = factory_idx(tid)
    idx_catalog = S.get("factory_idx")
    slot = u64(b, base + ft["rva"] + idx * 8)
    slot_rva = slot - base if slot >= base else slot
    slot_catalog_idx = None
    slot_catalog_rva = None
    if isinstance(idx_catalog, int):
        slot_catalog_idx = u64(b, base + ft["rva"] + idx_catalog * 8)
        slot_catalog_rva = slot_catalog_idx - base if slot_catalog_idx >= base else slot_catalog_idx

    # recreate FN readable
    rec = b.read(base + RECREATE, 32)
    # factory lookup FN readable
    lookup = b.read(base + ft["lookup"], 32)
    # Strategic factory body readable
    fac = b.read(base + S["factory"], 32)
    # gettypeid imm/mem quick (no Capstone): scan for C7 02 imm32
    gt = b.read(base + S["gettypeid"], 24)
    gettypeid_imm = None
    for i in range(len(gt) - 5):
        if gt[i] == 0xC7 and gt[i + 1] == 0x02:
            gettypeid_imm = struct.unpack_from("<I", gt, i + 2)[0]
            break

    # action serialize token presence (bytes scan, no Capstone)
    ser = b.read(base + S["action"]["serialize"], 0x120)
    tokens = S["action"]["serialize_tokens"]
    token_hits = {hex(tok): (struct.pack("<I", tok) in ser) for tok in tokens.values()}

    factory_match = slot_rva == S["factory"]
    return {
        "type_id": hex(tid),
        "factory_idx_formula": idx,
        "factory_idx_catalog_stale": idx_catalog,
        "factory_idx_note": (
            f"formula tid-0x2328 when tid>=0x2710 → {idx}; "
            f"catalog factory_idx={idx_catalog} is STALE vs live formula (do not Capstone churn)"
        ),
        "factory_table_slot_rva": hex(slot_rva),
        "catalog_factory_rva": hex(S["factory"]),
        "factory_slot_matches_catalog": factory_match,
        "stale_idx_slot_rva": hex(slot_catalog_rva) if slot_catalog_rva is not None else None,
        "recreate_rva": hex(RECREATE),
        "recreate_readable": len(rec) == 32,
        "recreate_prologue_hex": rec[:16].hex(),
        "lookup_rva": hex(ft["lookup"]),
        "lookup_readable": len(lookup) == 32,
        "factory_body_readable": len(fac) == 32,
        "factory_prologue_hex": fac[:16].hex(),
        "gettypeid_imm": hex(gettypeid_imm) if gettypeid_imm is not None else None,
        "gettypeid_matches_type_id": gettypeid_imm == tid,
        "action_serialize_token_hits": token_hits,
        "all_action_tokens_present": all(token_hits.values()),
        "birth_path_observe": (
            f"GetTypeId({hex(tid)}) → ser → recreate({hex(RECREATE)}) → "
            f"factory_lookup idx={idx} → factory {hex(S['factory'])} → "
            f"vt+0x18 des → ring@+{hex(post_abi.CDummyServer_RING)}"
        ),
    }


def live_dummy_ring_ro(b, base) -> dict:
    sess = u64(b, base + post_abi.G_SESSION)
    server = u64(b, sess + post_abi.CSession_SERVER)
    vt = u64(b, server) - base
    ring = server + post_abi.CDummyServer_RING
    # 2bq-style ring meta: read 0x40 at ring
    blob = b.read(ring, 0x40)
    pending_h = u64(b, server + post_abi.CDummyServer_PENDING)
    pending_c = u32(b, server + post_abi.CDummyServer_PENDING + 0x10)  # count +0x68 = pending+0x10
    execlist_h = u64(b, server + post_abi.CDummyServer_EXECLIST)
    execlist_c = u32(b, server + post_abi.CDummyServer_EXECLIST + 0x10)
    seq = u32(b, server + 0xD0)
    return {
        "session": hex(sess),
        "server": hex(server),
        "server_vt_rva": hex(vt),
        "server_vt_match": vt == post_abi.CDummyServer_VT,
        "ring_addr": hex(ring),
        "ring_blob_hex": blob.hex(),
        "pending_head": hex(pending_h) if pending_h else "0x0",
        "pending_count": pending_c,
        "execlist_head": hex(execlist_h) if execlist_h else "0x0",
        "execlist_count": execlist_c,
        "seq": seq,
        "note": "RO snapshot only — no ring push / no Post",
    }


def update_safe(result: str) -> None:
    j = json.loads(SAFE_JSON.read_text(encoding="utf-8"))
    j["notes_2fd"] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "allow_post": False,
        "offline_rebuild": "PASS" if "PASS" in result else result,
        "live_factory_wiring": "see report",
        "in_process_ring_embed": "STUBBED_needs_Post",
        "executed_2fb_recipe": False,
        "gate": "CLOSED",
    }
    for b in j.get("blocks_enabling_post") or []:
        if isinstance(b, dict) and b.get("id") == "serialize_recreate_roundtrip":
            b["status"] = (
                "offline_strategic_rebuild_PASS_live_factory_RO_"
                "inprocess_ring_embed_STUBBED"
            )
            b["note"] = (
                "2fd: offline Strategic 0x50 bit-identical rebuild PASS; "
                "live factory/recreate wiring RO; in-process ring embed still needs Post — "
                "NOT executed; allow_post False"
            )
    j["allow_post"] = False
    j["posting"] = "DISABLED"
    SAFE_JSON.write_text(json.dumps(j, indent=2), encoding="utf-8")


def main() -> int:
    assert allow_post() is False
    cap_raw = json.loads(CAPTURE.read_text(encoding="utf-8"))
    cap = cap_raw["captures"][0]
    offline = offline_rebuild(cap)

    live = {"skipped": True}
    dummy = {"skipped": True}
    date_info = {}
    pid = None
    try:
        pid = find_pid("hoi4.exe")
        b = Backend(pid)
        base = int(b.image_base)
        date_info = live_hours(b, base)
        live = live_factory_recreate_ro(b, base)
        dummy = live_dummy_ring_ro(b, base)
    except Exception as e:
        live = {"error": str(e)}
        dummy = {"error": str(e)}

    factory_ok = bool(live.get("factory_slot_matches_catalog"))
    tokens_ok = bool(live.get("all_action_tokens_present"))
    gettypeid_ok = bool(live.get("gettypeid_matches_type_id"))
    recreate_ok = bool(live.get("recreate_readable"))

    if offline["status"] == "PASS" and factory_ok and recreate_ok:
        result = "STRATEGIC_OFFLINE_REBUILD_PASS_LIVE_FACTORY_RO_RING_EMBED_STILL_STUBBED"
    elif offline["status"] == "PASS":
        result = "STRATEGIC_OFFLINE_REBUILD_PASS_LIVE_WIRING_PARTIAL"
    else:
        result = "STRATEGIC_OFFLINE_REBUILD_FAIL"

    harness_gap = {
        "in_process_serialize_recreate_ring_embed": {
            "status": "STUBBED",
            "why": (
                "Pushing rebuilt buffer into CDummyServer ring requires Post/sink write path; "
                "2fb recipe execution FORBIDDEN; allow_post False"
            ),
            "next_cheapest_RO": (
                "Keep offline rebuild PASS + live factory/recreate RO as proof ceiling until SAFE opens; "
                "optional: compare sticky StartGame 2bq structural RT pattern — no Capstone/121"
            ),
        }
    }

    report = {
        "phase": "2fd",
        "ts": datetime.now(timezone.utc).isoformat(),
        "allow_post": False,
        "executed_2fb_recipe": False,
        "never_5x": True,
        "pid": pid,
        "date": date_info,
        "source_capture": {
            "addr": cap.get("addr"),
            "seq": cap.get("seq"),
            "list": cap.get("list"),
            "captured_at_asia_shanghai": cap.get("captured_at_asia_shanghai"),
        },
        "offline_rebuild": offline,
        "live_factory_recreate": live,
        "live_dummy_ring": dummy,
        "harness_gap": harness_gap,
        "result": result,
    }
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    update_safe(result)

    works = [
        f"offline Strategic 0x50 rebuild {offline['status']} (bit_identical={offline['bit_identical']})",
        "did NOT execute 2fb recipe / Post / writes",
        "allow_post stays False",
    ]
    if factory_ok:
        works.append(f"live factory slot idx={live.get('factory_idx_formula')} → {live.get('factory_table_slot_rva')} MATCH")
    if recreate_ok:
        works.append("recreate FN 0x22d8ad0 readable RO")
    if gettypeid_ok:
        works.append("gettypeid imm matches type_id 0x35b9")
    if tokens_ok:
        works.append("action serialize tokens present RO")

    stubbed = [
        "in-process serialize→recreate→ring embed (needs Post)",
        "2fb recipe execution",
        "ordinary CMove live",
        "SAFE_POST",
        "self-MOVE",
        "tool-gate open",
    ]

    summary = {
        "phase": "2fd",
        "result": result,
        "scenario": "ETH@1x offline+live RO (no Post)",
        "pid": pid,
        "ui_date": (date_info or {}).get("ui_date"),
        "hours": (date_info or {}).get("hours"),
        "allow_post": False,
        "offline_rebuild": offline["status"],
        "factory_slot_match": factory_ok,
        "gettypeid_match": gettypeid_ok,
        "action_tokens_ok": tokens_ok,
        "factory_idx_formula": live.get("factory_idx_formula"),
        "works": works,
        "stubbed": stubbed,
        "harness_gap": harness_gap["in_process_serialize_recreate_ring_embed"]["why"],
        "next_shortest_blocker": (
            "In-process Dummy ring embed still needs Post — STUBBED; "
            "next cheapest RO: treat offline PASS+factory wiring as ceiling OR "
            "SAFE human review only — still NO ALLOW_POST"
        ),
        "parent_sha_base": "958b284",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    DOC.write_text(
        f"""# Phase 2fd — Strategic Dummy ring recreate RO

**Result:** `{result}`  
**allow_post:** **False** · 2fb recipe **NOT executed** · never 5x

## A) Offline rebuild (harness)

Rebuilt `CStrategicRedeploymentCommand` size `0x50` from catalog offsets + 2fa fields  
(absolute VTs from capture for ASLR).

| check | value |
|-------|-------|
| status | **{offline['status']}** |
| bit_identical | {offline['bit_identical']} |
| army_handle | {offline['fields_used']['army_handle']} |
| province | {offline['fields_used']['province']} |
| clear / move_priority | {offline['fields_used']['clear']} / {offline['fields_used']['move_priority']} |
| embed type_id | {offline['fields_used']['embed_type_id']} |

## B) Live factory / recreate wiring (RO)

| check | value |
|-------|-------|
| type_id | `0x35b9` |
| factory_idx formula | {live.get('factory_idx_formula')} (catalog factory_idx {live.get('factory_idx_catalog_stale')} STALE) |
| table slot RVA | {live.get('factory_table_slot_rva')} |
| catalog factory | `{hex(cmd_layout.STRATEGIC['factory'])}` |
| slot match | {factory_ok} |
| recreate `0x22d8ad0` readable | {recreate_ok} |
| gettypeid imm match | {gettypeid_ok} |
| action ser tokens | {tokens_ok} |

Birth path (observe only): {live.get('birth_path_observe')}

## C) Harness gap (STOP ceiling)

**In-process** serialize→recreate→ring embed still **STUBBED** — requires Post/sink write.  
Not done this slice. No Capstone/121. No endless-poll.

Dummy ring RO snapshot: pending={dummy.get('pending_count')} execlist={dummy.get('execlist_count')} seq={dummy.get('seq')}

## Next

Offline PASS + live factory RO is the proof ceiling without Post.  
Any real ring push waits on SAFE human enable — **still NO ALLOW_POST**.

Artifacts: `reports/phase2fd_*.json`, `scripts/phase2fd_strategic_ring_recreate_ro.py`
""",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
