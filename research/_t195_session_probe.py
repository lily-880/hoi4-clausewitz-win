from __future__ import annotations
import hashlib, json, struct, sys
from pathlib import Path

ROOT = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")
sys.path.insert(0, str(ROOT / "calling"))

from pe import PE
from mem import Proc, find_pid as mem_find_pid
from gamestate import detect_session, resolve_player_country, _rtti_name_from_vtable, read_campaign_summary
from input_loaded_fields import (
    LoadedReader, own_armies, own_army_groups, own_leaders, own_plans,
    unit_formation_army_id, unit_formation_army_group_id, unit_movement_path,
)

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
EXPECTED_PID = 8500
EXPECTED_SHA = "709F916AFBEBCFE64A26678702691AEB40945D206074C2A80DE8E9D601FCE148"
OUT = ROOT / "research" / "t195_session_recheck.json"


def is_ptr(x):
    return type(x) is int and 0x20000000000 < x < 0x7FFFFFFFFFFF


def pdx(p, a):
    return struct.unpack("<QII", p.read(a, 16))


def ptr_array(p, a, bound=4096):
    data, cap, size = pdx(p, a)
    if not 0 <= size <= cap <= max(bound, 100) or (size and not is_ptr(data)):
        return []
    return [struct.unpack("<Q", p.read(data + 8 * j, 8))[0] for j in range(size)]


def u32_array(p, a, bound=64):
    data, cap, size = pdx(p, a)
    if size <= 0 or not is_ptr(data) or size > bound:
        return {"data": hex(data) if is_ptr(data) else data, "cap": cap, "size": size, "items": []}
    raw = p.read(data, size * 4)
    return {"data": hex(data), "cap": cap, "size": size,
            "items": list(struct.unpack("<" + "I" * size, raw))}


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


def snap_unit(p, pe, ap):
    uid = struct.unpack("<I", p.read(ap + 0x1C, 4))[0]
    prov = struct.unpack("<I", p.read(ap + 0x28, 4))[0]
    path = u32_array(p, ap + 0x200)
    full = u32_array(p, ap + 0x220)
    prog = struct.unpack("<f", p.read(ap + 0x240, 4))[0]
    cmd = ptr_array(p, ap + 0x2C0, 64)
    og = struct.unpack("<Q", p.read(ap + 0xC0, 8))[0]
    return {
        "ptr": hex(ap),
        "class": cls(p, pe, ap),
        "unit_id": uid,
        "province": prov,
        "path": path["items"],
        "full_path": full["items"],
        "progress": prog,
        "commandlist_size": len(cmd),
        "orders_group": hex(og) if is_ptr(og) else None,
        "orders_group_class": cls(p, pe, og) if is_ptr(og) else None,
    }


def snap_instance(p, pe, ip):
    typ = struct.unpack("<I", p.read(ip + 0x30, 4))[0]
    inst = struct.unpack("<I", p.read(ip + 0x244, 4))[0]
    can = p.read(ip + 0x248, 1)[0]
    path = u32_array(p, ip + 0x70)
    states = u32_array(p, ip + 0xE0)
    return {
        "ptr": hex(ip),
        "class": cls(p, pe, ip),
        "type_30": typ,
        "instance_id_244": inst,
        "can_execute_248": can,
        "path_70": path["items"],
        "states_e0": states["items"],
        "field_258": struct.unpack("<I", p.read(ip + 0x258, 4))[0],
        "field_25c": struct.unpack("<I", p.read(ip + 0x25C, 4))[0],
    }


def snap_group(p, pe, gp, children_off=None):
    rec = {
        "ptr": hex(gp),
        "class": cls(p, pe, gp),
        "handle": handle_at(p, gp + 8) if is_ptr(gp) else None,
        "name": msvc_string(p, gp + 0x160) if is_ptr(gp) else None,
        "fm_flag_39": p.read(gp + 0x39, 1)[0] if is_ptr(gp) else None,
    }
    if not is_ptr(gp):
        return rec
    leader_ptr = struct.unpack("<Q", p.read(gp + 0x88, 8))[0]
    rec["leader_ptr"] = hex(leader_ptr) if is_ptr(leader_ptr) else None
    rec["leader_handle"] = handle_at(p, leader_ptr + 0x18) if is_ptr(leader_ptr) else None
    rec["members_n"] = pdx(p, gp + 0x50)[2]
    rec["order_instances"] = [snap_instance(p, pe, ip) for ip in ptr_array(p, gp + 0x98, 256)]
    parent = struct.unpack("<Q", p.read(gp + 0x1B8, 8))[0]
    rec["parent_1b8"] = {
        "ptr": hex(parent) if is_ptr(parent) else None,
        "class": cls(p, pe, parent) if is_ptr(parent) else None,
        "handle": handle_at(p, parent + 8) if is_ptr(parent) else None,
    }
    if children_off is not None:
        rec["children"] = []
        for cp in ptr_array(p, gp + children_off, 256):
            rec["children"].append({
                "ptr": hex(cp),
                "class": cls(p, pe, cp),
                "handle": handle_at(p, cp + 8) if is_ptr(cp) else None,
                "name": msvc_string(p, cp + 0x160) if is_ptr(cp) else None,
            })
    return rec


