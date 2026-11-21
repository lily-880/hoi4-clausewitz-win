# -*- coding: utf-8 -*-
import json, hashlib, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INV = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")


class Tests(unittest.TestCase):
    def test_assign_and_execute_posts(self):
        post = json.loads((ROOT / "research/t196_scaffold_post.json").read_text(encoding="utf-8"))
        self.assertEqual(post.get("ok"), True)
        self.assertIn("oa_post", post["steps"])
        self.assertIn("ex_post", post["steps"])
        self.assertEqual(post["oa_post"]["post_rax"], 1)
        self.assertEqual(post["ex_post"]["post_rax"], 1)
        self.assertEqual(post["nf_post"]["post_rax"], 1)
        self.assertTrue(post["final_pause"]["ok"])
        self.assertEqual(post["final_pause"]["pause"], 1)
        self.assertEqual(post["final_pause"]["speed"], 0)
        self.assertFalse(post["gate_closed"]["allow_post_after_close"])
        self.assertTrue(post["health_final"]["alive"])

    def test_live_scheduled_member_and_execute_byte(self):
        ev = json.loads((ROOT / "research/t196_plan_execute_assign.json").read_text(encoding="utf-8"))
        self.assertEqual(ev["live"]["assigned_unit_ids"], [1838])
        self.assertTrue(ev["live"]["executing"])
        self.assertEqual(ev["live"]["path_70"], [])
        self.assertEqual(ev["live"]["type_30"], 2)
        self.assertIn("world.plans.assigned_unit_ids", ev["promoted"])
        self.assertIn("world.plans.executing", ev["promoted"])
        self.assertIn("world.plans.type", ev["not_promoted"])
        self.assertIn("world.plans.vertex_province_ids", ev["not_promoted"])
        rb = json.loads((ROOT / "research/t196_leader_assign_inspect.json").read_text(encoding="utf-8"))
        self.assertEqual(rb["instance_210"]["unit_id"], 1838)
        self.assertEqual(rb["instance_210"]["unit_handle_18"], [51, 1838])
        self.assertEqual(rb["instance_248"], 1)
        self.assertEqual(rb["instance_path70_n"], 0)
        self.assertEqual(rb["pause"], 1)

    def test_readers_and_offsets(self):
        src = (ROOT / "calling/input_loaded_fields.py").read_text(encoding="utf-8")
        self.assertIn("def own_plans(", src)
        self.assertIn("assigned_unit_ids", src)
        self.assertIn("'executing': bool(r.exact(ip + 0x248, 1)[0])", src)
        self.assertIn("ip + 0x210", src)
        off = (ROOT / "calling/offsets.py").read_text(encoding="utf-8")
        self.assertIn('"OI_SCHEDULED_MEMBER": 0x210', off)
        self.assertIn('"OI_CAN_EXECUTE": 0x248', off)
        tab = json.loads((ROOT / "calling/tables/offsets_input_windows_1.19.5.json").read_text(encoding="utf-8"))
        self.assertEqual(tab["plan_execute_assign_t196"]["promoted"], [
            "world.plans.assigned_unit_ids",
            "world.plans.executing",
        ])

    def test_inventory_promotes_two_fields(self):
        rec = json.loads((ROOT / "research/t196_inventory_sha256.json").read_text(encoding="utf-8"))
        raw = INV.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        self.assertEqual(sha, rec["sha256"])
        self.assertTrue(rec["updated"])
        self.assertEqual(rec["fields"], 116)
        self.assertEqual(rec["tables"], 14)
        self.assertEqual(rec["columns"], 3)
        self.assertEqual(rec["verified"], 64)
        self.assertEqual(rec["unverified"], 52)
        self.assertFalse(rec["complete_input"])
        self.assertEqual(rec["promoted"], [
            "world.plans.assigned_unit_ids",
            "world.plans.executing",
        ])
        text = raw.decode("utf-8")
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
        self.assertIn("| 字段名 | 已验证/未验证 | 说明 |", text)
        self.assertIn("| world.plans.assigned_unit_ids | 已验证 |", text)
        self.assertIn("| world.plans.executing | 已验证 |", text)
        self.assertIn("scheduled_member", text)
        self.assertIn("COrderInstance+0x248", text)
        self.assertIn("| world.plans.type | 未验证 |", text)
        self.assertIn("| world.plans.vertex_province_ids | 未验证 |", text)
        self.assertIn("| world.own_units.order.type | 未验证 |", text)
        self.assertIn("| world.own_units.order.eta | 未验证 |", text)
        self.assertNotIn("附录", text)
        n_tables = sum(1 for ln in text.splitlines() if ln.startswith("| 字段名 | 已验证/未验证 | 说明 |"))
        self.assertEqual(n_tables, 14)
        n_fields = sum(1 for ln in text.splitlines() if ln.startswith("| ") and not ln.startswith("| 字段名 |") and not ln.startswith("| ---"))
        self.assertEqual(n_fields, 116)


if __name__ == "__main__":
    unittest.main()
