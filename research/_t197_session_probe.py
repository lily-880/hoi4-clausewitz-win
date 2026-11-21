# -*- coding: utf-8 -*-
from __future__ import annotations
import hashlib, json, struct, sys
from pathlib import Path

ROOT = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")
sys.path.insert(0, str(ROOT / "calling"))

from pe import PE
from mem import Proc, find_pid as mem_find_pid
from process import Backend
from gamestate import (
    detect_session, resolve_player_country, _rtti_name_from_vtable, read_campaign_summary,
)
from input_loaded_fields import (
    LoadedReader, own_armies, own_army_groups, own_leaders, own_plans,
    unit_formation_army_id, unit_formation_army_group_id,
)
from config import allow_post

EXE = r"D:\STEAM\steamapps\common\Hearts of Iron IV\hoi4.exe"
# also try the path used before
EXE_CANDIDATES = [
    r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe",
    r"D:\STEAM\steamapps\common\Hearts of Iron IV\hoi4.exe",
]
INV = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
OUT = ROOT / "research" / "t197_session_recheck.json"
EXPECTED_PID = 12948
EXPECTED_SHA = "709F916AFBEBCFE64A26678702691AEB40945D206074C2A80DE8E9D601FCE148"
INV_SHA = "a159657f42fa0ec4ab65e7342473c7a4432a763d91d378ff07c37b2059f5a4d2"
ITA_FRONT = {1984, 13237, 13238, 4995, 8062, 12812}


def is_ptr(x):
    return type(x) is int and 0x20000000000 < x < 0x7FFFFFFFFFFF


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


def process_health(pid):
    # STILL_ACTIVE = 259
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.windll.kernel32
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    h = kernel.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return {"alive": False, "exit_code": None}
    code = wintypes.DWORD()
    ok = kernel.GetExitCodeProcess(h, ctypes.byref(code))
    kernel.CloseHandle(h)
    return {"alive": bool(ok) and code.value == 259, "exit_code": int(code.value) if ok else None}


def find_unit(p, co, uid):
    for ap in ptr_array(p, co + 0x290, 4096):
        if struct.unpack("<I", p.read(ap + 0x1C, 4))[0] == uid:
            return ap
    return 0


def snap_unit(p, pe, ap):
    if not ap:
        return None
    raw240 = p.read(ap + 0x240, 4)
    og = struct.unpack("<Q", p.read(ap + 0xC0, 8))[0]
    return {
        "ptr": hex(ap),
        "class": cls(p, pe, ap),
        "unit_id": struct.unpack("<I", p.read(ap + 0x1C, 4))[0],
        "province": struct.unpack("<I", p.read(ap + 0x28, 4))[0],
        "path": u32_array(p, ap + 0x200),
        "full_path": u32_array(p, ap + 0x220),
        "progress_f32": struct.unpack("<f", raw240)[0],
        "progress_u32": struct.unpack("<I", raw240)[0],
        "progress_hex": raw240.hex(),
        "commandlist_size": pdx(p, ap + 0x2C0)[2],
        "orders_group": hex(og) if is_ptr(og) else None,
        "ita_adjacent": struct.unpack("<I", p.read(ap + 0x28, 4))[0] in ITA_FRONT,
    }


def snap_instance(p, pe, ip):
    rec = {
        "ptr": hex(ip),
        "class": cls(p, pe, ip),
        "type_30": struct.unpack("<I", p.read(ip + 0x30, 4))[0],
        "instance_id_244": struct.unpack("<I", p.read(ip + 0x244, 4))[0],
        "can_execute_248": p.read(ip + 0x248, 1)[0],
        "path_70": u32_array(p, ip + 0x70),
        "states_e0": u32_array(p, ip + 0xE0),
        "field_258": struct.unpack("<I", p.read(ip + 0x258, 4))[0],
        "field_25c": struct.unpack("<I", p.read(ip + 0x25C, 4))[0],
        "plus90": struct.unpack("<I", p.read(ip + 0x90, 4))[0],
        "plus224": struct.unpack("<I", p.read(ip + 0x224, 4))[0],
    }
    data, cap, size = pdx(p, ip + 0x210)
    rec["scheduled_210"] = {"data": hex(data), "cap": cap, "size": size}
    if size and is_ptr(data):
        q = struct.unpack("<Q", p.read(data, 8))[0]
        unadj = q - 0xB8
        rec["scheduled_210"]["elem0"] = hex(q)
        if is_ptr(unadj) and cls(p, pe, unadj) and "CArmy" in (cls(p, pe, unadj) or ""):
            rec["scheduled_210"]["unit_id"] = struct.unpack("<I", p.read(unadj + 0x1C, 4))[0]
    return rec


