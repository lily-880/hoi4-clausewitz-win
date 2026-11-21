import json, hashlib, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INV = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
T192_SHA = "0633ed5dd85b17bd13dfff0150edf721b32d9fc961a4aa916311799b5aaf39d5"


class Tests(unittest.TestCase):
    def test_order_group_command_posted_while_paused(self):
        post = json.loads((ROOT / "research/t192_post.json").read_text(encoding="utf-8"))
        self.assertEqual(post["authorized_by"], ["pt180u"])
        self.assertEqual(post["member_unit"], 1838)
        self.assertEqual(post["keep_unit"], 1829)
        self.assertEqual(post["og_dry_isvalid"]["isvalid"], 1)
        self.assertEqual(post["og_post"]["post_rax"], 1)
        self.assertTrue(post["og_created"])
        after = post["theatre_after"][0]["orders_groups"][0]
        self.assertEqual(after["class"], ".?AVCOrdersGroup@@")
        self.assertEqual(after["handle_type"], 53)
        self.assertEqual(after["id"], 1)
        self.assertEqual(after["name"], "第1集团军")
        self.assertEqual(after["leader_ptr"], "0x0")
        self.assertEqual(post["keep_path_after_og"], [8036])
        self.assertTrue(post["health_after_og"]["alive"])

    def test_set_army_leader_posted_and_not_deployed_flag(self):
        post = json.loads((ROOT / "research/t192_post.json").read_text(encoding="utf-8"))
        self.assertTrue(post["leader_attempted"])
        self.assertEqual(post["sl_packed"]["leader"], [4713, 312])
        self.assertEqual(post["sl_packed"]["group"], [53, 1])
        self.assertEqual(post["sl_packed"]["deploy_hq"], 0)
        self.assertEqual(post["sl_dry_isvalid"]["isvalid"], 1)
        self.assertEqual(post["sl_post"]["post_rax"], 1)
        final = post["theatre_final"][0]["orders_groups"][0]
        self.assertEqual(final["leader_id"], 312)
        self.assertEqual(final["leader_class"], ".?AVCArmyLeader@@")
        self.assertEqual(post["leaders_after_summary"]["deployed_nonzero"], [])
        self.assertTrue(post["still_paused"])
        self.assertEqual(post["speed_index_after"], 0)
        self.assertEqual(post["keep_path_final"], [8036])
        self.assertFalse(post["gate_closed"]["allow_post_after_close"])
        self.assertFalse(post["gate_closed"]["marker_exists"])

    def test_live_contrast_handle_and_backlink(self):
        con = json.loads((ROOT / "research/t192_contrast.json").read_text(encoding="utf-8"))
        self.assertEqual(con["c0_group_units"], [1838])
        self.assertEqual(len(con["leaders_assigned_nonzero"]), 1)
        row = con["leaders_assigned_nonzero"][0]
        self.assertEqual(row["leader_id"], 312)
        self.assertEqual(row["assigned_handle"], [53, 1])
        self.assertEqual(row["deployed"], 0)
        self.assertEqual(sum(1 for x in con["leaders_1048"] if x["assigned_handle"] == [0, 0]), 19)
        mem = con["member_resolve"][0]
        self.assertEqual(mem["primary_id_1c"], 1838)
        self.assertEqual(mem["primary_handle"], [51, 1838])
        live = json.loads((ROOT / "research/t192_live_fields.json").read_text(encoding="utf-8"))
        self.assertEqual(live["pid"], 26976)
        self.assertEqual(live["pause_flag_6c1"], 1)
        self.assertEqual(live["speed_index"], 0)
        self.assertEqual(live["armies"], [{
            "army_id": 1,
            "name": "第1集团军",
            "leader_id": 312,
            "unit_ids": [1838],
        }])
        self.assertEqual(live["assigned_leaders"][0]["assigned_to"], {"kind": "army", "id": 1})
        self.assertEqual(live["units_with_army"][0]["unit_id"], 1838)
        self.assertEqual(live["units_with_army"][0]["formation_army_id"], 1)
        self.assertEqual(live["keep_1829"]["path"], [8036])
        self.assertIsNone(live["keep_1829"]["formation_army_id"])
        self.assertEqual(len(live["units_without_army"]), 20)

    def test_promoted_and_honest_non_promotions(self):
        ev = json.loads((ROOT / "research/t192_army_leader.json").read_text(encoding="utf-8"))
        self.assertEqual(len(ev["promoted"]), 6)
        self.assertIn("world.armies.army_id", ev["promoted"])
        self.assertIn("world.leaders.assigned_to", ev["promoted"])
        self.assertIn("world.armies.plan_id", ev["not_promoted"])
        self.assertIn("world.own_units.formation.army_group_id", ev["not_promoted"])
        off = json.loads((ROOT / "calling/tables/offsets_input_windows_1.19.5.json").read_text(encoding="utf-8"))
        self.assertEqual(off["army_leader_t192"]["CArmy_orders_group"].split(";")[0], "+0xC0 COrdersGroup*")
        self.assertIn("0x1048", off["army_leader_t192"]["CArmyLeader_assigned_handle"])
        self.assertEqual(len(off["army_leader_t192"]["promoted"]), 6)
        self.assertEqual(len(off["army_leader_t192"]["not_promoted"]), 6)

    def test_inventory_promotes_six_fields(self):
        rec = json.loads((ROOT / "research/t192_inventory_sha256.json").read_text(encoding="utf-8"))
        self.assertEqual(rec["sha256"], T192_SHA)
        raw = INV.read_bytes()
        # live D SHA may change in later batches; this test pins t192's recorded hash
        self.assertTrue(rec["updated"])
        self.assertEqual(rec["fields"], 116)
        self.assertEqual(rec["tables"], 14)
        self.assertEqual(rec["columns"], 3)
        self.assertEqual(rec["verified"], 54)
        self.assertEqual(rec["unverified"], 62)
        self.assertFalse(rec["complete_input"])
        text = raw.decode("utf-8")
        self.assertIn("| 字段名 | 已验证/未验证 | 说明 |", text)
        for name in rec["promoted"]:
            self.assertIn(f"| {name} | 已验证 |", text)
        # formation.army_group_id / army_groups.* / armies.plan_id stayed unverified in t192; later batches may promote them
        self.assertIn("| world.own_units.order.type | 未验证 |", text)
        self.assertIn("CArmy+0xC0", text)
        self.assertIn("CArmyLeader+0x1048", text)
        self.assertNotIn("附录", text)
        n_tables = sum(1 for ln in text.splitlines() if ln.startswith("| 字段名 | 已验证/未验证 | 说明 |"))
        self.assertEqual(n_tables, 14)

    def test_readers_and_recipe_exist(self):
        src = (ROOT / "calling/input_loaded_fields.py").read_text(encoding="utf-8")
        self.assertIn("def own_armies(", src)
        self.assertIn("def unit_formation_army_id(", src)
        self.assertIn("lp + 0x1048", src)
        self.assertIn("army + 0xc0", src)
        off = (ROOT / "calling/offsets.py").read_text(encoding="utf-8")
        self.assertIn('"CA_ORDERS_GROUP": 0xC0', off)
        self.assertIn('"CAL_ASSIGNED_HANDLE": 0x1048', off)
        rec = (ROOT / "calling/army_subjects.py").read_text(encoding="utf-8")
        self.assertIn("orders_group_off", rec)
        self.assertIn("0x30", rec)
        self.assertIn('"posting": "DISABLED"', rec)


if __name__ == "__main__":
    unittest.main()
