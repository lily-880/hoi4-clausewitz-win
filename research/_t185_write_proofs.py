# -*- coding: utf-8 -*-
import json
from pathlib import Path

ROOT = Path(".")
INV_SHA = "ae0fd55a22e6e8917cacf0d767f659673f00c3ccbcda726b3ee727be8f288254"

# --- patch session country_index ---
sess_path = Path("research/t185_session_recheck.json")
sess = json.loads(sess_path.read_text(encoding="utf-8"))
sess["country_index"] = 44
sess["tag"] = "ETH"
sess["speed_notch"] = 1
sess["date_ui"] = "1936-01-01"
sess["ui_hour"] = 12
sess["hour_tick"] = 60759371
sess["idler"] = "CInGameIdler"
sess_path.write_text(json.dumps(sess, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

Path("research/t185_inventory_sha256.json").write_text(json.dumps({
    "path": r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md",
    "sha256": INV_SHA,
    "updated": False,
    "fields": 116,
    "verified": 43,
    "unverified": 73,
    "tables": 14,
    "columns": 3,
    "header": "| 字段名 | 已验证/未验证 | 说明 |",
    "complete_input": False,
    "reason": "independent ABI only; no official none-vs-unreadable promotion this batch",
}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

combatant = {
    "promoted": False,
    "CCombatant": {
        "rtti": ".?AVCCombatant@@",
        "vtable": "0x2a367d0",
        "serialize_slot": "+0x10",
        "writer": "0x147ff20",
        "note": ".pdata of 0x147ff20 is only 7 bytes; disassembled through ret / tail jmp 0x126a4c0",
        "unit": {
            "token": "0x28a3 unit",
            "data": "+0x20",
            "size": "+0x2c",
            "omit_if_size_le_0": True,
            "elem": "CArmy*; official handle at elem+0x18 via 0x22857c0",
            "schema_role": "Combat.attacker_unit_ids / defender_unit_ids official combined list (not a guessed union of front/reserves/retreat)",
        },
        "other_official_fields": {
            "losses": "+0xb8 token 0x28f8",
            "size_list": "data +0xa0 size +0xac, written iff size!=0",
            "has_flanked_opponent": "byte +0xdb token 0x3517, written iff nonzero",
            "last_hit": "+0xe0 token 0x30ac, written iff size>0",
            "shore_bombardment_collateral_damage_factor": "+0x10 token 0x288d, written iff >0",
            "weighted_participants": "+0x80 token 0x2a03, written iff [+0x90]!=0",
        },
    },
    "CLandCombatant": {
        "rtti": ".?AVCLandCombatant@@",
        "vtable": "0x2a236a0",
        "serialize_slot": "+0x10",
        "writer": "0x134d5f0",
        "starts_with_call": "0x147ff20",
        "sublists_already_bound_t184": {
            "front": "+0xe8 / +0xf4 token 0x29e0",
            "reserves": "+0x100 / +0x10c token 0x29e2",
            "retreat": "+0x118 / +0x124 token 0x2920",
            "unit_handle": "elem+0x18 via 0x22857c0",
        },
        "schema_note": "schema Combat has a single attacker_unit_ids / defender_unit_ids array; official combined shape is CCombatant unit +0x20/+0x2c, not a union invented from the three sublists",
    },
    "CCombatManager": {
        "rtti": ".?AVCCombatManager@@",
        "embedded_at": "GS+0x260",
        "array": "GS+0x268 is manager+0x8 (already known); live size 0",
        "history": "CCombatHistory vtable at GS+0x288",
        "writer": "0xc0eae0 writes token history 0x2835",
        "do_not_promote_empty_as_false": True,
    },
    "no_carmy_current_combat_pointer_bound": True,
    "gs_combats_size": 0,
    "clips": [
        "research/_t185_clip_combatant_base_0x147ff20.txt",
        "research/_t184_clip_landcombatant_writer_0x134d5f0.txt",
        "research/_t185_clip_combatmanager_writer_0xc0eae0.txt",
    ],
}
Path("research/t185_combatant_unit_shape.json").write_text(json.dumps(combatant, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

activity = {
    "promoted": False,
    "SArmyUnitActivityData": {
        "rtti": ".?AUSArmyUnitActivityData@@",
        "vtable": "0x29d7098",
        "serialize": "0x19eeaa0",
        "deserialize": "0x19ee810",
        "layout": {
            "combat": "dword +0x8 token 0x2916, written iff nonzero via 0x25459e0",
            "training": "dword +0xc token 0x2fba, written iff nonzero",
            "division": "handle at +0x10, written iff 0x74ad90 says present, via 0x22856e0",
        },
        "not_embedded_in_CArmy": True,
        "carmy_0x338": "CArmy interface vtable 0x29d7030 (this-adjustor 0xccb540 lea rax,[rcx-0x338]); 0x19eeaa0 is the NEXT packed vtable 0x29d7098, not a CArmy method",
        "carmy_0x340_is": "CNameGroupMember* (21/21 live ETH); not the combat dword. Do not treat CA+0x340 as in_combat.",
        "fill_paths_seen": "stack/array copies (0xce8ea0, 0xcecd10, 0x1338c40, 0x1468293); no official CArmy slot that sources combat+8 was bound",
    },
    "pLandCombat_assert": {
        "function": "0x11105b0",
        "string_rva": "0x2a04720",
        "xref": "0x1110ec5",
        "r14_is_CArmy": "uses location CArmy+0x1f0 and path size +0x20c",
        "not_a_bound_slot": "assert tests the result of 0x25c38b0 (typed lookup/cast) on rsi; not a proven CArmy field offset",
        "pMovingTo_sibling": "same function, 0xc52e90 after path size +0x20c > 0; not promoted as order.type",
    },
    "InCombat_string": "still navy carrier assert at 0x29f9547 only",
    "clips": [
        "research/_t185_clip_19eeaa0.txt",
        "research/_t185_clip_19ee810.txt",
        "research/_t185_clip_plandcombat_assert_0x11105b0.txt",
        "research/_t185_clip_c52e90.txt",
    ],
}
Path("research/t185_activity_combat_slot.json").write_text(json.dumps(activity, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

order = {
    "promoted": False,
    "COrderInstance": {
        "rtti": ".?AVCOrderInstance@@",
        "vtable": "0x2a026e8",
        "writer": "0x10d1450",
        "type": "dword +0x30 written as token type 0xe1 via 0x25459e0",
        "same_slot_as_GetOrderType": "0x10b2c60 cmp [rcx+0x30],1 ORDER_MOVE; 0x10b038e cmp 3 ORDER_INVASION",
        "schema_role": "battle-plan COrderInstance, not world.own_units.order.type",
    },
    "commandlist_plus8": "still unmapped to schema OrderType; no live command object; do not invent OrderType",
    "clips": ["research/_t185_clip_orderinstance_writer_0x10d1450.txt"],
}
Path("research/t185_orderinstance_type.json").write_text(json.dumps(order, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

supply = {
    "promoted": False,
    "CSupplyConsumer": {
        "rtti": ".?AVCSupplyConsumer@@",
        "vtable": "0x29cfa58",
        "writer": "0xf4ca30",
        "tokens": ["id via 0x22858a0", "disrupted_supply 0x4cf2", "motorization_level 0x4de7", "countries 0x2d49"],
        "no_in_supply_or_isolated_token": True,
        "not_embedded_in_CArmy_0x688": True,
    },
    "CSupplySystem_ptr": "GS+0x3d8 live 0x26cf13d1600",
    "still_no_named_in_supply_or_isolated_on_CArmy": True,
    "do_not_invent_72_over_108": True,
    "clips": ["research/_t185_clip_supplyconsumer_writer_0xf4ca30.txt"],
}
Path("research/t185_supply_consumer.json").write_text(json.dumps(supply, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

# offsets key
off_path = Path("calling/tables/offsets_input_windows_1.19.5.json")
off = json.loads(off_path.read_text(encoding="utf-8"))
off["land_combatant_activity_t185"] = {
    "CCombatant_writer": "0x147ff20 (vtable 0x2a367d0 +0x10)",
    "CCombatant_unit": "data +0x20 size +0x2c; handle elem+0x18 via 0x22857c0; token 0x28a3; official combined attacker/defender unit-id list",
    "CLandCombatant_writer": "0x134d5f0 calls 0x147ff20 then front/reserves/retreat (t184)",
    "SArmyUnitActivityData": "vtable 0x29d7098 writer 0x19eeaa0; combat dword +8 iff nonzero; training +0xc; not embedded in CArmy; CA+0x340 is CNameGroupMember*",
    "CCombatManager": "embedded GS+0x260; array GS+0x268 still size 0; do not promote false",
    "COrderInstance_type": "dword +0x30 token type 0xe1; battle-plan, not commandlist+8 / own_units.order",
    "CSupplyConsumer_writer": "0xf4ca30; disrupted_supply / motorization_level; no in_supply or isolated token",
    "promoted": False,
    "proofs": [
        "research/t185_combatant_unit_shape.json",
        "research/t185_activity_combat_slot.json",
        "research/t185_orderinstance_type.json",
        "research/t185_supply_consumer.json",
    ],
}
off_path.write_text(json.dumps(off, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("wrote offsets key land_combatant_activity_t185 promoted false")
print("all json ok")
