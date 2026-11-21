from pathlib import Path
p = Path("research/test_t192_input_army_leader.py")
t = p.read_text(encoding="utf-8")
t = t.replace('self.assertEqual(con["unassigned_count"], 19)',
              'self.assertEqual(sum(1 for x in con["leaders_1048"] if x["assigned_handle"] == [0, 0]), 19)')
t = t.replace('        self.assertIn("| world.army_groups.army_id | 未验证 |" if False else "| world.army_groups.army_group_id | 未验证 |", text)\n',
              '        self.assertIn("| world.army_groups.army_group_id | 未验证 |", text)\n')
p.write_text(t, encoding="utf-8")
print("test patched")
# confirm contrast has leaders_1048
import json
con=json.loads(Path("research/t192_contrast.json").read_text(encoding="utf-8"))
print("keys", con.keys())
print("n leaders_1048", len(con.get("leaders_1048") or []))
