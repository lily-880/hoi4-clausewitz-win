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
OUT = ROOT / "research" / "t197_setpath_post.json"

EXPECTED_PID = 12948
MEMBER_UNIT = 1846          # interior 12757; not 1829 mover, not army-1 member 1838
PATH_PROVINCES = (2072, 7944)  # known interior land neighbors, not ITA front, not 1829 path
SENTINEL_A = 380896
SENTINEL_B = 380934

OG = {"factory": 0x18D0140, "vt": 0x2A84560, "isvalid": 0x18DF050, "execute": 0x18D6560, "size": 0x60}
NR = {"factory": 0x18D0440, "vt": 0x2A856A0, "isvalid": 0x18DF5E0, "execute": 0x18D9A30, "size": 0x70}
SP = {"factory": 0x18D0950, "vt": 0x2A84FE0, "isvalid": 0x18DFF70, "execute": 0x18DAF60, "size": 0x58}

HANDLE_ARMY_UNIT = 0x33

def is_ptr(x):
    return type(x) is int and 0x20000000000 < x < 0x7FFFFFFFFFFF


def open_gates(note: str):
    os.environ["CLAUSEWITZ_ALLOW_POST"] = "1"
    MARKER.write_text(note + "\nPause/1x only. Close after this Post.\n", encoding="utf-8")
    if LEGACY.exists():
        LEGACY.unlink()


def close_gates():
    os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
    os.environ.pop("CLAUSEWITZ_ALLOW_WRITE", None)
    if MARKER.exists():
        MARKER.unlink()
    if LEGACY.exists():
        LEGACY.unlink()


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


def pdx(p, a):
    return struct.unpack("<QII", p.read(a, 16))


def ptr_array(p, a, bound=4096):
    data, cap, size = pdx(p, a)
    if not 0 <= size <= cap <= max(bound, 100) or (size and not is_ptr(data)):
        return []
    return [struct.unpack("<Q", p.read(data + 8 * j, 8))[0] for j in range(size)]


def u32_array(p, a, bound=256):
    data, cap, size = pdx(p, a)
    if size <= 0 or not is_ptr(data) or not 0 <= size <= cap <= bound:
        return []
    return list(struct.unpack("<" + "I" * size, p.read(data, size * 4)))


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
    return u32_array(p, ap + 0x200) if ap else []


def snap_unit(p, pe, ap):
    if not ap:
        return None
    cmd = ptr_array(p, ap + 0x2C0, 64)
    elems = []
    for c in cmd:
        ev = {"ptr": hex(c), "class": cls(p, pe, c)}
        if is_ptr(c):
            ev["plus8"] = struct.unpack("<I", p.read(c + 8, 4))[0]
            ev["head16"] = p.read(c, 16).hex()
        elems.append(ev)
    return {
        "ptr": hex(ap),
        "unit_id": struct.unpack("<I", p.read(ap + 0x1C, 4))[0],
        "province": struct.unpack("<I", p.read(ap + 0x28, 4))[0],
        "path": u32_array(p, ap + 0x200),
        "full_path": u32_array(p, ap + 0x220),
        "progress": struct.unpack("<f", p.read(ap + 0x240, 4))[0],
        "commandlist_size": len(cmd),
        "commandlist": elems,
    }


def snap_instance(p, pe, ip):
    rec = {"ptr": hex(ip), "class": cls(p, pe, ip)}
    if not is_ptr(ip):
        return rec
    rec["type_30"] = struct.unpack("<I", p.read(ip + 0x30, 4))[0]
    rec["instance_id_244"] = struct.unpack("<I", p.read(ip + 0x244, 4))[0]
    rec["can_execute_248"] = p.read(ip + 0x248, 1)[0]
    rec["path_70"] = u32_array(p, ip + 0x70)
    rec["states_e0"] = u32_array(p, ip + 0xE0)
    rec["field_258"] = struct.unpack("<I", p.read(ip + 0x258, 4))[0]
    rec["field_25c"] = struct.unpack("<I", p.read(ip + 0x25C, 4))[0]
    # candidate assigned-unit arrays
    arrays = {}
    for off in (0x38, 0x40, 0x48, 0x50, 0x58, 0x60, 0x80, 0x98, 0xB0, 0xC8, 0xF8, 0x110, 0x128, 0x140, 0x280, 0x298, 0x2B0):
        data, cap, size = pdx(p, ip + off)
        if 0 <= size <= cap <= 64 and (size == 0 or is_ptr(data)):
            preview = None
            if size and is_ptr(data):
                preview = p.read(data, min(size, 8) * 8).hex()
                # try as handle pairs
                if size <= 16:
                    hs = [list(struct.unpack("<II", p.read(data + 8 * j, 8))) for j in range(size)]
                    preview = {"handles": hs, "hex": preview}
            arrays[hex(off)] = {"data": hex(data), "cap": cap, "size": size, "preview": preview}
    rec["arrays"] = arrays
    return rec


