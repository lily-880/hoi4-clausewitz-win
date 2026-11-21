# -*- coding: utf-8 -*-
from pathlib import Path

test = r'''import json, hashlib, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INV = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
T181_SHA = "ae0fd55a22e6e8917cacf0d767f659673f00c3ccbcda726b3ee727be8f288254"


class Tests(unittest.TestCase):
    def test_is_assigned_writer_is_cscientist_not_leader(self):
        ev = json.loads((ROOT / "research/t183_assigned_to_contract.json").read_text(encoding="utf-8"))
        self.assertEqual(ev["writer_0x14a8ec0"]["rtti"], ".?AVCScientist@@")
        self.assertEqual(ev["writer_0x14a8ec0"]["field"], "byte at CScientist+0x130, written iff nonzero via 0x2546250")
        self.assertTrue(ev["registrar_0x26940"]["role"].startswith("string-token registrar"))
        self.assertFalse(ev["promoted"])
        text = (ROOT / "research/_t183_clip_is_assigned_0x14a8ec0.txt").read_text(encoding="utf-8")
        self.assertIn("0x14a90d1  movzx r8d, byte ptr [r14 + 0x130]", text)
        self.assertIn("0x14a90de  mov edx, 0x385b  ; TOKEN is_assigned", text)
        self.assertIn("mov edx, 0x278c  ; TOKEN is_scientist_injured", text)
        reg = (ROOT / "research/_t183_clip_is_assigned_0x26940.txt").read_text(encoding="utf-8")
        self.assertIn("mov edx, 0x385b  ; TOKEN is_assigned", reg)
        self.assertIn("jmp 0x597c00", reg)

    def test_carmy_leader_deployed_is_not_assigned_to(self):
        ev = json.loads((ROOT / "research/t183_assigned_to_contract.json").read_text(encoding="utf-8"))
        live = json.loads((ROOT / "research/t183_live_assigned_to.json").read_text(encoding="utf-8"))
        self.assertEqual(ev["carmy_leader"]["deployed"]["live"], 0)
        self.assertEqual(ev["carmy_leader"]["deployed"]["units"], 20)
        self.assertEqual(len(live["leaders"]), 20)
        self.assertTrue(ev["live"]["handle_ids_do_not_match_unit_leader_ids"])
        ids = sorted(L["handle_id"] for L in live["leaders"])
        self.assertEqual(ids, list(range(312, 332)))
        for L in live["leaders"]:
            self.assertEqual(L["deployed_1068"], 0)
            self.assertEqual(L["assigned_unit_ids"], [])
            self.assertEqual(L["ptrs_to_own_units"], [])
        unit_lids = [u["leader_id"] for u in live["units_with_leaders"]]
        self.assertEqual(sorted(unit_lids), [70392, 70393, 70394, 70395, 70396])
        self.assertTrue(set(unit_lids).isdisjoint(ids))

    def test_commandlist_element_token_at_plus8(self):
        text = (ROOT / "research/_t183_clip_commandlist_loop_0xc5c43f.txt").read_text(encoding="utf-8")
        self.assertIn("0xc5c43f  cmp dword ptr [rdi + 0x2bc], 0", text)
        self.assertIn("0xc5c448  mov edx, 0xcb  ; TOKEN commandlist", text)
        self.assertIn("0xc5c480  mov rdx, qword ptr [rsi]", text)
        self.assertIn("0xc5c483  mov edx, dword ptr [rdx + 8]", text)
        self.assertIn("call 0x2544f80", text)
        ev = json.loads((ROOT / "research/t183_commandlist_element.json").read_text(encoding="utf-8"))
        self.assertEqual(ev["commandlist"]["element"]["type_token_at"], "+8")
        self.assertFalse(ev["promoted"])
        self.assertEqual(ev["live"]["commandlist_size"], 0)

    def test_incombat_is_navy_assert_not_land_unit(self):
        ev = json.loads((ROOT / "research/t183_combat_reader.json").read_text(encoding="utf-8"))
        self.assertIn("GetNavy()->InCombat()", ev["InCombat_string_0x29f9547"]["text"])
        self.assertTrue(ev["no_land_unit_IsInCombat_bound"])
        self.assertEqual(ev["gs_combats"]["live"]["size"], 0)
        self.assertFalse(ev["promoted"])

    def test_formation_empty_not_promoted(self):
        ev = json.loads((ROOT / "research/t183_formation_empty.json").read_text(encoding="utf-8"))
        self.assertEqual(ev["player_theatres"], 1)
        self.assertEqual(ev["group_arrays_on_CTheatre"]["orders_group"]["size"], 0)
        self.assertEqual(ev["group_arrays_on_CTheatre"]["field_marshal_group"]["size"], 0)
        self.assertEqual(ev["group_arrays_on_CTheatre"]["theater_group"]["size"], 0)
        self.assertFalse(ev["promoted"])

    def test_inventory_unchanged(self):
        rec = json.loads((ROOT / "research/t183_inventory_sha256.json").read_text(encoding="utf-8"))
        self.assertFalse(rec["updated"])
        self.assertEqual(rec["sha256"], T181_SHA)
        self.assertEqual(rec["counts"]["verified"], 43)
        self.assertEqual(rec["counts"]["unverified"], 73)
        self.assertEqual(hashlib.sha256(INV.read_bytes()).hexdigest(), T181_SHA)
        text = INV.read_text(encoding="utf-8")
        self.assertIn("| 字段名 | 已验证/未验证 | 说明 |", text)
        self.assertIn("| world.own_units.in_combat | 未验证 |", text)
        self.assertIn("| world.own_units.order.type | 未验证 |", text)
        self.assertIn("| world.leaders.assigned_to | 未验证 |", text)
        self.assertIn("| world.own_units.formation.army_id | 未验证 |", text)


if __name__ == "__main__":
    unittest.main()
'''
Path("research/test_t183_input_assigned_combat_command.py").write_text(test, encoding="utf-8")

