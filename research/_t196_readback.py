from __future__ import annotations
import json, struct, sys
from pathlib import Path

ROOT = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")
sys.path.insert(0, str(ROOT / "calling"))

from pe import PE
from mem import Proc, find_pid as mem_find_pid
from gamestate import detect_session, resolve_player_country, _rtti_name_from_vtable, read_campaign_summary
from input_loaded_fields import (
    LoadedReader, own_armies, own_army_groups, own_leaders, own_plans,
    unit_formation_army_id, unit_formation_army_group_id,
)

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
EXPECTED_PID = 12948
POST = ROOT / "research" / "t196_scaffold_post.json"
OUT = ROOT / "research" / "t196_readback.json"


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


def snap_unit(p, pe, ap):
    if not ap:
        return None
    raw240 = p.read(ap + 0x240, 4)
    prog_f = struct.unpack("<f", raw240)[0]
    prog_u = struct.unpack("<I", raw240)[0]
    cmd = ptr_array(p, ap + 0x2C0, 64)
    elems = []
    for c in cmd:
        ev = {"ptr": hex(c), "class": cls(p, pe, c)}
        if is_ptr(c):
            ev["plus8"] = struct.unpack("<I", p.read(c + 8, 4))[0]
            ev["head16"] = p.read(c, 16).hex()
        elems.append(ev)
    og = struct.unpack("<Q", p.read(ap + 0xC0, 8))[0]
    return {
        "ptr": hex(ap),
        "class": cls(p, pe, ap),
        "unit_id": struct.unpack("<I", p.read(ap + 0x1C, 4))[0],
        "province": struct.unpack("<I", p.read(ap + 0x28, 4))[0],
        "path": u32_array(p, ap + 0x200),
        "full_path": u32_array(p, ap + 0x220),
        "progress_f32": prog_f,
        "progress_u32": prog_u,
        "progress_hex": raw240.hex(),
        "commandlist_size": len(cmd),
        "commandlist": elems,
        "orders_group": hex(og) if is_ptr(og) else None,
        "orders_group_class": cls(p, pe, og) if is_ptr(og) else None,
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
    arrays = {}
    for off in (0x38, 0x40, 0x48, 0x50, 0x58, 0x60, 0x70, 0x80, 0x98, 0xB0, 0xC8, 0xE0, 0xF8,
                0x110, 0x128, 0x140, 0x160, 0x178, 0x190, 0x1A8, 0x1C0, 0x1D8, 0x1E0, 0x1F8,
                0x210, 0x228, 0x280, 0x298, 0x2B0, 0x2C8, 0x2E0, 0x2F8, 0x310, 0x328, 0x340):
        try:
            data, cap, size = pdx(p, ip + off)
        except Exception:
            continue
        if 0 <= size <= cap <= 64 and (size == 0 or is_ptr(data)):
            preview = None
            if size and is_ptr(data):
                hs = [list(struct.unpack("<II", p.read(data + 8 * j, 8))) for j in range(min(size, 8))]
                u32s = u32_array(p, ip + off)
                ptrs = []
                for j in range(size):
                    q = struct.unpack("<Q", p.read(data + 8 * j, 8))[0]
                    ptrs.append({"ptr": hex(q), "class": cls(p, pe, q)} if is_ptr(q) else {"raw": hex(q)})
                preview = {"handles": hs, "u32s": u32s, "ptrs": ptrs}
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
    # instance arrays at +0x98, +0xb0, +0xc8 as t193 mentioned
    rec["instances_98"] = [snap_instance(p, pe, ip) for ip in ptr_array(p, gp + 0x98, 256)]
    rec["instances_b0"] = [snap_instance(p, pe, ip) for ip in ptr_array(p, gp + 0xB0, 256)]
    rec["instances_c8"] = [snap_instance(p, pe, ip) for ip in ptr_array(p, gp + 0xC8, 256)]
    if children:
        rec["children"] = []
        for cp in ptr_array(p, gp + 0x230, 256):
            rec["children"].append({
                "ptr": hex(cp), "class": cls(p, pe, cp),
                "handle": handle_at(p, cp + 8), "name": msvc_string(p, cp + 0x160),
            })
    return rec


def main():
    out = {"authorized_by": ["pt182u", "pt180u"]}
    post = json.loads(POST.read_text(encoding="utf-8")) if POST.exists() else {}
    # extract post outcomes
    keys = [
        "ok", "steps", "error",
        "move_post", "og_post", "sl_army_post", "ag_post", "sl_ag_post",
        "nr_post", "nf_post", "oa_post", "sl_unit_post", "sl_unit_dry", "sl_unit_packed",
        "unpause_post", "repause_post", "ex_post", "ex_packed",
        "contrast_1x", "after_unpause", "after_repause", "date_final", "final_pause",
        "health_final", "army_handle", "ag_handle",
        "instances_after_nf", "instances_after_oa", "instances_after_ex",
        "unit_1829_after_move", "unit_1829_after_1x", "unit_1838_after_ex",
        "gate_closed",
    ]
    out["from_post"] = {k: post.get(k) for k in keys}

    pid = mem_find_pid("hoi4.exe")
    out["found_pid"] = pid
    out["pid_ok"] = pid == EXPECTED_PID
    if pid != EXPECTED_PID:
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
        pause = p.read(idler + 0x6C1, 1)[0]
        speed = struct.unpack("<i", p.read(gs + 0x4BC, 4))[0]
        summary = read_campaign_summary(p, gs)
        date = (summary.get("verified") or {}).get("date_full")

        def rtti(a):
            return cls(p, pe, a)

        r = LoadedReader(p.read, rtti)
        armies, _ = own_armies(r, co)
        groups, _ = own_army_groups(r, co)
        leaders, _ = own_leaders(r, co)
        plans, _ = own_plans(r, co)

        theatres = []
        for tp in ptr_array(p, co + 0x168, 64):
            theatres.append({
                "ptr": hex(tp),
                "class": cls(p, pe, tp),
                "handle": handle_at(p, tp + 8),
                "orders_groups": [snap_group(p, pe, gp) for gp in ptr_array(p, tp + 0x80, 256)],
                "army_groups": [snap_group(p, pe, gp, children=True) for gp in ptr_array(p, tp + 0x98, 256)],
            })

        assigned = [x for x in leaders if x.get("assigned_to")]
        # specifically leaders 312, 313, 314
        interesting = []
        for x in leaders:
            if (x.get("leader_id") or x.get("id")) in (312, 313, 314):
                interesting.append(x)

        out["live"] = {
            "pid": pid,
            "gs": hex(gs),
            "co": hex(co),
            "idler": hex(idler),
            "date": date,
            "pause": pause,
            "speed": speed,
            "armies": armies,
            "army_groups": groups,
            "plans": plans,
            "assigned_leaders": assigned,
            "leaders_312_314": interesting,
            "unit_1829": snap_unit(p, pe, find_unit(p, co, 1829)),
            "unit_1838": snap_unit(p, pe, find_unit(p, co, 1838)),
            "unit_1846": snap_unit(p, pe, find_unit(p, co, 1846)),
            "theatres": theatres,
        }
        # formation for 1838/1846
        u1838 = find_unit(p, co, 1838)
        u1846 = find_unit(p, co, 1846)
        if u1838:
            fid, _ = unit_formation_army_id(r, u1838)
            gid, _ = unit_formation_army_group_id(r, u1838)
            out["live"]["unit_1838_formation"] = {"army_id": fid, "army_group_id": gid}
        if u1846:
            fid, _ = unit_formation_army_id(r, u1846)
            gid, _ = unit_formation_army_group_id(r, u1846)
            out["live"]["unit_1846_formation"] = {"army_id": fid, "army_group_id": gid}
            # leader handle on the unit? scan for type 4713 or +0x564 etc — do not treat as assigned_to
            # but record CArmyLeader assigned handle if 314 points at unit
    finally:
        p.close()

    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    # compact stdout
    live = out.get("live") or {}
    compact = {
        "pid_ok": out.get("pid_ok"),
        "pause": live.get("pause"),
        "speed": live.get("speed"),
        "date": live.get("date"),
        "armies": live.get("armies"),
        "army_groups": live.get("army_groups"),
        "plans": live.get("plans"),
        "assigned_leaders": live.get("assigned_leaders"),
        "leaders_312_314": live.get("leaders_312_314"),
        "unit_1829": live.get("unit_1829"),
        "unit_1838": live.get("unit_1838"),
        "unit_1838_formation": live.get("unit_1838_formation"),
        "unit_1846": live.get("unit_1846"),
        "unit_1846_formation": live.get("unit_1846_formation"),
        "og_instances_98": ((live.get("theatres") or [{}])[0].get("orders_groups") or [{}])[0].get("instances_98"),
        "og_instances_b0": ((live.get("theatres") or [{}])[0].get("orders_groups") or [{}])[0].get("instances_b0"),
        "og_instances_c8": ((live.get("theatres") or [{}])[0].get("orders_groups") or [{}])[0].get("instances_c8"),
        "ag": ((live.get("theatres") or [{}])[0].get("army_groups") or [None])[0],
        "post_steps": (out.get("from_post") or {}).get("steps"),
        "sl_unit_post": (out.get("from_post") or {}).get("sl_unit_post"),
        "ex_post": (out.get("from_post") or {}).get("ex_post"),
        "nf_post": (out.get("from_post") or {}).get("nf_post"),
        "oa_post": (out.get("from_post") or {}).get("oa_post"),
        "contrast_1x": (out.get("from_post") or {}).get("contrast_1x"),
        "final_pause_from_post": (out.get("from_post") or {}).get("final_pause"),
        "gate_closed": (out.get("from_post") or {}).get("gate_closed"),
    }
    print(json.dumps(compact, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
