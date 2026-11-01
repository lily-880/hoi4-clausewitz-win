"""One proven Windows post: ordinary CMoveCommand for one army.

Factory 0x13FB000 (idx 1402) builds CMoveCommand + CUnitMoveAction embed.
Province destinations use a remote VirtualAllocEx u32 array (size=1).
IsValid: action RVA 0x12C2CA0 (rcx=cmd+0x28). Post: FN_CMD_QUEUE_POST.
"""
from __future__ import annotations

import ctypes
import struct
from ctypes import wintypes as wt

import post_abi
from config import assert_post_allowed, allow_post
from handle import HANDLE_TYPE_ARMY, resolve_handle
from process import Backend, find_pid

FACTORY_RVA = 0x13FB000
FACTORY_IDX = 1402
ACTION_ISVALID_RVA = 0x12C2CA0
MOVE_VT = 0x2A2C790
ACTION_VT = 0x2A1F648
ARMY_VT = 0x29D6D68
PATH_OFF = 0x200
HANDLE_TYPE = 0x33

PROCESS_CREATE_THREAD = 0x0002
PROCESS_VM_OPERATION = 0x0008
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_ALL = 0x1F0FFF
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
MEM_RELEASE = 0x8000
PAGE_EXECUTE_READWRITE = 0x40


def _stub(fn: int, slot: int, regs: dict) -> bytes:
    code = bytearray(b"\x48\x83\xEC\x28")
    if "rcx" in regs:
        code += b"\x48\xB9" + struct.pack("<Q", regs["rcx"])
    if "rdx" in regs:
        code += b"\x48\xBA" + struct.pack("<Q", regs["rdx"])
    if "r8" in regs:
        code += b"\x49\xB8" + struct.pack("<Q", regs["r8"])
    code += b"\x48\xB8" + struct.pack("<Q", fn)
    code += b"\xFF\xD0"
    code += b"\x48\xB9" + struct.pack("<Q", slot)
    code += b"\x48\x89\x01\x31\xC0\x48\x83\xC4\x28\xC3"
    return bytes(code)


def _k32():
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.VirtualAllocEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wt.DWORD, wt.DWORD]
    k.VirtualAllocEx.restype = ctypes.c_void_p
    k.VirtualFreeEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wt.DWORD]
    k.VirtualFreeEx.restype = wt.BOOL
    k.WriteProcessMemory.argtypes = [
        wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)
    ]
    k.WriteProcessMemory.restype = wt.BOOL
    k.ReadProcessMemory.argtypes = [
        wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)
    ]
    k.ReadProcessMemory.restype = wt.BOOL
    k.CreateRemoteThread.argtypes = [
        wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD)
    ]
    k.CreateRemoteThread.restype = wt.HANDLE
    k.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
    k.WaitForSingleObject.restype = wt.DWORD
    return k


def _remote(pid: int, fn: int, regs: dict | None = None) -> dict:
    k = _k32()
    access = (
        PROCESS_CREATE_THREAD | PROCESS_QUERY_INFORMATION
        | PROCESS_VM_OPERATION | PROCESS_VM_WRITE | PROCESS_VM_READ
    )
    hp = k.OpenProcess(access, False, pid)
    if not hp:
        raise OSError(ctypes.get_last_error(), "OpenProcess failed")
    try:
        mem = k.VirtualAllocEx(hp, None, 0x1000, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE)
        if not mem:
            raise OSError(ctypes.get_last_error(), "VirtualAllocEx failed")
        mem = int(mem)
        slot = mem + 0x800
        stub = _stub(fn, slot, regs or {})
        written = ctypes.c_size_t(0)
        buf = (ctypes.c_char * len(stub)).from_buffer_copy(stub)
        if not k.WriteProcessMemory(hp, ctypes.c_void_p(mem), buf, len(stub), ctypes.byref(written)):
            raise OSError(ctypes.get_last_error(), "stub write failed")
        tid = wt.DWORD(0)
        th = k.CreateRemoteThread(hp, None, 0, ctypes.c_void_p(mem), None, 0, ctypes.byref(tid))
        if not th:
            raise OSError(ctypes.get_last_error(), "CreateRemoteThread failed")
        wait = k.WaitForSingleObject(th, 3000)
        k.CloseHandle(th)
        out = ctypes.c_uint64(0)
        nread = ctypes.c_size_t(0)
        k.ReadProcessMemory(hp, ctypes.c_void_p(slot), ctypes.byref(out), 8, ctypes.byref(nread))
        k.VirtualFreeEx(hp, ctypes.c_void_p(mem), 0, MEM_RELEASE)
        return {"wait": int(wait), "rax": int(out.value)}
    finally:
        k.CloseHandle(hp)


def _write(pid: int, addr: int, data: bytes) -> None:
    k = _k32()
    hp = k.OpenProcess(PROCESS_ALL, False, pid)
    if not hp:
        raise OSError(ctypes.get_last_error(), "OpenProcess write failed")
    try:
        written = ctypes.c_size_t(0)
        buf = (ctypes.c_char * len(data)).from_buffer_copy(data)
        if not k.WriteProcessMemory(hp, ctypes.c_void_p(addr), buf, len(data), ctypes.byref(written)):
            raise OSError(ctypes.get_last_error(), "field write failed")
    finally:
        k.CloseHandle(hp)


