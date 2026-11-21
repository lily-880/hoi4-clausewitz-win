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
OUT = ROOT / "research" / "t195_scaffold_post.json"
LIVE_OUT = ROOT / "research" / "t195_live_fields.json"

EXPECTED_PID = 8500
MOVE_UNIT = 1829
MOVE_FROM = 5010
MOVE_TO = 8036
MEMBER_UNIT = 1838  # 7980 interior, not the mover
SPARE_UNIT = 1846   # not used for move or army
LEADER_ARMY = 312
LEADER_AG = 313
LEADER_UNIT_TRY = 314
PLAN_A, PLAN_B = 5097, 7944  # interior land neighbors, not ITA front, not the move pair

OG = {"factory": 0x18D0140, "vt": 0x2A84560, "isvalid": 0x18DF050, "execute": 0x18D6560, "size": 0x60}
SL = {"factory": 0x18D0C10, "vt": 0x2A85E20, "isvalid": 0x18E0540, "execute": 0x18DB330, "size": 0x40}
AG = {"factory": 0x18CF780, "vt": 0x2A846E0, "isvalid": 0x18DDFE0, "execute": 0x18D2640, "size": 0x80}
NR = {"factory": 0x18D0440, "vt": 0x2A856A0, "isvalid": 0x18DF5E0, "execute": 0x18D9A30, "size": 0x70}
NF = {"factory": 0x18D03B0, "vt": 0x2A853A0, "isvalid": 0x18DF550, "execute": 0x18D9070, "size": 0x70}
OA = {"factory": 0x18CFD10, "vt": 0x2A84CE0, "isvalid": 0x18DE970, "execute": 0x18D4220, "size": 0x50}
EX = {"factory": 0x18D00E0, "vt": 0x2A85D60, "isvalid": 0x18DEFB0, "execute": 0x18D64A0, "size": 0x38}
PG = {"factory": 0xE53A00, "vt": 0x29E6E10, "isvalid": 0x188D90, "execute": 0xE55060, "size": 0x50}

HANDLE_ARMY_UNIT = 0x33
HANDLE_LEADER = 4713


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
    mo._write(pid, cmd + 8, bytes(size - 8))
    rec["zeroed"] = True
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


