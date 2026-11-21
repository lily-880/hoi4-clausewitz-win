# -*- coding: utf-8 -*-
from __future__ import annotations
import json, os, struct, sys, time, traceback
from pathlib import Path

ROOT = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")
sys.path.insert(0, str(ROOT / "calling"))
os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
os.environ.pop("CLAUSEWITZ_ALLOW_WRITE", None)

from pe import PE
from mem import Proc, find_pid as mem_find_pid
from gamestate import detect_session, resolve_player_country, _rtti_name_from_vtable, read_campaign_summary
from config import allow_post
from process import Backend
import move_order as mo
import post_abi

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
MARKER = ROOT / "research" / "safe_land_tool_gate.OPEN"
LEGACY = ROOT / "research" / "strategic_only_tool_gate.OPEN"
OUT = ROOT / "research" / "t197_setpath_zero_post.json"
EXPECTED_PID = 12948
ARMY_HANDLE = (53, 411)
PATH_PROVINCES = (2072, 7944)
OG_FACTORY_UNUSED = None
NR = {"factory": 0x18D0440, "vt": 0x2A856A0, "isvalid": 0x18DF5E0, "execute": 0x18D9A30, "size": 0x70}
SP = {"factory": 0x18D0950, "vt": 0x2A84FE0, "isvalid": 0x18DFF70, "execute": 0x18DAF60, "size": 0x58}


def is_ptr(x):
    return type(x) is int and 0x20000000000 < x < 0x7FFFFFFFFFFF


def open_gates(note):
    MARKER.write_text(note, encoding="utf-8")
    os.environ["CLAUSEWITZ_ALLOW_POST"] = "1"


def close_gates():
    os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
    os.environ.pop("CLAUSEWITZ_ALLOW_WRITE", None)
    for p in (MARKER, LEGACY):
        try:
            if p.exists():
                p.unlink()
        except Exception:
            pass


def process_health(pid):
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.windll.kernel32
    h = kernel.OpenProcess(0x1000, False, pid)
    if not h:
        return {"alive": False, "exit_code": None}
    code = wintypes.DWORD()
    ok = kernel.GetExitCodeProcess(h, ctypes.byref(code))
    kernel.CloseHandle(h)
    return {"alive": bool(ok) and code.value == 259, "exit_code": int(code.value) if ok else None}


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


def u32_array(p, a, bound=256):
    data, cap, size = pdx(p, a)
    if size <= 0 or not is_ptr(data) or not 0 <= size <= cap <= bound:
        return []
    return list(struct.unpack("<" + "I" * size, p.read(data, size * 4)))


def snap_inst(p, pe, ip):
    return {
        "ptr": hex(ip),
        "class": cls(p, pe, ip),
        "type_30": struct.unpack("<I", p.read(ip + 0x30, 4))[0],
        "instance_id_244": struct.unpack("<I", p.read(ip + 0x244, 4))[0],
        "can_execute_248": p.read(ip + 0x248, 1)[0],
        "path_70": u32_array(p, ip + 0x70),
        "field_258": struct.unpack("<I", p.read(ip + 0x258, 4))[0],
        "field_25c": struct.unpack("<I", p.read(ip + 0x25C, 4))[0],
    }


def find_group(p, pe, co, handle):
    for tp in ptr_array(p, co + 0x168, 64):
        for gp in ptr_array(p, tp + 0x80, 256):
            if handle_at(p, gp + 8) == list(handle):
                insts = [snap_inst(p, pe, ip) for ip in ptr_array(p, gp + 0x98, 256)]
                return gp, insts
    return 0, []


def factory_make(pid, b, factory_rva, expect_vt, size):
    made = mo._remote(pid, b.image_base + factory_rva, wait_ms=5000)
    cmd = made.get("rax") or 0
    rec = {"wait": made.get("wait"), "rax": made.get("rax"), "stub_freed": made.get("stub_freed")}
    if made.get("wait") != 0 or cmd < 0x10000:
        rec["error"] = "FACTORY_FAIL"
        return 0, rec
    vt = mo._u64(b, cmd) - b.image_base
    rec["vt"] = hex(vt)
    rec["cmd"] = hex(cmd)
    rec["zeroed"] = False
    if vt != expect_vt:
        rec["error"] = "VT_MISMATCH"
        return 0, rec
    return cmd, rec


