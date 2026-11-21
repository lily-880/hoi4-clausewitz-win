import json, hashlib, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INV = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
T181_SHA = "ae0fd55a22e6e8917cacf0d767f659673f00c3ccbcda726b3ee727be8f288254"


class Tests(unittest.TestCase):
    def test_ccombatant_combined_unit_array(self):
        text = (ROOT / "research/_t185_clip_combatant_base_0x147ff20.txt").read_text(encoding="utf-8")
        self.assertIn("0x147ff36  movsxd r14, dword ptr [rcx + 0x2c]", text)
        self.assertIn("0x147ff50  mov rax, qword ptr [rbx + 0x20]", text)
        self.assertIn("0x147ff54  mov edx, 0x28a3  ; TOKEN unit", text)
        self.assertIn("0x147ff60  add r8, 0x18", text)
        self.assertIn("0x147ff64  call 0x22857c0", text)
        ev = json.loads((ROOT / "research/t185_combatant_unit_shape.json").read_text(encoding="utf-8"))
        self.assertFalse(ev["promoted"])
        self.assertEqual(ev["CCombatant"]["writer"], "0x147ff20")
        self.assertEqual(ev["CCombatant"]["unit"]["data"], "+0x20")
        self.assertEqual(ev["CCombatant"]["unit"]["size"], "+0x2c")
        self.assertTrue(ev["CCombatant"]["unit"]["omit_if_size_le_0"])
        self.assertEqual(ev["CLandCombatant"]["writer"], "0x134d5f0")
        self.assertEqual(ev["CLandCombatant"]["starts_with_call"], "0x147ff20")

    def test_vtables_and_combat_manager_not_promoted(self):
        ev = json.loads((ROOT / "research/t185_combatant_unit_shape.json").read_text(encoding="utf-8"))
        self.assertEqual(ev["CCombatant"]["vtable"], "0x2a367d0")
        self.assertEqual(ev["CLandCombatant"]["vtable"], "0x2a236a0")
        self.assertTrue(ev["no_carmy_current_combat_pointer_bound"])
        self.assertEqual(ev["gs_combats_size"], 0)
        self.assertTrue(ev["CCombatManager"]["do_not_promote_empty_as_false"])
        self.assertEqual(ev["CCombatManager"]["embedded_at"], "GS+0x260")
        cm = (ROOT / "research/_t185_clip_combatmanager_writer_0xc0eae0.txt").read_text(encoding="utf-8")
        self.assertIn("mov edx, 0x2835  ; TOKEN history", cm)

    def test_activity_data_not_carmy_plus_340(self):
        text = (ROOT / "research/_t185_clip_19eeaa0.txt").read_text(encoding="utf-8")
        self.assertIn("0x19eeaaa  mov r8d, dword ptr [rcx + 8]", text)
        self.assertIn("0x19eeab9  mov edx, 0x2916  ; TOKEN combat", text)
        self.assertIn("0x19eeacf  mov edx, 0x2fba  ; TOKEN training", text)
        ev = json.loads((ROOT / "research/t185_activity_combat_slot.json").read_text(encoding="utf-8"))
        self.assertFalse(ev["promoted"])
        self.assertTrue(ev["SArmyUnitActivityData"]["not_embedded_in_CArmy"])
        self.assertIn("CNameGroupMember", ev["SArmyUnitActivityData"]["carmy_0x340_is"])
        live = json.loads((ROOT / "research/t185_live_carmy_340.json").read_text(encoding="utf-8"))
        self.assertEqual(len(live), 21)
        self.assertTrue(all(u["cls340"] == ".?AVCNameGroupMember@@" for u in live))

    def test_orderinstance_type_is_not_commandlist(self):
        text = (ROOT / "research/_t185_clip_orderinstance_writer_0x10d1450.txt").read_text(encoding="utf-8")
        self.assertIn("0x10d148a  mov r8d, dword ptr [r14 + 0x30]", text)
        self.assertIn("0x10d148e  mov edx, 0xe1  ; TOKEN type", text)
        ev = json.loads((ROOT / "research/t185_orderinstance_type.json").read_text(encoding="utf-8"))
        self.assertFalse(ev["promoted"])
        self.assertIn("not world.own_units.order.type", ev["COrderInstance"]["schema_role"])
        self.assertIn("still unmapped", ev["commandlist_plus8"])

    def test_supply_consumer_has_no_in_supply_token(self):
        text = (ROOT / "research/_t185_clip_supplyconsumer_writer_0xf4ca30.txt").read_text(encoding="utf-8")
        self.assertIn("0xf4ca40  call 0x22858a0", text)
        self.assertIn("0xf4ca51  mov edx, 0x4cf2  ; TOKEN disrupted_supply", text)
        self.assertNotIn("in_supply", text)
        self.assertNotIn("isolated", text)
        ev = json.loads((ROOT / "research/t185_supply_consumer.json").read_text(encoding="utf-8"))
        self.assertFalse(ev["promoted"])
        self.assertTrue(ev["CSupplyConsumer"]["no_in_supply_or_isolated_token"])
        self.assertTrue(ev["still_no_named_in_supply_or_isolated_on_CArmy"])

    def test_inventory_unchanged(self):
        # Historical t185 acceptance is pinned below. The live inventory legitimately
        # advances (t198 has nonempty player-involved combat evidence).
        rec = json.loads((ROOT / "research/t185_inventory_sha256.json").read_text(encoding="utf-8"))
        self.assertFalse(rec["updated"])
        self.assertEqual(rec["fields"], 116)
        self.assertEqual(rec["verified"], 43)
        self.assertEqual(rec["unverified"], 73)
        self.assertFalse(rec["complete_input"])
        off = json.loads((ROOT / "calling/tables/offsets_input_windows_1.19.5.json").read_text(encoding="utf-8"))
        self.assertFalse(off["land_combatant_activity_t185"]["promoted"])
        sess = json.loads((ROOT / "research/t185_session_recheck.json").read_text(encoding="utf-8"))
        self.assertEqual(sess["pid"], 26976)
        self.assertTrue(sess["in_game"])
        self.assertEqual(sess["gs_combats_size"], 0)


if __name__ == "__main__":
    unittest.main()
