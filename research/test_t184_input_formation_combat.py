import json, hashlib, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INV = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
T181_SHA = "ae0fd55a22e6e8917cacf0d767f659673f00c3ccbcda726b3ee727be8f288254"


class Tests(unittest.TestCase):
    def test_handle_id_writers(self):
        base = (ROOT / "research/_t184_clip_base_id_writer_0x22858a0.txt").read_text(encoding="utf-8")
        self.assertIn("0x22858ba  mov edx, 0xb  ; TOKEN id", base)
        self.assertIn("0x22858dc  mov edx, dword ptr [rdi + 0xc]", base)
        self.assertIn("0x22858cf  mov edx, 0xb  ; TOKEN id", base)
        self.assertIn("0x2285927  mov edx, 0xe1  ; TOKEN type", base)
        self.assertIn("0x2285934  mov edx, dword ptr [rdi + 8]", base)
        sub = (ROOT / "research/_t184_clip_unit_handle_writer_0x22857c0.txt").read_text(encoding="utf-8")
        self.assertIn("0x22857e2  mov edx, 0xb  ; TOKEN id", sub)
        self.assertIn("0x22857ef  mov edx, dword ptr [rdi + 4]", sub)
        self.assertIn("0x228583a  mov edx, 0xe1  ; TOKEN type", sub)
        self.assertIn("0x2285847  mov edx, dword ptr [rdi]", sub)

    def test_theatre_writer_groups_and_units(self):
        text = (ROOT / "research/_t184_clip_theatre_writer_0xf81510.txt").read_text(encoding="utf-8")
        self.assertIn("0xf81534  call 0x22858a0", text)
        self.assertIn("0xf81774  movsxd rdi, dword ptr [rbp + 0x8c]", text)
        self.assertIn("0xf8177b  test rdi, rdi", text)
        self.assertIn("0xf8177e  jle 0xf817b0", text)
        self.assertIn("0xf8179b  mov edx, 0x30ae  ; TOKEN orders_group", text)
        self.assertIn("0xf817cb  mov edx, 0x3801  ; TOKEN field_marshal_group", text)
        self.assertIn("0xf817fb  mov edx, 0x35d1  ; TOKEN theater_group", text)
        self.assertIn("0xf81810  movsxd rdi, dword ptr [rbp + 0x74]", text)
        self.assertIn("0xf81820  mov rax, qword ptr [rbp + 0x68]", text)
        self.assertIn("0xf81828  add r8, 0x18", text)
        self.assertIn("0xf8182c  mov edx, 0x28a3  ; TOKEN unit", text)
        self.assertIn("call 0x22857c0", text)

    def test_orders_and_army_group_writers(self):
        og = (ROOT / "research/_t184_clip_ordersgroup_writer_0xc4d030.txt").read_text(encoding="utf-8")
        self.assertIn("0xc4d05a  call 0x22858a0", og)
        self.assertIn("lea r8, [r14 + 0x160]", og)
        self.assertIn("mov edx, 0x1b  ; TOKEN name", og)
        self.assertIn("mov rax, qword ptr [r14 + 0x50]", og)
        self.assertIn("mov edx, 0x2b11  ; TOKEN member", og)
        self.assertIn("lea r8, [rax + 0x18]", og)
        self.assertIn("mov edx, 0x28a3  ; TOKEN unit", og)
        self.assertIn("mov r8, qword ptr [r14 + 0x88]", og)
        self.assertIn("add r8, 8", og)
        self.assertIn("mov edx, 0x28b7  ; TOKEN leader", og)
        ag = (ROOT / "research/_t184_clip_armygroup_writer_0xc4cfa0.txt").read_text(encoding="utf-8")
        self.assertIn("movsxd rbp, dword ptr [rcx + 0x23c]", ag)
        self.assertIn("mov rax, qword ptr [rdi + 0x230]", ag)
        self.assertIn("mov edx, 0x30ae  ; TOKEN orders_group", ag)
        self.assertIn("add r8, 8", ag)
        self.assertIn("jmp 0xc4d030", ag)
        ev = json.loads((ROOT / "research/t184_formation_writers.json").read_text(encoding="utf-8"))
        self.assertFalse(ev["promoted"])
        self.assertEqual(ev["COrdersGroup"]["schema_role"], "world.armies (集团军)")

    def test_landcombat_and_combatant_unit_handles(self):
        lc = (ROOT / "research/_t184_clip_landcombat_writer_0x147fe80.txt").read_text(encoding="utf-8")
        self.assertIn("0x147fe90  call 0x22858a0", lc)
        self.assertIn("0x147fe95  mov r8, qword ptr [rbx + 0x28]", lc)
        self.assertIn("0x147fea1  mov r8d, dword ptr [r8 + 0xa4]", lc)
        self.assertIn("0x147fe99  mov edx, 0x286d  ; TOKEN location", lc)
        self.assertIn("0x147fecf  mov r8, qword ptr [rbx + 0x18]", lc)
        self.assertIn("0x147fed3  mov edx, 0x28f5  ; TOKEN attacker", lc)
        self.assertIn("0x147fee0  mov r8, qword ptr [rbx + 0x20]", lc)
        self.assertIn("0x147fee4  mov edx, 0x28f6  ; TOKEN defender", lc)
        ca = (ROOT / "research/_t184_clip_landcombatant_writer_0x134d5f0.txt").read_text(encoding="utf-8")
        self.assertIn("mov rax, qword ptr [rbx + 0xe8]", ca)
        self.assertIn("mov edx, 0x29e0  ; TOKEN front", ca)
        self.assertIn("add r8, 0x18", ca)
        self.assertIn("mov edx, 0x29e2  ; TOKEN reserves", ca)
        ev = json.loads((ROOT / "research/t184_combat_writers.json").read_text(encoding="utf-8"))
        self.assertFalse(ev["promoted"])
        self.assertTrue(ev["no_carmy_current_combat_pointer_bound"])
        self.assertEqual(ev["gs_combats"]["size"], 0)

    def test_live_theatre_units_not_promoted_as_formation(self):
        live = json.loads((ROOT / "research/t184_live_theatre.json").read_text(encoding="utf-8"))
        ev = json.loads((ROOT / "research/t184_formation_writers.json").read_text(encoding="utf-8"))
        self.assertEqual(len(live["theatres"]), 1)
        t = live["theatres"][0]
        self.assertEqual(t["class"], ".?AVCTheatre@@")
        self.assertEqual(t["id"], 43)
        self.assertEqual(t["unit"]["size"], 21)
        self.assertEqual([u["unit_id"] for u in t["units"]], list(range(1829, 1850)))
        self.assertEqual(t["orders_group"]["size"], 0)
        self.assertEqual(t["field_marshal_group"]["size"], 0)
        self.assertEqual(t["theater_group"]["size"], 0)
        self.assertEqual(live["gs_combats"]["size"], 0)
        self.assertFalse(ev["promoted"])
        self.assertIn("not formation.army_id", ev["live_eth"]["note"])

    def test_inventory_unchanged(self):
        rec = json.loads((ROOT / "research/t184_inventory_sha256.json").read_text(encoding="utf-8"))
        self.assertFalse(rec["updated"])
        self.assertEqual(rec["sha256"], T181_SHA)
        self.assertEqual(rec["counts"]["verified"], 43)
        # live D SHA may change in later batches; this test pins t184's recorded hash
        text = INV.read_text(encoding="utf-8")
        self.assertIn("| 字段名 | 已验证/未验证 | 说明 |", text)
        self.assertIn("| world.combats.combat_id | 未验证 |", text)
        self.assertIn("| world.own_units.in_combat | 未验证 |", text)
        # formation.army_id / world.armies.army_id stayed unverified in t184; later batches may promote them


if __name__ == "__main__":
    unittest.main()
