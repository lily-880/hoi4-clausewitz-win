# research/_t191_move_post.py
# One-shot interior ETH move via existing move_order factory. Authorized pt180u.
# Unit 1829: province 5010 -> adjacent ETH interior 8036. Pause/1x only. Close gate after.
from __future__ import annotations
import json, os, struct, sys, time, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))

# Start closed; open only for the live Post.
os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
os.environ.pop("CLAUSEWITZ_ALLOW_WRITE", None)

from pe import PE
from mem import Proc, find_pid as mem_find_pid
from gamestate import detect_session, resolve_player_country, _rtti_name_from_vtable, read_campaign_summary
from input_loaded_fields import LoadedReader, province_adjacencies, country_tag
from province import resolve_province
from config import allow_post
from process import Backend, find_pid as proc_find_pid
from handle import resolve_handle, HANDLE_TYPE_ARMY
import move_order as mo
import post_abi

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
MARKER = ROOT / "research" / "safe_land_tool_gate.OPEN"
LEGACY = ROOT / "research" / "strategic_only_tool_gate.OPEN"
OUT = ROOT / "research" / "t191_move_post.json"
TOKEN_MAP = ROOT / "research" / "t163_script_token_map.json"

EXPECTED_PID = 26976
EXPECTED_GS = 0x26C259D0FF0
EXPECTED_CO = 0x26C4B672530
UNIT_ID = 1829
DEST = 8036
SRC = 5010
G_IDLER = 0x33DDB08


def is_ptr(x):
    return type(x) is int and 0x10000 < x < 0x7FFFFFFFFFFF


