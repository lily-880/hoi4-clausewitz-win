import json, hashlib, unittest
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
        # live D SHA may change in later batches; this test pins t183's recorded hash
        text = INV.read_text(encoding="utf-8")
        self.assertIn("| 字段名 | 已验证/未验证 | 说明 |", text)
        self.assertIn("| world.own_units.in_combat | 未验证 |", text)
        self.assertIn("| world.own_units.order.type | 未验证 |", text)
        # assigned_to / formation.army_id stayed unverified in t183; later batches may promote them


if __name__ == "__main__":
    unittest.main()
