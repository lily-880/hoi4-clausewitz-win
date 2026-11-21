from __future__ import annotations
import json, struct, sys
from pathlib import Path

ROOT = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")
sys.path.insert(0, str(ROOT / "calling"))

from pe import PE
from mem import Proc, find_pid as mem_find_pid
from gamestate import detect_session, resolve_player_country, _rtti_name_from_vtable
from province import resolve_province
from input_loaded_fields import LoadedReader, province_land_neighbors

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
TABLE = 0x35011E0
EXPECTED_PID = 8500
OUT = ROOT / "research" / "t195_neighbors_factories.json"

# ITA-adjacent ETH provinces from t191 survey — avoid for plan/move if possible
ITA_ADJ = {1984, 13237, 13238, 4995, 8062, 12812}
CANDS = [5010, 8036, 7980, 2072, 5097, 7944, 12757, 1984, 13237, 13238, 4995, 8062, 12812]

FACTORIES = {
    "CMoveCommand": 1402,
    "COrderGroupCommand": 2983,
    "CSetArmyLeaderCommand": 3369,
    "CArmyGroupCommand": 5433,
    "COrderNewRootCommand": 4096,
    "COrderNewFrontCommand": 4095,
    "COrderAssignCommand": 3350,
    "COrderExecuteCommand": 3352,
    "CPauseGame": 1732,
}

KNOWN = {
    "CMoveCommand": {"factory": 0x13fb070},
    "CSetArmyLeaderCommand": {"factory": 0x18d0c10, "vt": 0x2a85e20, "size": 0x40},
    "CArmyGroupCommand": {"factory": 0x18cf780, "vt": 0x2A846E0, "size": 0x80},
    "COrderNewRootCommand": {"factory": 0x18d0440, "vt": 0x2A856A0, "size": 0x70},
    "COrderNewFrontCommand": {"factory": 0x18d03b0, "vt": 0x2A853A0, "size": 0x70},
    "COrderAssignCommand": {"factory": 0x18cfd10, "vt": 0x2a84ce0, "size": 0x50},
    "COrderExecuteCommand": {"factory": 0x18d00e0, "vt": 0x2a85d60, "size": 0x38},
    "CPauseGame": {"factory": 0xe53a00, "vt": 0x29e6e10, "size": 0x50},
}


def is_ptr(x):
    return type(x) is int and 0x20000000000 < x < 0x7FFFFFFFFFFF


def cls_fn(p, pe):
    def cls(a):
        if not is_ptr(a):
            return None
        try:
            vt = struct.unpack("<Q", p.read(a, 8))[0]
        except OSError:
            return None
        if not p.base <= vt < p.base + p.image_size:
            return None
        return _rtti_name_from_vtable(pe, vt - p.base)
    return cls


def factory_info(p, pe, idx):
    slot = struct.unpack("<Q", p.read(p.base + TABLE + idx * 8, 8))[0]
    if not (p.base <= slot < p.base + p.image_size):
        return {"idx": idx, "error": "bad_slot", "slot": hex(slot)}
    rva = slot - p.base
    head = pe.data[pe.rva_to_off(rva):pe.rva_to_off(rva) + 16]
    size = None
    for i in range(0, 12):
        if head[i] == 0xB9:
            size = struct.unpack_from("<I", head, i + 1)[0]
            break
    return {"idx": idx, "factory": hex(rva), "size": size, "head": head.hex()}


def main():
    out = {"authorized_by": ["pt181u", "pt180u"], "pid": None}
    pid = mem_find_pid("hoi4.exe")
    out["pid"] = pid
    if pid != EXPECTED_PID:
        out["ok"] = False
        out["error"] = "PID_MISMATCH"
        OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return

    p = Proc(pid)
    pe = PE(EXE)
    try:
        session = detect_session(p, pe)
        gs = int(session["signals"]["gs_ptr"], 16)
        co = int(resolve_player_country(p, gs)["country_ptr"], 16)
        r = LoadedReader(p.read, cls_fn(p, pe))
        info = {}
        for pid_prov in CANDS:
            try:
                prov = resolve_province(p, pid_prov, image_base=p.base, gs=gs)
            except TypeError:
                try:
                    prov = resolve_province(p, pid_prov, p.base, gs)
                except Exception as e:
                    info[str(pid_prov)] = {"err": f"resolve {e}"}
                    continue
            except Exception as e:
                info[str(pid_prov)] = {"err": f"resolve {e}"}
                continue
            try:
                nbs, ev = province_land_neighbors(r, prov)
            except Exception as e:
                info[str(pid_prov)] = {"err": f"neighbors {e}", "prov": str(type(prov))}
                continue
            ids = []
            if isinstance(nbs, list):
                for item in nbs:
                    if isinstance(item, int):
                        ids.append(item)
                    elif isinstance(item, dict):
                        ids.append(item.get("id") or item.get("province_id"))
            info[str(pid_prov)] = {
                "neighbors": ids,
                "ita_adjacent": pid_prov in ITA_ADJ,
                "safe_interior_neighbors": [i for i in ids if i and i not in ITA_ADJ],
            }

        # land pairs among interior candidates
        interior = [c for c in CANDS if c not in ITA_ADJ]
        pairs = []
        seen = set()
        for a in interior:
            nbs = info.get(str(a), {}).get("neighbors") or []
            for b in nbs:
                if b in interior and a != b:
                    key = tuple(sorted((a, b)))
                    if key not in seen:
                        seen.add(key)
                        pairs.append(list(key))

        facts = {}
        for name, idx in FACTORIES.items():
            rec = factory_info(p, pe, idx)
            known = KNOWN.get(name) or {}
            if known.get("factory") is not None:
                rec["rva_match"] = rec.get("factory") == hex(known["factory"]).lower() or rec.get("factory") == hex(known["factory"])
                rec["expected_factory"] = hex(known["factory"])
            if known.get("size") is not None:
                rec["size_match"] = rec.get("size") == known["size"]
                rec["expected_size"] = known["size"]
            facts[name] = rec

        out.update({
            "ok": True,
            "gs": hex(gs),
            "co": hex(co),
            "provinces": info,
            "safe_interior_pairs": pairs,
            "recommended_move": [5010, 8036] if [5010, 8036] in pairs or [8036, 5010] in pairs else None,
            "factories": facts,
        })
    finally:
        p.close()

    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
