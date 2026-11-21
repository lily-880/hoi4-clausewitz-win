# -*- coding: utf-8 -*-
import json, hashlib
from pathlib import Path

ROOT = Path(".")
INV = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
sha = hashlib.sha256(INV.read_bytes()).hexdigest()
assert sha == "ae0fd55a22e6e8917cacf0d767f659673f00c3ccbcda726b3ee727be8f288254", sha

(ROOT / "research/t183_inventory_sha256.json").write_text(json.dumps({
    "path": str(INV),
    "sha256": sha,
    "updated": False,
    "reason": "no field promoted; empty theatres/groups and unassigned leaders do not prove formation or assigned_to; no land IsInCombat; commandlist element ABI only; is_assigned is CScientist",
    "counts": {"fields": 116, "tables": 14, "columns": 3, "verified": 43, "unverified": 73},
}, indent=2) + "\n", encoding="utf-8")

assigned = {
    "game": "HOI4 1.19.5.0.7c6c",
    "pid": 26976,
    "read_only": True,
    "token_is_assigned": "0x385b",
    "registrar_0x26940": {
        "role": "string-token registrar, not a field reader",
        "pattern": "same family as is_field_marshal 0x26c40 and is_leading_army_group 0x26e80; jmp 0x597c00",
        "clip": "research/_t183_clip_is_assigned_0x26940.txt"
    },
    "writer_0x14a8ec0": {
        "rtti": ".?AVCScientist@@",
        "vtable": "0x29fb128",
        "slot": "0x29fb138 = vtable+0x10",
        "field": "byte at CScientist+0x130, written iff nonzero via 0x2546250",
        "neighbors": "skills +0x108, is_scientist_injured +0x134",
        "clip": "research/_t183_clip_is_assigned_0x14a8ec0.txt",
        "not": "world.leaders.assigned_to"
    },
    "carmy_leader": {
        "writer": "0xc7e8c0",
        "deployed": {"token": "0x41c7", "ca": "CArmyLeader+0x1068", "type": "byte", "written_iff_nonzero": True, "live": 0, "units": 20},
        "deploy_army_hq": {"token": "0x282b", "ca": "CArmyLeader+0x1058", "live": 0, "units": 20},
        "pending_reassign_target": {"token": "0x283d", "ca": "CArmyLeader+0x1050"},
        "location_only_if_captured": True,
        "not_assigned_to_shape": "schema is {kind: army|army_group|unit, id}; deployed is a boolean and is 0 for all 20 ETH generals"
    },
    "id_spaces": {
        "world.leaders.leader_id": "CArmyLeader handle id at +0xc; this scene 312-331 (20 ETH generals)",
        "world.own_units.leader_id": "already verified at CArmy+0x564; this scene 5 units have 70392-70396, 16 have -1; SUnitOfficerData at CArmy+0x568 copies the same id at +0x54 or -1. Different space from the 20 generals (inventory already notes this)."
    },
    "live": {
        "player_characters": 52,
        "army_leaders": 20,
        "deployed_all_zero": True,
        "no_CArmy_back_pointer": True,
        "handle_ids_do_not_match_unit_leader_ids": True
    },
    "promoted": False,
    "why": "no official {kind,id} reader; all 20 generals unassigned; unit.leader_id is a different officer space and must not be inverted into assigned_to"
}
(ROOT / "research/t183_assigned_to_contract.json").write_text(json.dumps(assigned, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

cmd = {
    "commandlist": {
        "token": "0xcb",
        "ca": "CArmy+0x2c0 data, +0x2cc size (writer +0x2b0/+0x2bc on CArmy+0x10)",
        "empty_omits_key": True,
        "element": {
            "stride": 8,
            "pointer": True,
            "type_token_at": "+8",
            "serialize": "0xc5c480 mov rdx,[rsi]; mov edx,[rdx+8]; call 0x2546ce0 (write key); mov rdx,[rsi]; call 0x2544f80 (serialize object)",
            "clip": "research/_t183_clip_commandlist_loop_0xc5c43f.txt"
        }
    },
    "schema_order": {
        "required": ["type", "target_province_ids", "path_province_ids"],
        "type_enum": ["idle","move","strategic_redeploy","attack","support_attack","retreat","garrison","training","exercise","unknown"]
    },
    "live": {"units": 21, "commandlist_size": 0, "path_size": 0, "full_path_size": 0},
    "promoted": False,
    "why": "element ABI is official, but this scene has no command object so +8 tokens cannot be mapped onto OrderType; empty list still must not be written as type=idle"
}
(ROOT / "research/t183_commandlist_element.json").write_text(json.dumps(cmd, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

combat = {
    "gs_combats": {"location": "GS+0x268", "live": {"data": 0, "size": 0}, "structure_candidate_only": True},
    "InCombat_string_0x29f9547": {
        "text": "pAirBase->GetCarrierShip()->GetNavy()->InCombat() && \"Scrambled airwing's carrier is not in combat.\"",
        "note": "navy method used in a carrier assert, not a land-unit IsInCombat"
    },
    "land_combat_id_0x34a6": "still [obj+0x748] in 0x208f90, not CArmy (t182)",
    "no_land_unit_IsInCombat_bound": True,
    "promoted": False
}
(ROOT / "research/t183_combat_reader.json").write_text(json.dumps(combat, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

formation = {
    "player_theatres": 1,
    "roots": {"CCountry+0x168": "pdx array of CTheatre* (t165, reconfirmed)"},
    "group_arrays_on_CTheatre": {
        "orders_group": {"off": "0x80", "size": 0},
        "field_marshal_group": {"off": "0x98", "size": 0},
        "theater_group": {"off": "0xc8", "size": 0}
    },
    "unit_formation_pointers": "no CTheatre/CArmyGroup/CTheaterGroup pointer on the 21 own CArmy in +0x20..0x800",
    "schema": {"army_id": "integer optional", "army_group_id": "integer optional"},
    "promoted": False,
    "why": "official empty group arrays are a structure candidate only; this scene has no army or army-group object, so army_id/army_group_id cannot be proven"
}
(ROOT / "research/t183_formation_empty.json").write_text(json.dumps(formation, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

supply = {
    "0xf00797": "mid/other-object writer (railway_gun_name, repair_line) that also emits max_supply / army_current_supply_ratio / supply_gain from a different base; not a 0..1 getter",
    "clip": "research/_t183_clip_supply_ratio_0xf00797.txt",
    "still": "CA+0x610 = 72.0 /100000 is official token army_current_supply_ratio but not a 0..1 ratio; do not invent 72/108",
    "in_supply_isolated": "no official named CArmy getter bound this batch",
    "promoted": False
}
(ROOT / "research/t183_supply_still_not_ratio.json").write_text(json.dumps(supply, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

offp = ROOT / "calling/tables/offsets_input_windows_1.19.5.json"
off = json.loads(offp.read_text(encoding="utf-8"))
off["assigned_combat_command_t183"] = {
    "is_assigned_0x385b": "CScientist+0x130 byte, writer 0x14a8ec0; 0x26940 is only the token registrar",
    "carmy_leader_deployed": "token 0x41c7 at CArmyLeader+0x1068, written iff nonzero; live 0 for 20 ETH generals",
    "commandlist_element": "stride-8 pointer; type token at +8; object serializer 0x2544f80",
    "InCombat": "GetNavy()->InCombat() assert only; no land-unit reader",
    "formation_roots": "CCountry+0x168 theatres; CTheatre +0x80/+0x98/+0xc8 group arrays empty this scene",
    "character_country_index": "CCharacter+0x68; CArmyLeader at CCharacter+0xa8",
    "promoted": False,
    "proofs": [
        "research/t183_assigned_to_contract.json",
        "research/t183_commandlist_element.json",
        "research/t183_combat_reader.json",
        "research/t183_formation_empty.json",
        "research/t183_live_assigned_to.json"
    ]
}
offp.write_text(json.dumps(off, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("proofs written, D sha", sha)
