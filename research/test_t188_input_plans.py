import json, hashlib, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INV = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
T187_SHA = "98d83a601f67b73d71a62c559e9a9a29a75e92eb831c7df2be4d42de7ac7e201"


class Tests(unittest.TestCase):
    def test_orderinstance_writer_slots(self):
        w = (ROOT / "research/_t188_clip_orderinstance_writer_0x10d1450.txt").read_text(encoding="utf-8")
        self.assertIn("0x10d148a  mov r8d, dword ptr [r14 + 0x30]", w)
        self.assertIn("0x10d148e  mov edx, 0xe1  ; TOKEN type", w)
        self.assertIn("0x10d149b  lea r8, [r14 + 0x70]", w)
        self.assertIn("0x10d149f  mov edx, 0x174  ; TOKEN path", w)
        self.assertIn("0x10d14ac  lea r8, [r14 + 0xe0]", w)
        self.assertIn("0x10d14b3  mov edx, 0x2e3b  ; TOKEN states", w)
        self.assertIn("0x10d14c0  mov r8d, dword ptr [r14 + 0x244]", w)
        self.assertIn("0x10d14c7  mov edx, 0x30af  ; TOKEN instance_id", w)
        self.assertIn("0x10d1a10  mov edx, 0x30b2  ; TOKEN can_execute", w)
        tail = (ROOT / "research/_t188_clip_orderinstance_writer_tail.txt").read_text(encoding="utf-8")
        self.assertIn("0x10d1e37  mov edx, 0x36f9  ; TOKEN area_defense_settings", tail)

    def test_ordersgroup_holds_order_instances(self):
        g = (ROOT / "research/_t188_clip_ordersgroup_writer_0xc4d030.txt").read_text(encoding="utf-8")
        self.assertIn("0xc4d100  mov rax, qword ptr [r14 + 0x98]", g)
        self.assertIn("0xc4d208  mov edx, 0x35f7  ; TOKEN order_instance", g)

    def test_getordertype_move_and_invasion(self):
        ev = json.loads((ROOT / "research/t188_plan_writers.json").read_text(encoding="utf-8"))
        self.assertEqual(ev["COrderInstance"]["GetOrderType_proven"]["1"].split()[0], "ORDER_MOVE")
        self.assertEqual(ev["COrderInstance"]["GetOrderType_proven"]["3"].split()[0], "ORDER_INVASION")
        self.assertIn("0x30b2", ev["COrderInstance"]["can_execute"])
        self.assertIn("not plans.executing", ev["COrderInstance"]["can_execute"])

    def test_cfront_is_border_not_plan(self):
        f = (ROOT / "research/_t184_clip_front_writer_0xf809b0.txt").read_text(encoding="utf-8")
        self.assertIn("TOKEN dirty", f)
        self.assertIn("TOKEN provinces", f)
        self.assertIn("TOKEN enemies", f)
        self.assertIn("TOKEN section", f)
        self.assertIn("TOKEN area", f)
        self.assertNotIn("TOKEN instance_id", f)
        self.assertNotIn("TOKEN type", f)
        live = json.loads((ROOT / "research/t188_live_plans.json").read_text(encoding="utf-8"))
        self.assertEqual(len(live["eth_fronts"]), 6)
        self.assertTrue(all(x["class"] == ".?AVCFront@@" for x in live["eth_fronts"]))
        self.assertEqual(live["eth_order_instances"], [])
        self.assertEqual(live["world_order_instances"], 0)
        self.assertEqual(live["world_orders_groups"], 0)
        self.assertEqual(live["front_classes"], {".?AVCFront@@": 910})
        self.assertEqual(live["eth_theatre"]["orders_group"]["size"], 0)

    def test_already_spotted_is_naval_not_land_fow(self):
        ev = json.loads((ROOT / "research/t188_plan_writers.json").read_text(encoding="utf-8"))
        self.assertIn("naval-mission", ev["not_land_fow"]["already_spotted_0x3bb3"])
        clip = (ROOT / "research/_t188_clip_already_spotted_0x104353b.txt").read_text(encoding="utf-8")
        self.assertIn("TOKEN already_spotted", clip)
        self.assertIn("TOKEN navy_engagement_rule", clip)
        self.assertIn("TOKEN spotting_target", clip)

    def test_inventory_unchanged_plans_unverified(self):
        rec = json.loads((ROOT / "research/t188_inventory_sha256.json").read_text(encoding="utf-8"))
        self.assertFalse(rec["updated"])
        self.assertEqual(rec["sha256"], T187_SHA)
        raw = INV.read_bytes()
        # live D SHA may change in later batches; this test pins t188's recorded hash
        self.assertEqual(rec["fields"], 116)
        self.assertEqual(rec["verified"], 47)
        self.assertEqual(rec["unverified"], 69)
        self.assertFalse(rec["complete_input"])
        text = raw.decode("utf-8")
        self.assertIn("| world.plans.type | 未验证 |", text)
        # world.plans.plan_id stayed unverified in t188; later batches may promote it
        self.assertIn("| world.crises.kind | 未验证 |", text)
        self.assertIn("| world.visible_units.visibility.spotted | 未验证 |", text)
        self.assertIn("| meta.speed | 已验证 |", text)
        off = json.loads((ROOT / "calling/tables/offsets_input_windows_1.19.5.json").read_text(encoding="utf-8"))
        self.assertFalse(off["plan_orderinstance_t188"]["promoted"])
        ev = json.loads((ROOT / "research/t188_plan_writers.json").read_text(encoding="utf-8"))
        self.assertEqual(ev["promoted"], [])
        sess = json.loads((ROOT / "research/t188_session_recheck.json").read_text(encoding="utf-8"))
        self.assertEqual(sess["pid"], 26976)
        self.assertTrue(sess["in_game"])
        self.assertEqual(sess["pause_flag_6c1"], 1)


if __name__ == "__main__":
    unittest.main()
