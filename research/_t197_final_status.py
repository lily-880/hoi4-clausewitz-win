# -*- coding: utf-8 -*-
from __future__ import annotations
import hashlib, json, struct, sys
from pathlib import Path

ROOT = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")
sys.path.insert(0, str(ROOT / "calling"))
from pe import PE
from mem import Proc, find_pid as mem_find_pid
from gamestate import detect_session, resolve_player_country, read_campaign_summary
from config import allow_post
from input_loaded_fields import LoadedReader, own_plans, own_armies

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
INV = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
EXPECTED = "a159657f42fa0ec4ab65e7342473c7a4432a763d91d378ff07c37b2059f5a4d2"
OUT = ROOT / "research" / "t197_final_status.json"


def main():
    raw = INV.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    text = raw.decode("utf-8")
    lines = text.splitlines()
    n_tables = sum(1 for ln in lines if ln.startswith("| 字段名 | 已验证/未验证 | 说明 |"))
    n_fields = sum(1 for ln in lines if ln.startswith("| ") and not ln.startswith("| 字段名 |") and not ln.startswith("| ---"))
    n_v = sum(1 for ln in lines if "| 已验证 |" in ln)
    n_u = sum(1 for ln in lines if "| 未验证 |" in ln)
    out = {
        "inventory": {
            "sha256": sha, "sha_ok": sha == EXPECTED, "bom": raw.startswith(b"\xef\xbb\xbf"),
            "tables": n_tables, "fields": n_fields, "verified": n_v, "unverified": n_u,
        },
        "allow_post": allow_post(),
        "gate_open": (ROOT / "research" / "safe_land_tool_gate.OPEN").exists(),
    }
    pid = mem_find_pid("hoi4.exe")
    out["pid"] = pid
    if pid == 12948:
        p = Proc(pid)
        pe = PE(EXE)
        try:
            session = detect_session(p, pe)
            gs = int(session["signals"]["gs_ptr"], 16)
            idler = int(session["signals"]["idler_ptr"], 16)
            co = int(resolve_player_country(p, gs)["country_ptr"], 16)
            from gamestate import _rtti_name_from_vtable

            def rtti(a):
                if not (0x20000000000 < a < 0x7FFFFFFFFFFF):
                    return None
                try:
                    vt = struct.unpack("<Q", p.read(a, 8))[0]
                except OSError:
                    return None
                if not p.base <= vt < p.base + p.image_size:
                    return None
                return _rtti_name_from_vtable(pe, vt - p.base)

            r = LoadedReader(p.read, rtti)
            plans, _ = own_plans(r, co)
            armies, _ = own_armies(r, co)
            out["live"] = {
                "pid": pid,
                "pause": p.read(idler + 0x6C1, 1)[0],
                "speed": struct.unpack("<i", p.read(gs + 0x4BC, 4))[0],
                "date": (read_campaign_summary(p, gs).get("verified") or {}).get("date_full"),
                "plans": plans,
                "armies": armies,
            }
        finally:
            p.close()
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
