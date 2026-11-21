import json
from pathlib import Path

SHA = "98d83a601f67b73d71a62c559e9a9a29a75e92eb831c7df2be4d42de7ac7e201"

proof = {
    "promoted": [],
    "reason_not_promoted": {
        "crises": "No official persistent crisis table mapped to schema kind/unit_ids/province_ids/severity. 0x1571ef0 computes _EncirclementPoints at result+0x148 (assert string names that field) from a front/order-like province list via caller 0x156c870; this is a geometry/highlight computer, not a standing world.crises row. CTheaterGroup is empty worldwide (t188). UI ALERT_* keys (low supply, no equipment) are not the Crisis enum. Do not write false/no-crisis from an empty or unmapped table.",
        "visibility": "Token visible 0x2d2a at 0xf0a978 is a map/gfx object writer (z/scale/rotation/animation/min_zoom). already_spotted 0x3bb3 remains a naval-mission writer. Token intel 0x30ec at 0xd689d0 is national intel pools (intel_from_allies / static_intel_pools / dynamic_intel_pools), not per-unit spotted or 0-1 confidence. No land-unit FoW spotted+confidence getter was bound. Foreign units were not exported.",
        "buildings": "Official native slots unchanged: CBuilding +0x40 level, +0x42 healthy, overlay arrays +0x10 and +0x28; numeric getter 0x1201750 / 0x12017E0 plus 0x1162FE0 overlays; 1552CF0 is still a string formatter. Live official-container world scan found 0 damaged (healthy<level) and 0 nonempty overlays among 2140 state buildings and 4560 province buildings. Cannot lift the undamaged/no-overlay restriction or invent damaged/extra-level semantics without a contrast sample."
    },
    "encirclement": {
        "computer": "0x1571ef0",
        "caller": "0x156c870 site 0x156cab2",
        "points": "dword province-id array at result+0x148, named _EncirclementPoints in assert at 0x2a460a0",
        "clips": [
            "research/_t189_clip_encirclement_points_0x1571ef0.txt",
            "research/_t189_clip_encirc_caller_0x156cab2.txt"
        ]
    },
    "not_land_fow": {
        "visible_0x2d2a": "map/gfx writer 0xf0a978 (z/scale/rotation/animation)",
        "already_spotted_0x3bb3": "naval mission writer 0x104353b (t188)",
        "intel_0x30ec": "national intel writer 0xd689d0 (pools / allies / encryption)",
        "clips": [
            "research/_t189_clip_visible_token_0xf0a978.txt",
            "research/_t189_clip_intel_writer_0xd689d0.txt",
            "research/_t188_clip_already_spotted_0x104353b.txt"
        ]
    },
    "buildings": {
        "status_roots": "CState+0x120 and CProvince+0x190 (CBuildingStatus)",
        "live_scan": "research/t189_live_buildings.json",
        "state_province_array_live": "CState+0x18 is a live CProvince* array (ETH state 271 starts at province 5010); CState writer 0xa2bbc0 does not emit a provinces token at that slot",
        "counts": {
            "states": 1081,
            "state_buildings_undamaged_no_overlay": 2140,
            "provinces": 10272,
            "province_buildings_undamaged_no_overlay": 4560,
            "damaged": 0,
            "nonempty_overlays": 0
        }
    }
}
Path("research/t189_crisis_fow_buildings.json").write_text(json.dumps(proof, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")

Path("research/t189_inventory_sha256.json").write_text(json.dumps({
    "path": r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md",
    "sha256": SHA,
    "updated": False,
    "fields": 116,
    "verified": 47,
    "unverified": 69,
    "tables": 14,
    "columns": 3,
    "header": "| 字段名 | 已验证/未验证 | 说明 |",
    "promoted": [],
    "complete_input": False,
    "reason": "crises/FoW/damaged-buildings not promoted; no contract sample or land spotted getter"
}, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")

off_path = Path("calling/tables/offsets_input_windows_1.19.5.json")
off = json.loads(off_path.read_text(encoding="utf-8"))
off["crisis_fow_buildings_t189"] = {
    "encirclement_computer": "0x1571ef0",
    "encirclement_points": "result+0x148",
    "visible_token_0x2d2a": "map/gfx, not land FoW",
    "intel_token_0x30ec": "national intel pools at writer 0xd689d0, not unit confidence",
    "already_spotted_0x3bb3": "naval mission, not land spotted",
    "CBuilding_level_healthy": "+0x40 / +0x42",
    "CBuilding_overlays": "+0x10 / +0x28",
    "live_damaged": 0,
    "live_overlays": 0,
    "promoted": False,
    "proofs": ["research/t189_crisis_fow_buildings.json", "research/t189_live_buildings.json"]
}
off_path.write_text(json.dumps(off, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
print("proofs written")
