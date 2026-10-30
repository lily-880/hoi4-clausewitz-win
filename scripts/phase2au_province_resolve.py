"""Phase 2au — GS province resolve proven; CArmy+0x28 province id (RO). Posting DISABLED."""
from __future__ import annotations
import argparse, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "calling"))

G_GAMESTATE = 0x33DD6B0
GS_PROVINCES_BEGIN = 0x2B0  # via MI this+8 field 0x2a8
GS_PROVINCES_SIZE = 0x2BC
FN_PROVINCE_RESOLVE = 0x1E07F0
FN_PROVINCE_THUNK = 0xC5A9E0  # was HYP_GS_UNIT_THUNK — actually province
CA_PROVINCE_ID = 0x28
CA_PROVINCE_PTR = 0x1F0
CP_PROVINCE_ID = 0xA4
GS_COUNTRIES_BEGIN = 0x310
GS_COUNTRIES_SIZE = 0x318
GS_PLAYER_TAG = 0x518
CO_ARMIES = 0x290


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "research", "re-dumps", "phase2au_report.json"))
    args = ap.parse_args()
    out = {
        "phase": "2au",
        "posting": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "FN_PROVINCE_RESOLVE": hex(FN_PROVINCE_RESOLVE),
        "FN_PROVINCE_THUNK": hex(FN_PROVINCE_THUNK),
        "GS_PROVINCES_BEGIN": hex(GS_PROVINCES_BEGIN),
        "GS_PROVINCES_SIZE": hex(GS_PROVINCES_SIZE),
        "CA_PROVINCE_ID": hex(CA_PROVINCE_ID),
        "note": "0xc5a9e0 thunk -> 0x1e07f0 indexes GS province array; NOT unit resolve",
        "FN_HANDLE_RESOLVE": None,
        "safe_enable": "NOT proven",
    }
    if args.live:
        from process import Backend, find_pid
        b = Backend(find_pid("hoi4.exe"))
        base = b.image_base
        def u64(a): return struct.unpack("<Q", b.read(a, 8))[0]
        def u32(a): return struct.unpack("<I", b.read(a, 4))[0]
        gs = u64(base + G_GAMESTATE)
        arr = u64(gs + GS_PROVINCES_BEGIN)
        n = u32(gs + GS_PROVINCES_SIZE)
        begin = u64(gs + GS_COUNTRIES_BEGIN)
        ptag = u32(gs + GS_PLAYER_TAG)
        pc = u64(begin + ptag * 8)
        ab = u64(pc + CO_ARMIES)
        asz = u32(pc + CO_ARMIES + 0x0C)
        ok = 0
        for i in range(asz):
            army = u64(ab + i * 8)
            pid = u32(army + CA_PROVINCE_ID)
            prov = u64(army + CA_PROVINCE_PTR)
            got = u64(arr + pid * 8) if 0 <= pid < n else 0
            cp_id = u32(prov + CP_PROVINCE_ID) if prov > 0x10000 else None
            if got == prov and cp_id == pid:
                ok += 1
        # bytes of resolve fn
        impl = b.read(base + FN_PROVINCE_RESOLVE, 16)
        out["live"] = {
            "provinces": n,
            "armies": asz,
            "matches": ok,
            "impl_head": impl.hex(),
            "checks": {
                "n_13414": n == 13414,
                "all_army_province_resolve": ok == asz and asz > 0,
                "impl_cmp_edx_1": impl[0:3] == bytes([0x83, 0xFA, 0x01]),
            },
        }
        out["all_checks_ok"] = all(out["live"]["checks"].values())
        b.close()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
    print("wrote", args.out)
    if args.live:
        print("checks", out["all_checks_ok"], out["live"])


if __name__ == "__main__":
    main()
