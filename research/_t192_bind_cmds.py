# research/_t192_bind_cmds.py — read-only 1.19.5 factory/RTTI bind for OrderGroup / SetArmyLeader
from __future__ import annotations
import json, struct, sys, bisect
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

sys.path.insert(0, "calling")
from pe import PE
from mem import Proc, find_pid
from gamestate import _rtti_name_from_vtable

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
TABLE = 0x35011E0
# 1.19.4 catalog
CATALOG = {
    "COrderGroupCommand": {
        "factory_idx": 2983, "type_id": 0x2ECF, "old_factory": 0x18D00D0,
        "old_vt": 0x2A83D68, "old_isvalid": 0x18DEFE0, "old_execute": 0x18D64F0,
        "old_size": 0x60,
    },
    "CArmyGroupCommand": {
        "factory_idx": 5433, "type_id": 0x3861, "old_factory": 0x18CF710,
        "old_vt": 0x2A83ED8, "old_isvalid": 0x18DDF70, "old_execute": 0x18D25D0,
        "old_size": 0x80,
    },
    "CSetArmyLeaderCommand": {
        "factory_idx": 3369, "type_id": 0x3051, "old_factory": 0x18D0BA0,
        "old_vt": 0x2A85520, "old_isvalid": 0x18E04D0, "old_execute": 0x18DB2C0,
        "old_size": 0x40,
    },
    "CDeleteOrderGroupCommand": {
        "factory_idx": None, "type_id": None, "old_factory": None,
        "old_vt": None, "old_isvalid": None, "old_execute": None, "old_size": None,
    },
}

WANT = list(CATALOG) + ["COrdersGroup", "CArmyGroup", "CTheatre", "CArmyLeader", "CTheaterGroup"]


def pe_off_to_rva(pe, off):
    for s in pe.sections:
        if s.raw_ptr <= off < s.raw_ptr + s.raw_size:
            return s.virtual_address + (off - s.raw_ptr)
    return None


def find_vtables(pe, name):
    needle = (".?AV" + name + "@@").encode("ascii")
    data = pe.data
    rvas = []
    start = 0
    while True:
        i = data.find(needle, start)
        if i < 0:
            break
        rvas.append(pe_off_to_rva(pe, i))
        start = i + 1
    vts = []
    rdata = [s for s in pe.sections if s.name.startswith(".rdata") or s.name.startswith(".data")]
    for str_rva in rvas:
        if str_rva is None:
            continue
        typedecl = str_rva - 0x10
        target = struct.pack("<I", typedecl)
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
                            vts.append(s2.virtual_address + m + 8)
                            k = m + 1
                off = j + 1
    uniq = []
    for v in vts:
        if v not in uniq:
            uniq.append(v)
    return uniq


