import json, sys
from pathlib import Path
ROOT = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")
sys.path.insert(0, str(ROOT / "calling"))
from mem import find_pid as mem_find_pid

# also list hoi4 processes via ctypes / toolhelp if needed
import ctypes
from ctypes import wintypes as wt

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
TH32CS_SNAPPROCESS = 0x00000002

class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD),
        ("cntUsage", wt.DWORD),
        ("th32ProcessID", wt.DWORD),
        ("th32DefaultHeapID", ctypes.c_void_p),
        ("th32ModuleID", wt.DWORD),
        ("cntThreads", wt.DWORD),
        ("th32ParentProcessID", wt.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wt.DWORD),
        ("szExeFile", ctypes.c_wchar * 260),
    ]

CreateToolhelp32Snapshot = kernel32.CreateToolhelp32Snapshot
CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
CreateToolhelp32Snapshot.restype = wt.HANDLE
Process32FirstW = kernel32.Process32FirstW
Process32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
Process32FirstW.restype = wt.BOOL
Process32NextW = kernel32.Process32NextW
Process32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
Process32NextW.restype = wt.BOOL
CloseHandle = kernel32.CloseHandle

procs = []
snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
if snap and snap != wt.HANDLE(-1).value:
    try:
        pe = PROCESSENTRY32W()
        pe.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        ok = Process32FirstW(snap, ctypes.byref(pe))
        while ok:
            name = pe.szExeFile
            if "hoi4" in name.lower():
                procs.append({"pid": int(pe.th32ProcessID), "name": name})
            ok = Process32NextW(snap, ctypes.byref(pe))
    finally:
        CloseHandle(snap)

found = mem_find_pid("hoi4.exe")
out = {"found_pid": found, "hoi4_processes": procs, "pid_8500_present": any(x["pid"] == 8500 for x in procs)}
print(json.dumps(out, indent=2))
Path(ROOT / "research" / "t195_process_after_crash.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
