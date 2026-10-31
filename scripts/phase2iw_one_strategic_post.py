#!/usr/bin/env python3
"""Phase 2iw: ONE strategic redeploy, issued by the agent (no user click).

Synthetic input is already proven dead on this DX11 build, and the desktop
driver is unavailable. The user told the agent to operate the game itself.

This slice calls the live Strategic factory (no-arg, returns a 0x50 object),
fills the proven army/province fields, then calls FN_CMD_QUEUE_POST once.
It does not change speed, does not post HourlyTick/speed commands, and does
not open the global allow_post gate.
"""
from __future__ import annotations

import ctypes
import json
import struct
import sys
import time
from ctypes import wintypes as wt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

import post_abi
from handle import HANDLE_TYPE_ARMY, resolve_handle
from process import Backend, find_pid
from province import resolve_province

OUT = ROOT / "reports" / "phase2iw_one_strategic_post.json"
SUMMARY = ROOT / "reports" / "phase2iw_summary.json"

FACTORY_RVA = 0x13FB580
STRATEGIC_VT = 0x2A2D818
ACTION_VT = 0x2A1F7E8
ARMY_INDEX = 1042
DEST_FROM_ARMY = 461  # live sister army; its current province is the destination
CA_PROVINCE = 0x28
HANDLE_TYPE = 0x33

PROCESS_CREATE_THREAD = 0x0002
PROCESS_VM_OPERATION = 0x0008
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_QUERY_INFORMATION = 0x0400
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
MEM_RELEASE = 0x8000
PAGE_EXECUTE_READWRITE = 0x40
WAIT_OBJECT_0 = 0


def u64(b, a):
    return struct.unpack("<Q", b.read(a, 8))[0]


def u32(b, a):
    return struct.unpack("<I", b.read(a, 4))[0]


def i32(b, a):
    return struct.unpack("<i", b.read(a, 4))[0]


def counters(b, base, sess, server):
    return {
        "drain": u32(b, sess + post_abi.CSession_DRAIN_COUNTER),
        "exec": u32(b, sess + post_abi.CSession_EXEC_COUNTER),
        "executing": u32(b, sess + post_abi.CSession_EXECUTING_FLAG),
        "pending": u32(b, server + post_abi.CDummyServer_PENDING + 0x10),
        "stage": u32(b, sess + post_abi.CSession_STAGE_COUNT),
        "seq": u32(b, server + 0xD0),
        "gate725": b.read(sess + 0x725, 1)[0],
    }


def army_snap(b, base, idx):
    army = resolve_handle(b, HANDLE_TYPE_ARMY, idx, base)
    if not army:
        return {"index": idx, "alive": False}
    vt = u64(b, army) - base
    prov = u32(b, army + CA_PROVINCE)
    return {"index": idx, "alive": True, "vt_rva": hex(vt), "province": prov, "ptr": hex(army)}


def build_call_stub(fn: int, slot: int, regs: dict) -> bytes:
    """x64 stub. Entry RSP is 8 mod 16. Optional rcx/rdx/r8 immediates, then call fn, store rax."""
    code = bytearray()
    code += b"\x48\x83\xEC\x28"  # sub rsp, 0x28
    if "rcx" in regs:
        code += b"\x48\xB9" + struct.pack("<Q", regs["rcx"])
    if "rdx" in regs:
        code += b"\x48\xBA" + struct.pack("<Q", regs["rdx"])
    if "r8" in regs:
        code += b"\x49\xB8" + struct.pack("<Q", regs["r8"])
    code += b"\x48\xB8" + struct.pack("<Q", fn)  # mov rax, fn
    code += b"\xFF\xD0"  # call rax
    code += b"\x48\xB9" + struct.pack("<Q", slot)  # mov rcx, slot
    code += b"\x48\x89\x01"  # mov [rcx], rax
    code += b"\x31\xC0"  # xor eax, eax
    code += b"\x48\x83\xC4\x28"
    code += b"\xC3"
    return bytes(code)


def remote_call(pid: int, fn: int, regs: dict | None = None, timeout_ms: int = 3000):
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    access = (
        PROCESS_CREATE_THREAD
        | PROCESS_QUERY_INFORMATION
        | PROCESS_VM_OPERATION
        | PROCESS_VM_WRITE
        | PROCESS_VM_READ
    )
    hp = k.OpenProcess(access, False, pid)
    if not hp:
        raise OSError(ctypes.get_last_error(), "OpenProcess for remote call failed")
    try:
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

        mem = k.VirtualAllocEx(hp, None, 0x1000, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE)
        if not mem:
            raise OSError(ctypes.get_last_error(), "VirtualAllocEx failed")
        mem = int(mem)
        slot = mem + 0x800
        stub = build_call_stub(fn, slot, regs or {})
        written = ctypes.c_size_t(0)
        buf = (ctypes.c_char * len(stub)).from_buffer_copy(stub)
        if not k.WriteProcessMemory(hp, ctypes.c_void_p(mem), buf, len(stub), ctypes.byref(written)):
            raise OSError(ctypes.get_last_error(), "WriteProcessMemory stub failed")
        tid = wt.DWORD(0)
        th = k.CreateRemoteThread(hp, None, 0, ctypes.c_void_p(mem), None, 0, ctypes.byref(tid))
        if not th:
            raise OSError(ctypes.get_last_error(), "CreateRemoteThread failed")
        wait = k.WaitForSingleObject(th, timeout_ms)
        k.CloseHandle(th)
        out = ctypes.c_uint64(0)
        nread = ctypes.c_size_t(0)
        if not k.ReadProcessMemory(hp, ctypes.c_void_p(slot), ctypes.byref(out), 8, ctypes.byref(nread)):
            raise OSError(ctypes.get_last_error(), "ReadProcessMemory slot failed")
        k.VirtualFreeEx(hp, ctypes.c_void_p(mem), 0, MEM_RELEASE)
        return {"wait": int(wait), "rax": int(out.value), "ok": wait == WAIT_OBJECT_0}
    finally:
        k.CloseHandle(hp)


