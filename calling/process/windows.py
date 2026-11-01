"""Windows process backend: OpenProcess + ReadProcessMemory.

Phase 1 is READ-ONLY. Writes are disabled unless CLAUSEWITZ_ALLOW_WRITE=1.
Injector (CreateRemoteThread) is a Phase 2 stub.
"""
from __future__ import annotations

import ctypes
import os
from ctypes import wintypes as wt
from typing import List, Optional, Tuple

# Lazily bound so the file can be syntax-checked on Linux packaging hosts.
kernel32 = None
psapi = None

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
TH32CS_SNAPPROCESS = 0x00000002
MAX_PATH = 260
LIST_MODULES_ALL = 0x03
MEM_COMMIT = 0x1000


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD),
        ("cntUsage", wt.DWORD),
        ("th32ProcessID", wt.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID", wt.DWORD),
        ("cntThreads", wt.DWORD),
        ("th32ParentProcessID", wt.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wt.DWORD),
        ("szExeFile", wt.WCHAR * MAX_PATH),
    ]


class MODULEINFO(ctypes.Structure):
    _fields_ = [
        ("lpBaseOfDll", ctypes.c_void_p),
        ("SizeOfImage", wt.DWORD),
        ("EntryPoint", ctypes.c_void_p),
    ]


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wt.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wt.DWORD),
        ("Protect", wt.DWORD),
        ("Type", wt.DWORD),
    ]


class CallError(Exception):
    pass


def _bind():
    global kernel32, psapi
    if kernel32 is not None:
        return
    if os.name != "nt":
        raise RuntimeError("Windows backend requires a Windows host to attach.")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)

    kernel32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wt.HANDLE
    kernel32.Process32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32FirstW.restype = wt.BOOL
    kernel32.Process32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32NextW.restype = wt.BOOL
    kernel32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
    kernel32.OpenProcess.restype = wt.HANDLE
    kernel32.CloseHandle.argtypes = [wt.HANDLE]
    kernel32.CloseHandle.restype = wt.BOOL
    kernel32.ReadProcessMemory.argtypes = [
        wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    kernel32.ReadProcessMemory.restype = wt.BOOL
    kernel32.WriteProcessMemory.argtypes = kernel32.ReadProcessMemory.argtypes
    kernel32.WriteProcessMemory.restype = wt.BOOL
    kernel32.VirtualQueryEx.argtypes = [
        wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
    ]
    kernel32.VirtualQueryEx.restype = ctypes.c_size_t

    psapi.EnumProcessModulesEx.argtypes = [
        wt.HANDLE, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD), wt.DWORD,
    ]
    psapi.EnumProcessModulesEx.restype = wt.BOOL
    psapi.GetModuleFileNameExW.argtypes = [wt.HANDLE, wt.HANDLE, wt.LPWSTR, wt.DWORD]
    psapi.GetModuleFileNameExW.restype = wt.DWORD
    psapi.GetModuleInformation.argtypes = [
        wt.HANDLE, wt.HANDLE, ctypes.POINTER(MODULEINFO), wt.DWORD,
    ]
    psapi.GetModuleInformation.restype = wt.BOOL


def find_pid(name: str = "hoi4.exe") -> Optional[int]:
    """Prefer the alive hoi4 with the largest working set (skip zombies)."""
    _bind()
    name_l = name.lower()
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap is None or int(snap) == -1:
        raise OSError(ctypes.get_last_error(), "CreateToolhelp32Snapshot failed")
    cands: list[int] = []
    try:
        pe = PROCESSENTRY32W()
        pe.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        if not kernel32.Process32FirstW(snap, ctypes.byref(pe)):
            return None
        while True:
            if pe.szExeFile.lower() == name_l:
                cands.append(int(pe.th32ProcessID))
            if not kernel32.Process32NextW(snap, ctypes.byref(pe)):
                break
    finally:
        kernel32.CloseHandle(snap)
    if not cands:
        return None
    if len(cands) == 1:
        return cands[0]
    best_pid = None
    best_ws = -1
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    for pid in cands:
        h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_QUERY_INFORMATION, False, pid)
        if not h:
            continue
        try:
            # GetProcessMemoryInfo via psapi
            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", wt.DWORD),
                    ("PageFaultCount", wt.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]
            pmc = PROCESS_MEMORY_COUNTERS()
            pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
            psapi.GetProcessMemoryInfo.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), wt.DWORD]
            psapi.GetProcessMemoryInfo.restype = wt.BOOL
            if psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb):
                ws = int(pmc.WorkingSetSize)
                if ws > best_ws:
                    best_ws = ws
                    best_pid = pid
        finally:
            kernel32.CloseHandle(h)
    return best_pid or cands[-1]