def snap_group(p, pe, gp, children=False):
    rec = {
        "ptr": hex(gp),
        "class": cls(p, pe, gp),
        "handle": handle_at(p, gp + 8),
        "name": msvc_string(p, gp + 0x160),
        "fm_flag_39": p.read(gp + 0x39, 1)[0],
    }
    lp = struct.unpack("<Q", p.read(gp + 0x88, 8))[0]
    rec["leader_ptr"] = hex(lp) if is_ptr(lp) else None
    rec["leader_handle"] = handle_at(p, lp + 0x18) if is_ptr(lp) else None
    rec["order_instances"] = [snap_instance(p, pe, ip) for ip in ptr_array(p, gp + 0x98, 256)]
    if children:
        rec["children"] = []
        for cp in ptr_array(p, gp + 0x230, 256):
            rec["children"].append({"ptr": hex(cp), "class": cls(p, pe, cp), "handle": handle_at(p, cp + 8), "name": msvc_string(p, cp + 0x160)})
    return rec


def snap_theatre(p, pe, co):
    out = []
    for tp in ptr_array(p, co + 0x168, 64):
        rec = {"ptr": hex(tp), "class": cls(p, pe, tp), "handle": handle_at(p, tp + 8)}
        rec["orders_groups"] = [snap_group(p, pe, gp) for gp in ptr_array(p, tp + 0x80, 256)]
        rec["army_groups"] = [snap_group(p, pe, gp, children=True) for gp in ptr_array(p, tp + 0x98, 256)]
        out.append(rec)
    return out


def pause_speed(p, idler, gs):
    return p.read(idler + 0x6C1, 1)[0], struct.unpack("<i", p.read(gs + 0x4BC, 4))[0]


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
    if vt != expect_vt:
        rec["error"] = "VT_MISMATCH"
        return 0, rec
    # t195 lesson: do NOT memset the whole factory object from +0x8.
    # Pack only required slots; clear known leftover slots at the call site.
    rec["zeroed"] = False
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


def fail(result, err, **extra):
    result["ok"] = False
    result["error"] = err
    result.update(extra)
    save(result)
    print(json.dumps({k: result[k] for k in result if k not in ("traceback",)}, indent=2, ensure_ascii=False, default=str))
    return False


def still_paused(p, idler, gs):
    pause, speed = pause_speed(p, idler, gs)
    return pause == 1 and speed == 0, pause, speed



def fail(result, error):
    result["ok"] = False
    result["error"] = error
    save(result)
    return result


def still_paused(p, idler, gs):
    pause = p.read(idler + 0x6C1, 1)[0]
    speed = struct.unpack("<i", p.read(gs + 0x4BC, 4))[0]
    return pause == 1, {"pause": pause, "speed": speed}


def group_for_unit(theatres, unit_id):
    for th in theatres or []:
        for og in th.get("orders_groups") or []:
            # snap_group may not include members; caller can also pass handle
            yield og


