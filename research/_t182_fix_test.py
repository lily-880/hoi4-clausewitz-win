from pathlib import Path
p=Path("research/test_t182_input_combat_order.py")
t=p.read_text(encoding="utf-8")
old='        self.assertIn("| 字段名 | 已验证/未验证 | 一句简短说明 |", text)'
new='''        self.assertIn("| 字段名 | 已验证/未验证 | 说明 |", text)
        self.assertIn("| world.own_units.in_combat | 未验证 |", text)
        self.assertIn("| world.own_units.order.type | 未验证 |", text)'''
if old not in t:
    raise SystemExit("pattern not found")
p.write_text(t.replace(old,new), encoding="utf-8")
print("patched")