def main():
    pe = PE(EXE)
    pid = find_pid("hoi4.exe")
    p = Proc(pid)
    cs = Cs(CS_ARCH_X86, CS_MODE_64)
    pd = next(s for s in pe.sections if s.name == ".pdata")
    raw = pe.data[pd.raw_ptr:pd.raw_ptr + pd.raw_size]
    functions = []
    for i in range(0, len(raw) - 11, 12):
        start, end, _ = struct.unpack_from("<III", raw, i)
        if start and end and end > start:
            functions.append((start, end))
    starts = [s for s, e in functions]

    def rva_to_off(rva):
        return pe.rva_to_off(rva)

    def read_rva(rva, n):
        off = rva_to_off(rva)
        return pe.data[off:off + n] if off is not None else b""

    def func_of(target):
        i = bisect.bisect_right(starts, target) - 1
        if i >= 0 and functions[i][0] <= target < functions[i][1]:
            return functions[i]
        return None

    def disasm(start, end, limit=0x400):
        blob = read_rva(start, min(end - start, limit))
        return [{"rva": hex(i.address), "asm": i.mnemonic + " " + i.op_str} for i in cs.disasm(blob, start)]

    try:
        def q(a):
            return struct.unpack("<Q", p.read(a, 8))[0]

        base = p.base
        rtti = {n: [hex(v) for v in find_vtables(pe, n)] for n in WANT}

        slots = {}
        for name, cat in CATALOG.items():
            if not cat.get("factory_idx"):
                continue
            idx = cat["factory_idx"]
            fn = q(base + TABLE + idx * 8)
            rva = fn - base if base <= fn < base + p.image_size else None
            head = p.read(fn, 16) if rva else b""
            rec = {
                "idx": idx,
                "factory_rva": hex(rva) if rva else None,
                "old_factory": hex(cat["old_factory"]),
                "delta": (rva - cat["old_factory"]) if rva else None,
                "head16": head.hex(),
            }
            if head[0:1] == b"\xb9" or (len(head) >= 8 and head[5:6] == b"\xb9"):
                # find mov ecx, imm
                if head.startswith(b"\xb9"):
                    rec["mov_ecx_imm"] = hex(struct.unpack_from("<I", head, 1)[0])
                else:
                    i = head.find(b"\xb9")
                    if i >= 0 and i + 5 <= len(head):
                        rec["mov_ecx_imm"] = hex(struct.unpack_from("<I", head, i + 1)[0])
            # plus70 guesses
            rec["old_vt"] = hex(cat["old_vt"])
            rec["old_isvalid"] = hex(cat["old_isvalid"])
            rec["old_execute"] = hex(cat["old_execute"])
            rec["guess_isvalid_plus70"] = hex(cat["old_isvalid"] + 0x70)
            rec["guess_execute_plus70"] = hex(cat["old_execute"] + 0x70)
            slots[name] = rec

        # resolve current vtable slots IsValid 0x48 / Execute 0x50
        bound = {}
        for name, cat in CATALOG.items():
            if name not in slots:
                continue
            vts = [int(x, 16) for x in rtti.get(name, [])]
            # pick primary (usually first / matches old+delta)
            rec = {"rtti_vts": [hex(v) for v in vts]}
            chosen = vts[0] if vts else None
            rec["vt"] = hex(chosen) if chosen else None
            if chosen:
                rec["rtti"] = _rtti_name_from_vtable(pe, chosen)
                isvalid = q(base + chosen + 0x48)
                execute = q(base + chosen + 0x50)
                rec["isvalid"] = hex(isvalid - base) if base <= isvalid < base + p.image_size else hex(isvalid)
                rec["execute"] = hex(execute - base) if base <= execute < base + p.image_size else hex(execute)
                rec["isvalid_delta"] = (isvalid - base - cat["old_isvalid"]) if base <= isvalid < base + p.image_size else None
                rec["execute_delta"] = (execute - base - cat["old_execute"]) if base <= execute < base + p.image_size else None
                rec["vt_delta"] = chosen - cat["old_vt"]
            bound[name] = rec

        clips = {}
        for name, rec in bound.items():
            for kind in ("isvalid", "execute"):
                rva = int(rec[kind], 16) if rec.get(kind) else None
                if rva is None or rva < 0x1000:
                    continue
                bounds = func_of(rva)
                if not bounds:
                    continue
                code = disasm(bounds[0], bounds[1], min(bounds[1] - bounds[0], 0x600))
                key = f"{name}_{kind}"
                path = ROOT_CLIP if False else Path("research") / f"_t192_clip_{name}_{kind}_{rec[kind]}.txt"
                path.write_text(
                    f"function {hex(bounds[0])}-{hex(bounds[1])} size {bounds[1]-bounds[0]}\n"
                    + "\n".join(f"{c['rva']}  {c['asm']}" for c in code) + "\n",
                    encoding="utf-8",
                )
                # interesting refs to 0x28/0x48/0x50/0x58/handle
                interesting = [c for c in code if any(s in c["asm"] for s in (
                    "0x28", "0x30", "0x34", "0x38", "0x3c", "0x48", "0x50", "0x58",
                    "0x5c", "0x40", "+ 0x10", "call ",
                ))]
                clips[key] = {
                    "function": hex(bounds[0]),
                    "end": hex(bounds[1]),
                    "size": bounds[1] - bounds[0],
                    "head": code[:12],
                    "interesting_n": len(interesting),
                    "interesting_head": interesting[:40],
                    "clip": str(path),
                }

        out = {
            "pid": pid,
            "base": hex(base),
            "factory_slots": slots,
            "bound": bound,
            "rtti": rtti,
            "clips": {k: {kk: vv for kk, vv in v.items() if kk != "interesting_head"} | {"interesting_head": v["interesting_head"]} for k, v in clips.items()},
        }
        Path("research/t192_bind_cmds.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({
            "factory_slots": slots,
            "bound": bound,
            "rtti": rtti,
            "clip_funcs": {k: {"fn": v["function"], "size": v["size"]} for k, v in clips.items()},
        }, indent=2))
        # print interesting heads compact
        for k, v in clips.items():
            print("=" * 60, k)
            for c in v["interesting_head"][:25]:
                print(f"  {c['rva']}  {c['asm']}")
    finally:
        p.close()


if __name__ == "__main__":
    main()
