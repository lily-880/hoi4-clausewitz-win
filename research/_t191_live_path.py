# research/_t191_live_path.py — post-move readback of all 21 ETH paths (read-only)
from __future__ import annotations
import json, os, struct, sys
from pathlib import Path

os.environ["CLAUSEWITZ_ALLOW_POST"] = "0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"] = "0"
sys.path.insert(0, "calling")
from pe import PE
from mem import Proc, find_pid
from gamestate import detect_session, resolve_player_country, read_campaign_summary

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"

def main():
    pid = find_pid("hoi4.exe")
    p = Proc(pid)
    pe = PE(EXE)
    try:
        def q(a):
            return struct.unpack("<Q", p.read(a, 8))[0]
        def u32(a):
            return struct.unpack("<I", p.read(a, 4))[0]
        def i32(a):
            return struct.unpack("<i", p.read(a, 4))[0]
        def pdx(a):
            data, cap, size = struct.unpack("<QII", p.read(a, 16))
            return data, cap, size
        def u32arr(a, bound=64):
            data, cap, size = pdx(a)
            if not 0 <= size <= cap <= bound:
                return [], {"data": hex(data), "cap": cap, "size": size, "invalid": True}
            if size and data < 0x10000:
                return [], {"data": hex(data), "cap": cap, "size": size, "invalid": True}
            if size == 0:
                return [], {"data": hex(data), "cap": cap, "size": size}
            raw = p.read(data, size * 4)
            return list(struct.unpack("<" + "I" * size, raw)), {"data": hex(data), "cap": cap, "size": size}

        session = detect_session(p, pe)
        gs = int(session["signals"]["gs_ptr"], 16)
        res = resolve_player_country(p, gs)
        co = int(res["country_ptr"], 16)
        summary = read_campaign_summary(p, gs)
        ver = summary.get("verified") or {}
        date = ver.get("date_full") or ver.get("date") or {}
        idler = int(session["signals"].get("idler_ptr") or "0", 16)
        data, cap, n = pdx(co + 0x290)
        units = []
        for j in range(n):
            ap = q(data + 8 * j)
            path, ph = u32arr(ap + 0x200)
            full, fh = u32arr(ap + 0x220)
            cl = pdx(ap + 0x2C0)
            units.append({
                "unit_id": u32(ap + 0x1C),
                "province_id": u32(ap + 0x28),
                "path": path,
                "path_hdr": ph,
                "full_path": full,
                "full_path_hdr": fh,
                "commandlist_size": cl[2],
                "movement_progress": i32(ap + 0x240),
            })
        out = {
            "read_only": True,
            "pid": pid,
            "in_game": bool(session.get("in_game")),
            "tag_index": res.get("player_index"),
            "date": date,
            "pause_flag_6c1": p.read(idler + 0x6C1, 1)[0] if idler else None,
            "speed_index": i32(gs + 0x4BC),
            "n_units": len(units),
            "units": units,
            "nonempty_paths": [u for u in units if u["path"]],
            "nonempty_full_paths": [u for u in units if u["full_path"]],
            "nonempty_commandlists": [u["unit_id"] for u in units if u["commandlist_size"]],
        }
        Path("research/t191_live_path.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({
            "pid": pid,
            "pause": out["pause_flag_6c1"],
            "speed_index": out["speed_index"],
            "date": date,
            "n_units": len(units),
            "nonempty_paths": out["nonempty_paths"],
            "nonempty_full_paths": out["nonempty_full_paths"],
            "nonempty_commandlists": out["nonempty_commandlists"],
            "unit_1829": next(u for u in units if u["unit_id"]==1829),
        }, indent=2, ensure_ascii=False))
    finally:
        p.close()

if __name__ == "__main__":
    main()
