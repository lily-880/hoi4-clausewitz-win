"""Patch calling/move_order.py _remote: never VirtualFreeEx stub on WAIT_TIMEOUT."""
from pathlib import Path

ROOT = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")
p = ROOT / "calling" / "move_order.py"
t = p.read_text(encoding="utf-8")

old = '''def _remote(pid: int, fn: int, regs: dict | None = None, wait_ms: int = 3000) -> dict:
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
        wait = k.WaitForSingleObject(th, int(wait_ms))
        k.CloseHandle(th)
        out = ctypes.c_uint64(0)
        nread = ctypes.c_size_t(0)
        k.ReadProcessMemory(hp, ctypes.c_void_p(slot), ctypes.byref(out), 8, ctypes.byref(nread))
        k.VirtualFreeEx(hp, ctypes.c_void_p(mem), 0, MEM_RELEASE)
        return {"wait": int(wait), "rax": int(out.value)}
    finally:
        k.CloseHandle(hp)
'''

new = '''def _remote(pid: int, fn: int, regs: dict | None = None, wait_ms: int = 3000) -> dict:
    """Call fn in-process via CRT stub.

    CRITICAL: on WAIT_TIMEOUT do NOT VirtualFreeEx the stub — the remote thread may
    still be inside FN_CMD_QUEUE_POST; freeing exec pages crashes hoi4 (2ijx).
    """
    k = _k32()
    access = (
        PROCESS_CREATE_THREAD | PROCESS_QUERY_INFORMATION
        | PROCESS_VM_OPERATION | PROCESS_VM_WRITE | PROCESS_VM_READ
    )
    hp = k.OpenProcess(access, False, pid)
    if not hp:
        raise OSError(ctypes.get_last_error(), "OpenProcess failed")
    mem = 0
    freed = False
    try:
        mem = k.VirtualAllocEx(hp, None, 0x1000, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE)
        if not mem:
            raise OSError(ctypes.get_last_error(), "VirtualAllocEx failed")
        mem = int(mem)
        slot = mem + 0x800
        # zero result slot
        z = (ctypes.c_char * 8)()
        written = ctypes.c_size_t(0)
        k.WriteProcessMemory(hp, ctypes.c_void_p(slot), z, 8, ctypes.byref(written))
        stub = _stub(fn, slot, regs or {})
        buf = (ctypes.c_char * len(stub)).from_buffer_copy(stub)
        if not k.WriteProcessMemory(hp, ctypes.c_void_p(mem), buf, len(stub), ctypes.byref(written)):
            raise OSError(ctypes.get_last_error(), "stub write failed")
        tid = wt.DWORD(0)
        th = k.CreateRemoteThread(hp, None, 0, ctypes.c_void_p(mem), None, 0, ctypes.byref(tid))
        if not th:
            raise OSError(ctypes.get_last_error(), "CreateRemoteThread failed")
        # chunked wait: detect early completion; never free stub while thread alive
        budget = max(1, int(wait_ms))
        slice_ms = 500
        elapsed = 0
        wait = 258  # WAIT_TIMEOUT default
        while elapsed < budget:
            step = min(slice_ms, budget - elapsed)
            wait = k.WaitForSingleObject(th, int(step))
            elapsed += step
            if wait == 0:  # WAIT_OBJECT_0
                break
        still_alive = wait != 0
        out = ctypes.c_uint64(0)
        nread = ctypes.c_size_t(0)
        k.ReadProcessMemory(hp, ctypes.c_void_p(slot), ctypes.byref(out), 8, ctypes.byref(nread))
        k.CloseHandle(th)
        if still_alive:
            # LEAK stub pages intentionally — safer than UAF crash (Phase 2ijy)
            freed = False
        else:
            k.VirtualFreeEx(hp, ctypes.c_void_p(mem), 0, MEM_RELEASE)
            freed = True
            mem = 0
        return {
            "wait": int(wait),
            "rax": int(out.value),
            "wait_ms_budget": budget,
            "elapsed_ms": elapsed,
            "stub_freed": freed,
            "stub_leaked_on_timeout": (not freed),
        }
    except Exception:
        # on error, only free if we know thread never started / already joined — best-effort leak
        raise
    finally:
        k.CloseHandle(hp)
'''

if old not in t:
    raise SystemExit("PATTERN_MISS _remote block")
p.write_text(t.replace(old, new), encoding="utf-8")
# also soften Post wait to 8s chunks totaling 8s — completion often async; path is evidence
t2 = p.read_text(encoding="utf-8")
t2 = t2.replace(
    'posted = _remote(pid, base + post_abi.FN_CMD_QUEUE_POST, {"rcx": sess, "rdx": cmd, "r8": 1}, wait_ms=20000)',
    'posted = _remote(pid, base + post_abi.FN_CMD_QUEUE_POST, {"rcx": sess, "rdx": cmd, "r8": 1}, wait_ms=8000)',
)
# classify ok: path HIT OR (wait==0) — keep path primary; expose stub_leaked
if ' "post_wait": posted["wait"],' in t2 and "stub_freed" not in t2.split("return {", 1)[-1][:500]:
    t2 = t2.replace(
        '''        return {
            "ok": bool(ok or posted.get("wait") == 0),
            "result": "PATH_CONTAINS_DEST" if ok else "POSTED_DEST_NOT_IN_PATH",
            "army": army_index,
            "province": province_id,
            "post_rax": posted["rax"] & 0xFF,
            "post_wait": posted["wait"],
            "path_before": before,
            "path_after": after,
            "factory_idx": FACTORY_IDX,
        }''',
        '''        return {
            "ok": bool(ok),
            "result": "PATH_CONTAINS_DEST" if ok else "POSTED_DEST_NOT_IN_PATH",
            "army": army_index,
            "province": province_id,
            "post_rax": posted["rax"] & 0xFF,
            "post_wait": posted["wait"],
            "post_elapsed_ms": posted.get("elapsed_ms"),
            "stub_freed": posted.get("stub_freed"),
            "stub_leaked_on_timeout": posted.get("stub_leaked_on_timeout"),
            "path_before": before,
            "path_after": after,
            "factory_idx": FACTORY_IDX,
        }''',
    )
p.write_text(t2, encoding="utf-8")
print("patched", p)
