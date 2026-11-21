# research/_t191_post_rva.py — bind FN_CMD_QUEUE_POST / DummyServer on 1.19.5
from __future__ import annotations
import json, struct, sys
from pathlib import Path

sys.path.insert(0, "calling")
from pe import PE
from mem import Proc, find_pid
from gamestate import _rtti_name_from_vtable
import post_abi

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
WANT = ["CDummyServer", "CSession", "CNetworkServer"]


def pe_off_to_rva(pe, off):
    for s in pe.sections:
        if s.raw_ptr <= off < s.raw_ptr + s.raw_size:
            return s.virtual_address + (off - s.raw_ptr)
    return None


def find_vt(pe, name):
    needle = (".?AV" + name + "@@").encode("ascii")
    data = pe.data
    str_offs = []
    start = 0
    while True:
        i = data.find(needle, start)
        if i < 0:
            break
        str_offs.append(i)
        start = i + 1
    rvas = [pe_off_to_rva(pe, o) for o in str_offs]
    vts = []
    rdata = [s for s in pe.sections if s.name.startswith(".rdata") or s.name.startswith(".data")]
    for str_rva in rvas:
        if str_rva is None:
            continue
        typedecl_rva = str_rva - 0x10
        target = struct.pack("<I", typedecl_rva)
        for s in rdata:
            chunk = data[s.raw_ptr:s.raw_ptr + s.raw_size]
            off = 0
            while True:
                j = chunk.find(target, off)
                if j < 0:
                    break
                if j >= 0x0C:
                    col_rva = s.virtual_address + (j - 0x0C)
                    va = pe.image_base + col_rva
                    needle2 = struct.pack("<Q", va)
                    for s2 in rdata:
                        chunk2 = data[s2.raw_ptr:s2.raw_ptr + s2.raw_size]
                        k = 0
                        while True:
                            m = chunk2.find(needle2, k)
                            if m < 0:
                                break
                            vt_rva = s2.virtual_address + m + 8
                            vts.append(vt_rva)
                            k = m + 1
                off = j + 1
    uniq = []
    for v in vts:
        if v not in uniq:
            uniq.append(v)
    return {"typedef_rvas": [hex(x) if x else None for x in rvas], "vt_rvas": [hex(x) for x in uniq]}


def main():
    pe = PE(EXE)
    pid = find_pid("hoi4.exe")
    p = Proc(pid)
    try:
        def q(a):
            return struct.unpack("<Q", p.read(a, 8))[0]

        rtti = {n: find_vt(pe, n) for n in WANT}
        base = p.base
        dummy_vts = [int(x, 16) for x in rtti["CDummyServer"]["vt_rvas"]]
        dummy = {}
        for rva in dummy_vts:
            slots = []
            for i, off in enumerate((0x00, 0x28, 0x30, 0x40, 0x78)):
                fn = q(base + rva + off)
                frva = fn - base if base <= fn < base + p.image_size else None
                slots.append({"off": hex(off), "rva": hex(frva) if frva is not None else hex(fn)})
            dummy[hex(rva)] = {"rtti": _rtti_name_from_vtable(pe, rva), "slots": slots}

        def head(rva, n=16):
            return p.read(base + rva, n).hex()

        candidates = {
            "old_FN_CMD_QUEUE_POST": 0x22C41E0,
            "old_plus70": 0x22C4250,
            "old_FN_SESSION_UPDATE": 0x22C6410,
            "session_update_plus70": 0x22C6480,
            "old_FN_EXECUTE_LOOP": 0x22C4710,
            "execute_loop_plus70": 0x22C4780,
            "old_SINK_DUMMY": 0x23F5CD0,
            "sink_plus70": 0x23F5D40,
            "old_DRAIN_DUMMY": 0x23F64E0,
            "drain_plus70": 0x23F6550,
            "old_LOOKUP": 0x22D8D20,
            "lookup_plus70": 0x22D8D90,
        }
        heads = {k: head(v) for k, v in candidates.items()}

        # live session server vt vs CDummyServer
        sess = q(base + post_abi.G_SESSION)
        server = q(sess + post_abi.CSession_SERVER) if sess else 0
        server_vt = q(server) if server else 0
        server_vt_rva = server_vt - base if base <= server_vt < base + p.image_size else None

        out = {
            "pid": pid,
            "rtti": rtti,
            "dummy_vt_slots": dummy,
            "old_CDummyServer_VT": hex(post_abi.CDummyServer_VT),
            "live_session": hex(sess),
            "live_server": hex(server),
            "live_server_vt_rva": hex(server_vt_rva) if server_vt_rva is not None else None,
            "live_server_rtti": _rtti_name_from_vtable(pe, server_vt_rva) if server_vt_rva is not None else None,
            "heads": heads,
        }
        Path("research/t191_post_rva.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(out, indent=2))
    finally:
        p.close()


if __name__ == "__main__":
    main()
