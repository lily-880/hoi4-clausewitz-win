# -*- coding: utf-8 -*-
from __future__ import annotations
import json, struct, sys
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

ROOT = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")
sys.path.insert(0, str(ROOT / "calling"))
from pe import PE
from mem import Proc, find_pid as mem_find_pid
from gamestate import detect_session, resolve_player_country
from province import resolve_province

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
OUT = ROOT / "research" / "t197_bind_setpath.json"
TABLE = 0x35011E0
EXPECTED_PID = 12948
cs = Cs(CS_ARCH_X86, CS_MODE_64)

# known 1.19.5: factory idx = type_id - 0x2328


def dump_fn(pe, rva, n):
    off = pe.rva_to_off(rva)
    blob = pe.data[off:off + n]
    return [f"0x{i.address:x}  {i.mnemonic} {i.op_str}" for i in cs.disasm(blob, rva)]


def is_ptr(x):
    return type(x) is int and 0x20000000000 < x < 0x7FFFFFFFFFFF


def pdx(p, a):
    return struct.unpack("<QII", p.read(a, 16))


def ptr_array(p, a, bound=4096):
    data, cap, size = pdx(p, a)
    if not 0 <= size <= cap <= max(bound, 100) or (size and not is_ptr(data)):
        return []
    return [struct.unpack("<Q", p.read(data + 8 * j, 8))[0] for j in range(size)]


