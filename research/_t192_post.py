# research/_t192_post.py
# Create one ETH COrdersGroup with unit 1838 via COrderGroupCommand, then optionally
# CSetArmyLeaderCommand. Authorized pt180u. Pause/1x only. Close gate after.
from __future__ import annotations
import json, os, struct, sys, time, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
os.environ.pop("CLAUSEWITZ_ALLOW_WRITE", None)

from pe import PE
from mem import Proc, find_pid as mem_find_pid
from gamestate import detect_session, resolve_player_country, _rtti_name_from_vtable, read_campaign_summary
from config import allow_post
from process import Backend
from handle import resolve_handle, HANDLE_TYPE_ARMY
import move_order as mo
import post_abi

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
MARKER = ROOT / "research" / "safe_land_tool_gate.OPEN"
LEGACY = ROOT / "research" / "strategic_only_tool_gate.OPEN"
OUT = ROOT / "research" / "t192_post.json"

EXPECTED_PID = 26976
EXPECTED_GS = 0x26C259D0FF0
EXPECTED_CO = 0x26C4B672530
KEEP_UNIT = 1829
KEEP_PATH = [8036]
MEMBER_UNIT = 1838  # rear, not the t191 mover
THEATRE_TYPE = 67
THEATRE_ID = 43
G_IDLER = 0x33DDB08

# 1.19.5 bound
OG = {
    "factory": 0x18D0140,
    "idx": 2983,
    "vt": 0x2A84560,
    "isvalid": 0x18DF050,
    "execute": 0x18D6560,
    "size": 0x60,
}
SL = {
    "factory": 0x18D0C10,
    "idx": 3369,
    "vt": 0x2A85E20,
    "isvalid": 0x18E0540,
    "execute": 0x18DB330,
    "size": 0x40,
}


def is_ptr(x):
    return type(x) is int and 0x10000 < x < 0x7FFFFFFFFFFF


def open_gates():
    os.environ["CLAUSEWITZ_ALLOW_POST"] = "1"
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    MARKER.write_text(
        "t192 one-shot COrderGroupCommand (+ optional CSetArmyLeaderCommand) authorized by pt180u.\n"
        "Scope: ETH theatre 43, unit 1838 into a new orders_group; keep 1829 path.\n"
        "Pause/1x only. Close after this block.\n",
        encoding="utf-8",
    )
    if LEGACY.exists():
        LEGACY.unlink()


def close_gates():
    os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
    os.environ.pop("CLAUSEWITZ_ALLOW_WRITE", None)
    if MARKER.exists():
        MARKER.unlink()
    if LEGACY.exists():
        LEGACY.unlink()


def process_health(pid: int) -> dict:
    import ctypes
    from ctypes import wintypes as wt
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.OpenProcess.restype = wt.HANDLE
    k.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
    k.GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
    k.GetExitCodeProcess.restype = wt.BOOL
    k.CloseHandle.argtypes = [wt.HANDLE]
    STILL_ACTIVE = 259
    h = k.OpenProcess(0x1000 | 0x0400, False, pid)
    if not h:
        return {"alive": False, "exit_code": None, "open_err": ctypes.get_last_error()}
    try:
        code = wt.DWORD(0)
        k.GetExitCodeProcess(h, ctypes.byref(code))
        return {"alive": int(code.value) == STILL_ACTIVE, "exit_code": int(code.value)}
    finally:
        k.CloseHandle(h)


def msvc_string(p, a):
    blob = p.read(a, 32)
    n, cap = struct.unpack_from("<QQ", blob, 16)
    if not 0 <= n <= 1024 or cap < n:
        return None
    raw = blob[:n] if cap <= 15 else p.read(struct.unpack_from("<Q", blob)[0], n)
    return raw.decode("utf-8", "replace")


def pdx(p, a):
    data, cap, size = struct.unpack("<QII", p.read(a, 16))
    return {"data": data, "cap": cap, "size": size}


def ptr_array(p, a, bound=4096):
    h = pdx(p, a)
    if not 0 <= h["size"] <= h["cap"] <= max(bound, 100):
        return [], h
    if h["size"] and not is_ptr(h["data"]):
        return [], h
    return [struct.unpack("<Q", p.read(h["data"] + 8 * j, 8))[0] for j in range(h["size"])], h


def cls(p, pe, a):
    if not is_ptr(a):
        return None
    vt = struct.unpack("<Q", p.read(a, 8))[0]
    if not p.base <= vt < p.base + p.image_size:
        return None
    return _rtti_name_from_vtable(pe, vt - p.base)


