"""One proven Windows post: CCancelMovementCommand (factory idx 1415).

Factory 0x13FACE0 builds CCancelMovementCommand. Units vector at +0x28 (Qii:
ptr/size/cap) holds CHandle{type=0x33,index}. Live units buffer MUST be
ucrtbase!malloc (same heap lesson as Move 2ijy/2ijz). IsValid RVA 0x13FED40
(rcx=cmd). Post: FN_CMD_QUEUE_POST.
"""
from __future__ import annotations

import struct

import post_abi
from config import assert_post_allowed, allow_post
from handle import HANDLE_TYPE_ARMY, resolve_handle
from process import Backend, find_pid
import move_order as mo

FACTORY_RVA = 0x13FACE0
FACTORY_IDX = 1415
ISVALID_RVA = 0x13FED40
CANCEL_VT = 0x2A2C9B8
ARMY_VT = 0x29D6D68
PATH_OFF = 0x200
HANDLE_TYPE = 0x33
UNITS_OFF = 0x28  # Qii ptr,size,cap
STICKY_OFF = 0x40


def cancel_movement(army_index: int, dry_run: bool = False) -> dict:
    """Post CancelMovement for one army, or IsValid-only when dry_run."""
    pid = find_pid()
    if not pid:
        return {"ok": False, "result": "NO_PROCESS"}
    b = Backend()
    base = b.image_base
    army = resolve_handle(b, HANDLE_TYPE_ARMY, army_index, base)
    if not army or mo._u64(b, army) - base != ARMY_VT:
        return {"ok": False, "result": "ARMY_NOT_FOUND", "army": army_index}
    before = mo._path(b, base, army)

    made = mo._remote(pid, base + FACTORY_RVA, wait_ms=5000)
    cmd = made["rax"]
    if made["wait"] != 0 or cmd < 0x10000:
        return {"ok": False, "result": "FACTORY_FAIL", "call": made}
    if mo._u64(b, cmd) - base != CANCEL_VT:
        return {
            "ok": False,
            "result": "FACTORY_VT_MISMATCH",
            "vt": hex(mo._u64(b, cmd) - base),
            "expect": hex(CANCEL_VT),
        }

    buf = 0
    buf_kind = "none"
    try:
        # one CHandle = u32 type + u32 index
        if dry_run:
            buf = mo._alloc(pid, 0x1000)
            buf_kind = "virtualalloc"
        else:
            buf = mo._game_malloc(pid, 16)
            buf_kind = "ucrt_malloc"
        mo._write(pid, buf, struct.pack("<II", HANDLE_TYPE, int(army_index)))
        # vector Qii at +0x28
        mo._write(pid, cmd + UNITS_OFF, struct.pack("<Qii", buf, 1, 1))
        # leave sticky as factory default (read for report)
        sticky = b.read(cmd + STICKY_OFF, 1)[0]

        valid = mo._remote(pid, base + ISVALID_RVA, {"rcx": cmd}, wait_ms=5000)
        isvalid = valid["rax"] & 0xFF
        if valid["wait"] != 0 or isvalid != 1:
            return {
                "ok": False,
                "result": "ISVALID_FALSE",
                "army": army_index,
                "isvalid": isvalid,
                "path_before": before,
                "factory_idx": FACTORY_IDX,
                "units_buf_kind": buf_kind,
                "sticky": sticky,
                "call": valid,
            }
        if dry_run:
            return {
                "ok": True,
                "result": "DRY_RUN_VALID",
                "army": army_index,
                "path_before": before,
                "factory_idx": FACTORY_IDX,
                "units_buf_kind": buf_kind,
                "sticky": sticky,
            }

        assert_post_allowed()
        if not allow_post():
            return {"ok": False, "result": "ALLOW_POST_FALSE"}

        sess = mo._u64(b, base + post_abi.G_SESSION)
        posted = mo._remote(
            pid,
            base + post_abi.FN_CMD_QUEUE_POST,
            {"rcx": sess, "rdx": cmd, "r8": 1},
            wait_ms=8000,
        )
        if find_pid() != pid:
            return {
                "ok": False,
                "result": "PROCESS_EXITED",
                "army": army_index,
                "path_before": before,
                "units_buf_kind": buf_kind,
            }
        b = Backend()
        army = resolve_handle(b, HANDLE_TYPE_ARMY, army_index, base)
        after = mo._path(b, base, army) if army else []
        # Cancel evidence: path cleared (was nonempty) or became empty
        cleared = bool(before) and not after
        stopped = (not after) and bool(before)
        return {
            "ok": bool(cleared or posted.get("wait") == 0),
            "result": (
                "PATH_CLEARED"
                if cleared
                else ("POSTED_PATH_STILL_SET" if after else "POSTED_PATH_EMPTY_WAS_EMPTY")
            ),
            "army": army_index,
            "post_rax": posted["rax"] & 0xFF,
            "post_wait": posted["wait"],
            "path_before": before,
            "path_after": after,
            "path_cleared": cleared,
            "factory_idx": FACTORY_IDX,
            "units_buf_kind": buf_kind,
            "sticky": sticky,
            "stub_meta": {
                "wait": posted.get("wait"),
                "stub_leaked_on_timeout": posted.get("stub_leaked_on_timeout"),
                "stub_freed": posted.get("stub_freed"),
                "elapsed_ms": posted.get("elapsed_ms"),
            },
        }
    finally:
        if dry_run and buf:
            try:
                mo._free(pid, buf)
            except Exception:
                pass
