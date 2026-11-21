# -*- coding: utf-8 -*-
from __future__ import annotations
import json, struct, sys
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

ROOT = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")
sys.path.insert(0, str(ROOT / "calling"))
from pe import PE
from mem import Proc, find_pid as mem_find_pid
from gamestate import detect_session, resolve_player_country, _rtti_name_from_vtable, read_campaign_summary

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
OUT = ROOT / "research" / "t197_bb5a0_tails_and_combats.json"
EXPECTED_PID = 12948
cs = Cs(CS_ARCH_X86, CS_MODE_64)


def is_ptr(x):
    return type(x) is int and 0x20000000000 < x < 0x7FFFFFFFFFFF


def pdx(p, a):
    return struct.unpack("<QII", p.read(a, 16))


def ptr_array(p, a, bound=4096):
    data, cap, size = pdx(p, a)
    if not 0 <= size <= cap <= max(bound, 200) or (size and not is_ptr(data)):
        return {"data": hex(data) if isinstance(data, int) else data, "cap": cap, "size": size, "items": []}
    return {"data": hex(data), "cap": cap, "size": size,
            "items": [struct.unpack("<Q", p.read(data + 8 * j, 8))[0] for j in range(size)]}


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


def dump_fn(pe, rva, n):
    off = pe.rva_to_off(rva)
    blob = pe.data[off:off + n]
    return [f"0x{i.address:x}  {i.mnemonic} {i.op_str}" for i in cs.disasm(blob, rva)]


def u32_at(pe, rva):
    off = pe.rva_to_off(rva)
    return struct.unpack_from("<I", pe.data, off)[0]


def main():
    pe = PE(EXE)
    out = {"authorized_by": ["pt183u", "pt180u"]}
    # sentinels
    # 0x10bb5bb + 0x232fce9 = 0x33EB2A4; 0x10bb5c5 is after the qword load at 0x10bb5be
    # 0x10bb5be: mov rax, qword ptr [rip + 0x232fcdb]; rip=0x10bb5c5; 0x10bb5c5+0x232fcdb=0x33EB2A0
    out["sentinels"] = {
        "at_33EB2A0": u32_at(pe, 0x33EB2A0),
        "at_33EB2A4": u32_at(pe, 0x33EB2A4),
        "at_33CB2A0": u32_at(pe, 0x33CB2A0),
        "at_33CB2A4": u32_at(pe, 0x33CB2A4),
    }

    for rva, name, n in (
        (0x10BBD79, "bb5a0_jne_25c_0x10bbd79", 0x80),
        (0x10BBD86, "bb5a0_jne_258_0x10bbd86", 0xC0),
        (0x10BB9EA, "bb5a0_empty_path_0x10bb9ea", 0x120),
        (0x18DAF60, "SetPath_execute_0x18daf60", 0x200),
        (0x18DFF70, "SetPath_isvalid_0x18dff70", 0x180),
    ):
        lines = dump_fn(pe, rva, n)
        out[name] = {"head": lines[:70], "calls": [ln for ln in lines if "  call " in ln][:20],
                     "mentions_70": [ln for ln in lines if "0x70" in ln]}
        (ROOT / "research" / f"_t197_clip_{name}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # also existing t194 setpath clips if short
    for rel in (
        "research/_t194_clip_COrderSetPathCommand_execute_0x18daf60.txt",
        "research/_t194_clip_COrderSetPathCommand_isvalid_0x18dff70.txt",
    ):
        pth = ROOT / rel
        if pth.exists() and pth.stat().st_size < 20000:
            out[rel] = pth.read_text(encoding="utf-8", errors="ignore")

    pid = mem_find_pid("hoi4.exe")
    out["pid"] = pid
    if pid != EXPECTED_PID:
        OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
        print(json.dumps({"pid": pid, "pid_ok": False, "sentinels": out["sentinels"]}, indent=2))
        return

    p = Proc(pid)
    pe2 = pe
    try:
        session = detect_session(p, pe2)
        gs = int(session["signals"]["gs_ptr"], 16)
        idler = int(session["signals"]["idler_ptr"], 16)
        co = int(resolve_player_country(p, gs)["country_ptr"], 16)
        pause = p.read(idler + 0x6C1, 1)[0]

        # GS_COMBATS 0x268 — try as pdx pointer array and as various layouts
        rec = {"gs": hex(gs), "pause": pause}
        for off in (0x250, 0x258, 0x260, 0x268, 0x270, 0x278, 0x280, 0x288):
            try:
                data, cap, size = pdx(p, gs + off)
                rec[hex(off)] = {
                    "pdx": [hex(data), cap, size],
                    "looks_array": 0 <= size <= cap <= 4096 and (size == 0 or is_ptr(data)),
                }
                if 0 <= size <= cap <= 4096 and size and is_ptr(data):
                    items = []
                    for j in range(min(size, 8)):
                        q = struct.unpack("<Q", p.read(data + 8 * j, 8))[0]
                        items.append({"ptr": hex(q), "class": cls(p, pe2, q)})
                    rec[hex(off)]["preview"] = items
            except Exception as e:
                rec[hex(off)] = {"error": str(e)}
        out["gs_combatish"] = rec

        # also search offsets.py comments around GS_COMBATS
        text = (ROOT / "calling" / "offsets.py").read_text(encoding="utf-8")
        idx = text.find("GS_COMBATS")
        out["gs_combats_context"] = text[max(0, idx - 400): idx + 800] if idx >= 0 else None
    finally:
        p.close()

    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    compact = {
        "sentinels": out["sentinels"],
        "jne_25c": out["bb5a0_jne_25c_0x10bbd79"]["head"],
        "jne_258": out["bb5a0_jne_258_0x10bbd86"]["head"],
        "empty_path": out["bb5a0_empty_path_0x10bb9ea"]["head"][:40],
        "setpath_exec_head": out["SetPath_execute_0x18daf60"]["head"][:50],
        "setpath_exec_70": out["SetPath_execute_0x18daf60"]["mentions_70"],
        "setpath_isvalid_head": out["SetPath_isvalid_0x18dff70"]["head"][:50],
        "gs_combatish": out.get("gs_combatish"),
        "gs_combats_context": out.get("gs_combats_context"),
    }
    print(json.dumps(compact, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