def main():
    out = {"authorized_by": ["pt181u", "pt180u"], "expected_pid": EXPECTED_PID}
    exe_sha = hashlib.sha256(Path(EXE).read_bytes()).hexdigest().upper()
    out["exe_sha256"] = exe_sha
    out["exe_sha_ok"] = exe_sha == EXPECTED_SHA

    found = mem_find_pid("hoi4.exe")
    out["found_pid"] = found
    out["pid_ok"] = found == EXPECTED_PID
    if not found:
        out["ok"] = False
        out["error"] = "NO_HOI4"
        OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
        print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
        return

    p = Proc(found)
    pe = PE(EXE)
    try:
        session = detect_session(p, pe)
        signals = session.get("signals") or {}
        gs = int(signals.get("gs_ptr") or "0", 16)
        idler = int(signals.get("idler_ptr") or "0", 16)
        co_info = resolve_player_country(p, gs) if gs else {}
        co = int(co_info.get("country_ptr") or "0", 16)
        summary = read_campaign_summary(p, gs) if gs else {}
        ver = summary.get("verified") or {}
        pause = p.read(idler + 0x6C1, 1)[0] if idler else None
        speed = struct.unpack("<i", p.read(gs + 0x4BC, 4))[0] if gs else None
        hour_progress = struct.unpack("<f", p.read(gs + 0x4B8, 4))[0] if gs else None

        def rtti(a):
            return cls(p, pe, a)

        r = LoadedReader(p.read, rtti)
        armies, aev = own_armies(r, co) if co else ([], None)
        groups, gev = own_army_groups(r, co) if co else ([], None)
        leaders, lev = own_leaders(r, co) if co else ([], None)
        plans, pev = own_plans(r, co) if co else ([], None)

        units = []
        unit_1829 = None
        for ap in ptr_array(p, co + 0x290, 4096) if co else []:
            snap = snap_unit(p, pe, ap)
            fid, _ = unit_formation_army_id(r, ap)
            gid, _ = unit_formation_army_group_id(r, ap)
            snap["army_id"] = fid
            snap["army_group_id"] = gid
            units.append(snap)
            if snap["unit_id"] == 1829:
                unit_1829 = snap

        theatres = []
        for tp in ptr_array(p, co + 0x168, 64) if co else []:
            trec = {
                "ptr": hex(tp),
                "class": cls(p, pe, tp),
                "handle": handle_at(p, tp + 8) if is_ptr(tp) else None,
            }
            ogs = ptr_array(p, tp + 0x80, 256)
            fms = ptr_array(p, tp + 0x98, 256)
            tgs = ptr_array(p, tp + 0xC8, 256)
            trec["orders_groups"] = [snap_group(p, pe, gp) for gp in ogs]
            trec["army_groups"] = [snap_group(p, pe, gp, children_off=0x230) for gp in fms]
            trec["theater_groups"] = []
            for gp in tgs:
                trec["theater_groups"].append({
                    "ptr": hex(gp),
                    "class": cls(p, pe, gp),
                    "handle": handle_at(p, gp + 8) if is_ptr(gp) else None,
                })
            theatres.append(trec)

        assigned = [x for x in (leaders or []) if x.get("assigned_to")]
        unassigned = [x for x in (leaders or []) if not x.get("assigned_to")]

        out.update({
            "ok": True,
            "pid": p.pid,
            "base": hex(p.base),
            "gs": hex(gs),
            "co": hex(co),
            "idler": hex(idler),
            "country": {k: co_info.get(k) for k in co_info if k in ("tag", "tag_str", "index", "country_ptr", "player_index")},
            "date": ver.get("date_full") or ver.get("date"),
            "hour_tick": (ver.get("date_full") or {}).get("hour_tick") if isinstance(ver.get("date_full"), dict) else ver.get("hour_tick"),
            "pause": pause,
            "speed_index": speed,
            "hour_progress": hour_progress,
            "session_mode": session.get("mode") or session.get("state"),
            "n_units": len(units),
            "unit_ids": [u["unit_id"] for u in units],
            "units": units,
            "unit_1829": unit_1829,
            "unit_1829_present": unit_1829 is not None,
            "armies": armies,
            "army_groups": groups,
            "plans": plans,
            "assigned_leaders": assigned,
            "unassigned_leader_ids": [x.get("leader_id") or x.get("id") for x in unassigned],
            "unassigned_sample": [
                {"leader_id": x.get("leader_id") or x.get("id"), "name": x.get("name")}
                for x in unassigned[:10]
            ],
            "theatres": theatres,
            "legacy_contrast": {
                "path_1829": (unit_1829 or {}).get("path") if unit_1829 else None,
                "army_1": next((a for a in armies if a.get("army_id") == 1), None),
                "army_group_2": next((g for g in groups if g.get("army_group_id") == 2), None),
                "plan_1": next((pl for pl in plans if pl.get("plan_id") == 1), None),
            },
        })
        # friendly country tag if present under another key
        if not out["country"].get("tag") and not out["country"].get("tag_str"):
            out["country_raw_keys"] = list(co_info.keys())
            out["country_raw"] = {k: (hex(v) if isinstance(v, int) and v > 0x10000 else v) for k, v in co_info.items() if k != "traceback"}
    finally:
        p.close()

    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    # compact print
    compact = {k: out[k] for k in out if k not in ("units", "theatres", "country_raw")}
    compact["theatres_summary"] = []
    for t in out.get("theatres") or []:
        compact["theatres_summary"].append({
            "handle": t.get("handle"),
            "class": t.get("class"),
            "n_og": len(t.get("orders_groups") or []),
            "n_ag": len(t.get("army_groups") or []),
            "ogs": [{"handle": g.get("handle"), "name": g.get("name"), "n_plans": len(g.get("order_instances") or [])} for g in t.get("orders_groups") or []],
            "ags": [{"handle": g.get("handle"), "name": g.get("name"), "children": g.get("children")} for g in t.get("army_groups") or []],
        })
    compact["units_short"] = [
        {"unit_id": u["unit_id"], "province": u["province"], "path": u["path"], "army_id": u.get("army_id"), "army_group_id": u.get("army_group_id")}
        for u in out.get("units") or []
    ]
    print(json.dumps(compact, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
