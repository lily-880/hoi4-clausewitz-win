# -*- coding: utf-8 -*-
from __future__ import annotations
import json, struct, sys
from pathlib import Path

ROOT = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")
sys.path.insert(0, str(ROOT / "calling"))
from pe import PE
from mem import Proc, find_pid as mem_find_pid
from process import Backend
import move_order as mo

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
EXPECTED_PID = 12948
OUT = ROOT / "research" / "t197_live_sentinels.json"


def main():
    pid = mem_find_pid("hoi4.exe")
    p = Proc(pid)
    pe = PE(EXE)
    b = Backend()
    out = {"pid": pid, "base": hex(p.base)}
    try:
        # instruction 0x18dffb4: mov ecx, dword ptr [rip + 0x1b0b2ea]
        # confirm bytes
        raw = p.read(p.base + 0x18DFFB4, 16)
        out["isvalid_bytes_18dffb4"] = raw.hex()
        # 8B 0D rel32
        assert raw[0] == 0x8B and raw[1] == 0x0D
        rel1 = struct.unpack_from("<i", raw, 2)[0]
        addr1 = p.base + 0x18DFFB4 + 6 + rel1  # cmp of +0x25c uses this
        val1 = struct.unpack("<I", p.read(addr1, 4))[0]
        out["cmp_25c"] = {"rip_addr": hex(addr1), "rva": hex(addr1 - p.base), "value": val1}

        raw2 = p.read(p.base + 0x18DFFC2, 16)
        out["isvalid_bytes_18dffc2"] = raw2.hex()
        assert raw2[0] == 0x8B and raw2[1] == 0x0D
        rel2 = struct.unpack_from("<i", raw2, 2)[0]
        addr2 = p.base + 0x18DFFC2 + 6 + rel2
        val2 = struct.unpack("<I", p.read(addr2, 4))[0]
        out["cmp_258"] = {"rip_addr": hex(addr2), "rva": hex(addr2 - p.base), "value": val2}

        # PE-file constants at 0x33EB2A0 live
        live_a = p.base + 0x33EB2A0
        out["pe_33EB2A0_live"] = {
            "addr": hex(live_a),
            "dwords": list(struct.unpack("<II", p.read(live_a, 8))),
        }
        # instance
        inst = 0x20B45C456E0
        out["instance_258"] = list(struct.unpack("<II", p.read(inst + 0x258, 8)))
        out["match_25c"] = out["instance_258"][1] == val1
        out["match_258"] = out["instance_258"][0] == val2
    finally:
        p.close()
    Path(OUT).write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
