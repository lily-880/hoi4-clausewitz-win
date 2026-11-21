# research/_t191_live_units.py — read-only unit/neighbor/controller survey
from __future__ import annotations
import json, os, struct, sys
from pathlib import Path

os.environ["CLAUSEWITZ_ALLOW_POST"] = "0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"] = "0"
sys.path.insert(0, "calling")

from pe import PE
from mem import Proc, find_pid
from gamestate import (
    detect_session, resolve_player_country, _rtti_name_from_vtable, _pdx_array,
)
from input_loaded_fields import LoadedReader, province_adjacencies, country_tag
from province import resolve_province

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
EXPECTED_PID = 26976
EXPECTED_GS = 0x26C259D0FF0
EXPECTED_CO = 0x26C4B672530


def is_ptr(x):
    return type(x) is int and 0x10000 < x < 0x7FFFFFFFFFFF


def main():
    process_pid = find_pid("hoi4.exe")
    if process_pid != EXPECTED_PID:
        # still attach if the live in-game process is a successor, but record mismatch
        pass
    if not process_pid:
        Path("research/t191_live_units.json").write_text(
            json.dumps({"ok": False, "error": "NO_PROCESS"}, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps({"ok": False, "error": "NO_PROCESS"}))
        return
    p = Proc(process_pid)
    pe = PE(EXE)
    try:
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
            return {"data": data, "cap": cap, "size": size}

        def u32_array(a, bound=64):
            h = pdx(a)
            if not 0 <= h["size"] <= h["cap"] <= bound:
                return [], h
            if h["size"] and not is_ptr(h["data"]):
                return [], h
            if h["size"] == 0:
                return [], h
            raw = p.read(h["data"], h["size"] * 4)
            return list(struct.unpack("<" + "I" * h["size"], raw)), h

        def ptr_array(a, bound=4096):
            h = pdx(a)
            if not 0 <= h["size"] <= h["cap"] <= max(bound, 100):
                return [], h
            if h["size"] and not is_ptr(h["data"]):
                return [], h
            return [q(h["data"] + 8 * j) for j in range(h["size"])], h

        def msvc_string(a):
            blob = p.read(a, 32)
            n, cap = struct.unpack_from("<QQ", blob, 16)
            if not 0 <= n <= 1024 or cap < n:
                return None
            raw = blob[:n] if cap <= 15 else p.read(struct.unpack_from("<Q", blob)[0], n)
            return raw.decode("utf-8", "replace")

        session = detect_session(p, pe)
        if not session.get("in_game"):
            print(json.dumps({"ok": False, "error": "NOT_IN_GAME", "process_pid": process_pid}))
            return
        gs = int(session["signals"]["gs_ptr"], 16)
        res = resolve_player_country(p, gs)
        co = int(res["country_ptr"], 16)
        loaded = LoadedReader(p.read, cls)
        tag = country_tag(loaded, gs, res["player_index"], co)

        countries, _ = ptr_array(gs + 0x310, 2048)
        tag_data, tag_cap, tag_n = struct.unpack("<QII", p.read(gs + 0x358, 16))

        def tag_of(index):
            if not 0 <= index < tag_n:
                return None
            return msvc_string(tag_data + index * 32)

        index_by_tag = {}
        country_by_tag = {}
        for i, cp in enumerate(countries):
            t = tag_of(i)
            if t:
                index_by_tag[t] = i
                if is_ptr(cp):
                    country_by_tag[t] = cp

        def areas_of(country_ptr, off):
            arr, h = ptr_array(country_ptr + off, 4096)
            return arr, h

        # Build province -> controller/owner tag via official country area lists
        controller_of = {}
        owner_of = {}
        area_probe = {}
        for tname, cptr in country_by_tag.items():
            for field, off, dct in (("controller", 0x548, controller_of), ("owner", 0x560, owner_of)):
                arr, h = areas_of(cptr, off)
                if tname in ("ETH", "ITA") and field == "controller":
                    area_probe[tname] = {
                        "country": hex(cptr),
                        "index": index_by_tag.get(tname),
                        "n_areas": len(arr),
                    }
                    if arr:
                        area = arr[0]
                        # dump first area header for backlink learning
                        blob = p.read(area, 0x80)
                        qwords = [hex(struct.unpack_from("<Q", blob, i)[0]) for i in range(0, 0x80, 8)]
                        area_probe[tname]["first_area"] = hex(area)
                        area_probe[tname]["first_area_class"] = cls(area)
                        area_probe[tname]["qwords"] = qwords
                        # members array hunt
                        for moff in (0x10, 0x18, 0x20, 0x28, 0x30, 0x38, 0x40, 0x48, 0x50, 0x58, 0x60, 0x68, 0x70):
                            try:
                                mems, mh = ptr_array(area + moff, 8192)
                            except Exception:
                                continue
                            if mems and cls(mems[0]) == ".?AVCProvince@@":
                                area_probe[tname]["members_off"] = hex(moff)
                                area_probe[tname]["members"] = len(mems)
                for area in arr:
                    if not is_ptr(area):
                        continue
                    # try known member offsets; also from probe
                    found = False
                    for moff in (0x18, 0x20, 0x28, 0x30, 0x38, 0x40, 0x48, 0x50, 0x10, 0x58, 0x60, 0x68, 0x70):
                        try:
                            mems, mh = ptr_array(area + moff, 8192)
                        except Exception:
                            continue
                        if not mems:
                            continue
                        if cls(mems[0]) != ".?AVCProvince@@":
                            continue
                        found = True
                        for pp in mems:
                            if cls(pp) != ".?AVCProvince@@":
                                continue
                            pid = u32(pp + 0xA4)
                            dct[pid] = tname
                        break

        # snapshot ETH area membership via capture method too (province+0xd0 in ETH list)
        eth_ctrl_areas, _ = areas_of(co, 0x548)
        ita_cptr = country_by_tag.get("ITA")
        ita_ctrl_areas, _ = areas_of(ita_cptr, 0x548) if ita_cptr else ([], None)
        eth_ctrl_set = set(eth_ctrl_areas)
        ita_ctrl_set = set(ita_ctrl_areas)

        armies, ah = ptr_array(co + 0x290, 4096)
        units = []
        occupied = {}
        for ap in armies:
            ht = u32(ap + 0x18)
            uid = u32(ap + 0x1C)
            loc_id = u32(ap + 0x28)
            loc_ptr = q(ap + 0x1F0)
            path, ph = u32_array(ap + 0x200, 64)
            full_path, fh = u32_array(ap + 0x220, 64)
            cl = pdx(ap + 0x2C0)
            cl_elems = []
            if 0 < cl["size"] <= cl["cap"] <= 32 and is_ptr(cl["data"]):
                for j in range(cl["size"]):
                    cp = q(cl["data"] + 8 * j)
                    elem = {"ptr": hex(cp), "class": cls(cp)}
                    if is_ptr(cp):
                        elem["plus8"] = u32(cp + 8)
                    cl_elems.append(elem)
            occupied.setdefault(loc_id, []).append(uid)
            units.append({
                "unit_id": uid,
                "handle_type": ht,
                "army_ptr": hex(ap),
                "province_id": loc_id,
                "province_ptr": hex(loc_ptr),
                "owner_index": i32(ap + 0x1E0),
                "path": path,
                "path_hdr": {k: (hex(v) if k == "data" else v) for k, v in ph.items()},
                "full_path": full_path,
                "full_path_hdr": {k: (hex(v) if k == "data" else v) for k, v in fh.items()},
                "commandlist_size": cl["size"],
                "commandlist_hdr": {k: (hex(v) if k == "data" else v) for k, v in cl.items()},
                "commandlist_elems": cl_elems,
                "support_attack": hex(q(ap + 0x1E8)),
                "previous": hex(q(ap + 0x1F8)),
                "movement_progress": i32(ap + 0x240),
                "retreat": u8(ap + 0x24C),
                "withdraw": u8(ap + 0x24D),
                "strategic_redeployment": u8(ap + 0x2AF),
                "leader_id": i32(ap + 0x564),
            })

        needed = set(u["province_id"] for u in units)
        provinces = {}

        def load_prov(pid):
            if pid in provinces:
                return provinces[pid]
            backend = type("B", (), {"read": p.read, "image_base": p.base})()
            pp = resolve_province(backend, pid, p.base, gs)
            info = {"province_id": pid, "ptr": hex(pp) if pp else None, "class": cls(pp) if pp else None}
            if is_ptr(pp):
                adj = province_adjacencies(loaded, pp)
                info["land_neighbors"] = adj["neighbors"]
                info["has_river_crossing"] = adj["has_river_crossing"]
                info["adj_evidence"] = adj["evidence"]
                area = q(pp + 0xD0)
                owner_area = q(pp + 0xD8)
                info["controller_area"] = hex(area) if area else "0x0"
                info["controller_class"] = cls(area)
                info["owner_area"] = hex(owner_area) if owner_area else "0x0"
                info["owner_class"] = cls(owner_area)
                # official area-list membership first, then map, then heuristic
                if pid in controller_of:
                    info["controller"] = controller_of[pid]
                    info["controller_source"] = "country+0x548 area membership"
                elif area in eth_ctrl_set:
                    info["controller"] = "ETH"
                    info["controller_source"] = "province+0xd0 in ETH CO+0x548"
                elif area in ita_ctrl_set:
                    info["controller"] = "ITA"
                    info["controller_source"] = "province+0xd0 in ITA CO+0x548"
                else:
                    info["controller"] = None
                    info["controller_source"] = "unresolved"
                if pid in owner_of:
                    info["owner"] = owner_of[pid]
                needed.update(adj["neighbors"])
            provinces[pid] = info
            return info

        for row in units:
            load_prov(row["province_id"])
        for pid in list(needed):
            load_prov(pid)

        for pid, info in provinces.items():
            neigh = info.get("land_neighbors") or []
            ctrl = info.get("controller")
            nctrl = [(provinces[n].get("controller") if n in provinces else None) for n in neigh]
            info["neighbor_controllers"] = {str(n): c for n, c in zip(neigh, nctrl)}
            info["all_neighbors_eth"] = bool(ctrl == "ETH" and nctrl and all(c == "ETH" for c in nctrl))
            info["ita_adjacent"] = any(c == "ITA" for c in nctrl) or ctrl == "ITA"
            info["own_units_here"] = occupied.get(pid, [])

        candidates = []
        for u in units:
            src = provinces.get(u["province_id"], {})
            if src.get("controller") != "ETH":
                continue
            for nid in src.get("land_neighbors") or []:
                dst = provinces.get(nid, {})
                if dst.get("controller") != "ETH":
                    continue
                river = (src.get("has_river_crossing") or {}).get(str(nid), False)
                score = 0
                if src.get("all_neighbors_eth"):
                    score += 3
                if dst.get("all_neighbors_eth"):
                    score += 5
                if not src.get("ita_adjacent") and not dst.get("ita_adjacent"):
                    score += 4
                if not river:
                    score += 1
                if dst.get("own_units_here"):
                    score += 1
                candidates.append({
                    "unit_id": u["unit_id"],
                    "from": u["province_id"],
                    "to": nid,
                    "river": river,
                    "src_interior": bool(src.get("all_neighbors_eth")),
                    "dst_interior": bool(dst.get("all_neighbors_eth")),
                    "src_ita_adj": bool(src.get("ita_adjacent")),
                    "dst_ita_adj": bool(dst.get("ita_adjacent")),
                    "dst_own_units": dst.get("own_units_here") or [],
                    "score": score,
                })
        candidates.sort(key=lambda x: (-x["score"], x["unit_id"], x["to"]))

        combats = pdx(gs + 0x268)
        occupied_summary = {
            str(pid): {
                "units": occupied[pid],
                "controller": provinces[pid].get("controller"),
                "interior": provinces[pid].get("all_neighbors_eth"),
                "ita_adjacent": provinces[pid].get("ita_adjacent"),
                "neighbors": provinces[pid].get("neighbor_controllers"),
            }
            for pid in occupied
        }
        out = {
            "ok": True,
            "read_only": True,
            "process_pid": process_pid,
            "pid_matches_expected": process_pid == EXPECTED_PID,
            "gs_matches": gs == EXPECTED_GS,
            "co_matches": co == EXPECTED_CO,
            "tag": tag,
            "player_index": res["player_index"],
            "gs": hex(gs),
            "country": hex(co),
            "unit_count": len(units),
            "handle_types": sorted(set(u["handle_type"] for u in units)),
            "unit_ids": [u["unit_id"] for u in units],
            "gs_combats": {k: (hex(v) if k == "data" else v) for k, v in combats.items()},
            "area_probe": area_probe,
            "controller_map_counts": {t: sum(1 for v in controller_of.values() if v == t) for t in sorted(set(controller_of.values()))},
            "units": units,
            "provinces": provinces,
            "occupied_summary": occupied_summary,
            "candidates_top": candidates[:20],
            "candidate_count": len(candidates),
        }
        Path("research/t191_live_units.json").write_text(
            json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(json.dumps({
            "ok": True,
            "process_pid": process_pid,
            "same_campaign": process_pid == EXPECTED_PID and gs == EXPECTED_GS,
            "tag": tag,
            "units": len(units),
            "unit_ids": [u["unit_id"] for u in units],
            "handle_types": sorted(set(u["handle_type"] for u in units)),
            "combats_size": combats["size"],
            "controller_map_counts": out["controller_map_counts"],
            "area_probe": area_probe,
            "occupied_summary": occupied_summary,
            "paths_nonempty": sum(1 for u in units if u["path"]),
            "commandlists_nonempty": sum(1 for u in units if u["commandlist_size"]),
            "top8": candidates[:8],
        }, indent=2, ensure_ascii=False, default=str))
    finally:
        p.close()


if __name__ == "__main__":
    main()
