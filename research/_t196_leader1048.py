from __future__ import annotations
import json, struct, sys
from pathlib import Path

ROOT = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")
sys.path.insert(0, str(ROOT / "calling"))
from pe import PE
from mem import Proc, find_pid as mem_find_pid
from gamestate import detect_session, resolve_player_country, _rtti_name_from_vtable
from input_loaded_fields import own_leaders, LoadedReader

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
OUT = ROOT / "research" / "t196_leader1048.json"
POST = ROOT / "research" / "t196_scaffold_post.json"

def is_ptr(x):
    return type(x) is int and 0x20000000000 < x < 0x7FFFFFFFFFFF

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
    hist = {}
    for k in ("theatre_after_og", "theatre_after_ag", "theatre_after_oa", "theatre_final"):
        recs = []
        for th in (post.get(k) or []):
            for og in th.get("orders_groups") or []:
                recs.append({"kind": "og", "handle": og.get("handle"), "name": og.get("name"),
                             "leader_ptr": og.get("leader_ptr"), "leader_handle": og.get("leader_handle")})
            for ag in th.get("army_groups") or []:
                recs.append({"kind": "ag", "handle": ag.get("handle"), "name": ag.get("name"),
                             "leader_ptr": ag.get("leader_ptr"), "leader_handle": ag.get("leader_handle")})
        hist[k] = recs

    p = Proc(mem_find_pid("hoi4.exe"))
    pe = PE(EXE)
    out = {"hist": hist}
    try:
        session = detect_session(p, pe)
        gs = int(session["signals"]["gs_ptr"], 16)
        co = int(resolve_player_country(p, gs)["country_ptr"], 16)
        def rtti(a):
            return cls(p, pe, a)
        r = LoadedReader(p.read, rtti)
        leaders, ev = own_leaders(r, co)
        rows = []
        for link, rec in zip(ev["links"], leaders):
            lp = int(link["leader_ptr"], 16)
            h1048 = handle_at(p, lp + 0x1048)
            raw1048 = p.read(lp + 0x1048, 16).hex()
            dep = p.read(lp + 0x1068, 8).hex()
            # also scan nearby for a nonempty handle
            nearby = {}
            for off in (0x1020, 0x1028, 0x1030, 0x1038, 0x1040, 0x1048, 0x1050, 0x1058, 0x1060, 0x1068, 0x1070, 0x1078, 0x88, 0x90):
                h = handle_at(p, lp + off)
                q = struct.unpack("<Q", p.read(lp + off, 8))[0]
                if h != [0, 0] or (is_ptr(q)):
                    nearby[hex(off)] = {"handle": h, "u64": hex(q), "cls": cls(p, pe, q)}
            if rec.get("leader_id") in (312, 313, 314) or h1048 != [0, 0]:
                rows.append({
                    "leader_id": rec.get("leader_id"),
                    "name": rec.get("name"),
                    "assigned_to": rec.get("assigned_to"),
                    "ptr": link["leader_ptr"],
                    "h1048": h1048,
                    "raw1048_16": raw1048,
                    "deployed_1068": dep,
                    "nearby": nearby,
                })
        out["interesting"] = rows
        out["n_leaders"] = len(leaders)
        out["n_assigned_reader"] = sum(1 for x in leaders if x.get("assigned_to"))
    finally:
        p.close()
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))

if __name__ == "__main__":
    main()
