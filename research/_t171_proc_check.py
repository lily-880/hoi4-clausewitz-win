
import ctypes, ctypes.wintypes as w, struct, json, hashlib, time
from pathlib import Path

TH32CS_SNAPPROCESS = 0x2
PROCESS_QUERY_LIMITED = 0x1000
PROCESS_VM_READ = 0x10
PROCESS_QUERY_INFORMATION = 0x400

class PE(ctypes.Structure):
    _fields_ = [
        ("dwSize", w.DWORD),
        ("cntUsage", w.DWORD),
        ("th32ProcessID", w.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID", w.DWORD),
        ("cntThreads", w.DWORD),
        ("th32ParentProcessID", w.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", w.DWORD),
        ("szExeFile", w.CHAR * 260),
    ]

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
CreateToolhelp32Snapshot = kernel32.CreateToolhelp32Snapshot
CreateToolhelp32Snapshot.restype = w.HANDLE
Process32First = kernel32.Process32First
Process32Next = kernel32.Process32Next
OpenProcess = kernel32.OpenProcess
OpenProcess.restype = w.HANDLE
CloseHandle = kernel32.CloseHandle
ReadProcessMemory = kernel32.ReadProcessMemory
QueryFullProcessImageNameW = ctypes.WinDLL("kernel32", use_last_error=True).QueryFullProcessImageNameW

found = []
snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
pe = PE(); pe.dwSize = ctypes.sizeof(PE)
ok = Process32First(snap, ctypes.byref(pe))
while ok:
    name = pe.szExeFile.split(b"\0",1)[0].decode("utf-8","replace")
    if name.lower() == "hoi4.exe":
        found.append(int(pe.th32ProcessID))
    ok = Process32Next(snap, ctypes.byref(pe))
CloseHandle(snap)
print("PIDS", found)
Path("research/_t171_proc_pids.json").write_text(json.dumps({"pids":found}), encoding="utf-8")
