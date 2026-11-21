# -*- coding: utf-8 -*-
from pathlib import Path

test = r'''import json, hashlib, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INV = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
T181_SHA = "ae0fd55a22e6e8917cacf0d767f659673f00c3ccbcda726b3ee727be8f288254"


class Tests(unittest.TestCase):
    def test_path_serializer_empty_skip(self):
        text = (ROOT / "research/_t182_clip_path_serializer_0x1d2bf0.txt").read_text(encoding="utf-8")
        self.assertIn("0x1d2c00  movsxd rbx, dword ptr [r8 + 0xc]", text)
        self.assertIn("0x1d2c07  mov r14, qword ptr [r8]", text)
        self.assertIn("0x1d2c0a  test ebx, ebx", text)
        self.assertIn("0x1d2c0c  jle 0x1d2c7f", text)
        self.assertIn("mov edx, dword ptr [r14 + rbx*4]", text)

    def test_commandlist_omitted_when_size_zero(self):
        text = (ROOT / "research/_t182_clip_carmy_base_writer_0xc5c0a0.txt").read_text(encoding="utf-8")
        self.assertIn("0xc5c43f  cmp dword ptr [rdi + 0x2bc], 0", text)
        self.assertIn("0xc5c448  mov edx, 0xcb  ; TOKEN commandlist", text)
        self.assertIn("lea r8, [rdi + 0x1f0]", text)
        self.assertIn("mov edx, 0x174  ; TOKEN path", text)
        self.assertIn("lea r8, [rdi + 0x210]", text)
        self.assertIn("mov edx, 0x362c  ; TOKEN full_path", text)

    def test_supply_tokens_on_secondary_writer(self):
        text = (ROOT / "research/_t182_clip_carmy_secondary_writer_0xced2e0.txt").read_text(encoding="utf-8")
        self.assertIn("qword ptr [rbx + 0x5f0]", text)
        self.assertIn("mov edx, 0x3a43  ; TOKEN max_supply", text)
        self.assertIn("qword ptr [rbx + 0x600]", text)
        self.assertIn("mov edx, 0x4ced  ; TOKEN army_current_supply_ratio", text)
        self.assertIn("qword ptr [rbx + 0x5f8]", text)
        self.assertIn("mov edx, 0x4cec  ; TOKEN supply_gain", text)
        w = json.loads((ROOT / "research/t182_carmy_writers.json").read_text(encoding="utf-8"))
        self.assertEqual(w["secondary_interface"]["location"], "CArmy+0x10")
        self.assertEqual(w["fields"]["army_current_supply_ratio"]["ca_off"], "0x610")
        self.assertTrue(w["fields"]["army_current_supply_ratio"]["not_a_0_to_1_ratio"])
        self.assertFalse(w["promoted"])

    def test_getordertype_is_plan_object_not_unit_order(self):
        move = (ROOT / "research/_t182_clip_GetOrderType_0x10b2c60.txt").read_text(encoding="utf-8")
        inv = (ROOT / "research/_t182_clip_GetOrderType_0x10b0370.txt").read_text(encoding="utf-8")
        self.assertIn("cmp dword ptr [rcx + 0x30], 1", move)
        self.assertIn("cmp dword ptr [rcx + 0x30], 3", inv)
        w = json.loads((ROOT / "research/t182_carmy_writers.json").read_text(encoding="utf-8"))
        self.assertEqual(w["not_unit_fields"]["GetOrderType"]["values"]["1"], "ORDER_MOVE")
        self.assertEqual(w["not_unit_fields"]["GetOrderType"]["values"]["3"], "ORDER_INVASION")
        land = (ROOT / "research/_t182_clip_land_combat_id_0x208f90.txt").read_text(encoding="utf-8")
        self.assertIn("dword ptr [r15 + 0x748]", land)
        self.assertIn("mov edx, 0x34a6  ; TOKEN land_combat_id", land)

    def test_empty_live_arrays_are_not_idle_or_false(self):
        ev = json.loads((ROOT / "research/t182_empty_not_idle.json").read_text(encoding="utf-8"))
        live = json.loads((ROOT / "research/t182_carmy_order_supply_live.json").read_text(encoding="utf-8"))
        self.assertFalse(ev["promoted"])
        self.assertEqual(ev["live"]["commandlist"]["size"], 0)
        self.assertEqual(ev["live"]["path"]["size"], 0)
        self.assertEqual(ev["live"]["full_path"]["size"], 0)
        self.assertEqual(ev["live"]["gs_combats"]["size"], 0)
        self.assertEqual(ev["live"]["supply_ratio_610"], 72.0)
        self.assertEqual(len(live["units"]), 21)
        for u in live["units"]:
            self.assertEqual(u["commandlist"]["size"], 0)
            self.assertEqual(u["path"]["size"], 0)
            self.assertEqual(u["full_path"]["size"], 0)
            self.assertEqual(u["retreat"], 0)
            self.assertEqual(u["supply_ratio"], 72.0)
            self.assertEqual(u["max_supply"], 108.0)
        self.assertIn("idle", ev["why_not_promoted"]["order"])
        self.assertIn("IsInCombat", ev["why_not_promoted"]["in_combat"])

    def test_inventory_unchanged(self):
        rec = json.loads((ROOT / "research/t182_inventory_sha256.json").read_text(encoding="utf-8"))
        self.assertFalse(rec["updated"])
        self.assertEqual(rec["sha256"], T181_SHA)
        self.assertEqual(rec["counts"]["verified"], 43)
        self.assertEqual(rec["counts"]["unverified"], 73)
        self.assertEqual(hashlib.sha256(INV.read_bytes()).hexdigest(), T181_SHA)
        text = INV.read_text(encoding="utf-8")
        self.assertNotRegex(text, r"in_combat.*已验证")
        # still 116 field rows in 14 tables is counted elsewhere; keep column shape
        self.assertIn("| 字段名 | 已验证/未验证 | 一句简短说明 |", text)


if __name__ == "__main__":
    unittest.main()
'''
Path("research/test_t182_input_combat_order.py").write_text(test, encoding="utf-8")

# update writers clip path now that file exists
import json
p = Path("research/t182_carmy_writers.json")
w = json.loads(p.read_text(encoding="utf-8"))
w["path_serializer"]["clip"] = "research/_t182_clip_path_serializer_0x1d2bf0.txt"
p.write_text(json.dumps(w, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("test written")
