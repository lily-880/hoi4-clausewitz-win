"""One proven Windows post: CSupportAttackCommand (factory idx 3620).

Factory 0x13FB5E0 builds CSupportAttackCommand (size 0x38, VT 0x2A2CB28).
Fields (live RE 2bt/2bu + army_subjects): CHandle unit@+0x28, target_province@+0x30.
IsValid RVA 0x1402270 (rcx=cmd; gates FALSE). No remote heap buffers — inline only
(ucrt_malloc N/A; Move/Cancel still require ucrt for vectors).
Post: FN_CMD_QUEUE_POST. Wartime required for meaningful Execute (ETH day-1 war).
"""
from __future__ import annotations

import struct

import post_abi
from config import assert_post_allowed, allow_post
from handle import HANDLE_TYPE_ARMY, resolve_handle
from process import Backend, find_pid
import move_order as mo

FACTORY_RVA = 0x13FB5E0
FACTORY_IDX = 3620
ISVALID_RVA = 0x1402270
SA_VT = 0x2A2CB28
ARMY_VT = 0x29D6D68
HANDLE_TYPE = 0x33
HANDLE_OFF = 0x28
PROVINCE_OFF = 0x30


def support_attack(army_index: int, target_province_id: int, dry_run: bool = False) -> dict:
    """Post one SupportAttack, or IsValid-only when dry_run."""
    pid = find_pid()
    if not pid:
        return {"ok": False, "result": "NO_PROCESS"}
    b = Backend()
    base = b.image_base
    army = resolve_handle(b, HANDLE_TYPE_ARMY, int(army_index), base)
    if not army or mo._u64(b, army) - base != ARMY_VT:
        return {"ok": False, "result": "ARMY_NOT_FOUND", "army": army_index}
    before = mo._path(b, base, army)

    made = mo._remote(pid, base + FACTORY_RVA, wait_ms=5000)
    cmd = made["rax"]
    if made["wait"] != 0 or cmd < 0x10000:
        return {"ok": False, "result": "FACTORY_FAIL", "call": made}
    if mo._u64(b, cmd) - base != SA_VT:
        return {
            "ok": False,
            "result": "FACTORY_VT_MISMATCH",
            "vt": hex(mo._u64(b, cmd) - base),
            "expect": hex(SA_VT),
        }

    # Inline fields only — no remote buffer / no VirtualAllocEx on live Post path.
    mo._write(pid, cmd + HANDLE_OFF, struct.pack("<II", HANDLE_TYPE, int(army_index)))
    mo._write(pid, cmd + PROVINCE_OFF, struct.pack("<I", int(target_province_id)))

    valid = mo._remote(pid, base + ISVALID_RVA, {"rcx": cmd}, wait_ms=5000)
    # SA IsValid (vt+0x48 / 0x1402270) returns a pointer/object on success (observed
    # non-zero high rax), not necessarily AL==1 like Cancel/Move action IsValid.
    rax = int(valid.get("rax") or 0)
    isvalid_al = rax & 0xFF
    isvalid_ok = valid.get("wait") == 0 and (isvalid_al == 1 or rax > 0x10000)
    if not isvalid_ok:
        return {
            "ok": False,
            "result": "ISVALID_FALSE",
            "army": army_index,
            "province": target_province_id,
            "isvalid": isvalid_al,
            "isvalid_rax": rax,
            "path_before": before,
            "factory_idx": FACTORY_IDX,
            "buf_kind": "inline_none",
            "call": valid,
        }
    if dry_run:
        return {
            "ok": True,
            "result": "DRY_RUN_VALID",
            "army": army_index,
            "province": target_province_id,
            "path_before": before,
            "factory_idx": FACTORY_IDX,
            "buf_kind": "inline_none",
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
            "province": target_province_id,
            "path_before": before,
            "buf_kind": "inline_none",
        }
    b = Backend()
    army2 = resolve_handle(b, HANDLE_TYPE_ARMY, int(army_index), base)
    after = mo._path(b, base, army2) if army2 else []
    posted_ok = posted.get("wait") == 0 and (posted.get("rax", 0) & 0xFF) == 1
    return {
        "ok": bool(posted_ok),
        "result": "ATTACK_POSTED_STABLE" if posted_ok else "ATTACK_POST_UNCERTAIN",
        "army": army_index,
        "province": target_province_id,
        "post_rax": posted["rax"] & 0xFF,
        "post_wait": posted["wait"],
        "path_before": before,
        "path_after": after,
        "factory_idx": FACTORY_IDX,
        "buf_kind": "inline_none",
        "stub_meta": {
            "wait": posted.get("wait"),
            "stub_leaked_on_timeout": posted.get("stub_leaked_on_timeout"),
            "stub_freed": posted.get("stub_freed"),
            "elapsed_ms": posted.get("elapsed_ms"),
        },
    }