def unit_path(p, ap):
    h = pdx(p, ap + 0x200)
    if h["size"] <= 0 or not is_ptr(h["data"]) or h["size"] > 64:
        return []
    raw = p.read(h["data"], h["size"] * 4)
    return list(struct.unpack("<" + "I" * h["size"], raw))


def snapshot_theatre(p, pe, co):
    theatres, th = ptr_array(p, co + 0x168, 64)
    out = []
    for tp in theatres:
        rec = {
            "ptr": hex(tp),
            "class": cls(p, pe, tp),
            "handle_type": struct.unpack("<I", p.read(tp + 0x8, 4))[0] if is_ptr(tp) else None,
            "id": struct.unpack("<I", p.read(tp + 0xC, 4))[0] if is_ptr(tp) else None,
            "name": msvc_string(p, tp + 0x18) if is_ptr(tp) else None,
        }
        if is_ptr(tp):
            units, uh = ptr_array(p, tp + 0x68, 4096)
            rec["unit_ids"] = [struct.unpack("<I", p.read(u + 0x1C, 4))[0] for u in units if is_ptr(u)]
            ogs, oh = ptr_array(p, tp + 0x80, 256)
            rec["orders_group_hdr"] = {k: (hex(v) if k == "data" else v) for k, v in oh.items()}
            rec["orders_groups"] = []
            for gp in ogs:
                rec["orders_groups"].append(snapshot_orders_group(p, pe, gp))
            fms, fh = ptr_array(p, tp + 0x98, 256)
            rec["field_marshal_n"] = len(fms)
            tgs, tgh = ptr_array(p, tp + 0xC8, 256)
            rec["theater_group_n"] = len(tgs)
        out.append(rec)
    return out


def snapshot_orders_group(p, pe, gp):
    rec = {
        "ptr": hex(gp),
        "class": cls(p, pe, gp),
        "handle_type": struct.unpack("<I", p.read(gp + 0x8, 4))[0] if is_ptr(gp) else None,
        "id": struct.unpack("<I", p.read(gp + 0xC, 4))[0] if is_ptr(gp) else None,
        "name": msvc_string(p, gp + 0x160) if is_ptr(gp) else None,
        "fm_flag_39": p.read(gp + 0x39, 1)[0] if is_ptr(gp) else None,
    }
    if not is_ptr(gp):
        return rec
    mems, mh = ptr_array(p, gp + 0x50, 256)
    rec["members_hdr"] = {k: (hex(v) if k == "data" else v) for k, v in mh.items()}
    rec["member_unit_ids"] = []
    rec["member_classes"] = []
    for mp in mems:
        rec["member_classes"].append(cls(p, pe, mp))
        if is_ptr(mp):
            rec["member_unit_ids"].append(struct.unpack("<I", p.read(mp + 0x1C, 4))[0])
    leader = struct.unpack("<Q", p.read(gp + 0x88, 8))[0]
    rec["leader_ptr"] = hex(leader)
    rec["leader_class"] = cls(p, pe, leader)
    if is_ptr(leader):
        rec["leader_handle_type"] = struct.unpack("<I", p.read(leader + 0x8, 4))[0]
        rec["leader_id"] = struct.unpack("<I", p.read(leader + 0xC, 4))[0]
    ois, oih = ptr_array(p, gp + 0x98, 256)
    rec["order_instance_n"] = len(ois)
    return rec


def snapshot_leaders(p, pe, co):
    cc = struct.unpack("<Q", p.read(co + 0xFF0, 8))[0]
    leaders, _ = ptr_array(p, cc + 0x70, 512)
    out = []
    for lp in leaders:
        rec = {
            "ptr": hex(lp),
            "class": cls(p, pe, lp),
            "handle_type": struct.unpack("<I", p.read(lp + 0x8, 4))[0],
            "leader_id": struct.unpack("<I", p.read(lp + 0xC, 4))[0],
            "deployed": p.read(lp + 0x1068, 1)[0],
            "name_key": msvc_string(p, lp + 0x20),
        }
        # official assignment pointer? +0x88 was group leader slot, not here
        out.append(rec)
    return out


def find_unit(p, co, uid):
    arr, _ = ptr_array(p, co + 0x290, 4096)
    for ap in arr:
        if struct.unpack("<I", p.read(ap + 0x1C, 4))[0] == uid:
            return ap
    return 0