def open_gates():
    os.environ["CLAUSEWITZ_ALLOW_POST"] = "1"
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    MARKER.write_text(
        "t191 one-shot CMoveCommand (factory 1402) authorized by pt180u.\n"
        "Scope: ETH unit 1829 move 5010 -> adjacent interior 8036.\n"
        "Pause/1x only. Close after this Post.\n",
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


def token_name(tok, table):
    if table is None:
        return None
    s = str(tok)
    hx = hex(tok)
    return table.get(s) or table.get(hx) or table.get(hx.lower()) or table.get(f"0x{tok:x}") or table.get(f"0x{tok:X}")


def snapshot_unit(p, pe, gs, army_ptr, tokens):
    def q(a):
        return struct.unpack("<Q", p.read(a, 8))[0]

    def u32(a):
        return struct.unpack("<I", p.read(a, 4))[0]

    def i32(a):
        return struct.unpack("<i", p.read(a, 4))[0]

    def u8(a):
        return p.read(a, 1)[0]

    def cls(a):
        if not is_ptr(a):
            return None
        vt = q(a)
        if not p.base <= vt < p.base + p.image_size:
            return None
        return _rtti_name_from_vtable(pe, vt - p.base)

    def pdx(a):
        data, cap, size = struct.unpack("<QII", p.read(a, 16))
        return {"data": hex(data), "cap": cap, "size": size, "data_raw": data}

    def u32_array(a, bound=64):
        h = pdx(a)
        if not 0 <= h["size"] <= h["cap"] <= bound:
            return [], {k: v for k, v in h.items() if k != "data_raw"}
        if h["size"] and not is_ptr(h["data_raw"]):
            return [], {k: v for k, v in h.items() if k != "data_raw"}
        if h["size"] == 0:
            return [], {k: v for k, v in h.items() if k != "data_raw"}
        raw = p.read(h["data_raw"], h["size"] * 4)
        vals = list(struct.unpack("<" + "I" * h["size"], raw))
        return vals, {k: v for k, v in h.items() if k != "data_raw"}

    path, ph = u32_array(army_ptr + 0x200, 64)
    full_path, fh = u32_array(army_ptr + 0x220, 64)
    cl = pdx(army_ptr + 0x2C0)
    elems = []
    if 0 < cl["size"] <= cl["cap"] <= 32 and is_ptr(cl["data_raw"]):
        for j in range(cl["size"]):
            cp = q(cl["data_raw"] + 8 * j)
            elem = {"ptr": hex(cp), "class": cls(cp)}
            if is_ptr(cp):
                plus8 = u32(cp + 8)
                elem["plus8"] = plus8
                elem["plus8_hex"] = hex(plus8)
                elem["plus8_token"] = token_name(plus8, tokens)
                # a few more dwords for learning, not for invention
                elem["dwords_0_40"] = [u32(cp + off) for off in range(0, 0x40, 4)]
                elem["vt_rva"] = hex(q(cp) - p.base) if p.base <= q(cp) < p.base + p.image_size else None
            elems.append(elem)
    sess = q(p.base + post_abi.G_SESSION)
    server = q(sess + post_abi.CSession_SERVER) if is_ptr(sess) else 0
    return {
        "army_ptr": hex(army_ptr),
        "handle_type": u32(army_ptr + 0x18),
        "unit_id": u32(army_ptr + 0x1C),
        "province_id": u32(army_ptr + 0x28),
        "path": path,
        "path_hdr": ph,
        "full_path": full_path,
        "full_path_hdr": fh,
        "commandlist": {k: v for k, v in cl.items() if k != "data_raw"},
        "commandlist_elems": elems,
        "support_attack": hex(q(army_ptr + 0x1E8)),
        "previous": hex(q(army_ptr + 0x1F8)),
        "movement_progress": i32(army_ptr + 0x240),
        "retreat": u8(army_ptr + 0x24C),
        "withdraw": u8(army_ptr + 0x24D),
        "strategic_redeployment": u8(army_ptr + 0x2AF),
        "leader_id": i32(army_ptr + 0x564),
        "session": {
            "ptr": hex(sess) if sess else None,
            "drain": u32(sess + post_abi.CSession_DRAIN_COUNTER) if is_ptr(sess) else None,
            "exec": u32(sess + post_abi.CSession_EXEC_COUNTER) if is_ptr(sess) else None,
            "stage": u32(sess + post_abi.CSession_STAGE_COUNT) if is_ptr(sess) else None,
            "executing_flag": p.read(sess + post_abi.CSession_EXECUTING_FLAG, 1)[0] if is_ptr(sess) else None,
        },
        "gs_combats_size": struct.unpack("<I", p.read(gs + 0x268 + 8 + 4, 4))[0],
    }


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
        c = int(code.value)
        return {"alive": c == STILL_ACTIVE, "exit_code": c}
    finally:
        k.CloseHandle(h)


def session_guard(p, pe):
    session = detect_session(p, pe)
    if not session.get("in_game"):
        return None, {"ok": False, "error": "NOT_IN_GAME"}
    gs = int(session["signals"]["gs_ptr"], 16)
    res = resolve_player_country(p, gs)
    co = int(res["country_ptr"], 16)
    summary = read_campaign_summary(p, gs)
    ver = summary.get("verified") or {}
    date = ver.get("date_full") or ver.get("date") or {}
    idler = int(session["signals"].get("idler_ptr") or "0", 16)
    pause = p.read(idler + 0x6C1, 1)[0] if idler else None
    speed_index = struct.unpack("<i", p.read(gs + 0x4BC, 4))[0]
    info = {
        "process_pid": p.pid,
        "in_game": True,
        "tag_index": res.get("player_index"),
        "tag_ok_index_is": res.get("player_index"),
        "gs": hex(gs),
        "country": hex(co),
        "date": date,
        "hour_tick": date.get("hour_tick") if isinstance(date, dict) else None,
        "pause_flag_6c1": pause,
        "speed_index": speed_index,
        "speed_notch": ver.get("game_speed_notch"),
        "gs_matches": gs == EXPECTED_GS,
        "co_matches": co == EXPECTED_CO,
        "pid_matches": p.pid == EXPECTED_PID,
    }
    return (session, gs, res, co, info), None


def main():
    tokens = None
    if TOKEN_MAP.exists():
        raw = json.loads(TOKEN_MAP.read_text(encoding="utf-8"))
        # may be {hex: name} or list
        if isinstance(raw, dict):
            # sometimes {"entries": ...} or direct
            if all(isinstance(v, str) for v in list(raw.values())[:3]):
                tokens = raw
            elif "tokens" in raw:
                tokens = raw["tokens"]
            else:
                tokens = raw
    result = {
        "authorized_by": ["pt180u"],
        "unit_id": UNIT_ID,
        "src_province": SRC,
        "dest_province": DEST,
        "factory": {"idx": 1402, "rva": hex(mo.FACTORY_RVA), "name": "CMoveCommand"},
        "stay_paused": True,
        "never_5x": True,
    }
    gates_opened = False
    p = None
    try:
        process_pid = mem_find_pid("hoi4.exe")
        if process_pid != EXPECTED_PID:
            result.update({"ok": False, "error": "PID_MISMATCH", "process_pid": process_pid})
            OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return
        health0 = process_health(process_pid)
        result["health_before"] = health0
        if not health0.get("alive"):
            result.update({"ok": False, "error": "PROCESS_NOT_ALIVE"})
            OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return

        p = Proc(process_pid)
        pe = PE(EXE)
        guarded, err = session_guard(p, pe)
        if err:
            result.update(err)
            OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return
        session, gs, res, co, sinfo = guarded
        result["session_before"] = sinfo
        # hard guards
        date = sinfo["date"]
        if not (
            sinfo["pid_matches"]
            and sinfo["gs_matches"]
            and sinfo["co_matches"]
            and res.get("player_index") == 44
            and sinfo["pause_flag_6c1"] == 1
            and sinfo["speed_index"] == 0
            and isinstance(date, dict)
            and date.get("ui") == "1936-01-01"
            and date.get("ui_hour") == 12
        ):
            result.update({"ok": False, "error": "SESSION_GUARD_FAIL", "session": sinfo})
            OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return

        b = Backend()
        army = resolve_handle(b, HANDLE_TYPE_ARMY, UNIT_ID, b.image_base)
        if not army:
            result.update({"ok": False, "error": "ARMY_NOT_FOUND"})
            OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return
        before = snapshot_unit(p, pe, gs, army, tokens)
        result["readback_before"] = before
        if before["unit_id"] != UNIT_ID or before["province_id"] != SRC or before["path"] or before["commandlist"]["size"] != 0:
            result.update({"ok": False, "error": "UNIT_STATE_UNEXPECTED", "before": before})
            OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return

        # dest still ETH interior (controller via ETH area list)
        def ptr_array(addr, bound=4096):
            data, cap, size = struct.unpack("<QII", p.read(addr, 16))
            if not 0 <= size <= cap <= max(bound, 100) or (size and not is_ptr(data)):
                return []
            return [struct.unpack("<Q", p.read(data + 8 * j, 8))[0] for j in range(size)]

        eth_areas = set(ptr_array(co + 0x548, 4096))
        dest_ptr = resolve_province(type("B", (), {"read": p.read, "image_base": p.base})(), DEST, p.base, gs)
        dest_area = struct.unpack("<Q", p.read(dest_ptr + 0xD0, 8))[0] if is_ptr(dest_ptr) else 0
        loaded = LoadedReader(p.read, lambda a: _rtti_name_from_vtable(pe, struct.unpack("<Q", p.read(a, 8))[0] - p.base) if is_ptr(a) else None)
        src_ptr = resolve_province(type("B", (), {"read": p.read, "image_base": p.base})(), SRC, p.base, gs)
        adj = province_adjacencies(loaded, src_ptr)
        result["dest_check"] = {
            "dest_ptr": hex(dest_ptr) if dest_ptr else None,
            "dest_in_eth_areas": dest_area in eth_areas,
            "src_land_neighbors": adj["neighbors"],
            "dest_is_src_neighbor": DEST in adj["neighbors"],
            "river": (adj["has_river_crossing"] or {}).get(str(DEST), False),
        }
        if DEST not in adj["neighbors"] or dest_area not in eth_areas:
            result.update({"ok": False, "error": "DEST_NO_LONGER_SAFE"})
            OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return

        # --- dry run (factory + IsValid, no FN_CMD_QUEUE_POST) ---
        result["allow_post_before_dry"] = allow_post()
        dry = mo.move(UNIT_ID, DEST, dry_run=True)
        result["dry_run"] = dry
        if not (dry.get("ok") and dry.get("result") == "DRY_RUN_VALID"):
            result.update({"ok": False, "error": "DRY_RUN_NOT_VALID", "dry_run": dry})
            OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return

        # re-check process and pause still held
        if mem_find_pid("hoi4.exe") != EXPECTED_PID or process_health(EXPECTED_PID).get("alive") is not True:
            result.update({"ok": False, "error": "PROCESS_LOST_AFTER_DRY"})
            OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return
        idler = struct.unpack("<Q", p.read(p.base + G_IDLER, 8))[0]
        if p.read(idler + 0x6C1, 1)[0] != 1 or struct.unpack("<i", p.read(gs + 0x4BC, 4))[0] != 0:
            result.update({"ok": False, "error": "PAUSE_OR_SPEED_CHANGED_AFTER_DRY"})
            OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return

        # --- one live Post ---
        open_gates()
        gates_opened = True
        result["allow_post_at_post"] = allow_post()
        if not allow_post():
            result.update({"ok": False, "error": "ALLOW_POST_STILL_FALSE"})
            OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return

        posted = mo.move(UNIT_ID, DEST, dry_run=False)
        result["post"] = posted
        time.sleep(0.5)
        health1 = process_health(EXPECTED_PID)
        result["health_after"] = health1
        # refresh army pointer
        b2 = Backend()
        army2 = resolve_handle(b2, HANDLE_TYPE_ARMY, UNIT_ID, b2.image_base)
        after = snapshot_unit(p, pe, gs, army2 or army, tokens)
        result["readback_after"] = after
        # one extra delayed read if path still empty but process alive (Execute may lag; do not unpause)
        if health1.get("alive") and DEST not in (after.get("path") or []) and posted.get("result") != "PROCESS_EXITED":
            time.sleep(2.0)
            after2 = snapshot_unit(p, pe, gs, army2 or army, tokens)
            result["readback_after_plus2s"] = after2
            after = after2

        result["path_contains_dest"] = DEST in (after.get("path") or [])
        result["commandlist_nonempty"] = (after.get("commandlist") or {}).get("size", 0) > 0
        result["province_unchanged"] = after.get("province_id") == SRC
        result["still_paused"] = p.read(idler + 0x6C1, 1)[0] == 1
        result["speed_index_after"] = struct.unpack("<i", p.read(gs + 0x4BC, 4))[0]
        result["ok"] = bool(health1.get("alive") and posted.get("result") in ("PATH_CONTAINS_DEST", "POSTED_DEST_NOT_IN_PATH"))
        result["result"] = posted.get("result")
        # leave the move in place as the contrast sample; Cancel is documented, not issued
        result["left_order_in_place"] = True
        result["cancel_not_issued"] = True
        OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
        # compact stdout
        print(json.dumps({
            "ok": result["ok"],
            "result": result.get("result"),
            "dry_run": dry.get("result"),
            "post": {k: posted.get(k) for k in ("ok", "result", "post_rax", "post_wait", "path_before", "path_after", "province_buf_kind") if k in posted},
            "path_contains_dest": result["path_contains_dest"],
            "commandlist_nonempty": result["commandlist_nonempty"],
            "readback_after_path": after.get("path"),
            "readback_after_full_path": after.get("full_path"),
            "readback_after_commandlist": after.get("commandlist"),
            "readback_after_elems": after.get("commandlist_elems"),
            "movement_progress": after.get("movement_progress"),
            "province": after.get("province_id"),
            "still_paused": result["still_paused"],
            "speed_index_after": result["speed_index_after"],
            "health_after": health1,
            "allow_post_at_post": result.get("allow_post_at_post"),
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
        result_close = {"allow_post_after_close": allow_post(), "marker_exists": MARKER.exists()}
        # append close status
        try:
            data = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else result
            data["gate_closed"] = result_close
            OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
            print("GATE_CLOSED", json.dumps(result_close))
        except Exception as e:
            print("GATE_CLOSE_STATUS_WRITE_FAIL", e)
        if p is not None:
            try:
                p.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