class Backend:
    def __init__(self, pid: Optional[int] = None, exe_name: str = "hoi4.exe"):
        _bind()
        self.pid = pid or find_pid(exe_name)
        if not self.pid:
            raise RuntimeError("hoi4.exe process not found. Start the game, then retry.")
        access = PROCESS_QUERY_INFORMATION | PROCESS_VM_READ
        if os.environ.get("CLAUSEWITZ_ALLOW_WRITE") == "1":
            access |= PROCESS_VM_WRITE | PROCESS_VM_OPERATION
        self._handle = kernel32.OpenProcess(access, False, self.pid)
        if not self._handle:
            err = ctypes.get_last_error()
            raise OSError(err, "OpenProcess failed (error %s)" % err)
        self.image_base, self.image_size, self.image_path = self._module_info(exe_name)
        self.maps = self._enumerate_regions()

    def close(self):
        if getattr(self, "_handle", None):
            kernel32.CloseHandle(self._handle)
            self._handle = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def _module_info(self, exe_name: str) -> Tuple[int, int, str]:
        h_mods = (ctypes.c_void_p * 1024)()
        needed = wt.DWORD()
        if not psapi.EnumProcessModulesEx(
            self._handle, ctypes.byref(h_mods), ctypes.sizeof(h_mods),
            ctypes.byref(needed), LIST_MODULES_ALL,
        ):
            raise OSError(ctypes.get_last_error(), "EnumProcessModulesEx failed")
        count = needed.value // ctypes.sizeof(ctypes.c_void_p)
        path_buf = ctypes.create_unicode_buffer(MAX_PATH)
        fallback = None
        for i in range(count):
            mod = h_mods[i]
            if not mod:
                continue
            if not psapi.GetModuleFileNameExW(self._handle, mod, path_buf, MAX_PATH):
                continue
            path = path_buf.value
            base_name = os.path.basename(path).lower()
            mi = MODULEINFO()
            if not psapi.GetModuleInformation(
                self._handle, mod, ctypes.byref(mi), ctypes.sizeof(mi)
            ):
                continue
            info = (int(mi.lpBaseOfDll), int(mi.SizeOfImage), path)
            if base_name == exe_name.lower() or base_name == "hoi4.exe":
                return info
            if fallback is None and i == 0:
                fallback = info
        if fallback:
            return fallback
        raise RuntimeError("could not locate hoi4.exe module in process")

    def _enumerate_regions(self) -> List[dict]:
        out = []
        addr = 0
        mbi = MEMORY_BASIC_INFORMATION()
        while addr < 0x00007FFFFFFFFFFF:
            n = kernel32.VirtualQueryEx(
                self._handle, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)
            )
            if not n:
                break
            size = int(mbi.RegionSize)
            base = int(mbi.BaseAddress or 0)
            if int(mbi.State) == MEM_COMMIT:
                prot = int(mbi.Protect)
                out.append(
                    dict(
                        start=base,
                        end=base + size,
                        perms=self._prot_to_perms(prot),
                        fileoff=0,
                        path="",
                        protect=prot,
                        type=int(mbi.Type),
                    )
                )
            next_addr = base + size
            if next_addr <= addr:
                break
            addr = next_addr
        return out

    @staticmethod
    def _prot_to_perms(prot: int) -> str:
        PAGE_EXECUTE_READ = 0x20
        PAGE_EXECUTE_READWRITE = 0x40
        PAGE_EXECUTE_WRITECOPY = 0x80
        PAGE_READONLY = 0x02
        PAGE_READWRITE = 0x04
        PAGE_WRITECOPY = 0x08
        PAGE_EXECUTE = 0x10
        r = w = x = "-"
        if prot & (
            PAGE_READONLY | PAGE_READWRITE | PAGE_WRITECOPY
            | PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY
        ):
            r = "r"
        if prot & (
            PAGE_READWRITE | PAGE_WRITECOPY | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY
        ):
            w = "w"
        if prot & (
            PAGE_EXECUTE | PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY
        ):
            x = "x"
        return r + w + x + "p"

    def read(self, addr: int, size: int) -> bytes:
        buf = (ctypes.c_char * size)()
        nread = ctypes.c_size_t(0)
        ok = kernel32.ReadProcessMemory(
            self._handle, ctypes.c_void_p(addr), buf, size, ctypes.byref(nread)
        )
        if not ok:
            raise OSError(ctypes.get_last_error(), "ReadProcessMemory %#x+%d" % (addr, size))
        return bytes(buf[: nread.value])

    def write(self, addr: int, data: bytes) -> int:
        if os.environ.get("CLAUSEWITZ_ALLOW_WRITE") != "1":
            raise PermissionError(
                "Writes disabled (Phase 1 read-only). Set CLAUSEWITZ_ALLOW_WRITE=1 to enable."
            )
        buf = (ctypes.c_char * len(data)).from_buffer_copy(data)
        written = ctypes.c_size_t(0)
        ok = kernel32.WriteProcessMemory(
            self._handle, ctypes.c_void_p(addr), buf, len(data), ctypes.byref(written)
        )
        if not ok:
            raise OSError(ctypes.get_last_error(), "WriteProcessMemory %#x+%d" % (addr, len(data)))
        return int(written.value)

    def regions(self):
        return self.maps


class Injector:
    def __init__(self, *args, **kwargs):
        raise CallError(
            "Injector/CreateRemoteThread is not implemented yet (Phase 2). "
            "See research/WINDOWS_OFFSETS.md."
        )