def main():
    out = {"authorized_by": ["pt183u", "pt180u"]}
    # inventory
    raw = INV.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    text = raw.decode("utf-8")
    lines = text.splitlines()
    fields = []
    for ln in lines:
        if ln.startswith("| ") and not ln.startswith("| 字段名 |") and not ln.startswith("| ---"):
            parts = [x.strip() for x in ln.strip("|").split("|")]
            if len(parts) >= 3:
                fields.append({"name": parts[0], "status": parts[1], "note": parts[2]})
    unverified = [f for f in fields if f["status"] == "未验证"]
    verified = [f for f in fields if f["status"] == "已验证"]
    out["inventory"] = {
        "sha256": sha,
        "sha_ok": sha == INV_SHA,
        "fields": len(fields),
        "verified": len(verified),
        "unverified": len(unverified),
        "unverified_names": [f["name"] for f in unverified],
        "unverified_rows": unverified,
    }

    pid = mem_find_pid("hoi4.exe")
    out["found_pid"] = pid
    out["expected_pid"] = EXPECTED_PID
    out["pid_ok"] = pid == EXPECTED_PID
    out["health"] = process_health(pid) if pid else {"alive": False}
    out["allow_post"] = allow_post()
    out["gate_open"] = (ROOT / "research" / "safe_land_tool_gate.OPEN").exists()

    exe = None
    for c in EXE_CANDIDATES:
        if Path(c).exists():
            exe = c
            break
    out["exe_path"] = exe
    if exe:
        import hashlib as _h
        h = _h.sha256()
        with open(exe, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        out["exe_sha256"] = h.hexdigest().upper()
        out["exe_sha_ok"] = out["exe_sha256"] == EXPECTED_SHA

    if not pid or not out["health"].get("alive"):
        OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
        print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
        return

    p = Proc(pid)
    pe = PE(exe)
    try:
        session = detect_session(p, pe)
        in_game = bool(session.get("in_game") or (session.get("signals") or {}).get("idler_ptr"))
        out["session_raw_keys"] = list(session.keys())
        signals = session.get("signals") or {}
        if not signals.get("gs_ptr") or not signals.get("idler_ptr"):
            out["in_game"] = False
            out["session"] = session
            OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
            print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
            return
        gs = int(signals["gs_ptr"], 16)
        idler = int(signals["idler_ptr"], 16)
        player = resolve_player_country(p, gs)
        co = int(player["country_ptr"], 16)
        pause = p.read(idler + 0x6C1, 1)[0]
        speed = struct.unpack("<i", p.read(gs + 0x4BC, 4))[0]
        summary = read_campaign_summary(p, gs)
        date = (summary.get("verified") or {}).get("date_full")

        def rtti(a):
            return cls(p, pe, a)

        r = LoadedReader(p.read, rtti)
        armies, _ = own_armies(r, co)
        groups, _ = own_army_groups(r, co)
        leaders, evl = own_leaders(r, co)
        plans, _ = own_plans(r, co)
        assigned = [x for x in leaders if x.get("assigned_to")]

        units = []
        for ap in ptr_array(p, co + 0x290, 4096):
            units.append(snap_unit(p, pe, ap))

        theatres = []
        for tp in ptr_array(p, co + 0x168, 64):
            ogs = []
            for gp in ptr_array(p, tp + 0x80, 256):
                insts = [snap_instance(p, pe, ip) for ip in ptr_array(p, gp + 0x98, 256)]
                lp = struct.unpack("<Q", p.read(gp + 0x88, 8))[0]
                ogs.append({
                    "ptr": hex(gp),
                    "class": cls(p, pe, gp),
                    "handle": handle_at(p, gp + 8),
                    "leader_88": hex(lp),
                    "instances": insts,
                })
            ags = []
            for gp in ptr_array(p, tp + 0x98, 256):
                lp = struct.unpack("<Q", p.read(gp + 0x88, 8))[0]
                ags.append({
                    "ptr": hex(gp),
                    "class": cls(p, pe, gp),
                    "handle": handle_at(p, gp + 8),
                    "leader_88": hex(lp),
                })
            theatres.append({
                "ptr": hex(tp),
                "class": cls(p, pe, tp),
                "handle": handle_at(p, tp + 8),
                "orders_groups": ogs,
                "army_groups": ags,
            })

        out["live"] = {
            "in_game": True,
            "pid": pid,
            "base": hex(p.base),
            "gs": hex(gs),
            "co": hex(co),
            "idler": hex(idler),
            "idler_class": cls(p, pe, idler),
            "player": player,
            "date": date,
            "pause": pause,
            "speed": speed,
            "armies": armies,
            "army_groups": groups,
            "plans": plans,
            "assigned_leaders": assigned,
            "n_leaders": len(leaders),
            "n_units": len(units),
            "units": units,
            "theatres": theatres,
        }
    finally:
        p.close()

    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    compact = {
        "pid": out.get("found_pid"),
        "pid_ok": out.get("pid_ok"),
        "health": out.get("health"),
        "exe_sha_ok": out.get("exe_sha_ok"),
        "allow_post": out.get("allow_post"),
        "gate_open": out.get("gate_open"),
        "inventory": {k: out["inventory"][k] for k in ("sha_ok", "fields", "verified", "unverified", "unverified_names")},
        "live": None,
    }
    live = out.get("live")
    if live:
        compact["live"] = {
            "pause": live["pause"],
            "speed": live["speed"],
            "date": live["date"],
            "player_tag": (live.get("player") or {}).get("tag") or (live.get("player") or {}).get("country_tag"),
            "player_index": (live.get("player") or {}).get("index") or (live.get("player") or {}).get("country_index"),
            "armies": live["armies"],
            "army_groups": live["army_groups"],
            "plans": live["plans"],
            "assigned_leaders": live["assigned_leaders"],
            "n_units": live["n_units"],
            "units_brief": [
                {k: u[k] for k in ("unit_id", "province", "path", "full_path", "progress_u32", "commandlist_size", "ita_adjacent") if k in u}
                for u in live["units"]
            ],
            "instances": ((live.get("theatres") or [{}])[0].get("orders_groups") or [{}])[0].get("instances"),
        }
    print(json.dumps(compact, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
