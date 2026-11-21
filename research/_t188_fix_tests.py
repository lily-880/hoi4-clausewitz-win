from pathlib import Path
p=Path("research/test_t188_input_plans.py")
t=p.read_text(encoding="utf-8")
old1='''        self.assertIn("0x10d14c7  mov edx, 0x30af  ; TOKEN instance_id", w)
        tail = (ROOT / "research/_t188_clip_orderinstance_writer_tail.txt").read_text(encoding="utf-8")
        self.assertIn("0x10d1a10  mov edx, 0x30b2  ; TOKEN can_execute", tail)
        self.assertIn("0x10d1e37  mov edx, 0x36f9  ; TOKEN area_defense_settings", tail)
'''
new1='''        self.assertIn("0x10d14c7  mov edx, 0x30af  ; TOKEN instance_id", w)
        self.assertIn("0x10d1a10  mov edx, 0x30b2  ; TOKEN can_execute", w)
        tail = (ROOT / "research/_t188_clip_orderinstance_writer_tail.txt").read_text(encoding="utf-8")
        self.assertIn("0x10d1e37  mov edx, 0x36f9  ; TOKEN area_defense_settings", tail)
'''
assert old1 in t, "block1 not found"
t=t.replace(old1,new1)
old2='        self.assertIn("can_execute", ev["COrderInstance"]["can_execute"])'
new2='''        self.assertIn("0x30b2", ev["COrderInstance"]["can_execute"])
        self.assertIn("not plans.executing", ev["COrderInstance"]["can_execute"])'''
assert old2 in t, "block2 not found"
t=t.replace(old2,new2)
p.write_text(t, encoding="utf-8", newline="\n")
print("patched ok")
