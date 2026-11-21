from __future__ import annotations
import json, struct, sys, time
from pathlib import Path

ROOT = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")
sys.path.insert(0, str(ROOT / "calling"))

from pe import PE
from mem import Proc, find_pid as mem_find_pid
from gamestate import detect_session, resolve_player_country, _rtti_name_from_vtable, read_campaign_summary

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
EXPECTED_PID = 8500
OUT = ROOT / "research" / "t195_after_og_timeout.json"


def is_ptr(x):
    return type(x) is int and 0x20000000000 < x < 0x7FFFFFFFFFFF


def pdx(p, a):
    return struct.unpack("<QII", p.read(a, 16))


def ptr_array(p, a, bound=4096):
    data, cap, size = pdx(p, a)
    if not 0 <= size <= cap <= max(bound, 100) or (size and not is_ptr(data)):
        return []
    return [struct.unpack("<Q", p.read(data + 8 * j, 8))[0] for j in range(size)]


def handle_at(p, a):
    return list(struct.unpack("<II", p.read(a, 8)))


def cls(p, pe, a):
    if not is_ptr(a):
        return None
    try:
        vt = struct.unpack("<Q", p.read(a, 8))[0]
    except OSError:
        return None
    if not p.base <= vt < p.base + p.image_size:
        return None
    return _rtti_name_from_vtable(pe, vt - p.base)


def msvc_string(p, a):
    blob = p.read(a, 32)
    n, cap = struct.unpack_from("<QQ", blob, 16)
    if not 0 <= n <= 1024 or cap < n:
        return None
    raw = blob[:n] if cap <= 15 else p.read(struct.unpack_from("<Q", blob)[0], n)
    return raw.decode("utf-8", "replace")


def find_unit(p, co, uid):
    for ap in ptr_array(p, co + 0x290, 4096):
        if struct.unpack("<I", p.read(ap + 0x1C, 4))[0] == uid:
            return ap
    return 0


def unit_path(p, ap):
    data, cap, size = pdx(p, ap + 0x200)
    if size <= 0 or not is_ptr(data) or size > 64:
        return []
    return list(struct.unpack("<" + "I" * size, p.read(data, size * 4)))


def process_health(pid):
    import ctypes
    from ctypes import wintypes as wt
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.OpenProcess.restype = wt.HANDLE
    k.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
    k.GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
    k.GetExitCodeProcess.restype = wt.BOOL
    k.CloseHandle.argtypes = [wt.HANDLE]
    h = k.OpenProcess(0x1000 | 0x0400, False, pid)
    if not h:
        return {"alive": False}
    try:
        code = wt.DWORD(0)
        k.GetExitCodeProcess(h, ctypes.byref(code))
        return {"alive": int(code.value) == 259, "exit_code": int(code.value)}
    finally:
        k.CloseHandle(h)


def snap(p, pe, co, idler, gs):
    theatres = []
    for tp in ptr_array(p, co + 0x168, 64):
        ogs = []
        for gp in ptr_array(p, tp + 0x80, 256):
            ogs.append({
                "ptr": hex(gp), "class": cls(p, pe, gp),
                "handle": handle_at(p, gp + 8),
                "name": msvc_string(p, gp + 0x160),
            })
        fms = []
        for gp in ptr_array(p, tp + 0x98, 256):
            fms.append({
                "ptr": hex(gp), "class": cls(p, pe, gp),
                "handle": handle_at(p, gp + 8),
                "name": msvc_string(p, gp + 0x160),
            })
        theatres.append({"handle": handle_at(p, tp + 8), "ogs": ogs, "ags": fms})
    u1829 = find_unit(p, co, 1829)
    u1838 = find_unit(p, co, 1838)
    summary = read_campaign_summary(p, gs)
    return {
        "health": process_health(p.pid),
        "pause": p.read(idler + 0x6C1, 1)[0],
        "speed": struct.unpack("<i", p.read(gs + 0x4BC, 4))[0],
        "date": (summary.get("verified") or {}).get("date_full"),
        "theatres": theatres,
        "u1829_path": unit_path(p, u1829) if u1829 else None,
        "u1829_prov": struct.unpack("<I", p.read(u1829 + 0x28, 4))[0] if u1829 else None,
        "u1838_og": hex(struct.unpack("<Q", p.read(u1838 + 0xC0, 8))[0]) if u1838 else None,
    }


def main():
    pid = mem_find_pid("hoi4.exe")
    out = {"authorized_by": ["pt181u", "pt180u"], "found_pid": pid, "polls": []}
    if pid != EXPECTED_PID:
        out["ok"] = False
        out["error"] = "PID_MISMATCH"
        OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
        print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
        return
    p = Proc(pid)
    pe = PE(EXE)
    try:
        session = detect_session(p, pe)
        gs = int(session["signals"]["gs_ptr"], 16)
        co = int(resolve_player_country(p, gs)["country_ptr"], 16)
        idler = int(session["signals"]["idler_ptr"], 16)
        for i in range(6):
            rec = snap(p, pe, co, idler, gs)
            rec["i"] = i
            out["polls"].append(rec)
            print("POLL", i, json.dumps({k: rec[k] for k in rec if k != "theatres"}, ensure_ascii=False, default=str),
                  "ogs", rec["theatres"][0]["ogs"] if rec["theatres"] else None)
            if rec["theatres"] and rec["theatres"][0]["ogs"]:
                break
            if not rec["health"].get("alive"):
                break
            time.sleep(2)
        last = out["polls"][-1]
        out["ok"] = bool(last["health"].get("alive") and last["pause"] == 1)
        out["army_appeared"] = bool(last["theatres"] and last["theatres"][0]["ogs"])
        out["final"] = last
    finally:
        p.close()
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in out if k != "polls"}, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