def main():
    result = {
        "ok": False,
        "error": None,
        "steps": [],
        "authorized_by": ["pt183u", "pt180u"],
        "note": "New army on 1846 + NewRoot with SetPath sentinels + COrderSetPathCommand to fill official +0x70. Does not touch army 1 / executing plan 1. No SetArmyLeader. No 1x.",
    }
    close_gates()
    process_pid = mem_find_pid("hoi4.exe")
    result["found_pid"] = process_pid
    result["health"] = process_health(process_pid) if process_pid else {"alive": False}
    if process_pid != EXPECTED_PID or not result["health"].get("alive"):
        return fail(result, "PID_MISMATCH_OR_DEAD")
    p = Proc(process_pid)
    pe = PE(EXE)
    b = Backend()
    try:
        session = detect_session(p, pe)
        gs = int(session["signals"]["gs_ptr"], 16)
        idler = int(session["signals"]["idler_ptr"], 16)
        co = int(resolve_player_country(p, gs)["country_ptr"], 16)
        paused, ps = still_paused(p, idler, gs)
        date = (read_campaign_summary(p, gs).get("verified") or {}).get("date_full")
        result["session"] = {
            "pid": process_pid, "gs": hex(gs), "co": hex(co), "idler": hex(idler),
            "base": hex(p.base), "date": date, "pause": ps["pause"], "speed": ps["speed"],
        }
        if not paused or ps["speed"] != 0:
            return fail(result, "NOT_OFFICIALLY_PAUSED")

        theatres0 = snap_theatre(p, pe, co)
        result["theatre_before"] = theatres0
        if not theatres0:
            return fail(result, "NO_THEATRE")
        theatre_handle = theatres0[0]["handle"]
        existing_og = {tuple(og["handle"]) for og in theatres0[0].get("orders_groups") or []}
        u = find_unit(p, co, MEMBER_UNIT)
        if not u:
            return fail(result, "SPARE_UNIT_MISSING")
        result["unit_1846_before"] = snap_unit(p, pe, u)
        if not still_paused(p, idler, gs)[0]:
            return fail(result, "PAUSE_CHANGED")

        # ----- 1. COrderGroupCommand for 1846 -----
        cmd, frec = factory_make(process_pid, b, OG["factory"], OG["vt"], OG["size"])
        result["og_factory"] = frec
        if not cmd:
            return fail(result, "OG_FACTORY_FAIL")
        buf = mo._game_malloc(process_pid, 16)
        mo._write(process_pid, buf, struct.pack("<II", HANDLE_ARMY_UNIT, MEMBER_UNIT))
        mo._write(process_pid, cmd + 0x30, struct.pack("<QII", buf, 1, 1))
        mo._write(process_pid, cmd + 0x48, struct.pack("<II", theatre_handle[0], theatre_handle[1]))
        raw = p.read(cmd, OG["size"])
        result["og_packed"] = {
            "cmd": hex(cmd),
            "flag28": list(struct.unpack_from("<II", raw, 0x28)),
            "vec": list(struct.unpack_from("<QII", raw, 0x30)),
            "theatre": list(struct.unpack_from("<II", raw, 0x48)),
        }
        result["og_dry"] = dry_isvalid(process_pid, b, OG["isvalid"], cmd)
        print("OG DRY", result["og_dry"], result["og_packed"])
        if result["og_dry"].get("isvalid") != 1:
            return fail(result, "OG_ISVALID_FALSE")
        result["og_post"] = do_post(process_pid, b, cmd, "t197 COrderGroupCommand unit 1846 authorized by pt183u+pt180u.")
        result["steps"].append("og_post")
        result["health_after_og"] = process_health(EXPECTED_PID)
        if result["og_post"].get("wait") not in (0, None):
            result["theatre_after_og"] = snap_theatre(p, pe, co) if result["health_after_og"].get("alive") else None
            return fail(result, "OG_POST_TIMEOUT_STOP")
        if not result["health_after_og"].get("alive"):
            return fail(result, "PROCESS_DEAD_AFTER_OG")
        theatres = snap_theatre(p, pe, co)
        result["theatre_after_og"] = theatres
        if result["og_post"].get("post_rax") != 1:
            return fail(result, "OG_POST_FAIL")
        new_ogs = [og for og in (theatres[0].get("orders_groups") or []) if tuple(og["handle"]) not in existing_og]
        if not new_ogs:
            return fail(result, "OG_NOT_CREATED")
        army = new_ogs[0]
        army_handle = army["handle"]
        result["army_handle"] = army_handle
        result["new_army_name"] = army.get("name")
        save(result)

        # ----- 2. COrderNewRootCommand with SetPath sentinels -----
        cmd2, frec2 = factory_make(process_pid, b, NR["factory"], NR["vt"], NR["size"])
        result["nr_factory"] = frec2
        if not cmd2:
            return fail(result, "NR_FACTORY_FAIL")
        mo._write(process_pid, cmd2 + 0x28, struct.pack("<II", army_handle[0], army_handle[1]))
        mo._write(process_pid, cmd2 + 0x48, struct.pack("<II", SENTINEL_A, SENTINEL_B))
        mo._write(process_pid, cmd2 + 0x60, struct.pack("<Q", 0))
        mo._write(process_pid, cmd2 + 0x6C, struct.pack("<I", 0))
        raw2 = p.read(cmd2, NR["size"])
        result["nr_packed"] = {
            "group": list(struct.unpack_from("<II", raw2, 0x28)),
            "provinces": list(struct.unpack_from("<II", raw2, 0x48)),
            "q60": struct.unpack_from("<Q", raw2, 0x60)[0],
            "b6c": struct.unpack_from("<I", raw2, 0x6C)[0],
        }
        result["nr_dry"] = dry_isvalid(process_pid, b, NR["isvalid"], cmd2)
        print("NR DRY", result["nr_dry"], result["nr_packed"])
        if result["nr_dry"].get("isvalid") != 1:
            return fail(result, "NR_ISVALID_FALSE")
        if not still_paused(p, idler, gs)[0]:
            return fail(result, "PAUSE_CHANGED")
        result["nr_post"] = do_post(process_pid, b, cmd2, "t197 COrderNewRootCommand sentinels 380896/380934 authorized by pt183u+pt180u.")
        result["steps"].append("nr_post")
        result["health_after_nr"] = process_health(EXPECTED_PID)
        if result["nr_post"].get("wait") not in (0, None):
            return fail(result, "NR_POST_TIMEOUT_STOP")
        if not result["health_after_nr"].get("alive"):
            return fail(result, "PROCESS_DEAD_AFTER_NR")
        if result["nr_post"].get("post_rax") != 1:
            return fail(result, "NR_POST_FAIL")
        theatres = snap_theatre(p, pe, co)
        result["theatre_after_nr"] = theatres
        insts = []
        for og in theatres[0].get("orders_groups") or []:
            if og.get("handle") == army_handle:
                insts = og.get("order_instances") or og.get("instances") or []
                # snap_group uses order_instances? t196 snap_group field name
                break
        # snap_group in t196: check keys
        if not insts:
            # re-read via raw
            for og in theatres[0].get("orders_groups") or []:
                if og.get("handle") == army_handle:
                    insts = og.get("order_instances") or []
        result["instances_after_nr"] = insts
        if not insts:
            # fallback live walk
            result["nr_instances_missing_in_snap"] = True
        inst = insts[0] if insts else None
        if inst:
            result["root_after_nr"] = inst
            if inst.get("field_258") != SENTINEL_A or inst.get("field_25c") != SENTINEL_B:
                result["sentinel_mismatch"] = True
                return fail(result, "NR_SENTINEL_NOT_APPLIED")
            if inst.get("path_70"):
                result["unexpected_path_after_nr"] = inst.get("path_70")
        save(result)

        # resolve instance id
        if inst:
            inst_id = inst.get("instance_id_244")
        else:
            return fail(result, "NO_INSTANCE_AFTER_NR")

        # ----- 3. COrderSetPathCommand -----
        cmd3, frec3 = factory_make(process_pid, b, SP["factory"], SP["vt"], SP["size"])
        result["sp_factory"] = frec3
        if not cmd3:
            return fail(result, "SP_FACTORY_FAIL")
        pbuf = mo._game_malloc(process_pid, 8)
        mo._write(process_pid, pbuf, struct.pack("<II", PATH_PROVINCES[0], PATH_PROVINCES[1]))
        mo._write(process_pid, cmd3 + 0x28, struct.pack("<II", army_handle[0], army_handle[1]))
        mo._write(process_pid, cmd3 + 0x30, struct.pack("<I", inst_id))
        mo._write(process_pid, cmd3 + 0x38, struct.pack("<QII", pbuf, 2, 2))
        mo._write(process_pid, cmd3 + 0x50, struct.pack("<B", 1))
        raw3 = p.read(cmd3, SP["size"])
        result["sp_packed"] = {
            "group": list(struct.unpack_from("<II", raw3, 0x28)),
            "attach_id": struct.unpack_from("<I", raw3, 0x30)[0],
            "path_vec": list(struct.unpack_from("<QII", raw3, 0x38)),
            "flag50": raw3[0x50],
            "pbuf": hex(pbuf),
            "provinces": list(PATH_PROVINCES),
        }
        result["sp_dry"] = dry_isvalid(process_pid, b, SP["isvalid"], cmd3)
        print("SP DRY", result["sp_dry"], result["sp_packed"])
        if result["sp_dry"].get("isvalid") != 1:
            return fail(result, "SP_ISVALID_FALSE")
        if not still_paused(p, idler, gs)[0]:
            return fail(result, "PAUSE_CHANGED")
        result["sp_post"] = do_post(process_pid, b, cmd3, "t197 COrderSetPathCommand 2072,7944 authorized by pt183u+pt180u.")
        result["steps"].append("sp_post")
        result["health_after_sp"] = process_health(EXPECTED_PID)
        if result["sp_post"].get("wait") not in (0, None):
            return fail(result, "SP_POST_TIMEOUT_STOP")
        if not result["health_after_sp"].get("alive"):
            return fail(result, "PROCESS_DEAD_AFTER_SP")
        if result["sp_post"].get("post_rax") != 1:
            return fail(result, "SP_POST_FAIL")
        theatres = snap_theatre(p, pe, co)
        result["theatre_after_sp"] = theatres
        insts2 = []
        for og in theatres[0].get("orders_groups") or []:
            if og.get("handle") == army_handle:
                insts2 = og.get("order_instances") or og.get("instances") or []
        result["instances_after_sp"] = insts2
        path = (insts2[0].get("path_70") if insts2 else None)
        result["path_70_after_sp"] = path
        print("PATH70", path)
        if path != list(PATH_PROVINCES):
            return fail(result, "PATH70_NOT_FILLED")
        result["ok"] = True
        paused, ps = still_paused(p, idler, gs)
        result["final_pause"] = {"ok": paused and ps["speed"] == 0, **ps}
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
    print(json.dumps({k: rec.get(k) for k in (
        "ok", "error", "steps", "army_handle", "nr_dry", "sp_dry",
        "path_70_after_sp", "final_pause", "health_final", "root_after_nr",
        "instances_after_sp", "og_post", "nr_post", "sp_post",
    )}, indent=2, ensure_ascii=False, default=str))
