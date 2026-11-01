#!/usr/bin/env python3
"""Patch move_order.py: allocate province_arr via ucrtbase!malloc (game-compatible heap).

2ijy finding: stub-leak alone insufficient; exit 0xC0000374 STATUS_HEAP_CORRUPTION
~8s after PATH_CONTAINS_DEST — game vector dtor HeapFree/free on VirtualAllocEx ptr.
Strategic embeds inline (no external vector) → stable. Move must use CRT malloc.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
# when run on PC, script lives in scripts/
candidates = [
    Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win\calling\move_order.py"),
]
path = None
for c in candidates:
    if c.is_file():
        path = c
        break
if path is None:
    # relative from scripts/
    path = Path(__file__).resolve().parents[1] / "calling" / "move_order.py"

text = path.read_text(encoding="utf-8")

MARKER = "def _game_malloc(pid: int, n: int = 16) -> int:"
if MARKER in text:
    print("already patched", path)
    raise SystemExit(0)

# Insert game malloc helpers after _free
HELPERS = '''

def _remote_module_base(pid: int, want: tuple[str, ...]) -> int:
    """Return base of first matching module name (case-insensitive substring)."""
    import ctypes
    from ctypes import wintypes as wt

    k = ctypes.WinDLL("kernel32", use_last_error=True)
    TH32CS_SNAPMODULE = 0x00000008
    TH32CS_SNAPMODULE32 = 0x00000010
    class MODULEENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wt.DWORD),
            ("th32ModuleID", wt.DWORD),
            ("th32ProcessID", wt.DWORD),
            ("GlblcntUsage", wt.DWORD),
            ("ProccntUsage", wt.DWORD),
            ("modBaseAddr", ctypes.POINTER(ctypes.c_byte)),
            ("modBaseSize", wt.DWORD),
            ("hModule", wt.HMODULE),
            ("szModule", ctypes.c_wchar * 256),
            ("szExePath", ctypes.c_wchar * 260),
        ]
    k.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
    k.CreateToolhelp32Snapshot.restype = wt.HANDLE
    k.Module32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
    k.Module32FirstW.restype = wt.BOOL
    k.Module32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
    k.Module32NextW.restype = wt.BOOL
    snap = k.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    if not snap or snap == wt.HANDLE(-1).value:
        raise OSError(ctypes.get_last_error(), "CreateToolhelp32Snapshot modules failed")
    try:
        me = MODULEENTRY32W()
        me.dwSize = ctypes.sizeof(MODULEENTRY32W)
        if not k.Module32FirstW(snap, ctypes.byref(me)):
            raise OSError(ctypes.get_last_error(), "Module32FirstW failed")
        want_l = tuple(w.lower() for w in want)
        while True:
            name = (me.szModule or "").lower()
            if any(w in name for w in want_l):
                return ctypes.cast(me.modBaseAddr, ctypes.c_void_p).value or 0
            if not k.Module32NextW(snap, ctypes.byref(me)):
                break
    finally:
        k.CloseHandle(snap)
    raise OSError(0, f"module not found: {want}")


def _local_export_rva(dll_file: str, export: str) -> int:
    import ctypes
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.LoadLibraryW.argtypes = [wt_wchar := ctypes.c_wchar_p]
    k.LoadLibraryW.restype = ctypes.c_void_p
    k.GetProcAddress.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    k.GetProcAddress.restype = ctypes.c_void_p
    h = k.LoadLibraryW(dll_file)
    if not h:
        raise OSError(ctypes.get_last_error(), f"LoadLibraryW {dll_file}")
    p = k.GetProcAddress(h, export.encode("ascii"))
    if not p:
        raise OSError(ctypes.get_last_error(), f"GetProcAddress {export}")
    return int(p) - int(h)


def _resolve_ucrt_malloc(pid: int) -> int:
    """ucrtbase!malloc in the remote process (same RVA as local ucrtbase)."""
    remote = _remote_module_base(pid, ("ucrtbase.dll", "ucrtbase"))
    rva = _local_export_rva("ucrtbase.dll", "malloc")
    return int(remote) + int(rva)


def _game_malloc(pid: int, n: int = 16) -> int:
    """Allocate n bytes on the game CRT heap (safe for std::vector free)."""
    fn = _resolve_ucrt_malloc(pid)
    got = _remote(pid, fn, {"rcx": int(n)}, wait_ms=3000)
    if got.get("wait") != 0 or int(got.get("rax") or 0) < 0x10000:
        raise OSError(0, f"game malloc failed: {got}")
    return int(got["rax"])

'''

# Fix the broken wt_wchar inline - rewrite helper cleanly
HELPERS = '''

def _remote_module_base(pid: int, want: tuple[str, ...]) -> int:
    """Return base of first matching module name (case-insensitive substring)."""
    import ctypes
    from ctypes import wintypes as wt

    k = ctypes.WinDLL("kernel32", use_last_error=True)
    TH32CS_SNAPMODULE = 0x00000008
    TH32CS_SNAPMODULE32 = 0x00000010

    class MODULEENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wt.DWORD),
            ("th32ModuleID", wt.DWORD),
            ("th32ProcessID", wt.DWORD),
            ("GlblcntUsage", wt.DWORD),
            ("ProccntUsage", wt.DWORD),
            ("modBaseAddr", ctypes.POINTER(ctypes.c_byte)),
            ("modBaseSize", wt.DWORD),
            ("hModule", wt.HMODULE),
            ("szModule", ctypes.c_wchar * 256),
            ("szExePath", ctypes.c_wchar * 260),
        ]

    k.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
    k.CreateToolhelp32Snapshot.restype = wt.HANDLE
    k.Module32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
    k.Module32FirstW.restype = wt.BOOL
    k.Module32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
    k.Module32NextW.restype = wt.BOOL
    snap = k.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    if not snap or int(snap) == -1:
        raise OSError(ctypes.get_last_error(), "CreateToolhelp32Snapshot modules failed")
    try:
        me = MODULEENTRY32W()
        me.dwSize = ctypes.sizeof(MODULEENTRY32W)
        if not k.Module32FirstW(snap, ctypes.byref(me)):
            raise OSError(ctypes.get_last_error(), "Module32FirstW failed")
        want_l = tuple(w.lower() for w in want)
        while True:
            name = (me.szModule or "").lower()
            if any(w in name for w in want_l):
                return int(ctypes.cast(me.modBaseAddr, ctypes.c_void_p).value or 0)
            if not k.Module32NextW(snap, ctypes.byref(me)):
                break
    finally:
        k.CloseHandle(snap)
    raise OSError(0, f"module not found: {want}")


def _local_export_rva(dll_file: str, export: str) -> int:
    import ctypes

    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.LoadLibraryW.argtypes = [ctypes.c_wchar_p]
    k.LoadLibraryW.restype = ctypes.c_void_p
    k.GetProcAddress.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    k.GetProcAddress.restype = ctypes.c_void_p
    h = k.LoadLibraryW(dll_file)
    if not h:
        raise OSError(ctypes.get_last_error(), f"LoadLibraryW {dll_file}")
    p = k.GetProcAddress(h, export.encode("ascii"))
    if not p:
        raise OSError(ctypes.get_last_error(), f"GetProcAddress {export}")
    return int(p) - int(h)


def _resolve_ucrt_malloc(pid: int) -> int:
    """ucrtbase!malloc in the remote process (same RVA as local ucrtbase)."""
    remote = _remote_module_base(pid, ("ucrtbase.dll", "ucrtbase"))
    rva = _local_export_rva("ucrtbase.dll", "malloc")
    return int(remote) + int(rva)


def _game_malloc(pid: int, n: int = 16) -> int:
    """Allocate n bytes on the game CRT heap (safe for std::vector free)."""
    fn = _resolve_ucrt_malloc(pid)
    got = _remote(pid, fn, {"rcx": int(n)}, wait_ms=3000)
    if got.get("wait") != 0 or int(got.get("rax") or 0) < 0x10000:
        raise OSError(0, f"game malloc failed: {got}")
    return int(got["rax"])

'''

anchor = "def _u64(b, addr: int) -> int:"
if anchor not in text:
    raise SystemExit("anchor _u64 missing")
if "_game_malloc" not in text:
    text = text.replace(anchor, HELPERS + "\n" + anchor, 1)

# Replace province alloc in move(): use game malloc for live Post; VirtualAlloc for dry_run OK
old = """    buf = 0
    try:
        buf = _alloc(pid, 0x1000)
        _write(pid, buf, struct.pack("<I", int(province_id)))"""

new = """    buf = 0
    buf_kind = "none"
    try:
        # Live Post: province_arr MUST be CRT-heap (ucrt malloc). VirtualAllocEx causes
        # STATUS_HEAP_CORRUPTION (0xC0000374) when the command vector dtor frees it (2ijy).
        if dry_run:
            buf = _alloc(pid, 0x1000)
            buf_kind = "virtualalloc"
        else:
            buf = _game_malloc(pid, 16)
            buf_kind = "ucrt_malloc"
        _write(pid, buf, struct.pack("<I", int(province_id)))"""

if old not in text:
    raise SystemExit("alloc block not found")
text = text.replace(old, new, 1)

# enrich return with buf_kind (optional, non-breaking)
old_ret = """        return {
            "ok": bool(ok or posted.get("wait") == 0),
            "result": "PATH_CONTAINS_DEST" if ok else "POSTED_DEST_NOT_IN_PATH",
            "army": army_index,
            "province": province_id,
            "post_rax": posted["rax"] & 0xFF,
            "post_wait": posted["wait"],
            "path_before": before,
            "path_after": after,
            "factory_idx": FACTORY_IDX,
        }"""
new_ret = """        return {
            "ok": bool(ok or posted.get("wait") == 0),
            "result": "PATH_CONTAINS_DEST" if ok else "POSTED_DEST_NOT_IN_PATH",
            "army": army_index,
            "province": province_id,
            "post_rax": posted["rax"] & 0xFF,
            "post_wait": posted["wait"],
            "path_before": before,
            "path_after": after,
            "factory_idx": FACTORY_IDX,
            "province_buf_kind": buf_kind,
            "stub_meta": {
                "wait": posted.get("wait"),
                "stub_leaked_on_timeout": posted.get("stub_leaked_on_timeout"),
                "stub_freed": posted.get("stub_freed"),
                "elapsed_ms": posted.get("elapsed_ms"),
            },
        }"""
if old_ret not in text:
    raise SystemExit("return block not found")
text = text.replace(old_ret, new_ret, 1)

# docstring bump
text = text.replace(
    "Province destinations use a remote VirtualAllocEx u32 array (size=1).",
    "Province destinations: dry_run VirtualAllocEx; live Post ucrtbase!malloc u32[1]\n"
    "(2ijy: VirtualAllocEx + vector dtor → 0xC0000374 heap corruption).",
)

path.write_text(text, encoding="utf-8")
print("patched", path)
print("has_game_malloc", "_game_malloc" in path.read_text(encoding="utf-8"))