def factory_make(pid, b, factory_rva, expect_vt, size_note=None):
    made = mo._remote(pid, b.image_base + factory_rva, wait_ms=5000)
    cmd = made.get("rax") or 0
    if made.get("wait") != 0 or cmd < 0x10000:
        return {"ok": False, "result": "FACTORY_FAIL", "call": made}
    vt = mo._u64(b, cmd) - b.image_base
    if vt != expect_vt:
        return {"ok": False, "result": "FACTORY_VT_MISMATCH", "vt": hex(vt), "expect": hex(expect_vt), "cmd": hex(cmd)}
    return {"ok": True, "cmd": cmd, "call": made, "vt": hex(vt)}


def main():
    result = {
        "authorized_by": ["pt180u"],
        "keep_unit": KEEP_UNIT,
        "member_unit": MEMBER_UNIT,
        "theatre": {"type": THEATRE_TYPE, "id": THEATRE_ID},
        "stay_paused": True,
        "never_5x": True,
        "og_cmd": {k: (hex(v) if isinstance(v, int) and v > 0x100 else v) for k, v in OG.items()},
        "sl_cmd": {k: (hex(v) if isinstance(v, int) and v > 0x100 else v) for k, v in SL.items()},
    }
    p = None
    try:
        process_pid = mem_find_pid("hoi4.exe")
        if process_pid != EXPECTED_PID:
            result.update({"ok": False, "error": "PID_MISMATCH", "process_pid": process_pid})
            OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
            return
        result["health_before"] = process_health(process_pid)
        if not result["health_before"].get("alive"):
            result.update({"ok": False, "error": "PROCESS_NOT_ALIVE"})
            OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
            return

        p = Proc(process_pid)
        pe = PE(EXE)
        session = detect_session(p, pe)
        if not session.get("in_game"):
            result.update({"ok": False, "error": "NOT_IN_GAME"})
            OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
            return
        gs = int(session["signals"]["gs_ptr"], 16)
        res = resolve_player_country(p, gs)
        co = int(res["country_ptr"], 16)
        summary = read_campaign_summary(p, gs)
        ver = summary.get("verified") or {}
        date = ver.get("date_full") or ver.get("date") or {}
        idler = int(session["signals"].get("idler_ptr") or "0", 16)
        pause = p.read(idler + 0x6C1, 1)[0] if idler else None
        speed_index = struct.unpack("<i", p.read(gs + 0x4BC, 4))[0]
        sinfo = {
            "process_pid": process_pid,
            "gs": hex(gs),
            "country": hex(co),
            "player_index": res.get("player_index"),
            "date": date,
            "pause_flag_6c1": pause,
            "speed_index": speed_index,
            "gs_matches": gs == EXPECTED_GS,
            "co_matches": co == EXPECTED_CO,
        }
        result["session_before"] = sinfo
        if not (
            sinfo["gs_matches"] and sinfo["co_matches"] and res.get("player_index") == 44
            and pause == 1 and speed_index == 0
            and isinstance(date, dict) and date.get("ui") == "1936-01-01" and date.get("ui_hour") == 12
        ):
            result.update({"ok": False, "error": "SESSION_GUARD_FAIL"})
            OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
            return

        # keep path + member unit + theatre
        u1829 = find_unit(p, co, KEEP_UNIT)
        u1838 = find_unit(p, co, MEMBER_UNIT)
        if not u1829 or not u1838:
            result.update({"ok": False, "error": "UNIT_MISSING"})
            OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
            return
        path1829 = unit_path(p, u1829)
        result["keep_path_before"] = path1829
        if path1829 != KEEP_PATH:
            result.update({"ok": False, "error": "KEEP_PATH_CHANGED", "path": path1829})
            OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
            return

        theatres_before = snapshot_theatre(p, pe, co)
        leaders_before = snapshot_leaders(p, pe, co)
        result["theatre_before"] = theatres_before
        result["leaders_before_summary"] = {
            "n": len(leaders_before),
            "ids": [x["leader_id"] for x in leaders_before],
            "handle_types": sorted(set(x["handle_type"] for x in leaders_before)),
            "deployed_nonzero": [x["leader_id"] for x in leaders_before if x["deployed"]],
            "first": leaders_before[0] if leaders_before else None,
        }
        if (
            not theatres_before
            or theatres_before[0].get("id") != THEATRE_ID
            or theatres_before[0].get("handle_type") != THEATRE_TYPE
            or MEMBER_UNIT not in (theatres_before[0].get("unit_ids") or [])
            or theatres_before[0].get("orders_groups")
        ):
            result.update({"ok": False, "error": "THEATRE_UNEXPECTED", "theatre": theatres_before})
            OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
            return
        if not leaders_before or result["leaders_before_summary"]["deployed_nonzero"]:
            result.update({"ok": False, "error": "LEADERS_UNEXPECTED"})
            OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
            return

        leader = leaders_before[0]
        result["chosen_leader"] = leader
        result["member_unit_ptr"] = hex(u1838)
        result["member_unit_province"] = struct.unpack("<I", p.read(u1838 + 0x28, 4))[0]

        b = Backend()
        # ---- dry-run COrderGroupCommand ----
        made = factory_make(process_pid, b, OG["factory"], OG["vt"])
        result["og_factory"] = {k: v for k, v in made.items() if k != "call"} | {"wait": (made.get("call") or {}).get("wait")}
        if not made.get("ok"):
            result.update({"ok": False, "error": "OG_FACTORY_FAIL", "og_factory": made})
            OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
            return
        cmd = made["cmd"]
        buf = mo._game_malloc(process_pid, 16)
        mo._write(process_pid, buf, struct.pack("<II", 0x33, MEMBER_UNIT))
        # flag +0x28 = 0; vector at +0x30; theatre handle +0x48; groups 0
        mo._write(process_pid, cmd + 0x28, bytes(8))  # flag + pad
        mo._write(process_pid, cmd + 0x30, struct.pack("<QII", buf, 1, 1))
        mo._write(process_pid, cmd + 0x48, struct.pack("<II", THEATRE_TYPE, THEATRE_ID))
        mo._write(process_pid, cmd + 0x50, bytes(16))  # theater_group + army_group
        # dump packed command
        raw = p.read(cmd, OG["size"])
        result["og_packed"] = {
            "cmd": hex(cmd),
            "buf": hex(buf),
            "flag_28": raw[0x28],
            "vec": struct.unpack_from("<QII", raw, 0x30),
            "theatre": struct.unpack_from("<II", raw, 0x48),
            "theater_group": struct.unpack_from("<II", raw, 0x50),
            "army_group": struct.unpack_from("<II", raw, 0x58),
        }
        valid = mo._remote(process_pid, b.image_base + OG["isvalid"], {"rcx": cmd}, wait_ms=5000)
        isvalid = valid["rax"] & 0xFF if valid.get("wait") == 0 else None
        result["og_dry_isvalid"] = {"wait": valid.get("wait"), "rax": valid.get("rax"), "isvalid": isvalid}
        if valid.get("wait") != 0 or isvalid != 1:
            result.update({"ok": False, "error": "OG_ISVALID_FALSE"})
            OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
            return

        # still paused / alive
        if mem_find_pid("hoi4.exe") != EXPECTED_PID or process_health(EXPECTED_PID).get("alive") is not True:
            result.update({"ok": False, "error": "PROCESS_LOST_AFTER_OG_DRY"})
            OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
            return
        if p.read(idler + 0x6C1, 1)[0] != 1 or struct.unpack("<i", p.read(gs + 0x4BC, 4))[0] != 0:
            result.update({"ok": False, "error": "PAUSE_OR_SPEED_CHANGED"})
            OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
            return

        open_gates()
        result["allow_post_at_post"] = allow_post()
        if not allow_post():
            result.update({"ok": False, "error": "ALLOW_POST_STILL_FALSE"})
            OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
            return

        sess = mo._u64(b, b.image_base + post_abi.G_SESSION)
        posted = mo._remote(process_pid, b.image_base + post_abi.FN_CMD_QUEUE_POST, {"rcx": sess, "rdx": cmd, "r8": 1}, wait_ms=8000)
        result["og_post"] = {
            "wait": posted.get("wait"),
            "rax": posted.get("rax"),
            "post_rax": (posted.get("rax") or 0) & 0xFF,
            "elapsed_ms": posted.get("elapsed_ms"),
            "stub_freed": posted.get("stub_freed"),
        }
        time.sleep(0.5)
        result["health_after_og"] = process_health(EXPECTED_PID)
        theatres_after = snapshot_theatre(p, pe, co)
        result["theatre_after"] = theatres_after
        result["keep_path_after_og"] = unit_path(p, u1829)
        result["og_created"] = bool(theatres_after and theatres_after[0].get("orders_groups"))
        result["new_groups"] = (theatres_after[0].get("orders_groups") if theatres_after else []) or []

        # ---- optional SetArmyLeader if a group exists ----
        result["leader_attempted"] = False
        if result["og_created"] and result["health_after_og"].get("alive") and result["keep_path_after_og"] == KEEP_PATH:
            group = result["new_groups"][0]
            gtype, gid = group.get("handle_type"), group.get("id")
            ltype, lid = leader["handle_type"], leader["leader_id"]
            if gtype and gid and ltype and lid:
                result["leader_attempted"] = True
                made2 = factory_make(process_pid, b, SL["factory"], SL["vt"])
                result["sl_factory"] = {k: v for k, v in made2.items() if k != "call"}
                if made2.get("ok"):
                    cmd2 = made2["cmd"]
                    mo._write(process_pid, cmd2 + 0x28, struct.pack("<II", int(ltype), int(lid)))
                    mo._write(process_pid, cmd2 + 0x30, struct.pack("<II", int(gtype), int(gid)))
                    mo._write(process_pid, cmd2 + 0x38, struct.pack("<I", 0))  # do not deploy HQ
                    raw2 = p.read(cmd2, SL["size"])
                    result["sl_packed"] = {
                        "cmd": hex(cmd2),
                        "leader": struct.unpack_from("<II", raw2, 0x28),
                        "group": struct.unpack_from("<II", raw2, 0x30),
                        "deploy_hq": struct.unpack_from("<I", raw2, 0x38)[0],
                    }
                    valid2 = mo._remote(process_pid, b.image_base + SL["isvalid"], {"rcx": cmd2}, wait_ms=5000)
                    isvalid2 = valid2["rax"] & 0xFF if valid2.get("wait") == 0 else None
                    result["sl_dry_isvalid"] = {"wait": valid2.get("wait"), "rax": valid2.get("rax"), "isvalid": isvalid2}
                    if isvalid2 == 1 and p.read(idler + 0x6C1, 1)[0] == 1:
                        posted2 = mo._remote(
                            process_pid,
                            b.image_base + post_abi.FN_CMD_QUEUE_POST,
                            {"rcx": sess, "rdx": cmd2, "r8": 1},
                            wait_ms=8000,
                        )
                        result["sl_post"] = {
                            "wait": posted2.get("wait"),
                            "rax": posted2.get("rax"),
                            "post_rax": (posted2.get("rax") or 0) & 0xFF,
                        }
                        time.sleep(0.5)
                    else:
                        result["sl_post"] = {"skipped": True, "reason": "ISVALID_FALSE_OR_UNPAUSED"}
        result["health_after"] = process_health(EXPECTED_PID)
        result["theatre_final"] = snapshot_theatre(p, pe, co)
        result["leaders_after"] = snapshot_leaders(p, pe, co)
        result["keep_path_final"] = unit_path(p, find_unit(p, co, KEEP_UNIT) or u1829)
        result["still_paused"] = p.read(idler + 0x6C1, 1)[0] == 1
        result["speed_index_after"] = struct.unpack("<i", p.read(gs + 0x4BC, 4))[0]
        # compact leaders after
        result["leaders_after_summary"] = {
            "n": len(result["leaders_after"]),
            "deployed_nonzero": [x for x in result["leaders_after"] if x["deployed"]],
        }
        result["ok"] = bool(
            result["health_after"].get("alive")
            and result.get("og_created")
            and result["keep_path_final"] == KEEP_PATH
            and result["still_paused"]
            and result["speed_index_after"] == 0
        )
        result["result"] = "ORDERS_GROUP_CREATED" if result.get("og_created") else "POSTED_BUT_NO_GROUP"
        OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
        print(json.dumps({
            "ok": result["ok"],
            "result": result.get("result"),
            "og_dry_isvalid": result.get("og_dry_isvalid"),
            "og_post": result.get("og_post"),
            "og_created": result.get("og_created"),
            "new_groups": result.get("theatre_final", result.get("theatre_after"))[0].get("orders_groups") if result.get("theatre_final") or result.get("theatre_after") else None,
            "leader_attempted": result.get("leader_attempted"),
            "sl_dry_isvalid": result.get("sl_dry_isvalid"),
            "sl_post": result.get("sl_post"),
            "leaders_deployed_after": result["leaders_after_summary"]["deployed_nonzero"],
            "keep_path_final": result.get("keep_path_final"),
            "still_paused": result.get("still_paused"),
            "speed_index_after": result.get("speed_index_after"),
            "health_after": result.get("health_after"),
        }, indent=2, ensure_ascii=False, default=str))
    except Exception as e:
        result["ok"] = False
        result["error"] = "EXCEPTION"
        result["exception"] = f"{type(e).__name__}: {e}"
        result["traceback"] = traceback.format_exc()
        OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
        print(json.dumps({k: result[k] for k in result if k != "traceback"}, indent=2, ensure_ascii=False, default=str))
        print(result["traceback"])
    finally:
        close_gates()
        try:
            data = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else result
            data["gate_closed"] = {"allow_post_after_close": allow_post(), "marker_exists": MARKER.exists()}
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
