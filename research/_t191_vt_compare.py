import json, struct, sys
from pathlib import Path
sys.path.insert(0, "calling")
from pe import PE
from mem import Proc, find_pid
from process import Backend, find_pid as pfind
from handle import resolve_handle, HANDLE_TYPE_ARMY
import move_order as mo

profile = json.loads(Path("calling/tables/offsets_input_windows_1.19.5.json").read_text(encoding="utf-8-sig"))
pid = find_pid("hoi4.exe")
p = Proc(pid)
b = Backend()
try:
    army = resolve_handle(b, HANDLE_TYPE_ARMY, 1829, b.image_base)
    vt = struct.unpack("<Q", b.read(army, 8))[0] if army else 0
    live_rva = vt - b.image_base if army else None
    out = {
        "pid": pid,
        "backend_base": hex(b.image_base),
        "proc_base": hex(p.base),
        "bases_equal": b.image_base == p.base,
        "army": hex(army) if army else None,
        "live_vt": hex(vt) if vt else None,
        "live_rva": hex(live_rva) if live_rva is not None else None,
        "move_order.ARMY_VT": hex(mo.ARMY_VT),
        "move_order.MOVE_VT": hex(mo.MOVE_VT),
        "move_order.ACTION_VT": hex(mo.ACTION_VT),
        "move_order.FACTORY_RVA": hex(mo.FACTORY_RVA),
        "profile_CArmy": hex(profile.get("vtable_rvas", {}).get("CArmy") or profile.get("vtables", {}).get("CArmy") or 0),
        "profile_keys": list(profile.keys()),
        "match_move_order": live_rva == mo.ARMY_VT if live_rva is not None else None,
    }
    # print vtable keys from profile
    for k in ("vtable_rvas", "vtables", "rtti", "globals"):
        if k in profile:
            v = profile[k]
            if isinstance(v, dict):
                hits = {ik: (hex(iv) if isinstance(iv, int) else iv) for ik, iv in v.items() if "Army" in ik or "Move" in ik or "Command" in ik or ik in ("CArmy", "CMoveCommand", "CUnitMoveAction")}
                out[f"profile_{k}_hits"] = hits
                if k == "vtable_rvas":
                    out["profile_vtable_rvas_count"] = len(v)
                    out["profile_vtable_rvas_sample"] = list(v)[:20]
    Path("research/t191_vt_compare.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))
finally:
    p.close()