def dry_isvalid(pid, b, isvalid_rva, cmd):
    valid = mo._remote(pid, b.image_base + isvalid_rva, {"rcx": cmd}, wait_ms=5000)
    return {"wait": valid.get("wait"), "rax": valid.get("rax"),
            "isvalid": (valid["rax"] & 0xFF) if valid.get("wait") == 0 else None}


def do_post(pid, b, cmd, note):
    open_gates(note)
    try:
        if not allow_post():
            return {"error": "ALLOW_POST_FALSE", "allow_post": False}
        sess = mo._u64(b, b.image_base + post_abi.G_SESSION)
        posted = mo._remote(pid, b.image_base + post_abi.FN_CMD_QUEUE_POST,
                            {"rcx": sess, "rdx": cmd, "r8": 1}, wait_ms=8000)
        time.sleep(0.4)
        return {"wait": posted.get("wait"), "rax": posted.get("rax"),
                "post_rax": (posted.get("rax") or 0) & 0xFF,
                "elapsed_ms": posted.get("elapsed_ms"), "stub_freed": posted.get("stub_freed"),
                "allow_post_at_post": True}
    finally:
        close_gates()


def save(result):
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def fail(result, error):
    result["ok"] = False
    result["error"] = error
    save(result)
    return result


def main():
    result = {
        "ok": False, "error": None, "steps": [],
        "authorized_by": ["pt183u", "pt180u"],
        "note": "NewRoot on existing army 411 with live SetPath sentinels 0,0 then SetPath 2072,7944. No SetArmyLeader. No 1x. Does not touch plan 1.",
    }
    close_gates()
    pid = mem_find_pid("hoi4.exe")
    result["found_pid"] = pid
    result["health"] = process_health(pid) if pid else {"alive": False}
    if pid != EXPECTED_PID or not result["health"].get("alive"):
        return fail(result, "PID_MISMATCH_OR_DEAD")
    p = Proc(pid)
    pe = PE(EXE)
    b = Backend()
    try:
        session = detect_session(p, pe)
        gs = int(session["signals"]["gs_ptr"], 16)
        idler = int(session["signals"]["idler_ptr"], 16)
        co = int(resolve_player_country(p, gs)["country_ptr"], 16)
        pause = p.read(idler + 0x6C1, 1)[0]
        speed = struct.unpack("<i", p.read(gs + 0x4BC, 4))[0]
        result["session"] = {"pid": pid, "pause": pause, "speed": speed,
                             "date": (read_campaign_summary(p, gs).get("verified") or {}).get("date_full")}
        if pause != 1 or speed != 0:
            return fail(result, "NOT_OFFICIALLY_PAUSED")
        live_sent = list(struct.unpack("<II", p.read(p.base + 0x33EB2A0, 8)))
        result["live_setpath_sentinels"] = live_sent
        gp, insts_before = find_group(p, pe, co, ARMY_HANDLE)
        result["instances_before"] = insts_before
        if not gp:
            return fail(result, "ARMY_411_MISSING")
        ids_before = {x["instance_id_244"] for x in insts_before}

        cmd, frec = factory_make(pid, b, NR["factory"], NR["vt"], NR["size"])
        result["nr_factory"] = frec
        if not cmd:
            return fail(result, "NR_FACTORY_FAIL")
        mo._write(pid, cmd + 0x28, struct.pack("<II", *ARMY_HANDLE))
        mo._write(pid, cmd + 0x48, struct.pack("<II", live_sent[0], live_sent[1]))
        mo._write(pid, cmd + 0x60, struct.pack("<Q", 0))
        mo._write(pid, cmd + 0x6C, struct.pack("<I", 0))
        raw = p.read(cmd, NR["size"])
        result["nr_packed"] = {
            "group": list(struct.unpack_from("<II", raw, 0x28)),
            "provinces": list(struct.unpack_from("<II", raw, 0x48)),
        }
        result["nr_dry"] = dry_isvalid(pid, b, NR["isvalid"], cmd)
        print("NR DRY", result["nr_dry"], result["nr_packed"])
        if result["nr_dry"].get("isvalid") != 1:
            return fail(result, "NR_ISVALID_FALSE")
        result["nr_post"] = do_post(pid, b, cmd, "t197 COrderNewRootCommand live sentinels 0,0 authorized by pt183u+pt180u.")
        result["steps"].append("nr_post")
        result["health_after_nr"] = process_health(EXPECTED_PID)
        if result["nr_post"].get("wait") not in (0, None):
            return fail(result, "NR_POST_TIMEOUT_STOP")
        if not result["health_after_nr"].get("alive"):
            return fail(result, "PROCESS_DEAD_AFTER_NR")
        if result["nr_post"].get("post_rax") != 1:
            return fail(result, "NR_POST_FAIL")
        gp, insts = find_group(p, pe, co, ARMY_HANDLE)
        result["instances_after_nr"] = insts
        new = [x for x in insts if x["instance_id_244"] not in ids_before]
        if not new:
            return fail(result, "NO_NEW_INSTANCE")
        inst = new[0]
        result["new_instance"] = inst
        if inst["field_258"] != live_sent[0] or inst["field_25c"] != live_sent[1]:
            return fail(result, "SENTINEL_NOT_APPLIED")
        save(result)

        inst_id = inst["instance_id_244"]
        cmd2, frec2 = factory_make(pid, b, SP["factory"], SP["vt"], SP["size"])
        result["sp_factory"] = frec2
        if not cmd2:
            return fail(result, "SP_FACTORY_FAIL")
        pbuf = mo._game_malloc(pid, 8)
        mo._write(pid, pbuf, struct.pack("<II", PATH_PROVINCES[0], PATH_PROVINCES[1]))
        mo._write(pid, cmd2 + 0x28, struct.pack("<II", *ARMY_HANDLE))
        mo._write(pid, cmd2 + 0x30, struct.pack("<II", inst_id, 0))  # id + clear leftover
        mo._write(pid, cmd2 + 0x38, struct.pack("<QII", pbuf, 2, 2))
        mo._write(pid, cmd2 + 0x50, struct.pack("<B", 1))
        raw2 = p.read(cmd2, SP["size"])
        result["sp_packed"] = {
            "group": list(struct.unpack_from("<II", raw2, 0x28)),
            "plus30": list(struct.unpack_from("<II", raw2, 0x30)),
            "path_vec": list(struct.unpack_from("<QII", raw2, 0x38)),
            "flag50": raw2[0x50],
            "provinces": list(PATH_PROVINCES),
        }
        result["sp_dry"] = dry_isvalid(pid, b, SP["isvalid"], cmd2)
        print("SP DRY", result["sp_dry"], result["sp_packed"])
        if result["sp_dry"].get("isvalid") != 1:
            return fail(result, "SP_ISVALID_FALSE")
        result["sp_post"] = do_post(pid, b, cmd2, "t197 COrderSetPathCommand 2072,7944 authorized by pt183u+pt180u.")
        result["steps"].append("sp_post")
        result["health_after_sp"] = process_health(EXPECTED_PID)
        if result["sp_post"].get("wait") not in (0, None):
            return fail(result, "SP_POST_TIMEOUT_STOP")
        if not result["health_after_sp"].get("alive"):
            return fail(result, "PROCESS_DEAD_AFTER_SP")
        if result["sp_post"].get("post_rax") != 1:
            return fail(result, "SP_POST_FAIL")
        gp, insts = find_group(p, pe, co, ARMY_HANDLE)
        result["instances_after_sp"] = insts
        after = next((x for x in insts if x["instance_id_244"] == inst_id), None)
        result["path_70_after_sp"] = after["path_70"] if after else None
        print("PATH70", result["path_70_after_sp"])
        if result["path_70_after_sp"] != list(PATH_PROVINCES):
            return fail(result, "PATH70_NOT_FILLED")
        result["ok"] = True
        pause = p.read(idler + 0x6C1, 1)[0]
        speed = struct.unpack("<i", p.read(gs + 0x4BC, 4))[0]
        result["final_pause"] = {"ok": pause == 1 and speed == 0, "pause": pause, "speed": speed}
        result["health_final"] = process_health(EXPECTED_PID)
        save(result)
        return result
    except Exception as e:
        result["exception"] = traceback.format_exc()
        return fail(result, "EXCEPTION:" + type(e).__name__)
    finally:
        try:
            p.close()
        except Exception:
            pass
        close_gates()
        print("GATE_CLOSED", {"allow_post_after_close": allow_post(), "marker_exists": MARKER.exists()})


if __name__ == "__main__":
    rec = main()
    keys = ("ok", "error", "steps", "nr_dry", "nr_post", "new_instance", "sp_dry", "sp_post",
            "path_70_after_sp", "final_pause", "health_final", "live_setpath_sentinels", "instances_after_sp")
    print(json.dumps({k: rec.get(k) for k in keys}, indent=2, ensure_ascii=False, default=str))
