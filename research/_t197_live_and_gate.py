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
OUT = ROOT / "research" / "t197_live_and_gate.json"
EXPECTED_PID = 12948
cs = Cs(CS_ARCH_X86, CS_MODE_64)


def is_ptr(x):
    return type(x) is int and 0x20000000000 < x < 0x7FFFFFFFFFFF


def pdx(p, a):
    return struct.unpack("<QII", p.read(a, 16))


def ptr_array(p, a, bound=4096):
    data, cap, size = pdx(p, a)
    if not 0 <= size <= cap <= max(bound, 100) or (size and not is_ptr(data)):
        return []
    return [struct.unpack("<Q", p.read(data + 8 * j, 8))[0] for j in range(size)]


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


def hexdump(b):
    return " ".join(f"{x:02x}" for x in b)


def main():
    out = {"authorized_by": ["pt183u", "pt180u"]}
    pe = PE(EXE)
    # 0x10bb5a0 is the helper NewFront gate calls on the parent instance
    for rva, name, n in ((0x10BB5A0, "helper_10bb5a0", 0x280), (0x10B8A40, "helper_10b8a40", 0x200)):
        lines = dump_fn(pe, rva, n)
        out[name] = {"head": lines[:80], "calls": [ln for ln in lines if "  call " in ln][:30],
                     "mentions": [ln for ln in lines if any(s in ln for s in ("0x70", "0x258", "0x298", "0x299", "0x2ac"))]}
        (ROOT / "research" / f"_t197_clip_{name}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    pid = mem_find_pid("hoi4.exe")
    out["pid"] = pid
    out["pid_ok"] = pid == EXPECTED_PID
    if pid != EXPECTED_PID:
        OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"pid": pid, "pid_ok": False}, indent=2))
        return

    p = Proc(pid)
    try:
        session = detect_session(p, pe)
        gs = int(session["signals"]["gs_ptr"], 16)
        idler = int(session["signals"]["idler_ptr"], 16)
        co = int(resolve_player_country(p, gs)["country_ptr"], 16)
        pause = p.read(idler + 0x6C1, 1)[0]
        speed = struct.unpack("<i", p.read(gs + 0x4BC, 4))[0]
        date = (read_campaign_summary(p, gs).get("verified") or {}).get("date_full")

        # theatres / instance raw
        tp = ptr_array(p, co + 0x168, 64)[0]
        gp = ptr_array(p, tp + 0x80, 256)[0]
        insts = ptr_array(p, gp + 0x98, 256)
        ip = insts[0]
        raw = p.read(ip, 0x3C8)
        fields = {
            "ptr": hex(ip),
            "class": cls(p, pe, ip),
            "type_30": struct.unpack_from("<I", raw, 0x30)[0],
            "plus90": struct.unpack_from("<I", raw, 0x90)[0],
            "plus224": struct.unpack_from("<I", raw, 0x224)[0],
            "id_244": struct.unpack_from("<I", raw, 0x244)[0],
            "exec_248": raw[0x248],
            "field_258": struct.unpack_from("<I", raw, 0x258)[0],
            "field_25c": struct.unpack_from("<I", raw, 0x25C)[0],
            "plus298": raw[0x298],
            "plus299": raw[0x299],
            "plus2a0_pdx": list(struct.unpack_from("<QII", raw, 0x2A0)),
            "plus2ac_as_size_if_pdx_at_2a0": struct.unpack_from("<I", raw, 0x2AC)[0],
        }
        # pdx-like around 280-2c0
        arrays = {}
        for off in range(0x270, 0x330, 8):
            data, cap, size = struct.unpack_from("<QII", raw, off)
            if 0 <= size <= cap <= 256 and (size == 0 or is_ptr(data)):
                arrays[hex(off)] = {"data": hex(data), "cap": cap, "size": size}
        fields["arrays_270_330"] = arrays
        fields["hex_290_2b8"] = hexdump(raw[0x290:0x2B8])
        fields["path70_pdx"] = list(struct.unpack_from("<QII", raw, 0x70))
        out["instance"] = fields
        out["session"] = {"pid": pid, "gs": hex(gs), "co": hex(co), "pause": pause, "speed": speed, "date": date}

        # combat table candidates: search known GS offsets from t182 if present
        # country units in_combat-like bytes: scan a few known offsets later
        # wars: country diplomacy
        # GS combats: try common researched offset if in offsets.py
        out["gs_scan_notes"] = "filled below if offsets known"

        # inventory of wars / combats pointers from offsets.py quickly
        off_text = (ROOT / "calling" / "offsets.py").read_text(encoding="utf-8")
        interesting = [ln.strip() for ln in off_text.splitlines() if any(k in ln.lower() for k in ("combat", "supply", "spotted", "crisis", "shortage", "war", "visible", "fow", "encirc", "isolated"))]
        out["offsets_mentions"] = interesting[:80]
    finally:
        p.close()

    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    compact = {
        "pid_ok": out["pid_ok"],
        "session": out.get("session"),
        "instance": out.get("instance"),
        "helper_10bb5a0_head": out["helper_10bb5a0"]["head"][:50],
        "helper_10bb5a0_calls": out["helper_10bb5a0"]["calls"],
        "helper_10bb5a0_mentions": out["helper_10bb5a0"]["mentions"],
        "offsets_mentions": out.get("offsets_mentions"),
    }
    print(json.dumps(compact, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
