"""Phase 2as — live CArmy handle + CProvince id mapping (RO); posting DISABLED."""
from __future__ import annotations
import argparse, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "calling"))

G_GAMESTATE = 0x33DD6B0
GS_COUNTRIES_BEGIN = 0x310
GS_COUNTRIES_SIZE = 0x318
GS_PLAYER_TAG = 0x518
CO_ARMIES = 0x290
CO_ARMIES_SIZE = 0x0C  # within array object at +0x290 → absolute +0x29C
CA_HANDLE = 0x18  # CHandle {type:u32, index:u32}
CA_HANDLE_TYPE_ARMY = 0x33  # observed on all HAI CArmy
CA_PROVINCE_PTR = 0x1F0
CA_COUNTRY_TAG = 0x1E0  # matches player_tag on sampled armies
CP_PROVINCE_ID = 0xA4  # hypothesis; unique across HAI provinces this session


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "research", "re-dumps", "phase2as_report.json"))
    args = ap.parse_args()
    out = {
        "phase": "2as",
        "posting": "DISABLED",
        "command_queue": "DISABLED",
        "speed_rule": "pause or 1x only; never 5x",
        "GS_COUNTRIES": {
            "begin": hex(GS_COUNTRIES_BEGIN),
            "size": hex(GS_COUNTRIES_SIZE),
            "note": "CPdxArray at GS+0x310: begin u64, size u32 at +0x8 (=GS+0x318)",
        },
        "CArmy_HANDLE": {
            "off": hex(CA_HANDLE),
            "layout": "u32 type + u32 index (little-endian qword)",
            "type_army_observed": hex(CA_HANDLE_TYPE_ARMY),
            "note": "Move action uses token unit 0x28a3; Strategic uses token army 0x289d — both likely this CHandle shape",
        },
        "CProvince_ID": {
            "off": hex(CP_PROVINCE_ID),
            "via": f"CArmy+{hex(CA_PROVINCE_PTR)} -> CProvince*",
            "status": "hypothesis_strong",
            "note": "15 unique ids in 740..13071 on paused HAI 17-army sample",
        },
        "safe_enable": "NOT proven — posting DISABLED",
        "FN_HANDLE_RESOLVE": {
            "prior_claim": "0x6e4800",
            "status": "UNVERIFIED on this pass — not promoted; Apply paths call other helpers",
        },
    }
    if args.live:
        from process import Backend, find_pid
        b = Backend(find_pid("hoi4.exe"))
        base = b.image_base
        def u64(a): return struct.unpack("<Q", b.read(a, 8))[0]
        def u32(a): return struct.unpack("<I", b.read(a, 4))[0]
        gs = u64(base + G_GAMESTATE)
        begin = u64(gs + GS_COUNTRIES_BEGIN)
        ncountry = u32(gs + GS_COUNTRIES_SIZE)
        ptag = u32(gs + GS_PLAYER_TAG)
        pc = u64(begin + ptag * 8)
        ab = u64(pc + CO_ARMIES)
        asz = u32(pc + CO_ARMIES + CO_ARMIES_SIZE)
        rows = []
        types = set(); ids = []; prov_ids = []
        for i in range(asz):
            ap = u64(ab + i * 8)
            typ, idx = u32(ap + CA_HANDLE), u32(ap + CA_HANDLE + 4)
            types.add(typ); ids.append(idx)
            prov = u64(ap + CA_PROVINCE_PTR)
            pid = u32(prov + CP_PROVINCE_ID) if prov > 0x10000 else None
            if pid is not None: prov_ids.append(pid)
            rows.append({
                "i": i, "army": hex(ap), "handle_type": typ, "handle_index": idx,
                "country_tag_at_1e0": u32(ap + CA_COUNTRY_TAG),
                "province_id": pid, "province_ptr": hex(prov),
            })
        out["live"] = {
            "countries": ncountry, "player_tag": ptag, "armies": asz,
            "handle_types": sorted(types),
            "handle_index_range": [min(ids), max(ids)] if ids else None,
            "province_ids_unique": len(set(prov_ids)),
            "province_ids_sample": sorted(set(prov_ids))[:20],
            "rows": rows,
            "checks": {
                "countries_440": ncountry == 440,
                "handle_type_all_0x33": types == {0x33},
                "indices_sequential": ids == list(range(ids[0], ids[0] + len(ids))) if ids else False,
                "country_tag_matches_player": all(r["country_tag_at_1e0"] == ptag for r in rows),
            },
        }
        out["all_checks_ok"] = all(out["live"]["checks"].values())
        b.close()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), indent=2)
    print("wrote", args.out)
    if args.live:
        print("checks", out["all_checks_ok"], out["live"]["checks"])
        print("armies", out["live"]["armies"], "prov_unique", out["live"]["province_ids_unique"])


if __name__ == "__main__":
    main()
