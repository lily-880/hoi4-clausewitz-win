from __future__ import annotations
import json, struct, sys
from pathlib import Path

ROOT = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")
sys.path.insert(0, str(ROOT / "calling"))
from pe import PE
from mem import Proc, find_pid as mem_find_pid
from gamestate import detect_session, resolve_player_country, _rtti_name_from_vtable

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
EXPECTED_PID = 12948
POST = ROOT / "research" / "t196_scaffold_post.json"
OUT = ROOT / "research" / "t196_leader_assign_inspect.json"


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


def main():
    post = json.loads(POST.read_text(encoding="utf-8"))
    posts = {k: post.get(k) for k in (
        "sl_army_dry", "sl_army_post", "sl_army_packed",
        "sl_ag_dry", "sl_ag_post", "sl_ag_packed",
        "sl_unit_dry", "sl_unit_post", "sl_unit_packed",
        "oa_post", "ex_post",
    )}
    p = Proc(mem_find_pid("hoi4.exe"))
    pe = PE(EXE)
    out = {"authorized_by": ["pt182u", "pt180u"], "posts": posts}
    try:
        session = detect_session(p, pe)
        gs = int(session["signals"]["gs_ptr"], 16)
        co = int(resolve_player_country(p, gs)["country_ptr"], 16)
        theatres = ptr_array(p, co + 0x168, 64)
        tp = theatres[0]
        og = ptr_array(p, tp + 0x80, 256)[0]
        ag = ptr_array(p, tp + 0x98, 256)[0]
        inst = ptr_array(p, og + 0x98, 256)[0]
        out["army"] = {
            "ptr": hex(og), "class": cls(p, pe, og), "handle": handle_at(p, og + 8),
            "leader_88": hex(struct.unpack("<Q", p.read(og + 0x88, 8))[0]),
            "leader_88_cls": cls(p, pe, struct.unpack("<Q", p.read(og + 0x88, 8))[0]),
        }
        out["ag"] = {
            "ptr": hex(ag), "class": cls(p, pe, ag), "handle": handle_at(p, ag + 8),
            "leader_88": hex(struct.unpack("<Q", p.read(ag + 0x88, 8))[0]),
            "leader_88_cls": cls(p, pe, struct.unpack("<Q", p.read(ag + 0x88, 8))[0]),
        }
        # walk leaders from country — find typical array. own_leaders used something.
        # CArmyLeader handle type 4713; scan country leader list if we can find 312/313/314
        # Try common country offsets used before? Look at input_loaded_fields via import.
        sys.path.insert(0, str(ROOT / "calling"))
        from input_loaded_fields import own_leaders, LoadedReader

        def rtti(a):
            return cls(p, pe, a)

        r = LoadedReader(p.read, rtti)
        leaders, ev = own_leaders(r, co)
        out["own_leaders_ev"] = ev
        # find raw pointers from ev if present
        raw_leaders = []
        # brute: country might have leaders at a known offset; search ev
        out["leader_reader_sample"] = leaders[:3]
        # locate leader objects: from previous work, leader handle 4713, id at some slot
        # Use theatre or country commander list. Scan country pointer arrays for CArmyLeader
        cands = {}
        for off in range(0, 0x800, 8):
            try:
                data, cap, size = pdx(p, co + off)
            except Exception:
                continue
            if not (1 <= size <= cap <= 64 and is_ptr(data)):
                continue
            items = []
            for j in range(size):
                q = struct.unpack("<Q", p.read(data + 8 * j, 8))[0]
                name = cls(p, pe, q)
                if name and "CArmyLeader" in (name or ""):
                    items.append(q)
            if items:
                cands[hex(off)] = {"size": size, "n_leaders": len(items), "first": hex(items[0])}
        out["country_leader_arrays"] = cands

        # also search all CArmyLeader in a wider set of arrays (size up to 256)
        leaders_found = []
        for off, rec in cands.items():
            data, cap, size = pdx(p, co + int(off, 16))
            for j in range(size):
                q = struct.unpack("<Q", p.read(data + 8 * j, 8))[0]
                name = cls(p, pe, q)
                if not (name and "CArmyLeader" in name):
                    continue
                # try several id/handle offsets
                h18 = handle_at(p, q + 0x18)
                h0 = handle_at(p, q + 0x8)
                h1048 = handle_at(p, q + 0x1048)
                deployed = p.read(q + 0x1068, 1)[0]
                # id candidates
                raw_ids = {
                    "u32_10": struct.unpack("<I", p.read(q + 0x10, 4))[0],
                    "u32_1c": struct.unpack("<I", p.read(q + 0x1C, 4))[0],
                    "h8": h0,
                    "h18": h18,
                }
                leaders_found.append({
                    "ptr": hex(q),
                    "ids": raw_ids,
                    "assigned_1048": h1048,
                    "assigned_1048_resolved": cls(p, pe, 0),  # placeholder
                    "deployed_1068": deployed,
                })
        # filter those with id 312/313/314 in any slot
        interesting = []
        for L in leaders_found:
            vals = [L["ids"]["u32_10"], L["ids"]["u32_1c"], L["ids"]["h8"][1], L["ids"]["h18"][1]]
            if any(v in (312, 313, 314) for v in vals):
                h = L["assigned_1048"]
                resolved = None
                # try resolve handle via 0x2284870 we can't call; just record
                L["maybe_ids"] = vals
                interesting.append(L)
        out["n_cleaders"] = len(leaders_found)
        out["leaders_312_314_raw"] = interesting

        # assigned units at instance+0x210
        data, cap, size = pdx(p, inst + 0x210)
        rec = {"data": hex(data), "cap": cap, "size": size}
        if size and is_ptr(data):
            q = struct.unpack("<Q", p.read(data, 8))[0]
            rec["elem0"] = hex(q)
            rec["elem0_cls"] = cls(p, pe, q)
            unadj = q - 0xB8
            rec["unadj_b8"] = hex(unadj)
            rec["unadj_cls"] = cls(p, pe, unadj)
            if is_ptr(unadj) and rec["unadj_cls"] and "CArmy" in rec["unadj_cls"]:
                rec["unit_id"] = struct.unpack("<I", p.read(unadj + 0x1C, 4))[0]
                rec["unit_handle_18"] = handle_at(p, unadj + 0x18)
            # also try elem as already primary
            if rec["elem0_cls"] and "CArmy" in rec["elem0_cls"]:
                rec["elem_unit_id_1c"] = struct.unpack("<I", p.read(q + 0x1C, 4))[0]
                rec["elem_unit_id_1c_unadj"] = struct.unpack("<I", p.read(unadj + 0x1C, 4))[0] if is_ptr(unadj) else None
        out["instance_210"] = rec
        out["instance_248"] = p.read(inst + 0x248, 1)[0]
        out["instance_path70_n"] = pdx(p, inst + 0x70)[2]
        out["pause"] = p.read(int(session["signals"]["idler_ptr"], 16) + 0x6C1, 1)[0]
    finally:
        p.close()
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
