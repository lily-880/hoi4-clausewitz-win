# -*- coding: utf-8 -*-
from __future__ import annotations
import json, struct, sys
from pathlib import Path

ROOT = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")
sys.path.insert(0, str(ROOT / "calling"))
from pe import PE
from mem import Proc, find_pid as mem_find_pid
from gamestate import detect_session, resolve_player_country, read_campaign_summary
from config import allow_post
from input_loaded_fields import LoadedReader, own_plans

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
EXPECTED_PID = 12948
OUT = ROOT / "research" / "t196_final_pause.json"

def main():
    pid = mem_find_pid("hoi4.exe")
    out = {"found_pid": pid, "pid_ok": pid == EXPECTED_PID, "allow_post": allow_post()}
    if pid != EXPECTED_PID:
        OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(out, indent=2))
        return
    p = Proc(pid)
    pe = PE(EXE)
    try:
        session = detect_session(p, pe)
        gs = int(session["signals"]["gs_ptr"], 16)
        idler = int(session["signals"]["idler_ptr"], 16)
        co = int(resolve_player_country(p, gs)["country_ptr"], 16)
        pause = p.read(idler + 0x6C1, 1)[0]
        speed = struct.unpack("<i", p.read(gs + 0x4BC, 4))[0]
        date = (read_campaign_summary(p, gs).get("verified") or {}).get("date_full")
        def rtti(a):
            return None
        # own_plans needs class_name; use gamestate rtti
        from gamestate import _rtti_name_from_vtable
        def rtti2(a):
            if not (0x20000000000 < a < 0x7FFFFFFFFFFF):
                return None
            try:
                vt = struct.unpack("<Q", p.read(a, 8))[0]
            except OSError:
                return None
            if not p.base <= vt < p.base + p.image_size:
                return None
            return _rtti_name_from_vtable(pe, vt - p.base)
        r = LoadedReader(p.read, rtti2)
        plans, ev = own_plans(r, co)
        out.update({
            "pause": pause,
            "speed": speed,
            "date": date,
            "plans": plans,
            "plans_ev": ev,
            "gate_open_exists": (ROOT / "research" / "safe_land_tool_gate.OPEN").exists(),
        })
    finally:
        p.close()
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))

if __name__ == "__main__":
    main()