md = r'''# t183 checkpoint — is_assigned is CScientist; commandlist +8 bound; nothing promoted

## Session

Live process rechecked first: pid 26976, HOI4 1.19.5.0.7c6c, in_game, ETH index 44 1x, country 0x26c4b672530, gs 0x26c259d0ff0. This batch was read-only: no memory writes, no Post, no game-function execution, no save access, no speed or campaign change. No test war, no orders, no leader assignments issued.

## is_assigned / leaders.assigned_to

Token `is_assigned` 0x385b at `0x26940` is a **string-token registrar** (same family as `is_field_marshal` 0x26c40 and `is_leading_army_group` 0x26e80), not a field reader.

The only non-registrar consumer `0x14a8ec0` belongs to **CScientist** (vtable 0x29fb128, this function at +0x10). It writes the token from `byte [this+0x130]` only if nonzero; the next field is `is_scientist_injured` at +0x134. That is not `world.leaders.assigned_to`.

CArmyLeader writer `0xc7e8c0` has official `deployed` (token 0x41c7, byte at +0x1068, written iff nonzero) and `deploy_army_hq` (+0x1058). Schema `assigned_to` is `{kind: army|army_group|unit, id}`. A boolean is the wrong shape.

Live: CCharacter+0x68 is the country index; CArmyLeader* is at CCharacter+0xa8. 52 player characters, **20** CArmyLeader (handle ids 312–331, same space as t163). All 20 have `deployed=0`, no pointer to an own CArmy, and no handle match to unit `leader_id`. The five own divisions with `CArmy+0x564` in {70392..70396} (16 others −1) use a **different officer space**, already noted in the inventory as 非师军官编号; `SUnitOfficerData` at CArmy+0x568 copies that same id at +0x54. Do not invert unit.leader_id into assigned_to.

## commandlist element

Official element ABI from `0xc5c0a0` (offsets relative to CArmy+0x10):

    0xc5c43f  cmp dword ptr [rdi + 0x2bc], 0
    0xc5c448  mov edx, 0xcb  ; TOKEN commandlist
    0xc5c480  mov rdx, qword ptr [rsi]
    0xc5c483  mov edx, dword ptr [rdx + 8]
    0xc5c489  call 0x2546ce0          ; write the per-command token
    0xc5c48e  mov rdx, qword ptr [rsi]
    0xc5c494  call 0x2544f80          ; serialize the command object

Stride-8 pointers; type token at element+8. 21/21 commandlists still size 0, so +8 cannot be mapped onto schema `OrderType` this scene. Empty official lists still must not be written as `order.type=idle`.

## in_combat

`InCombat(` at 0x29f9547 is the navy assert `pAirBase->GetCarrierShip()->GetNavy()->InCombat() && "Scrambled airwing's carrier is not in combat."` — not a land-unit reader. `land_combat_id` remains a non-CArmy field (t182). GS+0x268 combats are still empty (data 0, size 0): structure candidate only.

## formation / supply

One ETH CTheatre at CCountry+0x168. Group arrays at CTheatre+0x80 / +0x98 / +0xc8 (orders / field_marshal / theater) all size 0. No CTheatre/CArmyGroup/CTheaterGroup pointer on the 21 own CArmy in +0x20..0x800. Empty groups cannot prove `formation.army_id` / `army_group_id`.

`0xf00797` is another object writer (railway_gun_name / repair_line) that also emits the same supply tokens; not a 0..1 getter. CA+0x610 remains 72.0 under /100000. No named `in_supply` / `isolated` CArmy getter bound.

## Not promoted

`in_combat`, `order`, `supply.ratio` / `in_supply` / `isolated`, `formation`, `leaders.assigned_to` stay unverified. `complete_input` stays false. Do not promote 77, `[1835]`, demanded / deficit / affected_unit_ids. `produced` is still not `min(need, current stockpile)`. Building damaged/overlay levels remain restricted; 1552CF0 remains a string formatter.

## Official inventory

D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md was **not** written. Still 116 fields, 14 tables, 3 columns; **43 verified / 73 unverified**. SHA256 `ae0fd55a22e6e8917cacf0d767f659673f00c3ccbcda726b3ee727be8f288254` (unchanged from t181).

## Artifacts

- research/t183_checkpoint.md
- research/t183_session_recheck.json
- research/t183_assigned_to_contract.json
- research/t183_commandlist_element.json
- research/t183_combat_reader.json
- research/t183_formation_empty.json
- research/t183_supply_still_not_ratio.json
- research/t183_live_assigned_to.json, research/t183_live_formation_leaders.json, research/t183_live_officerdata.json
- research/t183_inventory_sha256.json
- clips: `_t183_clip_is_assigned_0x26940.txt`, `_t183_clip_is_assigned_0x14a8ec0.txt`, `_t183_clip_is_field_marshal_0x26c40.txt`, `_t183_clip_is_leading_army_group_0x26e80.txt`, `_t183_clip_commandlist_loop_0xc5c43f.txt`, `_t183_clip_leader_writer_0xc7e8c0.txt`, `_t183_clip_supply_ratio_0xf00797.txt`
- offsets key: `assigned_combat_command_t183` (`promoted: false`)
- tests: research/test_t183_input_assigned_combat_command.py (6 tests). Suite 163 + 6 = 169. No new field emission.

## Next independent block

Bind official CTheatre / group / army membership and id writers (CTheatre `0xf81510` and group object serializers) as ABI only; do not promote empty groups. Keep hunting a land-unit current-combat pointer or CLandCombat membership reader without promoting false from empty GS_COMBATS. A static map of commandlist +8 tokens onto `OrderType` can continue from command-class vtables even without a live command, but promotion still needs a present command or an official idle flag. Continue `in_supply` / `isolated` / 0–1 supply only with a named getter. Do not promote 77 or [1835]. Do not write `produced = min(need, stockpile)` against the current empty infantry row. Do not advance the campaign. Building damaged / overlay levels remain restricted; 1552CF0 remains a string formatter.

This empty peace scene still cannot finish `in_combat` / `order.type`. `leaders.assigned_to` additionally cannot be finished while all 20 generals are unassigned and no official `{kind,id}` slot is bound. Minimal user conditions, only when those fields must be contrasted: issue one move order to one own division, or provide a live combat, **or assign one of the 20 ETH generals to a division / army / army group**. The agent will not start a war, change speed/pause, give orders, or assign leaders. Other ABI work above can continue without that.

If HOI4 is gone or not in-game at the next resume, report and stop; do not start or change a campaign.
'''
Path("research/t183_checkpoint.md").write_text(md, encoding="utf-8")
print("test+checkpoint written")
