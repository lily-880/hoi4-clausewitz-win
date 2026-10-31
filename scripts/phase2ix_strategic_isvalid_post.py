#!/usr/bin/env python3
"""Phase 2ix: find a destination Strategic IsValid accepts, then post once.

2iw posted army 1042 toward province 9680. That province belongs to tag 3, not
Italy, and the army never moved. This slice asks the game's own IsValid, picks
an Italian-owned province that passes, posts one strategic redeploy, and checks
whether the army object changes. No speed writes. One post at most.
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
from handle import HANDLE_TYPE_ARMY, resolve_handle
from process import Backend, find_pid
from province import resolve_province

spec = importlib.util.spec_from_file_location(
    "iw", ROOT / "scripts" / "phase2iw_one_strategic_post.py"
)
iw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(iw)

OUT = ROOT / "reports" / "phase2ix_strategic_isvalid_post.json"
SUMMARY = ROOT / "reports" / "phase2ix_summary.json"

ARMY = 1042
PLAYER_TAG = 15
CA_VT = 0x29D6D68
CA_TAG = 0x1E0
CA_PROV = 0x28
CMD_ISVALID = 0x12C2C20  # action vt+0x48; command vt+0x48 tail-jumps to EXECUTE
AUTH = 0x13FE900
STRATEGIC_VT = 0x2A2D818
ACTION_VT = 0x2A1F7E8


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def i32(b, a):
    return struct.unpack("<i", b.read(a, 4))[0]


def game_date(b, base):
    gs = u64(b, base + post_abi.G_GAMESTATE)
    year = i32(b, gs + 0x478)
    day_index = i32(b, gs + 0x484)
    try:
        shown = datetime(year, 1, 1) + timedelta(days=day_index)
        text = shown.strftime("%Y-%m-%d")
    except Exception:
        text = None
    return {"year": year, "day_index": day_index, "date": text}


def italian_provinces(b, base):
    found = {}
    for idx in range(1, 3001):
        try:
            army = resolve_handle(b, HANDLE_TYPE_ARMY, idx, base)
        except Exception:
            continue
        if not army:
            continue
        vt = u64(b, army) - base
        if vt != CA_VT:
            continue
        tag = u32(b, army + CA_TAG)
        if tag != PLAYER_TAG:
            continue
        prov = u32(b, army + CA_PROV)
        found.setdefault(prov, []).append(idx)
    return found


def fill(pid, cmd, army_index, dest):
    fields = struct.pack("<IIIiI", 0x33, army_index, dest, 1, 2)
    iw.write_bytes(pid, cmd + 0x38, fields)


def low_byte(result):
    return result["rax"] & 0xFF


def main():
    pid = find_pid()
    if not pid:
        print(json.dumps({"result": "NO_PROCESS"}))
        return 1
    b = Backend()
    base = b.image_base
    date = game_date(b, base)
    src = resolve_handle(b, HANDLE_TYPE_ARMY, ARMY, base)
    if not src:
        print(json.dumps({"result": "ARMY_GONE", "date": date}))
        return 2
    src_prov = u32(b, src + CA_PROV)
    src_tag = u32(b, src + CA_TAG)
    owned = italian_provinces(b, base)
    candidates = [p for p in owned if p != src_prov][:24]
    report = {
        "phase": "2ix",
        "pid": pid,
        "date": date,
        "src": {"index": ARMY, "tag": src_tag, "province": src_prov},
        "italian_province_n": len(owned),
        "candidates": candidates,
    }
    made = iw.remote_call(pid, base + iw.FACTORY_RVA)
    cmd = made["rax"]
    report["factory"] = {"wait": made["wait"], "rax": hex(cmd)}
    if made["wait"] != 0 or cmd < 0x10000:
        report["result"] = "FACTORY_FAIL"
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2)[:2000])
        return 3
    b = Backend()
    vt = u64(b, cmd) - base
    avt = u64(b, cmd + 0x28) - base
    if vt != STRATEGIC_VT or avt != ACTION_VT:
        report["result"] = "VT_MISMATCH"
        report["vt"] = hex(vt)
        report["avt"] = hex(avt)
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2)[:2000])
        return 3

    trials = []
    # Always include the previous bad destination so the failure is explained.
    dests = [9680] + candidates
    seen = set()
    for dest in dests:
        if dest in seen:
            continue
        seen.add(dest)
        if resolve_province(b, dest, base) is None:
            trials.append({"dest": dest, "skip": "not_a_province"})
            continue
        fill(pid, cmd, ARMY, dest)
        valid = iw.remote_call(pid, base + CMD_ISVALID, {"rcx": cmd + 0x28})
        trials.append(
            {
                "dest": dest,
                "owners": owned.get(dest, []),
                "isvalid_wait": valid["wait"],
                "isvalid": low_byte(valid) if valid["wait"] == 0 else None,
            }
        )
        if len(trials) >= 25:
            break
    report["trials"] = trials
    good = next((t for t in trials if t.get("isvalid") == 1), None)
    report["chosen"] = good
    if not good:
        report["result"] = "NO_VALID_DEST"
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        SUMMARY.write_text(
            json.dumps({"phase": "2ix", "result": report["result"], "date": date, "trials": trials[:8]}, indent=2)
            + "\n",
            encoding="utf-8",
        )
        print(json.dumps({"result": report["result"], "date": date, "src_prov": src_prov, "pass_n": 0, "trials": trials[:8]}, indent=2))
        return 0

    dest = good["dest"]
    fill(pid, cmd, ARMY, dest)
    b = Backend()
    before = b.read(src, 0x280)
    sess = u64(b, base + post_abi.G_SESSION)
    server = u64(b, sess + post_abi.CSession_SERVER)
    seq_before = u32(b, server + 0xD0)
    prov_before = u32(b, src + CA_PROV)
    posted = iw.remote_call(
        pid,
        base + post_abi.FN_CMD_QUEUE_POST,
        {"rcx": sess, "rdx": cmd, "r8": 1},
    )
    time.sleep(1.5)
    if find_pid() != pid:
        report["result"] = "PROCESS_EXITED"
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"result": "PROCESS_EXITED"}))
        return 4
    b = Backend()
    after = b.read(src, 0x280)
    diffs = [hex(i) for i in range(0, 0x280, 4) if before[i:i + 4] != after[i:i + 4]]
    prov_after = u32(b, src + CA_PROV)
    seq_after = u32(b, server + 0xD0)
    report["post"] = {
        "wait": posted["wait"],
        "rax": hex(posted["rax"]),
        "dest": dest,
        "prov_before": prov_before,
        "prov_after": prov_after,
        "seq_before": seq_before,
        "seq_after": seq_after,
        "army_diff_n": len(diffs),
        "army_diff_head": diffs[:24],
        "date_after": game_date(b, base),
    }
    if prov_after != prov_before or diffs:
        report["result"] = "ORDER_TOUCHED_ARMY"
    else:
        report["result"] = "VALID_POST_NO_ARMY_DIFF"
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2ix",
                "result": report["result"],
                "date": date,
                "dest": dest,
                "prov_before": prov_before,
                "prov_after": prov_after,
                "seq_delta": seq_after - seq_before,
                "diff_n": len(diffs),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["post"] | {"result": report["result"], "date": date}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
