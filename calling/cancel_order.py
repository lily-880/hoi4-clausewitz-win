"""One proven Windows post: CCancelMovementCommand (factory idx 1415).

Factory 0x13FACE0 builds CCancelMovementCommand. Units vector at +0x28 (Qii:
ptr/size/cap) holds CHandle{type=0x33,index}[]. Live units buffer MUST be
ucrtbase!malloc (same heap lesson as Move 2ijy/2ijz). IsValid RVA 0x13FED40
(rcx=cmd). Post: FN_CMD_QUEUE_POST.

Phase 2ikb: multi-army Cancel via army_indices list.
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
HANDLE_TYPE = 0x33
UNITS_OFF = 0x28
STICKY_OFF = 0x40


def _as_indices(army_index=None, army_indices=None) -> list[int]:
    if army_indices is not None:
        out = [int(x) for x in army_indices]
    elif army_index is not None:
        out = [int(army_index)]
    else:
        out = []
    if not out:
        raise ValueError("army_index or army_indices required")
    return out


def cancel_movement(army_index: int | None = None, dry_run: bool = False, army_indices=None) -> dict:
    """Post CancelMovement for one or more armies, or IsValid-only when dry_run."""
    indices = _as_indices(army_index, army_indices)
    pid = find_pid()
    if not pid:
        return {"ok": False, "result": "NO_PROCESS"}
    b = Backend()
    base = b.image_base

    resolved = []
    path_before = {}
    for idx in indices:
        army = resolve_handle(b, HANDLE_TYPE_ARMY, idx, base)
        if not army or mo._u64(b, army) - base != ARMY_VT:
            return {"ok": False, "result": "ARMY_NOT_FOUND", "army": idx, "armies": indices}
        resolved.append((idx, army))
        path_before[idx] = mo._path(b, base, army)

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

    n = len(indices)
    buf = 0
    buf_kind = "none"
    try:
        nbytes = max(16, n * 8)
        if dry_run:
            buf = mo._alloc(pid, max(0x1000, nbytes))
            buf_kind = "virtualalloc"
        else:
            buf = mo._game_malloc(pid, nbytes)
            buf_kind = "ucrt_malloc"
        blob = b"".join(struct.pack("<II", HANDLE_TYPE, int(idx)) for idx in indices)
        mo._write(pid, buf, blob)
        mo._write(pid, cmd + UNITS_OFF, struct.pack("<Qii", buf, n, n))
        sticky = b.read(cmd + STICKY_OFF, 1)[0]

        valid = mo._remote(pid, base + ISVALID_RVA, {"rcx": cmd}, wait_ms=5000)
        isvalid = valid["rax"] & 0xFF
        if valid["wait"] != 0 or isvalid != 1:
            return {
                "ok": False,
                "result": "ISVALID_FALSE",
                "armies": indices,
                "isvalid": isvalid,
                "path_before": path_before,
                "factory_idx": FACTORY_IDX,
                "units_buf_kind": buf_kind,
                "units_count": n,
                "sticky": sticky,
                "call": valid,
            }
        if dry_run:
            return {
                "ok": True,
                "result": "DRY_RUN_VALID",
                "armies": indices,
                "path_before": path_before,
                "factory_idx": FACTORY_IDX,
                "units_buf_kind": buf_kind,
                "units_count": n,
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
                "armies": indices,
                "path_before": path_before,
                "units_buf_kind": buf_kind,
            }
        b = Backend()
        path_after = {}
        cleared_map = {}
        for idx, _ in resolved:
            army = resolve_handle(b, HANDLE_TYPE_ARMY, idx, base)
            after = mo._path(b, base, army) if army else []
            path_after[idx] = after
            cleared_map[idx] = bool(path_before.get(idx)) and not after
        all_cleared = all(cleared_map.values()) and any(path_before.values())
        any_cleared = any(cleared_map.values())
        return {
            "ok": bool(all_cleared or (any_cleared and posted.get("wait") == 0)),
            "result": (
                "PATH_CLEARED_ALL"
                if all_cleared
                else ("PATH_CLEARED_PARTIAL" if any_cleared else "POSTED_PATH_STILL_SET")
            ),
            "armies": indices,
            "post_rax": posted["rax"] & 0xFF,
            "post_wait": posted["wait"],
            "path_before": path_before,
            "path_after": path_after,
            "path_cleared_map": cleared_map,
            "path_cleared": all_cleared,
            "factory_idx": FACTORY_IDX,
            "units_buf_kind": buf_kind,
            "units_count": n,
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