def write_bytes(pid: int, addr: int, data: bytes) -> None:
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    access = PROCESS_VM_OPERATION | PROCESS_VM_WRITE | PROCESS_VM_READ | PROCESS_QUERY_INFORMATION
    hp = k.OpenProcess(access, False, pid)
    if not hp:
        raise OSError(ctypes.get_last_error(), "OpenProcess write failed")
    try:
        k.WriteProcessMemory.argtypes = [
            wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)
        ]
        k.WriteProcessMemory.restype = wt.BOOL
        written = ctypes.c_size_t(0)
        buf = (ctypes.c_char * len(data)).from_buffer_copy(data)
        if not k.WriteProcessMemory(hp, ctypes.c_void_p(addr), buf, len(data), ctypes.byref(written)):
            raise OSError(ctypes.get_last_error(), "WriteProcessMemory fields failed")
    finally:
        k.CloseHandle(hp)


def main():
    pid = find_pid()
    if not pid:
        print(json.dumps({"result": "NO_PROCESS"}))
        return 1
    b = Backend()
    base = b.image_base
    sess = u64(b, base + post_abi.G_SESSION)
    server = u64(b, sess + post_abi.CSession_SERVER)
    svt = u64(b, server) - base
    before = counters(b, base, sess, server)
    src = army_snap(b, base, ARMY_INDEX)
    anchor = army_snap(b, base, DEST_FROM_ARMY)
    gs = u64(b, base + post_abi.G_GAMESTATE)
    prov_n = u32(b, gs + 0x2BC)
    report = {
        "phase": "2iw",
        "pid": pid,
        "allow_post_global": False,
        "one_shot": "strategic redeploy only",
        "before": before,
        "server_vt_rva": hex(svt),
        "src": src,
        "anchor": anchor,
        "province_count": prov_n,
    }
    if svt != post_abi.CDummyServer_VT or not src.get("alive") or not anchor.get("alive"):
        report["result"] = "PRECONDITION_FAIL"
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 2
    dest = int(anchor["province"])
    if not (1 <= dest < prov_n) or resolve_province(b, dest, base, gs) is None:
        report["result"] = "DEST_PROVINCE_INVALID"
        report["dest"] = dest
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 2
    if before["executing"] != 0:
        report["result"] = "SESSION_EXECUTING_SKIP"
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 2

    factory = base + FACTORY_RVA
    made = remote_call(pid, factory)
    report["factory_call"] = {k: (hex(v) if k == "rax" else v) for k, v in made.items()}
    cmd = made["rax"]
    if made["wait"] != 0 or cmd < 0x10000:
        report["result"] = "FACTORY_FAIL"
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 3
    # Re-open read backend; remote call used its own handle.
    b = Backend()
    vt = u64(b, cmd) - base
    avt = u64(b, cmd + 0x28) - base
    report["object"] = {"cmd": hex(cmd), "vt_rva": hex(vt), "action_vt_rva": hex(avt)}
    if vt != STRATEGIC_VT or avt != ACTION_VT:
        report["result"] = "FACTORY_VT_MISMATCH"
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 3

    fields = struct.pack("<IIIiI", HANDLE_TYPE, ARMY_INDEX, dest, 1, 2)
    write_bytes(pid, cmd + 0x38, fields)
    b = Backend()
    report["wrote"] = {
        "army_type": HANDLE_TYPE,
        "army_index": ARMY_INDEX,
        "from_province": src["province"],
        "dest_province": dest,
        "clear": 1,
        "move_priority": 2,
        "echo": b.read(cmd + 0x38, 20).hex(),
    }
    posted = remote_call(
        pid,
        base + post_abi.FN_CMD_QUEUE_POST,
        {"rcx": sess, "rdx": cmd, "r8": 1},
    )
    report["post_call"] = {k: (hex(v) if k == "rax" else v) for k, v in posted.items()}
    time.sleep(0.4)
    b = Backend()
    if find_pid() != pid:
        report["result"] = "PROCESS_EXITED_AFTER_POST"
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 4
    after = counters(b, base, sess, server)
    report["after"] = after
    report["src_after"] = army_snap(b, base, ARMY_INDEX)
    report["delta"] = {
        "drain": after["drain"] - before["drain"],
        "exec": after["exec"] - before["exec"],
        "seq": after["seq"] - before["seq"],
    }
    if after["seq"] != before["seq"] and report["src_after"].get("province") == src.get("province"):
        report["result"] = "POST_ACCEPTED_NO_VISIBLE_MOVE"
    elif after["drain"] != before["drain"] or after["exec"] != before["exec"] or after["seq"] != before["seq"]:
        report["result"] = "POST_OBSERVED"
    else:
        report["result"] = "POST_RETURNED_NO_COUNTER_MOVE"
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    SUMMARY.write_text(
        json.dumps(
            {
                "phase": "2iw",
                "result": report["result"],
                "from": src.get("province"),
                "dest": dest,
                "army": ARMY_INDEX,
                "delta": report["delta"],
                "post_wait": posted["wait"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({k: report[k] for k in ("result", "wrote", "post_call", "before", "after", "delta", "src_after")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