def _alloc(pid: int, n: int = 0x1000) -> int:
    k = _k32()
    hp = k.OpenProcess(PROCESS_ALL, False, pid)
    if not hp:
        raise OSError(ctypes.get_last_error(), "OpenProcess alloc failed")
    try:
        mem = k.VirtualAllocEx(hp, None, n, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE)
        if not mem:
            raise OSError(ctypes.get_last_error(), "VirtualAllocEx buffer failed")
        return int(mem)
    finally:
        k.CloseHandle(hp)


def _free(pid: int, mem: int) -> None:
    if not mem:
        return
    k = _k32()
    hp = k.OpenProcess(PROCESS_ALL, False, pid)
    if not hp:
        return
    try:
        k.VirtualFreeEx(hp, ctypes.c_void_p(mem), 0, MEM_RELEASE)
    finally:
        k.CloseHandle(hp)


def _u64(b, addr: int) -> int:
    return struct.unpack("<Q", b.read(addr, 8))[0]


def _path(b, base: int, army: int) -> list[int]:
    data, _cap, size = struct.unpack("<Qii", b.read(army + PATH_OFF, 16))
    if data < 0x10000 or not (0 < size <= 24) or base <= data < base + 0x4000000:
        return []
    raw = b.read(data, size * 4)
    vals = list(struct.unpack("<" + "I" * size, raw))
    if not all(1 <= v <= 20000 for v in vals):
        return []
    return vals


def move(army_index: int, province_id: int, dry_run: bool = False) -> dict:
    """Post one ordinary Move, or only check IsValid when dry_run is set."""
    pid = find_pid()
    if not pid:
        return {"ok": False, "result": "NO_PROCESS"}
    b = Backend()
    base = b.image_base
    army = resolve_handle(b, HANDLE_TYPE_ARMY, army_index, base)
    if not army or _u64(b, army) - base != ARMY_VT:
        return {"ok": False, "result": "ARMY_NOT_FOUND", "army": army_index}
    before = _path(b, base, army)
    made = _remote(pid, base + FACTORY_RVA)
    cmd = made["rax"]
    if made["wait"] != 0 or cmd < 0x10000:
        return {"ok": False, "result": "FACTORY_FAIL", "call": made}
    if _u64(b, cmd) - base != MOVE_VT or _u64(b, cmd + 0x28) - base != ACTION_VT:
        return {"ok": False, "result": "FACTORY_VT_MISMATCH"}

    buf = 0
    try:
        buf = _alloc(pid, 0x1000)
        _write(pid, buf, struct.pack("<I", int(province_id)))
        emb = cmd + 0x28
        _write(pid, emb + 0x10, struct.pack("<II", HANDLE_TYPE, int(army_index)))
        _write(pid, emb + 0x18, struct.pack("<Qii", buf, 1, 1))
        _write(pid, emb + 0x50, bytes([1, 0, 0, 0, 0, 0, 0, 0]))
        _write(pid, emb + 0x58, struct.pack("<I", 2))

        valid = _remote(pid, base + ACTION_ISVALID_RVA, {"rcx": emb})
        isvalid = valid["rax"] & 0xFF
        if valid["wait"] != 0 or isvalid != 1:
            return {
                "ok": False,
                "result": "ISVALID_FALSE",
                "army": army_index,
                "province": province_id,
                "isvalid": isvalid,
                "path_before": before,
                "factory_idx": FACTORY_IDX,
            }
        if dry_run:
            return {
                "ok": True,
                "result": "DRY_RUN_VALID",
                "army": army_index,
                "province": province_id,
                "path_before": before,
                "factory_idx": FACTORY_IDX,
            }

        assert_post_allowed()
        if not allow_post():
            return {"ok": False, "result": "ALLOW_POST_FALSE"}

        sess = _u64(b, base + post_abi.G_SESSION)
        posted = _remote(pid, base + post_abi.FN_CMD_QUEUE_POST, {"rcx": sess, "rdx": cmd, "r8": 1})
        if find_pid() != pid:
            return {"ok": False, "result": "PROCESS_EXITED"}
        b = Backend()
        army = resolve_handle(b, HANDLE_TYPE_ARMY, army_index, base)
        after = _path(b, base, army) if army else []
        ok = province_id in after
        return {
            "ok": bool(ok or posted.get("wait") == 0),
            "result": "PATH_CONTAINS_DEST" if ok else "POSTED_DEST_NOT_IN_PATH",
            "army": army_index,
            "province": province_id,
            "post_rax": posted["rax"] & 0xFF,
            "post_wait": posted["wait"],
            "path_before": before,
            "path_after": after,
            "factory_idx": FACTORY_IDX,
        }
    finally:
        # dry_run: free; live Post: intentionally leak 4KB so queued cmd cannot UAF province_arr
        if dry_run:
            try:
                _free(pid, buf)
            except Exception:
                pass
