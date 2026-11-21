import json, hashlib, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INV = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
T193_SHA = "e4b7db714556524ac084c55367414e5f3ac55feb4b904bbb2fdec8ea866b75f0"


class Tests(unittest.TestCase):
    def test_army_group_created_and_leader_appointed(self):
        post = json.loads((ROOT / "research/t193_ag_post.json").read_text(encoding="utf-8"))
        self.assertEqual(post["authorized_by"], ["pt180u"])
        self.assertEqual(post["ag_dry_isvalid"]["isvalid"], 1)
        self.assertEqual(post["ag_post"]["post_rax"], 1)
        self.assertTrue(post["ag_created"])
        after = post["theatre_after_ag"][0]["field_marshal"]["items"][0]
        self.assertEqual(after["class"], ".?AVCArmyGroup@@")
        self.assertEqual(after["handle"], [53, 2])
        self.assertEqual(after["name"], "第1集团军群")
        self.assertEqual(after["leader_ptr"], "0x0")
        self.assertEqual(after["child_orders"][0]["handle"], [53, 1])
        self.assertEqual(post["sl_packed"]["leader"], [4713, 313])
        self.assertEqual(post["sl_packed"]["group"], [53, 2])
        self.assertEqual(post["sl_dry_isvalid"]["isvalid"], 1)
        self.assertEqual(post["sl_post"]["post_rax"], 1)
        final = post["theatre_final"][0]["field_marshal"]["items"][0]
        self.assertEqual(final["leader_handle"], [4713, 313])
        self.assertEqual(post["keep_path_final"], [8036])
        self.assertTrue(post["still_paused"])
        self.assertEqual(post["speed_after"], 0)
        self.assertFalse(post["gate_closed"]["allow_post_after_close"])

    def test_new_root_plan_created_path_empty(self):
        post = json.loads((ROOT / "research/t193_plan_post.json").read_text(encoding="utf-8"))
        self.assertEqual(post["nr_dry_isvalid"]["isvalid"], 1)
        self.assertEqual(post["nr_post"]["post_rax"], 1)
        self.assertTrue(post["plan_created"])
        inst = post["army_after"]["order_instances"][0]
        self.assertEqual(inst["class"], ".?AVCOrderInstance@@")
        self.assertEqual(inst["type_30"], 2)
        self.assertEqual(inst["instance_id_244"], 1)
        self.assertEqual(inst["path_70"], [])
        self.assertEqual(post["keep_path_after"], [8036])
        self.assertTrue(post["still_paused"])
        self.assertFalse(post["gate_closed"]["allow_post_after_close"])
        self.assertEqual(post["provinces"], [13237, 13238])

    def test_live_readers_and_assigned_to_kinds(self):
        live = json.loads((ROOT / "research/t193_live_fields.json").read_text(encoding="utf-8"))
        self.assertEqual(live["pid"], 26976)
        self.assertEqual(live["pause"], 1)
        self.assertEqual(live["speed"], 0)
        self.assertEqual(live["army_groups"], [{
            "army_group_id": 2,
            "name": "第1集团军群",
            "leader_id": 313,
            "army_ids": [1],
        }])
        self.assertEqual(live["armies"][0]["plan_id"], 1)
        self.assertEqual(live["plans"], [{"plan_id": 1, "assigned_army_ids": [1]}])
        kinds = {row["leader_id"]: row["assigned_to"] for row in live["assigned"]}
        self.assertEqual(kinds[312], {"kind": "army", "id": 1})
        self.assertEqual(kinds[313], {"kind": "army_group", "id": 2})
        u = live["units_with_formation"][0]
        self.assertEqual(u["unit_id"], 1838)
        self.assertEqual(u["army_id"], 1)
        self.assertEqual(u["army_group_id"], 2)
        self.assertEqual(live["keep_1829"]["path"], [8036])
        self.assertIsNone(live["keep_1829"]["army_id"])

    def test_promoted_and_honest_non_promotions(self):
        ev = json.loads((ROOT / "research/t193_army_group_plan.json").read_text(encoding="utf-8"))
        self.assertEqual(len(ev["promoted"]), 8)
        self.assertIn("world.army_groups.army_group_id", ev["promoted"])
        self.assertIn("world.plans.plan_id", ev["promoted"])
        self.assertIn("world.plans.type", ev["not_promoted"])
        self.assertIn("world.plans.vertex_province_ids", ev["not_promoted"])
        self.assertIn("world.plans.executing", ev["not_promoted"])
        off = json.loads((ROOT / "calling/tables/offsets_input_windows_1.19.5.json").read_text(encoding="utf-8"))
        self.assertEqual(len(off["army_group_plan_t193"]["promoted"]), 8)
        self.assertIn("COrdersGroup_parent_army_group", off["army_group_plan_t193"])

    def test_inventory_promotes_eight_fields(self):
        rec = json.loads((ROOT / "research/t193_inventory_sha256.json").read_text(encoding="utf-8"))
        # live D SHA may change in later batches; this test pins t193's recorded hash
        self.assertEqual(rec["sha256"], T193_SHA)
        self.assertTrue(rec["updated"])
        self.assertEqual(rec["fields"], 116)
        self.assertEqual(rec["tables"], 14)
        self.assertEqual(rec["columns"], 3)
        self.assertEqual(rec["verified"], 62)
        self.assertEqual(rec["unverified"], 54)
        self.assertFalse(rec["complete_input"])
        self.assertIn("world.plans.plan_id", rec["promoted"])
        self.assertEqual(len(rec["promoted"]), 8)

    def test_readers_exist(self):
        src = (ROOT / "calling/input_loaded_fields.py").read_text(encoding="utf-8")
        self.assertIn("def own_army_groups(", src)
        self.assertIn("def unit_formation_army_group_id(", src)
        self.assertIn("def own_plans(", src)
        self.assertIn("def assigned_to_from_handle(", src)
        off = (ROOT / "calling/offsets.py").read_text(encoding="utf-8")
        self.assertIn('"OG_PARENT_ARMY_GROUP": 0x1B8', off)
        self.assertIn('"AG_CHILD_ORDERS": 0x230', off)
        self.assertIn('"OI_INSTANCE_ID": 0x244', off)


if __name__ == "__main__":
    unittest.main()