def main():
    pe = PE(EXE)
    out = {"authorized_by": ["pt183u", "pt180u"]}
    # scan factory table for IsValid 0x18dff70 or Execute 0x18daf60
    # table entry layout from prior work: typically {factory, size?} — look at t194 bind
    bind = {}
    t194 = ROOT / "research" / "t194_bind_cmds.json"
    if t194.exists():
        raw = json.loads(t194.read_text(encoding="utf-8"))
        # keep SetPath / NewFront related keys
        if isinstance(raw, dict):
            bind["t194_keys"] = list(raw.keys())[:60]
            for k, v in raw.items():
                if "path" in k.lower() or "SetPath" in str(k) or "set_path" in k.lower() or "409" in str(k):
                    bind[k] = v
        out["t194_subset"] = bind

    # factory table scan:  each slot historically 3 qwords or similar. Use prior method from t195 neighbors_factories if present.
    # We'll scan for immediate RVAs 0x18daf60 / 0x18dff70 in .text already known; find which factory function references them?
    # Better: table at 0x35011E0, entries used as: factory_addr = table[idx]; we can iterate, read function start, see if it's the factory that stores VT for SetPath.
    # From t194: SetPath execute 0x18daf60, isvalid 0x18dff70. Search pe.data for pointers to these in rdata near vtables, then find factory that movs that VT.

    # Search factory functions: many start at 0x18cxxxx. Load t193/t195 factory records.
    for name in ("research/t195_neighbors_factories.json", "research/t194_bind_cmds.json", "research/t193_bind_newfront.json"):
        pth = ROOT / name
        if pth.exists():
            try:
                obj = json.loads(pth.read_text(encoding="utf-8"))
            except Exception:
                continue
            s = json.dumps(obj, ensure_ascii=False)
            if "SetPath" in s or "18daf60" in s or "18dff70" in s or "set_path" in s.lower():
                out.setdefault("mentions", []).append(name)

    # brute: read factory table as array of qwords (function pointers). For each, if pe function bytes contain lea/mov of isvalid? Too heavy.
    # Instead scan rdata for vtable that has isvalid 0x18dff70 or execute 0x18daf60 as entries.
    rdata = next(s for s in pe.sections if s.name.startswith(".rdata"))
    blob = pe.data[rdata.raw_ptr:rdata.raw_ptr + rdata.raw_size]
    exec_le = struct.pack("<Q", 0x140000000 + 0x18daf60)
    valid_le = struct.pack("<Q", 0x140000000 + 0x18dff70)
    hits = []
    for needle, lab in ((exec_le, "execute"), (valid_le, "isvalid")):
        start = 0
        while True:
            i = blob.find(needle, start)
            if i < 0:
                break
            rva = rdata.virtual_address + i
            hits.append({"lab": lab, "slot_rva": hex(rva), "off_in_rdata": i})
            start = i + 1
            if len(hits) > 20:
                break
    out["vt_hits"] = hits

    # For each isvalid hit, walk back to plausible vtable start and record a few slots
    vts = []
    for h in hits:
        if h["lab"] != "isvalid":
            continue
        slot = int(h["slot_rva"], 16)
        # vtable usually: rtti/col at -8, then funcs. IsValid is often an early slot. Record -0x20..+0x40
        rec = {"isvalid_slot": hex(slot)}
        for delta in range(-0x40, 0x50, 8):
            off = pe.rva_to_off(slot + delta)
            val = struct.unpack_from("<Q", pe.data, off)[0]
            rec[f"{delta:+}"] = hex(val)
            if val == 0x140000000 + 0x18daf60:
                rec["execute_delta"] = delta
        vts.append(rec)
    out["vtables"] = vts

    # disasm 0x18e5f60 (SetPath execute calls this to apply path)
    lines = dump_fn(pe, 0x18E5F60, 0x280)
    out["apply_path_0x18e5f60"] = {
        "head": lines[:80],
        "calls": [ln for ln in lines if "  call " in ln][:30],
        "mentions_70": [ln for ln in lines if "0x70" in ln],
        "mentions_258": [ln for ln in lines if "0x258" in ln or "0x25c" in ln],
    }
    (ROOT / "research/_t197_clip_apply_path_0x18e5f60.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # live neighbors for spare units
    pid = mem_find_pid("hoi4.exe")
    out["pid"] = pid
    if pid == EXPECTED_PID:
        from mem import Proc
        p = Proc(pid)
        try:
            session = detect_session(p, pe)
            gs = int(session["signals"]["gs_ptr"], 16)
            neigh = {}
            for prov in (12757, 2072, 7944, 5097, 5010, 8036, 7980):
                try:
                    rec = resolve_province(p, prov, image_base=p.base, gs=gs)
                    # rec shape unknown; keep compact
                    if isinstance(rec, dict):
                        neigh[str(prov)] = {k: rec[k] for k in rec if k in ("id", "province_id", "neighbors", "land_neighbors", "adj", "name", "error") or "neigh" in k}
                        # if neighbors buried, include a short str
                        if "neighbors" not in neigh[str(prov)] and "land_neighbors" not in neigh[str(prov)]:
                            neigh[str(prov)]["keys"] = list(rec.keys())[:20]
                            neigh[str(prov)]["preview"] = {k: str(rec[k])[:120] for k in list(rec.keys())[:12]}
                    else:
                        neigh[str(prov)] = rec
                except TypeError:
                    try:
                        rec = resolve_province(p, prov)
                        neigh[str(prov)] = rec if not isinstance(rec, dict) else {k: str(rec[k])[:160] for k in list(rec.keys())[:15]}
                    except Exception as e:
                        neigh[str(prov)] = {"error": str(e)}
                except Exception as e:
                    neigh[str(prov)] = {"error": str(e)}
            out["neighbors"] = neigh
        finally:
            p.close()

    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    compact = {
        "vt_hits": out.get("vt_hits"),
        "vtables": out.get("vtables"),
        "t194_subset_keys": (out.get("t194_subset") or {}).get("t194_keys"),
        "mentions": out.get("mentions"),
        "apply_head": out["apply_path_0x18e5f60"]["head"][:60],
        "apply_calls": out["apply_path_0x18e5f60"]["calls"],
        "apply_70": out["apply_path_0x18e5f60"]["mentions_70"],
        "apply_258": out["apply_path_0x18e5f60"]["mentions_258"],
        "neighbors": out.get("neighbors"),
    }
    print(json.dumps(compact, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