def main():
    result = {"authorized_by": ["pt181u", "pt180u"], "stay_paused": True, "steps": []}
    p = None
    idler = 0
    gs = 0
    b = None
    process_pid = EXPECTED_PID
    unpaused = False
    try:
        process_pid = mem_find_pid("hoi4.exe")
        result["health_before"] = process_health(process_pid)
        if process_pid != EXPECTED_PID or not result["health_before"].get("alive"):
            return fail(result, "PID_OR_HEALTH", found=process_pid)
        p = Proc(process_pid)
        pe = PE(EXE)
        session = detect_session(p, pe)
        gs = int(session["signals"]["gs_ptr"], 16)
        co = int(resolve_player_country(p, gs)["country_ptr"], 16)
        idler = int(session["signals"].get("idler_ptr") or "0", 16)
        summary = read_campaign_summary(p, gs)
        ver = summary.get("verified") or {}
        date = ver.get("date_full") or ver.get("date") or {}
        pause, speed = pause_speed(p, idler, gs)
        result["session"] = {
            "pid": process_pid, "gs": hex(gs), "co": hex(co), "idler": hex(idler),
            "date": date, "pause": pause, "speed": speed,
            "base": hex(p.base),
        }
        if pause != 1 or speed != 0:
            return fail(result, "NOT_PAUSED_OR_SPEED")
        theatres = snap_theatre(p, pe, co)
        result["theatre_before"] = theatres
        if not theatres or theatres[0]["handle"][0] != 67 or theatres[0].get("orders_groups") or theatres[0].get("army_groups"):
            return fail(result, "THEATRE_UNEXPECTED")
        theatre_handle = theatres[0]["handle"]
        u1829 = find_unit(p, co, MOVE_UNIT)
        u1838 = find_unit(p, co, MEMBER_UNIT)
        u_spare = find_unit(p, co, SPARE_UNIT)
        if not u1829 or not u1838:
            return fail(result, "UNITS_MISSING")
        s1829 = snap_unit(p, pe, u1829)
        s1838 = snap_unit(p, pe, u1838)
        result["units_before"] = {"1829": s1829, "1838": s1838, "spare": snap_unit(p, pe, u_spare) if u_spare else None}
        if s1829["province"] != MOVE_FROM or s1829["path"] or s1838["path"]:
            return fail(result, "UNIT_STATE_UNEXPECTED")

        b = Backend()

        # ----- 1. Move 1829 5010->8036 (scaffold) -----
        dry = mo.move(MOVE_UNIT, MOVE_TO, dry_run=True)
        result["move_dry"] = dry
        result["steps"].append("move_dry")
        if dry.get("result") not in ("DRY_RUN_VALID",) and "VALID" not in str(dry.get("result") or "").upper():
            # still continue only if clearly valid
            return fail(result, "MOVE_DRY_FAIL")
        if not still_paused(p, idler, gs)[0]:
            return fail(result, "PAUSE_CHANGED_BEFORE_MOVE")
        open_gates("t195 one-shot CMoveCommand 1829 5010->8036 authorized by pt181u+pt180u.")
        try:
            if not allow_post():
                return fail(result, "ALLOW_POST_FALSE_MOVE")
            posted_move = mo.move(MOVE_UNIT, MOVE_TO, dry_run=False)
        finally:
            close_gates()
        time.sleep(0.4)
        s1829 = snap_unit(p, pe, find_unit(p, co, MOVE_UNIT) or u1829)
        result["move_post"] = posted_move
        result["unit_1829_after_move"] = s1829
        ok_p, pause, speed = still_paused(p, idler, gs)
        result["after_move_pause"] = {"pause": pause, "speed": speed}
        result["steps"].append("move_post")
        if not (ok_p and s1829 and s1829["path"] == [MOVE_TO] and s1829["province"] == MOVE_FROM and process_health(EXPECTED_PID).get("alive")):
            return fail(result, "MOVE_POST_UNEXPECTED")
        save(result)

        # ----- 2. Create army + appoint 312 -----
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
            "cmd": hex(cmd), "buf": hex(buf),
            "flag28": list(struct.unpack_from("<II", raw, 0x28)),
            "vec": list(struct.unpack_from("<QII", raw, 0x30)),
            "theatre": list(struct.unpack_from("<II", raw, 0x48)),
        }
        result["og_dry"] = dry_isvalid(process_pid, b, OG["isvalid"], cmd)
        print("OG DRY", result["og_dry"], result["og_packed"])
        if result["og_dry"].get("isvalid") != 1:
            return fail(result, "OG_ISVALID_FALSE")
        if not still_paused(p, idler, gs)[0]:
            return fail(result, "PAUSE_CHANGED")
        result["og_post"] = do_post(process_pid, b, cmd, "t195 COrderGroupCommand unit 1838 authorized by pt181u+pt180u.")
        result["steps"].append("og_post")
        theatres = snap_theatre(p, pe, co)
        result["theatre_after_og"] = theatres
        if not (result["og_post"].get("post_rax") == 1 and theatres and theatres[0]["orders_groups"]):
            return fail(result, "OG_POST_FAIL")
        army = theatres[0]["orders_groups"][0]
        army_handle = army["handle"]
        result["army_handle"] = army_handle
        if unit_path(p, find_unit(p, co, MOVE_UNIT) or u1829) != [MOVE_TO]:
            return fail(result, "KEEP_PATH_LOST_AFTER_OG")
        save(result)

        # appoint 312
        cmd2, frec2 = factory_make(process_pid, b, SL["factory"], SL["vt"], SL["size"])
        result["sl_army_factory"] = frec2
        if not cmd2:
            return fail(result, "SL_ARMY_FACTORY_FAIL")
        mo._write(process_pid, cmd2 + 0x28, struct.pack("<II", HANDLE_LEADER, LEADER_ARMY))
        mo._write(process_pid, cmd2 + 0x30, struct.pack("<II", army_handle[0], army_handle[1]))
        mo._write(process_pid, cmd2 + 0x38, struct.pack("<I", 0))
        result["sl_army_packed"] = {"leader": [HANDLE_LEADER, LEADER_ARMY], "group": army_handle}
        result["sl_army_dry"] = dry_isvalid(process_pid, b, SL["isvalid"], cmd2)
        print("SL ARMY DRY", result["sl_army_dry"])
        if result["sl_army_dry"].get("isvalid") != 1:
            return fail(result, "SL_ARMY_ISVALID_FALSE")
        result["sl_army_post"] = do_post(process_pid, b, cmd2, "t195 CSetArmyLeaderCommand 312 -> army authorized by pt181u+pt180u.")
        result["steps"].append("sl_army_post")
        if result["sl_army_post"].get("post_rax") != 1:
            return fail(result, "SL_ARMY_POST_FAIL")
        save(result)

        # ----- 3. Army group + marshal 313 -----
        cmd3, frec3 = factory_make(process_pid, b, AG["factory"], AG["vt"], AG["size"])
        result["ag_factory"] = frec3
        if not cmd3:
            return fail(result, "AG_FACTORY_FAIL")
        buf3 = mo._game_malloc(process_pid, 16)
        mo._write(process_pid, buf3, struct.pack("<II", army_handle[0], army_handle[1]))
        mo._write(process_pid, cmd3 + 0x28, struct.pack("<II", theatre_handle[0], theatre_handle[1]))
        mo._write(process_pid, cmd3 + 0x30, struct.pack("<QII", buf3, 1, 1))
        result["ag_packed"] = {"theatre": theatre_handle, "orders_groups": [army_handle], "buf": hex(buf3)}
        result["ag_dry"] = dry_isvalid(process_pid, b, AG["isvalid"], cmd3)
        print("AG DRY", result["ag_dry"])
        if result["ag_dry"].get("isvalid") != 1:
            return fail(result, "AG_ISVALID_FALSE")
        result["ag_post"] = do_post(process_pid, b, cmd3, "t195 CArmyGroupCommand authorized by pt181u+pt180u.")
        result["steps"].append("ag_post")
        theatres = snap_theatre(p, pe, co)
        result["theatre_after_ag"] = theatres
        if not (result["ag_post"].get("post_rax") == 1 and theatres and theatres[0]["army_groups"]):
            return fail(result, "AG_POST_FAIL")
        ag = theatres[0]["army_groups"][0]
        ag_handle = ag["handle"]
        result["ag_handle"] = ag_handle
        save(result)

        cmd4, frec4 = factory_make(process_pid, b, SL["factory"], SL["vt"], SL["size"])
        result["sl_ag_factory"] = frec4
        if not cmd4:
            return fail(result, "SL_AG_FACTORY_FAIL")
        mo._write(process_pid, cmd4 + 0x28, struct.pack("<II", HANDLE_LEADER, LEADER_AG))
        mo._write(process_pid, cmd4 + 0x30, struct.pack("<II", ag_handle[0], ag_handle[1]))
        mo._write(process_pid, cmd4 + 0x38, struct.pack("<I", 0))
        result["sl_ag_packed"] = {"leader": [HANDLE_LEADER, LEADER_AG], "group": ag_handle}
        result["sl_ag_dry"] = dry_isvalid(process_pid, b, SL["isvalid"], cmd4)
        print("SL AG DRY", result["sl_ag_dry"])
        if result["sl_ag_dry"].get("isvalid") != 1:
            return fail(result, "SL_AG_ISVALID_FALSE")
        result["sl_ag_post"] = do_post(process_pid, b, cmd4, "t195 CSetArmyLeaderCommand 313 -> army group authorized by pt181u+pt180u.")
        result["steps"].append("sl_ag_post")
        if result["sl_ag_post"].get("post_rax") != 1:
            return fail(result, "SL_AG_POST_FAIL")
        save(result)

        # ----- 4. NewRoot then NewFront (interior 5097/7944) -----
        cmd5, frec5 = factory_make(process_pid, b, NR["factory"], NR["vt"], NR["size"])
        result["nr_factory"] = frec5
        if not cmd5:
            return fail(result, "NR_FACTORY_FAIL")
        mo._write(process_pid, cmd5 + 0x28, struct.pack("<II", army_handle[0], army_handle[1]))
        mo._write(process_pid, cmd5 + 0x48, struct.pack("<II", PLAN_A, PLAN_B))
        raw = p.read(cmd5, NR["size"])
        result["nr_packed"] = {
            "group": list(struct.unpack_from("<II", raw, 0x28)),
            "provinces": list(struct.unpack_from("<II", raw, 0x48)),
            "q60": struct.unpack_from("<Q", raw, 0x60)[0],
            "b6c": raw[0x6C],
        }
        result["nr_dry"] = dry_isvalid(process_pid, b, NR["isvalid"], cmd5)
        print("NR DRY", result["nr_dry"], result["nr_packed"])
        if result["nr_dry"].get("isvalid") != 1:
            return fail(result, "NR_ISVALID_FALSE")
        result["nr_post"] = do_post(process_pid, b, cmd5, "t195 COrderNewRootCommand 5097/7944 authorized by pt181u+pt180u.")
        result["steps"].append("nr_post")
        theatres = snap_theatre(p, pe, co)
        result["theatre_after_nr"] = theatres
        insts = theatres[0]["orders_groups"][0]["order_instances"] if theatres else []
        if not (result["nr_post"].get("post_rax") == 1 and insts):
            return fail(result, "NR_POST_FAIL")
        root = insts[0]
        root_id = root["instance_id_244"]
        result["root_instance"] = root
        save(result)

        # NewFront attached to root
        cmd6, frec6 = factory_make(process_pid, b, NF["factory"], NF["vt"], NF["size"])
        result["nf_factory"] = frec6
        if not cmd6:
            return fail(result, "NF_FACTORY_FAIL")
        path_buf = mo._game_malloc(process_pid, 16)
        mo._write(process_pid, path_buf, struct.pack("<II", PLAN_A, PLAN_B))
        mo._write(process_pid, cmd6 + 0x28, struct.pack("<II", army_handle[0], army_handle[1]))
        # path CPdxArray at +0x50: data, cap, size
        mo._write(process_pid, cmd6 + 0x50, struct.pack("<QII", path_buf, 2, 2))
        mo._write(process_pid, cmd6 + 0x68, struct.pack("<I", root_id))
        raw = p.read(cmd6, NF["size"])
        result["nf_packed"] = {
            "group": list(struct.unpack_from("<II", raw, 0x28)),
            "path_vec": list(struct.unpack_from("<QII", raw, 0x50)),
            "attach_id": struct.unpack_from("<I", raw, 0x68)[0],
            "blitz": raw[0x6D], "withdraw": raw[0x6E],
            "path_buf": hex(path_buf), "provinces": [PLAN_A, PLAN_B],
        }
        result["nf_dry"] = dry_isvalid(process_pid, b, NF["isvalid"], cmd6)
        print("NF DRY", result["nf_dry"], result["nf_packed"])
        if result["nf_dry"].get("isvalid") != 1:
            # do not loop; record and continue to 1x / other work if possible
            result["nf_skipped"] = True
            result["nf_skip_reason"] = "ISVALID_FALSE"
            save(result)
        else:
            result["nf_post"] = do_post(process_pid, b, cmd6, "t195 COrderNewFrontCommand attach root authorized by pt181u+pt180u.")
            result["steps"].append("nf_post")
            theatres = snap_theatre(p, pe, co)
            result["theatre_after_nf"] = theatres
            insts = theatres[0]["orders_groups"][0]["order_instances"] if theatres else []
            result["instances_after_nf"] = insts
            if result["nf_post"].get("post_rax") != 1:
                return fail(result, "NF_POST_FAIL")
            save(result)

        # pick instance for assign: prefer one with official path_70 filled
        theatres = snap_theatre(p, pe, co)
        insts = theatres[0]["orders_groups"][0]["order_instances"] if theatres else []
        target_inst = None
        for inst in insts:
            if inst.get("path_70"):
                target_inst = inst
                break
        if target_inst is None and insts:
            target_inst = insts[-1]
        result["assign_target_instance"] = target_inst
        assign_id = (target_inst or {}).get("instance_id_244")

        # ----- 5. Assign unit 1838 -----
        if assign_id:
            cmd7, frec7 = factory_make(process_pid, b, OA["factory"], OA["vt"], OA["size"])
            result["oa_factory"] = frec7
            if not cmd7:
                return fail(result, "OA_FACTORY_FAIL")
            ubuf = mo._game_malloc(process_pid, 16)
            mo._write(process_pid, ubuf, struct.pack("<II", HANDLE_ARMY_UNIT, MEMBER_UNIT))
            mo._write(process_pid, cmd7 + 0x28, struct.pack("<QII", ubuf, 1, 1))
            mo._write(process_pid, cmd7 + 0x40, struct.pack("<II", army_handle[0], army_handle[1]))
            mo._write(process_pid, cmd7 + 0x48, struct.pack("<I", assign_id))
            raw = p.read(cmd7, OA["size"])
            result["oa_packed"] = {
                "units_vec": list(struct.unpack_from("<QII", raw, 0x28)),
                "group": list(struct.unpack_from("<II", raw, 0x40)),
                "order_index": struct.unpack_from("<I", raw, 0x48)[0],
                "ubuf": hex(ubuf),
            }
            result["oa_dry"] = dry_isvalid(process_pid, b, OA["isvalid"], cmd7)
            print("OA DRY", result["oa_dry"], result["oa_packed"])
            if result["oa_dry"].get("isvalid") != 1:
                result["oa_skipped"] = True
                save(result)
            else:
                result["oa_post"] = do_post(process_pid, b, cmd7, "t195 COrderAssignCommand unit 1838 authorized by pt181u+pt180u.")
                result["steps"].append("oa_post")
                theatres = snap_theatre(p, pe, co)
                result["theatre_after_oa"] = theatres
                result["instances_after_oa"] = theatres[0]["orders_groups"][0]["order_instances"] if theatres else []
                if result["oa_post"].get("post_rax") != 1:
                    return fail(result, "OA_POST_FAIL")
                save(result)
        else:
            result["oa_skipped"] = True
            result["oa_skip_reason"] = "NO_INSTANCE"

        # ----- 6. Leader-to-unit dry-run (no post unless valid) -----
        if u_spare:
            cmd8, frec8 = factory_make(process_pid, b, SL["factory"], SL["vt"], SL["size"])
            result["sl_unit_factory"] = frec8
            if cmd8:
                mo._write(process_pid, cmd8 + 0x28, struct.pack("<II", HANDLE_LEADER, LEADER_UNIT_TRY))
                mo._write(process_pid, cmd8 + 0x30, struct.pack("<II", HANDLE_ARMY_UNIT, SPARE_UNIT))
                mo._write(process_pid, cmd8 + 0x38, struct.pack("<I", 0))
                result["sl_unit_packed"] = {"leader": [HANDLE_LEADER, LEADER_UNIT_TRY], "group": [HANDLE_ARMY_UNIT, SPARE_UNIT]}
                result["sl_unit_dry"] = dry_isvalid(process_pid, b, SL["isvalid"], cmd8)
                print("SL UNIT DRY", result["sl_unit_dry"])
                if result["sl_unit_dry"].get("isvalid") == 1:
                    result["sl_unit_post"] = do_post(process_pid, b, cmd8, "t195 CSetArmyLeaderCommand 314 -> unit 1846 authorized by pt181u+pt180u.")
                    result["steps"].append("sl_unit_post")
                else:
                    result["sl_unit_skipped"] = True
                    result["sl_unit_skip_reason"] = "ISVALID_FALSE"
                save(result)

        # ----- 7. Brief 1x for 1829 type/target/eta, then re-pause. Do this BEFORE Execute. -----
        s1829 = snap_unit(p, pe, find_unit(p, co, MOVE_UNIT) or u1829)
        result["unit_1829_before_1x"] = s1829
        cmd9, frec9 = factory_make(process_pid, b, PG["factory"], PG["vt"], PG["size"])
        result["pause_unpause_factory"] = frec9
        if not cmd9:
            return fail(result, "PAUSEGAME_FACTORY_FAIL")
        mo._write(process_pid, cmd9 + 0x48, struct.pack("<BB", 0, 0))  # unpause, always apply
        result["unpause_dry"] = dry_isvalid(process_pid, b, PG["isvalid"], cmd9)
        if result["unpause_dry"].get("isvalid") != 1:
            return fail(result, "UNPAUSE_ISVALID_FALSE")
        result["unpause_post"] = do_post(process_pid, b, cmd9, "t195 CPauseGame unpause for 1829 contrast authorized by pt181u+pt180u.")
        result["steps"].append("unpause")
        if result["unpause_post"].get("post_rax") != 1:
            return fail(result, "UNPAUSE_POST_FAIL")
        time.sleep(0.2)
        pause, speed = pause_speed(p, idler, gs)
        result["after_unpause"] = {"pause": pause, "speed": speed}
        if pause == 1:
            result["unpause_no_effect"] = True
        else:
            unpaused = True
        # poll
        t0 = time.time()
        polls = []
        contrast = None
        start_tick = None
        if isinstance(date, dict):
            start_tick = date.get("hour_tick")
        while time.time() - t0 < 40:
            tick_now = None
            try:
                summary = read_campaign_summary(p, gs)
                d2 = (summary.get("verified") or {}).get("date_full") or {}
                tick_now = d2.get("hour_tick") if isinstance(d2, dict) else None
            except Exception:
                pass
            snap = snap_unit(p, pe, find_unit(p, co, MOVE_UNIT) or u1829)
            rec = {"t": round(time.time() - t0, 3), "pause": p.read(idler + 0x6C1, 1)[0],
                   "tick": tick_now, "unit": snap}
            polls.append(rec)
            if snap and (snap["commandlist_size"] > 0 or snap["progress"] > 0 or snap["full_path"] or (snap["province"] != MOVE_FROM)):
                contrast = snap
                break
            if start_tick and tick_now and tick_now - start_tick >= 12:
                break
            time.sleep(0.15)
        result["polls_1x_n"] = len(polls)
        result["polls_1x_head"] = polls[:3]
        result["polls_1x_tail"] = polls[-3:]
        result["contrast_1x"] = contrast
        # re-pause immediately
        cmd10, frec10 = factory_make(process_pid, b, PG["factory"], PG["vt"], PG["size"])
        result["repause_factory"] = frec10
        if cmd10:
            mo._write(process_pid, cmd10 + 0x48, struct.pack("<BB", 1, 0))
            result["repause_dry"] = dry_isvalid(process_pid, b, PG["isvalid"], cmd10)
            result["repause_post"] = do_post(process_pid, b, cmd10, "t195 CPauseGame restore official pause authorized by pt181u+pt180u.")
            result["steps"].append("repause")
            time.sleep(0.3)
            pause, speed = pause_speed(p, idler, gs)
            result["after_repause"] = {"pause": pause, "speed": speed}
            if pause == 1:
                unpaused = False
        result["unit_1829_after_1x"] = snap_unit(p, pe, find_unit(p, co, MOVE_UNIT) or u1829)
        save(result)
        if not still_paused(p, idler, gs)[0]:
            return fail(result, "FAILED_TO_REPAUSE")

        # ----- 8. Execute while paused (no 1x after) -----
        theatres = snap_theatre(p, pe, co)
        insts = theatres[0]["orders_groups"][0]["order_instances"] if theatres else []
        exec_inst = None
        for inst in insts:
            if inst.get("path_70"):
                exec_inst = inst
                break
        if exec_inst is None and insts:
            exec_inst = insts[0]
        result["execute_target"] = exec_inst
        if exec_inst and still_paused(p, idler, gs)[0]:
            cmd11, frec11 = factory_make(process_pid, b, EX["factory"], EX["vt"], EX["size"])
            result["ex_factory"] = frec11
            if not cmd11:
                return fail(result, "EX_FACTORY_FAIL")
            mo._write(process_pid, cmd11 + 0x28, struct.pack("<II", army_handle[0], army_handle[1]))
            mo._write(process_pid, cmd11 + 0x30, struct.pack("<I", exec_inst["instance_id_244"]))
            mo._write(process_pid, cmd11 + 0x34, struct.pack("<BB", 1, 0))  # execute_order=1, all=0
            result["ex_packed"] = {"group": army_handle, "order_index": exec_inst["instance_id_244"], "execute_order": 1}
            result["ex_dry"] = dry_isvalid(process_pid, b, EX["isvalid"], cmd11)
            print("EX DRY", result["ex_dry"])
            if result["ex_dry"].get("isvalid") != 1:
                result["ex_skipped"] = True
                save(result)
            else:
                result["ex_post"] = do_post(process_pid, b, cmd11, "t195 COrderExecuteCommand while paused authorized by pt181u+pt180u.")
                result["steps"].append("ex_post")
                theatres = snap_theatre(p, pe, co)
                result["theatre_after_ex"] = theatres
                result["instances_after_ex"] = theatres[0]["orders_groups"][0]["order_instances"] if theatres else []
                result["unit_1838_after_ex"] = snap_unit(p, pe, find_unit(p, co, MEMBER_UNIT) or u1838)
                ok_p, pause, speed = still_paused(p, idler, gs)
                result["after_ex_pause"] = {"pause": pause, "speed": speed}
                if not ok_p:
                    return fail(result, "UNPAUSED_AFTER_EXECUTE")
                if result["ex_post"].get("post_rax") != 1:
                    return fail(result, "EX_POST_FAIL")
                save(result)
        else:
            result["ex_skipped"] = True
            result["ex_skip_reason"] = "NO_INSTANCE_OR_NOT_PAUSED"

        # final snaps
        theatres = snap_theatre(p, pe, co)
        result["theatre_final"] = theatres
        result["unit_1829_final"] = snap_unit(p, pe, find_unit(p, co, MOVE_UNIT))
        result["unit_1838_final"] = snap_unit(p, pe, find_unit(p, co, MEMBER_UNIT))
        result["unit_spare_final"] = snap_unit(p, pe, find_unit(p, co, SPARE_UNIT))
        summary = read_campaign_summary(p, gs)
        result["date_final"] = (summary.get("verified") or {}).get("date_full")
        ok_p, pause, speed = still_paused(p, idler, gs)
        result["final_pause"] = {"pause": pause, "speed": speed, "ok": ok_p}
        result["health_final"] = process_health(EXPECTED_PID)
        result["ok"] = bool(ok_p and result["health_final"].get("alive") and "move_post" in result["steps"])
        result["allow_post_final"] = allow_post()
        save(result)
        print(json.dumps({
            "ok": result["ok"],
            "error": result.get("error"),
            "steps": result["steps"],
            "session": result["session"],
            "date_final": result.get("date_final"),
            "army_handle": result.get("army_handle"),
            "ag_handle": result.get("ag_handle"),
            "root_instance": result.get("root_instance"),
            "instances_after_nf": result.get("instances_after_nf") or result.get("instances_after_oa") or result.get("instances_after_ex"),
            "oa_dry": result.get("oa_dry"),
            "nf_dry": result.get("nf_dry"),
            "ex_dry": result.get("ex_dry"),
            "sl_unit_dry": result.get("sl_unit_dry"),
            "contrast_1x": result.get("contrast_1x"),
            "unit_1829_final": result.get("unit_1829_final"),
            "unit_1838_final": result.get("unit_1838_final"),
            "final_pause": result.get("final_pause"),
            "health_final": result.get("health_final"),
            "skipped": {k: result[k] for k in result if k.endswith("_skipped") or k.endswith("_skip_reason")},
        }, indent=2, ensure_ascii=False, default=str))
    except Exception as e:
        result["ok"] = False
        result["error"] = "EXCEPTION"
        result["exception"] = f"{type(e).__name__}: {e}"
        result["traceback"] = traceback.format_exc()
        save(result)
        print(json.dumps({k: result[k] for k in result if k != "traceback"}, indent=2, ensure_ascii=False, default=str))
        print(result["traceback"])
    finally:
        close_gates()
        # If we left the game unpaused, try one official re-pause.
        try:
            if unpaused and p is not None and b is not None and idler and p.read(idler + 0x6C1, 1)[0] != 1:
                cmdp, _ = factory_make(process_pid, b, PG["factory"], PG["vt"], PG["size"])
                if cmdp:
                    mo._write(process_pid, cmdp + 0x48, struct.pack("<BB", 1, 0))
                    do_post(process_pid, b, cmdp, "t195 emergency CPauseGame restore authorized by pt181u+pt180u.")
                    time.sleep(0.3)
                    result["emergency_repause"] = {"pause": p.read(idler + 0x6C1, 1)[0]}
                    save(result)
        except Exception as e:
            result["emergency_repause_error"] = str(e)
            save(result)
        try:
            data = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else result
            data["gate_closed"] = {"allow_post_after_close": allow_post(), "marker_exists": MARKER.exists()}
            if p is not None and idler:
                data["gate_closed"]["pause"] = p.read(idler + 0x6C1, 1)[0]
            OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
            print("GATE_CLOSED", json.dumps(data["gate_closed"]))
        except Exception as e:
            print("GATE_CLOSE_STATUS_WRITE_FAIL", e)
        if p is not None:
            try:
                p.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
