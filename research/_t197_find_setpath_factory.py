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
from input_loaded_fields import LoadedReader, province_land_neighbors, province_adjacencies

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
OUT = ROOT / "research" / "t197_setpath_factory.json"
TABLE = 0x35011E0
EXPECTED_PID = 12948
VT = 0x2A85028
cs = Cs(CS_ARCH_X86, CS_MODE_64)


def main():
    pe = PE(EXE)
    out = {"authorized_by": ["pt183u", "pt180u"], "vt": hex(VT)}

    # t194 cmds entry if any
    raw = json.loads((ROOT / "research/t194_bind_cmds.json").read_text(encoding="utf-8"))
    cmds = raw.get("cmds") or raw
    setpath_keys = [k for k in (cmds.keys() if isinstance(cmds, dict) else []) if "path" in k.lower() or "Path" in k]
    out["t194_path_keys"] = setpath_keys
    for k in setpath_keys:
        out[f"t194_{k}"] = cmds[k]

    # Also dump a few cmd names
    if isinstance(cmds, dict):
        out["t194_cmd_names"] = list(cmds.keys())

    # Factory table: from prior work idx = type_id - 0x2328, entries are 8-byte function pointers.
    # Search each factory function's first 0x80 bytes for mov of VT 0x2A85028 (or lea).
    # Typical: lea rax, [rip+vt] / mov [rcx], rax. Also size often in an immediate.
    # Scan table as qwords until we hit 0s stretch.
    tab_off = pe.rva_to_off(TABLE)
    # read a generous number of entries
    n = 8000
    entries = []
    blob = pe.data[tab_off:tab_off + n * 8]
    needle = struct.pack("<I", VT)
    # search all factory functions referenced by the table for the VT immediate
    hits = []
    for i in range(n):
        fn = struct.unpack_from("<Q", blob, i * 8)[0]
        if not fn:
            continue
        # factory ptrs may be RVA or VA
        if fn > 0x140000000:
            rva = fn - 0x140000000
        else:
            rva = fn
        if not (0x1000 <= rva < 0x3500000):
            continue
        off = pe.rva_to_off(rva)
        if off is None:
            continue
        code = pe.data[off:off + 0xC0]
        if needle in code:
            # disasm to get size immediate and confirm VT
            lines = []
            for ins in cs.disasm(code, rva):
                lines.append(f"0x{ins.address:x}  {ins.mnemonic} {ins.op_str}")
                if ins.mnemonic == "ret":
                    break
            hits.append({"idx": i, "type_id": i + 0x2328, "factory_rva": hex(rva), "head": lines[:40]})
    out["factory_hits"] = hits

    # neighbors via official helper
    pid = mem_find_pid("hoi4.exe")
    out["pid"] = pid
    if pid == EXPECTED_PID:
        p = Proc(pid)
        try:
            session = detect_session(p, pe)
            gs = int(session["signals"]["gs_ptr"], 16)
            co = int(resolve_player_country(p, gs)["country_ptr"], 16)

            def rtti(a):
                return None

            # LoadedReader needs class; province helpers may not need class if they only read adj
            r = LoadedReader(p.read, rtti)
            neigh = {}
            for prov in (12757, 2072, 7944, 5097, 7980, 5010, 8036):
                try:
                    lands, ev = province_land_neighbors(r, prov)
                    neigh[str(prov)] = {"land": lands, "ev_keys": list(ev)[:12] if isinstance(ev, dict) else ev}
                except Exception as e:
                    try:
                        adj = province_adjacencies(r, prov)
                        neigh[str(prov)] = {"adj_error_fallback": str(e), "adj": {k: str(adj[k])[:200] for k in list(adj)[:15]} if isinstance(adj, dict) else str(adj)[:200]}
                    except Exception as e2:
                        neigh[str(prov)] = {"error": str(e), "error2": str(e2)}
            out["neighbors"] = neigh
        finally:
            p.close()

    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    compact = {
        "t194_cmd_names": out.get("t194_cmd_names"),
        "t194_path_keys": out.get("t194_path_keys"),
        "factory_hits": [
            {"idx": h["idx"], "type_id": h["type_id"], "factory_rva": h["factory_rva"], "head": h["head"][:25]}
            for h in hits
        ],
        "neighbors": out.get("neighbors"),
    }
    # include t194 setpath records
    for k, v in out.items():
        if k.startswith("t194_") and k not in ("t194_cmd_names", "t194_path_keys"):
            compact[k] = v
    print(json.dumps(compact, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
