import json
from pathlib import Path

sess = {
    "pid": 26976,
    "in_game": True,
    "idler": ".?AVCInGameIdler@@",
    "country_ptr": "0x26c4b672530",
    "gs_ptr": "0x26c259d0ff0",
    "tag": "ETH",
    "player_index": 44,
    "date": {
        "year": 1936,
        "ui": "1936-01-01",
        "day_index": 0,
        "ui_hour": 12,
        "hour_tick": 60759371
    },
    "speed_notch": 1,
    "speed_index": 0,
    "hour_progress": 0.0,
    "hour_tick": 60759371,
    "pause_flag_6c1": 1,
    "armies_size": 21,
    "read_only": True,
}
Path("research/t188_session_recheck.json").write_text(json.dumps(sess, indent=2)+"\n", encoding="utf-8")

proof = {
    "promoted": [],
    "reason_not_promoted": "Official player plans are COrderInstance hanging off COrdersGroup (CTheatre+0x80 / group+0x98). Live ETH and the whole world have 0 orders_groups and 0 COrderInstance. The 6 ETH CFronts (and 910 world CFronts) are theatre border structures (writer tokens dirty/provinces/enemies/section/area), not player-drawn plans. Empty tables and border fronts must not be promoted.",
    "COrderInstance": {
        "writer": "0x10d1450",
        "writer_vtable_plus_10": "0x2a026e8",
        "type": "dword +0x30, token type 0xe1 via 0x25459e0",
        "GetOrderType_proven": {"1": "ORDER_MOVE (assert 0x10b2c8a / 0x2a02d50)", "3": "ORDER_INVASION (assert 0x10b038e / 0x2a02c18)"},
        "GetOrderType_candidates": {"4": "compared at 0x10bc966 and tooltip 0xfcae58 near ORDER_PARADROP loc", "5": "compared at 0x10bc7d8, not named"},
        "instance_id": "dword +0x244, token 0x30af",
        "path": "array +0x70, token path 0x174 (not proven as schema vertex_province_ids without a live plan)",
        "states": "array +0xe0, token states 0x2e3b (area-defense states candidate)",
        "can_execute": "token 0x30b2; this is not plans.executing",
        "other_tokens": ["order_children", "fallback", "midpoints", "root_front", "root_section", "area_defense_settings", "area_defense_state_assignment", "blitz", "withdraw", "invasion_source"],
        "clips": [
            "research/_t188_clip_orderinstance_writer_0x10d1450.txt",
            "research/_t188_clip_orderinstance_writer_tail.txt",
            "research/_t184_clip_front_writer_0xf809b0.txt",
            "research/_t188_clip_ordersgroup_writer_0xc4d030.txt"
        ]
    },
    "COrdersGroup": {
        "writer": "0xc4d030",
        "order_instance_array": "+0x98 / size +0xa4, token 0x35f7",
        "fallback": "token 0x33d8",
        "virtual_fallback": "token 0x35f3",
        "execution_type": "token 0x36aa at 0xc4d619, group-level, not proven as plans.executing"
    },
    "CTheatre": {
        "front": "token 0x29e0, data +0x50 / size +0x5c, live elems are CFront only",
        "orders_group": "token 0x30ae, data +0x80 / size +0x8c, live size 0 worldwide"
    },
    "CFront": {
        "writer": "0xf809b0",
        "tokens": ["dirty", "provinces", "enemies", "id_counter", "section", "area"],
        "not": "player plan; no type/instance_id/path/executing"
    },
    "not_land_fow": {
        "already_spotted_0x3bb3": "naval-mission writer around 0x104353b (mission/radar/navy_engagement_rule/spotting_target); not world.visible_units.visibility.spotted"
    },
    "live": "research/t188_live_plans.json"
}
Path("research/t188_plan_writers.json").write_text(json.dumps(proof, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")

Path("research/t188_inventory_sha256.json").write_text(json.dumps({
    "path": r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md",
    "sha256": "98d83a601f67b73d71a62c559e9a9a29a75e92eb831c7df2be4d42de7ac7e201",
    "updated": False,
    "fields": 116,
    "verified": 47,
    "unverified": 69,
    "tables": 14,
    "columns": 3,
    "header": "| 字段名 | 已验证/未验证 | 说明 |",
    "promoted": [],
    "complete_input": False,
    "reason": "plans not promoted: no live COrderInstance; CFronts are border structures"
}, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")

off_path = Path("calling/tables/offsets_input_windows_1.19.5.json")
off = json.loads(off_path.read_text(encoding="utf-8"))
off["plan_orderinstance_t188"] = {
    "COrderInstance_writer": "0x10d1450",
    "type": "+0x30 token type 0xe1",
    "instance_id": "+0x244 token 0x30af",
    "path": "+0x70 token 0x174",
    "states": "+0xe0 token 0x2e3b",
    "can_execute_token": "0x30b2 (not plans.executing)",
    "COrdersGroup_order_instance": "+0x98 / +0xa4 token 0x35f7",
    "CTheatre_orders_group": "+0x80 / +0x8c token 0x30ae",
    "CFront_not_plan": "CTheatre+0x50 writer 0xf809b0 tokens dirty/provinces/enemies/section/area",
    "GetOrderType": {"1": "ORDER_MOVE", "3": "ORDER_INVASION"},
    "live": "0 COrderInstance worldwide in official theatre/group containers; ETH 6 CFronts only",
    "promoted": False,
    "proofs": ["research/t188_plan_writers.json", "research/t188_live_plans.json"]
}
off_path.write_text(json.dumps(off, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
print("wrote proofs")
