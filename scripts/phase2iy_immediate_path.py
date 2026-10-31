#!/usr/bin/env python3
"""Phase 2iy: post one IsValid strategic order and read the army path immediately.

Does not call the command-slot thunk (that tail-jumps into Execute and crashed
the process). Action IsValid is vt+0x48. One post. Speed is not written.
"""
from __future__ import annotations

import importlib.util
import json
import struct
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))
import post_abi
from handle import HANDLE_TYPE_ARMY, resolve_handle
from process import Backend, find_pid

spec = importlib.util.spec_from_file_location("iw", ROOT / "scripts" / "phase2iw_one_strategic_post.py")
iw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(iw)

OUT = ROOT / "reports" / "phase2iy_immediate_path.json"
ARMY = 1042
DEST = 758
ACTION_ISVALID = 0x12C2C20


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def i32(b, a):
    return struct.unpack("<i", b.read(a, 4))[0]


def path_ids(b, base, army):
    blob = b.read(army + 0x200, 24)
    data, _c, size = struct.unpack_from("<Qii", blob, 0)
    if data < 0x10000 or not (0 < size <= 24) or base <= data < base + 0x4000000:
        return []
    raw = b.read(data, size * 4)
    vals = list(struct.unpack("<" + "I" * size, raw))
    if not all(1 <= v <= 20000 for v in vals):
        return []
    return vals


def main():
    pid = find_pid()
    b = Backend()
    base = b.image_base
    gs = u64(b, base + post_abi.G_GAMESTATE)
    year = i32(b, gs + 0x478)
    days = i32(b, gs + 0x484)
    army = resolve_handle(b, HANDLE_TYPE_ARMY, ARMY, base)
    before = {
        "date": (datetime(year, 1, 1) + timedelta(days=days)).strftime("%Y-%m-%d"),
        "province": u32(b, army + 0x28),
        "path": path_ids(b, base, army),
    }
    made = iw.remote_call(pid, base + iw.FACTORY_RVA)
    cmd = made["rax"]
    if made["wait"] != 0 or cmd < 0x10000:
        print(json.dumps({"result": "FACTORY_FAIL", "before": before}))
        return 2
    iw.write_bytes(pid, cmd + 0x38, struct.pack("<IIIiI", 0x33, ARMY, DEST, 1, 2))
    valid = iw.remote_call(pid, base + ACTION_ISVALID, {"rcx": cmd + 0x28})
    if valid["wait"] != 0 or (valid["rax"] & 0xFF) != 1:
        result = {"result": "ISVALID_NOT_TRUE", "valid": valid["rax"] & 0xFF, "wait": valid["wait"], "before": before}
        OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 0
    sess = u64(b, base + post_abi.G_SESSION)
    posted = iw.remote_call(pid, base + post_abi.FN_CMD_QUEUE_POST, {"rcx": sess, "rdx": cmd, "r8": 1})
    b = Backend()
    if find_pid() != pid:
        print(json.dumps({"result": "PROCESS_EXITED", "before": before}))
        return 4
    army = resolve_handle(b, HANDLE_TYPE_ARMY, ARMY, base)
    after_path = path_ids(b, base, army)
    after_prov = u32(b, army + 0x28)
    blob = b.read(army, 0x300)
    hits = [hex(i) for i in range(0, 0x300 - 4, 4) if struct.unpack_from("<I", blob, i)[0] == DEST]
    report = {
        "phase": "2iy",
        "result": "PATH_CONTAINS_DEST" if DEST in after_path or after_prov == DEST else "POSTED_DEST_NOT_IN_PATH",
        "before": before,
        "dest": DEST,
        "isvalid": 1,
        "post_rax": posted["rax"] & 0xFF,
        "post_wait": posted["wait"],
        "after_province": after_prov,
        "after_path": after_path,
        "dest_dwords_in_army": hits,
        "alive": find_pid() == pid,
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
